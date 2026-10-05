"""Contenido de demostración de capacitación (usado por el comando seed_demo)."""

from datetime import timedelta

from django.utils import timezone

from .models import Curso, Evaluacion, Leccion, Opcion, Pregunta
from .servicios import asignar_a_usuarios

CURSO_BASICO = {
    "titulo": "Fundamentos para reconocer el phishing",
    "descripcion": "Curso básico obligatorio: qué es el phishing, cómo identificarlo y cómo "
    "reportarlo en PhishGuard.",
    "lecciones": [
        (
            "¿Qué es el phishing?",
            "<p>El <strong>phishing</strong> es un engaño en el que un atacante se hace pasar "
            "por una persona o entidad de confianza para obtener contraseñas, datos bancarios "
            "o lograr que la víctima abra un archivo malicioso.</p>"
            "<p>Suele llegar por correo electrónico e imita a bancos, proveedores, servicios "
            "de paquetería o incluso a compañeros de trabajo.</p>",
        ),
        (
            "Señales de alerta en un correo",
            "<h3>Revise siempre:</h3><ul>"
            "<li>El <strong>remitente real</strong>: dominios parecidos como "
            "<em>curex-net.ve</em> o <em>curex.net.ve.soporte.com</em>.</li>"
            "<li><strong>Urgencia o amenazas</strong>: «su cuenta será suspendida hoy».</li>"
            "<li><strong>Enlaces</strong> cuyo destino no coincide con el texto (pase el "
            "cursor sin hacer clic).</li>"
            "<li><strong>Adjuntos inesperados</strong>: .zip, .exe, .html o documentos que "
            "piden «habilitar contenido».</li>"
            "<li>Saludos genéricos y errores de ortografía.</li></ul>",
        ),
        (
            "Qué hacer ante un correo sospechoso",
            "<ol><li>No haga clic en enlaces ni abra adjuntos.</li>"
            "<li>No responda ni reenvíe el correo a sus compañeros.</li>"
            "<li>Repórtelo desde <strong>PhishGuard → Reportar correo</strong>.</li>"
            "<li>Si ya hizo clic o escribió su contraseña, cámbiela y avise de inmediato al "
            "Departamento de Soporte Técnico y Sistemas.</li></ol>"
            "<blockquote>Reportar a tiempo protege a toda la organización.</blockquote>",
        ),
    ],
    "preguntas": [
        (
            "Recibe un correo de «su banco» que le pide confirmar su clave en un enlace. "
            "¿Qué hace?",
            ["Hago clic y confirmo mis datos", "Lo reporto en PhishGuard sin hacer clic",
             "Lo reenvío a un compañero para preguntarle"],
            1,
        ),
        (
            "¿Cuál de estos remitentes es más sospechoso?",
            ["soporte@curex.net.ve", "notificaciones@curex-net-ve.com",
             "rrhh@curex.net.ve"],
            1,
        ),
        (
            "¿Qué tipo de adjunto inesperado es más riesgoso?",
            ["factura.pdf.exe", "Una imagen enviada por un compañero que la anunció antes",
             "Un documento que usted mismo solicitó"],
            0,
        ),
        (
            "Si ya escribió su contraseña en una página sospechosa, debe:",
            ["Esperar a ver si pasa algo", "Cambiar la contraseña y avisar a Soporte Técnico",
             "Borrar el correo y olvidarlo"],
            1,
        ),
    ],
}

CURSO_REFUERZO = {
    "titulo": "Refuerzo: cayó en una simulación",
    "descripcion": "Curso corto que se asigna automáticamente a quien hace clic en una "
    "simulación de phishing.",
    "lecciones": [
        (
            "¿Qué acaba de pasar?",
            "<p>Hizo clic en un correo de <strong>simulación</strong> preparado por el "
            "Departamento de Soporte Técnico y Sistemas. No hubo ningún daño, pero un "
            "atacante real habría podido robar su información.</p>"
            "<p>Repase las señales de alerta y, la próxima vez, use el botón "
            "<strong>Reportar correo</strong>.</p>",
        ),
    ],
    "preguntas": [],
}


def _crear_curso(datos, creado_por, es_refuerzo=False):
    curso, creado = Curso.objects.get_or_create(
        titulo=datos["titulo"],
        defaults={
            "descripcion": datos["descripcion"],
            "estado": Curso.Estado.PUBLICADO,
            "es_refuerzo": es_refuerzo,
            "creado_por": creado_por,
        },
    )
    if not creado:
        return curso
    for orden, (titulo, html) in enumerate(datos["lecciones"], start=1):
        Leccion.objects.create(curso=curso, orden=orden, titulo=titulo, contenido_html=html)
    if datos["preguntas"]:
        evaluacion = Evaluacion.objects.create(curso=curso, nota_minima=75, intentos_maximos=3)
        for orden, (enunciado, opciones, correcta) in enumerate(datos["preguntas"], start=1):
            pregunta = Pregunta.objects.create(
                evaluacion=evaluacion, enunciado=enunciado, orden=orden
            )
            for i, texto in enumerate(opciones):
                Opcion.objects.create(pregunta=pregunta, texto=texto, es_correcta=i == correcta)
    return curso


def cargar(admin, colaboradores):
    """Crea los cursos de demostración y asigna el básico a los Colaboradores."""
    basico = _crear_curso(CURSO_BASICO, admin)
    _crear_curso(CURSO_REFUERZO, admin, es_refuerzo=True)
    return asignar_a_usuarios(
        basico, colaboradores, fecha_limite=timezone.localdate() + timedelta(days=30)
    )
