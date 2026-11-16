"""HU-01-02. Modificar un usuario (AGENDA-123).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA5) y las de lo que se añadió a
la historia: activar o desactivar la cuenta y restablecer la contraseña con una temporal.
Solo el administrador edita cuentas. Datos de prueba: `admin` / «despega2026».
"""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.usuarios import edicion
from apps.usuarios.models import Clase, Estudiante, Usuario

pytestmark = pytest.mark.django_db

CONTRASENA = "despega2026"
PANEL = reverse("usuarios:panel")
CAMBIAR = reverse("usuarios:cambiar_contrasena")


@pytest.fixture
def admin(client, datos):
    client.force_login(Usuario.objects.get(username="admin"))
    return client


def url_editar(cuenta):
    return reverse("usuarios:editar", args=[cuenta.pk])


def lucia():
    return Estudiante.objects.select_related("usuario", "clase").get(codigo_estudiante="A01")


def tutor():
    return Usuario.objects.get(username="tutor")


def datos_estudiante(estudiante, **cambios):
    datos = {
        "nombre": estudiante.usuario.first_name,
        "apellidos": estudiante.usuario.last_name,
        "clase": estudiante.clase_id,
        "estado": "activa",
    }
    datos.update(cambios)
    return datos


def datos_adulto(cuenta, **cambios):
    datos = {
        "nombre": cuenta.first_name,
        "apellidos": cuenta.last_name,
        "usuario": cuenta.username,
        "correo": cuenta.email,
        "estado": "activa",
    }
    datos.update(cambios)
    return datos


def imagen_png(nombre="nuevo.png"):
    salida = io.BytesIO()
    Image.new("RGB", (8, 8), "#1F6F6B").save(salida, format="PNG")
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type="image/png")


def entrar(client, usuario, contrasena):
    return client.post(reverse("usuarios:entrar"), {"username": usuario, "password": contrasena})


# --- PA1: cambio el nombre de una cuenta y el cambio aparece en las listas ---


def test_pa1_el_nombre_nuevo_aparece_en_las_listas(admin):
    estudiante = lucia()
    respuesta = admin.post(
        url_editar(estudiante.usuario),
        datos_estudiante(estudiante, nombre="Lucía María", apellidos="Fernández Ruiz"),
    )
    assert respuesta.status_code == 302 and respuesta["Location"] == reverse("usuarios:lista")

    lista = admin.get(reverse("usuarios:lista"), {"q": "A01"}).content.decode()
    assert "Lucía María Fernández Ruiz" in lista
    assert "Cambios guardados en la cuenta de Lucía María Fernández Ruiz: el nombre." in lista
    # También donde el estudiante elige su avatar para entrar.
    avatares = admin.get(reverse("usuarios:avatares", args=[estudiante.clase_id])).content.decode()
    assert "Lucía María" in avatares


def test_pa1_tambien_el_de_un_adulto_y_su_usuario(admin):
    cuenta = tutor()
    admin.post(url_editar(cuenta), datos_adulto(cuenta, nombre="Ana María", usuario="anamaria"))
    cuenta.refresh_from_db()
    assert (cuenta.first_name, cuenta.username) == ("Ana María", "anamaria")
    assert "Ana María" in admin.get(reverse("usuarios:lista"), {"rol": "tutor"}).content.decode()


def test_la_lista_tiene_un_enlace_para_editar_cada_cuenta(admin):
    html = admin.get(reverse("usuarios:lista")).content.decode()
    for cuenta in Usuario.objects.all():
        assert f'href="{url_editar(cuenta)}"' in html
    assert 'Editar<span class="visualmente-oculto"> la cuenta de ' in html


def test_el_formulario_llega_con_los_datos_de_la_cuenta(admin):
    estudiante = lucia()
    html = admin.get(url_editar(estudiante.usuario)).content.decode()
    assert f'value="{estudiante.usuario.first_name}"' in html
    assert "Código A01" in html and estudiante.avatar.url in html
    # A un estudiante no se le pide usuario ni se le restablece la contraseña.
    assert 'name="usuario"' not in html and "Restablecer contraseña" not in html

    html = admin.get(url_editar(tutor())).content.decode()
    assert 'name="usuario"' in html and 'value="tutor"' in html
    assert 'name="clase"' not in html and "Restablecer contraseña" in html


# --- PA2: cambio el avatar de un estudiante y se muestra el nuevo ---


