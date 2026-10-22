"""Datos de demostración adicionales: más cursos, intentos y avances (seed_demo)."""

from datetime import timedelta

from django.utils import timezone

from usuarios.models import Usuario

from . import servicios
from .demo import _crear_curso
from .models import Asignacion, Curso, Evaluacion, Intento, Opcion, Pregunta

CURSOS = [
    {
        "titulo": "Contraseñas seguras y autenticación",
        "descripcion": "Cómo crear y proteger contraseñas y por qué activar la verificación "
        "en dos pasos.",
        "lecciones": [
            ("Características de una contraseña segura",
             "<p>Use frases largas (12 caracteres o más), únicas para cada servicio y "
             "difíciles de adivinar.</p>"),
            ("Gestores de contraseñas",
             "<p>Un gestor de contraseñas genera y guarda claves distintas para cada "
             "servicio, de modo que solo debe recordar una.</p>"),
        ],
        "preguntas": [
            ("¿Cuál es la contraseña más segura?",
             ["123456", "Una frase larga y única", "Su fecha de nacimiento"], 1),
            ("¿Conviene reutilizar la misma contraseña en varios servicios?",
             ["Sí, es más práctico", "No, cada servicio debe tener la suya"], 1),
        ],
    },
    {
        "titulo": "Manejo seguro de archivos adjuntos",
        "descripcion": "Qué tipos de archivo son riesgosos y cómo verificar un adjunto "
        "antes de abrirlo.",
        "lecciones": [
            ("Extensiones peligrosas",
             "<p>Desconfíe de archivos .exe, .js, .vbs, .scr, .zip o documentos que piden "
             "«habilitar macros».</p>"),
            ("Verificar antes de abrir",
             "<p>Si no esperaba el adjunto, confirme con el remitente por otro medio "
             "(teléfono o en persona) antes de abrirlo.</p>"),
        ],
        "preguntas": [
            ("Un documento le pide «habilitar contenido» para verse. ¿Qué hace?",
             ["Lo habilito", "No lo habilito y lo reporto"], 1),
            ("¿Qué extensión es más riesgosa en un adjunto inesperado?",
             [".exe", ".txt"], 0),
        ],
    },
    {
        "titulo": "Ingeniería social en el trabajo",
        "descripcion": "Técnicas de manipulación por teléfono, correo y en persona, y cómo "
        "responder ante ellas.",
        "lecciones": [
            ("¿Qué es la ingeniería social?",
             "<p>Es la manipulación de personas para que entreguen información o realicen "
             "acciones que favorecen a un atacante.</p>"),
            ("Cómo responder",
             "<p>Verifique la identidad de quien solicita información, no comparta datos "
             "confidenciales por teléfono y reporte los intentos sospechosos.</p>"),
        ],
        "preguntas": [
            ("Alguien llama diciendo ser de Soporte y le pide su contraseña. ¿Qué hace?",
             ["Se la doy", "No la doy y lo reporto"], 1),
        ],
    },
]

PREGUNTAS_REFUERZO = [
    ("¿Qué debe hacer la próxima vez que reciba un correo sospechoso?",
     ["Abrir el enlace para comprobar", "Reportarlo en PhishGuard"], 1),
]

# (usuario, cantidad de respuestas correctas en el curso básico de 4 preguntas)
INTENTOS = [
    ("maria.gonzalez", 4), ("jose.rodriguez", 3), ("ana.martinez", 2),
    ("carlos.perez", 4), ("luisa.hernandez", 1), ("ana.martinez", 4),
]


def _evaluacion_refuerzo():
    refuerzo = Curso.objects.filter(es_refuerzo=True).first()
    if refuerzo is None or Evaluacion.objects.filter(curso=refuerzo).exists():
        return
    evaluacion = Evaluacion.objects.create(curso=refuerzo, nota_minima=100, intentos_maximos=3)
    for orden, (enunciado, opciones, correcta) in enumerate(PREGUNTAS_REFUERZO, start=1):
        pregunta = Pregunta.objects.create(evaluacion=evaluacion, enunciado=enunciado, orden=orden)
        for i, texto in enumerate(opciones):
            Opcion.objects.create(pregunta=pregunta, texto=texto, es_correcta=i == correcta)


def _respuestas(evaluacion, correctas):
    resultado = {}
    for i, pregunta in enumerate(evaluacion.preguntas.prefetch_related("opciones")):
        opciones = list(pregunta.opciones.all())
        buena = next(o for o in opciones if o.es_correcta)
        mala = next((o for o in opciones if not o.es_correcta), buena)
        resultado[pregunta.pk] = (buena if i < correctas else mala).pk
    return resultado


def cargar(admin):
    """Crea cursos, evaluaciones, avances e intentos adicionales (idempotente)."""
    for datos in CURSOS:
        curso = _crear_curso(datos, admin)
        colaboradores = Usuario.objects.filter(
            rol=Usuario.Rol.COLABORADOR, departamento__nombre__in=["Contabilidad", "Compras"]
        )
        servicios.asignar_a_usuarios(
            curso, colaboradores, fecha_limite=timezone.localdate() + timedelta(days=45)
        )
    _evaluacion_refuerzo()

    if Intento.objects.exists():
        return
    basico = Curso.objects.get(titulo="Fundamentos para reconocer el phishing")
    for usuario, correctas in INTENTOS:
        asignacion = Asignacion.objects.filter(
            curso=basico, usuario__email=f"{usuario}@curex.net.ve"
        ).first()
        if asignacion is None:
            continue
        for leccion in basico.lecciones.all():
            servicios.completar_leccion(asignacion, leccion)
        try:
            servicios.presentar_evaluacion(
                asignacion, _respuestas(basico.evaluacion, correctas)
            )
        except servicios.EvaluacionNoDisponible:
            pass
    # Avance parcial de otros colaboradores (sin evaluación todavía).
    for usuario in ["pedro.ramirez", "carmen.torres", "rosa.morales"]:
        asignacion = Asignacion.objects.filter(
            curso=basico, usuario__email=f"{usuario}@curex.net.ve"
        ).first()
        if asignacion:
            servicios.completar_leccion(asignacion, basico.lecciones.first())
