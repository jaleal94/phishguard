"""Rutas de autenticación, perfil y gestión de usuarios."""

from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "usuarios"

urlpatterns = [
    path("login/", views.login_vista, name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # RF-03: recuperación de contraseña (enlace de un solo uso, válido 1 hora).
    path(
        "recuperar/",
        auth_views.PasswordResetView.as_view(
            template_name="usuarios/recuperar.html",
            email_template_name="usuarios/correo_recuperacion.txt",
            subject_template_name="usuarios/correo_recuperacion_asunto.txt",
            success_url=reverse_lazy("usuarios:recuperar_enviado"),
        ),
        name="recuperar",
    ),
    path(
        "recuperar/enviado/",
        auth_views.PasswordResetDoneView.as_view(template_name="usuarios/recuperar_enviado.html"),
        name="recuperar_enviado",
    ),
    path(
        "recuperar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="usuarios/recuperar_confirmar.html",
            success_url=reverse_lazy("usuarios:recuperar_completado"),
        ),
        name="recuperar_confirmar",
    ),
    path(
        "recuperar/completado/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="usuarios/recuperar_completado.html"
        ),
        name="recuperar_completado",
    ),
    path("perfil/", views.perfil, name="perfil"),
    # Gestión (Administrador)
    path("admin-panel/usuarios/", views.usuarios_lista, name="usuarios_lista"),
    path("admin-panel/usuarios/nuevo/", views.usuario_crear, name="usuario_crear"),
    path("admin-panel/usuarios/importar/", views.usuarios_importar, name="usuarios_importar"),
    path("admin-panel/usuarios/<int:pk>/editar/", views.usuario_editar, name="usuario_editar"),
    path(
        "admin-panel/usuarios/<int:pk>/desbloquear/",
        views.usuario_desbloquear,
        name="usuario_desbloquear",
    ),
    path("admin-panel/departamentos/", views.departamentos_lista, name="departamentos_lista"),
    path(
        "admin-panel/departamentos/nuevo/", views.departamento_crear, name="departamento_crear"
    ),
    path(
        "admin-panel/departamentos/<int:pk>/editar/",
        views.departamento_editar,
        name="departamento_editar",
    ),
    path(
        "admin-panel/departamentos/<int:pk>/eliminar/",
        views.departamento_eliminar,
        name="departamento_eliminar",
    ),
]
