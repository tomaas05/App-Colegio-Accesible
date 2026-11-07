from django.apps import AppConfig


class ComunConfig(AppConfig):
    """Utilidades compartidas por todas las apps (sin tablas propias).

    De momento solo contiene el comando cargar_datos_prueba.
    """

    name = "apps.comun"
    label = "comun"
    verbose_name = "Común"
