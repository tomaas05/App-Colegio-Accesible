"""Formularios de HU-05-03 (Javi): comedor de un día, reparto del menú y menú del mes.
Y de HU-05-01: la tarea de reprografía.

Solo comprueban que llegan los datos. Lo demás (días que ya han pasado, choques con otras
tareas, sustituir al estudiante) está en servicios.py.
"""

from datetime import date

from django import forms
from django.core.validators import FileExtensionValidator

from apps.usuarios.vinculos import estudiantes_de

from . import servicios
from .models import AULA_MAXIMO, COPIAS_MAXIMO, EXTENSIONES_MENU
from .reprografia import Datos

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


# --- HU-05-01: tarea de reprografía ------------------------------------------------------

TRABAJOS = [("imprimir", "Imprimir"), ("fotocopiar", "Fotocopiar"), ("plastificar", "Plastificar")]
COLORES = [("bn", "Blanco y negro"), ("color", "Color")]


class FormReprografia(_Horas):
    """PA1 y PA2: estudiante, día y horas, y los datos del trabajo (RF5.1.1 a RF5.1.3).

    Cada dato que falta sale como error en su campo. Lo demás (día pasado, choques con
    otras tareas, si ya la ha empezado) está en reprografia.py.
    """

    prefix = "reprografia"
    field_order = [
        "estudiante", "dia", "hora_inicio", "hora_fin", "copias", "trabajos", "color", "aula",
    ]  # fmt: skip

    estudiante = forms.ModelChoiceField(
        label="Estudiante",
        queryset=None,
        empty_label="Elige un estudiante",
        error_messages={
            "required": "Elige un estudiante.",
            "invalid_choice": "Elige uno de la lista.",
        },
    )
    dia = forms.DateField(
        label="Día",
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        error_messages={"required": "Elige el día.", "invalid": "Escribe una fecha."},
    )
    copias = forms.IntegerField(
        label="Número de copias (de 1 a 99)",
        min_value=1,
        max_value=COPIAS_MAXIMO,
        widget=forms.NumberInput(attrs={"inputmode": "numeric"}),
        error_messages={
            "required": "Pon el número de copias.",
            "invalid": "Escribe un número.",
            "min_value": "Tiene que ser al menos 1 copia.",
            "max_value": f"Como mucho, {COPIAS_MAXIMO} copias.",
        },
    )
    trabajos = forms.MultipleChoiceField(
        label="Tipo de trabajo (uno o varios)",
        choices=TRABAJOS,
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            "required": "Elige el tipo de trabajo: imprimir, fotocopiar o plastificar.",
            "invalid_choice": "Elige de la lista.",
        },
    )
    color = forms.ChoiceField(
        label="Color (si se imprime o se fotocopia)",
        choices=COLORES,
        initial="bn",
        required=False,
        widget=forms.RadioSelect,
    )
    aula = forms.CharField(
        label="Aula de recogida y entrega",
        max_length=AULA_MAXIMO,
        error_messages={
            "required": "Escribe el aula.",
            "max_length": f"Como mucho, {AULA_MAXIMO} letras.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dia"].widget.attrs["min"] = servicios.hoy().isoformat()

    def clean_dia(self):
        dia = self.cleaned_data["dia"]
        if dia.isoweekday() not in servicios.DIAS_LECTIVOS:
            raise forms.ValidationError("Elige un día de lunes a viernes.")
        if dia < servicios.hoy():
            raise forms.ValidationError("Ese día ya ha pasado.")
        return dia

    def datos(self):
        d = self.cleaned_data
        return Datos(
            estudiante=d["estudiante"],
            fecha=d["dia"],
            hora_inicio=d["hora_inicio"],
            hora_fin=d["hora_fin"],
            copias=d["copias"],
            trabajos=d["trabajos"],
            color=d.get("color") == "color",
            aula=d["aula"],
        )

    @classmethod
    def de_un_trabajo(cls, fila, **kwargs):
        """El formulario de «Cambiar», con los datos que tiene ahora (las horas, las de ese día)."""
        t = fila.trabajo
        inicial = {
            "estudiante": t.asignacion.estudiante_id,
            "dia": fila.fecha,
            "hora_inicio": fila.hora_inicio,
            "hora_fin": fila.hora_fin,
            "copias": t.copias,
            "trabajos": t.trabajos,
            "color": "color" if t.color else "bn",
            "aula": t.aula,
        }
        return cls(initial=inicial, **kwargs)
