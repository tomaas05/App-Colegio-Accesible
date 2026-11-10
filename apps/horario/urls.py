from django.urls import path

from . import views

app_name = "horario"

urlpatterns = [
    # HU-03-11: el administrador carga el horario de cada clase (B37).
    path("", views.cargar_horario, name="cargar"),
    # HU-03-11, PA1: el estudiante ve el horario de su clase.
    path("mi-horario/", views.mi_horario, name="mi_horario"),
]
