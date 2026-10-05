"""Datos de prueba para la app capacitacion."""

from capacitacion.models import Curso, Evaluacion, Leccion, Opcion, Pregunta


def crear_curso(titulo="Phishing básico", estado=Curso.Estado.PUBLICADO, lecciones=3, **campos):
    """Crea un curso con ``lecciones`` lecciones numeradas."""
    curso = Curso.objects.create(titulo=titulo, estado=estado, **campos)
    for i in range(1, lecciones + 1):
        Leccion.objects.create(
            curso=curso, orden=i, titulo=f"Lección {i}", contenido_html="<p>x</p>"
        )
    return curso


def crear_evaluacion(curso, preguntas=3, nota_minima=70, intentos_maximos=2):
    """Crea una evaluación con preguntas de dos opciones (la primera es la correcta)."""
    evaluacion = Evaluacion.objects.create(
        curso=curso, nota_minima=nota_minima, intentos_maximos=intentos_maximos
    )
    for i in range(1, preguntas + 1):
        pregunta = Pregunta.objects.create(
            evaluacion=evaluacion, enunciado=f"Pregunta {i}", orden=i
        )
        Opcion.objects.create(pregunta=pregunta, texto="Correcta", es_correcta=True)
        Opcion.objects.create(pregunta=pregunta, texto="Incorrecta", es_correcta=False)
    return evaluacion


def respuestas(evaluacion, correctas):
    """Respuestas {pregunta: opción} con las primeras ``correctas`` respondidas bien."""
    resultado = {}
    for i, pregunta in enumerate(evaluacion.preguntas.all()):
        opcion = pregunta.opciones.get(es_correcta=i < correctas)
        resultado[pregunta.pk] = opcion.pk
    return resultado


def completar_todo(asignacion):
    """Marca todas las lecciones del curso como completadas."""
    from capacitacion.servicios import completar_leccion

    for leccion in asignacion.curso.lecciones.all():
        completar_leccion(asignacion, leccion)
