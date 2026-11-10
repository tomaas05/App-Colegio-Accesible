"""HU-01-01. Crear un usuario (AGENDA-117).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA5) y algunas más.
Solo el administrador crea cuentas. Datos de prueba: `admin` / «despega2026».
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.perfil.models import MetodoAcceso
from apps.usuarios.altas import siguiente_codigo
from apps.usuarios.models import Clase, Estudiante, ImagenAcceso, Rol, Usuario

pytestmark = pytest.mark.django_db

CONTRASENA = "despega2026"


@pytest.fixture
def admin(client, datos):
    client.force_login(Usuario.objects.get(username="admin"))
    return client


def ids(*palabras):
    return [ImagenAcceso.objects.get(descripcion_imagen=p).pk for p in palabras]


def ptval1():
    return Clase.objects.get(nombre="PTVAL 1")


def estudiante_nuevo(**cambios):
    datos = {
        "rol": Rol.ESTUDIANTE,
        "nombre": "Noa",
        "apellidos": "Ruiz Gil",
        "clase": ptval1().pk,
        "metodo_acceso": MetodoAcceso.IMAGENES,
        "imagenes": ("luna", "pez", "casa"),
    }
    datos.update(cambios)
    # Las imágenes se escriben con palabras y aquí se pasan a ids (ya hay base de datos).
    if isinstance(datos["imagenes"], tuple):
        datos["imagenes"] = ids(*datos["imagenes"])
    return datos


def adulto_nuevo(rol=Rol.TUTOR, **cambios):
    datos = {
        "rol": rol,
        "nombre": "Elena",
        "apellidos": "Martín",
        "usuario": "elena",
        "contrasena": "Colegio-2026",
    }
    datos.update(cambios)
    return datos


def csv(texto, nombre="lista.csv", codificacion="utf-8"):
    return SimpleUploadedFile(nombre, texto.encode(codificacion), content_type="text/csv")


# --- PA1: creo un estudiante con nombre, avatar y clase, sin foto, y aparece en su clase ---


def test_pa1_creo_un_estudiante_y_aparece_en_la_lista_de_su_clase(admin):
    codigo = siguiente_codigo()
    respuesta = admin.post(reverse("usuarios:crear"), estudiante_nuevo(usa_lector_pantalla="on"))
    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse("usuarios:lista") + f"?clase={ptval1().pk}"

    estudiante = Estudiante.objects.get(codigo_estudiante=codigo)
    assert estudiante.usuario.get_full_name() == "Noa Ruiz Gil"
    assert estudiante.usuario.rol == Rol.ESTUDIANTE
    assert estudiante.clase == ptval1()
    assert estudiante.avatar.name.endswith(".png")  # avatar dibujado con su inicial
    assert estudiante.perfil.metodo_acceso == MetodoAcceso.IMAGENES
    assert estudiante.perfil.usa_lector_pantalla is True

    # Aparece en la lista de su clase: la de Usuarios y la de los avatares para entrar.
    assert "Noa Ruiz Gil" in admin.get(respuesta["Location"]).content.decode()
    avatares = admin.get(reverse("usuarios:avatares", args=[ptval1().pk])).content.decode()
    assert '<span class="loseta__nombre">Noa</span>' in avatares


def test_pa1_el_estudiante_nuevo_entra_con_sus_imagenes(admin, client):
    admin.post(reverse("usuarios:crear"), estudiante_nuevo())
    codigo = Estudiante.objects.get(usuario__first_name="Noa").codigo_estudiante
    admin.post(reverse("usuarios:salir"))
    respuesta = client.post(
        reverse("usuarios:entrar_estudiante", args=[codigo]),
        {"imagenes": ids("casa", "luna", "pez")},
    )
    assert respuesta["Location"] == reverse("agenda:dia")


def test_pa1_el_estudiante_nuevo_puede_entrar_con_contrasena(admin, client):
    admin.post(
        reverse("usuarios:crear"),
        estudiante_nuevo(
            metodo_acceso=MetodoAcceso.CONTRASENA, imagenes=[], contrasena_estudiante="noa1"
        ),
    )
    estudiante = Estudiante.objects.get(usuario__first_name="Noa")
    assert estudiante.perfil.metodo_acceso == MetodoAcceso.CONTRASENA
    admin.post(reverse("usuarios:salir"))
    respuesta = client.post(
        reverse("usuarios:entrar_estudiante", args=[estudiante.codigo_estudiante]),
        {"password": "noa1"},
    )
    assert respuesta["Location"] == reverse("agenda:dia")


def test_pa1_se_puede_subir_un_avatar_dibujado(admin):
    from apps.usuarios.altas import avatar_por_defecto

    dibujo = avatar_por_defecto("Noa", "A99")
    archivo = SimpleUploadedFile("noa.png", dibujo.read(), content_type="image/png")
    admin.post(reverse("usuarios:crear"), estudiante_nuevo(avatar=archivo))
    estudiante = Estudiante.objects.get(usuario__first_name="Noa")
    assert estudiante.avatar.name.endswith("noa.png")


def test_pa1_el_codigo_se_asigna_solo_y_no_se_repite(admin):
    admin.post(reverse("usuarios:crear"), estudiante_nuevo(nombre="Uno"))
    admin.post(reverse("usuarios:crear"), estudiante_nuevo(nombre="Dos"))
    uno = Estudiante.objects.get(usuario__first_name="Uno").codigo_estudiante
    dos = Estudiante.objects.get(usuario__first_name="Dos").codigo_estudiante
    assert int(dos[1:]) == int(uno[1:]) + 1


def test_pa1_un_nombre_con_tilde_tiene_avatar_con_su_inicial(admin):
    """La fuente no tiene «Á»: se dibuja «A» en vez de un cuadro roto."""
    admin.post(reverse("usuarios:crear"), estudiante_nuevo(nombre="Álvaro"))
    assert Estudiante.objects.filter(usuario__first_name="Álvaro").exists()


# --- PA2: creo tutor, profesional y familiar con usuario y contraseña, y pueden entrar ---


@pytest.mark.parametrize("rol", [Rol.TUTOR, Rol.PROFESIONAL, Rol.FAMILIAR, Rol.ADMINISTRADOR])
def test_pa2_creo_un_adulto_y_entra_con_su_usuario(admin, client, rol):
    respuesta = admin.post(reverse("usuarios:crear"), adulto_nuevo(rol=rol))
    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse("usuarios:lista") + f"?rol={rol}"
    adulto = Usuario.objects.get(username="elena")
    assert adulto.rol == rol
    assert adulto.check_password("Colegio-2026")

    admin.post(reverse("usuarios:salir"))
    entrada = client.post(
        reverse("usuarios:entrar"), {"username": "elena", "password": "Colegio-2026"}
    )
    assert entrada["Location"] == reverse("usuarios:panel")
    assert "Hola, Elena" in client.get(reverse("usuarios:panel")).content.decode()


def test_pa2_el_administrador_nuevo_puede_abrir_clases(admin, client):
    """Su panel lleva a «Clases» en la administración de Django: tiene que poder entrar."""
    admin.post(reverse("usuarios:crear"), adulto_nuevo(rol=Rol.ADMINISTRADOR))
    nuevo = Usuario.objects.get(username="elena")
    assert nuevo.is_staff and nuevo.is_superuser
    client.force_login(nuevo)
    assert client.get(reverse("admin:usuarios_clase_changelist")).status_code == 200


def test_pa2_los_demas_adultos_no_entran_en_la_administracion(admin):
    admin.post(reverse("usuarios:crear"), adulto_nuevo(rol=Rol.TUTOR))
    nuevo = Usuario.objects.get(username="elena")
    assert not nuevo.is_staff and not nuevo.is_superuser


def test_pa2_tras_crear_sale_un_aviso_con_el_usuario(admin):
    respuesta = admin.post(reverse("usuarios:crear"), adulto_nuevo(), follow=True)
    contenido = respuesta.content.decode()
    assert "Cuenta creada: Elena Martín (Tutor)" in contenido
    assert "«elena»" in contenido
    assert 'role="status"' in contenido


# --- PA3: sin nombre o sin rol no se guarda y se indica qué falta ---


def test_pa3_los_campos_obligatorios_llevan_asterisco(admin):
    contenido = admin.get(reverse("usuarios:crear")).content.decode()
    assert "Los campos con * son obligatorios." in contenido
    assert '<label for="id_nombre">Nombre *</label>' in contenido
    assert '<label for="id_apellidos">Apellidos</label>' in contenido  # opcional


def test_pa3_sin_nombre_ni_rol_no_se_guarda(admin):
    antes = Usuario.objects.count()
    respuesta = admin.post(reverse("usuarios:crear"), {"rol": "", "nombre": ""})
    assert respuesta.status_code == 200
    assert Usuario.objects.count() == antes
    contenido = respuesta.content.decode()
    assert "Elige el rol." in contenido
    assert "Escribe el nombre." in contenido
    assert 'role="alert"' in contenido
    assert 'href="#id_rol"' in contenido  # el resumen lleva a cada campo


@pytest.mark.parametrize(
    "cambios, mensaje",
    [
        ({"clase": ""}, "Elige la clase."),
        ({"imagenes": ("luna", "pez")}, "Elige 3 imágenes."),
        (
            {"metodo_acceso": MetodoAcceso.CONTRASENA, "imagenes": []},
            "Escribe su contraseña.",
        ),
        (
            {
                "metodo_acceso": MetodoAcceso.CONTRASENA,
                "imagenes": [],
                "contrasena_estudiante": "ab",
            },
            "al menos 4 caracteres",
        ),
    ],
)
def test_pa3_a_un_estudiante_le_falta_algo(admin, cambios, mensaje):
    antes = Usuario.objects.count()
    respuesta = admin.post(reverse("usuarios:crear"), estudiante_nuevo(**cambios))
    assert respuesta.status_code == 200
    assert Usuario.objects.count() == antes
    assert mensaje in respuesta.content.decode()


def test_pa3_el_resumen_lleva_tambien_a_la_rejilla_de_imagenes(admin):
    """Las casillas no tienen id_for_label: el enlace va a la lista, no a «#»."""
    respuesta = admin.post(reverse("usuarios:crear"), estudiante_nuevo(imagenes=("luna",)))
    contenido = respuesta.content.decode()
    assert '<a href="#id_imagenes">Sus 3 imágenes</a>' in contenido
    assert 'aria-describedby="id_imagenes_error"' in contenido
    assert 'href="#"' not in contenido


