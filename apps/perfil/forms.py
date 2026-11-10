"""Formulario de configuración del perfil visual del estudiante (HU-04-01)."""

from django import forms

from .models import Perfil


class PerfilVisualForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = [
            "tema",
            "paleta",
            "tipo_letra",
            "tamano_letra",
            "tamano_botones",
            "usa_lector_pantalla",
        ]
        widgets = {
            "tema": forms.RadioSelect,
            "paleta": forms.RadioSelect,
            "tipo_letra": forms.RadioSelect,
            "tamano_letra": forms.RadioSelect,
            "tamano_botones": forms.RadioSelect,
        }
