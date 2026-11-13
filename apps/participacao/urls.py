from django.urls import path

from . import contas, views

app_name = "participacao"

urlpatterns = [
    path("conta/", contas.conta, name="conta"),
    path("conta/entrar/", contas.entrar_visitante, name="entrar"),
    path("conta/cadastrar/", contas.cadastrar_visitante, name="cadastrar"),
    path("conta/sair/", contas.sair_visitante, name="sair"),
    path("interesse/", views.interesse, name="interesse"),
    path("presenca/", views.presenca, name="presenca"),
    path("perfil/", views.perfil, name="perfil"),
    path("checkin/<int:evento_id>/<str:token>/", views.checkin, name="checkin"),
    path("avaliar/<int:evento_id>/", views.avaliar, name="avaliar"),
]