@pytest.mark.parametrize(
    "cambios, mensaje",
    [
        ({"usuario": ""}, "Escribe el usuario."),
        ({"contrasena": ""}, "Escribe la contraseña inicial."),
        ({"usuario": "tutor"}, "Ese usuario ya existe."),
        ({"usuario": "TUTOR"}, "Ese usuario ya existe."),
        ({"contrasena": "1234"}, "contraseña"),  # validadores de Django: corta y numérica
        ({"usuario": "con espacios"}, "usuario"),
        ({"usuario": "est-a99"}, "son de los estudiantes"),  # reservado a los estudiantes
        ({"contrasena": "elena2026"}, "demasiado similar"),  # se parece al usuario «elena»
    ],
)
def test_pa3_a_un_adulto_le_falta_algo(admin, cambios, mensaje):
    antes = Usuario.objects.count()
    respuesta = admin.post(reverse("usuarios:crear"), adulto_nuevo(**cambios))
    assert respuesta.status_code == 200
    assert Usuario.objects.count() == antes
    assert mensaje in respuesta.content.decode()


def test_pa3_un_avatar_que_no_es_imagen_no_se_acepta(admin):
    falso = SimpleUploadedFile("avatar.png", b"no soy una imagen", content_type="image/png")
    antes = Usuario.objects.count()
    respuesta = admin.post(reverse("usuarios:crear"), estudiante_nuevo(avatar=falso))
    assert respuesta.status_code == 200
    assert Usuario.objects.count() == antes


