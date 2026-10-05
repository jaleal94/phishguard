"""Filtros de plantilla de la app capacitacion."""

import re

from django import template

register = template.Library()

PATRON_YOUTUBE = re.compile(r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([\w-]{11})")
PATRON_VIMEO = re.compile(r"vimeo\.com/(?:video/)?(\d+)")

CLASES_ESTADO = {
    "BORRADOR": "text-bg-secondary",
    "PUBLICADO": "text-bg-success",
    "ARCHIVADO": "text-bg-light border",
}


@register.filter
def video_embed(url):
    """Convierte un enlace de YouTube o Vimeo en su URL de inserción; si no, cadena vacía."""
    if not url:
        return ""
    if coincidencia := PATRON_YOUTUBE.search(url):
        return f"https://www.youtube-nocookie.com/embed/{coincidencia.group(1)}"
    if coincidencia := PATRON_VIMEO.search(url):
        return f"https://player.vimeo.com/video/{coincidencia.group(1)}"
    return ""


@register.filter
def clase_estado(estado):
    """Clase de Bootstrap para la insignia del estado de un curso."""
    return CLASES_ESTADO.get(estado, "text-bg-secondary")
