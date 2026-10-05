"""Rutas de la app reportes."""

from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("reportar/", views.reportar, name="reportar"),
    path("reportes/<int:pk>/", views.detalle, name="detalle"),
    path("admin-panel/reportes/", views.bandeja, name="bandeja"),
    path("admin-panel/reportes/<int:pk>/", views.atender, name="atender"),
    path(
        "admin-panel/reportes/<int:pk>/adjunto/",
        views.descargar_adjunto,
        name="descargar_adjunto",
    ),
]
