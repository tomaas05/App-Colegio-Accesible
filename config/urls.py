"""Rutas principales.

Cada app añadirá aquí su include(...) cuando tenga vistas, por ejemplo:
    path("agenda/", include("apps.agenda.urls")),
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.usuarios import views as usuarios_views

admin.site.site_header = "Despega · administración"
admin.site.site_title = "Despega"
admin.site.index_title = "Datos de la aplicación"

urlpatterns = [
    # B01 + B02 · Portada: «¿Cuál es tu clase?» y, en pequeño, la entrada de adultos (HU-01-06).
    path("", usuarios_views.portada, name="inicio"),
    path("admin/", admin.site.urls),
    path("agenda/", include("apps.agenda.urls")),
    path("tareas/", include("apps.tareas.urls")),
    path("horario/", include("apps.horario.urls")),
    path("perfil/", include("apps.perfil.urls")),
    path("centro/", include("apps.centro.urls")),
    # Buscador de pictogramas de ARASAAC en el servidor (decisión 0004).
    path("pictogramas/", include("apps.comun.urls")),
    # Entrar, salir y panel del adulto: /entrar/, /salir/ y /panel/ (HU-01-07).
    path("", include("apps.usuarios.urls")),
]

# En desarrollo, Django sirve las imágenes subidas. En la demo lo hace Caddy.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
