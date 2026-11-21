# Retrospectiva de la profesora (19/11) y auditoría de la rama

Rama `diseno/encuadre-responsive`. Primero se auditó lo que ya había en la rama (los fallos de
diseño del acta del 19/11) y después se aplicó la retrospectiva de la profesora.

## 1. Auditoría de la rama (acta del 19/11)

| Punto del acta | Estado | Notas |
| --- | --- | --- |
| a · Letra pequeña con letra y botones al máximo | Corregido | Escala `--letra-*` (decisión 0007) |
| b · Botones descuadrados | Corregido | Píldoras `nowrap`, vista previa del perfil en su tarjeta |
| c · Texto de abajo descuadrado | Corregido | Aviso grande y centrado en la tableta |
| d · Temporizador en grupos | Corregido | Tres `fieldset` con `legend` |
| e · «Mi semana» cortada en el móvil | **Corregido a medias → arreglado ahora** | Con el peor perfil a 360×640 y un sábado, `<main>` se desplazaba 3 px: «Anterior / Siguiente» no caben en una fila. Ahora «Mi semana» usa «Antes / Después», como «Tareas de hoy» |
| f · Rejilla según el ancho | Corregido | `auto-fit` con mínimo en `em` |
| g · Medidas relativas en el móvil | Corregido | `dvh`, `em`, tokens |
| h · Horario escolar por días | Corregido | Un día cada vez, con L M X J V |
| i · Entrada centrada en todas las pantallas | Corregido | `encaja--centro` |
| Profesor · papelera roja | Corregido | `.boton--papelera` |
| Profesor · buscador de tareas | **Faltaba → hecho ahora** | Punto 14 de la retrospectiva |
| Profesor · pulir formato | Corregido | |

Otros hallazgos de la auditoría:

- **`static/css/tarea.css` tenía un `@media (min-width: 30.01rem)` sin cerrar** (ya en `main`). Todo
  lo que iba detrás (el bloque «Corrección estricta… móviles» y cualquier regla nueva) quedaba
  dentro y **nunca se aplicaba en el móvil**. Se cierra el bloque y se quita `.encaja` del
  `overflow-x: hidden !important`, que recortaría el foco y engañaría a `paginar.js`.
- `tests/test_profesional_tareas.py` (2 pruebas) falla también en `main`: no es de esta rama.
- El comentario de `.paginador--apilado` dice que los dos botones quedan en una fila, pero si no
  caben «Siguiente» baja: lo dice la última línea del comentario. No es un fallo.

## 2. Retrospectiva aplicada