def test_pa2_el_avatar_nuevo_se_muestra(admin):
    estudiante = lucia()
    anterior = estudiante.avatar.name
    respuesta = admin.post(
        url_editar(estudiante.usuario), datos_estudiante(estudiante, avatar=imagen_png())
    )
    assert respuesta.status_code == 302
    estudiante.refresh_from_db()
    assert estudiante.avatar.name != anterior and "a01-nuevo" in estudiante.avatar.name
    avatares = admin.get(reverse("usuarios:avatares", args=[estudiante.clase_id])).content.decode()
    assert estudiante.avatar.url in avatares


def test_pa2_sin_elegir_avatar_se_queda_el_que_tenia(admin):
    estudiante = lucia()
    anterior = estudiante.avatar.name
    admin.post(url_editar(estudiante.usuario), datos_estudiante(estudiante, nombre="Luci"))
    estudiante.refresh_from_db()
    assert estudiante.avatar.name == anterior


def test_pa2_un_archivo_que_no_es_una_imagen_no_se_guarda(admin):
    estudiante = lucia()
    falso = SimpleUploadedFile("nota.png", b"esto no es una imagen", content_type="image/png")
    respuesta = admin.post(
        url_editar(estudiante.usuario), datos_estudiante(estudiante, avatar=falso)
    )
    assert respuesta.status_code == 200 and "avatar" in respuesta.context["form"].errors


# --- PA3: cambio la clase de un estudiante y aparece en la lista de la clase nueva ---


def test_pa3_el_estudiante_aparece_en_la_clase_nueva(admin):
    estudiante = lucia()
    vieja = estudiante.clase
    nueva = Clase.objects.get(nombre="PTVAL 2")
    admin.post(url_editar(estudiante.usuario), datos_estudiante(estudiante, clase=nueva.pk))

    estudiante.refresh_from_db()
    assert estudiante.clase == nueva
    nombre = estudiante.usuario.first_name
    assert nombre in admin.get(reverse("usuarios:avatares", args=[nueva.pk])).content.decode()
    assert nombre not in admin.get(reverse("usuarios:avatares", args=[vieja.pk])).content.decode()
    # En Usuarios, al filtrar por la clase nueva.
    lista = admin.get(reverse("usuarios:lista"), {"clase": nueva.pk}).content.decode()
    assert estudiante.usuario.get_full_name() in lista
    # Cambiar de clase no cambia el tutor: se avisa de que sigue con el mismo.
    assert "sigue con su tutor, Ana Martín Ruiz" in lista


# --- PA4: un nombre vacío no se guarda ---


@pytest.mark.parametrize("vacio", ["", "   "])
def test_pa4_un_nombre_vacio_no_se_guarda(admin, vacio):
    estudiante = lucia()
    antes = estudiante.usuario.first_name
    respuesta = admin.post(
        url_editar(estudiante.usuario),
        datos_estudiante(estudiante, nombre=vacio, apellidos="Otro"),
    )
    assert respuesta.status_code == 200
    assert respuesta.context["form"].errors["nombre"] == ["Escribe el nombre."]
    estudiante.usuario.refresh_from_db()
    # No se guarda nada: tampoco los apellidos, que sí eran válidos.
    assert (estudiante.usuario.first_name, estudiante.usuario.last_name) != (vacio, "Otro")
    assert estudiante.usuario.first_name == antes
    html = respuesta.content.decode()
    assert 'role="alert"' in html and 'aria-invalid="true"' in html


def test_un_usuario_repetido_o_de_estudiante_no_se_guarda(admin):
    cuenta = tutor()
    for usuario in ("profesional", "PROFESIONAL", "est-a01"):
        respuesta = admin.post(url_editar(cuenta), datos_adulto(cuenta, usuario=usuario))
        assert respuesta.status_code == 200 and "usuario" in respuesta.context["form"].errors
    cuenta.refresh_from_db()
    assert cuenta.username == "tutor"
    # Dejar el suyo no cuenta como repetido.
    assert admin.post(url_editar(cuenta), datos_adulto(cuenta)).status_code == 302


# --- PA5: un usuario que no es administrador no puede modificar cuentas ---


@pytest.mark.parametrize("quien", ["tutor", "profesional", "familiar"])
def test_pa5_quien_no_es_administrador_no_puede(client, datos, quien):
    estudiante = lucia()
    client.force_login(Usuario.objects.get(username=quien))
    assert client.get(url_editar(estudiante.usuario)).status_code == 403
    respuesta = client.post(
        url_editar(estudiante.usuario), datos_estudiante(estudiante, nombre="Otra")
    )
    assert respuesta.status_code == 403
    assert client.post(url_editar(tutor()), {"accion": "restablecer"}).status_code == 403
    estudiante.usuario.refresh_from_db()
    assert estudiante.usuario.first_name == "Lucía"


