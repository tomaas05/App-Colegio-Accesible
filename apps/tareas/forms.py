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
        self.fields['imagen'].required = False  # Permite inyección vía ARASAAC en views.py

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
        self.fields['imagen'].required = False  # Permite inyección vía ARASAAC en views.py
        self.fields['descripcion_imagen'].required = True

# Definición y exportación del formset que faltaba o estaba mal nombrado
PasoFormSet = inlineformset_factory(
    Tarea,
    Paso,
    form=PasoForm,
    extra=0,
    can_delete=True,
)
