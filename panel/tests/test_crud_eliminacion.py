"""Pruebas de las operaciones Consultar/Eliminar y de los nuevos eventos de bitácora."""

import time
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from capacitacion.models import Asignacion, Curso
from capacitacion.servicios import asignar_curso, completar_leccion
from capacitacion.tests.utilidades import crear_curso, crear_evaluacion
from panel.models import Bitacora
from reportes.models import ReporteSospechoso
from usuarios.middleware import CLAVE_ACTIVIDAD
from usuarios.models import Usuario
from usuarios.tests.utilidades import CLAVE, crear_admin, crear_usuario


def crear_reporte(usuario, **campos):
    return ReporteSospechoso.objects.create(
        reportado_por=usuario, remitente="x@ejemplo.com", asunto="Asunto",
        fecha_recepcion=timezone.now(), **campos,
    )


class EliminacionTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()
        self.colaborador = crear_usuario()
        self.client.force_login(self.admin)

    def test_consultar_usuario(self):
        asignar_curso(crear_curso("Curso X"), self.colaborador)
        r = self.client.get(reverse("usuarios:usuario_detalle", args=[self.colaborador.pk]))
        self.assertContains(r, self.colaborador.email)
        self.assertContains(r, "Curso X")

    def test_eliminar_usuario_pide_confirmacion_y_registra(self):
        url = reverse("usuarios:usuario_eliminar", args=[self.colaborador.pk])
        r = self.client.get(url)
        self.assertContains(r, "También se eliminarán")
        self.assertTrue(Usuario.objects.filter(pk=self.colaborador.pk).exists())
        r = self.client.post(url)
        self.assertRedirects(r, reverse("usuarios:usuarios_lista"))
        self.assertFalse(Usuario.objects.filter(pk=self.colaborador.pk).exists())
        registro = Bitacora.objects.get(accion="ELIMINAR_USUARIO")
        self.assertEqual(registro.usuario, self.admin)
        self.assertEqual(registro.objeto, "colaborador@curex.net.ve")

    def test_admin_no_puede_eliminarse_a_si_mismo(self):
        self.client.post(reverse("usuarios:usuario_eliminar", args=[self.admin.pk]))
        self.assertTrue(Usuario.objects.filter(pk=self.admin.pk).exists())

    def test_eliminar_curso_con_sus_dependencias(self):
        curso = crear_curso()
        crear_evaluacion(curso)
        asignar_curso(curso, self.colaborador)
        r = self.client.get(reverse("capacitacion:curso_eliminar", args=[curso.pk]))
        self.assertContains(r, "3 lección(es)")
        self.client.post(reverse("capacitacion:curso_eliminar", args=[curso.pk]))
        self.assertFalse(Curso.objects.filter(pk=curso.pk).exists())
        self.assertFalse(Asignacion.objects.exists())
        self.assertTrue(Bitacora.objects.filter(accion="ELIMINAR_CURSO").exists())

    def test_eliminar_asignacion(self):
        curso = crear_curso()
        asignacion, _ = asignar_curso(curso, self.colaborador)
        completar_leccion(asignacion, curso.lecciones.first())
        r = self.client.post(reverse("capacitacion:asignacion_eliminar", args=[asignacion.pk]))
        self.assertRedirects(r, reverse("capacitacion:curso_detalle_admin", args=[curso.pk]))
        self.assertFalse(Asignacion.objects.exists())
        self.assertTrue(Bitacora.objects.filter(accion="ELIMINAR_ASIGNACION").exists())

    @override_settings(SUPABASE_URL="https://demo.supabase.co", SUPABASE_SERVICE_KEY="clave")
    def test_eliminar_reporte_borra_tambien_el_adjunto(self):
        reporte = crear_reporte(self.colaborador, adjunto_url="reportes/abc.pdf")
        with mock.patch("phishguard.almacenamiento.requests.delete") as borrar:
            borrar.return_value.status_code = 200
            r = self.client.post(reverse("reportes:reporte_eliminar", args=[reporte.pk]))
        self.assertRedirects(r, reverse("reportes:bandeja"))
        self.assertFalse(ReporteSospechoso.objects.exists())
        self.assertIn("/object/phishguard/reportes/abc.pdf", borrar.call_args.args[0])
        self.assertTrue(Bitacora.objects.filter(accion="ELIMINAR_REPORTE").exists())


class PermisosEliminacionTests(TestCase):
    """RF-04/05: las nuevas vistas administrativas responden 403 al Colaborador."""

    def test_colaborador_recibe_403_y_no_elimina_nada(self):
        colaborador = crear_usuario()
        otro = crear_usuario("otro@curex.net.ve")
        curso = crear_curso()
        asignacion, _ = asignar_curso(curso, otro)
        reporte = crear_reporte(otro)
        self.client.force_login(colaborador)
        vistas = [
            ("usuarios:usuario_detalle", otro.pk),
            ("usuarios:usuario_eliminar", otro.pk),
            ("capacitacion:curso_eliminar", curso.pk),
            ("capacitacion:asignacion_eliminar", asignacion.pk),
            ("reportes:reporte_eliminar", reporte.pk),
        ]
        for nombre, pk in vistas:
            for metodo in ("get", "post"):
                with self.subTest(vista=nombre, metodo=metodo):
                    r = getattr(self.client, metodo)(reverse(nombre, args=[pk]))
                    self.assertEqual(r.status_code, 403)
        self.assertTrue(Usuario.objects.filter(pk=otro.pk).exists())
        self.assertTrue(Curso.objects.filter(pk=curso.pk).exists())
        self.assertTrue(ReporteSospechoso.objects.filter(pk=reporte.pk).exists())


class BitacoraSesionTests(TestCase):
    """La bitácora registra intentos fallidos de inicio de sesión y cierres de sesión."""

    def setUp(self):
        self.usuario = crear_usuario()

    def test_intento_fallido_queda_registrado_con_motivo(self):
        url = reverse("usuarios:login")
        self.client.post(url, {"email": self.usuario.email, "password": "incorrecta"})
        self.client.post(url, {"email": "nadie@curex.net.ve", "password": "x"})
        motivos = list(
            Bitacora.objects.filter(accion="INICIO_SESION_FALLIDO")
            .order_by("ocurrido_en").values_list("objeto", "detalle__motivo")
        )
        self.assertEqual(motivos, [
            ("colaborador@curex.net.ve", "credenciales inválidas"),
            ("nadie@curex.net.ve", "correo no registrado"),
        ])
        # La contraseña escrita nunca se guarda.
        self.assertFalse(Bitacora.objects.filter(detalle__icontains="incorrecta").exists())

    def test_cierre_de_sesion_manual(self):
        datos = {"email": self.usuario.email, "password": CLAVE}
        self.client.post(reverse("usuarios:login"), datos)
        self.client.post(reverse("usuarios:logout"))
        self.assertTrue(
            Bitacora.objects.filter(accion="CIERRE_SESION", usuario=self.usuario).exists()
        )

    def test_cierre_de_sesion_por_inactividad(self):
        self.client.force_login(self.usuario)
        sesion = self.client.session
        sesion[CLAVE_ACTIVIDAD] = int(time.time()) - 16 * 60
        sesion.save()
        self.client.get(reverse("panel:mi_panel"))
        self.assertTrue(
            Bitacora.objects.filter(accion="CIERRE_SESION", usuario=self.usuario).exists()
        )
