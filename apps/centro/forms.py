"""Formularios de HU-05-03 (Javi): comedor de un día, reparto del menú y menú del mes.

Solo comprueban que llegan los datos. Lo demás (días que ya han pasado, choques con otras
tareas, sustituir al estudiante) está en servicios.py.
"""

from datetime import date

from django import forms
from django.core.validators import FileExtensionValidator

from apps.usuarios.vinculos import estudiantes_de

from . import servicios
from .models import EXTENSIONES_MENU

MENU_MAXIMO_MB = 5


class _Horas(forms.Form):
    hora_inicio = forms.TimeField(
        label="Hora de inicio",
        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        error_messages={"required": "Pon la hora de inicio.", "invalid": "Escribe una hora."},
    )
    hora_fin = forms.TimeField(
        label="Hora de fin",
        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        error_messages={"required": "Pon la hora de fin.", "invalid": "Escribe una hora."},
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Un estudiante, de entre los que ve el administrador (todos los activos).
        self.fields["estudiante"].queryset = estudiantes_de(usuario).order_by(
            "clase__nombre", "usuario__first_name", "usuario__last_name"
        )
        self.fields["estudiante"].label_from_instance = lambda e: (
            f"{e.usuario.get_full_name()} ({e.clase.nombre})"
        )

    def clean(self):
        datos = super().clean()
        inicio, fin = datos.get("hora_inicio"), datos.get("hora_fin")
        if inicio and fin and fin <= inicio:
            self.add_error("hora_fin", "La hora de fin tiene que ser después de la de inicio.")
        return datos


class FormComedor(_Horas):
    """PA1 y PA3: el comedor de un día, con su estudiante y su horario."""

    prefix = "comedor"
    field_order = ["dia", "estudiante", "hora_inicio", "hora_fin"]

    dia = forms.TypedChoiceField(
        label="Día",
        coerce=date.fromisoformat,
        error_messages={
            "required": "Elige un día.",
            "invalid_choice": "Elige un día de la lista.",
        },
    )
    estudiante = forms.ModelChoiceField(
        label="Estudiante",
        queryset=None,
        empty_label="Elige un estudiante",
        error_messages={
            "required": "Elige un estudiante.",
            "invalid_choice": "Elige uno de la lista.",
        },
    )

    def __init__(self, *args, mes, **kwargs):
        super().__init__(*args, **kwargs)
        hoy = servicios.hoy()
        self.fields["dia"].choices = [("", "Elige un día")] + [
            (d.isoformat(), servicios.texto_fecha(d).capitalize())
            for d in servicios.dias_lectivos(mes)
            if d >= hoy
        ]


class FormReparto(_Horas):
    """PA2 y PA3: el reparto del menú de un mes, con su estudiante y su horario."""

    prefix = "reparto"
    field_order = ["estudiante", "dias", "hora_inicio", "hora_fin"]

    estudiante = forms.ModelChoiceField(
        label="Estudiante",
        queryset=None,
        empty_label="Elige un estudiante",
        error_messages={
            "required": "Elige un estudiante.",
            "invalid_choice": "Elige uno de la lista.",
        },
    )
    dias = forms.TypedMultipleChoiceField(
        label="Días de la semana",
        choices=[(d, servicios.DIAS[d - 1].capitalize()) for d in servicios.DIAS_LECTIVOS],
        coerce=int,
        widget=forms.CheckboxSelectMultiple,
        initial=servicios.DIAS_LECTIVOS,
        error_messages={"required": "Elige al menos un día."},
    )


class FormMenu(forms.Form):
    """El menú del mes (PDF o imagen), para que el familiar lo vea (HU-06-03)."""

    prefix = "menu"

    archivo = forms.FileField(
        label="Menú del mes (PDF o imagen)",
        validators=[FileExtensionValidator(EXTENSIONES_MENU)],
        error_messages={"required": "Elige el archivo del menú."},
        widget=forms.FileInput(attrs={"accept": ".pdf,image/png,image/jpeg,image/webp"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if archivo.size > MENU_MAXIMO_MB * 1024 * 1024:
            raise forms.ValidationError(f"El archivo pesa más de {MENU_MAXIMO_MB} MB.")
        return archivo
