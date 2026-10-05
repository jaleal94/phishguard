"""Modelos de usuarios y departamentos."""

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ModeloBase(models.Model):
    """Modelo abstracto con marcas de tiempo de creación y actualización."""

    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        abstract = True


def validar_dominio_corporativo(email):
    """RF-01: solo se aceptan correos del dominio corporativo."""
    dominio = settings.DOMINIO_CORPORATIVO
    if not email or not email.strip().lower().endswith(f"@{dominio}"):
        raise ValidationError(
            f"Solo se permiten correos del dominio @{dominio}.", code="dominio_invalido"
        )


class Departamento(ModeloBase):
    """Unidad organizativa de CUREX, C.A."""

    nombre = models.CharField("nombre", max_length=120, unique=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "departamento"
        verbose_name_plural = "departamentos"

    def __str__(self):
        return self.nombre


class UsuarioManager(BaseUserManager):
    """Manager que usa el correo electrónico como identificador de inicio de sesión."""

    use_in_migrations = True

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)

    def _crear(self, email, password, **campos):
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")
        email = self.normalize_email(email).lower()
        validar_dominio_corporativo(email)
        usuario = self.model(email=email, **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **campos):
        campos.setdefault("rol", Usuario.Rol.COLABORADOR)
        campos.setdefault("is_staff", False)
        campos.setdefault("is_superuser", False)
        return self._crear(email, password, **campos)

    def create_superuser(self, email, password=None, **campos):
        campos.setdefault("rol", Usuario.Rol.ADMIN)
        campos["is_staff"] = True
        campos["is_superuser"] = True
        return self._crear(email, password, **campos)


class Usuario(AbstractUser, ModeloBase):
    """Usuario de PhishGuard: Administrador (nivel 1) o Colaborador (nivel 2)."""

    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        COLABORADOR = "COLABORADOR", "Colaborador"

    username = None
    first_name = None
    last_name = None

    email = models.EmailField(
        "correo electrónico", unique=True, validators=[validar_dominio_corporativo]
    )
    nombre_completo = models.CharField("nombre completo", max_length=150)
    rol = models.CharField("rol", max_length=12, choices=Rol.choices, default=Rol.COLABORADOR)
    departamento = models.ForeignKey(
        Departamento,
        verbose_name="departamento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios",
    )
    intentos_fallidos = models.PositiveSmallIntegerField("intentos fallidos", default=0)
    bloqueado_hasta = models.DateTimeField("bloqueado hasta", null=True, blank=True)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nombre_completo"]

    objects = UsuarioManager()

    class Meta:
        ordering = ["nombre_completo"]
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return f"{self.nombre_completo} <{self.email}>"

    def get_full_name(self):
        return self.nombre_completo

    def get_short_name(self):
        return self.nombre_completo.split(" ")[0] if self.nombre_completo else self.email

    @property
    def es_admin(self):
        """Indica si el usuario tiene el rol de Administrador."""
        return self.rol == self.Rol.ADMIN

    @property
    def esta_bloqueado(self):
        """Indica si la cuenta está bloqueada temporalmente por intentos fallidos (RF-08)."""
        return bool(self.bloqueado_hasta and self.bloqueado_hasta > timezone.now())
