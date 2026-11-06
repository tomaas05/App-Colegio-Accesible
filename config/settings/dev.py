"""Configuración para desarrollo en el equipo de cada miembro."""

from .base import *  # noqa: F403
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)

# Muestra los correos en la consola en lugar de enviarlos.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
