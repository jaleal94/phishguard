"""Cliente mínimo de Supabase Storage (API REST) para subir archivos sin tocar el disco.

Se usan dos buckets:
- SUPABASE_BUCKET_PUBLICO: imágenes de lecciones (lectura pública).
- SUPABASE_BUCKET: adjuntos de reportes (privado; se accede con URL firmada).
"""

import logging
import uuid
from pathlib import PurePosixPath
from urllib.parse import quote

import requests
from django.conf import settings

logger = logging.getLogger("phishguard.almacenamiento")
TIEMPO_ESPERA = 15


class AlmacenamientoError(Exception):
    """Error al comunicarse con Supabase Storage o falta de configuración."""


def esta_configurado():
    """Indica si hay credenciales de Supabase Storage."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY)


def _cabeceras(extra=None):
    cabeceras = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_KEY,
    }
    cabeceras.update(extra or {})
    return cabeceras


def generar_ruta(carpeta, nombre_original):
    """Genera una ruta única conservando solo la extensión del archivo original."""
    extension = PurePosixPath(nombre_original or "").suffix.lower()
    return f"{carpeta}/{uuid.uuid4().hex}{extension}"


def subir(ruta, contenido, tipo_contenido, bucket=None):
    """Sube ``contenido`` (bytes) a ``bucket/ruta`` y devuelve la ruta."""
    if not esta_configurado():
        raise AlmacenamientoError("El almacenamiento de archivos no está configurado.")
    bucket = bucket or settings.SUPABASE_BUCKET
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{quote(ruta)}"
    try:
        respuesta = requests.post(
            url,
            data=contenido,
            headers=_cabeceras({"Content-Type": tipo_contenido, "x-upsert": "false"}),
            timeout=TIEMPO_ESPERA,
        )
    except requests.RequestException as error:
        logger.error("error_subida", extra={"detalle": str(error)})
        raise AlmacenamientoError("No se pudo conectar con el almacenamiento.") from error
    if respuesta.status_code >= 300:
        logger.error("error_subida", extra={"detalle": respuesta.text[:300]})
        raise AlmacenamientoError("El almacenamiento rechazó el archivo.")
    return ruta


def url_publica(ruta, bucket=None):
    """URL pública de un objeto en un bucket público."""
    bucket = bucket or settings.SUPABASE_BUCKET_PUBLICO
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{quote(ruta)}"


def url_firmada(ruta, segundos=300, bucket=None):
    """Genera una URL temporal para descargar un objeto de un bucket privado."""
    if not esta_configurado():
        raise AlmacenamientoError("El almacenamiento de archivos no está configurado.")
    bucket = bucket or settings.SUPABASE_BUCKET
    url = f"{settings.SUPABASE_URL}/storage/v1/object/sign/{bucket}/{quote(ruta)}"
    try:
        respuesta = requests.post(
            url, json={"expiresIn": segundos}, headers=_cabeceras(), timeout=TIEMPO_ESPERA
        )
        respuesta.raise_for_status()
        firmada = respuesta.json()["signedURL"]
    except (requests.RequestException, KeyError, ValueError) as error:
        raise AlmacenamientoError("No se pudo generar el enlace de descarga.") from error
    return f"{settings.SUPABASE_URL}/storage/v1{firmada}"
