"""Rutas principales.

Cada app añadirá aquí su include(...) cuando tenga vistas, por ejemplo:
    path("agenda/", include("apps.agenda.urls")),
"""

from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    # Página provisional para comprobar que la instalación funciona.
    path("", TemplateView.as_view(template_name="inicio.html"), name="inicio"),
    path("admin/", admin.site.urls),
]
