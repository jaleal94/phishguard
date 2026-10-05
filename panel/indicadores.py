"""Cálculo de indicadores del panel del Administrador (RF-26 y RF-27)."""

from django.db.models import Count, F, Q

from capacitacion.models import Asignacion, Curso
from reportes.models import ReporteSospechoso
from simulaciones.models import Campana, Destinatario, EventoSimulacion


def _tasa(parte, total):
    """Porcentaje con un decimal; 0 si no hay base."""
    return round(parte * 100 / total, 1) if total else 0.0


def indicadores_campanas(departamento=None, campana=None):
    """RF-26: tasas de clics y de reporte por campaña, en orden cronológico.

    tasa de clics   = destinatarios con clic    / destinatarios enviados
    tasa de reporte = destinatarios con reporte / destinatarios enviados
    Ambas filtrables por departamento (del destinatario) y por campaña.
    """
    destinatarios = Destinatario.objects.filter(enviado_en__isnull=False)
    if departamento:
        destinatarios = destinatarios.filter(usuario__departamento=departamento)
    if campana:
        destinatarios = destinatarios.filter(campana=campana)
    filas = (
        destinatarios.values("campana_id", "campana__nombre", "campana__fecha_envio")
        .annotate(
            enviados=Count("id", distinct=True),
            clics=Count(
                "id", filter=Q(eventos__tipo=EventoSimulacion.Tipo.CLIC), distinct=True
            ),
            reportes=Count(
                "id", filter=Q(eventos__tipo=EventoSimulacion.Tipo.REPORTE), distinct=True
            ),
        )
        .order_by("campana__fecha_envio", "campana_id")
    )
    resultado = []
    for fila in filas:
        resultado.append(
            {
                "id": fila["campana_id"],
                "nombre": fila["campana__nombre"],
                "fecha": fila["campana__fecha_envio"],
                "enviados": fila["enviados"],
                "clics": fila["clics"],
                "reportes": fila["reportes"],
                "tasa_clics": _tasa(fila["clics"], fila["enviados"]),
                "tasa_reporte": _tasa(fila["reportes"], fila["enviados"]),
            }
        )
    return resultado


def totales_campanas(filas):
    """Tasas globales de un conjunto de campañas (sobre el total de enviados)."""
    enviados = sum(f["enviados"] for f in filas)
    clics = sum(f["clics"] for f in filas)
    reportes = sum(f["reportes"] for f in filas)
    return {
        "enviados": enviados,
        "clics": clics,
        "reportes": reportes,
        "tasa_clics": _tasa(clics, enviados),
        "tasa_reporte": _tasa(reportes, enviados),
    }


def variacion_clics(filas):
    """Variación porcentual de la tasa de clics entre la primera campaña (línea base)
    y la última. Negativa = mejora. None si hay menos de dos campañas o base 0."""
    if len(filas) < 2 or not filas[0]["tasa_clics"]:
        return None
    base, ultima = filas[0]["tasa_clics"], filas[-1]["tasa_clics"]
    return round((ultima - base) * 100 / base, 1)


def indicadores_capacitacion(departamento=None):
    """Cobertura de capacitación de los cursos no de refuerzo publicados.

    Una asignación cuenta «a tiempo» si se completó en o antes de su fecha límite
    (o si no tiene fecha límite).
    """
    asignaciones = Asignacion.objects.filter(
        curso__estado=Curso.Estado.PUBLICADO, curso__es_refuerzo=False, usuario__is_active=True
    )
    if departamento:
        asignaciones = asignaciones.filter(usuario__departamento=departamento)
    datos = asignaciones.aggregate(
        total=Count("id"),
        completadas=Count("id", filter=Q(completada_en__isnull=False)),
        a_tiempo=Count(
            "id",
            filter=Q(completada_en__isnull=False)
            & (Q(fecha_limite__isnull=True) | Q(completada_en__date__lte=F("fecha_limite"))),
        ),
    )
    datos["cobertura"] = _tasa(datos["a_tiempo"], datos["total"])
    return datos


def indicadores_reportes(departamento=None):
    """Trazabilidad de reportes: totales, pendientes y porcentaje atendido."""
    reportes = ReporteSospechoso.objects.all()
    if departamento:
        reportes = reportes.filter(reportado_por__departamento=departamento)
    datos = reportes.aggregate(
        total=Count("id"),
        pendientes=Count("id", filter=Q(estado=ReporteSospechoso.Estado.PENDIENTE)),
        atendidos=Count("id", filter=Q(atendido_en__isnull=False)),
        confirmados=Count("id", filter=Q(estado=ReporteSospechoso.Estado.PHISHING_CONFIRMADO)),
    )
    datos["porcentaje_atendidos"] = _tasa(datos["atendidos"], datos["total"])
    return datos


def campanas_para_filtro():
    """Campañas disponibles en el filtro del panel."""
    return Campana.objects.order_by("-fecha_envio").only("id", "nombre")
