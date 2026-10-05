# PRODUCT REQUIREMENTS DOCUMENT (PRD)

**PhishGuard – Plataforma Web de Concientización contra Phishing para CUREX, C.A.**
Documento de trabajo para el desarrollo con Claude Code · Versión 1.0 · 05/10/2026 · Autor: Jesús Antonio Leal Pérez

## 1. Resumen del producto

PhishGuard es una aplicación web que capacita al personal administrativo de CUREX, C.A. para reconocer y reportar correos fraudulentos (phishing). Combina cuatro capacidades: cursos cortos con evaluaciones, campañas de simulación de phishing controladas, un canal formal para reportar correos sospechosos y un panel de indicadores para el Departamento de Soporte Técnico y Sistemas.

**Problema que resuelve:** el personal abre los adjuntos de correos no deseados sin verificarlos, la empresa no ofrece capacitación en seguridad y los correos sospechosos se reportan por teléfono, sin registro ni seguimiento.

**Usuarios:** aproximadamente 120 trabajadores administrativos (Colaboradores) y 3 integrantes del Departamento de Soporte Técnico y Sistemas (Administradores).

## 2. Objetivos y métricas de éxito

- Tasa de clics en simulaciones: reducción de al menos 50 % entre la primera campaña (línea base) y la campaña de cierre.
- Tasa de reporte: al menos 30 % de los destinatarios de una campaña reporta el correo simulado a través de la plataforma.
- Cobertura de capacitación: al menos 80 % del personal completa el curso básico dentro de su fecha límite.
- Trazabilidad: 100 % de los reportes de correos sospechosos queda registrado con estado y fecha de atención.

## 3. Usuarios, roles y permisos

El sistema maneja exactamente dos roles. Todo acceso se valida en el servidor; ocultar un botón en la interfaz no se considera control de acceso.

| Funcionalidad | Administrador (Nivel 1) | Colaborador (Nivel 2) |
|---|---|---|
| Gestionar usuarios y departamentos | Sí | No |
| Crear, editar y asignar cursos y evaluaciones | Sí | No |
| Tomar cursos y presentar evaluaciones | Sí (vista previa) | Sí |
| Gestionar plantillas y campañas de simulación | Sí | No |
| Reportar correos sospechosos | Sí | Sí |
| Atender la bandeja de reportes | Sí | No |
| Ver el panel de indicadores de la organización | Sí | No |
| Ver su propio progreso, notas y certificados | Sí | Sí |
| Consultar la bitácora de acciones | Sí | No |

## 4. Alcance

### 4.1 Incluido en el prototipo (MVP)
- Autenticación funcional con dos roles, bloqueo por intentos fallidos y cierre de sesión por inactividad (RF-01 a RF-08, salvo la carga masiva por CSV).
- Cursos, lecciones, asignaciones, evaluaciones con calificación automática y progreso del Colaborador (RF-09 a RF-13).
- Plantillas y campañas de simulación, envío por lotes con enlace único, registro de aperturas y clics, y página educativa (RF-16 a RF-21).
- Formulario y bandeja de reportes de correos sospechosos (RF-22 a RF-25).
- Panel de indicadores con gráficos, bitácora de acciones y panel personal del Colaborador (RF-26, RF-27, RF-29 y RF-30).

### 4.2 Fase 2 (maquetado visualmente en el prototipo)
- Carga masiva de usuarios desde un archivo CSV (parte de RF-01).
- Certificado de aprobación en PDF (RF-14).
- Recordatorios automáticos por correo de cursos próximos a vencer (RF-15).
- Exportación de reportes en CSV y PDF (RF-28).

Estas funciones deben aparecer en la interfaz (botón o pantalla) con un aviso de «Próximamente», para que la navegación del prototipo quede completa.

### 4.3 Fuera de alcance
- Simulaciones por SMS, llamada telefónica o mensajería instantánea.
- Integración con el servidor de correo corporativo o con Active Directory.
- Análisis automático de malware en los archivos reportados.
- Aplicación móvil nativa (el sistema es web responsive).

## 5. Stack técnico y restricciones

