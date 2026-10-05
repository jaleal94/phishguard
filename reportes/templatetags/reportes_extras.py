"""Filtros de plantilla de la app reportes."""

from django import template

register = template.Library()

CLASES_ESTADO = {
    "PENDIENTE": "text-bg-warning",
    "EN_REVISION": "text-bg-info",
    "PHISHING_CONFIRMADO": "text-bg-danger",
    "FALSO_POSITIVO": "text-bg-success",
}


@register.filter
def clase_estado_reporte(estado):
    """Clase de Bootstrap para la insignia del estado de un reporte."""
    return CLASES_ESTADO.get(estado, "text-bg-secondary")
