"""Pruebas de los modelos Usuario y Departamento."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from usuarios.models import Usuario

from .utilidades import crear_admin, crear_usuario


class UsuarioModeloTests(TestCase):
    def test_rf01_rechaza_dominio_externo_al_crear(self):
        with self.assertRaisesMessage(ValidationError, "@curex.net.ve"):
            Usuario.objects.create_user(
                email="alguien@gmail.com", password="x", nombre_completo="X"
            )

    def test_email_se_normaliza_en_minusculas(self):
        usuario = crear_usuario(email="Ana.Perez@CUREX.net.ve")
        self.assertEqual(usuario.email, "ana.perez@curex.net.ve")

    def test_contrasena_con_pbkdf2_sha256(self):
        usuario = crear_usuario()
        self.assertTrue(usuario.password.startswith("pbkdf2_sha256$"))

    def test_roles(self):
        self.assertTrue(crear_admin().es_admin)
        self.assertFalse(crear_usuario().es_admin)

    def test_superusuario_es_admin(self):
        su = Usuario.objects.create_superuser(
            email="root@curex.net.ve", password="x", nombre_completo="Root"
        )
        self.assertTrue(su.es_admin and su.is_staff and su.is_superuser)

    def test_esta_bloqueado(self):
        usuario = crear_usuario()
        self.assertFalse(usuario.esta_bloqueado)
        usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=5)
        self.assertTrue(usuario.esta_bloqueado)
        usuario.bloqueado_hasta = timezone.now() - timedelta(minutes=1)
        self.assertFalse(usuario.esta_bloqueado)

    def test_marcas_de_tiempo(self):
        usuario = crear_usuario()
        self.assertIsNotNone(usuario.creado_en)
        self.assertIsNotNone(usuario.actualizado_en)
