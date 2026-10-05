"""Servicio para registrar acciones en la bitácora."""

import ipaddress
import logging

from .models import Bitacora

logger = logging.getLogger("phishguard.bitacora")


def obtener_ip(request):
    """Devuelve la IP del cliente considerando el proxy de Vercel, o None si no es válida."""
    if request is None:
        return None
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR", "")
    candidata = reenviada.split(",")[0].strip() if reenviada else request.META.get("REMOTE_ADDR")
    try:
        return str(ipaddress.ip_address(candidata)) if candidata else None
    except ValueError:
        return None


def registrar(accion, *, usuario=None, objeto="", detalle=None, request=None):
    """Crea un registro en la bitácora y lo emite también como log estructurado.

    Si no se indica ``usuario`` se toma el usuario autenticado de ``request``.
    """
    if usuario is None and request is not None and request.user.is_authenticated:
        usuario = request.user
    registro = Bitacora.objects.create(
        usuario=usuario,
        accion=accion,
        objeto=str(objeto)[:200],
        detalle=detalle or {},
        ip=obtener_ip(request),
    )
    logger.info(
        "bitacora",
        extra={
            "accion": accion,
            "usuario": getattr(usuario, "email", None),
            "ip": registro.ip,
            "detalle": registro.detalle,
        },
    )
    return registro


def cambios_formulario(form):
    """Devuelve los campos modificados de un ModelForm, para el detalle de la bitácora."""
    return {campo: str(form.cleaned_data.get(campo))[:200] for campo in form.changed_data}