# --- PA4: cargo una lista de 25 estudiantes; una fila incorrecta no se crea y se dice cuál ---


def test_pa4_cargo_25_estudiantes_y_la_fila_mala_se_indica(admin):
    filas = ["nombre;apellidos;imagenes;contrasena"]
    filas += [f"Alumno{n};Prueba;perro sol flor;" for n in range(1, 26)]
    filas.insert(13, "Malo;Prueba;perro sol dragón;")  # fila 14 del archivo
    antes = Estudiante.objects.count()

    respuesta = admin.post(
        reverse("usuarios:cargar"), {"clase": ptval1().pk, "archivo": csv("\n".join(filas))}
    )
    assert respuesta.status_code == 200
    assert Estudiante.objects.count() == antes + 25
    assert not Usuario.objects.filter(first_name="Malo").exists()
    contenido = respuesta.content.decode()
    assert "Se han creado 25 cuentas en PTVAL 1." in contenido
    assert '<th scope="row">14</th>' in contenido
    assert "No hay ninguna imagen «dragón» en la rejilla." in contenido
    assert Estudiante.objects.filter(clase=ptval1(), usuario__first_name="Alumno25").exists()


def test_pa4_los_estudiantes_cargados_pueden_entrar(admin, client):
    texto = "nombre;apellidos;imagenes;contrasena\nIris;Sol;gato luna pez;\nOmar;Paz;;omar2026\n"
    admin.post(reverse("usuarios:cargar"), {"clase": ptval1().pk, "archivo": csv(texto)})
    iris = Estudiante.objects.get(usuario__first_name="Iris")
    omar = Estudiante.objects.get(usuario__first_name="Omar")
    assert omar.perfil.metodo_acceso == MetodoAcceso.CONTRASENA
    url = reverse("usuarios:entrar_estudiante", args=[iris.codigo_estudiante])
    assert client.post(url, {"imagenes": ids("pez", "gato", "luna")}).status_code == 302
    client.post(reverse("usuarios:salir"))
    url = reverse("usuarios:entrar_estudiante", args=[omar.codigo_estudiante])
    assert client.post(url, {"password": "omar2026"}).status_code == 302


