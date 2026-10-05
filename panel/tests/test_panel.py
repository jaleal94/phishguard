"""Pruebas del panel de indicadores y la bitácora (RF-26 a RF-30)."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from capacitacion.models import Asignacion
from capacitacion.servicios import asignar_curso
from capacitacion.tests.utilidades import crear_curso
from panel import indicadores
from panel.models import Bitacora
from reportes.models import ReporteSospechoso
from simulaciones.models import Campana, Destinatario, EventoSimulacion, PlantillaCorreo
from usuarios.tests.utilidades import crear_admin, crear_departamento, crear_usuario

CLIC = EventoSimulacion.Tipo.CLIC
REPORTE = EventoSimulacion.Tipo.REPORTE


class DatosCampanasMixin:
    """Dos campañas con 4 destinatarios enviados cada una, en dos departamentos."""

    def preparar_campanas(self):
        self.ventas = crear_departamento("Ventas")
        self.compras = crear_departamento("Compras")
        self.usuarios = [
            crear_usuario(f"u{i}@curex.net.ve", departamento=d)
            for i, d in enumerate([self.ventas, self.ventas, self.compras, self.compras])
        ]
        plantilla = PlantillaCorreo.objects.create(
            nombre="P", asunto="A", remitente_visible="r@x.com", cuerpo_html="<p>p</p>"
        )
        ahora = timezone.now()
        self.c1 = Campana.objects.create(
            nombre="Línea base", plantilla=plantilla, fecha_envio=ahora - timedelta(days=60),
            estado=Campana.Estado.FINALIZADA,
        )
        self.c2 = Campana.objects.create(
            nombre="Cierre", plantilla=plantilla, fecha_envio=ahora - timedelta(days=1),
            estado=Campana.Estado.FINALIZADA,
        )
        self.dest = {}
        for campana in (self.c1, self.c2):
            for usuario in self.usuarios:
                self.dest[(campana.pk, usuario.pk)] = Destinatario.objects.create(
                    campana=campana, usuario=usuario, enviado_en=ahora
                )
        # Campaña 1: 2 clics (u0 hace clic dos veces, u2) y 1 reporte (u1).
        self.evento(self.c1, 0, CLIC)
        self.evento(self.c1, 0, CLIC)
        self.evento(self.c1, 2, CLIC)
        self.evento(self.c1, 1, REPORTE)
        # Campaña 2: 1 clic (u2) y 2 reportes (u0, u1).
        self.evento(self.c2, 2, CLIC)
        self.evento(self.c2, 0, REPORTE)
        self.evento(self.c2, 1, REPORTE)
        # Un destinatario sin enviar no cuenta.
        pendiente = crear_usuario("pendiente@curex.net.ve", departamento=self.ventas)
        Destinatario.objects.create(campana=self.c2, usuario=pendiente)

    def evento(self, campana, indice_usuario, tipo):
        destinatario = self.dest[(campana.pk, self.usuarios[indice_usuario].pk)]
        EventoSimulacion.objects.create(destinatario=destinatario, tipo=tipo)


class IndicadoresCampanasTests(DatosCampanasMixin, TestCase):
    """RF-26: tasas de clics y de reporte, filtrables por departamento y campaña."""

    def setUp(self):
        self.preparar_campanas()

    def test_tasas_por_campana_en_orden_cronologico(self):
        filas = indicadores.indicadores_campanas()
        self.assertEqual([f["nombre"] for f in filas], ["Línea base", "Cierre"])
        base, cierre = filas
        self.assertEqual((base["enviados"], base["clics"], base["reportes"]), (4, 2, 1))
        self.assertEqual((base["tasa_clics"], base["tasa_reporte"]), (50.0, 25.0))
        self.assertEqual((cierre["enviados"], cierre["clics"], cierre["reportes"]), (4, 1, 2))
        self.assertEqual((cierre["tasa_clics"], cierre["tasa_reporte"]), (25.0, 50.0))

    def test_filtro_por_departamento(self):
        filas = indicadores.indicadores_campanas(departamento=self.ventas)
        base = filas[0]
        self.assertEqual((base["enviados"], base["clics"], base["reportes"]), (2, 1, 1))
        self.assertEqual(base["tasa_clics"], 50.0)

    def test_filtro_por_campana(self):
        filas = indicadores.indicadores_campanas(campana=self.c2)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["nombre"], "Cierre")

    def test_totales_y_variacion_respecto_de_la_linea_base(self):
        filas = indicadores.indicadores_campanas()
        totales = indicadores.totales_campanas(filas)
        self.assertEqual(totales["enviados"], 8)
        self.assertEqual(totales["tasa_clics"], 37.5)
        self.assertEqual(totales["tasa_reporte"], 37.5)
        self.assertEqual(indicadores.variacion_clics(filas), -50.0)

    def test_sin_campanas(self):
        self.assertEqual(indicadores.indicadores_campanas(departamento=crear_departamento("X")),
                         [])
        self.assertEqual(indicadores.totales_campanas([])["tasa_clics"], 0.0)
        self.assertIsNone(indicadores.variacion_clics([]))


class OtrosIndicadoresTests(TestCase):
    def test_cobertura_de_capacitacion_a_tiempo(self):
        curso = crear_curso()
        refuerzo = crear_curso("Refuerzo", es_refuerzo=True)
        hoy = timezone.localdate()
        a_tiempo, _ = asignar_curso(curso, crear_usuario("a@curex.net.ve"), fecha_limite=hoy)
        tarde, _ = asignar_curso(
            curso, crear_usuario("b@curex.net.ve"), fecha_limite=hoy - timedelta(days=5)
        )
        asignar_curso(curso, crear_usuario("c@curex.net.ve"), fecha_limite=hoy)
        asignar_curso(refuerzo, crear_usuario("d@curex.net.ve"))
        Asignacion.objects.filter(pk__in=[a_tiempo.pk, tarde.pk]).update(
            completada_en=timezone.now()
        )
        datos = indicadores.indicadores_capacitacion()
        self.assertEqual((datos["total"], datos["completadas"], datos["a_tiempo"]), (3, 2, 1))
        self.assertEqual(datos["cobertura"], 33.3)

    def test_trazabilidad_de_reportes(self):
        usuario = crear_usuario()
        for estado, atendido in [("PENDIENTE", None), ("FALSO_POSITIVO", timezone.now())]:
            ReporteSospechoso.objects.create(
                reportado_por=usuario, remitente="x", asunto="y",
                fecha_recepcion=timezone.now(), estado=estado, atendido_en=atendido,
            )
        datos = indicadores.indicadores_reportes()
        self.assertEqual((datos["total"], datos["pendientes"], datos["atendidos"]), (2, 1, 1))
        self.assertEqual(datos["porcentaje_atendidos"], 50.0)


class PanelAdminVistaTests(DatosCampanasMixin, TestCase):
    """RF-26, RF-27 y RF-28 en la vista del panel."""

    def setUp(self):
        self.client.force_login(crear_admin())
        self.url = reverse("panel:admin_panel")

    def test_panel_vacio_muestra_aviso_sin_grafico(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Sin datos de campañas")
        self.assertNotContains(r, "chart.umd.min.js")

    def test_rf27_grafico_de_lineas_con_datos_por_campana(self):
        self.preparar_campanas()
        r = self.client.get(self.url)
        self.assertContains(r, "chart.umd.min.js")
        self.assertContains(r, 'id="grafico-campanas"')
        self.assertEqual(r.context["grafico"]["etiquetas"], ["Línea base", "Cierre"])
        self.assertEqual(r.context["grafico"]["clics"], [50.0, 25.0])
        self.assertEqual(r.context["grafico"]["reportes"], [25.0, 50.0])

    def test_filtros_desde_la_url(self):
        self.preparar_campanas()
        r = self.client.get(self.url, {"departamento": self.ventas.pk, "campana": self.c1.pk})
        self.assertEqual(len(r.context["filas"]), 1)
        self.assertEqual(r.context["filas"][0]["enviados"], 2)

    def test_filtros_invalidos_se_ignoran(self):
        r = self.client.get(self.url, {"departamento": "abc", "campana": "999"})
        self.assertEqual(r.status_code, 200)

    def test_rf28_exportacion_proximamente(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Exportar CSV")
        self.assertContains(r, "Próximamente")

    def test_colaborador_recibe_403(self):
        self.client.force_login(crear_usuario())
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(reverse("panel:bitacora")).status_code, 403)


class Rf29BitacoraTests(TestCase):
    """RF-29: toda creación, edición o eliminación de un Administrador queda registrada."""

    def setUp(self):
        self.admin = crear_admin()
        self.client.force_login(self.admin)

    def test_cada_accion_administrativa_genera_registro(self):
        c = self.client
        depto = crear_departamento("Temporal")
        usuario = crear_usuario("editable@curex.net.ve")
        curso = crear_curso(lecciones=2)
        leccion = curso.lecciones.first()
        reporte = ReporteSospechoso.objects.create(
            reportado_por=usuario, remitente="x", asunto="y", fecha_recepcion=timezone.now()
        )
        acciones = [
            ("CREAR_DEPARTAMENTO", lambda: c.post(
                reverse("usuarios:departamento_crear"), {"nombre": "Nuevo", "activo": "on"})),
            ("EDITAR_DEPARTAMENTO", lambda: c.post(
                reverse("usuarios:departamento_editar", args=[depto.pk]),
                {"nombre": "Temporal 2", "activo": "on"})),
            ("ELIMINAR_DEPARTAMENTO", lambda: c.post(
                reverse("usuarios:departamento_eliminar", args=[depto.pk]))),
            ("CREAR_USUARIO", lambda: c.post(reverse("usuarios:usuario_crear"), {
                "email": "nuevo@curex.net.ve", "nombre_completo": "Nuevo", "rol": "COLABORADOR",
                "is_active": "on", "password1": "ClaveInicial.2026",
                "password2": "ClaveInicial.2026"})),
            ("EDITAR_USUARIO", lambda: c.post(
                reverse("usuarios:usuario_editar", args=[usuario.pk]), {
                    "email": usuario.email, "nombre_completo": "Editado",
                    "rol": "COLABORADOR", "is_active": "on"})),
            ("CREAR_CURSO", lambda: c.post(
                reverse("capacitacion:curso_crear"), {"titulo": "C2", "estado": "BORRADOR"})),
            ("EDITAR_CURSO", lambda: c.post(
                reverse("capacitacion:curso_editar", args=[curso.pk]),
                {"titulo": "Título nuevo", "estado": "PUBLICADO"})),
            ("CREAR_LECCION", lambda: c.post(
                reverse("capacitacion:leccion_crear", args=[curso.pk]),
                {"orden": 3, "titulo": "L3", "contenido_html": "<p>x</p>"})),
            ("EDITAR_LECCION", lambda: c.post(
                reverse("capacitacion:leccion_editar", args=[leccion.pk]),
                {"orden": 1, "titulo": "Cambiada", "contenido_html": "<p>x</p>"})),
            ("ELIMINAR_LECCION", lambda: c.post(
                reverse("capacitacion:leccion_eliminar", args=[leccion.pk]))),
            ("CREAR_EVALUACION", lambda: c.post(
                reverse("capacitacion:evaluacion_editar", args=[curso.pk]),
                {"nota_minima": 70, "intentos_maximos": 3})),
            ("ASIGNAR_CURSO", lambda: c.post(
                reverse("capacitacion:curso_asignar", args=[curso.pk]), {
                    "usuarios": [usuario.pk],
                    "fecha_limite": (timezone.localdate() + timedelta(days=5)).isoformat()})),
            ("CAMBIO_ESTADO_REPORTE", lambda: c.post(
                reverse("reportes:atender", args=[reporte.pk]),
                {"estado": "EN_REVISION", "comentario": ""})),
        ]
        for accion, ejecutar in acciones:
            with self.subTest(accion=accion):
                antes = Bitacora.objects.filter(accion=accion, usuario=self.admin).count()
                respuesta = ejecutar()
                self.assertEqual(respuesta.status_code, 302)
                despues = Bitacora.objects.filter(accion=accion, usuario=self.admin).count()
                self.assertEqual(despues, antes + 1)

    def test_bitacora_filtra_por_accion_y_usuario(self):
        Bitacora.objects.create(usuario=self.admin, accion="CREAR_CURSO", objeto="A")
        Bitacora.objects.create(usuario=crear_usuario(), accion="INICIO_SESION", objeto="B")
        r = self.client.get(reverse("panel:bitacora"), {"accion": "CREAR_CURSO"})
        self.assertEqual([x.objeto for x in r.context["pagina"]], ["A"])
        r = self.client.get(reverse("panel:bitacora"), {"usuario": "colaborador@"})
        self.assertEqual([x.objeto for x in r.context["pagina"]], ["B"])


class Rf30PrivacidadTests(TestCase):
    """RF-30: el Colaborador solo ve sus propios datos en su panel."""

    def test_mi_panel_solo_muestra_datos_propios(self):
        yo = crear_usuario("yo@curex.net.ve")
        otro = crear_usuario("otro@curex.net.ve")
        asignar_curso(crear_curso("Curso mío"), yo)
        asignar_curso(crear_curso("Curso ajeno"), otro)
        ReporteSospechoso.objects.create(
            reportado_por=otro, remitente="x", asunto="Reporte ajeno",
            fecha_recepcion=timezone.now(),
        )
        self.client.force_login(yo)
        r = self.client.get(reverse("panel:mi_panel"))
        self.assertContains(r, "Curso mío")
        self.assertNotContains(r, "Curso ajeno")
        self.assertNotContains(r, "Reporte ajeno")
        self.assertTrue(all(a.usuario_id == yo.pk for a in r.context["asignaciones"]))
        self.assertTrue(all(x.reportado_por_id == yo.pk for x in r.context["reportes"]))
