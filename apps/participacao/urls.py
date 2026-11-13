from django.urls import path

from . import views

app_name = "participacao"

urlpatterns = [
    path("interesse/", views.interesse, name="interesse"),
    path("presenca/", views.presenca, name="presenca"),
    path("perfil/", views.perfil, name="perfil"),
    path("checkin/<int:evento_id>/<str:token>/", views.checkin, name="checkin"),
    path("avaliar/<int:evento_id>/", views.avaliar, name="avaliar"),
]
