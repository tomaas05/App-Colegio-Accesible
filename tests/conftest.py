import os

import pytest

# Playwright (síncrono) y el servidor de pruebas de Django comparten hilo en
# las pruebas e2e; sin esto Django protesta con SynchronousOnlyOperation.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture(autouse=True)
def media_temporal(settings, tmp_path):
    """Las imágenes que se suben en las pruebas van a una carpeta temporal."""
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def datos(db):
    """Base de datos con los datos de prueba del comando cargar_datos_prueba."""
    from django.core.management import call_command

    call_command("cargar_datos_prueba", verbosity=0)
