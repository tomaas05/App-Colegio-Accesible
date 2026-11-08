"""Formularios de usuarios y acceso (Manu).

HU-01-07: entrada de tutor, profesional, familiar y administrador (boceto B12).
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Rol


class EntrarAdultoForm(AuthenticationForm):
    """Usuario y contraseña de un adulto.

    Es el formulario de Django con los textos del boceto B12. El mensaje de error
    no dice si ha fallado el usuario o la contraseña, para no dar pistas (RF1.3.4).
    Una cuenta desactivada da el mismo mensaje: el backend de Django ni la encuentra.
    """

    username = forms.CharField(
        label="Usuario",
        max_length=150,
        error_messages={"required": "Escribe tu usuario."},
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "autocapitalize": "none",
                "spellcheck": "false",
            }
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        error_messages={"required": "Escribe tu contraseña."},
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        "invalid_login": (
            "Los datos no coinciden con una cuenta existente. Revisa tu usuario y tu contraseña."
        ),
        "inactive": "Esta cuenta está desactivada. Habla con el administrador del centro.",
        "estudiante": "Esta entrada es para adultos. Los estudiantes entran desde «Estudiante».",
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        # El estudiante entra con su avatar (HU-01-06), no por aquí.
        if user.rol == Rol.ESTUDIANTE:
            raise forms.ValidationError(self.error_messages["estudiante"], code="estudiante")
