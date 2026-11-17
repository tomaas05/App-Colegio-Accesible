from django.urls import path

from . import views

app_name = "centro"

urlpatterns = [
    # HU-05-03: el administrador asigna el comedor de cada día y el reparto del menú del mes.
    path("comedor/", views.comedor, name="comedor"),
]
