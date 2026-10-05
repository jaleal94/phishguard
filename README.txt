===============================================================================
 PHISHGUARD - Plataforma web de concientización contra phishing
 CUREX, C.A.
 Prototipo funcional · Autor: Jesús Antonio Leal Pérez · Octubre 2026
===============================================================================

ENLACES
-------
  Sitio en producción : https://phishguard-omega-nine.vercel.app
  Repositorio GitHub  : https://github.com/jaleal94/phishguard

  Las credenciales del sitio en producción están en el archivo CREDENCIALES.txt
  incluido en el ZIP de entrega. No se publican en el repositorio.


1. DESCRIPCIÓN
--------------
PhishGuard capacita al personal administrativo de CUREX, C.A. para reconocer y
reportar correos fraudulentos (phishing). El prototipo incluye:

  - Autenticación real contra la base de datos, con dos niveles de usuario:
      Nivel 1: Administrador (Departamento de Soporte Técnico y Sistemas)
      Nivel 2: Colaborador (personal administrativo)
  - Cursos con lecciones, evaluaciones con calificación automática y progreso.
  - Canal formal para reportar correos sospechosos y bandeja de atención.
  - Panel de indicadores con gráfico y bitácora de acciones.

Tecnologías: Python 3.12, Django 5.2, PostgreSQL (Supabase), Bootstrap 5,
Chart.js, Quill, WhiteNoise. Despliegue en Vercel.


