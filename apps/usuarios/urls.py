from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("entrar/", views.EntrarAdultoView.as_view(), name="entrar"),
    # Django solo deja salir con POST: un enlace no puede cerrar la sesión de nadie.
    path("salir/", LogoutView.as_view(), name="salir"),
    path("panel/", views.panel, name="panel"),
]