- **Backend:** Python 3.12 y Django 5, con el sistema de autenticación integrado y un modelo de usuario personalizado.
- **Frontend:** plantillas de Django, HTML5, CSS3 y JavaScript sin empaquetador; Bootstrap 5, Bootstrap Icons, Chart.js y Quill desde CDN.
- **Base de datos:** PostgreSQL en Supabase, conectada mediante el agrupador de conexiones (puerto 6543) con dj-database-url y psycopg.
- **Archivos:** Supabase Storage para imágenes de lecciones y adjuntos de reportes; los archivos estáticos se sirven con WhiteNoise.
- **Despliegue:** Vercel con el entorno de ejecución de Python (interfaz WSGI) y despliegue automático desde la rama main de GitHub.
- **Correo:** envío por SMTP configurado con variables de entorno; en desarrollo se usa el backend de consola de Django.

### 5.1 Restricciones obligatorias del entorno serverless
- No usar Celery, Redis ni procesos en segundo plano. Las tareas programadas se ejecutan con Vercel Cron Jobs que llaman a un endpoint protegido con un token secreto.
- No escribir archivos en el disco local del servidor; todo archivo subido va a Supabase Storage.
- El envío de campañas se hace por lotes pequeños (por ejemplo, 20 correos por invocación) para no superar el tiempo máximo de ejecución de una función.
- Las sesiones se guardan en la base de datos, no en memoria.
- Las migraciones se ejecutan manualmente o en el pipeline, nunca en cada petición.

## 6. Modelo de datos

Modelos de Django por aplicación. Todos incluyen los campos `creado_en` y `actualizado_en`. Los nombres de modelos y campos se escriben en español, sin tildes.

| Aplicación | Modelo | Campos principales |
|---|---|---|
| usuarios | Departamento | nombre (único), activo |
| usuarios | Usuario (AbstractUser) | email (único, login), nombre_completo, rol (ADMIN/COLABORADOR), departamento (FK), intentos_fallidos, bloqueado_hasta |
| capacitacion | Curso | titulo, descripcion, estado (BORRADOR/PUBLICADO/ARCHIVADO), es_refuerzo, creado_por (FK) |
| capacitacion | Leccion | curso (FK), orden, titulo, contenido_html, video_url |
| capacitacion | Asignacion | curso (FK), usuario (FK), fecha_limite, origen (MANUAL/SIMULACION), completada_en |
| capacitacion | ProgresoLeccion | asignacion (FK), leccion (FK), completada_en |
| capacitacion | Evaluacion | curso (1:1), nota_minima, intentos_maximos |
| capacitacion | Pregunta / Opcion | evaluacion (FK), enunciado, orden / pregunta (FK), texto, es_correcta |
| capacitacion | Intento | evaluacion (FK), usuario (FK), nota, aprobado, respuestas (JSON) |
| simulaciones | PlantillaCorreo | nombre, asunto, remitente_visible, cuerpo_html, dificultad (BAJA/MEDIA/ALTA), tiene_formulario |
| simulaciones | Campana | nombre, plantilla (FK), fecha_envio, estado (PROGRAMADA/ENVIANDO/FINALIZADA), curso_refuerzo (FK) |
| simulaciones | Destinatario | campana (FK), usuario (FK), token (UUID, único), enviado_en |
| simulaciones | EventoSimulacion | destinatario (FK), tipo (APERTURA/CLIC/ENVIO_FORMULARIO/REPORTE), ocurrido_en, user_agent |
| reportes | ReporteSospechoso | reportado_por (FK), remitente, asunto, fecha_recepcion, adjunto_url, estado, comentario_admin, destinatario_sim (FK opcional) |
| panel | Bitacora | usuario (FK), accion, objeto, detalle (JSON), ip, ocurrido_en |

**Regla de privacidad:** EventoSimulacion nunca guarda lo que el usuario escribe en un formulario simulado; solo registra que hubo un envío.

## 7. Mapa de pantallas y rutas