def test_pa5_un_estudiante_y_quien_no_ha_entrado_tampoco(client, datos):
    estudiante = lucia()
    url = url_editar(estudiante.usuario)
    assert client.get(url).status_code == 302  # sin sesión, a la portada
    client.force_login(estudiante.usuario)
    assert client.post(url, datos_estudiante(estudiante, nombre="Otra")).status_code == 403


def test_una_cuenta_que_no_existe_da_404(admin):
    assert admin.get(reverse("usuarios:editar", args=[999999])).status_code == 404


# --- Activar y desactivar una cuenta ---


def test_una_cuenta_desactivada_no_puede_entrar_y_conserva_sus_vinculos(admin, client):
    cuenta = tutor()
    tutorizados = cuenta.estudiantes_tutorizados.count()
    admin.post(url_editar(cuenta), datos_adulto(cuenta, estado="desactivada"))
    cuenta.refresh_from_db()
    assert not cuenta.is_active and cuenta.estudiantes_tutorizados.count() == tutorizados
    lista = admin.get(reverse("usuarios:lista"), {"rol": "tutor"}).content.decode()
    assert "<strong>Desactivada</strong>" in lista and "Ya no puede entrar" in lista

    client.logout()
    respuesta = entrar(client, "tutor", CONTRASENA)
    # El mismo mensaje que con datos equivocados: no se dice que la cuenta existe.
    assert respuesta.status_code == 200 and "no coinciden" in respuesta.content.decode()


def test_al_desactivarla_se_cierra_la_sesion_que_tuviera_abierta(admin, django_user_model):
    from django.test import Client

    cuenta = tutor()
    otro = Client()
    otro.force_login(cuenta)
    assert otro.get(PANEL).status_code == 200
    admin.post(url_editar(cuenta), datos_adulto(cuenta, estado="desactivada"))
    assert otro.get(PANEL).status_code == 302  # ya no tiene sesión: a la portada


def test_una_cuenta_reactivada_vuelve_a_entrar(admin, client):
    cuenta = tutor()
    Usuario.objects.filter(pk=cuenta.pk).update(is_active=False)
    cuenta.refresh_from_db()
    admin.post(url_editar(cuenta), datos_adulto(cuenta, estado="activa"))
    client.logout()
    assert entrar(client, "tutor", CONTRASENA).status_code == 302


def test_un_estudiante_desactivado_no_sale_para_entrar(admin):
    estudiante = lucia()
    admin.post(url_editar(estudiante.usuario), datos_estudiante(estudiante, estado="desactivada"))
    html = admin.get(reverse("usuarios:avatares", args=[estudiante.clase_id])).content.decode()
    assert "Lucía" not in html


def test_nadie_desactiva_su_propia_cuenta(admin):
    yo = Usuario.objects.get(username="admin")
    respuesta = admin.post(url_editar(yo), datos_adulto(yo, estado="desactivada"))
    assert respuesta.status_code == 200 and "estado" in respuesta.context["form"].errors
    yo.refresh_from_db()
    assert yo.is_active


# --- Restablecer la contraseña de un adulto ---


def restablecer(admin, cuenta):
    respuesta = admin.post(url_editar(cuenta), {"accion": "restablecer"})
    assert respuesta.status_code == 302 and respuesta["Location"] == url_editar(cuenta)
    return admin.get(url_editar(cuenta))


def test_restablecer_da_una_temporal_que_se_ve_una_sola_vez(admin):
    cuenta = tutor()
    respuesta = restablecer(admin, cuenta)
    temporal = respuesta.context["temporal"]
    assert temporal and f'value="{temporal}"' in respuesta.content.decode()

    cuenta.refresh_from_db()
    assert cuenta.debe_cambiar_contrasena
    assert cuenta.check_password(temporal) and not cuenta.check_password(CONTRASENA)
    # Al volver a abrir la pantalla ya no está, ni queda guardada en la sesión.
    otra_vez = admin.get(url_editar(cuenta))
    assert otra_vez.context["temporal"] == "" and temporal not in otra_vez.content.decode()
    assert "todavía no la ha cambiado" in otra_vez.content.decode()
    # No ha viajado al navegador en ninguna cookie.
    assert all(temporal not in cookie.value for cookie in admin.cookies.values())


def test_la_temporal_es_facil_de_dictar_y_distinta_cada_vez():
    temporales = {edicion.contrasena_temporal() for _ in range(20)}
    assert len(temporales) == 20
    for temporal in temporales:
        grupos = temporal.split("-")
        assert [len(g) for g in grupos] == [4, 4, 4]
        assert not set(temporal) & set("lio01")


