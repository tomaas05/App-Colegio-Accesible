from django.urls import path

from . import views

app_name = "agenda"

urlpatterns = [
    path("", views.dia, name="dia"),
    path("aviso/", views.aviso, name="aviso"),
    path("tarea/<int:pk>/", views.detalle, name="detalle"),
    path("tarea/<int:pk>/empezar/", views.empezar, name="empezar"),
    path("tarea/<int:pk>/terminar/", views.terminar, name="terminar"),
    path("tarea/<int:pk>/paso/<int:paso_pk>/hecho/", views.paso_hecho, name="paso_hecho"),
]
