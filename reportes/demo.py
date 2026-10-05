"""Reportes de demostración (usados por el comando seed_demo)."""

from datetime import timedelta

from django.utils import timezone

from usuarios.models import Usuario

from .models import ReporteSospechoso

REPORTES = [
    ("colaborador.demo", "Banco Nacional <alertas@bnacional-seguridad.com>",
     "Su cuenta será bloqueada en 24 horas", ReporteSospechoso.Estado.PHISHING_CONFIRMADO,
     "Confirmado: dominio falso. Ya fue bloqueado en el correo corporativo."),
    ("ana.martinez", "Paquetería Express <envios@px-entregas.net>",
     "Su paquete está retenido en aduana", ReporteSospechoso.Estado.EN_REVISION, ""),
    ("pedro.ramirez", "Proveedor ABC <facturacion@proveedorabc.com>",
     "Factura de octubre", ReporteSospechoso.Estado.FALSO_POSITIVO,
     "Es un proveedor real; puede abrir la factura con normalidad."),
    ("rosa.morales", "Microsoft 365 <no-reply@m365-verificacion.com>",
     "Su contraseña vence hoy", ReporteSospechoso.Estado.PENDIENTE, ""),
]


def cargar(admin):
    """Crea los reportes de demostración una sola vez. Devuelve cuántos creó."""
    if ReporteSospechoso.objects.exists():
        return 0
    ahora = timezone.now()
    creados = 0
    for i, (usuario, remitente, asunto, estado, comentario) in enumerate(REPORTES):
        autor = Usuario.objects.filter(email=f"{usuario}@curex.net.ve").first()
        if autor is None:
            continue
        atendido = estado != ReporteSospechoso.Estado.PENDIENTE
        ReporteSospechoso.objects.create(
            reportado_por=autor,
            remitente=remitente,
            asunto=asunto,
            fecha_recepcion=ahora - timedelta(days=i + 1, hours=2),
            estado=estado,
            comentario_admin=comentario,
            atendido_por=admin if atendido else None,
            atendido_en=ahora - timedelta(days=i) if atendido else None,
        )
        creados += 1
    return creados
