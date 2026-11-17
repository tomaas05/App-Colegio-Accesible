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
]
