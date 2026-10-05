"""Pruebas de autenticación: RF-02, RF-03, RF-06, RF-07 y RF-08."""

import re
import time
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from panel.models import Bitacora
from usuarios.forms import MENSAJE_LOGIN_GENERICO
from usuarios.middleware import CLAVE_ACTIVIDAD

from .utilidades import CLAVE, crear_admin, crear_usuario

URL_LOGIN = reverse("usuarios:login")


class LoginTests(TestCase):
    """RF-02: inicio de sesión."""

    def setUp(self):
        self.colaborador = crear_usuario()
        self.admin = crear_admin()

    def test_colaborador_llega_a_su_panel(self):
        r = self.client.post(
            URL_LOGIN, {"email": self.colaborador.email, "password": CLAVE}, follow=True
        )
        self.assertRedirects(r, reverse("panel:mi_panel"))

    def test_admin_llega_al_panel_de_indicadores(self):
        r = self.client.post(URL_LOGIN, {"email": self.admin.email, "password": CLAVE}, follow=True)
        self.assertRedirects(r, reverse("panel:admin_panel"))

    def test_login_no_distingue_mayusculas_en_correo(self):
        r = self.client.post(URL_LOGIN, {"email": "COLABORADOR@curex.net.ve", "password": CLAVE})
        self.assertRedirects(r, reverse("inicio"), fetch_redirect_response=False)

    def test_mensaje_generico_no_revela_si_el_correo_existe(self):
        r1 = self.client.post(URL_LOGIN, {"email": self.colaborador.email, "password": "mala"})
        r2 = self.client.post(URL_LOGIN, {"email": "noexiste@curex.net.ve", "password": "mala"})
        self.assertContains(r1, MENSAJE_LOGIN_GENERICO)
        self.assertContains(r2, MENSAJE_LOGIN_GENERICO)
        self.assertEqual(r1.context["form"].errors, r2.context["form"].errors)

    def test_usuario_inactivo_no_entra(self):
        self.colaborador.is_active = False
        self.colaborador.save()
        r = self.client.post(URL_LOGIN, {"email": self.colaborador.email, "password": CLAVE})
        self.assertContains(r, MENSAJE_LOGIN_GENERICO)

    def test_next_externo_es_ignorado(self):
        r = self.client.post(
            URL_LOGIN,
            {"email": self.colaborador.email, "password": CLAVE, "next": "https://malo.com/"},
        )
        self.assertRedirects(r, reverse("inicio"), fetch_redirect_response=False)

    def test_logout_cierra_sesion(self):
        self.client.force_login(self.colaborador)
        r = self.client.post(reverse("usuarios:logout"))
        self.assertRedirects(r, URL_LOGIN)
        r = self.client.get(reverse("panel:mi_panel"))
        self.assertEqual(r.status_code, 302)

    def test_login_queda_en_bitacora(self):
        self.client.post(URL_LOGIN, {"email": self.colaborador.email, "password": CLAVE})
        self.assertTrue(
            Bitacora.objects.filter(accion="INICIO_SESION", usuario=self.colaborador).exists()
        )


class BloqueoTests(TestCase):
    """RF-08: bloqueo tras 5 intentos fallidos."""

    def setUp(self):
        self.usuario = crear_usuario()

    def _fallar(self, veces):
        for _ in range(veces):
            self.client.post(URL_LOGIN, {"email": self.usuario.email, "password": "incorrecta"})

    def test_cuatro_fallos_no_bloquean(self):
        self._fallar(4)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.esta_bloqueado)
        self.assertEqual(self.usuario.intentos_fallidos, 4)

    def test_quinto_fallo_bloquea_15_minutos_y_registra_bitacora(self):
        self._fallar(5)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.esta_bloqueado)
        restante = self.usuario.bloqueado_hasta - timezone.now()
        self.assertTrue(timedelta(minutes=14) < restante <= timedelta(minutes=15))
        registro = Bitacora.objects.get(accion="BLOQUEO_CUENTA")
        self.assertEqual(registro.usuario, self.usuario)

    def test_cuenta_bloqueada_rechaza_contrasena_correcta(self):
        self._fallar(5)
        r = self.client.post(URL_LOGIN, {"email": self.usuario.email, "password": CLAVE})
        self.assertContains(r, MENSAJE_LOGIN_GENERICO)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_tras_15_minutos_puede_entrar(self):
        self._fallar(5)
        Usuario = type(self.usuario)
        Usuario.objects.filter(pk=self.usuario.pk).update(
            bloqueado_hasta=timezone.now() - timedelta(seconds=1)
        )
        r = self.client.post(URL_LOGIN, {"email": self.usuario.email, "password": CLAVE})
        self.assertEqual(r.status_code, 302)

    def test_login_exitoso_reinicia_contador(self):
        self._fallar(3)
        self.client.post(URL_LOGIN, {"email": self.usuario.email, "password": CLAVE})
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 0)


