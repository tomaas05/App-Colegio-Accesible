"""Formularios de usuarios y acceso (Manu).

HU-01-07: entrada de tutor, profesional, familiar y administrador (boceto B12).
HU-01-06: entrada del estudiante con 3 imágenes o con contraseña.
HU-01-01: crear una cuenta (B21) y cargar una lista de estudiantes.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from apps.perfil.models import MetodoAcceso

from .acceso import IMAGENES_POR_CONTRASENA, comprobar_contrasena_imagenes
from .altas import PREFIJO_ESTUDIANTE, crear_adulto, crear_estudiante
from .models import Clase, ImagenAcceso, Rol, Usuario

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


# --- HU-01-01 · Crear un usuario (solo el administrador) ---------------------

ROLES_ADULTO = [Rol.TUTOR, Rol.PROFESIONAL, Rol.FAMILIAR, Rol.ADMINISTRADOR]
TAMANO_MAXIMO_AVATAR = 2 * 1024 * 1024  # 2 MB


class CrearCuentaForm(forms.Form):
    """B21 · Crear cuenta. Los campos obligatorios dependen del rol.

    Un estudiante necesita clase y forma de entrar (3 imágenes o contraseña);
    un adulto, usuario y contraseña inicial. Todo se comprueba aquí, en el
    servidor, aunque el navegador esconda las secciones que no tocan.
    """

    rol = forms.ChoiceField(
        label="Rol",
        choices=[("", "Elige un rol"), *Rol.choices],
        error_messages={"required": "Elige el rol."},
    )
    nombre = forms.CharField(
        label="Nombre", max_length=150, error_messages={"required": "Escribe el nombre."}
    )
    apellidos = forms.CharField(label="Apellidos", max_length=150, required=False)

    # Estudiante
    clase = forms.ModelChoiceField(
        label="Clase",
        queryset=Clase.objects.all(),
        required=False,
        empty_label="Elige una clase",
    )
    avatar = forms.ImageField(
        label="Avatar (opcional)",
        required=False,
        help_text="Un dibujo, nunca una foto. Si no subes ninguno, se dibuja uno con su inicial.",
    )
    metodo_acceso = forms.ChoiceField(
        label="Cómo entra",
        choices=MetodoAcceso.choices,
        initial=MetodoAcceso.IMAGENES,
        required=False,
        widget=forms.RadioSelect,
    )
    imagenes = forms.ModelMultipleChoiceField(
        label="Sus 3 imágenes",
        queryset=ImagenAcceso.objects.filter(activa=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    contrasena_estudiante = forms.CharField(
        label="Su contraseña",
        required=False,
        strip=False,
        min_length=4,
        widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
        error_messages={"min_length": "La contraseña debe tener al menos 4 caracteres."},
    )
    usa_lector_pantalla = forms.BooleanField(
        label="Usa lector de pantalla (VoiceOver, TalkBack…)", required=False
    )

    # Adulto
    usuario = forms.CharField(
        label="Usuario",
        max_length=150,
        required=False,
        validators=[Usuario.username_validator],
        help_text="Con el que entrará. Letras, números y . @ + - _",
        widget=forms.TextInput(
            attrs={"autocomplete": "off", "autocapitalize": "none", "spellcheck": "false"}
        ),
    )
    contrasena = forms.CharField(
        label="Contraseña inicial",
        required=False,
        strip=False,
        help_text="Mínimo 8 caracteres. Que no sea solo números ni se parezca al usuario.",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}, render_value=True),
    )
    correo = forms.EmailField(label="Correo electrónico (opcional)", required=False)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and avatar.size > TAMANO_MAXIMO_AVATAR:
            raise forms.ValidationError("La imagen no puede pasar de 2 MB.")
        return avatar

    def clean_usuario(self):
        usuario = self.cleaned_data.get("usuario", "").strip()
        # «est-a07» es el usuario interno del estudiante A07 (altas.crear_estudiante):
        # si un adulto lo cogiera, el alta de ese estudiante fallaría más adelante.
        if usuario.lower().startswith(PREFIJO_ESTUDIANTE):
            raise forms.ValidationError(
                f"Los usuarios que empiezan por «{PREFIJO_ESTUDIANTE}» son de los estudiantes. "
                "Elige otro."
            )
        if usuario and Usuario.objects.filter(username__iexact=usuario).exists():
            raise forms.ValidationError("Ese usuario ya existe. Elige otro.")
        return usuario

    def clean(self):
        datos = super().clean()
        rol = datos.get("rol")
        if rol == Rol.ESTUDIANTE:
            self._clean_estudiante(datos)
        elif rol in ROLES_ADULTO:
            self._clean_adulto(datos)
        return datos

    def _clean_estudiante(self, datos):
        if not datos.get("clase"):
            self.add_error("clase", "Elige la clase.")
        metodo = datos.get("metodo_acceso") or MetodoAcceso.IMAGENES
        datos["metodo_acceso"] = metodo
        if metodo == MetodoAcceso.IMAGENES:
            if len(datos.get("imagenes") or []) != IMAGENES_POR_CONTRASENA:
                self.add_error("imagenes", f"Elige {IMAGENES_POR_CONTRASENA} imágenes.")
        elif not datos.get("contrasena_estudiante") and "contrasena_estudiante" not in self.errors:
            self.add_error("contrasena_estudiante", "Escribe su contraseña.")

    def _clean_adulto(self, datos):
        if not datos.get("usuario") and "usuario" not in self.errors:
            self.add_error("usuario", "Escribe el usuario.")
        contrasena = datos.get("contrasena")
        if not contrasena:
            self.add_error("contrasena", "Escribe la contraseña inicial.")
        else:
            # Con un usuario provisional, para que Django rechace también una contraseña
            # parecida al usuario, al nombre o al correo («elena2026» para «elena»).
            provisional = Usuario(
                username=datos.get("usuario") or "",
                first_name=datos.get("nombre") or "",
                last_name=datos.get("apellidos") or "",
                email=datos.get("correo") or "",
            )
            try:
                validate_password(contrasena, user=provisional)
            except forms.ValidationError as error:
                self.add_error("contrasena", error)

    def crear(self):
        """Crea la cuenta con los datos ya validados y la devuelve."""
        datos = self.cleaned_data
        if datos["rol"] == Rol.ESTUDIANTE:
            return crear_estudiante(
                nombre=datos["nombre"],
                apellidos=datos["apellidos"],
                clase=datos["clase"],
                metodo_acceso=datos["metodo_acceso"],
                imagenes=datos.get("imagenes"),
                contrasena=datos.get("contrasena_estudiante", ""),
                usa_lector_pantalla=datos.get("usa_lector_pantalla", False),
                avatar=datos.get("avatar"),
            ).usuario
        return crear_adulto(
            rol=datos["rol"],
            nombre=datos["nombre"],
            apellidos=datos["apellidos"],
            usuario=datos["usuario"],
            contrasena=datos["contrasena"],
            correo=datos.get("correo", ""),
        )


class CargarListaForm(forms.Form):
    """Cargar una lista de estudiantes en una clase desde un CSV (HU-01-01, PA4)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)

    clase = forms.ModelChoiceField(
        label="Clase",
        queryset=Clase.objects.all(),
        empty_label="Elige una clase",
        error_messages={"required": "Elige la clase."},
    )
    archivo = forms.FileField(
        label="Archivo CSV",
        help_text="Columnas: nombre; apellidos; imagenes; contrasena. Máximo 500 filas.",
        error_messages={"required": "Elige el archivo."},
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if archivo.size > 1024 * 1024:
            raise forms.ValidationError("El archivo no puede pasar de 1 MB.")
        if not archivo.name.lower().endswith((".csv", ".txt")):
            raise forms.ValidationError("Tiene que ser un archivo .csv.")
        return archivo
