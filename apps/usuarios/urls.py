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
    # HU-01-01: cuentas (solo el administrador).
    path("usuarios/", views.lista_usuarios, name="lista"),
    path("usuarios/nueva/", views.crear_cuenta, name="crear"),
    path("usuarios/cargar/", views.cargar_estudiantes, name="cargar"),
    path("usuarios/cargar/plantilla.csv", views.plantilla_csv, name="plantilla"),
]
