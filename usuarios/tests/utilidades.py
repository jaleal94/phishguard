"""Utilidades compartidas por las pruebas."""

from usuarios.models import Departamento, Usuario

CLAVE = "ClaveSegura.2026"


def crear_usuario(email="colaborador@curex.net.ve", rol=Usuario.Rol.COLABORADOR, **campos):
    """Crea un usuario de prueba con la contraseña CLAVE."""
    campos.setdefault("nombre_completo", "Usuario Prueba")
    return Usuario.objects.create_user(email=email, password=CLAVE, rol=rol, **campos)


def crear_admin(email="admin@curex.net.ve", **campos):
    """Crea un Administrador de prueba."""
    campos.setdefault("nombre_completo", "Admin Prueba")
    return crear_usuario(email=email, rol=Usuario.Rol.ADMIN, **campos)


def crear_departamento(nombre="Contabilidad"):
    """Crea un departamento de prueba."""
    return Departamento.objects.create(nombre=nombre)
