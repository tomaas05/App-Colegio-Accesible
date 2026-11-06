"""Pruebas de humo: comprueban que la instalación está bien, no funcionalidad."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse


def test_modelo_de_usuario_propio():
    assert settings.AUTH_USER_MODEL == "cuentas.Usuario"
    assert get_user_model()._meta.label == "cuentas.Usuario"


def test_contrasenas_con_argon2():
    from config.settings import base

    assert base.PASSWORD_HASHERS[0].endswith("Argon2PasswordHasher")


def test_pagina_de_inicio_responde(client):
    respuesta = client.get(reverse("inicio"))
    assert respuesta.status_code == 200
    assert b'<html lang="es">' in respuesta.content


def test_htmx_servido_desde_nuestro_servidor(client):
    respuesta = client.get(reverse("inicio"))
    assert b"/static/vendor/htmx/htmx.min.js" in respuesta.content
    assert b"unpkg.com" not in respuesta.content
    assert b"fonts.googleapis.com" not in respuesta.content


def test_base_de_datos_accesible(db):
    assert get_user_model().objects.count() == 0
