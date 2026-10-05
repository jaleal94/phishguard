"""Saneamiento del HTML producido por el editor Quill (RF-09)."""

import nh3

ETIQUETAS_PERMITIDAS = {
    "p", "br", "h1", "h2", "h3", "h4", "strong", "b", "em", "i", "u", "s",
    "a", "ol", "ul", "li", "blockquote", "pre", "code", "img", "span",
}
ATRIBUTOS_PERMITIDOS = {
    "*": {"class"},
    "a": {"href", "target"},
    "img": {"src", "alt", "width", "height"},
    "li": {"data-list"},
}
ESQUEMAS_PERMITIDOS = {"http", "https", "mailto"}


def sanear_html(html):
    """Elimina scripts, eventos, estilos y URLs peligrosas; conserva el formato de Quill."""
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=ETIQUETAS_PERMITIDAS,
        attributes=ATRIBUTOS_PERMITIDOS,
        url_schemes=ESQUEMAS_PERMITIDOS,
        link_rel="noopener noreferrer",
        strip_comments=True,
    )
