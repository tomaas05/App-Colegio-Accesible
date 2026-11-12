"""Navegación principal de los adultos (Manu). Decisión 0003.

`OPCIONES_POR_ROL` es la única lista de opciones de cada rol: de aquí salen las
tarjetas de la pantalla principal (`/panel/`, B13) y el panel lateral de todas las
pantallas de adulto (`templates/_aside.html`), para que no se desincronicen.
"""

from django.urls import NoReverseMatch, reverse

from .models import Rol

# (texto, descripción, nombre de la URL). Cada dueño añade aquí la entrada de su pantalla
# cuando la tenga. Si la URL todavía no existe, la opción no se enseña (así nadie rompe
# el panel de otro).
OPCIONES_POR_ROL = {
    Rol.ADMINISTRADOR: [
        (
            "Usuarios",
            "Ver las cuentas, crear una o cargar una lista de estudiantes.",
            "usuarios:lista",
        ),
        (
            "Clases",
            "Crear y editar clases, desde la administración de Django.",
            "admin:usuarios_clase_changelist",
        ),
        (
            "Horario escolar",
            "Qué asignatura o taller tiene cada clase en cada franja.",
            "horario:cargar",
        ),
        ("Vínculos", "Tutor y familiar de cada estudiante.", "usuarios:vinculos"),
    ],
    Rol.TUTOR: [
        ("Crear una tarea", "Con su imagen y sus pasos.", "tareas:crear_tarea"),
        ("Tareas creadas", "Las tareas que ya existen.", "tareas:catalogo"),
        (
            "Perfil visual",
            "Tema, colores, letra, botones y lector de pantalla de tus estudiantes.",
            "perfil:lista",
        ),
    ],
    Rol.PROFESIONAL: [
        (
            "Mis estudiantes",
            "Elige a qué estudiantes atiendes y consulta su agenda.",
            "usuarios:mis_estudiantes",
        ),
        ("Crear una tarea", "Con su imagen y sus pasos.", "tareas:crear_tarea"),
        ("Tareas creadas", "Las tareas que ya existen.", "tareas:catalogo"),
    ],
    Rol.FAMILIAR: [
        ("Crear una tarea", "Con su imagen y sus pasos.", "tareas:crear_tarea"),
        ("Tareas creadas", "Las tareas que ya existen.", "tareas:catalogo"),
    ],
}


def opciones_de(rol):
    """Las opciones de un rol cuya URL existe: [{"texto", "descripcion", "url"}]."""
    opciones = []
    for texto, descripcion, nombre_url in OPCIONES_POR_ROL.get(rol, []):
        try:
            opciones.append(
                {"texto": texto, "descripcion": descripcion, "url": reverse(nombre_url)}
            )
        except NoReverseMatch:
            continue
    return opciones


def inicio_de(usuario):
    """La pantalla principal de cada uno: es a donde lleva el logotipo.

    El estudiante a su agenda, el adulto a su panel y quien no ha entrado a la portada.
    """
    if not getattr(usuario, "is_authenticated", False):
        return reverse("inicio")
    if usuario.es_estudiante:
        return reverse("agenda:dia")
    return reverse("usuarios:panel")


def navegacion_de(usuario, ruta):
    """El panel lateral de un adulto: «Inicio» y sus opciones, con la página actual marcada.

    `actual` es la opción de esta misma página (aria-current="page"). `seccion` es la
    opción dentro de la que está la página (por ejemplo «Usuarios» en /usuarios/nueva/):
    se marca también, pero sin decir que es la página actual.
    """
    inicio = reverse("usuarios:panel")
    enlaces = [{"texto": "Inicio", "url": inicio}, *opciones_de(usuario.rol)]
    # La sección es la opción con la dirección más larga que contiene a esta página.
    candidatas = [e for e in enlaces if e["url"] != inicio and ruta.startswith(e["url"])]
    seccion = max(candidatas, key=lambda e: len(e["url"]), default=None)
    for enlace in enlaces:
        enlace["actual"] = enlace["url"] == ruta
        enlace["seccion"] = enlace is seccion
    return enlaces
