"""Modelos de la app simulaciones."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from usuarios.models import ModeloBase


class PlantillaCorreo(ModeloBase):
    """Plantilla de correo de phishing simulado."""

    class Dificultad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"

    nombre = models.CharField("nombre", max_length=150)
    asunto = models.CharField("asunto", max_length=200)
    remitente_visible = models.CharField(
        "remitente visible",
        max_length=200,
        help_text="Nombre y correo que verá el destinatario, p. ej. «Banco X <avisos@bx.com>».",
    )
    cuerpo_html = models.TextField(
        "cuerpo HTML", help_text="Use {{enlace}} donde debe ir el enlace de la simulación."
    )
    dificultad = models.CharField(
        "dificultad", max_length=5, choices=Dificultad.choices, default=Dificultad.MEDIA
    )
    tiene_formulario = models.BooleanField(
        "tiene formulario",
        default=False,
        help_text="Al hacer clic se muestra un formulario falso antes de la página educativa.",
    )
    senales = models.TextField(
        "señales de alerta",
        blank=True,
        help_text="Una señal por línea; se muestran en la página educativa (RF-20).",
    )

    class Meta:
        ordering = ["nombre"]
        verbose_name = "plantilla de correo"
        verbose_name_plural = "plantillas de correo"

    def __str__(self):
        return self.nombre


class Campana(ModeloBase):
    """Campaña de simulación de phishing enviada a uno o más departamentos."""

    class Estado(models.TextChoices):
        PROGRAMADA = "PROGRAMADA", "Programada"
        ENVIANDO = "ENVIANDO", "Enviando"
        FINALIZADA = "FINALIZADA", "Finalizada"

    nombre = models.CharField("nombre", max_length=150)
    plantilla = models.ForeignKey(
        PlantillaCorreo,
        verbose_name="plantilla",
        on_delete=models.PROTECT,
        related_name="campanas",
    )
    fecha_envio = models.DateTimeField("fecha de envío", default=timezone.now)
    estado = models.CharField(
        "estado", max_length=10, choices=Estado.choices, default=Estado.PROGRAMADA
    )
    curso_refuerzo = models.ForeignKey(
        "capacitacion.Curso",
        verbose_name="curso de refuerzo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campanas",
    )
    departamentos = models.ManyToManyField(
        "usuarios.Departamento", verbose_name="departamentos", blank=True
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="creado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campanas_creadas",
    )

    class Meta:
        ordering = ["-fecha_envio"]
        verbose_name = "campaña"
        verbose_name_plural = "campañas"

    def __str__(self):
        return self.nombre


class Destinatario(ModeloBase):
    """Usuario que recibe el correo de una campaña, identificado por un token único."""

    campana = models.ForeignKey(
        Campana, verbose_name="campaña", on_delete=models.CASCADE, related_name="destinatarios"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.CASCADE,
        related_name="destinos_simulacion",
    )
    token = models.UUIDField("token", default=uuid.uuid4, unique=True, editable=False)
    enviado_en = models.DateTimeField("enviado en", null=True, blank=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "destinatario"
        verbose_name_plural = "destinatarios"
        constraints = [
            models.UniqueConstraint(fields=["campana", "usuario"], name="destinatario_unico")
        ]

    def __str__(self):
        return f"{self.campana} → {self.usuario}"


class EventoSimulacion(ModeloBase):
    """Evento registrado sobre un destinatario.

    Regla de privacidad: nunca guarda lo que el usuario escribe en un formulario
    simulado; solo registra que hubo un envío.
    """

    class Tipo(models.TextChoices):
        APERTURA = "APERTURA", "Apertura"
        CLIC = "CLIC", "Clic"
        ENVIO_FORMULARIO = "ENVIO_FORMULARIO", "Envío de formulario"
        REPORTE = "REPORTE", "Reporte"

    destinatario = models.ForeignKey(
        Destinatario, verbose_name="destinatario", on_delete=models.CASCADE, related_name="eventos"
    )
    tipo = models.CharField("tipo", max_length=16, choices=Tipo.choices)
    ocurrido_en = models.DateTimeField("ocurrido en", default=timezone.now)
    user_agent = models.CharField("user agent", max_length=300, blank=True)

    class Meta:
        ordering = ["-ocurrido_en"]
        verbose_name = "evento de simulación"
        verbose_name_plural = "eventos de simulación"
        indexes = [models.Index(fields=["destinatario", "tipo"], name="evento_dest_tipo_idx")]

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.destinatario}"
