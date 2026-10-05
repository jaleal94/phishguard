"""Modelos de la app capacitacion."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from usuarios.models import ModeloBase

from .saneamiento import sanear_html


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

    @property
    def total_lecciones(self):
        return self.curso.lecciones.count()

    @property
    def lecciones_completadas(self):
        return self.progresos.count()

    @property
    def porcentaje_avance(self):
        """RF-11: lecciones completadas entre lecciones totales, en porcentaje entero."""
        total = self.total_lecciones
        if not total:
            return 0
        return round(self.lecciones_completadas * 100 / total)

    @property
    def vencida(self):
        """Indica si pasó la fecha límite sin completar el curso."""
        return bool(
            self.fecha_limite and not self.completada and self.fecha_limite < timezone.localdate()
        )


class Leccion(ModeloBase):
    """Lección de un curso. El HTML se sanea antes de guardarse (RF-09)."""

    curso = models.ForeignKey(
        Curso, verbose_name="curso", on_delete=models.CASCADE, related_name="lecciones"
    )
    orden = models.PositiveSmallIntegerField("orden", default=1)
    titulo = models.CharField("título", max_length=200)
    contenido_html = models.TextField("contenido", blank=True)
    video_url = models.URLField("URL del video", blank=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "lección"
        verbose_name_plural = "lecciones"

    def __str__(self):
        return f"{self.orden}. {self.titulo}"

    def save(self, *args, **kwargs):
        self.contenido_html = sanear_html(self.contenido_html)
        super().save(*args, **kwargs)


class ProgresoLeccion(ModeloBase):
    """Marca de lección completada dentro de una asignación (RF-11)."""

    asignacion = models.ForeignKey(
        Asignacion, verbose_name="asignación", on_delete=models.CASCADE, related_name="progresos"
    )
    leccion = models.ForeignKey(
        Leccion, verbose_name="lección", on_delete=models.CASCADE, related_name="progresos"
    )
    completada_en = models.DateTimeField("completada en", default=timezone.now)

    class Meta:
        verbose_name = "progreso de lección"
        verbose_name_plural = "progresos de lección"
        constraints = [
            models.UniqueConstraint(fields=["asignacion", "leccion"], name="progreso_unico")
        ]


class Evaluacion(ModeloBase):
    """Evaluación final de un curso (RF-12 y RF-13)."""

    curso = models.OneToOneField(
        Curso, verbose_name="curso", on_delete=models.CASCADE, related_name="evaluacion"
    )
    nota_minima = models.PositiveSmallIntegerField(
        "nota mínima",
        default=70,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Sobre 100.",
    )
    intentos_maximos = models.PositiveSmallIntegerField(
        "intentos máximos", default=3, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )

    class Meta:
        verbose_name = "evaluación"
        verbose_name_plural = "evaluaciones"

    def __str__(self):
        return f"Evaluación de {self.curso}"


class Pregunta(ModeloBase):
    """Pregunta de selección simple de una evaluación."""

    evaluacion = models.ForeignKey(
        Evaluacion, verbose_name="evaluación", on_delete=models.CASCADE, related_name="preguntas"
    )
    enunciado = models.TextField("enunciado")
    orden = models.PositiveSmallIntegerField("orden", default=1)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "pregunta"
        verbose_name_plural = "preguntas"

    def __str__(self):
        return self.enunciado[:80]


class Opcion(ModeloBase):
    """Opción de respuesta de una pregunta."""

    pregunta = models.ForeignKey(
        Pregunta, verbose_name="pregunta", on_delete=models.CASCADE, related_name="opciones"
    )
    texto = models.CharField("texto", max_length=300)
    es_correcta = models.BooleanField("es correcta", default=False)

    class Meta:
        ordering = ["id"]
        verbose_name = "opción"
        verbose_name_plural = "opciones"

    def __str__(self):
        return self.texto


class Intento(ModeloBase):
    """Intento de un usuario en una evaluación, con nota sobre 100."""

    evaluacion = models.ForeignKey(
        Evaluacion, verbose_name="evaluación", on_delete=models.CASCADE, related_name="intentos"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.CASCADE,
        related_name="intentos",
    )
    nota = models.DecimalField("nota", max_digits=5, decimal_places=2)
    aprobado = models.BooleanField("aprobado", default=False)
    respuestas = models.JSONField("respuestas", default=dict)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "intento"
        verbose_name_plural = "intentos"

    def __str__(self):
        return f"{self.usuario} · {self.evaluacion} · {self.nota}"
