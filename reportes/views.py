"""Vistas de la app reportes (RF-22 a RF-25)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from panel.bitacora import registrar
from phishguard import almacenamiento
from usuarios.decoradores import admin_requerido

from . import servicios
from .forms import AtenderReporteForm, ReporteForm
from .models import ReporteSospechoso


@login_required
def reportar(request):
    """RF-22: formulario para reportar un correo sospechoso."""
    form = ReporteForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        reporte = form.save(commit=False)
        reporte.reportado_por = request.user
        archivo = form.cleaned_data.get("adjunto")
        if archivo:
            try:
                reporte.adjunto_url = servicios.guardar_adjunto(archivo)
                reporte.adjunto_nombre = archivo.name[:255]
            except (servicios.AdjuntoInvalido, almacenamiento.AlmacenamientoError) as error:
                form.add_error("adjunto", f"No se pudo guardar el adjunto: {error}")
        if not form.errors:
            reporte.save()
            servicios.vincular_con_campana(reporte)
            registrar("REPORTE_RECIBIDO", objeto=f"Reporte #{reporte.pk}", request=request)
            messages.success(
                request,
                "¡Gracias por reportar! El Departamento de Soporte Técnico y Sistemas lo "
                "revisará y le avisará por correo.",
            )
            return redirect("reportes:detalle", reporte.pk)
    recientes = ReporteSospechoso.objects.filter(reportado_por=request.user)[:5]
    return render(request, "reportes/reportar.html", {"form": form, "recientes": recientes})


@login_required
def detalle(request, pk):
    """Detalle de un reporte propio. RF-30: solo el autor puede verlo."""
    reporte = get_object_or_404(ReporteSospechoso, pk=pk, reportado_por=request.user)
    return render(request, "reportes/detalle.html", {"reporte": reporte})


@admin_requerido
def bandeja(request):
    """Bandeja de reportes con filtros por estado y búsqueda."""
    reportes = ReporteSospechoso.objects.select_related(
        "reportado_por", "reportado_por__departamento", "destinatario_sim__campana"
    )
    estado = request.GET.get("estado", "")
    if estado in ReporteSospechoso.Estado.values:
        reportes = reportes.filter(estado=estado)
    q = request.GET.get("q", "").strip()
    if q:
        reportes = reportes.filter(
            Q(asunto__icontains=q) | Q(remitente__icontains=q)
            | Q(reportado_por__email__icontains=q)
        )
    conteo = dict(
        ReporteSospechoso.objects.values_list("estado").annotate(n=Count("id")).values_list(
            "estado", "n"
        )
    )
    resumen = [
        {"valor": valor, "etiqueta": etiqueta, "total": conteo.get(valor, 0)}
        for valor, etiqueta in ReporteSospechoso.Estado.choices
    ]
    pagina = Paginator(reportes, 20).get_page(request.GET.get("pagina"))
    return render(
        request,
        "reportes/admin/bandeja.html",
        {"pagina": pagina, "resumen": resumen, "filtros": {"estado": estado, "q": q}},
    )


@admin_requerido
def atender(request, pk):
    """RF-23 y RF-24: detalle del reporte y cambio de estado por el Administrador."""
    reporte = get_object_or_404(
        ReporteSospechoso.objects.select_related(
            "reportado_por", "atendido_por", "destinatario_sim__campana"
        ),
        pk=pk,
    )
    form = AtenderReporteForm(
        request.POST or None,
        initial={"estado": reporte.estado, "comentario": reporte.comentario_admin},
    )
    if request.method == "POST" and form.is_valid():
        cambio = servicios.cambiar_estado(
            reporte,
            estado=form.cleaned_data["estado"],
            comentario=form.cleaned_data["comentario"],
            administrador=request.user,
            request=request,
        )
        if cambio:
            messages.success(request, "Estado actualizado y usuario notificado por correo.")
        else:
            messages.info(request, "Se guardó el comentario; el estado no cambió.")
        return redirect("reportes:atender", reporte.pk)
    return render(request, "reportes/admin/atender.html", {"reporte": reporte, "form": form})


@admin_requerido
@require_POST
def descargar_adjunto(request, pk):
    """Redirige a una URL firmada y temporal del adjunto (bucket privado)."""
    reporte = get_object_or_404(ReporteSospechoso, pk=pk)
    if not reporte.adjunto_url:
        messages.error(request, "Este reporte no tiene adjunto.")
        return redirect("reportes:atender", reporte.pk)
    try:
        url = almacenamiento.url_firmada(reporte.adjunto_url, segundos=120)
    except almacenamiento.AlmacenamientoError as error:
        messages.error(request, str(error))
        return redirect("reportes:atender", reporte.pk)
    registrar("DESCARGAR_ADJUNTO", objeto=f"Reporte #{reporte.pk}", request=request)
    return redirect(url)
