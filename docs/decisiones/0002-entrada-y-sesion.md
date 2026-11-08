# 0002 · Entrada, sesión y bloqueo de adultos

- **Estado:** propuesta (se acepta al fusionar el PR de HU-01-07)
- **Fecha:** 2026-11-08 (HU-01-07, AGENDA-149)
- **Responsable:** Manu Izquierdo

## Contexto

Todas las pantallas, salvo la portada y las de entrar, piden saber quién es el usuario y qué rol tiene. Los adultos entran con usuario y contraseña (HU-01-07) y los estudiantes con su avatar y 3 imágenes o una contraseña (HU-01-06). RNF1.2.3 pide bloquear tras 5 intentos fallidos durante 5 minutos, y en el colegio todas las tabletas y ordenadores salen a Internet por la misma IP.

## Decisión

- **Entrada de adultos con lo que trae Django:** `LoginView` y `AuthenticationForm` con los textos del boceto B12 (`apps/usuarios/views.py` y `forms.py`). El mensaje de error es el mismo si falla el usuario o la contraseña, y una cuenta desactivada no entra. Un estudiante no puede entrar por esta pantalla.
- **`LOGIN_URL = "usuarios:entrar"`:** cualquier vista con `@login_required` manda a `/entrar/?next=…` a quien no ha entrado. Al entrar, cada rol va a su pantalla (`destino_tras_entrar`): el adulto a `/panel/` y el estudiante a `agenda:dia`. `LOGIN_REDIRECT_URL` solo admite un destino, por eso lo decide la vista.
- **Salir solo con POST** (`/salir/`, `LogoutView`): un enlace o una imagen de otra web no pueden cerrar la sesión de nadie.
- **Bloqueo con django-axes por la pareja usuario + IP** (`AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]`): tras 5 fallos seguidos, ese usuario no puede entrar desde ese equipo durante 5 minutos, y acertar pone la cuenta a cero. Lo que ve el usuario está en `usuarios/bloqueado.html`.
- **Panel del adulto (B13) común a todos los roles:** las opciones de cada rol están en `OPCIONES_POR_ROL` (`apps/usuarios/views.py`). Cada responsable añade la de su pantalla; si la URL todavía no existe, la opción no se enseña.

## Alternativas descartadas

- **Bloquear por IP (lo que hace axes por defecto):** un adulto que se equivoca 5 veces dejaría sin entrar a todo el colegio.
- **Bloquear solo por usuario:** cualquiera que sepa el nombre de usuario de un tutor podría dejarlo fuera desde otro equipo con 5 intentos.
- **Una pantalla principal por app:** cada responsable tendría que repetir la cabecera, el saludo y el botón de salir.

## Consecuencias

- Las vistas de cada app usan `@login_required` y, además, comprueban el rol y el estudiante en el servidor (ver `docs/contribuir.md`).
- Detrás de Caddy (demo por HTTPS) axes debe leer la IP real del cliente y no la del proxy. Hay que revisarlo al montar la demo (`AXES_IPWARE_PROXY_COUNT`).
- En las pruebas axe está apagado (`config/settings/test.py`). Las pruebas del bloqueo lo encienden con el fixture `settings`.
- La entrada del estudiante (HU-01-06) cambiará `LOGIN_URL` a la portada «¿Quién eres?», desde donde se elige Estudiante o Adulto.
