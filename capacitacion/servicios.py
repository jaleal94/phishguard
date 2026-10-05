"""Servicios de la app capacitacion: asignaciones, progreso y evaluaciones."""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from usuarios.models import Usuario

from .models import Asignacion, Intento, ProgresoLeccion


class EvaluacionNoDisponible(Exception):
    """La evaluación no puede presentarse (sin intentos, ya aprobada o lecciones pendientes)."""


def asignar_curso(curso, usuario, *, fecha_limite=None, origen=Asignacion.Origen.MANUAL):
    """Asigna un curso a un usuario sin crear duplicados.

    Contrato compartido con la Línea B (RF-20). Devuelve ``(asignacion, creada)``.
    Si la asignación ya existía no se modifica.
    """
    return Asignacion.objects.get_or_create(
        curso=curso,
        usuario=usuario,
        defaults={"fecha_limite": fecha_limite, "origen": origen},
    )


def asignar_a_usuarios(curso, usuarios, *, fecha_limite=None, origen=Asignacion.Origen.MANUAL):
    """Asigna el curso a varios usuarios activos, omitiendo los que ya lo tienen.

    Devuelve la cantidad de asignaciones nuevas.
    """
    ids = set(usuarios.filter(is_active=True).values_list("pk", flat=True))
    existentes = set(
        Asignacion.objects.filter(curso=curso, usuario_id__in=ids).values_list(
            "usuario_id", flat=True
        )
    )
    nuevas = [
        Asignacion(curso=curso, usuario_id=uid, fecha_limite=fecha_limite, origen=origen)
        for uid in sorted(ids - existentes)
    ]
    Asignacion.objects.bulk_create(nuevas, ignore_conflicts=True)
    return len(nuevas)


def asignar_a_departamento(curso, departamento, *, fecha_limite=None):
    """RF-10: una asignación por cada usuario activo del departamento, sin duplicados."""
    return asignar_a_usuarios(
        curso, Usuario.objects.filter(departamento=departamento), fecha_limite=fecha_limite
    )


def tiene_evaluacion(curso):
    """Indica si el curso tiene una evaluación con al menos una pregunta."""
    evaluacion = getattr(curso, "evaluacion", None)
    return evaluacion is not None and evaluacion.preguntas.exists()


def completar_leccion(asignacion, leccion):
    """RF-11: marca una lección como completada y cierra el curso si no tiene evaluación."""
    ProgresoLeccion.objects.get_or_create(asignacion=asignacion, leccion=leccion)
    if (
        not asignacion.completada
        and asignacion.porcentaje_avance == 100
        and not tiene_evaluacion(asignacion.curso)
    ):
        asignacion.completada_en = timezone.now()
        asignacion.save(update_fields=["completada_en", "actualizado_en"])


def intentos_usados(evaluacion, usuario):
    """Cantidad de intentos que el usuario ya presentó en la evaluación."""
    return Intento.objects.filter(evaluacion=evaluacion, usuario=usuario).count()


def motivo_no_disponible(asignacion):
    """Devuelve por qué no se puede presentar la evaluación, o None si se puede."""
    evaluacion = asignacion.curso.evaluacion
    if asignacion.completada:
        return "Ya aprobó este curso."
    if asignacion.porcentaje_avance < 100:
        return "Debe completar todas las lecciones antes de presentar la evaluación."
    if intentos_usados(evaluacion, asignacion.usuario) >= evaluacion.intentos_maximos:
        return "Agotó el número máximo de intentos de esta evaluación."
    return None


def calificar(evaluacion, respuestas):
    """RF-12: nota sobre 100 según la proporción de respuestas correctas.

    ``respuestas`` es un diccionario {id_pregunta: id_opcion}.
    """
    preguntas = list(evaluacion.preguntas.prefetch_related("opciones"))
    if not preguntas:
        return Decimal("0.00")
    correctas = 0
    for pregunta in preguntas:
        elegida = respuestas.get(pregunta.pk)
        if any(o.pk == elegida and o.es_correcta for o in pregunta.opciones.all()):
            correctas += 1
    nota = Decimal(correctas * 100) / Decimal(len(preguntas))
    return nota.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@transaction.atomic
def presentar_evaluacion(asignacion, respuestas):
    """RF-12 y RF-13: registra un intento respetando el máximo y la nota mínima.

    Aprobar marca la asignación como completada. Lanza ``EvaluacionNoDisponible``
    si el intento no está permitido.
    """
    asignacion = Asignacion.objects.select_for_update().get(pk=asignacion.pk)
    motivo = motivo_no_disponible(asignacion)
    if motivo:
        raise EvaluacionNoDisponible(motivo)
    evaluacion = asignacion.curso.evaluacion
    nota = calificar(evaluacion, respuestas)
    aprobado = nota >= evaluacion.nota_minima
    intento = Intento.objects.create(
        evaluacion=evaluacion,
        usuario=asignacion.usuario,
        nota=nota,
        aprobado=aprobado,
        respuestas={str(k): v for k, v in respuestas.items()},
    )
    if aprobado:
        asignacion.completada_en = timezone.now()
        asignacion.save(update_fields=["completada_en", "actualizado_en"])
    return intento
