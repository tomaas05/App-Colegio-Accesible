"""Pruebas de humo: comprueban que la instalación está bien, no funcionalidad."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse


def test_modelo_de_usuario_propio():
    assert settings.AUTH_USER_MODEL == "usuarios.Usuario"
    assert get_user_model()._meta.label == "usuarios.Usuario"


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


def test_admin_abre_todas_las_tablas(client, datos):
    """El admin es la herramienta del equipo mientras no hay pantallas propias."""
    from django.contrib import admin

    client.force_login(get_user_model().objects.get(username="admin"))
    for modelo in admin.site._registry:
        meta = modelo._meta
        url = reverse(f"admin:{meta.app_label}_{meta.model_name}_changelist")
        assert client.get(url).status_code == 200, url
        primero = modelo.objects.first()
        if primero:
            url = reverse(f"admin:{meta.app_label}_{meta.model_name}_change", args=[primero.pk])
            assert client.get(url).status_code == 200, url