2. REQUISITOS PREVIOS
---------------------
  - Python 3.12 o superior (https://www.python.org/downloads/)
    En Windows, marque «Add python.exe to PATH» durante la instalación.
  - Conexión a internet (Bootstrap, Chart.js y Quill se cargan desde CDN).
  - No se necesita instalar PostgreSQL: en local se usa SQLite automáticamente.


3. INSTALACIÓN Y EJECUCIÓN LOCAL (PASO A PASO)
----------------------------------------------
Abra una terminal (Windows: PowerShell; Linux/macOS: Terminal) dentro de la
carpeta del proyecto (donde está el archivo manage.py).

  Paso 1. Crear el entorno virtual
      Windows       : python -m venv .venv
      Linux/macOS   : python3 -m venv .venv

  Paso 2. Activar el entorno virtual
      Windows       : .venv\Scripts\activate
      Linux/macOS   : source .venv/bin/activate
      (Si PowerShell bloquea el script, ejecute primero:
       Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)

  Paso 3. Instalar las dependencias
      pip install -r requirements.txt

  Paso 4. Crear el archivo de configuración local
      Windows       : copy .env.example .env
      Linux/macOS   : cp .env.example .env

      Abra el archivo .env con un editor de texto y deje estas líneas así:
          DJANGO_DEBUG=True
          DATABASE_URL=
      (DATABASE_URL vacío = usar SQLite local; el resto puede quedar vacío.)

  Paso 5. Crear la base de datos (migraciones)
      python manage.py migrate

  Paso 6. Cargar los datos de demostración
      python manage.py seed_demo
      Crea 6 departamentos, 12 usuarios, un curso con evaluación, un curso de
      refuerzo y reportes de ejemplo.

  Paso 7. Iniciar el servidor
      python manage.py runserver

  Paso 8. Abrir el navegador en  http://127.0.0.1:8000/

Para detener el servidor presione Ctrl+C en la terminal.


4. CREDENCIALES DE PRUEBA (ENTORNO LOCAL)
-----------------------------------------
Creadas por el comando seed_demo:

  Nivel 1 - Administrador
      Correo     : admin.demo@curex.net.ve
      Contraseña : PhishGuard.Demo2026

  Nivel 2 - Colaborador
      Correo     : colaborador.demo@curex.net.ve
      Contraseña : PhishGuard.Demo2026

  Otros colaboradores de ejemplo (misma contraseña): maria.gonzalez,
  ana.martinez, carlos.perez, luisa.hernandez, pedro.ramirez, carmen.torres,
  miguel.flores, rosa.morales, andres.castillo, jose.rodriguez
  (todos con @curex.net.ve).

  En producción las cuentas demo usan otra contraseña (ver CREDENCIALES.txt).

  Respuestas correctas de la evaluación del curso demo: 2.ª, 2.ª, 1.ª y 2.ª opción.


5. RECORRIDO SUGERIDO
---------------------
  Como Colaborador:
    1. Mi panel: cursos asignados, avance, certificados y reportes.
    2. Abrir el curso «Fundamentos para reconocer el phishing», completar las
       lecciones y presentar la evaluación final.
    3. Reportar correo: enviar un reporte de correo sospechoso.
    4. Mi perfil: cambiar la contraseña.
    5. Escribir /admin-panel/ en la barra de direcciones: se muestra el error
       403 (el control de acceso se valida en el servidor).

  Como Administrador:
    1. Indicadores: tasas, cobertura de capacitación y reportes atendidos.
    2. Usuarios y Departamentos: alta, edición, desbloqueo. Intentar crear un
       usuario con correo @gmail.com para ver el rechazo por dominio.
    3. Cursos: crear un curso, agregar lecciones con el editor, configurar la
       evaluación y asignarlo a un departamento.
    4. Reportes: atender un reporte y cambiar su estado.
    5. Bitácora: ver el registro de todas las acciones anteriores.

  Seguridad que puede comprobarse:
    - Tras 5 intentos fallidos de inicio de sesión, la cuenta se bloquea
      15 minutos (el Administrador puede desbloquearla).
    - Tras 15 minutos sin actividad, la sesión se cierra.
    - En local, los correos (recuperación de contraseña, notificaciones) se
      muestran en la terminal donde corre el servidor.


6. PRUEBAS AUTOMATIZADAS
------------------------
  python manage.py test           (135 pruebas)
  pip install ruff  y luego  ruff check .     (estilo PEP 8)


7. ESTRUCTURA DEL PROYECTO
--------------------------
  manage.py                     Punto de entrada de Django
  requirements.txt              Dependencias
  vercel.json                   Configuración de despliegue en Vercel
  .env.example                  Plantilla de variables de entorno
  phishguard/                   Configuración (settings.py, urls.py, wsgi.py)
  usuarios/                     Usuarios, departamentos, autenticación (RF-01 a RF-08)
     management/commands/seed_demo.py   Script de datos de demostración
  capacitacion/                 Cursos, lecciones, evaluaciones (RF-09 a RF-15)
  simulaciones/                 Modelos de campañas de simulación (RF-16 a RF-21)
  reportes/                     Reportes de correos sospechosos (RF-22 a RF-25)
  panel/                        Indicadores, bitácora, panel personal (RF-26 a RF-30)
  */migrations/                 Scripts de base de datos (migraciones de Django)
  docs/base_de_datos/esquema_postgresql.sql   Esquema SQL de referencia
  templates/                    Plantillas HTML (Bootstrap 5)
  static/                       CSS, JavaScript e imágenes
  PRD.md / CLAUDE.md            Especificación y reglas de desarrollo


8. ALCANCE DEL PROTOTIPO
------------------------
  Implementado: RF-01 a RF-13 y RF-22 a RF-30.

  Fase 2 (maquetado con aviso «Próximamente»):
    - Carga masiva de usuarios por CSV (parte de RF-01)
    - Certificado de aprobación en PDF (RF-14)
    - Recordatorios automáticos por correo (RF-15)
    - Exportación de reportes en CSV y PDF (RF-28)

  En construcción en esta versión:
    - Plantillas y campañas de simulación de phishing (RF-16 a RF-21). Sus
      modelos de datos ya existen; las pantallas muestran «En construcción».
      Por eso las tasas de clics y de reporte del panel muestran «Sin datos de
      campañas» hasta que se envíe la primera campaña.

  Ajuste respecto de la especificación: el adjunto de un reporte admite hasta
  4 MB (no 5 MB) porque Vercel limita cada petición a 4,5 MB.


9. DESPLIEGUE (REFERENCIA)
--------------------------
  1. Crear un proyecto en Supabase y dos buckets de Storage:
     «phishguard» (privado) y «phishguard-publico» (público).
  2. Configurar las variables de .env.example con DATABASE_URL apuntando al
     pooler de Supabase (puerto 6543).
  3. python manage.py migrate   y   python manage.py seed_demo --password <clave>
  4. Activar RLS en las tablas del esquema public (ver el final de
     docs/base_de_datos/esquema_postgresql.sql).
  5. Importar el repositorio en Vercel y cargar las variables de entorno con
     DJANGO_DEBUG=False. Cada push a la rama main se despliega automáticamente.

===============================================================================
