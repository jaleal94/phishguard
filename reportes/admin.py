"""Registro de reportes en el panel /admin/ nativo (solo superusuarios técnicos)."""

from django.contrib import admin

from .models import ReporteSospechoso


@admin.register(ReporteSospechoso)
class ReporteSospechosoAdmin(admin.ModelAdmin):
    list_display = ["asunto", "reportado_por", "estado", "creado_en", "atendido_en"]
    list_filter = ["estado"]
    search_fields = ["asunto", "remitente", "reportado_por__email"]
    raw_id_fields = ["reportado_por", "atendido_por", "destinatario_sim"]
