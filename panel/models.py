"""Modelos de la app panel."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from usuarios.models import ModeloBase


class Bitacora(ModeloBase):
    """Registro de acciones relevantes del sistema (RF-08, RF-23 y RF-29)."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones_bitacora",
    )
    accion = models.CharField("acción", max_length=50, db_index=True)
    objeto = models.CharField("objeto", max_length=200, blank=True)
    detalle = models.JSONField("detalle", default=dict, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    ocurrido_en = models.DateTimeField("ocurrido en", default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-ocurrido_en"]
        verbose_name = "registro de bitácora"
        verbose_name_plural = "bitácora"

    def __str__(self):
        return f"{self.ocurrido_en:%d/%m/%Y %H:%M} · {self.accion} · {self.objeto}"
