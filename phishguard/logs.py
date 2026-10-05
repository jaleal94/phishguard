"""Formateador de logs estructurados en JSON."""

import json
import logging
from datetime import UTC, datetime


class FormateadorJSON(logging.Formatter):
    """Emite cada registro como una línea JSON con nivel, módulo y mensaje."""

    CAMPOS_EXTRA = ("usuario", "accion", "ip", "detalle")

    def format(self, record):
        datos = {
            "momento": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "nivel": record.levelname,
            "modulo": record.name,
            "mensaje": record.getMessage(),
        }
        for campo in self.CAMPOS_EXTRA:
            if hasattr(record, campo):
                datos[campo] = getattr(record, campo)
        if record.exc_info:
            datos["excepcion"] = self.formatException(record.exc_info)
        return json.dumps(datos, ensure_ascii=False, default=str)
