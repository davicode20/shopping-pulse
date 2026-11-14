from django.http import HttpResponse
from django.urls import include, path


def saude(request):
    """Health check do Render: resposta mínima, sem montar página nem criar sessão."""
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("saude/", saude, name="saude"),
    path("", include("apps.eventos.urls")),                 # área do visitante
    path("participacao/", include("apps.participacao.urls")),  # interesse, check-in, avaliação
    path("painel/", include("apps.dashboard.urls")),        # área administrativa
    path("inteligencia/", include("apps.inteligencia.urls")),  # análises da IA
]
