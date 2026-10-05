"""Rutas de la app capacitacion (provisionales hasta la Línea A)."""

from django.urls import path

from panel.views import en_construccion

app_name = "capacitacion"

urlpatterns = [
    path(
        "admin-panel/cursos/",
        en_construccion(
            "Gestión de cursos",
            "Cursos, lecciones, evaluaciones y asignaciones (RF-09 a RF-13).",
            solo_admin=True,
        ),
        name="cursos_admin",
    ),
]
