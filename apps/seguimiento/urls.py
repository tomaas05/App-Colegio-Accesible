from django.urls import path

from . import views

app_name = "seguimiento"

urlpatterns = [
    # HU-06-02: cómo van hoy los estudiantes del tutor o del profesional (B50).
    path("", views.hoy, name="hoy"),
]
