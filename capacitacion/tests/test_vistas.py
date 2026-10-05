"""Pruebas de las vistas de capacitación (permisos, flujo del Colaborador y gestión)."""

from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from capacitacion import servicios
from capacitacion.models import Asignacion, Curso, Intento, Pregunta
from panel.models import Bitacora
from usuarios.tests.utilidades import crear_admin, crear_departamento, crear_usuario

from .utilidades import completar_todo, crear_curso, crear_evaluacion, respuestas

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


class PermisosCapacitacionTests(TestCase):
    """RF-04/05: cada vista administrativa de capacitación responde 403 al Colaborador."""

    @classmethod
    def setUpTestData(cls):
        cls.colaborador = crear_usuario()
        cls.admin = crear_admin()
        cls.curso = crear_curso()
        cls.evaluacion = crear_evaluacion(cls.curso)
        cls.leccion = cls.curso.lecciones.first()
        cls.pregunta = cls.evaluacion.preguntas.first()

    def vistas(self):
        c, lec, p = self.curso.pk, self.leccion.pk, self.pregunta.pk
        return [
            ("capacitacion:cursos_admin", [], "get"),
            ("capacitacion:curso_crear", [], "get"),
            ("capacitacion:curso_detalle_admin", [c], "get"),
            ("capacitacion:curso_editar", [c], "get"),
            ("capacitacion:curso_asignar", [c], "get"),
            ("capacitacion:curso_recordatorios", [c], "get"),
            ("capacitacion:leccion_crear", [c], "get"),
            ("capacitacion:leccion_editar", [lec], "get"),
            ("capacitacion:leccion_eliminar", [lec], "post"),
            ("capacitacion:evaluacion_editar", [c], "get"),
            ("capacitacion:pregunta_crear", [c], "get"),
            ("capacitacion:pregunta_editar", [p], "get"),
            ("capacitacion:pregunta_eliminar", [p], "post"),
            ("capacitacion:subir_imagen", [], "post"),
        ]

    def test_colaborador_recibe_403(self):
        self.client.force_login(self.colaborador)
        for nombre, args, metodo in self.vistas():
            with self.subTest(vista=nombre):
                r = getattr(self.client, metodo)(reverse(nombre, args=args))
                self.assertEqual(r.status_code, 403)

    def test_admin_accede(self):
        self.client.force_login(self.admin)
        for nombre, args, metodo in self.vistas():
            if metodo == "get":
                with self.subTest(vista=nombre):
                    self.assertEqual(self.client.get(reverse(nombre, args=args)).status_code, 200)


