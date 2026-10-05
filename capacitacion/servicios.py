"""Servicios de la app capacitacion."""

from .models import Asignacion


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