def test_restablecer_no_guarda_lo_que_hubiera_escrito_en_el_formulario(admin):
    """El botón es de otro formulario: restablecer no toca el nombre ni el estado."""
    cuenta = tutor()
    admin.post(url_editar(cuenta), {"accion": "restablecer", "nombre": "Otro", "estado": "x"})
    cuenta.refresh_from_db()
    assert cuenta.first_name == "Ana" and cuenta.is_active


def test_pulsar_intro_en_un_campo_no_restablece(admin):
    """El botón de restablecer señala a otro formulario, que no tiene campos de texto."""
    html = admin.get(url_editar(tutor())).content.decode()
    # El formulario de la cuenta (el de «Salir» del panel lateral va antes y no cuenta).
    principal, resto = html.split('enctype="multipart/form-data"', 1)[1].split("</form>", 1)
    assert 'form="form-restablecer"' in principal and 'name="accion"' not in principal
    assert 'id="form-restablecer"' in resto and 'name="accion" value="restablecer"' in resto


def test_no_se_restablece_la_de_un_estudiante_ni_la_propia(admin):
    yo = Usuario.objects.get(username="admin")
    for cuenta in (lucia().usuario, yo):
        assert admin.post(url_editar(cuenta), {"accion": "restablecer"}).status_code == 403
        cuenta.refresh_from_db()
        assert not cuenta.debe_cambiar_contrasena
    assert "Restablecer contraseña" not in admin.get(url_editar(yo)).content.decode()


# --- Con la contraseña temporal solo se puede cambiarla o salir (B15) ---


@pytest.fixture
def con_temporal(admin, client):
    """El tutor, que acaba de entrar con la contraseña temporal que le ha dado el administrador."""
    temporal = restablecer(admin, tutor()).context["temporal"]
    client.logout()
    respuesta = entrar(client, "tutor", temporal)
    assert respuesta.status_code == 302
    return client, temporal


def test_con_la_temporal_cualquier_pantalla_lleva_a_cambiarla(con_temporal):
    client, _ = con_temporal
    for url in (PANEL, reverse("tareas:catalogo"), reverse("perfil:lista"), "/admin/"):
        respuesta = client.get(url)
        assert respuesta.status_code == 302 and respuesta["Location"] == CAMBIAR
    html = client.get(CAMBIAR).content.decode()
    assert "Cambia tu contraseña" in html and "contraseña temporal" in html
    # Sin panel lateral: hasta cambiarla no hay a dónde ir.
    assert 'id="lateral"' not in html


def test_con_la_temporal_se_puede_salir(con_temporal):
    client, _ = con_temporal
    assert client.post(reverse("usuarios:salir")).status_code == 302
    assert client.get(PANEL).status_code == 302  # sin sesión
    assert tutor().debe_cambiar_contrasena  # sigue pendiente para la próxima vez


def test_la_contrasena_nueva_tiene_que_valer(con_temporal):
    client, temporal = con_temporal
    casos = {
        ("", ""): "new_password1",
        ("Colegio-2026", "Colegio-2027"): "new_password2",
        ("12345678", "12345678"): "new_password2",
        (temporal, temporal): "new_password1",
    }
    for (una, otra), campo in casos.items():
        respuesta = client.post(CAMBIAR, {"new_password1": una, "new_password2": otra})
        assert respuesta.status_code == 200, (una, otra)
        assert campo in respuesta.context["form"].errors, (una, otra)
    assert tutor().debe_cambiar_contrasena


def test_al_cambiarla_sigue_dentro_y_entra_con_la_nueva(con_temporal):
    client, temporal = con_temporal
    respuesta = client.post(
        CAMBIAR, {"new_password1": "Colegio-2026", "new_password2": "Colegio-2026"}
    )
    assert respuesta.status_code == 302 and respuesta["Location"] == PANEL
    cuenta = tutor()
    assert not cuenta.debe_cambiar_contrasena and cuenta.check_password("Colegio-2026")
    # No ha tenido que volver a entrar, y la pantalla de cambiar ya no es para él.
    assert client.get(PANEL).status_code == 200
    assert client.get(CAMBIAR).status_code == 302

    client.logout()
    assert entrar(client, "tutor", temporal).status_code == 200  # la temporal ya no sirve
    assert entrar(client, "tutor", "Colegio-2026").status_code == 302


def test_quien_no_tiene_temporal_no_ve_la_pantalla_de_cambiar(client, datos):
    client.force_login(tutor())
    respuesta = client.get(CAMBIAR)
    assert respuesta.status_code == 302 and respuesta["Location"] == PANEL