| Ruta | Pantalla | Rol |
|---|---|---|
| /login/, /logout/, /recuperar/ | Inicio de sesión, cierre y recuperación de contraseña | Público |
| / | Redirección al panel según el rol | Ambos |
| /mi-panel/ | Panel personal: cursos asignados, notas, certificados y reportes | Colaborador |
| /cursos/&lt;id&gt;/ y /cursos/&lt;id&gt;/evaluacion/ | Lecciones del curso y evaluación | Colaborador |
| /reportar/ | Formulario de correo sospechoso | Ambos |
| /perfil/ | Edición de perfil y cambio de contraseña | Ambos |
| /admin-panel/ | Panel de indicadores con gráficos y filtros | Administrador |
| /admin-panel/usuarios/ y /departamentos/ | Gestión de usuarios y departamentos | Administrador |
| /admin-panel/cursos/ | Gestión de cursos, lecciones, evaluaciones y asignaciones | Administrador |
| /admin-panel/plantillas/ y /campanas/ | Plantillas y campañas de simulación con resultados | Administrador |
| /admin-panel/reportes/ | Bandeja de reportes de correos sospechosos | Administrador |
| /admin-panel/bitacora/ | Bitácora de acciones | Administrador |
| /s/&lt;token&gt;/ y /s/&lt;token&gt;/px.gif | Enlace de la simulación (clic) y píxel de apertura | Público |
| /aprende/&lt;token&gt;/ | Página educativa tras el clic | Público |
| /cron/enviar-campanas/ | Endpoint de envío por lotes (protegido con CRON_SECRET) | Vercel Cron |

El panel /admin/ nativo de Django queda disponible solo para superusuarios técnicos; la gestión diaria se hace desde /admin-panel/.

## 8. Requisitos funcionales y criterios de aceptación

Cada requisito se considera terminado cuando cumple su criterio de aceptación y tiene al menos una prueba automatizada.

### 8.1 Autenticación y gestión de usuarios
- **RF-01:** un correo fuera del dominio @curex.net.ve se rechaza con un mensaje claro. La carga por CSV se muestra como «Próximamente».
- **RF-02:** con credenciales válidas, el usuario llega a su panel; con credenciales inválidas, ve un mensaje genérico que no revela si el correo existe.
- **RF-03:** el enlace de recuperación expira en 1 hora y solo puede usarse una vez.
- **RF-04 y RF-05:** un Colaborador que escribe una URL de /admin-panel/ recibe un error 403. Se verifica con una prueba por cada vista administrativa.
- **RF-06:** el cambio de contraseña exige la contraseña actual y aplica los validadores de Django (mínimo 10 caracteres).
- **RF-07:** tras 15 minutos sin actividad, la siguiente petición redirige al login.
- **RF-08:** al quinto intento fallido la cuenta se bloquea 15 minutos y el evento queda en la bitácora.

### 8.2 Capacitación y evaluaciones
- **RF-09:** solo los cursos PUBLICADOS son visibles para los Colaboradores; el contenido HTML de Quill se sanea antes de guardarse.
- **RF-10:** asignar un curso a un departamento crea una asignación por cada usuario activo del departamento, sin duplicados.
- **RF-11:** el porcentaje de avance es igual a lecciones completadas entre lecciones totales.
- **RF-12 y RF-13:** la nota se calcula sobre 100; se respetan la nota mínima y el número máximo de intentos; aprobar marca la asignación como completada.
- **RF-14 y RF-15 (fase 2):** botón «Descargar certificado» y configuración de recordatorios visibles con aviso «Próximamente».

### 8.3 Simulación de phishing
- **RF-16:** la vista previa de la plantilla muestra el correo tal como lo verá el destinatario.
- **RF-17 y RF-18:** una campaña genera un Destinatario con token UUID por usuario; el cron envía como máximo 20 correos por invocación y marca la campaña como FINALIZADA al terminar.
- **RF-19:** el píxel registra la apertura una sola vez por destinatario; cada clic queda registrado con fecha y user agent.
- **RF-20:** el clic muestra la página educativa con las señales de la plantilla y crea una Asignacion del curso de refuerzo con origen SIMULACION.
- **RF-21:** una prueba confirma que el formulario simulado no guarda ningún valor escrito por el usuario.

### 8.4 Reporte de correos sospechosos
- **RF-22:** el adjunto acepta solo .png, .jpg, .pdf y .eml, de hasta 5 MB, y se sube a Supabase Storage.
- **RF-23:** el cambio de estado queda registrado en la bitácora con el administrador que lo hizo.
- **RF-24:** el Colaborador ve el nuevo estado en su panel y recibe un correo de notificación.
- **RF-25:** si el asunto y el remitente coinciden con una campaña activa enviada al usuario, se crea un EventoSimulacion de tipo REPORTE.

