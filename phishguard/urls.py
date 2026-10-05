"""Rutas principales de PhishGuard."""

from django.contrib import admin
from django.urls import include, path

from usuarios.views import inicio

urlpatterns = [
    path("", inicio, name="inicio"),
    # Panel nativo de Django: solo para superusuarios técnicos.
    path("admin/", admin.site.urls),
    path("", include("usuarios.urls")),
    path("", include("panel.urls")),
    path("", include("capacitacion.urls")),
    path("", include("simulaciones.urls")),
    path("", include("reportes.urls")),
]
