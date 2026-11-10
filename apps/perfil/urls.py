"""Rutas del módulo de perfil (HU-04-01)."""

from django.urls import path

from . import views

app_name = "perfil"

urlpatterns = [
    path("", views.elegir_estudiante, name="lista"),
    path("<str:codigo>/", views.editar_perfil, name="editar"),
]
