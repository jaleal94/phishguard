"""Modelos de la app capacitacion."""

from django.conf import settings
from django.db import models

from usuarios.models import ModeloBase


class Curso(ModeloBase):
    """Curso de concientización compuesto por lecciones y una evaluación opcional."""

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PUBLICADO = "PUBLICADO", "Publicado"
        ARCHIVADO = "ARCHIVADO", "Archivado"

    titulo = models.CharField("título", max_length=200)
    descripcion = models.TextField("descripción", blank=True)
    estado = models.CharField(
        "estado", max_length=10, choices=Estado.choices, default=Estado.BORRADOR
    )
    es_refuerzo = models.BooleanField(
        "es curso de refuerzo",
        default=False,
        help_text="Se asigna automáticamente a quien hace clic en una simulación.",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="creado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cursos_creados",
    )

    class Meta:
        ordering = ["titulo"]
        verbose_name = "curso"
        verbose_name_plural = "cursos"

    def __str__(self):
        return self.titulo

    @property
    def esta_publicado(self):
        return self.estado == self.Estado.PUBLICADO


class Asignacion(ModeloBase):
    """Curso asignado a un usuario (manualmente o por caer en una simulación).

    Contrato compartido con la Línea B: crear asignaciones siempre mediante
    ``capacitacion.servicios.asignar_curso``.
    """

    class Origen(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        SIMULACION = "SIMULACION", "Simulación"

    curso = models.ForeignKey(
        Curso, verbose_name="curso", on_delete=models.CASCADE, related_name="asignaciones"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.CASCADE,
        related_name="asignaciones",
    )
    fecha_limite = models.DateField("fecha límite", null=True, blank=True)
    origen = models.CharField(
        "origen", max_length=10, choices=Origen.choices, default=Origen.MANUAL
    )
    completada_en = models.DateTimeField("completada en", null=True, blank=True)

    class Meta:
        ordering = ["fecha_limite", "id"]
        verbose_name = "asignación"
        verbose_name_plural = "asignaciones"
        constraints = [
            models.UniqueConstraint(fields=["curso", "usuario"], name="asignacion_unica")
        ]

    def __str__(self):
        return f"{self.curso} → {self.usuario}"

    @property
    def completada(self):
        return self.completada_en is not None
