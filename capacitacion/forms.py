"""Formularios de la app capacitacion."""

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from usuarios.models import Departamento, Usuario

from .models import Curso, Evaluacion, Leccion, Opcion, Pregunta


class CursoForm(forms.ModelForm):
    """Alta y edición de cursos. Un curso solo puede publicarse si tiene lecciones."""

    class Meta:
        model = Curso
        fields = ["titulo", "descripcion", "estado", "es_refuerzo"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        datos = super().clean()
        if datos.get("estado") == Curso.Estado.PUBLICADO and (
            not self.instance.pk or not self.instance.lecciones.exists()
        ):
            self.add_error("estado", "Agregue al menos una lección antes de publicar el curso.")
        return datos


class LeccionForm(forms.ModelForm):
    """Lección con contenido enriquecido (Quill); el HTML se sanea al guardar."""

    class Meta:
        model = Leccion
        fields = ["orden", "titulo", "contenido_html", "video_url"]
        widgets = {"contenido_html": forms.HiddenInput()}
        help_texts = {"video_url": "Opcional. Enlace de YouTube o Vimeo."}


class EvaluacionForm(forms.ModelForm):
    """Configuración de la evaluación de un curso."""

    class Meta:
        model = Evaluacion
        fields = ["nota_minima", "intentos_maximos"]


class PreguntaForm(forms.ModelForm):
    """Enunciado de una pregunta de selección simple."""

    class Meta:
        model = Pregunta
        fields = ["orden", "enunciado"]
        widgets = {"enunciado": forms.Textarea(attrs={"rows": 2})}


class BaseOpcionFormSet(BaseInlineFormSet):
    """Exige al menos dos opciones y exactamente una correcta."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        vigentes = [
            f.cleaned_data
            for f in self.forms
            if f.cleaned_data and not f.cleaned_data.get("DELETE") and f.cleaned_data.get("texto")
        ]
        if len(vigentes) < 2:
            raise forms.ValidationError("La pregunta debe tener al menos dos opciones.")
        if sum(1 for d in vigentes if d.get("es_correcta")) != 1:
            raise forms.ValidationError("Marque exactamente una opción como correcta.")


OpcionFormSet = inlineformset_factory(
    Pregunta,
    Opcion,
    formset=BaseOpcionFormSet,
    fields=["texto", "es_correcta"],
    extra=4,
    max_num=6,
    can_delete=True,
)


class AsignarCursoForm(forms.Form):
    """RF-10: asignación de un curso a departamentos completos o a usuarios puntuales."""

    departamentos = forms.ModelMultipleChoiceField(
        label="Departamentos",
        queryset=Departamento.objects.filter(activo=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Se asignará a todos los usuarios activos de cada departamento.",
    )
    usuarios = forms.ModelMultipleChoiceField(
        label="Usuarios puntuales",
        queryset=Usuario.objects.filter(is_active=True),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 8}),
        help_text="Mantenga Ctrl (o Cmd) para seleccionar varios.",
    )
    fecha_limite = forms.DateField(
        label="Fecha límite", widget=forms.DateInput(attrs={"type": "date"})
    )

    def clean_fecha_limite(self):
        fecha = self.cleaned_data["fecha_limite"]
        if fecha < timezone.localdate():
            raise forms.ValidationError("La fecha límite no puede estar en el pasado.")
        return fecha

    def clean(self):
        datos = super().clean()
        if not datos.get("departamentos") and not datos.get("usuarios"):
            raise forms.ValidationError("Seleccione al menos un departamento o un usuario.")
        return datos
