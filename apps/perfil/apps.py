from django.apps import AppConfig


class PerfilConfig(AppConfig):
    """Perfil visual del estudiante y temporizador (Objetivo 4). Dueño: Jorge."""

    name = "apps.perfil"
    label = "perfil"
    verbose_name = "Perfil del estudiante"

    def ready(self):
        from . import signals  # noqa: F401  (crea el perfil al crear un estudiante)
