from django.urls import path

from . import views

app_name = "eventos"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("descobrir/", views.descobrir, name="descobrir"),
    path("propostas/", views.propostas, name="propostas"),
    path("minha-agenda/", views.agenda, name="agenda"),
    path("evento/<int:evento_id>/", views.detalhe, name="detalhe"),
]
