from django.urls import path

from . import views

app_name = "centro"

urlpatterns = [
    # HU-05-03: el administrador asigna el comedor de cada día y el reparto del menú del mes.
    path("comedor/", views.comedor, name="comedor"),
    # HU-05-04: el estudiante encargado del comedor de hoy anota quién come.
    path("comedor/hoy/", views.comedor_hoy, name="comedor_hoy"),
    path("comedor/hoy/clase/<int:pk>/", views.comedor_clase, name="comedor_clase"),
    path(
        "comedor/hoy/clase/<int:pk>/marcar/<str:codigo>/",
        views.comedor_marcar,
        name="comedor_marcar",
    ),
    path("comedor/hoy/clase/<int:pk>/terminar/", views.comedor_terminar, name="comedor_terminar"),
    # HU-05-01: el tutor o el administrador crea una tarea de reprografía.
    path("reprografia/", views.reprografia_lista, name="reprografia"),
    path("reprografia/nueva/", views.reprografia_nueva, name="reprografia_nueva"),
    path("reprografia/<int:pk>/", views.reprografia_cambiar, name="reprografia_cambiar"),
    path("reprografia/fases/", views.reprografia_fases, name="reprografia_fases"),
]
