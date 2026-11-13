from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("dados.json", views.dados, name="dados"),
    path("eventos/", views.eventos, name="eventos"),
    path("eventos/novo/", views.novo_evento, name="novo_evento"),
    path("eventos/<int:evento_id>/", views.evento, name="evento"),
    path("eventos/<int:evento_id>/qrcode.png", views.qrcode_png, name="qrcode"),
    path("eventos/<int:evento_id>/simular/", views.simular, name="simular"),
    path("reiniciar/", views.reiniciar, name="reiniciar"),
]
