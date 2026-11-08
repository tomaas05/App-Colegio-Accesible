from django.urls import path
from . import views

app_name = "tareas"

urlpatterns = [
    path("crear/", views.crear_tarea, name="crear_tarea"),
    path("anadir-paso/", views.anadir_paso, name="anadir_paso"),
    path('catalogo/', views.catalogo_tareas, name='catalogo'),
]
