"""Formulario del perfil del estudiante (HU-04-01, HU-04-02, HU-07-01)."""

from django import forms

from .models import (
    AlcanceAgenda,
    ContenidoBotones,
    CreacionTareas,
    MaxTarjetas,
    Perfil,
    TipoTemporizador,
)


class PerfilVisualForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = [
            "tema",
            "paleta",
            "tipo_letra",
            "tamano_letra",
            "tamano_botones",
            "contenido_botones",
            "alcance_agenda",
            "max_tarjetas",
            "tipo_temporizador",
            "temporizador_visible",
            "puede_ocultar_temporizador",
            "aviso_5_min",
            "aviso_1_min",
            "sonidos_activos",
            "baja_sobrecarga_sensorial",
            "creacion_tareas",
            "usa_lector_pantalla",
        ]
        widgets = {
            "tema": forms.RadioSelect,
            "paleta": forms.RadioSelect,
            "tipo_letra": forms.RadioSelect,
            "tamano_letra": forms.RadioSelect,
            "tamano_botones": forms.RadioSelect,
            "contenido_botones": forms.RadioSelect,
            "alcance_agenda": forms.RadioSelect,
            "max_tarjetas": forms.RadioSelect,
            "tipo_temporizador": forms.RadioSelect,
            "creacion_tareas": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in (
            "contenido_botones",
            "alcance_agenda",
            "max_tarjetas",
            "tipo_temporizador",
            "creacion_tareas",
        ):
            self.fields[campo].required = False

    def clean_contenido_botones(self):
        valor = self.cleaned_data.get("contenido_botones")
        if valor:
            return valor
        if self.instance and self.instance.pk and self.instance.contenido_botones:
            return self.instance.contenido_botones
        return ContenidoBotones.AMBOS

    def clean_alcance_agenda(self):
        valor = self.cleaned_data.get("alcance_agenda")
        if valor:
            return valor
        if self.instance and self.instance.pk and self.instance.alcance_agenda:
            return self.instance.alcance_agenda
        return AlcanceAgenda.SEMANA

    def clean_max_tarjetas(self):
        valor = self.cleaned_data.get("max_tarjetas")
        if valor:
            return valor
        if self.instance and self.instance.pk and self.instance.max_tarjetas:
            return self.instance.max_tarjetas
        return MaxTarjetas.SEIS

    def clean_tipo_temporizador(self):
        valor = self.cleaned_data.get("tipo_temporizador")
        if valor:
            return valor
        if self.instance and self.instance.pk and self.instance.tipo_temporizador:
            return self.instance.tipo_temporizador
        return TipoTemporizador.LINEAL

    def clean_creacion_tareas(self):
        valor = self.cleaned_data.get("creacion_tareas")
        if valor:
            return valor
        if self.instance and self.instance.pk:
            return self.instance.creacion_tareas
        return CreacionTareas.NINGUNA

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

    def _limpiar_booleano_por_defecto_true(self, nombre_campo):
        if self.data and "tipo_temporizador" not in self.data and nombre_campo not in self.data:
            if self.instance and self.instance.pk:
                return getattr(self.instance, nombre_campo)
            return True
        return bool(self.cleaned_data.get(nombre_campo))

    def clean_aviso_5_min(self):
        return self._limpiar_booleano_por_defecto_true("aviso_5_min")

    def clean_aviso_1_min(self):
        return self._limpiar_booleano_por_defecto_true("aviso_1_min")

    def clean_sonidos_activos(self):
        return self._limpiar_booleano_por_defecto_true("sonidos_activos")
