from django import forms
from django.forms import inlineformset_factory
from .models import Tarea, Paso

class TareaForm(forms.ModelForm):
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
        self.fields['descripcion_imagen'].required = True
        self.fields['imagen'].required = False  # Permite inyección vía ARASAAC in views.py

class PasoForm(forms.ModelForm):
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
        self.fields['imagen'].required = False  # Permite inyección vía ARASAAC in views.py
        self.fields['descripcion_imagen'].required = True

PasoFormSet = inlineformset_factory(
    Tarea,
    Paso,
    form=PasoForm,
    extra=0,
    can_delete=True,
)

# --- AÑADIDO EXCLUSIVAMENTE PARA ASIGNAR TAREA (SIN CAMBIAR NADA ANTERIOR) ---
from .models import Asignacion, Estudiante, DiaSemana
from django.core.exceptions import ValidationError

class AsignacionForm(forms.ModelForm):
    estudiantes = forms.ModelMultipleChoiceField(
        queryset=Estudiante.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=True,
        label="Estudiantes"
    )

    dias_semana = forms.MultipleChoiceField(
        choices=DiaSemana.choices,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=True,
        label="Días de la semana",
        help_text="1 = lunes … 7 = domingo"
    )

    class Meta:
        model = Asignacion
        fields = ["tarea", "estudiantes", "hora_inicio", "hora_fin", "dias_semana", "vigencia_desde", "vigencia_hasta"]
        widgets = {
            "tarea": forms.Select(attrs={"class": "form-select"}),
            "hora_inicio": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_fin": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "vigencia_desde": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "vigencia_hasta": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

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
                    estudiante=estudiante,
                    hora_inicio__lt=hora_fin,
                    hora_fin__gt=hora_inicio
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
                        f"El estudiante {estudiante} ya tiene una tarea asignada en ese horario y día ({tarea_choca})."
                    )

        return cleaned_data
