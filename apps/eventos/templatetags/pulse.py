"""Filtros de template: números e moeda no formato brasileiro."""
from django import template

register = template.Library()


def _br(texto):
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


@register.filter
def num(valor, casas=0):
    """1644 -> 1.644 | 4.62 (casas=1) -> 4,6"""
    if valor in (None, ""):
        return "—"
    try:
        return _br(f"{float(valor):,.{int(casas)}f}")
    except (TypeError, ValueError):
        return valor


@register.filter
def brl(valor):
    if not valor:
        return "—"
    return "R$ " + _br(f"{float(valor):,.2f}")


@register.filter
def porcentagem_de(parte, total):
    """Largura (0-100) para barras: {{ parte|porcentagem_de:total }}"""
    try:
        return round(min(100, float(parte) / float(total) * 100), 1) if float(total) else 0
    except (TypeError, ValueError):
        return 0
