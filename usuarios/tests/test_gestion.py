"""Pruebas de gestión de usuarios y departamentos (RF-01 y bitácora)."""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from panel.models import Bitacora
from usuarios.models import Departamento, Usuario

from .utilidades import crear_admin, crear_departamento, crear_usuario


class GestionUsuariosTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()
        self.departamento = crear_departamento()
        self.client.force_login(self.admin)

    def _datos(self, **extra):
        datos = {
            "email": "nuevo@curex.net.ve",
            "nombre_completo": "Nuevo Usuario",
            "rol": Usuario.Rol.COLABORADOR,
            "departamento": self.departamento.pk,
            "is_active": "on",
            "password1": "ClaveInicial.2026",
            "password2": "ClaveInicial.2026",
        }
        datos.update(extra)
        return datos

    def test_rf01_rechaza_correo_fuera_del_dominio(self):
        r = self.client.post(reverse("usuarios:usuario_crear"), self._datos(email="x@gmail.com"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Solo se permiten correos del dominio @curex.net.ve.")
        self.assertFalse(Usuario.objects.filter(email="x@gmail.com").exists())

    def test_crear_usuario_registra_bitacora(self):
        r = self.client.post(reverse("usuarios:usuario_crear"), self._datos())
        self.assertRedirects(r, reverse("usuarios:usuarios_lista"))
        nuevo = Usuario.objects.get(email="nuevo@curex.net.ve")
        self.assertTrue(nuevo.check_password("ClaveInicial.2026"))
        self.assertTrue(
            Bitacora.objects.filter(accion="CREAR_USUARIO", usuario=self.admin).exists()
        )

    def test_correo_duplicado_sin_distinguir_mayusculas(self):
        crear_usuario(email="repetido@curex.net.ve")
        r = self.client.post(
            reverse("usuarios:usuario_crear"), self._datos(email="REPETIDO@curex.net.ve")
        )
        self.assertContains(r, "Ya existe un usuario con este correo.")

    def test_contrasena_inicial_debe_cumplir_validadores(self):
        r = self.client.post(
            reverse("usuarios:usuario_crear"), self._datos(password1="corta", password2="corta")
        )
        self.assertIn("password1", r.context["form"].errors)

    def test_editar_usuario_registra_cambios(self):
        usuario = crear_usuario()
        datos = {
            "email": usuario.email,
            "nombre_completo": "Nombre Editado",
            "rol": Usuario.Rol.COLABORADOR,
            "departamento": self.departamento.pk,
            "is_active": "on",
        }
        r = self.client.post(reverse("usuarios:usuario_editar", args=[usuario.pk]), datos)
        self.assertRedirects(r, reverse("usuarios:usuarios_lista"))
        registro = Bitacora.objects.get(accion="EDITAR_USUARIO")
        self.assertIn("nombre_completo", registro.detalle)

    def test_admin_no_puede_quitarse_su_rol(self):
        datos = {
            "email": self.admin.email,
            "nombre_completo": self.admin.nombre_completo,
            "rol": Usuario.Rol.COLABORADOR,
            "is_active": "on",
        }
        r = self.client.post(reverse("usuarios:usuario_editar", args=[self.admin.pk]), datos)
        self.assertEqual(r.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.es_admin)

    def test_desbloquear_usuario(self):
        usuario = crear_usuario(bloqueado_hasta=timezone.now() + timedelta(minutes=10))
        self.client.post(reverse("usuarios:usuario_desbloquear", args=[usuario.pk]))
        usuario.refresh_from_db()
        self.assertFalse(usuario.esta_bloqueado)
        self.assertTrue(Bitacora.objects.filter(accion="DESBLOQUEAR_USUARIO").exists())

    def test_carga_csv_muestra_proximamente(self):
        r = self.client.get(reverse("usuarios:usuarios_importar"))
        self.assertContains(r, "Próximamente")

    def test_filtro_de_busqueda(self):
        crear_usuario(email="buscado@curex.net.ve", nombre_completo="Persona Buscada")
        r = self.client.get(reverse("usuarios:usuarios_lista"), {"q": "buscada"})
        emails = [u.email for u in r.context["pagina"]]
        self.assertEqual(emails, ["buscado@curex.net.ve"])


class GestionDepartamentosTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()
        self.client.force_login(self.admin)

    def test_crear_departamento_registra_bitacora(self):
        r = self.client.post(
            reverse("usuarios:departamento_crear"), {"nombre": "Ventas", "activo": "on"}
        )
        self.assertRedirects(r, reverse("usuarios:departamentos_lista"))
        self.assertTrue(Departamento.objects.filter(nombre="Ventas").exists())
        self.assertTrue(Bitacora.objects.filter(accion="CREAR_DEPARTAMENTO").exists())

    def test_no_elimina_departamento_con_usuarios(self):
        departamento = crear_departamento()
        crear_usuario(departamento=departamento)
        self.client.post(reverse("usuarios:departamento_eliminar", args=[departamento.pk]))
        self.assertTrue(Departamento.objects.filter(pk=departamento.pk).exists())

    def test_elimina_departamento_vacio(self):
        departamento = crear_departamento("Temporal")
        self.client.post(reverse("usuarios:departamento_eliminar", args=[departamento.pk]))
        self.assertFalse(Departamento.objects.filter(pk=departamento.pk).exists())
        self.assertTrue(Bitacora.objects.filter(accion="ELIMINAR_DEPARTAMENTO").exists())

    def test_eliminar_exige_post(self):
        departamento = crear_departamento("Temporal")
        r = self.client.get(reverse("usuarios:departamento_eliminar", args=[departamento.pk]))
        self.assertEqual(r.status_code, 405)


class SeedDemoTests(TestCase):
    def test_seed_demo_crea_credenciales_y_es_idempotente(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())
        admin = Usuario.objects.get(email="admin.demo@curex.net.ve")
        colaborador = Usuario.objects.get(email="colaborador.demo@curex.net.ve")
        self.assertTrue(admin.es_admin)
        self.assertFalse(colaborador.es_admin)
        self.assertEqual(Usuario.objects.count(), 12)
