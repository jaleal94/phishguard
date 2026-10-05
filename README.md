# PhishGuard

Plataforma web de concientización contra phishing para CUREX, C.A.: cursos con evaluaciones, campañas de simulación de phishing, reporte de correos sospechosos y panel de indicadores.

**Stack:** Python 3.12 · Django 5.2 · PostgreSQL (Supabase) · Bootstrap 5 · Vercel.

## Instalación local

```bash
# 1. Entorno virtual y dependencias
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
pip install ruff

# 2. Variables de entorno
copy .env.example .env          # Linux/macOS: cp .env.example .env
#   Para desarrollo: DJANGO_DEBUG=True y DATABASE_URL vacío (usa SQLite).

# 3. Base de datos y datos de demostración
python manage.py migrate
python manage.py seed_demo

# 4. Servidor de desarrollo
python manage.py runserver
```

Abra http://localhost:8000/ e inicie sesión con:

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | admin.demo@curex.net.ve | PhishGuard.Demo2026 |
| Colaborador | colaborador.demo@curex.net.ve | PhishGuard.Demo2026 |

En desarrollo los correos (por ejemplo, la recuperación de contraseña) se imprimen en la consola.

## Pruebas y calidad

```bash
python manage.py test
ruff check .
python manage.py check --deploy   # con DJANGO_DEBUG=False
```

## Despliegue en Vercel

1. Crear el proyecto en Supabase y copiar la cadena del **pooler** (puerto 6543) en `DATABASE_URL`.
2. Ejecutar las migraciones contra Supabase desde su equipo (nunca en cada petición):
   `DATABASE_URL=... python manage.py migrate` y luego `python manage.py seed_demo`.
3. Importar el repositorio de GitHub en Vercel y configurar las variables de `.env.example` en
   *Project Settings → Environment Variables* (`DJANGO_DEBUG=False`).
4. Cada push a `main` despliega automáticamente.

## Estructura

| App | Responsabilidad |
|---|---|
| `usuarios` | Usuario, Departamento, autenticación (RF-01 a RF-08), decorador `@admin_requerido`, `seed_demo` |
| `capacitacion` | Cursos, lecciones, evaluaciones y asignaciones (RF-09 a RF-15) |
| `simulaciones` | Plantillas, campañas, píxel, clics y página educativa (RF-16 a RF-21) |
| `reportes` | Reporte de correos sospechosos y bandeja (RF-22 a RF-25) |
| `panel` | Indicadores, bitácora y panel personal (RF-26 a RF-30) |

Las especificaciones completas están en `PRD.md` y las reglas de desarrollo en `CLAUDE.md`.
