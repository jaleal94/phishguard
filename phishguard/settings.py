"""Configuración de PhishGuard.

Todos los valores sensibles o dependientes del entorno se leen de variables de
entorno (ver .env.example). En local se cargan desde un archivo .env.
"""

import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(nombre, defecto=False):
    """Lee una variable de entorno booleana."""
    valor = os.environ.get(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in {"1", "true", "si", "sí", "yes", "on"}


def _lista(nombre, defecto=""):
    """Lee una variable de entorno separada por comas."""
    return [v.strip() for v in os.environ.get(nombre, defecto).split(",") if v.strip()]


EJECUTANDO_PRUEBAS = len(sys.argv) > 1 and sys.argv[1] == "test"

DEBUG = _bool("DJANGO_DEBUG", False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG or EJECUTANDO_PRUEBAS:
        SECRET_KEY = "clave-solo-para-desarrollo-no-usar-en-produccion"
    else:
        raise RuntimeError("Falta la variable de entorno DJANGO_SECRET_KEY.")

ALLOWED_HOSTS = _lista("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = _lista("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "usuarios",
    "capacitacion",
    "simulaciones",
    "reportes",
    "panel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "usuarios.middleware.InactividadMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "phishguard.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "usuarios.context_processors.plantilla_base",
            ],
        },
    },
]

WSGI_APPLICATION = "phishguard.wsgi.application"

# Base de datos: PostgreSQL de Supabase (pooler, puerto 6543) o SQLite local.
_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if _DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(_DATABASE_URL, conn_max_age=0)}
else:
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }
if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    # El pooler en modo transacción no admite sentencias preparadas ni cursores de servidor.
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].update({"sslmode": "require", "prepare_threshold": None})
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

AUTH_USER_MODEL = "usuarios.Usuario"
DOMINIO_CORPORATIVO = "curex.net.ve"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "usuarios:login"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "usuarios:login"

# RF-03: el enlace de recuperación expira en 1 hora.
PASSWORD_RESET_TIMEOUT = 60 * 60

# RF-07 y RF-08
INACTIVIDAD_SEGUNDOS = 15 * 60
MAX_INTENTOS_FALLIDOS = 5
MINUTOS_BLOQUEO = 15

# Sesiones en base de datos (entorno serverless).
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Caracas"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# Sin escritura en disco: los archivos subidos se procesan en memoria y van a Supabase Storage.
FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.MemoryFileUploadHandler"]
# En Vercel no se ejecuta collectstatic: WhiteNoise sirve directamente desde las carpetas static.
WHITENOISE_USE_FINDERS = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Correo: SMTP si hay EMAIL_HOST; si no, se imprime en consola.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = _bool("EMAIL_USE_TLS", True)
    EMAIL_TIMEOUT = 10
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "PhishGuard <no-responder@curex.net.ve>")

# Integraciones
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "phishguard")
SUPABASE_BUCKET_PUBLICO = os.environ.get("SUPABASE_BUCKET_PUBLICO", "phishguard-publico")
CRON_SECRET = os.environ.get("CRON_SECRET", "")
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000").rstrip("/")

# Seguridad en producción (RNF de seguridad; check --deploy sin advertencias).
if not DEBUG and not EJECUTANDO_PRUEBAS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Logs estructurados (una línea JSON por evento) hacia la salida estándar.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "phishguard.logs.FormateadorJSON"}},
    "handlers": {"consola": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["consola"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["consola"], "level": "WARNING", "propagate": False},
    },
}
if EJECUTANDO_PRUEBAS:
    LOGGING["root"]["level"] = "CRITICAL"
    LOGGING["loggers"]["django"]["level"] = "CRITICAL"

MESSAGE_TAGS = {40: "danger"}  # messages.ERROR -> clase «danger» de Bootstrap