| # | Qué pidió | Qué se ha hecho |
| --- | --- | --- |
| 1 | Contraseña del alumno que destaque | Recuadro menta con borde de 4 px, campo de 64 px y letra grande. En las 3 imágenes, la elegida lleva borde grueso continuo, fondo menta y un ✓ grande en SVG |
| 2 | Error de contraseña abajo | El aviso va debajo del campo (o de la rejilla), justo encima de «Entrar». Sigue con `role="alert"` |
| 3 | Avatares distintos de las contraseñas | Galería propia (`static/img/avatares/`, 18 caras alegres «Fun Emoji», CC BY 4.0) y `apps/usuarios/avatares.py`. El administrador la elige al crear o editar una cuenta (o sube un dibujo). Ningún nombre coincide con las 12 imágenes de la contraseña |
| 4 | Ver en qué hora estamos (valor añadido) | Flecha «Ahora» que avanza por la línea de «Tareas de hoy» y de «Mi horario» (de hoy): dentro de la tarea de ahora según lo que lleva y, entre dos, en el hueco. Decorativa (`aria-hidden`), se recoloca cada 30 s |
| 5 | Por defecto, el horario | El estudiante entra a «Mi horario» (de hoy, con «Salir»); «Tareas de hoy» es un botón al pie. Afecta a HU-01-06 PA3/PA4 (a dónde lleva al entrar) |
| 6 | Logo del día en la barra | La forma del día (`_dia_forma.html`) junto a la fecha. En la tableta en vertical, con la fecha corta; en el móvil con letra 24 o 32 no cabe y se quita (la fecha sigue escrita) |
| 7 | No tan estrictos con la hora | Se puede empezar una tarea en cualquier momento del día hasta su hora de fin, si no hay otra en marcha. `MARGEN_EMPEZAR_ANTES = None`. **Cambia la prueba de aceptación de HU-02-03** («Antes de la hora de inicio no puedo confirmar el inicio»): hay que actualizarla en Jira y en el Product Backlog |
| 8 | Plan B más sencillo (valor añadido) | Opción A elegida por el equipo, con el buscador arriba: «así lo verá el alumno» numerado y las tarjetas de la biblioteca; tocar = añadir o quitar (`aria-pressed`), «Primera» lo pone el primero, «+ Nueva» es una tarjeta más. Sin desplegables ni Subir / Bajar |
| 9 | Fecha de hoy al asignar | «Desde» sale con la fecha de hoy (formato ISO para `<input type="date">`) |
| 10 | El alumno personaliza su perfil | **No se hace:** es HU-04-05 (Could, iteración 3) |
| 11 | Más sitio para los pasos | Al empezar una tarea con pasos, una sola columna: el tiempo arriba, el paso grande y el botón abajo. «Escuchar» pasa a la cabecera de los pasos |
| 12 | Pantalla de enhorabuena | «¡Bravo!» tras terminar: pictograma con ✓, la frase, cuántas lleva hoy y «Siguiente: …». Sin sonido; la única animación respeta `prefers-reduced-motion` |
| 13 | Hecha frente a no hecha | Hecha: borde verde continuo, etiqueta rellena y sello ✓. Vencida o no se ha podido: borde discontinuo y sello ✕ |
| 14 | Buscador de tareas del tutor | Buscar por nombre o descripción y filtrar por ámbito en la biblioteca |
| 15 | Distinguir a los alumnos en Tareas planificadas | Franja con avatar y nombre arriba de cada tarjeta; dos columnas también en la tableta |
| 16 | «Tareas creadas» → «Biblioteca de tareas» | En el menú, el título y los botones de volver («‹ Biblioteca») |
| 17 | Buscador de alumnos del tutor | En «Alumnos», por nombre, apellidos o código |

## 3. Auditoría de accesibilidad (skill `a11y-colegio`)

Medido con axe + barrido (tableta 1024×768 y móvil 390×844) en «Mi horario», «Tareas de hoy»,
«¡Bravo!», contraseña del estudiante, Plan B, Biblioteca, Alumnos y Crear cuenta; Lighthouse en
la contraseña (100/100). Además, las pruebas de navegador del proyecto en los 6 tamaños con el
perfil por defecto y con el peor (Sofía).

- **Corregido durante la auditoría:** la letra del día en la barra salía a 13,6 px; ahora 16 px.
- **Sin fallos axe** en ninguna pantalla revisada.
- **Revisado y aceptado:** en las pantallas de adulto el barrido pasa del panel lateral a la barra
  de título «subiendo» (es la estructura de la decisión 0003). En Plan B, de la columna «así lo
  verá» a la de la biblioteca (orden de columnas, el mismo que se ve).
- **Falso positivo:** en la biblioteca del móvil, el desplegable «Ámbito» «se solapa» con las
  tarjetas, pero está dentro del `<details>` cerrado.
- **Paradas de barrido:** «Mi horario» 8 (la de «Tareas de hoy» es la octava, tras los 5 días),
  «¡Bravo!» 3, contraseña 2. En adultos, 15–30 (la biblioteca, por los 3 botones de cada tarea).
- **No verificable aquí:** VoiceOver y TalkBack reales, y un pulsador físico.
- **Pendiente (ya lo estaba):** la tarea en marcha con el peor perfil en móviles de 360–412 px
  sigue desplazando `<main>` (último recurso de la decisión 0005); ahora los pasos tienen toda la
  pantalla, pero con letra 32 y botones de 80 el paso no cabe entero.

## 4. Pruebas

- `tests/test_retrospectiva_19_11.py` (24) y `tests/e2e/test_retrospectiva_19_11.py` (81).
- Actualizadas las que dependían de la hora de empezar, de a dónde se entra y del Plan B.
- Unitarias: 917 pasan (fallan las 2 de `test_profesional_tareas.py`, igual que en `main`).
  Navegador: 557 pasan y 3 fallos conocidos (`xfail`).
