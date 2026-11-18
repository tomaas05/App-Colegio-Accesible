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
        (
            "Comedor y menú",
            "Quién se encarga del comedor cada día y del reparto del menú cada mes.",
            "centro:comedor",
        ),
    ],
    Rol.TUTOR: [
        (
            "Seguimiento de hoy",
            "Cómo van hoy tus estudiantes y quién no ha podido hacer una tarea.",
            "seguimiento:hoy",
        ),
        ("Crear una tarea", "Con su imagen y sus pasos.", "tareas:crear_tarea"),
        ("Tareas creadas", "Las tareas que ya existen.", "tareas:catalogo"),
        (
            "Tareas planificadas",
            "Modificar o cancelar una tarea, en un día o en toda la serie.",
            "tareas:tareas_planificadas",
        ),
        (
            "Alumnos",
            "Cómo ve la agenda cada uno: colores, letra, botones y temporizador.",
            "perfil:lista",
        ),
    ],
    Rol.PROFESIONAL: [
        (
            "Mis estudiantes",
            "Elige a qué estudiantes atiendes y consulta su agenda.",
            "usuarios:mis_estudiantes",
        ),
        (
            "Seguimiento de hoy",
            "Cómo van hoy los estudiantes que atiendes.",
            "seguimiento:hoy",
        ),
        ("Crear una tarea", "Con su imagen y sus pasos.", "tareas:crear_tarea"),
        ("Tareas creadas", "Las tareas que ya existen.", "tareas:catalogo"),
    ],
    Rol.FAMILIAR: [
        ("Crear una tarea", "Con su imagen y sus pasos.", "tareas:crear_tarea"),
        ("Tareas creadas", "Las tareas que ya existen.", "tareas:catalogo"),
    ],
}


# Icono de cada opción en las tarjetas de /panel/, como en el boceto B13. Los dibujos están
# en templates/_icono.html. Una opción sin icono aquí sale con la flecha.
ICONOS = {
    "usuarios:lista": "personas",
    "admin:usuarios_clase_changelist": "escuela",
    "horario:cargar": "reloj",
    "usuarios:vinculos": "enlace",
    "centro:comedor": "calendario",
    "tareas:crear_tarea": "mas",
    "tareas:catalogo": "archivo",
    "perfil:lista": "personas",
    "usuarios:mis_estudiantes": "personas",
}

# Opciones que ya enseñan «mis estudiantes»: quien tiene una no los ve además en el panel.
OPCIONES_CON_ESTUDIANTES = {"perfil:lista", "usuarios:mis_estudiantes"}


def opciones_de(rol):
    """Las opciones de un rol cuya URL existe: [{"texto", "descripcion", "url", "icono"}]."""
    opciones = []
    for texto, descripcion, nombre_url in OPCIONES_POR_ROL.get(rol, []):
        try:
            opciones.append(
                {
                    "texto": texto,
                    "descripcion": descripcion,
                    "url": reverse(nombre_url),
                    "icono": ICONOS.get(nombre_url, "der"),
                }
            )
        except NoReverseMatch:
            continue
    return opciones


def lista_estudiantes_en_el_panel(rol):
    """Si «Tus estudiantes» sale en /panel/: solo para quien no tiene una opción que los liste.

    Revisión con la profesora: el tutor no ve a sus alumnos directamente en el panel, entra
    por «Alumnos». El profesional tiene «Mis estudiantes». El familiar no tiene ninguna
    opción así, de modo que los sigue viendo en su panel (HU-01-04, PA3).
    """
    if rol == Rol.ADMINISTRADOR:
        return False
    return not any(url in OPCIONES_CON_ESTUDIANTES for _, _, url in OPCIONES_POR_ROL.get(rol, []))


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
