"""Pruebas de bloqueo, cambio de estatus y cambio de clave de usuarios por el Administrador."""

from django.test import TestCase
from django.urls import reverse

from panel.models import Bitacora
from usuarios.forms import MENSAJE_LOGIN_GENERICO
from usuarios.middleware import MENSAJE_BLOQUEO

from .utilidades import CLAVE, crear_admin, crear_usuario

URL_LOGIN = reverse("usuarios:login")


def intentar_login(cliente, email, clave=CLAVE):
    return cliente.post(URL_LOGIN, {"email": email, "password": clave})


class BloqueoManualTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()
        self.usuario = crear_usuario()
        self.client.force_login(self.admin)

    def test_bloquear_impide_iniciar_sesion_y_queda_en_bitacora(self):
        r = self.client.post(reverse("usuarios:usuario_bloquear", args=[self.usuario.pk]))
        self.assertRedirects(r, reverse("usuarios:usuarios_lista"))
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.esta_bloqueado)
        self.assertTrue(self.usuario.bloqueo_por_administrador)
        registros = Bitacora.objects.filter(accion="BLOQUEAR_USUARIO", usuario=self.admin)
        self.assertTrue(registros.exists())
        r = intentar_login(self.client_class(), self.usuario.email)
        self.assertContains(r, MENSAJE_LOGIN_GENERICO)

    def test_bloquear_cierra_la_sesion_abierta_del_usuario(self):
        cliente = self.client_class()
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.get(reverse("panel:mi_panel")).status_code, 200)
        self.client.post(reverse("usuarios:usuario_bloquear", args=[self.usuario.pk]))
        r = cliente.get(reverse("panel:mi_panel"), follow=True)
        self.assertRedirects(r, URL_LOGIN)
        self.assertContains(r, MENSAJE_BLOQUEO)
        self.assertNotIn("_auth_user_id", cliente.session)

    def test_desbloquear_permite_volver_a_entrar(self):
        self.client.post(reverse("usuarios:usuario_bloquear", args=[self.usuario.pk]))
        r = self.client.post(
            reverse("usuarios:usuario_desbloquear", args=[self.usuario.pk]), {"volver": "detalle"}
        )
        self.assertRedirects(r, reverse("usuarios:usuario_detalle", args=[self.usuario.pk]))
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.esta_bloqueado)
        r = intentar_login(self.client_class(), self.usuario.email)
        self.assertEqual(r.status_code, 302)

    def test_admin_no_puede_bloquearse_a_si_mismo(self):
        self.client.post(reverse("usuarios:usuario_bloquear", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.esta_bloqueado)


class EstatusTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()
        self.usuario = crear_usuario()
        self.client.force_login(self.admin)
        self.url = reverse("usuarios:usuario_cambiar_estado", args=[self.usuario.pk])

    def test_desactivar_y_activar(self):
        self.client.post(self.url)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)
        self.assertTrue(Bitacora.objects.filter(accion="DESACTIVAR_USUARIO").exists())
        r = intentar_login(self.client_class(), self.usuario.email)
        self.assertContains(r, MENSAJE_LOGIN_GENERICO)
        self.client.post(self.url)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.is_active)
        self.assertTrue(Bitacora.objects.filter(accion="ACTIVAR_USUARIO").exists())

    def test_usuario_desactivado_pierde_su_sesion(self):
        cliente = self.client_class()
        cliente.force_login(self.usuario)
        self.client.post(self.url)
        r = cliente.get(reverse("panel:mi_panel"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(URL_LOGIN, r.url)

    def test_admin_no_puede_desactivarse_a_si_mismo(self):
        self.client.post(reverse("usuarios:usuario_cambiar_estado", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)


class CambioClaveTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()
        self.usuario = crear_usuario()
        self.client.force_login(self.admin)
        self.url = reverse("usuarios:usuario_cambiar_clave", args=[self.usuario.pk])

    def test_aplica_los_validadores_de_contrasena(self):
        r = self.client.post(self.url, {"new_password1": "corta", "new_password2": "corta"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("new_password2", r.context["form"].errors)
        distintas = {"new_password1": "Clave.Nueva.2026", "new_password2": "Otra.Distinta.2026"}
        r = self.client.post(self.url, distintas)
        self.assertIn("new_password2", r.context["form"].errors)

    def test_cambio_correcto_registra_y_cierra_sesiones_del_usuario(self):
        cliente = self.client_class()
        cliente.force_login(self.usuario)
        nueva = "Clave.Nueva.2026"
        r = self.client.post(self.url, {"new_password1": nueva, "new_password2": nueva})
        self.assertRedirects(r, reverse("usuarios:usuario_detalle", args=[self.usuario.pk]))
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(nueva))
        registro = Bitacora.objects.get(accion="CAMBIAR_CLAVE_USUARIO")
        self.assertEqual(registro.usuario, self.admin)
        self.assertNotIn(nueva, str(registro.detalle))
        self.assertEqual(cliente.get(reverse("panel:mi_panel")).status_code, 302)
        con_nueva = intentar_login(self.client_class(), self.usuario.email, nueva)
        self.assertEqual(con_nueva.status_code, 302)
        con_vieja = intentar_login(self.client_class(), self.usuario.email)
        self.assertContains(con_vieja, MENSAJE_LOGIN_GENERICO)

    def test_admin_cambia_su_propia_clave_sin_perder_la_sesion(self):
        nueva = "Mi.Clave.Nueva.2026"
        url = reverse("usuarios:usuario_cambiar_clave", args=[self.admin.pk])
        self.client.post(url, {"new_password1": nueva, "new_password2": nueva})
        self.assertEqual(self.client.get(reverse("usuarios:usuarios_lista")).status_code, 200)


class ProteccionRutasGestionTests(TestCase):
    """Las nuevas rutas de gestión responden 403 al Colaborador y piden login al anónimo."""

    def test_proteccion_de_rutas(self):
        otro = crear_usuario("otro@curex.net.ve")
        rutas = [
            ("usuarios:usuario_bloquear", "post"),
            ("usuarios:usuario_desbloquear", "post"),
            ("usuarios:usuario_cambiar_estado", "post"),
            ("usuarios:usuario_cambiar_clave", "get"),
            ("usuarios:usuario_cambiar_clave", "post"),
        ]
        for nombre, metodo in rutas:
            with self.subTest(ruta=nombre, metodo=metodo):
                r = getattr(self.client_class(), metodo)(reverse(nombre, args=[otro.pk]))
                self.assertEqual(r.status_code, 302)
                self.assertIn(URL_LOGIN, r.url)
        self.client.force_login(crear_usuario())
        for nombre, metodo in rutas:
            with self.subTest(ruta=nombre, metodo=metodo, rol="colaborador"):
                r = getattr(self.client, metodo)(reverse(nombre, args=[otro.pk]))
                self.assertEqual(r.status_code, 403)
        otro.refresh_from_db()
        self.assertTrue(otro.is_active)
        self.assertFalse(otro.esta_bloqueado)