### 8.5 Panel de indicadores
- **RF-26:** tasa de clics = destinatarios con clic / destinatarios enviados; tasa de reporte = destinatarios con reporte / enviados; ambas filtrables por departamento y campaña.
- **RF-27:** gráfico de líneas con Chart.js que muestra la evolución por campaña.
- **RF-28 (fase 2):** botones de exportación visibles con aviso «Próximamente».
- **RF-29:** toda acción de creación, edición o eliminación hecha por un Administrador genera un registro en la bitácora.
- **RF-30:** el Colaborador solo ve sus propios datos; una prueba verifica que no puede consultar los de otro usuario.

## 9. Requisitos no funcionales clave
- **Seguridad:** contraseñas con PBKDF2-SHA256; DEBUG=False en producción; SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE y SESSION_COOKIE_HTTPONLY activados; protección CSRF en todos los formularios; el comando `manage.py check --deploy` no debe arrojar advertencias.
- **Rendimiento:** páginas en menos de 3 segundos y transacciones en menos de 2 segundos; índices en EventoSimulacion (destinatario, tipo).
- **Usabilidad y accesibilidad:** diseño responsive desde 360 px, menú distinto por rol, textos y mensajes en español, contraste y etiquetas según WCAG 2.1 AA.
- **Mantenibilidad:** PEP 8 verificado con ruff, docstrings en las funciones públicas y logs estructurados.

## 10. Estructura del repositorio

```
/phishguard/
├── CLAUDE.md
├── PRD.md
├── README.md
├── manage.py
├── requirements.txt
├── vercel.json
├── .env.example
├── phishguard/        (settings.py, urls.py, wsgi.py)
├── usuarios/          (modelos, vistas, forms, decoradores de rol, tests/)
├── capacitacion/
├── simulaciones/
├── reportes/
├── panel/
├── templates/         (base.html, base_admin.html, base_colaborador.html, una carpeta por app)
├── static/            (css/, js/, img/)
└── usuarios/management/commands/seed_demo.py
```

## 11. Variables de entorno (.env.example)

Ver `.env.example`. El archivo `.env` real nunca se sube al repositorio; debe estar en `.gitignore`. En Vercel, las variables se configuran en Project Settings → Environment Variables.

## 12. Plan de trabajo

| Fase / línea | Contenido | Depende de |
|---|---|---|
| Fase 0 – Base | Proyecto Django, settings por entorno, conexión a Supabase, vercel.json, Usuario y Departamento, RF-01 a RF-08, plantillas base por rol, @admin_requerido, Bitacora, seed_demo | — |
| Línea A – Capacitación | App capacitacion: RF-09 a RF-15 | Fase 0 |
| Línea B – Simulaciones | App simulaciones: RF-16 a RF-21 | Fase 0; Asignacion (RF-20) |
| Línea C – Reportes | App reportes: RF-22 a RF-25 | Fase 0; Destinatario (RF-25) |
| Fase final – Panel e integración | App panel: RF-26 a RF-30, pruebas E2E, check --deploy, despliegue | A, B y C en main |

### 12.1 Cómo ejecutarlo
- Completar y fusionar la Fase 0 en main antes de abrir las líneas.
- Definir primero los modelos compartidos (Asignacion, Destinatario y EventoSimulacion) en un único commit de «contratos».
- Cada línea solo genera migraciones de su propia app. Antes de fusionar: `makemigrations --check` y suite de pruebas completa.
- Fusionar en orden A → B → C y luego abrir la fase final.

## 13. Definición de terminado
- Cumple los criterios de aceptación de sus RF y tiene pruebas con el TestCase de Django que pasan con `python manage.py test`.
- Las vistas administrativas tienen una prueba que confirma el error 403 para el Colaborador.
- Funciona en 360 px y en 1920 px, sin errores en la consola del navegador.
- `ruff check` sin errores y sin credenciales en el código.
- Commit con mensaje que cite el RF, por ejemplo: «feat(simulaciones): RF-19 registro de aperturas».
- README actualizado si cambian la instalación o las variables de entorno.

## 14. Entregables (Anexo B)
- ZIP `PhishGuard_Prototipo_[DDMMAAAA].zip` con código, recursos, migraciones, seed_demo y documentación.
- README.txt con instrucciones de instalación y ejecución paso a paso.
- Credenciales de prueba creadas por `seed_demo` (admin.demo@curex.net.ve y colaborador.demo@curex.net.ve) y enlace al repositorio de GitHub.
- Capturas de pantalla para el Anexo A.

## 15. Reglas para Claude Code
Ver `CLAUDE.md`.
