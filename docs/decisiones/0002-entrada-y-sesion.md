# 0002 · Entrada, sesión y bloqueo

- **Estado:** aceptada (PR #12, HU-01-07). Ampliada con la entrada del estudiante (HU-01-06).
- **Fecha:** 2026-11-08 (HU-01-07, AGENDA-149; HU-01-06, AGENDA-144)
- **Responsable:** Manu Izquierdo

## Contexto

Todas las pantallas, salvo la portada y las de entrar, piden saber quién es el usuario y qué rol tiene. Los adultos entran con usuario y contraseña (HU-01-07) y los estudiantes con su avatar y 3 imágenes o una contraseña (HU-01-06). RNF1.2.3 pide bloquear tras 5 intentos fallidos durante 5 minutos, y en el colegio todas las tabletas y ordenadores salen a Internet por la misma IP.

## Decisión

- **Entrada de adultos con lo que trae Django:** `LoginView` y `AuthenticationForm` con los textos del boceto B12 (`apps/usuarios/views.py` y `forms.py`). El mensaje de error es el mismo si falla el usuario o la contraseña, y una cuenta desactivada no entra. Un estudiante no puede entrar por esta pantalla.
- **`LOGIN_URL = "inicio"`:** cualquier vista con `@login_required` manda a la portada «¿Quién eres?» (`/?next=…`) a quien no ha entrado. La portada pasa el `next` a la entrada del estudiante y a la del adulto. Al entrar, cada uno va a la pantalla que pedía o, si no pedía ninguna, a la suya: el adulto a `/panel/` y el estudiante a `agenda:dia`. `LOGIN_REDIRECT_URL` solo admite un destino, por eso lo decide la vista. Solo se vuelve a direcciones de esta misma web.
- **Salir solo con POST** (`/salir/`, `LogoutView`): un enlace o una imagen de otra web no pueden cerrar la sesión de nadie.
- **Bloqueo con django-axes por la pareja usuario + IP** (`AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]`): tras 5 fallos seguidos, ese usuario no puede entrar desde ese equipo durante 5 minutos, y acertar pone la cuenta a cero. Lo que ve el usuario está en `usuarios/bloqueado.html`.
- **Entrada del estudiante** (HU-01-06): portada → clase (B02) → avatar (B03) → 3 imágenes de la rejilla común o contraseña de texto, según `perfil.metodo_acceso`. Cada estudiante solo puede entrar de su forma: a quien usa imágenes no le vale una contraseña, y al revés. Se comprueba con `acceso.py` y `check_password`, sin `authenticate()`, y se inicia la sesión con `login()` indicando el backend de Django. Si falla, el mensaje no dice qué imagen o qué letra ha fallado. Solo aparecen y entran los estudiantes con la cuenta activa.
- **Al estudiante no se le bloquea** tras varios fallos: un niño que se equivoca no puede quedarse sin su agenda, y los estudiantes no tienen datos que proteger frente a sus compañeros más allá de su propia agenda. Es un riesgo aceptado: con 12 imágenes hay 220 combinaciones de 3, así que alguien con paciencia podría adivinar la de un compañero. Si el centro lo pide, se puede añadir más adelante una espera creciente tras varios fallos o un aviso al tutor.
- **Panel del adulto (B13) común a todos los roles:** las opciones de cada rol están en `OPCIONES_POR_ROL` (`apps/usuarios/views.py`). Cada responsable añade la de su pantalla; si la URL todavía no existe, la opción no se enseña.

## Alternativas descartadas

- **Bloquear por IP (lo que hace axes por defecto):** un adulto que se equivoca 5 veces dejaría sin entrar a todo el colegio.
- **Bloquear solo por usuario:** cualquiera que sepa el nombre de usuario de un tutor podría dejarlo fuera desde otro equipo con 5 intentos.
- **Una pantalla principal por app:** cada responsable tendría que repetir la cabecera, el saludo y el botón de salir.

## Consecuencias

- Las vistas de cada app usan `@login_required` y, además, comprueban el rol y el estudiante en el servidor (ver `docs/contribuir.md`).
- Detrás de Caddy (demo por HTTPS) axes debe leer la IP real del cliente y no la del proxy. Hay que revisarlo al montar la demo (`AXES_IPWARE_PROXY_COUNT`).
- En las pruebas axe está apagado (`config/settings/test.py`). Las pruebas del bloqueo lo encienden con el fixture `settings`.
- Un adulto que pedía una pantalla de estudiante (por ejemplo `/agenda/`) vuelve a ella al entrar y ve un 403: es correcto, esa pantalla no es para él.
