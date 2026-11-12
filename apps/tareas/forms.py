from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from apps.comun import pictogramas
from apps.usuarios.vinculos import estudiantes_de

from .models import Asignacion, DiaSemana, Estudiante, Paso, Tarea

FALTA_IMAGEN = "Sube una imagen o elige un pictograma de ARASAAC."


def _id_de_pictograma(valor):
    """ "" si no se ha elegido pictograma, o su número. Cualquier otra cosa es un error."""
    if not valor:
        return ""
    try:
        return pictogramas.id_valido(valor)
    except pictogramas.IdentificadorNoValido:
        raise ValidationError("Ese pictograma no existe. Elige otro.") from None


class ConPictograma:
    """Para volver a enseñar el pictograma elegido si el formulario vuelve con errores."""

    campo_pictograma = ""

    @property
    def pictograma_elegido(self):
        """El número elegido, solo si es válido (nunca se pinta lo que no sea un número)."""
        try:
            return pictogramas.id_valido(self[self.campo_pictograma].value() or "")
        except pictogramas.IdentificadorNoValido:
            return ""


class TareaForm(ConPictograma, forms.ModelForm):
    campo_pictograma = "arasaac_id_tarea"
    arasaac_id_tarea = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Tarea
        fields = ["nombre", "descripcion", "imagen", "descripcion_imagen", "ambito"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "descripcion_imagen": forms.TextInput(attrs={"class": "form-control"}),
            "ambito": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["descripcion_imagen"].required = True
        # La imagen puede ser un archivo o un pictograma de ARASAAC: lo comprueba clean().
        self.fields["imagen"].required = False

    def clean_arasaac_id_tarea(self):
        return _id_de_pictograma(self.cleaned_data.get("arasaac_id_tarea"))

    def clean(self):
        datos = super().clean()
        sin_error_previo = "imagen" not in self.errors and "arasaac_id_tarea" not in self.errors
        if sin_error_previo and not datos.get("imagen") and not datos.get("arasaac_id_tarea"):
            self.add_error("imagen", FALTA_IMAGEN)
        return datos


class PasoForm(ConPictograma, forms.ModelForm):
    campo_pictograma = "arasaac_id_paso"
    arasaac_id_paso = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Paso
        fields = ["orden", "imagen", "descripcion", "descripcion_imagen", "arasaac_id_paso"]
        widgets = {
            "orden": forms.NumberInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "descripcion_imagen": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["imagen"].required = False  # archivo o pictograma: lo comprueba clean()
        self.fields["descripcion_imagen"].required = True

    def clean_arasaac_id_paso(self):
        return _id_de_pictograma(self.cleaned_data.get("arasaac_id_paso"))

    def clean(self):
        datos = super().clean()
        sin_error_previo = "imagen" not in self.errors and "arasaac_id_paso" not in self.errors
        if (
            sin_error_previo
            and not datos.get("DELETE")
            and not datos.get("imagen")
            and not datos.get("arasaac_id_paso")
        ):
            self.add_error("imagen", FALTA_IMAGEN)
        return datos


PasoFormSet = inlineformset_factory(
    Tarea,
    Paso,
    form=PasoForm,
    extra=0,
    can_delete=True,
)

# --- Asignar una tarea (HU-03-03) ---


class AsignacionForm(forms.ModelForm):
    estudiantes = forms.ModelMultipleChoiceField(
        queryset=Estudiante.objects.none(),  # se pone en __init__: solo los de quien asigna
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=True,
        label="Estudiantes",
    )

    dias_semana = forms.MultipleChoiceField(
        choices=DiaSemana.choices,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=True,
        label="Días de la semana",
        help_text="1 = lunes … 7 = domingo",
    )

    class Meta:
        model = Asignacion
        fields = [
            "tarea",
            "estudiantes",
            "hora_inicio",
            "hora_fin",
            "dias_semana",
            "vigencia_desde",
            "vigencia_hasta",
        ]
        widgets = {
            "tarea": forms.Select(attrs={"class": "form-select"}),
            "hora_inicio": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_fin": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "vigencia_desde": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "vigencia_hasta": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Única regla de visibilidad (docs/contribuir.md): cada adulto, solo sus estudiantes.
        self.fields["estudiantes"].queryset = estudiantes_de(usuario)
        self.fields["estudiantes"].label_from_instance = lambda e: (
            f"{e.usuario.get_full_name()} ({e.clase.nombre})"
        )
        self.fields["dias_semana"].help_text = ""

    def clean_dias_semana(self):
        datos = self.cleaned_data.get("dias_semana")
        if datos:
            return [int(d) for d in datos]
        return []

    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get("hora_inicio")
        hora_fin = cleaned_data.get("hora_fin")
        estudiantes = cleaned_data.get("estudiantes")
        dias_semana = cleaned_data.get("dias_semana")
        vigencia_desde = cleaned_data.get("vigencia_desde")
        vigencia_hasta = cleaned_data.get("vigencia_hasta")

        if hora_inicio and hora_fin and hora_fin <= hora_inicio:
            raise ValidationError(
                "La hora de fin no puede ser anterior o igual a la hora de inicio."
            )

        if estudiantes and hora_inicio and hora_fin and dias_semana:
            from datetime import date

            for estudiante in estudiantes:
                solapes = Asignacion.objects.filter(
                    estudiante=estudiante, hora_inicio__lt=hora_fin, hora_fin__gt=hora_inicio
                )

                if self.instance.pk:
                    solapes = solapes.exclude(pk=self.instance.pk)

                conflicto_encontrado = False
                for asignacion_existente in solapes:
                    dias_en_comun = set(dias_semana) & set(asignacion_existente.dias_semana)
                    if dias_en_comun:
                        v_desde = vigencia_desde or date.min
                        v_hasta = vigencia_hasta or date.max
                        ae_desde = asignacion_existente.vigencia_desde or date.min
                        ae_hasta = asignacion_existente.vigencia_hasta or date.max

                        if v_desde <= ae_hasta and v_hasta >= ae_desde:
                            conflicto_encontrado = True
                            tarea_choca = asignacion_existente.tarea.nombre
                            break

                if conflicto_encontrado:
                    raise ValidationError(
                        f"El estudiante {estudiante} ya tiene una tarea asignada "
                        f"en ese horario y día ({tarea_choca})."
                    )

        return cleaned_data
