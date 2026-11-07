"""Crea el perfil con los valores por defecto al crear un estudiante."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.usuarios.models import Estudiante

from .models import Perfil


@receiver(post_save, sender=Estudiante)
def crear_perfil(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        Perfil.objects.get_or_create(estudiante=instance)
