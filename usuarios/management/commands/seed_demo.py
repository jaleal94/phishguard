"""Comando para cargar datos de demostración (departamentos y usuarios de prueba)."""

from django.core.management.base import BaseCommand
from django.db import transaction

from capacitacion import demo as demo_capacitacion
from capacitacion import demo_extra as demo_capacitacion_extra
from panel.bitacora import registrar
from reportes import demo as demo_reportes
from simulaciones import demo as demo_simulaciones
from usuarios.models import Departamento, Usuario

DEPARTAMENTOS = [
    "Administración",
    "Contabilidad",
    "Compras",
    "Recursos Humanos",
    "Ventas",
    "Soporte Técnico y Sistemas",
]

COLABORADORES = [
    ("maria.gonzalez", "María González", "Administración"),
    ("jose.rodriguez", "José Rodríguez", "Administración"),
    ("ana.martinez", "Ana Martínez", "Contabilidad"),
    ("carlos.perez", "Carlos Pérez", "Contabilidad"),
    ("luisa.hernandez", "Luisa Hernández", "Compras"),
    ("pedro.ramirez", "Pedro Ramírez", "Compras"),
    ("carmen.torres", "Carmen Torres", "Recursos Humanos"),
    ("miguel.flores", "Miguel Flores", "Recursos Humanos"),
    ("rosa.morales", "Rosa Morales", "Ventas"),
    ("andres.castillo", "Andrés Castillo", "Ventas"),
]

CLAVE_DEMO = "PhishGuard.Demo2026"


class Command(BaseCommand):
    help = "Crea departamentos y usuarios de demostración (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=CLAVE_DEMO,
            help="Contraseña para los usuarios de demostración.",
        )

    @transaction.atomic
    def handle(self, *args, **opciones):
        clave = opciones["password"]
        origen = {"origen": "seed_demo"}
        deptos = {}
        for nombre in DEPARTAMENTOS:
            deptos[nombre], nuevo = Departamento.objects.get_or_create(nombre=nombre)
            if nuevo:
                registrar("CREAR_DEPARTAMENTO", objeto=nombre, detalle=origen)

        cuentas = [
            ("admin.demo", "Administrador Demo", "Soporte Técnico y Sistemas", Usuario.Rol.ADMIN),
            ("colaborador.demo", "Colaborador Demo", "Contabilidad", Usuario.Rol.COLABORADOR),
        ] + [(u, n, d, Usuario.Rol.COLABORADOR) for u, n, d in COLABORADORES]

        creados = 0
        for usuario, nombre, depto, rol in cuentas:
            email = f"{usuario}@curex.net.ve"
            obj = Usuario.objects.filter(email=email).first()
            if obj is None:
                Usuario.objects.create_user(
                    email=email,
                    password=clave,
                    nombre_completo=nombre,
                    departamento=deptos[depto],
                    rol=rol,
                )
                registrar("CREAR_USUARIO", objeto=email, detalle={**origen, "rol": rol})
                creados += 1

        admin = Usuario.objects.get(email="admin.demo@curex.net.ve")
        asignaciones = demo_capacitacion.cargar(
            admin, Usuario.objects.filter(rol=Usuario.Rol.COLABORADOR)
        )

        demo_capacitacion_extra.cargar(admin)
        reportes = demo_reportes.cargar(admin)
        campanas = demo_simulaciones.cargar(admin)
        if creados or asignaciones or reportes or campanas:
            registrar(
                "CARGA_DATOS_DEMO",
                usuario=admin,
                objeto="seed_demo",
                detalle={"usuarios": creados, "asignaciones": asignaciones,
                         "reportes": reportes, "campanas": campanas},
            )

        mensaje = (
            f"Datos de demostración listos ({creados} usuarios, {asignaciones} asignaciones "
            f"y {reportes} reportes nuevos)."
        )
        self.stdout.write(self.style.SUCCESS(mensaje))
        self.stdout.write("Credenciales de prueba:")
        self.stdout.write(f"  Administrador: admin.demo@curex.net.ve / {clave}")
        self.stdout.write(f"  Colaborador:   colaborador.demo@curex.net.ve / {clave}")
