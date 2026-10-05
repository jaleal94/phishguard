"""Formularios de la app reportes."""

from django import forms
from django.conf import settings
from django.utils import timezone

from .models import ReporteSospechoso
from .servicios import AdjuntoInvalido, validar_adjunto


class ReporteForm(forms.ModelForm):
    """RF-22: reporte de un correo sospechoso con adjunto opcional."""

    adjunto = forms.FileField(
        label="Adjunto (opcional)",
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": ".png,.jpg,.jpeg,.pdf,.eml"}),
    )

    class Meta:
        model = ReporteSospechoso
        fields = ["remitente", "asunto", "fecha_recepcion", "descripcion"]
        widgets = {
            "fecha_recepcion": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["adjunto"].help_text = (
            "Captura de pantalla (.png, .jpg), PDF o el correo guardado (.eml), "
            f"de hasta {settings.REPORTE_TAMANO_MAX_MB} MB."
        )
        self.fields["fecha_recepcion"].input_formats = ["%Y-%m-%dT%H:%M"]
        if not self.is_bound:
            self.initial.setdefault(
                "fecha_recepcion", timezone.localtime().strftime("%Y-%m-%dT%H:%M")
            )

    def clean_fecha_recepcion(self):
        fecha = self.cleaned_data["fecha_recepcion"]
        if fecha > timezone.now():
            raise forms.ValidationError("La fecha de recepción no puede estar en el futuro.")
        return fecha

    def clean_adjunto(self):
        archivo = self.cleaned_data.get("adjunto")
        if archivo:
            try:
                validar_adjunto(archivo)
            except AdjuntoInvalido as error:
                raise forms.ValidationError(str(error)) from error
            archivo.seek(0)
        return archivo


class AtenderReporteForm(forms.Form):
    """RF-23: cambio de estado de un reporte por un Administrador."""

    estado = forms.ChoiceField(label="Estado", choices=ReporteSospechoso.Estado.choices)
    comentario = forms.CharField(
        label="Comentario para el usuario",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Se incluye en la notificación por correo.",
    )
