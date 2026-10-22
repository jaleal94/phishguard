"""Exporta los datos de las tablas del proyecto como un script SQL de inserción (PostgreSQL)."""

import datetime
import decimal
import json
import uuid
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand

# Orden de inserción respetando las claves foráneas.
TABLAS = [
    "usuarios.Departamento",
    "usuarios.Usuario",
    "panel.Bitacora",
    "capacitacion.Curso",
    "capacitacion.Leccion",
    "capacitacion.Asignacion",
    "capacitacion.ProgresoLeccion",
    "capacitacion.Evaluacion",
    "capacitacion.Pregunta",
    "capacitacion.Opcion",
    "capacitacion.Intento",
    "simulaciones.PlantillaCorreo",
    "simulaciones.Campana",
    "simulaciones.Campana_departamentos",
    "simulaciones.Destinatario",
    "simulaciones.EventoSimulacion",
    "reportes.ReporteSospechoso",
]


def literal(valor, es_json=False):
    """Convierte un valor de Python en un literal SQL de PostgreSQL."""
    if valor is None:
        return "NULL"
    if es_json:
        texto = json.dumps(valor, ensure_ascii=False).replace("'", "''")
        return f"'{texto}'::jsonb"
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, int | float | decimal.Decimal):
        return str(valor)
    if isinstance(valor, datetime.datetime | datetime.date | uuid.UUID):
        return f"'{valor.isoformat() if hasattr(valor, 'isoformat') else valor}'"
    texto = str(valor).replace("'", "''")
    return f"'{texto}'"


def modelo_de(etiqueta):
    """Obtiene el modelo, incluidas las tablas intermedias automáticas (M2M)."""
    app, nombre = etiqueta.split(".")
    if "_" in nombre:
        base, campo = nombre.split("_", 1)
        return apps.get_model(app, base)._meta.get_field(campo).remote_field.through
    return apps.get_model(app, nombre)


class Command(BaseCommand):
    help = "Genera docs/base_de_datos/datos_iniciales.sql con INSERT de todas las tablas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--salida", default="docs/base_de_datos/datos_iniciales.sql", help="Archivo de salida."
        )

    def handle(self, *args, **opciones):
        lineas = [
            "-- PhishGuard: script de inserción de datos iniciales (PostgreSQL).",
            "-- Generado con 'python manage.py exportar_datos_sql' a partir de 'seed_demo'.",
            "-- Requiere haber creado antes las tablas (python manage.py migrate o",
            "-- esquema_postgresql.sql). Contraseña de las cuentas demo: PhishGuard.Demo2026",
            "",
            "BEGIN;",
            "",
        ]
        resumen = []
        for etiqueta in TABLAS:
            modelo = modelo_de(etiqueta)
            tabla = modelo._meta.db_table
            campos = list(modelo._meta.concrete_fields)
            columnas = ", ".join(f'"{c.column}"' for c in campos)
            filas = list(modelo.objects.order_by("pk").values_list(*[c.attname for c in campos]))
            resumen.append((tabla, len(filas)))
            lineas.append(f"-- {tabla}: {len(filas)} registros")
            for fila in filas:
                valores = ", ".join(
                    literal(v, es_json=c.get_internal_type() == "JSONField")
                    for c, v in zip(campos, fila, strict=True)
                )
                lineas.append(f'INSERT INTO "{tabla}" ({columnas}) VALUES ({valores});')
            lineas.append("")
        lineas.append("-- Ajuste de secuencias para continuar la numeración de los ids.")
        for tabla, _ in resumen:
            lineas.append(
                f"SELECT setval(pg_get_serial_sequence('\"{tabla}\"', 'id'), "
                f'(SELECT COALESCE(MAX("id"), 1) FROM "{tabla}"));'
            )
        lineas += ["", "COMMIT;", ""]
        salida = Path(opciones["salida"])
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text("\n".join(lineas), encoding="utf-8")
        for tabla, total in resumen:
            self.stdout.write(f"{tabla:<40}{total:>5}")
        self.stdout.write(self.style.SUCCESS(f"Script generado en {salida}"))
