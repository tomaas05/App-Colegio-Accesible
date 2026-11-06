"""Modelos del Objetivo 1 – Gestión de usuarios, acceso y permisos.

Requisitos de información: RI1.1.1, RI1.1.2, RI1.2.1, RI1.2.2, RI1.3.1, RI1.4.1.
Entidades previstas (se definen con el modelo relacional de la iteración 1):
    SchoolClass, StudentLink, ProfessionalAccess, AuditLog.
"""

from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    """Modelo de usuario propio de Despega.

    Se crea vacío a propósito: Django recomienda definir el modelo de usuario
    antes de la primera migración, porque cambiarlo después obliga a rehacer la
    base de datos. El rol, el avatar y la clase (RI1.1.1) se añaden en la
    iteración 2, a partir del diccionario de datos.
    """

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
