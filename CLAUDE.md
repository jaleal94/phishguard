# CLAUDE.md – Reglas para Claude Code (PhishGuard)

- Lee `PRD.md` antes de cada tarea y trabaja solo en la línea o RF indicado.
- Toda la interfaz, los mensajes y los comentarios van en español; los nombres de modelos y campos, en español y sin tildes.
- Respeta las restricciones serverless de la sección 5: sin Celery, sin escritura en disco y con envío por lotes.
- Toda vista nueva lleva `@login_required` y, si es administrativa, `@admin_requerido`, además de su prueba de error 403.
- Nunca guardes contraseñas ni datos escritos en las páginas de simulación.
- No subas secretos al código; usa variables de entorno y actualiza `.env.example`.
- Antes de terminar una tarea, ejecuta `python manage.py test` y `ruff check`, y resume qué RF quedaron cubiertos.
- No modifiques migraciones de otras apps ni hagas cambios fuera del alcance pedido; si algo del PRD es ambiguo, pregunta.

## Decisiones técnicas acordadas (Fase 0)

- Django 5.2 LTS (compatible con Python 3.12 en Vercel y 3.14 en local).
- Sin `DATABASE_URL` se usa SQLite (desarrollo y pruebas); en producción, PostgreSQL de Supabase por el pooler (puerto 6543).
- `Bitacora` vive en la app `panel`; se registra con `panel.bitacora.registrar(...)`.
- Todos los modelos heredan de `usuarios.models.ModeloBase` (`creado_en`, `actualizado_en`).
- Vistas administrativas: decorador `usuarios.decoradores.admin_requerido` (incluye `login_required` y responde 403).
- Supabase Storage se usa vía API REST con `requests` (sin SDK).
- Estados de `ReporteSospechoso`: PENDIENTE / EN_REVISION / PHISHING_CONFIRMADO / FALSO_POSITIVO.

## Comandos

```
.venv/Scripts/python manage.py test
.venv/Scripts/ruff check .
.venv/Scripts/python manage.py seed_demo
```
