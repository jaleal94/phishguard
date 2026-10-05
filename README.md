# PhishGuard

Plataforma web de concientización contra phishing para CUREX, C.A.: cursos con evaluaciones, campañas de simulación de phishing, reporte de correos sospechosos y panel de indicadores.

**Stack:** Python 3.12 · Django 5.2 · PostgreSQL (Supabase) · Bootstrap 5 · Vercel.

**Producción:** https://phishguard-omega-nine.vercel.app · **Repositorio:** https://github.com/jaleal94/phishguard

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

Las credenciales anteriores son solo para el entorno local. En producción las cuentas demo usan
otra contraseña, que se entrega por separado.

En desarrollo los correos (por ejemplo, la recuperación de contraseña) se imprimen en la consola.

## Pruebas y calidad

```bash
python manage.py test
ruff check .
python manage.py check --deploy   # con DJANGO_DEBUG=False
```

## Despliegue en Vercel

1. Crear el proyecto en Supabase y copiar la cadena del **pooler** (puerto 6543) en `DATABASE_URL`.
2. En Supabase Storage crear dos buckets: `phishguard` (**privado**, adjuntos de reportes) y
   `phishguard-publico` (**público**, imágenes de lecciones).
3. Ejecutar las migraciones contra Supabase desde su equipo (nunca en cada petición):
   `DATABASE_URL=... python manage.py migrate` y luego `python manage.py seed_demo`.
4. Importar el repositorio de GitHub en Vercel y configurar las variables de `.env.example` en
   *Project Settings → Environment Variables* (`DJANGO_DEBUG=False`).
5. Cada push a `main` despliega automáticamente.
6. **Seguridad de Supabase:** active RLS (Row Level Security) en todas las tablas del esquema
   `public` para que la API REST pública de Supabase no exponga datos. Django no se ve afectado
   porque se conecta como dueño de las tablas. Repítalo cada vez que una migración cree tablas nuevas:
   `ALTER TABLE public.<tabla> ENABLE ROW LEVEL SECURITY;`

## Estructura

| App | Responsabilidad |
|---|---|
| `usuarios` | Usuario, Departamento, autenticación (RF-01 a RF-08), decorador `@admin_requerido`, `seed_demo` |
| `capacitacion` | Cursos, lecciones, evaluaciones y asignaciones (RF-09 a RF-15) |
| `simulaciones` | Plantillas, campañas, píxel, clics y página educativa (RF-16 a RF-21) |
| `reportes` | Reporte de correos sospechosos y bandeja (RF-22 a RF-25) |
| `panel` | Indicadores, bitácora y panel personal (RF-26 a RF-30) |
