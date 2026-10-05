"""Modelos de la app reportes."""

from django.conf import settings
from django.db import models

from usuarios.models import ModeloBase


class ReporteSospechoso(ModeloBase):
    """Correo sospechoso reportado por un usuario (RF-22 a RF-25)."""

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_REVISION = "EN_REVISION", "En revisión"
        PHISHING_CONFIRMADO = "PHISHING_CONFIRMADO", "Phishing confirmado"
        FALSO_POSITIVO = "FALSO_POSITIVO", "Falso positivo"

    reportado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="reportado por",
        on_delete=models.CASCADE,
        related_name="reportes",
    )
    remitente = models.CharField(
        "remitente", max_length=254, help_text="Correo o nombre que aparece como remitente."
    )
    asunto = models.CharField("asunto", max_length=300)
    fecha_recepcion = models.DateTimeField("fecha de recepción")
    descripcion = models.TextField(
        "comentarios", blank=True, help_text="Opcional: qué le pareció sospechoso."
    )
    adjunto_url = models.CharField(
        "adjunto", max_length=300, blank=True, help_text="Ruta del archivo en Supabase Storage."
    )
    adjunto_nombre = models.CharField("nombre del adjunto", max_length=255, blank=True)
    estado = models.CharField(
        "estado", max_length=20, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    comentario_admin = models.TextField("comentario del Administrador", blank=True)
    atendido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="atendido por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes_atendidos",
    )
    atendido_en = models.DateTimeField("atendido en", null=True, blank=True)
    destinatario_sim = models.ForeignKey(
        "simulaciones.Destinatario",
        verbose_name="destinatario de simulación",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes",
    )

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "reporte de correo sospechoso"
        verbose_name_plural = "reportes de correos sospechosos"

    def __str__(self):
        return f"{self.asunto} ({self.get_estado_display()})"

    @property
    def es_simulacion(self):
        """Indica si el reporte corresponde a un correo de una campaña de simulación."""
        return self.destinatario_sim_id is not None
