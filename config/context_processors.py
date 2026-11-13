from django.conf import settings


def projeto(request):
    """Disponibiliza nome e slogan em todos os templates (facilita trocar o nome depois)."""
    return {
        "NOME_PROJETO": settings.NOME_PROJETO,
        "SLOGAN_PROJETO": settings.SLOGAN_PROJETO,
    }
