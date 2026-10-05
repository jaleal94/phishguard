"""Registro de la bitácora en el panel /admin/ nativo (solo lectura)."""

from django.contrib import admin

from .models import Bitacora


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = ["ocurrido_en", "accion", "usuario", "objeto", "ip"]
    list_filter = ["accion"]
    search_fields = ["objeto", "usuario__email"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
