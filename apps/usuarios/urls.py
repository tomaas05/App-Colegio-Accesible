from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("entrar/", views.EntrarAdultoView.as_view(), name="entrar"),
    # Django solo deja salir con POST: un enlace no puede cerrar la sesión de nadie.
    path("salir/", LogoutView.as_view(), name="salir"),
    path("panel/", views.panel, name="panel"),
    # HU-01-06: la portada «¿Quién eres?» (B01) es la ruta "inicio" de config/urls.py.
    path("estudiante/", views.clases, name="clases"),
    path("estudiante/clase/<int:pk>/", views.avatares, name="avatares"),
    path("estudiante/<str:codigo>/entrar/", views.entrar_estudiante, name="entrar_estudiante"),
]
