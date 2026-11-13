from django.urls import path

from . import views

app_name = "inteligencia"

urlpatterns = [
    path("analise/", views.analise, name="analise"),
]
