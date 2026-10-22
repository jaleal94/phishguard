"""Registros de demostración para las tablas de simulaciones (seed_demo).

Solo crea filas en la base de datos para el panel de indicadores: no envía correos.
Las plantillas usan texto genérico de ejemplo.
"""

from datetime import timedelta

from django.utils import timezone

from capacitacion.models import Curso
from usuarios.models import Departamento, Usuario

from .models import Campana, Destinatario, EventoSimulacion, PlantillaCorreo

PLANTILLAS = [
    ("Plantilla de práctica 1", PlantillaCorreo.Dificultad.BAJA, False),
    ("Plantilla de práctica 2", PlantillaCorreo.Dificultad.BAJA, False),
    ("Plantilla de práctica 3", PlantillaCorreo.Dificultad.MEDIA, True),
    ("Plantilla de práctica 4", PlantillaCorreo.Dificultad.MEDIA, False),
    ("Plantilla de práctica 5", PlantillaCorreo.Dificultad.ALTA, True),
]

# (días atrás, departamentos, proporción de clics, proporción de reportes)
CAMPANAS = [
    (150, ["Administración", "Contabilidad", "Compras"], 0.6, 0.1),
    (120, ["Recursos Humanos", "Ventas"], 0.5, 0.25),
    (90, ["Administración", "Contabilidad"], 0.4, 0.3),
    (60, ["Compras", "Recursos Humanos", "Ventas"], 0.3, 0.4),
    (30, ["Administración", "Contabilidad", "Compras", "Recursos Humanos", "Ventas"], 0.2, 0.5),
]


def cargar(admin):
    """Crea 5 plantillas y 5 campañas finalizadas con destinatarios y eventos (idempotente)."""
    if Campana.objects.exists():
        return 0
    plantillas = []
    for i, (nombre, dificultad, formulario) in enumerate(PLANTILLAS, start=1):
        plantilla, _ = PlantillaCorreo.objects.get_or_create(
            nombre=nombre,
            defaults={
                "asunto": f"Asunto de ejemplo {i}",
                "remitente_visible": f"Remitente de ejemplo {i} <ejemplo{i}@demo.invalid>",
                "cuerpo_html": f"<p>Contenido de ejemplo de la plantilla de práctica {i}.</p>",
                "dificultad": dificultad,
                "tiene_formulario": formulario,
                "senales": "Remitente desconocido\nSentido de urgencia\nEnlace que no coincide",
            },
        )
        plantillas.append(plantilla)
    refuerzo = Curso.objects.filter(es_refuerzo=True).first()
    ahora = timezone.now()
    for i, (dias, deptos, p_clic, p_reporte) in enumerate(CAMPANAS):
        fecha = ahora - timedelta(days=dias)
        campana = Campana.objects.create(
            nombre=f"Campaña de demostración {i + 1}",
            plantilla=plantillas[i],
            fecha_envio=fecha,
            estado=Campana.Estado.FINALIZADA,
            curso_refuerzo=refuerzo,
            creado_por=admin,
        )
        departamentos = Departamento.objects.filter(nombre__in=deptos)
        campana.departamentos.set(departamentos)
        usuarios = Usuario.objects.filter(
            rol=Usuario.Rol.COLABORADOR, departamento__in=departamentos, is_active=True
        ).order_by("id")
        destinatarios = [
            Destinatario.objects.create(campana=campana, usuario=u, enviado_en=fecha)
            for u in usuarios
        ]
        total = len(destinatarios)
        n_clics, n_reportes = round(total * p_clic), round(total * p_reporte)
        for j, destinatario in enumerate(destinatarios):
            momento = fecha + timedelta(hours=j + 1)
            if j < n_clics:
                EventoSimulacion.objects.create(
                    destinatario=destinatario, tipo=EventoSimulacion.Tipo.APERTURA,
                    ocurrido_en=momento,
                )
                EventoSimulacion.objects.create(
                    destinatario=destinatario, tipo=EventoSimulacion.Tipo.CLIC,
                    ocurrido_en=momento + timedelta(minutes=5),
                )
            elif j >= total - n_reportes:
                EventoSimulacion.objects.create(
                    destinatario=destinatario, tipo=EventoSimulacion.Tipo.REPORTE,
                    ocurrido_en=momento,
                )
    return len(CAMPANAS)
