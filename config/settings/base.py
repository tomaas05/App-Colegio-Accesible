"""Configuración común de Despega.

Los valores que cambian entre equipos o entornos se leen del archivo .env
(ver .env.example). dev.py y test.py heredan de aquí.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="solo-para-desarrollo-no-usar-en-demo")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# ---------------------------------------------------------------------------
# Aplicaciones. Una app de Django por objetivo de la Propuesta Técnica.
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "django_htmx",
    "axes",
]
LOCAL_APPS = [
    "apps.usuarios",  # Usuarios y acceso (Manu)
    "apps.agenda",  # Agenda del estudiante y ejecución (Tomás)
    "apps.tareas",  # Tareas, pasos y asignaciones (Úrsula)
    "apps.perfil",  # Perfil visual y temporizador (Jorge)
    "apps.horario",  # Horario escolar y vista del adulto (Javi)
    "apps.centro",  # Tareas del centro (iteración 2)
    "apps.seguimiento",  # Seguimiento y bienestar (iteración 2)
    "apps.comun",  # Utilidades compartidas: datos de prueba
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    # AxesMiddleware debe ir el último.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.perfil.context_processors.perfil_estudiante",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Base de datos: PostgreSQL 16+
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="despega"),
        "USER": env("POSTGRES_USER", default="despega"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="despega"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------
# Modelo de usuario propio (docs/iteracion-1/base-datos/diccionario.md).
AUTH_USER_MODEL = "usuarios.Usuario"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # debe ir el primero
    "django.contrib.auth.backends.ModelBackend",
]

# Argon2 como algoritmo principal (RNF1.1.4)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# django-axes: valores de RNF1.2.3 (5 intentos, 5 minutos de bloqueo).
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 5 / 60  # en horas
AXES_RESET_ON_SUCCESS = True
# Se bloquea la pareja usuario + equipo, no la IP sola: en el colegio todas las tabletas
# salen por la misma IP y un adulto que falla no debe dejar fuera a los demás.
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
# Lo que se ve al quedar bloqueado (HU-01-07, prueba de aceptación 5).
AXES_LOCKOUT_TEMPLATE = "usuarios/bloqueado.html"

# Entrada y salida (HU-01-07 y HU-01-06). Quien no ha entrado va a la portada
# «¿Quién eres?», que lleva a la entrada del estudiante o a la del adulto.
# Tras entrar, cada rol va a su pantalla: lo decide la vista, porque
# LOGIN_REDIRECT_URL solo admite una.
LOGIN_URL = "inicio"
LOGIN_REDIRECT_URL = "usuarios:panel"
LOGOUT_REDIRECT_URL = "inicio"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ---------------------------------------------------------------------------
# Idioma y hora
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estáticos. Todo se sirve desde nuestro servidor: ninguna fuente,
# librería ni imagen se carga de terceros (RNF1.1.2).
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Imágenes subidas (tareas, pasos, avatares, asignaturas). Carpeta fuera de Git.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Django REST Framework (solo para los pocos endpoints JSON)
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