@pytest.mark.parametrize(
    "texto, codificacion",
    [
        ("nombre,apellidos,imagenes,contrasena\nÍñigo,Peña,perro sol flor,\n", "utf-8"),
        ("﻿Nombre;Apellidos;Imágenes;Contraseña\nÍñigo;Peña;Perro Sol Flor;\n", "utf-8"),
        ("nombre;apellidos;imagenes;contrasena\r\nÍñigo;Peña;perro sol flor;\r\n", "cp1252"),
    ],
    ids=["comas", "excel-con-bom-y-tildes", "excel-windows-cp1252"],
)
def test_pa4_acepta_los_csv_de_excel(admin, texto, codificacion):
    admin.post(
        reverse("usuarios:cargar"),
        {"clase": ptval1().pk, "archivo": csv(texto, codificacion=codificacion)},
    )
    assert Usuario.objects.filter(first_name="Íñigo", last_name="Peña").exists()


@pytest.mark.parametrize(
    "fila, motivo",
    [
        (";Sin Nombre;perro sol flor;", "Escribe el nombre."),
        ("Ana;López;perro sol;", "Elige 3 imágenes."),
        ("Ana;López;perro sol flor;ana2026", "no las dos"),
        ("Ana;López;;", "Pon sus 3 imágenes o su contraseña."),
    ],
)
def test_pa4_cada_fila_mala_dice_por_que(admin, fila, motivo):
    texto = f"nombre;apellidos;imagenes;contrasena\n{fila}\n"
    respuesta = admin.post(
        reverse("usuarios:cargar"), {"clase": ptval1().pk, "archivo": csv(texto)}
    )
    contenido = respuesta.content.decode()
    assert "Se han creado 0 cuentas" in contenido
    assert motivo in contenido


def test_pa4_un_archivo_con_caracteres_raros_no_rompe_la_pagina(admin):
    """Bytes que no son ni UTF-8 ni cp1252: se lee igual y se crea la fila, sin error 500."""
    datos = b"nombre;apellidos;imagenes;contrasena\nRa\x81l;P\x8dna;perro sol flor;\n"
    archivo = SimpleUploadedFile("lista.csv", datos, content_type="text/csv")
    respuesta = admin.post(reverse("usuarios:cargar"), {"clase": ptval1().pk, "archivo": archivo})
    assert respuesta.status_code == 200
    assert "Se ha creado 1 cuenta en" in respuesta.content.decode()