class VisibilidadTests(TestCase):
    """RF-09: solo los cursos PUBLICADOS (y asignados) son visibles para el Colaborador."""

    def setUp(self):
        self.colaborador = crear_usuario()
        self.client.force_login(self.colaborador)

    def test_curso_publicado_y_asignado_es_visible(self):
        curso = crear_curso()
        servicios.asignar_curso(curso, self.colaborador)
        r = self.client.get(reverse("capacitacion:curso_ver", args=[curso.pk]))
        self.assertEqual(r.status_code, 200)

    def test_curso_en_borrador_no_es_visible_aunque_este_asignado(self):
        curso = crear_curso(estado=Curso.Estado.BORRADOR)
        servicios.asignar_curso(curso, self.colaborador)
        r = self.client.get(reverse("capacitacion:curso_ver", args=[curso.pk]))
        self.assertEqual(r.status_code, 404)

    def test_curso_archivado_no_es_visible(self):
        curso = crear_curso(estado=Curso.Estado.ARCHIVADO)
        servicios.asignar_curso(curso, self.colaborador)
        r = self.client.get(reverse("capacitacion:curso_ver", args=[curso.pk]))
        self.assertEqual(r.status_code, 404)

    def test_curso_no_asignado_no_es_visible(self):
        curso = crear_curso()
        r = self.client.get(reverse("capacitacion:curso_ver", args=[curso.pk]))
        self.assertEqual(r.status_code, 404)

    def test_admin_ve_vista_previa_de_borrador(self):
        self.client.force_login(crear_admin())
        curso = crear_curso(estado=Curso.Estado.BORRADOR)
        r = self.client.get(reverse("capacitacion:curso_ver", args=[curso.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["vista_previa"])
        r = self.client.post(
            reverse("capacitacion:leccion_completar", args=[curso.pk, curso.lecciones.first().pk])
        )
        self.assertFalse(Asignacion.objects.exists())


class FlujoColaboradorTests(TestCase):
    """Recorrido completo: lecciones → evaluación → resultado (RF-11 a RF-13)."""

    def setUp(self):
        self.colaborador = crear_usuario()
        self.client.force_login(self.colaborador)
        self.curso = crear_curso(lecciones=2)
        self.evaluacion = crear_evaluacion(self.curso, preguntas=2, nota_minima=100)
        self.asignacion, _ = servicios.asignar_curso(self.curso, self.colaborador)

    def _post_evaluacion(self, correctas):
        datos = {f"pregunta_{p}": o for p, o in respuestas(self.evaluacion, correctas).items()}
        return self.client.post(reverse("capacitacion:evaluacion", args=[self.curso.pk]), datos)

    def test_completar_lecciones_desde_la_vista(self):
        primera, segunda = self.curso.lecciones.all()
        r = self.client.post(
            reverse("capacitacion:leccion_completar", args=[self.curso.pk, primera.pk])
        )
        self.assertRedirects(
            r, f"{reverse('capacitacion:curso_ver', args=[self.curso.pk])}?leccion={segunda.pk}"
        )
        self.assertEqual(self.asignacion.porcentaje_avance, 50)

    def test_evaluacion_bloqueada_hasta_completar_lecciones(self):
        r = self.client.get(reverse("capacitacion:evaluacion", args=[self.curso.pk]))
        self.assertContains(r, "Debe completar todas las lecciones")
        self._post_evaluacion(2)
        self.assertFalse(Intento.objects.exists())

    def test_aprobar_desde_la_vista(self):
        completar_todo(self.asignacion)
        r = self._post_evaluacion(2)
        intento = Intento.objects.get()
        self.assertRedirects(
            r, reverse("capacitacion:resultado", args=[self.curso.pk, intento.pk])
        )
        self.assertEqual(intento.nota, 100)
        self.asignacion.refresh_from_db()
        self.assertTrue(self.asignacion.completada)

    def test_respuestas_incompletas_no_cuentan_como_intento(self):
        completar_todo(self.asignacion)
        pregunta = self.evaluacion.preguntas.first()
        opcion = pregunta.opciones.first()
        r = self.client.post(
            reverse("capacitacion:evaluacion", args=[self.curso.pk]),
            {f"pregunta_{pregunta.pk}": opcion.pk},
        )
        self.assertContains(r, "Responda todas las preguntas")
        self.assertFalse(Intento.objects.exists())

    def test_opcion_de_otra_pregunta_es_ignorada(self):
        completar_todo(self.asignacion)
        p1, p2 = self.evaluacion.preguntas.all()
        correcta_p1 = p1.opciones.get(es_correcta=True)
        r = self.client.post(
            reverse("capacitacion:evaluacion", args=[self.curso.pk]),
            {f"pregunta_{p1.pk}": correcta_p1.pk, f"pregunta_{p2.pk}": correcta_p1.pk},
        )
        self.assertContains(r, "Responda todas las preguntas")

    def test_rf30_no_puede_ver_resultado_de_otro_usuario(self):
        otro = crear_usuario("otro@curex.net.ve")
        asignacion_otro, _ = servicios.asignar_curso(self.curso, otro)
        completar_todo(asignacion_otro)
        intento = servicios.presentar_evaluacion(asignacion_otro, respuestas(self.evaluacion, 2))
        r = self.client.get(reverse("capacitacion:resultado", args=[self.curso.pk, intento.pk]))
        self.assertEqual(r.status_code, 404)

    def test_mi_panel_muestra_solo_mis_cursos(self):
        otro_curso = crear_curso("Curso ajeno")
        servicios.asignar_curso(otro_curso, crear_usuario("otro@curex.net.ve"))
        r = self.client.get(reverse("panel:mi_panel"))
        self.assertContains(r, self.curso.titulo)
        self.assertNotContains(r, "Curso ajeno")

    def test_rf14_certificado_proximamente(self):
        r = self.client.get(reverse("capacitacion:certificado", args=[self.curso.pk]))
        self.assertContains(r, "Próximamente")


class GestionCursosTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()
        self.client.force_login(self.admin)

    def test_crear_curso_queda_en_bitacora(self):
        r = self.client.post(
            reverse("capacitacion:curso_crear"),
            {"titulo": "Nuevo", "descripcion": "", "estado": Curso.Estado.BORRADOR},
        )
        curso = Curso.objects.get(titulo="Nuevo")
        self.assertRedirects(r, reverse("capacitacion:curso_detalle_admin", args=[curso.pk]))
        self.assertEqual(curso.creado_por, self.admin)
        self.assertTrue(Bitacora.objects.filter(accion="CREAR_CURSO").exists())

    def test_no_se_publica_un_curso_sin_lecciones(self):
        r = self.client.post(
            reverse("capacitacion:curso_crear"),
            {"titulo": "Vacío", "estado": Curso.Estado.PUBLICADO},
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Curso.objects.exists())

    def test_crear_leccion_sanea_y_registra(self):
        curso = crear_curso(lecciones=0, estado=Curso.Estado.BORRADOR)
        self.client.post(
            reverse("capacitacion:leccion_crear", args=[curso.pk]),
            {"orden": 1, "titulo": "Intro", "contenido_html": "<p>Hola</p><script>x</script>"},
        )
        self.assertEqual(curso.lecciones.get().contenido_html, "<p>Hola</p>")
        self.assertTrue(Bitacora.objects.filter(accion="CREAR_LECCION").exists())

    def test_eliminar_leccion_registra_bitacora(self):
        curso = crear_curso(lecciones=2)
        leccion = curso.lecciones.first()
        self.client.post(reverse("capacitacion:leccion_eliminar", args=[leccion.pk]))
        self.assertEqual(curso.lecciones.count(), 1)
        self.assertTrue(Bitacora.objects.filter(accion="ELIMINAR_LECCION").exists())

    def _datos_pregunta(self, correctas):
        datos = {
            "orden": 1,
            "enunciado": "¿Qué hacer ante un adjunto inesperado?",
            "opciones-TOTAL_FORMS": 4,
            "opciones-INITIAL_FORMS": 0,
            "opciones-MIN_NUM_FORMS": 0,
            "opciones-MAX_NUM_FORMS": 6,
        }
        for i, texto in enumerate(["Abrirlo", "Reportarlo", "Reenviarlo"]):
            datos[f"opciones-{i}-texto"] = texto
            if i in correctas:
                datos[f"opciones-{i}-es_correcta"] = "on"
        return datos

    def test_pregunta_exige_exactamente_una_correcta(self):
        curso = crear_curso()
        crear_evaluacion(curso, preguntas=0)
        url = reverse("capacitacion:pregunta_crear", args=[curso.pk])
        r = self.client.post(url, self._datos_pregunta(correctas=[0, 1]))
        self.assertContains(r, "exactamente una opción")
        r = self.client.post(url, self._datos_pregunta(correctas=[1]))
        self.assertRedirects(r, reverse("capacitacion:curso_detalle_admin", args=[curso.pk]))
        pregunta = Pregunta.objects.get()
        self.assertEqual(pregunta.opciones.count(), 3)
        self.assertEqual(pregunta.opciones.get(es_correcta=True).texto, "Reportarlo")

    def test_rf10_asignar_por_departamento_desde_la_vista(self):
        curso = crear_curso()
        depto = crear_departamento()
        crear_usuario("a@curex.net.ve", departamento=depto)
        crear_usuario("b@curex.net.ve", departamento=depto)
        url = reverse("capacitacion:curso_asignar", args=[curso.pk])
        fecha = (timezone.localdate() + timedelta(days=15)).isoformat()
        self.client.post(url, {"departamentos": [depto.pk], "fecha_limite": fecha})
        self.client.post(url, {"departamentos": [depto.pk], "fecha_limite": fecha})
        self.assertEqual(Asignacion.objects.filter(curso=curso).count(), 2)
        self.assertEqual(Bitacora.objects.filter(accion="ASIGNAR_CURSO").count(), 2)

    def test_no_asigna_cursos_no_publicados(self):
        curso = crear_curso(estado=Curso.Estado.BORRADOR)
        r = self.client.get(reverse("capacitacion:curso_asignar", args=[curso.pk]))
        self.assertRedirects(r, reverse("capacitacion:curso_detalle_admin", args=[curso.pk]))

    def test_fecha_limite_no_puede_ser_pasada(self):
        curso = crear_curso()
        r = self.client.post(
            reverse("capacitacion:curso_asignar", args=[curso.pk]),
            {"usuarios": [crear_usuario().pk], "fecha_limite": "2020-01-01"},
        )
        self.assertIn("fecha_limite", r.context["form"].errors)

    def test_rf15_recordatorios_proximamente(self):
        curso = crear_curso()
        r = self.client.get(reverse("capacitacion:curso_recordatorios", args=[curso.pk]))
        self.assertContains(r, "Próximamente")

    def test_vista_previa_de_evaluacion_para_admin(self):
        curso = crear_curso()
        crear_evaluacion(curso)
        r = self.client.get(reverse("capacitacion:evaluacion", args=[curso.pk]))
        self.assertTrue(r.context["vista_previa"])


class SubirImagenTests(TestCase):
    def setUp(self):
        self.client.force_login(crear_admin())
        self.url = reverse("capacitacion:subir_imagen")

    def test_rechaza_archivos_que_no_son_imagenes(self):
        archivo = SimpleUploadedFile("x.png", b"<script>", content_type="image/png")
        r = self.client.post(self.url, {"imagen": archivo})
        self.assertEqual(r.status_code, 400)

    def test_sin_configuracion_responde_503(self):
        archivo = SimpleUploadedFile("x.png", PNG, content_type="image/png")
        r = self.client.post(self.url, {"imagen": archivo})
        self.assertEqual(r.status_code, 503)

    @override_settings(SUPABASE_URL="https://demo.supabase.co", SUPABASE_SERVICE_KEY="clave")
    def test_sube_a_supabase_y_devuelve_url_publica(self):
        archivo = SimpleUploadedFile("foto.png", PNG, content_type="image/png")
        with mock.patch("phishguard.almacenamiento.requests.post") as post:
            post.return_value.status_code = 200
            r = self.client.post(self.url, {"imagen": archivo})
        self.assertEqual(r.status_code, 200)
        url = r.json()["url"]
        self.assertTrue(url.startswith("https://demo.supabase.co/storage/v1/object/public/"))
        self.assertTrue(url.endswith(".png"))
        self.assertIn("/object/phishguard-publico/lecciones/", post.call_args.args[0])
