"""Formularios de autenticación, perfil y gestión de usuarios."""

from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, password_validation
from django.db.models import F
from django.utils import timezone

from panel.bitacora import registrar

from .models import Departamento, Usuario, validar_dominio_corporativo

MENSAJE_LOGIN_GENERICO = (
    "Credenciales inválidas o cuenta bloqueada temporalmente. "
    "Verifique sus datos o intente de nuevo en unos minutos."
)


class LoginForm(forms.Form):
    """Inicio de sesión por correo (RF-02) con bloqueo por intentos fallidos (RF-08).

    Todos los fallos muestran el mismo mensaje genérico para no revelar si el
    correo existe ni si la cuenta está bloqueada.
    """

    email = forms.EmailField(
        label="Correo corporativo",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.usuario = None
        super().__init__(*args, **kwargs)

    def clean(self):
        datos = super().clean()
        email = (datos.get("email") or "").strip().lower()
        password = datos.get("password")
        if not email or not password:
            return datos

        candidato = Usuario.objects.filter(email__iexact=email).first()
        if candidato and candidato.esta_bloqueado:
            raise forms.ValidationError(MENSAJE_LOGIN_GENERICO, code="invalido")

        usuario = authenticate(self.request, username=email, password=password)
        if usuario is None:
            if candidato and candidato.is_active:
                self._registrar_fallo(candidato)
            raise forms.ValidationError(MENSAJE_LOGIN_GENERICO, code="invalido")

        if usuario.intentos_fallidos or usuario.bloqueado_hasta:
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
        self.usuario = usuario
        return datos

    def _registrar_fallo(self, usuario):
        """Suma un intento fallido y bloquea la cuenta al llegar al máximo (RF-08)."""
        Usuario.objects.filter(pk=usuario.pk).update(intentos_fallidos=F("intentos_fallidos") + 1)
        usuario.refresh_from_db(fields=["intentos_fallidos"])
        if usuario.intentos_fallidos >= settings.MAX_INTENTOS_FALLIDOS:
            usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=settings.MINUTOS_BLOQUEO)
            usuario.intentos_fallidos = 0
            usuario.save(update_fields=["bloqueado_hasta", "intentos_fallidos"])
            registrar(
                "BLOQUEO_CUENTA",
                usuario=usuario,
                objeto=usuario.email,
                detalle={
                    "motivo": f"{settings.MAX_INTENTOS_FALLIDOS} intentos fallidos",
                    "bloqueado_hasta": usuario.bloqueado_hasta.isoformat(),
                },
                request=self.request,
            )


class PerfilForm(forms.ModelForm):
    """Edición de los datos propios del usuario (el correo y el rol no son editables)."""

    class Meta:
        model = Usuario
        fields = ["nombre_completo"]


class EmailCorporativoMixin:
    """Valida dominio corporativo y unicidad del correo sin distinguir mayúsculas."""

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        validar_dominio_corporativo(email)
        existentes = Usuario.objects.filter(email__iexact=email)
        if self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise forms.ValidationError("Ya existe un usuario con este correo.")
        return email


class UsuarioCrearForm(EmailCorporativoMixin, forms.ModelForm):
    """Alta de usuario por un Administrador, con contraseña inicial."""

    password1 = forms.CharField(
        label="Contraseña inicial",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Mínimo 10 caracteres; no puede ser común ni solo numérica.",
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = Usuario
        fields = ["email", "nombre_completo", "rol", "departamento", "is_active"]
        labels = {"is_active": "Activo"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["departamento"].queryset = Departamento.objects.filter(activo=True)

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get("password1"), datos.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        elif p1:
            try:
                password_validation.validate_password(p1, self.instance)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario


class UsuarioEditarForm(EmailCorporativoMixin, forms.ModelForm):
    """Edición de un usuario por un Administrador."""

    class Meta:
        model = Usuario
        fields = ["email", "nombre_completo", "rol", "departamento", "is_active"]
        labels = {"is_active": "Activo"}

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor
        self.fields["departamento"].queryset = Departamento.objects.filter(activo=True) | (
            Departamento.objects.filter(pk=self.instance.departamento_id)
        )

    def clean(self):
        datos = super().clean()
        if self.editor and self.editor.pk == self.instance.pk:
            if datos.get("rol") != Usuario.Rol.ADMIN:
                self.add_error("rol", "No puede quitarse a sí mismo el rol de Administrador.")
            if not datos.get("is_active"):
                self.add_error("is_active", "No puede desactivar su propia cuenta.")
        return datos


class DepartamentoForm(forms.ModelForm):
    """Alta y edición de departamentos."""

    class Meta:
        model = Departamento
        fields = ["nombre", "activo"]
