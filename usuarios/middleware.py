"""Middleware de cierre de sesión por inactividad (RF-07)."""

import time
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect, resolve_url

CLAVE_ACTIVIDAD = "ultima_actividad"
# Para no escribir la sesión en cada petición, solo se actualiza cada minuto.
INTERVALO_ACTUALIZACION = 60
MENSAJE_INACTIVIDAD = "Su sesión se cerró por inactividad. Inicie sesión de nuevo."


class InactividadMiddleware:
    """Cierra la sesión si pasaron más de INACTIVIDAD_SEGUNDOS desde la última petición."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            ahora = int(time.time())
            ultima = request.session.get(CLAVE_ACTIVIDAD)
            if ultima is not None and ahora - ultima > settings.INACTIVIDAD_SEGUNDOS:
                logout(request)
                messages.info(request, MENSAJE_INACTIVIDAD)
                url = resolve_url(settings.LOGIN_URL)
                return redirect(f"{url}?{urlencode({'next': request.get_full_path()})}")
            if ultima is None or ahora - ultima >= INTERVALO_ACTUALIZACION:
                request.session[CLAVE_ACTIVIDAD] = ahora
        return self.get_response(request)