def test_pa4_un_archivo_sin_cabecera_se_rechaza_entero(admin):
    antes = Usuario.objects.count()
    respuesta = admin.post(
        reverse("usuarios:cargar"),
        {"clase": ptval1().pk, "archivo": csv("Ana;López;perro sol flor;\n")},
    )
    assert Usuario.objects.count() == antes
    assert "La primera fila tiene que tener los nombres de las columnas" in (
        respuesta.content.decode()
    )


def test_pa4_las_filas_vacias_del_final_se_ignoran(admin):
    texto = "nombre;apellidos;imagenes;contrasena\nAna;López;perro sol flor;\n;;;\n\n"
    respuesta = admin.post(
        reverse("usuarios:cargar"), {"clase": ptval1().pk, "archivo": csv(texto)}
    )
    assert "Se ha creado 1 cuenta en PTVAL 1." in respuesta.content.decode()


def test_pa4_la_plantilla_se_descarga(admin):
    respuesta = admin.get(reverse("usuarios:plantilla"))
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].startswith("text/csv")
    assert "attachment" in respuesta["Content-Disposition"]
    assert respuesta.content.decode("utf-8-sig").startswith("nombre;apellidos;imagenes;contrasena")


def test_pa4_sin_archivo_ni_clase_indica_que_falta(admin):
    respuesta = admin.post(reverse("usuarios:cargar"), {})
    contenido = respuesta.content.decode()
    assert "Elige la clase." in contenido
    assert "Elige el archivo." in contenido


# --- PA5: quien no es administrador no ve la opción y el servidor rechaza la petición ---


@pytest.mark.parametrize("nombre_url", ["lista", "crear", "cargar", "plantilla"])
@pytest.mark.parametrize("usuario", ["tutor", "profesional", "familiar", "est-a01"])
def test_pa5_otros_roles_reciben_403(client, datos, nombre_url, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    assert client.get(reverse(f"usuarios:{nombre_url}")).status_code == 403


def test_pa5_un_tutor_no_puede_crear_cuentas_aunque_mande_el_formulario(client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    antes = Usuario.objects.count()
    assert client.post(reverse("usuarios:crear"), adulto_nuevo()).status_code == 403
    assert Usuario.objects.count() == antes


def test_pa5_sin_sesion_va_a_la_portada(client, datos):
    respuesta = client.get(reverse("usuarios:crear"))
    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(reverse("inicio") + "?next=")


def test_pa5_solo_el_panel_del_administrador_tiene_la_opcion(client, datos):
    client.force_login(Usuario.objects.get(username="admin"))
    assert reverse("usuarios:lista") in client.get(reverse("usuarios:panel")).content.decode()
    for usuario in ["tutor", "profesional", "familiar"]:
        client.force_login(Usuario.objects.get(username=usuario))
        assert (
            reverse("usuarios:lista") not in client.get(reverse("usuarios:panel")).content.decode()
        )


# --- B20 · Lista de usuarios ---


def test_la_lista_filtra_por_rol_clase_y_texto(admin):
    por_rol = admin.get(reverse("usuarios:lista"), {"rol": Rol.TUTOR}).content.decode()
    assert "Ana" in por_rol and "Lucía" not in por_rol

    por_clase = admin.get(reverse("usuarios:lista"), {"clase": ptval1().pk}).content.decode()
    assert "Lucía" in por_clase and "Daniela" not in por_clase

    por_codigo = admin.get(reverse("usuarios:lista"), {"q": "A02"}).content.decode()
    assert "Mateo" in por_codigo and "Lucía" not in por_codigo


@pytest.mark.parametrize("texto", ["lucia", "LUCÍA", "lucia fernandez", "fernández"])
def test_la_lista_busca_sin_mirar_tildes_ni_mayusculas(admin, texto):
    contenido = admin.get(reverse("usuarios:lista"), {"q": texto}).content.decode()
    assert "Lucía Fernández" in contenido
    assert "Mateo" not in contenido


def test_la_lista_ensena_tutor_y_familiar_de_cada_estudiante(admin):
    contenido = admin.get(reverse("usuarios:lista"), {"q": "A01"}).content.decode()
    assert "Ana" in contenido  # tutora de Lucía
    assert "Carmen" in contenido  # familiar de Lucía
