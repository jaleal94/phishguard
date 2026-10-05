"""Pruebas de saneamiento, asignaciones, avance y calificación (RF-09 a RF-13)."""

from decimal import Decimal

from django.test import TestCase

from capacitacion import servicios
from capacitacion.models import Asignacion, Intento, Leccion
from capacitacion.saneamiento import sanear_html
from usuarios.tests.utilidades import crear_departamento, crear_usuario

from .utilidades import completar_todo, crear_curso, crear_evaluacion, respuestas


class SaneamientoTests(TestCase):
    """RF-09: el HTML de Quill se sanea antes de guardarse."""

    def test_elimina_scripts_eventos_y_urls_peligrosas(self):
        html = (
            '<p onclick="robar()">Hola<script>alert(1)</script></p>'
            '<a href="javascript:alert(1)">x</a><img src="x" onerror="alert(1)">'
            '<iframe src="https://malo.com"></iframe>'
        )
        limpio = sanear_html(html)
        for peligroso in ("script", "onclick", "javascript:", "onerror", "iframe"):
            self.assertNotIn(peligroso, limpio)
        self.assertIn("Hola", limpio)

    def test_conserva_formato_de_quill(self):
        html = '<h2>Título</h2><p><strong>a</strong> <em>b</em></p><ul><li>uno</li></ul>'
        self.assertEqual(sanear_html(html), html)

    def test_enlaces_externos_llevan_rel_seguro(self):
        limpio = sanear_html('<a href="https://curex.net.ve" target="_blank">ok</a>')
        self.assertIn('rel="noopener noreferrer"', limpio)

    def test_leccion_se_sanea_al_guardar(self):
        curso = crear_curso(lecciones=0)
        leccion = Leccion.objects.create(
            curso=curso, titulo="L", contenido_html="<p>ok</p><script>x()</script>"
        )
        leccion.refresh_from_db()
        self.assertEqual(leccion.contenido_html, "<p>ok</p>")


class AsignacionTests(TestCase):
    def setUp(self):
        self.curso = crear_curso()
        self.depto = crear_departamento()

    def test_rf10_asigna_a_cada_usuario_activo_del_departamento_sin_duplicados(self):
        u1 = crear_usuario("a@curex.net.ve", departamento=self.depto)
        u2 = crear_usuario("b@curex.net.ve", departamento=self.depto)
        crear_usuario("inactivo@curex.net.ve", departamento=self.depto, is_active=False)
        crear_usuario("otro@curex.net.ve")
        self.assertEqual(servicios.asignar_a_departamento(self.curso, self.depto), 2)
        self.assertEqual(servicios.asignar_a_departamento(self.curso, self.depto), 0)
        asignados = set(Asignacion.objects.values_list("usuario_id", flat=True))
        self.assertEqual(asignados, {u1.pk, u2.pk})

    def test_contrato_asignar_curso_no_duplica_y_respeta_origen(self):
        usuario = crear_usuario()
        a1, creada1 = servicios.asignar_curso(
            self.curso, usuario, origen=Asignacion.Origen.SIMULACION
        )
        a2, creada2 = servicios.asignar_curso(self.curso, usuario)
        self.assertTrue(creada1)
        self.assertFalse(creada2)
        self.assertEqual(a1.pk, a2.pk)
        self.assertEqual(a2.origen, Asignacion.Origen.SIMULACION)


class AvanceTests(TestCase):
    """RF-11: avance = lecciones completadas / lecciones totales."""

    def setUp(self):
        self.curso = crear_curso(lecciones=3)
        self.asignacion, _ = servicios.asignar_curso(self.curso, crear_usuario())

    def test_porcentaje_de_avance(self):
        lecciones = list(self.curso.lecciones.all())
        self.assertEqual(self.asignacion.porcentaje_avance, 0)
        servicios.completar_leccion(self.asignacion, lecciones[0])
        self.assertEqual(self.asignacion.porcentaje_avance, 33)
        servicios.completar_leccion(self.asignacion, lecciones[1])
        self.assertEqual(self.asignacion.porcentaje_avance, 67)
        servicios.completar_leccion(self.asignacion, lecciones[1])  # repetida no suma
        self.assertEqual(self.asignacion.porcentaje_avance, 67)
        servicios.completar_leccion(self.asignacion, lecciones[2])
        self.assertEqual(self.asignacion.porcentaje_avance, 100)

    def test_curso_sin_evaluacion_se_completa_al_terminar_lecciones(self):
        completar_todo(self.asignacion)
        self.asignacion.refresh_from_db()
        self.assertTrue(self.asignacion.completada)

    def test_curso_con_evaluacion_no_se_completa_solo_con_lecciones(self):
        crear_evaluacion(self.curso)
        completar_todo(self.asignacion)
        self.asignacion.refresh_from_db()
        self.assertFalse(self.asignacion.completada)


class EvaluacionTests(TestCase):
    """RF-12 y RF-13: nota sobre 100, nota mínima e intentos máximos."""

    def setUp(self):
        self.curso = crear_curso()
        self.evaluacion = crear_evaluacion(self.curso, preguntas=3, nota_minima=70,
                                           intentos_maximos=2)
        self.asignacion, _ = servicios.asignar_curso(self.curso, crear_usuario())
        completar_todo(self.asignacion)

    def test_nota_sobre_100(self):
        self.assertEqual(servicios.calificar(self.evaluacion, respuestas(self.evaluacion, 3)),
                         Decimal("100.00"))
        self.assertEqual(servicios.calificar(self.evaluacion, respuestas(self.evaluacion, 2)),
                         Decimal("66.67"))
        self.assertEqual(servicios.calificar(self.evaluacion, {}), Decimal("0.00"))

    def test_bajo_la_nota_minima_no_aprueba(self):
        intento = servicios.presentar_evaluacion(
            self.asignacion, respuestas(self.evaluacion, 2)
        )
        self.assertFalse(intento.aprobado)
        self.asignacion.refresh_from_db()
        self.assertFalse(self.asignacion.completada)

    def test_aprobar_marca_la_asignacion_como_completada(self):
        intento = servicios.presentar_evaluacion(
            self.asignacion, respuestas(self.evaluacion, 3)
        )
        self.assertTrue(intento.aprobado)
        self.asignacion.refresh_from_db()
        self.assertTrue(self.asignacion.completada)

    def test_respeta_intentos_maximos(self):
        for _ in range(2):
            servicios.presentar_evaluacion(self.asignacion, respuestas(self.evaluacion, 0))
        with self.assertRaises(servicios.EvaluacionNoDisponible):
            servicios.presentar_evaluacion(self.asignacion, respuestas(self.evaluacion, 3))
        self.assertEqual(Intento.objects.count(), 2)

    def test_no_permite_nuevo_intento_tras_aprobar(self):
        servicios.presentar_evaluacion(self.asignacion, respuestas(self.evaluacion, 3))
        with self.assertRaises(servicios.EvaluacionNoDisponible):
            servicios.presentar_evaluacion(self.asignacion, respuestas(self.evaluacion, 3))

    def test_exige_completar_lecciones(self):
        self.asignacion.progresos.all().delete()
        with self.assertRaises(servicios.EvaluacionNoDisponible):
            servicios.presentar_evaluacion(self.asignacion, respuestas(self.evaluacion, 3))
