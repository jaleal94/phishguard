"""Decoradores de control de acceso por rol (RF-04 y RF-05)."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def admin_requerido(vista):
    """Exige sesión iniciada y rol Administrador; si no, responde 403.

    Incluye ``login_required``: un visitante anónimo es redirigido al login y un
    Colaborador autenticado recibe un error 403.
    """

    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.es_admin:
            raise PermissionDenied("Esta sección es exclusiva para Administradores.")
        return vista(request, *args, **kwargs)

    return login_required(envoltura)