class RecuperacionTests(TestCase):
    """RF-03: recuperación de contraseña con enlace de 1 hora y un solo uso."""

    def setUp(self):
        self.usuario = crear_usuario()

    def _solicitar_enlace(self):
        self.client.post(reverse("usuarios:recuperar"), {"email": self.usuario.email})
        self.assertEqual(len(mail.outbox), 1)
        return re.search(r"https?://[^/]+(/recuperar/[^\s]+/)", mail.outbox[0].body).group(1)

    def test_correo_inexistente_muestra_misma_respuesta_sin_enviar(self):
        r = self.client.post(reverse("usuarios:recuperar"), {"email": "nadie@curex.net.ve"})
        self.assertRedirects(r, reverse("usuarios:recuperar_enviado"))
        self.assertEqual(len(mail.outbox), 0)

    def test_enlace_permite_cambiar_contrasena_una_sola_vez(self):
        enlace = self._solicitar_enlace()
        r = self.client.get(enlace, follow=True)
        self.assertTrue(r.context["validlink"])
        nueva = "OtraClave.Segura.99"
        r = self.client.post(
            r.redirect_chain[-1][0], {"new_password1": nueva, "new_password2": nueva}
        )
        self.assertRedirects(r, reverse("usuarios:recuperar_completado"))
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(nueva))
        # Segundo uso del mismo enlace: inválido.
        cliente = self.client_class()
        r = cliente.get(enlace, follow=True)
        self.assertFalse(r.context["validlink"])

    def test_enlace_expira_en_una_hora(self):
        self.assertEqual(settings.PASSWORD_RESET_TIMEOUT, 3600)
        enlace = self._solicitar_enlace()
        futuro = PasswordResetTokenGenerator()._now() + timedelta(minutes=61)
        with mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=futuro):
            r = self.client.get(enlace, follow=True)
        self.assertFalse(r.context["validlink"])


class CambioContrasenaTests(TestCase):
    """RF-06: cambio de contraseña con la contraseña actual y validadores."""

    def setUp(self):
        self.usuario = crear_usuario()
        self.client.force_login(self.usuario)
        self.url = reverse("usuarios:perfil")

    def _cambiar(self, actual, nueva):
        return self.client.post(
            self.url,
            {
                "accion": "clave",
                "old_password": actual,
                "new_password1": nueva,
                "new_password2": nueva,
            },
        )

    def test_exige_contrasena_actual(self):
        r = self._cambiar("incorrecta", "NuevaClave.Segura.1")
        self.assertEqual(r.status_code, 200)
        self.assertIn("old_password", r.context["form_clave"].errors)

    def test_minimo_10_caracteres(self):
        r = self._cambiar(CLAVE, "Ab.12345")
        self.assertIn("new_password2", r.context["form_clave"].errors)

    def test_cambio_correcto_mantiene_sesion(self):
        r = self._cambiar(CLAVE, "NuevaClave.Segura.1")
        self.assertRedirects(r, self.url)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("NuevaClave.Segura.1"))
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_editar_nombre_no_cambia_rol_ni_correo(self):
        self.client.post(
            self.url,
            {"accion": "perfil", "nombre_completo": "Nuevo Nombre", "rol": "ADMIN",
             "email": "otro@curex.net.ve"},
        )
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.nombre_completo, "Nuevo Nombre")
        self.assertFalse(self.usuario.es_admin)
        self.assertEqual(self.usuario.email, "colaborador@curex.net.ve")


class InactividadTests(TestCase):
    """RF-07: cierre de sesión tras 15 minutos de inactividad."""

    def setUp(self):
        self.usuario = crear_usuario()
        self.client.force_login(self.usuario)

    def _fijar_ultima_actividad(self, hace_segundos):
        sesion = self.client.session
        sesion[CLAVE_ACTIVIDAD] = int(time.time()) - hace_segundos
        sesion.save()

    def test_actividad_reciente_mantiene_sesion(self):
        self._fijar_ultima_actividad(14 * 60)
        r = self.client.get(reverse("panel:mi_panel"))
        self.assertEqual(r.status_code, 200)

    def test_mas_de_15_minutos_redirige_al_login(self):
        self._fijar_ultima_actividad(15 * 60 + 5)
        r = self.client.get(reverse("panel:mi_panel"))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(URL_LOGIN))
        self.assertNotIn("_auth_user_id", self.client.session)
