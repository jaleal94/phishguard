"""Vistas de la app panel: paneles por rol, bitácora y pantallas provisionales."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render

from capacitacion.models import Asignacion, Curso, Intento
from usuarios.decoradores import admin_requerido
from usuarios.models import Departamento, Usuario

from .models import Bitacora


@admin_requerido
def admin_panel(request):
    """Panel de indicadores del Administrador (los gráficos llegan en la fase final)."""
    contexto = {
        "total_colaboradores": Usuario.objects.filter(
            rol=Usuario.Rol.COLABORADOR, is_active=True
        ).count(),
        "total_departamentos": Departamento.objects.filter(activo=True).count(),
        "ultimas_acciones": Bitacora.objects.select_related("usuario")[:8],
    }
    return render(request, "panel/admin_panel.html", contexto)


@login_required
def mi_panel(request):
    """Panel personal: cursos, notas, certificados y reportes del usuario.

    RF-30: todas las consultas se filtran por el usuario autenticado.
    """
    asignaciones = list(
        Asignacion.objects.filter(usuario=request.user, curso__estado=Curso.Estado.PUBLICADO)
        .select_related("curso")
        .annotate(
            n_lecciones=Count("curso__lecciones", distinct=True),
            n_progresos=Count("progresos", distinct=True),
        )
        .order_by("completada_en", "fecha_limite")
    )
    notas = {}
    for intento in Intento.objects.filter(usuario=request.user).select_related("evaluacion"):
        notas.setdefault(intento.evaluacion.curso_id, intento)  # el más reciente primero
    for a in asignaciones:
        a.avance = round(a.n_progresos * 100 / a.n_lecciones) if a.n_lecciones else 0
        a.ultimo_intento = notas.get(a.curso_id)
    aprobadas = [a for a in asignaciones if a.completada]
    return render(
        request, "panel/mi_panel.html", {"asignaciones": asignaciones, "aprobadas": aprobadas}
    )


@admin_requerido
def bitacora(request):
    """Bitácora de acciones con filtros por acción y usuario."""
    registros = Bitacora.objects.select_related("usuario")
    accion = request.GET.get("accion", "")
    if accion:
        registros = registros.filter(accion=accion)
    usuario = request.GET.get("usuario", "").strip()
    if usuario:
        registros = registros.filter(usuario__email__icontains=usuario)
    acciones = Bitacora.objects.order_by("accion").values_list("accion", flat=True).distinct()
    pagina = Paginator(registros, 25).get_page(request.GET.get("pagina"))
    return render(
        request,
        "panel/bitacora.html",
        {
            "pagina": pagina,
            "acciones": acciones,
            "filtros": {"accion": accion, "usuario": usuario},
        },
    )


def en_construccion(titulo, descripcion, solo_admin=False):
    """Crea una vista provisional para módulos del MVP que aún no se implementan.

    Evita enlaces rotos (404) en el menú mientras avanzan las líneas A, B y C.
    """

    def vista(request, *args, **kwargs):
        return render(
            request,
            "comun/proximamente.html",
            {"titulo": titulo, "descripcion": descripcion, "en_construccion": True},
        )

    vista.__doc__ = f"Pantalla provisional: {titulo}."
    return admin_requerido(vista) if solo_admin else login_required(vista)
