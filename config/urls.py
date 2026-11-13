from django.urls import include, path

urlpatterns = [
    path("", include("apps.eventos.urls")),                 # área do visitante
    path("participacao/", include("apps.participacao.urls")),  # interesse, check-in, avaliação
    path("painel/", include("apps.dashboard.urls")),        # área administrativa
    path("inteligencia/", include("apps.inteligencia.urls")),  # análises da IA
]
