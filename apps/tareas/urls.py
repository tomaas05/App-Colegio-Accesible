from django.urls import path

from . import views

app_name = "tareas"

urlpatterns = [
    path("crear/", views.crear_tarea, name="crear_tarea"),
    path("anadir-paso/", views.anadir_paso, name="anadir_paso"),
    path("catalogo/", views.catalogo_tareas, name="catalogo"),
    path("asignar/", views.asignar_tarea, name="asignar_tarea"),
    path("asignar/<int:tarea_id>/", views.asignar_tarea, name="asignar_tarea_con_id"),
    path("planificadas/", views.tareas_planificadas, name="tareas_planificadas"),
    path(
        "asignaciones/<int:asignacion_id>/editar/",
        views.editar_asignacion,
        name="editar_asignacion",
    ),
    path(
        "asignaciones/<int:asignacion_id>/cancelar/",
        views.cancelar_asignacion,
        name="confirmar_cancelacion",
    ),
    path("<int:tarea_id>/pasos/", views.editar_pasos_tarea, name="editar_pasos_tarea"),
]
