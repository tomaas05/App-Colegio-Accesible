"""HU-06-03 · Consultar el día del estudiante (Manu).

El familiar ve, desde el móvil, el día de su estudiante: sus tareas en modo consulta (PA1 y
PA2), si ha ido al comedor (PA3) y el menú del mes (PA4). Solo el estudiante con el que
está vinculado (PA5, `estudiantes_de` en apps/usuarios/vinculos.py).

Reutiliza: las tareas, de la agenda en modo consulta (apps/usuarios/consulta.py, HU-01-09);
el comedor y el menú, de las funciones que Javi dejó para esto en apps/centro
(`comedor_de`, HU-05-04, y `menu_del_mes`, HU-05-03).
"""

from dataclasses import dataclass

from apps.centro import comedor as comedor_del_centro
from apps.centro import servicios as centro


@dataclass(frozen=True)
class Comedor:
    """Si ha ido al comedor ese día, contado para el familiar."""

    estado: str  # come, no_come, sin_saber, sin_anotar, no_hay, no_ha_llegado
    simbolo: str
    texto: str


def comedor(estudiante, fecha, hoy):
    """PA3. Solo cuenta lo que el encargado ha dado por terminado: hasta entonces la marca
    se puede cambiar y se dice «todavía no se sabe» (HU-05-04, RF5.2.5)."""
    if fecha.isoweekday() not in centro.DIAS_LECTIVOS:
        return Comedor("no_hay", "–", "Los sábados y los domingos no hay comedor.")
    if fecha > hoy:
        return Comedor("no_ha_llegado", "–", "Este día todavía no ha llegado.")
    resultado = comedor_del_centro.comedor_de(estudiante, fecha)
    nombre = estudiante.usuario.first_name
    if resultado == comedor_del_centro.COME:
        return Comedor("come", "✓", f"{nombre} ha ido al comedor.")
    if resultado == comedor_del_centro.NO_COME:
        return Comedor("no_come", "✕", f"{nombre} no ha ido al comedor.")
    if fecha == hoy:
        return Comedor("sin_saber", "⏳", "Todavía no se sabe: aún no se ha anotado.")
    return Comedor("sin_anotar", "–", "Ese día no se anotó.")


@dataclass(frozen=True)
class Menu:
    """PA4. El menú del mes que ha subido el colegio (PDF o imagen), si lo ha subido."""

    archivo: object  # FieldFile o None
    mes: str  # «noviembre de 2026»

    @property
    def es_imagen(self):
        return bool(self.archivo) and centro.menu_es_imagen(self.archivo)


def menu(fecha):
    return Menu(centro.menu_del_mes(fecha), centro.nombre_mes(fecha))
