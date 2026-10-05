"""Vistas de autenticación, perfil y gestión de usuarios y departamentos."""

import time

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from panel.bitacora import registrar

from .decoradores import admin_requerido
from .forms import (
    DepartamentoForm,
    LoginForm,
    PerfilForm,
    UsuarioCrearForm,
    UsuarioEditarForm,
)
from .middleware import CLAVE_ACTIVIDAD
from .models import Departamento, Usuario


def login_vista(request):
    """RF-02: inicio de sesión con correo corporativo y contraseña."""
    if request.user.is_authenticated:
        return redirect("inicio")
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.usuario
        login(request, usuario)
        request.session[CLAVE_ACTIVIDAD] = int(time.time())
        registrar("INICIO_SESION", usuario=usuario, objeto=usuario.email, request=request)
        destino = request.POST.get("next") or request.GET.get("next")
        if destino and url_has_allowed_host_and_scheme(
            destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(destino)
        return redirect("inicio")
    return render(
        request, "usuarios/login.html", {"form": form, "next": request.GET.get("next", "")}
    )


@login_required
def inicio(request):
    """Redirige al panel que corresponde al rol del usuario."""
    if request.user.es_admin:
        return redirect("panel:admin_panel")
    return redirect("panel:mi_panel")


@login_required
def perfil(request):
    """RF-06: edición de perfil y cambio de contraseña con la contraseña actual."""
    form_perfil = PerfilForm(instance=request.user)
    form_clave = PasswordChangeForm(request.user)
    if request.method == "POST":
        if request.POST.get("accion") == "clave":
            form_clave = PasswordChangeForm(request.user, request.POST)
            if form_clave.is_valid():
                usuario = form_clave.save()
                update_session_auth_hash(request, usuario)
                registrar("CAMBIO_CONTRASENA", objeto=usuario.email, request=request)
                messages.success(request, "Su contraseña se actualizó correctamente.")
                return redirect("usuarios:perfil")
        else:
            form_perfil = PerfilForm(request.POST, instance=request.user)
            if form_perfil.is_valid():
                form_perfil.save()
                messages.success(request, "Sus datos se actualizaron correctamente.")
                return redirect("usuarios:perfil")
    return render(
        request,
        "usuarios/perfil.html",
        {"form_perfil": form_perfil, "form_clave": form_clave},
    )


# --- Gestión de usuarios (Administrador) ---------------------------------------------


def _cambios(form):
    """Devuelve los campos modificados de un ModelForm para la bitácora."""
    return {campo: str(form.cleaned_data.get(campo)) for campo in form.changed_data}


@admin_requerido
def usuarios_lista(request):
    """Lista de usuarios con búsqueda y filtros por departamento y rol."""
    usuarios = Usuario.objects.select_related("departamento")
    q = request.GET.get("q", "").strip()
    if q:
        usuarios = usuarios.filter(Q(nombre_completo__icontains=q) | Q(email__icontains=q))
    departamento = request.GET.get("departamento", "")
    if departamento.isdigit():
        usuarios = usuarios.filter(departamento_id=departamento)
    rol = request.GET.get("rol", "")
    if rol in Usuario.Rol.values:
        usuarios = usuarios.filter(rol=rol)
    pagina = Paginator(usuarios, 20).get_page(request.GET.get("pagina"))
    return render(
        request,
        "usuarios/usuarios_lista.html",
        {
            "pagina": pagina,
            "departamentos": Departamento.objects.all(),
            "roles": Usuario.Rol.choices,
            "filtros": {"q": q, "departamento": departamento, "rol": rol},
        },
    )


@admin_requerido
def usuario_crear(request):
    """Alta de un usuario (RF-01)."""
    form = UsuarioCrearForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        registrar(
            "CREAR_USUARIO",
            objeto=usuario.email,
            detalle={"rol": usuario.rol, "departamento": str(usuario.departamento or "")},
            request=request,
        )
        messages.success(request, f"Usuario {usuario.email} creado correctamente.")
        return redirect("usuarios:usuarios_lista")
    return render(request, "usuarios/usuario_form.html", {"form": form, "titulo": "Nuevo usuario"})


@admin_requerido
def usuario_editar(request, pk):
    """Edición de un usuario existente."""
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioEditarForm(request.POST or None, instance=usuario, editor=request.user)
    if request.method == "POST" and form.is_valid():
        cambios = _cambios(form)
        form.save()
        if cambios:
            registrar("EDITAR_USUARIO", objeto=usuario.email, detalle=cambios, request=request)
        messages.success(request, f"Usuario {usuario.email} actualizado.")
        return redirect("usuarios:usuarios_lista")
    return render(
        request,
        "usuarios/usuario_form.html",
        {"form": form, "titulo": f"Editar usuario: {usuario.nombre_completo}", "objeto": usuario},
    )


@admin_requerido
@require_POST
def usuario_desbloquear(request, pk):
    """Levanta el bloqueo por intentos fallidos de un usuario."""
    usuario = get_object_or_404(Usuario, pk=pk)
    usuario.bloqueado_hasta = None
    usuario.intentos_fallidos = 0
    usuario.save(update_fields=["bloqueado_hasta", "intentos_fallidos"])
    registrar("DESBLOQUEAR_USUARIO", objeto=usuario.email, request=request)
    messages.success(request, f"Se desbloqueó la cuenta de {usuario.email}.")
    return redirect("usuarios:usuarios_lista")


@admin_requerido
def usuarios_importar(request):
    """Carga masiva por CSV (fase 2): pantalla «Próximamente»."""
    return render(
        request,
        "comun/proximamente.html",
        {
            "titulo": "Carga masiva de usuarios (CSV)",
            "descripcion": "Permitirá registrar usuarios en lote a partir de un archivo CSV.",
            "volver": "usuarios:usuarios_lista",
        },
    )


# --- Gestión de departamentos (Administrador) ----------------------------------------


@admin_requerido
def departamentos_lista(request):
    """Lista de departamentos con su cantidad de usuarios."""
    departamentos = Departamento.objects.annotate(total_usuarios=Count("usuarios"))
    return render(request, "usuarios/departamentos_lista.html", {"departamentos": departamentos})


@admin_requerido
def departamento_crear(request):
    """Alta de un departamento."""
    form = DepartamentoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        departamento = form.save()
        registrar("CREAR_DEPARTAMENTO", objeto=departamento.nombre, request=request)
        messages.success(request, f"Departamento «{departamento.nombre}» creado.")
        return redirect("usuarios:departamentos_lista")
    return render(
        request, "usuarios/departamento_form.html", {"form": form, "titulo": "Nuevo departamento"}
    )


@admin_requerido
def departamento_editar(request, pk):
    """Edición de un departamento."""
    departamento = get_object_or_404(Departamento, pk=pk)
    form = DepartamentoForm(request.POST or None, instance=departamento)
    if request.method == "POST" and form.is_valid():
        cambios = _cambios(form)
        form.save()
        if cambios:
            registrar(
                "EDITAR_DEPARTAMENTO", objeto=departamento.nombre, detalle=cambios, request=request
            )
        messages.success(request, f"Departamento «{departamento.nombre}» actualizado.")
        return redirect("usuarios:departamentos_lista")
    return render(
        request,
        "usuarios/departamento_form.html",
        {"form": form, "titulo": f"Editar departamento: {departamento.nombre}"},
    )


@admin_requerido
@require_POST
def departamento_eliminar(request, pk):
    """Elimina un departamento solo si no tiene usuarios asociados."""
    departamento = get_object_or_404(Departamento, pk=pk)
    if departamento.usuarios.exists():
        messages.error(
            request,
            f"No se puede eliminar «{departamento.nombre}» porque tiene usuarios. "
            "Puede desactivarlo en su lugar.",
        )
    else:
        nombre = departamento.nombre
        departamento.delete()
        registrar("ELIMINAR_DEPARTAMENTO", objeto=nombre, request=request)
        messages.success(request, f"Departamento «{nombre}» eliminado.")
    return redirect("usuarios:departamentos_lista")
