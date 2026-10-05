"""Servicios de la app reportes."""

import logging
import re
from email.utils import parseaddr
from pathlib import PurePosixPath

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from panel.bitacora import registrar
from phishguard import almacenamiento
from simulaciones.models import Campana, Destinatario, EventoSimulacion

from .models import ReporteSospechoso

logger = logging.getLogger("phishguard.reportes")

# RF-22: extensión permitida -> (tipo de contenido, firma inicial del archivo o None).
TIPOS_ADJUNTO = {
    ".png": ("image/png", b"\x89PNG"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".pdf": ("application/pdf", b"%PDF"),
    ".eml": ("message/rfc822", None),
}
PREFIJOS_RESPUESTA = re.compile(r"^\s*((re|rv|fw|fwd|reenviado)\s*:\s*)+", re.IGNORECASE)


class AdjuntoInvalido(Exception):
    """El archivo adjunto no cumple las reglas de RF-22."""


def tamano_maximo():
    """Tamaño máximo del adjunto en bytes."""
    return settings.REPORTE_TAMANO_MAX_MB * 1024 * 1024


def validar_adjunto(archivo):
    """RF-22: solo .png, .jpg, .pdf y .eml dentro del tamaño máximo.

    Devuelve ``(contenido, tipo_contenido)``. Además de la extensión se verifica la
    firma del archivo para que no se pueda renombrar un ejecutable como .pdf.
    """
    extension = PurePosixPath(archivo.name or "").suffix.lower()
    if extension not in TIPOS_ADJUNTO:
        raise AdjuntoInvalido("Solo se permiten archivos .png, .jpg, .pdf o .eml.")
    if archivo.size > tamano_maximo():
        raise AdjuntoInvalido(
            f"El archivo supera el tamaño máximo de {settings.REPORTE_TAMANO_MAX_MB} MB."
        )
    contenido = archivo.read()
    tipo, firma = TIPOS_ADJUNTO[extension]
    if firma is not None and not contenido.startswith(firma):
        raise AdjuntoInvalido("El contenido del archivo no corresponde a su extensión.")
    if firma is None and b"\x00" in contenido[:4096]:
        raise AdjuntoInvalido("El archivo .eml no es un mensaje de correo válido.")
    return contenido, tipo


def guardar_adjunto(archivo):
    """Valida y sube el adjunto al bucket privado de Supabase Storage; devuelve la ruta."""
    contenido, tipo = validar_adjunto(archivo)
    ruta = almacenamiento.generar_ruta("reportes", archivo.name)
    almacenamiento.subir(ruta, contenido, tipo, bucket=settings.SUPABASE_BUCKET)
    return ruta


def _normalizar_asunto(asunto):
    sin_prefijos = PREFIJOS_RESPUESTA.sub("", asunto or "")
    return " ".join(sin_prefijos.split()).casefold()


def _partes_remitente(texto):
    nombre, correo = parseaddr(texto or "")
    if not correo and "@" not in (texto or ""):
        nombre, correo = texto, ""
    return " ".join(nombre.split()).casefold(), correo.strip().casefold()


def remitentes_coinciden(reportado, plantilla):
    """Compara el remitente reportado con el remitente visible de la plantilla."""
    nombre_r, correo_r = _partes_remitente(reportado)
    nombre_p, correo_p = _partes_remitente(plantilla)
    if correo_r and correo_p:
        return correo_r == correo_p
    return bool(nombre_r) and nombre_r in {nombre_p, correo_p}


def vincular_con_campana(reporte):
    """RF-25: si el correo reportado es de una campaña activa enviada al usuario,
    vincula el reporte y registra un EventoSimulacion de tipo REPORTE (una sola vez).

    Se considera activa una campaña en estado ENVIANDO o FINALIZADA cuyo correo ya se
    envió al usuario. Devuelve el Destinatario vinculado o None.
    """
    asunto = _normalizar_asunto(reporte.asunto)
    candidatos = (
        Destinatario.objects.filter(
            usuario=reporte.reportado_por,
            enviado_en__isnull=False,
            campana__estado__in=[Campana.Estado.ENVIANDO, Campana.Estado.FINALIZADA],
        )
        .select_related("campana__plantilla")
        .order_by("-enviado_en")
    )
    for destinatario in candidatos:
        plantilla = destinatario.campana.plantilla
        if _normalizar_asunto(plantilla.asunto) == asunto and remitentes_coinciden(
            reporte.remitente, plantilla.remitente_visible
        ):
            reporte.destinatario_sim = destinatario
            reporte.save(update_fields=["destinatario_sim", "actualizado_en"])
            ya_reportado = destinatario.eventos.filter(
                tipo=EventoSimulacion.Tipo.REPORTE
            ).exists()
            if not ya_reportado:
                EventoSimulacion.objects.create(
                    destinatario=destinatario, tipo=EventoSimulacion.Tipo.REPORTE
                )
            return destinatario
    return None


def notificar_estado(reporte):
    """RF-24: avisa por correo al usuario que su reporte cambió de estado."""
    contexto = {"reporte": reporte, "url": f"{settings.SITE_URL}/reportes/{reporte.pk}/"}
    try:
        send_mail(
            subject=f"PhishGuard: su reporte está «{reporte.get_estado_display()}»",
            message=render_to_string("reportes/correo_estado.txt", contexto),
            from_email=None,
            recipient_list=[reporte.reportado_por.email],
        )
    except Exception:  # El cambio de estado no debe fallar por un problema de SMTP.
        logger.exception("error_notificacion_reporte", extra={"detalle": {"id": reporte.pk}})
        return False
    return True


def cambiar_estado(reporte, *, estado, comentario, administrador, request=None):
    """RF-23 y RF-24: cambia el estado, lo registra en la bitácora y notifica al usuario."""
    anterior = reporte.estado
    reporte.estado = estado
    reporte.comentario_admin = comentario
    if estado != ReporteSospechoso.Estado.PENDIENTE:
        reporte.atendido_por = administrador
        reporte.atendido_en = timezone.now()
    reporte.save()
    if anterior == estado:
        return False
    registrar(
        "CAMBIO_ESTADO_REPORTE",
        usuario=administrador,
        objeto=f"Reporte #{reporte.pk}: {reporte.asunto}"[:200],
        detalle={"antes": anterior, "despues": estado, "comentario": comentario[:200]},
        request=request,
    )
    notificar_estado(reporte)
    return True
