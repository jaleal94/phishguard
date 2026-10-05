"""Pruebas de control de acceso por rol (RF-04 y RF-05) y de navegación."""

from django.test import TestCase
from django.urls import reverse

from .utilidades import crear_admin, crear_departamento, crear_usuario


class PermisosAdministrativosTests(TestCase):
    """Cada vista administrativa responde 403 al Colaborador."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_admin()
        cls.colaborador = crear_usuario()
        cls.departamento = crear_departamento()

    def vistas_admin(self):
        """(nombre de ruta, argumentos, método) de todas las vistas administrativas."""
        u, d = self.colaborador.pk, self.departamento.pk
        return [
            ("panel:admin_panel", [], "get"),
            ("panel:bitacora", [], "get"),
            ("usuarios:usuarios_lista", [], "get"),
            ("usuarios:usuario_crear", [], "get"),
            ("usuarios:usuarios_importar", [], "get"),
            ("usuarios:usuario_editar", [u], "get"),
            ("usuarios:usuario_desbloquear", [u], "post"),
            ("usuarios:departamentos_lista", [], "get"),
            ("usuarios:departamento_crear", [], "get"),
            ("usuarios:departamento_editar", [d], "get"),
            ("usuarios:departamento_eliminar", [d], "post"),
            ("capacitacion:cursos_admin", [], "get"),
            ("simulaciones:plantillas", [], "get"),
            ("simulaciones:campanas", [], "get"),
            ("reportes:bandeja", [], "get"),
        ]

    def test_colaborador_recibe_403_en_cada_vista_admin(self):
        self.client.force_login(self.colaborador)
        for nombre, args, metodo in self.vistas_admin():
            with self.subTest(vista=nombre):
                r = getattr(self.client, metodo)(reverse(nombre, args=args))
                self.assertEqual(r.status_code, 403)

    def test_anonimo_es_redirigido_al_login(self):
        for nombre, args, metodo in self.vistas_admin():
            with self.subTest(vista=nombre):
                r = getattr(self.client, metodo)(reverse(nombre, args=args))
                self.assertEqual(r.status_code, 302)
                self.assertIn(reverse("usuarios:login"), r.url)

    def test_admin_accede_a_cada_vista_get(self):
        self.client.force_login(self.admin)
        for nombre, args, metodo in self.vistas_admin():
            if metodo != "get":
                continue
            with self.subTest(vista=nombre):
                r = self.client.get(reverse(nombre, args=args))
                self.assertEqual(r.status_code, 200)


class NavegacionTests(TestCase):
    """Ninguna opción del menú responde 404 (requisito del prototipo)."""

    def test_menu_colaborador_sin_enlaces_rotos(self):
        self.client.force_login(crear_usuario())
        for nombre in ["inicio", "panel:mi_panel", "reportes:reportar", "usuarios:perfil"]:
            with self.subTest(vista=nombre):
                r = self.client.get(reverse(nombre), follow=True)
                self.assertEqual(r.status_code, 200)

    def test_menu_colaborador_no_muestra_opciones_admin(self):
        self.client.force_login(crear_usuario())
        r = self.client.get(reverse("panel:mi_panel"))
        self.assertNotContains(r, reverse("usuarios:usuarios_lista"))
        self.assertNotContains(r, reverse("panel:bitacora"))

    def test_menu_admin_muestra_opciones_admin(self):
        self.client.force_login(crear_admin())
        r = self.client.get(reverse("panel:admin_panel"))
        self.assertContains(r, reverse("usuarios:usuarios_lista"))
        self.assertContains(r, reverse("panel:bitacora"))

    def test_inicio_anonimo_redirige_al_login(self):
        r = self.client.get(reverse("inicio"))
        self.assertRedirects(r, f"{reverse('usuarios:login')}?next=/")

    def test_pagina_404_en_espanol(self):
        r = self.client.get("/no-existe/")
        self.assertEqual(r.status_code, 404)
