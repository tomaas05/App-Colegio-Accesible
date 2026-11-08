"""Formularios de usuarios y acceso (Manu).

HU-01-07: entrada de tutor, profesional, familiar y administrador (boceto B12).
HU-01-06: entrada del estudiante con 3 imágenes o con contraseña.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .acceso import IMAGENES_POR_CONTRASENA, comprobar_contrasena_imagenes
from .models import ImagenAcceso, Rol

# Lo que ve el estudiante si se equivoca. No dice qué imagen o qué letra ha fallado.
NO_ES_CORRECTO = "No es correcto. Vuelve a intentarlo."


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


class EntrarConImagenesForm(forms.Form):
    """HU-01-06. El estudiante elige sus 3 imágenes de la rejilla común, en cualquier orden."""

    imagenes = forms.ModelMultipleChoiceField(
        queryset=ImagenAcceso.objects.filter(activa=True),
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            "required": f"Elige {IMAGENES_POR_CONTRASENA} imágenes.",
            "invalid_choice": NO_ES_CORRECTO,
            "invalid_pk_value": NO_ES_CORRECTO,
        },
    )

    def __init__(self, *args, usuario, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean_imagenes(self):
        imagenes = self.cleaned_data["imagenes"]
        if len(imagenes) != IMAGENES_POR_CONTRASENA:
            raise forms.ValidationError(
                f"Elige {IMAGENES_POR_CONTRASENA} imágenes.", code="cuantas"
            )
        return imagenes

    def clean(self):
        datos = super().clean()
        imagenes = datos.get("imagenes")
        if imagenes is not None and not comprobar_contrasena_imagenes(
            self.usuario, [i.pk for i in imagenes]
        ):
            raise forms.ValidationError(NO_ES_CORRECTO, code="no_coincide")
        return datos


class EntrarConContrasenaForm(forms.Form):
    """HU-01-06. El estudiante escribe su contraseña de texto."""

    password = forms.CharField(
        label="Contraseña",
        strip=False,
        error_messages={"required": "Escribe tu contraseña."},
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "autofocus": True}),
    )

    def __init__(self, *args, usuario, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean(self):
        datos = super().clean()
        contrasena = datos.get("password")
        if contrasena and not self.usuario.check_password(contrasena):
            raise forms.ValidationError(NO_ES_CORRECTO, code="no_coincide")
        return datos
