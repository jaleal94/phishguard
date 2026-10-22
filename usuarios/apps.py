from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"
    verbose_name = "usuarios"

    def ready(self):
        from . import signals  # noqa: F401  (registra los receptores de señales)
