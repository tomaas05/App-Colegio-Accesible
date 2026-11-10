"""Formulario del perfil visual y temporizador del estudiante (HU-04-01, HU-07-01)."""

from django import forms

from .models import Perfil, TipoTemporizador


class PerfilVisualForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = [
            "tema",
            "paleta",
            "tipo_letra",
            "tamano_letra",
            "tamano_botones",
            "tipo_temporizador",
            "temporizador_visible",
            "puede_ocultar_temporizador",
            "usa_lector_pantalla",
        ]
        widgets = {
            "tema": forms.RadioSelect,
            "paleta": forms.RadioSelect,
            "tipo_letra": forms.RadioSelect,
            "tamano_letra": forms.RadioSelect,
            "tamano_botones": forms.RadioSelect,
            "tipo_temporizador": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_temporizador"].required = False

    def clean_tipo_temporizador(self):
        valor = self.cleaned_data.get("tipo_temporizador")
        if valor:
            return valor
        if self.instance and self.instance.pk and self.instance.tipo_temporizador:
            return self.instance.tipo_temporizador
        return TipoTemporizador.LINEAL

    def clean_temporizador_visible(self):
        if (
            self.data
            and "tipo_temporizador" not in self.data
            and "temporizador_visible" not in self.data
        ):
            if self.instance and self.instance.pk:
                return self.instance.temporizador_visible
            return True
        return bool(self.cleaned_data.get("temporizador_visible"))
