"""Rutas de la app reportes (provisionales hasta la Línea C)."""

from django.urls import path

from panel.views import en_construccion

app_name = "reportes"

urlpatterns = [
    path(
        "reportar/",
        en_construccion(
            "Reportar correo sospechoso",
            "Formulario para reportar correos sospechosos con adjunto (RF-22).",
        ),
        name="reportar",
    ),
    path(
        "admin-panel/reportes/",
        en_construccion(
            "Bandeja de reportes",
            "Atención de reportes de correos sospechosos (RF-23 a RF-25).",
            solo_admin=True,
        ),
        name="bandeja",
    ),
]
