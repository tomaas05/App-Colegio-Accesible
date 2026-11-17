"""Avisos a un usuario (HU-03-04 y HU-03-05; también HU-07-04 y HU-07-05).

Un aviso es una frase corta y, si es de una tarea, su pictograma (RF2.12.1, RNF2.3.3).
Se crea con `avisar()` y se marca como visto cuando la persona pulsa «Entendido»:
así queda registrado que lo ha visto (HU-07-05), no basta con abrir la pantalla.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class TipoAviso(models.TextChoices):
    CAMBIO = "cambio", "Cambio"
    CANCELACION = "cancelacion", "Cancelación"
    PLAN_B = "plan_b", "Plan B"
    NO_SE_PUEDE = "no_se_puede", "No se puede hacer"


class Notificacion(models.Model):
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones",
    )
    tipo = models.CharField(max_length=12, choices=TipoAviso.choices, default=TipoAviso.CAMBIO)
    mensaje = models.TextField()
    # La tarea de la que habla: su imagen es el pictograma del aviso. Puede no haberla.
    tarea = models.ForeignKey(
        "tareas.Tarea", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    leida = models.BooleanField(default=False)
    vista_el = models.DateTimeField("vista el", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "aviso"
        verbose_name_plural = "avisos"
        ordering = ["fecha_creacion", "pk"]
        indexes = [models.Index(fields=["destinatario", "leida"], name="aviso_pendiente_idx")]

    def __str__(self):
        return f"Aviso para {self.destinatario.username}"

    def marcar_vista(self):
        if not self.leida:
            self.leida = True
            self.vista_el = timezone.now()
            self.save(update_fields=["leida", "vista_el"])


def avisar(destinatario, mensaje, *, tipo=TipoAviso.CAMBIO, tarea=None):
    """Crea un aviso. Sin destinatario (un estudiante sin tutor, p. ej.) no hace nada."""
    if destinatario is None:
        return None
    return Notificacion.objects.create(
        destinatario=destinatario, mensaje=mensaje, tipo=tipo, tarea=tarea
    )


def pendientes(usuario):
    """Los avisos sin ver de un usuario, del más antiguo al más nuevo."""
    return Notificacion.objects.filter(destinatario=usuario, leida=False).select_related("tarea")
