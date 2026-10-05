"""Filtros de plantilla para renderizar campos de formulario con Bootstrap 5."""

from django import forms, template

register = template.Library()


@register.filter
def bootstrap(campo):
    """Renderiza el widget de un campo con las clases de Bootstrap y atributos ARIA."""
    widget = campo.field.widget
    if isinstance(widget, forms.CheckboxInput):
        clase = "form-check-input"
    elif isinstance(widget, forms.Select | forms.SelectMultiple):
        clase = "form-select"
    else:
        clase = "form-control"
    attrs = {"class": f"{clase} is-invalid" if campo.errors else clase}
    descritos = []
    if campo.help_text:
        descritos.append(f"{campo.auto_id}_ayuda")
    if campo.errors:
        attrs["aria-invalid"] = "true"
        descritos.append(f"{campo.auto_id}_error")
    if descritos:
        attrs["aria-describedby"] = " ".join(descritos)
    return campo.as_widget(attrs=attrs)


@register.filter
def es_casilla(campo):
    """Indica si el campo es una casilla de verificación."""
    return isinstance(campo.field.widget, forms.CheckboxInput)
