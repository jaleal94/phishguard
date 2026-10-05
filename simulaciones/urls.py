"""Rutas de la app simulaciones (provisionales hasta la Línea B)."""

from django.urls import path

from panel.views import en_construccion

app_name = "simulaciones"

urlpatterns = [
    path(
        "admin-panel/plantillas/",
        en_construccion(
            "Plantillas de simulación",
            "Plantillas de correo de phishing simulado con vista previa (RF-16).",
            solo_admin=True,
        ),
        name="plantillas",
    ),
    path(
        "admin-panel/campanas/",
        en_construccion(
            "Campañas de simulación",
            "Campañas, envío por lotes y resultados (RF-17 a RF-21).",
            solo_admin=True,
        ),
        name="campanas",
    ),
]
