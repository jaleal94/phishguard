"""Señales de la app usuarios."""

from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

from panel.bitacora import registrar


@receiver(user_logged_out)
def registrar_cierre_sesion(sender, request, user, **kwargs):
    """Registra en la bitácora cada cierre de sesión (manual o por inactividad)."""
    if user is not None:
        registrar("CIERRE_SESION", usuario=user, objeto=user.email, request=request)
