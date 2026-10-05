"""Vistas de la app capacitacion (RF-09 a RF-15)."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from panel.bitacora import cambios_formulario, registrar
from phishguard import almacenamiento
from usuarios.decoradores import admin_requerido
from usuarios.models import Usuario

from . import servicios
from .forms import (
    AsignarCursoForm,
    CursoForm,
    EvaluacionForm,
    LeccionForm,
    OpcionFormSet,
    PreguntaForm,
)
from .models import Asignacion, Curso, Evaluacion, Intento, Leccion, Pregunta

TIPOS_IMAGEN = {"image/png": b"\x89PNG", "image/jpeg": b"\xff\xd8\xff", "image/gif": b"GIF8"}
TAMANO_MAX_IMAGEN = 2 * 1024 * 1024


# --- Administración de cursos ---------------------------------------------------------


@admin_requerido
def cursos_admin(request):
    """Listado de cursos con indicadores de asignación y avance."""
    cursos = Curso.objects.annotate(
        total_lecciones=Count("lecciones", distinct=True),
        total_asignaciones=Count("asignaciones", distinct=True),
        total_completadas=Count(
            "asignaciones", filter=Q(asignaciones__completada_en__isnull=False), distinct=True
        ),
    )
    estado = request.GET.get("estado", "")
    if estado in Curso.Estado.values:
        cursos = cursos.filter(estado=estado)
    return render(
        request,
        "capacitacion/admin/cursos_lista.html",
        {"cursos": cursos, "estados": Curso.Estado.choices, "estado": estado},
    )


@admin_requerido
def curso_crear(request):
    """Alta de un curso (en borrador hasta tener lecciones)."""
    form = CursoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        curso = form.save(commit=False)
        curso.creado_por = request.user
        curso.save()
        registrar("CREAR_CURSO", objeto=curso.titulo, request=request)
        messages.success(request, "Curso creado. Ahora agregue sus lecciones.")
        return redirect("capacitacion:curso_detalle_admin", curso.pk)
    return render(
        request, "capacitacion/admin/curso_form.html", {"form": form, "titulo": "Nuevo curso"}
    )


@admin_requerido
def curso_editar(request, pk):
    """Edición de datos y estado de un curso."""
    curso = get_object_or_404(Curso, pk=pk)
    form = CursoForm(request.POST or None, instance=curso)
    if request.method == "POST" and form.is_valid():
        cambios = cambios_formulario(form)
        form.save()
        if cambios:
            registrar("EDITAR_CURSO", objeto=curso.titulo, detalle=cambios, request=request)
        messages.success(request, "Curso actualizado.")
        return redirect("capacitacion:curso_detalle_admin", curso.pk)
    return render(
        request,
        "capacitacion/admin/curso_form.html",
        {"form": form, "titulo": f"Editar curso: {curso.titulo}", "curso": curso},
    )


@admin_requerido
def curso_detalle_admin(request, pk):
    """Detalle del curso: lecciones, evaluación y asignaciones con su avance."""
    curso = get_object_or_404(Curso, pk=pk)
    lecciones = list(curso.lecciones.all())
    total = len(lecciones)
    asignaciones = (
        Asignacion.objects.filter(curso=curso)
        .select_related("usuario", "usuario__departamento")
        .annotate(n_progresos=Count("progresos"))
        .order_by("usuario__nombre_completo")
    )
    filas = [
        {"asignacion": a, "avance": round(a.n_progresos * 100 / total) if total else 0}
        for a in asignaciones
    ]
    evaluacion = Evaluacion.objects.filter(curso=curso).first()
    return render(
        request,
        "capacitacion/admin/curso_detalle.html",
        {
            "curso": curso,
            "lecciones": lecciones,
            "evaluacion": evaluacion,
            "preguntas": evaluacion.preguntas.prefetch_related("opciones") if evaluacion else [],
            "filas": filas,
        },
    )


@admin_requerido
def curso_recordatorios(request, pk):
    """RF-15 (fase 2): configuración de recordatorios automáticos."""
    curso = get_object_or_404(Curso, pk=pk)
    return render(
        request,
        "comun/proximamente.html",
        {
            "titulo": "Recordatorios automáticos",
            "descripcion": f"Envío de recordatorios por correo de «{curso.titulo}» "
            "a quienes tengan el curso próximo a vencer.",
            "volver_href": reverse("capacitacion:curso_detalle_admin", args=[curso.pk]),
        },
    )


# --- Lecciones -------------------------------------------------------------------------


@admin_requerido
def leccion_crear(request, curso_pk):
    """Alta de una lección con editor Quill."""
    curso = get_object_or_404(Curso, pk=curso_pk)
    siguiente = (curso.lecciones.order_by("-orden").values_list("orden", flat=True).first() or 0)
    form = LeccionForm(request.POST or None, initial={"orden": siguiente + 1})
    if request.method == "POST" and form.is_valid():
        leccion = form.save(commit=False)
        leccion.curso = curso
        leccion.save()
        registrar(
            "CREAR_LECCION", objeto=f"{curso.titulo} · {leccion.titulo}", request=request
        )
        messages.success(request, "Lección creada.")
        return redirect("capacitacion:curso_detalle_admin", curso.pk)
    return render(
        request,
        "capacitacion/admin/leccion_form.html",
        {"form": form, "curso": curso, "titulo": "Nueva lección"},
    )


@admin_requerido
def leccion_editar(request, pk):
    """Edición de una lección."""
    leccion = get_object_or_404(Leccion.objects.select_related("curso"), pk=pk)
    form = LeccionForm(request.POST or None, instance=leccion)
    if request.method == "POST" and form.is_valid():
        cambios = cambios_formulario(form)
        form.save()
        if cambios:
            registrar(
                "EDITAR_LECCION",
                objeto=f"{leccion.curso.titulo} · {leccion.titulo}",
                detalle={c: "modificado" for c in cambios},
                request=request,
            )
        messages.success(request, "Lección actualizada.")
        return redirect("capacitacion:curso_detalle_admin", leccion.curso_id)
    return render(
        request,
        "capacitacion/admin/leccion_form.html",
        {"form": form, "curso": leccion.curso, "titulo": f"Editar lección: {leccion.titulo}"},
    )


@admin_requerido
@require_POST
def leccion_eliminar(request, pk):
    """Elimina una lección (no se permite dejar sin lecciones un curso publicado)."""
    leccion = get_object_or_404(Leccion.objects.select_related("curso"), pk=pk)
    curso = leccion.curso
    if curso.esta_publicado and curso.lecciones.count() == 1:
        messages.error(request, "Un curso publicado debe conservar al menos una lección.")
    else:
        registrar("ELIMINAR_LECCION", objeto=f"{curso.titulo} · {leccion.titulo}", request=request)
        leccion.delete()
        messages.success(request, "Lección eliminada.")
    return redirect("capacitacion:curso_detalle_admin", curso.pk)


@admin_requerido
@require_POST
def subir_imagen(request):
    """Sube una imagen del editor de lecciones a Supabase Storage y devuelve su URL."""
    archivo = request.FILES.get("imagen")
    if archivo is None:
        return JsonResponse({"error": "No se recibió ninguna imagen."}, status=400)
    if archivo.size > TAMANO_MAX_IMAGEN:
        return JsonResponse({"error": "La imagen supera los 2 MB."}, status=400)
    contenido = archivo.read()
    firma = TIPOS_IMAGEN.get(archivo.content_type)
    if firma is None or not contenido.startswith(firma):
        return JsonResponse({"error": "Solo se permiten imágenes PNG, JPG o GIF."}, status=400)
    try:
        ruta = almacenamiento.generar_ruta("lecciones", archivo.name)
        almacenamiento.subir(
            ruta, contenido, archivo.content_type, bucket=settings.SUPABASE_BUCKET_PUBLICO
        )
    except almacenamiento.AlmacenamientoError as error:
        return JsonResponse({"error": str(error)}, status=503)
    return JsonResponse({"url": almacenamiento.url_publica(ruta)})


# --- Evaluación ----------------------------------------------------------------------


@admin_requerido
def evaluacion_editar(request, curso_pk):
    """Configura nota mínima e intentos máximos (crea la evaluación si no existe)."""
    curso = get_object_or_404(Curso, pk=curso_pk)
    evaluacion = Evaluacion.objects.filter(curso=curso).first() or Evaluacion(curso=curso)
    form = EvaluacionForm(request.POST or None, instance=evaluacion)
    if request.method == "POST" and form.is_valid():
        nueva = evaluacion.pk is None
        cambios = cambios_formulario(form)
        form.save()
        if nueva or cambios:
            registrar(
                "CREAR_EVALUACION" if nueva else "EDITAR_EVALUACION",
                objeto=curso.titulo,
                detalle=cambios,
                request=request,
            )
        messages.success(request, "Evaluación guardada. Agregue o revise sus preguntas.")
        return redirect("capacitacion:curso_detalle_admin", curso.pk)
    return render(
        request, "capacitacion/admin/evaluacion_form.html", {"form": form, "curso": curso}
    )


def _guardar_pregunta(request, curso, pregunta, accion):
    form = PreguntaForm(request.POST or None, instance=pregunta)
    formset = OpcionFormSet(request.POST or None, instance=pregunta, prefix="opciones")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        pregunta = form.save()
        formset.instance = pregunta
        formset.save()
        registrar(accion, objeto=f"{curso.titulo} · {pregunta}", request=request)
        messages.success(request, "Pregunta guardada.")
        return redirect("capacitacion:curso_detalle_admin", curso.pk)
    return render(
        request,
        "capacitacion/admin/pregunta_form.html",
        {"form": form, "formset": formset, "curso": curso},
    )


@admin_requerido
def pregunta_crear(request, curso_pk):
    """Alta de una pregunta con sus opciones."""
    curso = get_object_or_404(Curso, pk=curso_pk)
    evaluacion = Evaluacion.objects.filter(curso=curso).first()
    if evaluacion is None:
        messages.info(request, "Primero configure la evaluación del curso.")
        return redirect("capacitacion:evaluacion_editar", curso.pk)
    siguiente = evaluacion.preguntas.count() + 1
    pregunta = Pregunta(evaluacion=evaluacion, orden=siguiente)
    return _guardar_pregunta(request, curso, pregunta, "CREAR_PREGUNTA")


@admin_requerido
def pregunta_editar(request, pk):
    """Edición de una pregunta y sus opciones."""
    pregunta = get_object_or_404(Pregunta.objects.select_related("evaluacion__curso"), pk=pk)
    return _guardar_pregunta(request, pregunta.evaluacion.curso, pregunta, "EDITAR_PREGUNTA")


@admin_requerido
@require_POST
def pregunta_eliminar(request, pk):
    """Elimina una pregunta de la evaluación."""
    pregunta = get_object_or_404(Pregunta.objects.select_related("evaluacion__curso"), pk=pk)
    curso = pregunta.evaluacion.curso
    registrar("ELIMINAR_PREGUNTA", objeto=f"{curso.titulo} · {pregunta}", request=request)
    pregunta.delete()
    messages.success(request, "Pregunta eliminada.")
    return redirect("capacitacion:curso_detalle_admin", curso.pk)


# --- Asignaciones ----------------------------------------------------------------------


@admin_requerido
def curso_asignar(request, pk):
    """RF-10: asigna el curso a departamentos y/o usuarios sin crear duplicados."""
    curso = get_object_or_404(Curso, pk=pk)
    if not curso.esta_publicado:
        messages.error(request, "Solo se pueden asignar cursos publicados.")
        return redirect("capacitacion:curso_detalle_admin", curso.pk)
    form = AsignarCursoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        fecha = form.cleaned_data["fecha_limite"]
        nuevas = 0
        for departamento in form.cleaned_data["departamentos"]:
            nuevas += servicios.asignar_a_departamento(curso, departamento, fecha_limite=fecha)
        usuarios = form.cleaned_data["usuarios"]
        if usuarios:
            ids = [u.pk for u in usuarios]
            nuevas += servicios.asignar_a_usuarios(
                curso, Usuario.objects.filter(pk__in=ids), fecha_limite=fecha
            )
        registrar(
            "ASIGNAR_CURSO",
            objeto=curso.titulo,
            detalle={
                "departamentos": [d.nombre for d in form.cleaned_data["departamentos"]],
                "usuarios": [u.email for u in usuarios],
                "fecha_limite": fecha.isoformat(),
                "nuevas": nuevas,
            },
            request=request,
        )
        messages.success(request, f"Se crearon {nuevas} asignaciones nuevas.")
        return redirect("capacitacion:curso_detalle_admin", curso.pk)
    return render(request, "capacitacion/admin/asignar.html", {"form": form, "curso": curso})


# --- Vistas del Colaborador ----------------------------------------------------------


def _contexto_curso(request, pk):
    """Devuelve (curso, asignacion). El Administrador sin asignación entra en vista previa.

    RF-09: un Colaborador solo ve cursos PUBLICADOS que tenga asignados.
    """
    curso = get_object_or_404(Curso, pk=pk)
    asignacion = Asignacion.objects.filter(curso=curso, usuario=request.user).first()
    if request.user.es_admin:
        if asignacion and not curso.esta_publicado:
            asignacion = None
        return curso, asignacion
    if asignacion is None or not curso.esta_publicado:
        raise Http404("Curso no disponible.")
    return curso, asignacion


@login_required
def curso_ver(request, pk):
    """Lecciones del curso con el avance del usuario (RF-11)."""
    curso, asignacion = _contexto_curso(request, pk)
    lecciones = list(curso.lecciones.all())
    completadas = (
        set(asignacion.progresos.values_list("leccion_id", flat=True)) if asignacion else set()
    )
    actual = None
    elegida = request.GET.get("leccion", "")
    if elegida.isdigit():
        actual = next((lec for lec in lecciones if lec.pk == int(elegida)), None)
    if actual is None and lecciones:
        actual = next((lec for lec in lecciones if lec.pk not in completadas), lecciones[0])
    indice = lecciones.index(actual) if actual else 0
    contexto = {
        "curso": curso,
        "asignacion": asignacion,
        "vista_previa": asignacion is None,
        "lecciones": lecciones,
        "completadas": completadas,
        "actual": actual,
        "numero": indice + 1,
        "anterior": lecciones[indice - 1] if actual and indice > 0 else None,
        "siguiente": lecciones[indice + 1] if actual and indice + 1 < len(lecciones) else None,
        "avance": asignacion.porcentaje_avance if asignacion else 0,
        "tiene_evaluacion": servicios.tiene_evaluacion(curso),
    }
    return render(request, "capacitacion/curso_ver.html", contexto)


@login_required
@require_POST
def leccion_completar(request, pk, leccion_pk):
    """Marca una lección como completada y avanza a la siguiente."""
    curso, asignacion = _contexto_curso(request, pk)
    if asignacion is None:
        messages.info(request, "En vista previa no se registra el avance.")
        return redirect("capacitacion:curso_ver", curso.pk)
    leccion = get_object_or_404(Leccion, pk=leccion_pk, curso=curso)
    servicios.completar_leccion(asignacion, leccion)
    siguiente = curso.lecciones.filter(
        Q(orden__gt=leccion.orden) | Q(orden=leccion.orden, id__gt=leccion.id)
    ).first()
    if siguiente:
        url = reverse("capacitacion:curso_ver", args=[curso.pk])
        return redirect(f"{url}?leccion={siguiente.pk}")
    asignacion.refresh_from_db()
    if asignacion.completada:
        messages.success(request, "¡Felicitaciones! Completó el curso.")
    elif servicios.tiene_evaluacion(curso):
        messages.success(request, "Completó las lecciones. Ya puede presentar la evaluación.")
    return redirect("capacitacion:curso_ver", curso.pk)


def _leer_respuestas(request, preguntas):
    """Lee las opciones elegidas validando que pertenezcan a cada pregunta."""
    respuestas = {}
    for pregunta in preguntas:
        valor = request.POST.get(f"pregunta_{pregunta.pk}", "")
        if valor.isdigit() and any(o.pk == int(valor) for o in pregunta.opciones.all()):
            respuestas[pregunta.pk] = int(valor)
    return respuestas


@login_required
def evaluacion_presentar(request, pk):
    """RF-12 y RF-13: presentación y calificación automática de la evaluación."""
    curso, asignacion = _contexto_curso(request, pk)
    evaluacion = Evaluacion.objects.filter(curso=curso).first()
    if evaluacion is None or not evaluacion.preguntas.exists():
        raise Http404("El curso no tiene evaluación.")
    preguntas = list(evaluacion.preguntas.prefetch_related("opciones"))
    contexto = {"curso": curso, "evaluacion": evaluacion, "preguntas": preguntas}

    if asignacion is None:
        contexto["vista_previa"] = True
        return render(request, "capacitacion/evaluacion.html", contexto)

    usados = servicios.intentos_usados(evaluacion, request.user)
    contexto.update(
        {
            "asignacion": asignacion,
            "motivo": servicios.motivo_no_disponible(asignacion),
            "intentos_usados": usados,
            "intentos_restantes": max(evaluacion.intentos_maximos - usados, 0),
            "intentos": Intento.objects.filter(evaluacion=evaluacion, usuario=request.user),
        }
    )
    if request.method == "POST" and not contexto["motivo"]:
        respuestas = _leer_respuestas(request, preguntas)
        if len(respuestas) < len(preguntas):
            contexto["error"] = "Responda todas las preguntas antes de enviar."
            contexto["elegidas"] = respuestas
        else:
            try:
                intento = servicios.presentar_evaluacion(asignacion, respuestas)
            except servicios.EvaluacionNoDisponible as error:
                messages.error(request, str(error))
                return redirect("capacitacion:evaluacion", curso.pk)
            return redirect("capacitacion:resultado", curso.pk, intento.pk)
    return render(request, "capacitacion/evaluacion.html", contexto)


@login_required
def intento_resultado(request, pk, intento_pk):
    """Resultado de un intento. RF-30: solo el propio usuario puede verlo."""
    curso = get_object_or_404(Curso, pk=pk)
    intento = get_object_or_404(
        Intento, pk=intento_pk, usuario=request.user, evaluacion__curso=curso
    )
    usados = servicios.intentos_usados(intento.evaluacion, request.user)
    return render(
        request,
        "capacitacion/resultado.html",
        {
            "curso": curso,
            "intento": intento,
            "evaluacion": intento.evaluacion,
            "intentos_restantes": max(intento.evaluacion.intentos_maximos - usados, 0),
        },
    )


@login_required
def certificado(request, pk):
    """RF-14 (fase 2): descarga del certificado en PDF."""
    curso, _ = _contexto_curso(request, pk)
    return render(
        request,
        "comun/proximamente.html",
        {
            "titulo": "Certificado de aprobación",
            "descripcion": f"Descarga en PDF del certificado del curso «{curso.titulo}».",
        },
    )
