"""Rutas principales.

Cada app añadirá aquí su include(...) cuando tenga vistas, por ejemplo:
    path("agenda/", include("apps.agenda.urls")),
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

admin.site.site_header = "Despega · administración"
admin.site.site_title = "Despega"
admin.site.index_title = "Datos de la aplicación"

urlpatterns = [
    # B01 · Portada «¿Quién eres?»: Estudiante o Adulto (HU-01-06). Sin lógica: solo dos enlaces.
    path("", TemplateView.as_view(template_name="usuarios/portada.html"), name="inicio"),
    path("admin/", admin.site.urls),
    path("agenda/", include("apps.agenda.urls")),
    path("tareas/", include("apps.tareas.urls")),
    path("horario/", include("apps.horario.urls")),
    path("perfil/", include("apps.perfil.urls")),
    # Entrar, salir y panel del adulto: /entrar/, /salir/ y /panel/ (HU-01-07).
    path("", include("apps.usuarios.urls")),
]

# En desarrollo, Django sirve las imágenes subidas. En la demo lo hace Caddy.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
