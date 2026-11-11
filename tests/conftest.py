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


@pytest.fixture(autouse=True)
def cache_limpia():
    """La caché (búsquedas de pictogramas, límite de peticiones) empieza vacía en cada prueba."""
    from django.core.cache import cache

    cache.clear()


@pytest.fixture
def arasaac(monkeypatch):
    """ARASAAC de mentira: ninguna prueba sale a Internet (decisión 0004)."""
    from apps.comun import pictogramas

    from .arasaac_falso import ArasaacFalso

    falso = ArasaacFalso()
    monkeypatch.setattr(pictogramas.requests, "get", falso.get)
    return falso


@pytest.fixture(autouse=True)
def sin_internet(request, monkeypatch):
    """Si una prueba intenta salir a ARASAAC sin el fixture `arasaac`, falla con un aviso claro."""
    if "arasaac" in request.fixturenames:
        return
    from apps.comun import pictogramas

    def prohibido(url, **opciones):
        raise AssertionError(f"Esta prueba ha intentado salir a Internet: {url}")

    monkeypatch.setattr(pictogramas.requests, "get", prohibido)
