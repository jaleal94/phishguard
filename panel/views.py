"""Vistas de la app panel: paneles por rol, bitácora y pantallas provisionales."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

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
    """Panel personal: cursos, notas, certificados y reportes del usuario."""
    return render(request, "panel/mi_panel.html")


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
