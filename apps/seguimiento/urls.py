from django.urls import path

from . import views, views_familiar

app_name = "seguimiento"

urlpatterns = [
    # HU-06-02: cómo van hoy los estudiantes del tutor o del profesional (B50).
    path("", views.hoy, name="hoy"),
    # HU-06-03: el familiar consulta el día de su estudiante (B34 y B35).
    path("dia/", views_familiar.elegir, name="familiar"),
    path("dia/<str:codigo>/", views_familiar.dia_del_estudiante, name="dia"),
]
