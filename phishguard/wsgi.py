"""Punto de entrada WSGI de PhishGuard (usado por Vercel y servidores WSGI)."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "phishguard.settings")

application = get_wsgi_application()

# El entorno de ejecución de Python de Vercel busca una variable llamada «app».
app = application
