"""Rutas de la app panel."""

from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("mi-panel/", views.mi_panel, name="mi_panel"),
    path("admin-panel/", views.admin_panel, name="admin_panel"),
    path("admin-panel/bitacora/", views.bitacora, name="bitacora"),
]
