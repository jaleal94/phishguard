"""Rutas de la app capacitacion."""

from django.urls import path

from . import views

app_name = "capacitacion"

urlpatterns = [
    # Administrador
    path("admin-panel/cursos/", views.cursos_admin, name="cursos_admin"),
    path("admin-panel/cursos/nuevo/", views.curso_crear, name="curso_crear"),
    path("admin-panel/cursos/imagen/", views.subir_imagen, name="subir_imagen"),
    path("admin-panel/cursos/<int:pk>/", views.curso_detalle_admin, name="curso_detalle_admin"),
    path("admin-panel/cursos/<int:pk>/editar/", views.curso_editar, name="curso_editar"),
    path("admin-panel/cursos/<int:pk>/asignar/", views.curso_asignar, name="curso_asignar"),
    path(
        "admin-panel/cursos/<int:pk>/recordatorios/",
        views.curso_recordatorios,
        name="curso_recordatorios",
    ),
    path(
        "admin-panel/cursos/<int:curso_pk>/lecciones/nueva/",
        views.leccion_crear,
        name="leccion_crear",
    ),
    path("admin-panel/lecciones/<int:pk>/editar/", views.leccion_editar, name="leccion_editar"),
    path(
        "admin-panel/lecciones/<int:pk>/eliminar/", views.leccion_eliminar, name="leccion_eliminar"
    ),
    path(
        "admin-panel/cursos/<int:curso_pk>/evaluacion/",
        views.evaluacion_editar,
        name="evaluacion_editar",
    ),
    path(
        "admin-panel/cursos/<int:curso_pk>/preguntas/nueva/",
        views.pregunta_crear,
        name="pregunta_crear",
    ),
    path("admin-panel/preguntas/<int:pk>/editar/", views.pregunta_editar, name="pregunta_editar"),
    path(
        "admin-panel/preguntas/<int:pk>/eliminar/",
        views.pregunta_eliminar,
        name="pregunta_eliminar",
    ),
    # Colaborador (y vista previa del Administrador)
    path("cursos/<int:pk>/", views.curso_ver, name="curso_ver"),
    path(
        "cursos/<int:pk>/leccion/<int:leccion_pk>/completar/",
        views.leccion_completar,
        name="leccion_completar",
    ),
    path("cursos/<int:pk>/evaluacion/", views.evaluacion_presentar, name="evaluacion"),
    path(
        "cursos/<int:pk>/evaluacion/resultado/<int:intento_pk>/",
        views.intento_resultado,
        name="resultado",
    ),
    path("cursos/<int:pk>/certificado/", views.certificado, name="certificado"),
]
