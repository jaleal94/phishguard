"""Procesadores de contexto de la app usuarios."""


def plantilla_base(request):
    """Elige la plantilla base según el rol, para pantallas compartidas por ambos roles."""
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {"base_plantilla": "base.html"}
    if usuario.es_admin:
        return {"base_plantilla": "base_admin.html"}
    return {"base_plantilla": "base_colaborador.html"}
