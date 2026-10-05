"""Registro en el panel /admin/ nativo (solo superusuarios técnicos)."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Departamento, Usuario


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "activo"]
    search_fields = ["nombre"]


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "nombre_completo", "rol", "departamento", "is_active"]
    list_filter = ["rol", "departamento", "is_active"]
    search_fields = ["email", "nombre_completo"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Datos", {"fields": ["nombre_completo", "rol", "departamento"]}),
        ("Seguridad", {"fields": ["intentos_fallidos", "bloqueado_hasta"]}),
        ("Permisos", {"fields": ["is_active", "is_staff", "is_superuser"]}),
        ("Fechas", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["email", "nombre_completo", "rol", "password1", "password2"],
            },
        )
    ]
