"""Configuración para pytest (local y GitHub Actions)."""

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "clave-solo-para-pruebas"

# Hash rápido: Argon2 ralentizaría mucho las pruebas.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# En las pruebas no interesa que axes bloquee entre casos.
AXES_ENABLED = False
