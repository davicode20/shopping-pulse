from django.urls import path

from . import views

app_name = "inteligencia"

urlpatterns = [
    path("analise/", views.analise, name="analise"),
    path("miro/exportar/", views.exportar_miro, name="exportar_miro"),
    path("miro/csv/", views.csv_miro, name="csv_miro"),
]
