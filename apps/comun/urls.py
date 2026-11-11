from django.urls import path

from . import views

app_name = "pictogramas"

urlpatterns = [
    # Decisión 0004: el navegador solo habla con nuestro servidor.
    path("buscar/", views.buscar, name="buscar"),
    path("<int:identificador>.png", views.vista_previa, name="vista_previa"),
]
