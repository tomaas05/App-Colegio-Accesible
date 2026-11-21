# 0005 · Pantallas sin desplazamiento y revisión de la profesora

- **Estado:** propuesta (rama `correcciones-profesora`, pendiente de revisión del equipo)
- **Fecha:** 2026-11-16
- **Responsable:** Tomás (con los dueños de cada pantalla: Manu, Úrsula, Jorge y Javi)

## Contexto

En la reunión de noviembre de 2026 la profesora revisó los bocetos y pidió:

1. **Entrada:** que la primera pantalla enseñe directamente las clases y, en pequeño, la entrada de
   los adultos (antes había que elegir «Estudiante o Adulto»).
2. **Agenda del estudiante:** las tareas en una sola línea de tiempo, horizontal o vertical, nunca
   partida en filas; si no caben, en pantallas distintas y no en filas distintas. Un solo paso por
   pantalla. Nada de otras tareas dentro de una tarea («siguiente tarea: …»).
3. **Barra de título en todas las pantallas:** dónde estoy, la fecha de hoy y quién soy.
4. **Adultos:** sin desplazamiento. En lugar de «Perfil visual», «Alumnos»: al pulsar uno se abre su
   perfil visual, por categorías (letra, colores…) y en tarjetas, con dos pasos como mucho. Sin
   tarjeta de vista previa aparte: los cambios se ven en la propia tarjeta de configuración y se
   guardan solo al pulsar «Guardar»; si se sale sin guardar, se avisa.
5. **Creación de tareas por el estudiante:** los que tengan más capacidad podrían usar la misma
   creación que los adultos; el tutor configuraría qué tipo tiene cada uno.

Y, como regla general del equipo: **ninguna pantalla se desplaza** (solo se tolera en alguna vista
de ordenador). Por «sin desplazamiento» la profesora entiende botones de «Anterior / Siguiente».

## Decisión

### Paginar en lugar de desplazarse (`static/js/paginar.js`)

- Cada pantalla ocupa justo el alto del dispositivo (`base.css`: `body` a `100dvh`, `overflow:
  hidden`). La barra de título va arriba, el cuerpo (`.encaja`) se queda con lo que sobra y, si hace
  falta, un pie con el paginador (`templates/_paginador.html`).
- Una lista con `data-paginar` enseña solo los elementos que caben en su `.encaja` y el resto pasa a
  otras pantallas con «Anterior / Siguiente». Sirve igual para avatares, la línea de tiempo, una
  tabla, un formulario o una lista dentro de una parte de la pantalla (listas anidadas).
- **Formularios largos por pantallas** (`data-pag-variable`): el formulario se parte en bloques y en
  cada pantalla van los que caben. En crear tarea los bloques son pequeños (`data-items=".bloque"`) y
  el título de su grupo («Imagen de la tarea», «Paso 2») sale en cada pantalla donde hay uno suyo.
  El botón de guardar ocupa el sitio de «Siguiente» en la última pantalla (`final=True` y
  `data-solo-ultima`), así la acción principal está siempre abajo a la derecha.
- La pantalla que se ve es siempre la del elemento con el foco; un campo con error o el destino de
  un enlace del resumen de errores se enseñan solos.
- **Plegables** (`.plegable--solo`): lo que no hace falta siempre (buscar y filtrar, «Poner una
  asignatura») va plegado; en el móvil, al abrirlo ocupa el sitio de lo que va detrás.
- **Tablas en el móvil** (`.tabla--tarjetas`): cada fila es una tarjeta; nada de desplazarse a
  los lados.
- **Sin JavaScript** no se oculta nada: la página se ve entera y se desplaza como siempre.
- Último recurso: si ni un solo elemento cabe (letra de 32 px en un móvil pequeño), se desplaza
  `<main>`; el texto nunca se corta (RNF4.1.6).

### Plantillas comunes

`_volver.html` (botón de volver de la barra), `_paginador.html`, `_barra_datos.html` (fecha, nombre
y hora del estudiante), `_icono.html` (iconos del boceto v3), `_dia_forma.html` (letra, forma y color
de cada día, boceto B30: se usa en «Mi horario», asignar tarea, el horario del administrador y la
agenda que consulta el profesional), `perfil/_grupo.html` y `usuarios/_errores.html`. Los parciales
comunes se incluyen con `only`, para que no hereden por error variables de la vista (la agenda del
profesional pasaba `anterior` y `siguiente` y salían en los botones de otra lista).

### La fecha, siempre en español

`apps/comun/templatetags/fechas.py` escribe la fecha con nombres fijos. `{% now %}` usa el idioma
activo y, con el navegador en inglés, salía «Sunday, 15 de November».

### Punto 5 (creación de tareas por el estudiante)

Ahora solo el ajuste del tutor: `perfil.creacion_tareas` (`ninguna`, `asistente` o `completa`),
por defecto `ninguna`, como categoría «Crear tareas» del perfil de cada alumno. Recoge también el
permiso de RF3.3.3 (`ninguna` = sin permiso). Las pantallas del estudiante siguen en la iteración 3
(HU-03-09 y HU-03-10): `asistente` será el paso a paso del boceto B31 y `completa`, el mismo
formulario de crear tarea de los adultos (B32), solo con el ámbito «ocio» y fuera del horario
escolar.

## Alternativas descartadas

- **Desplazamiento con barras más grandes:** la profesora lo descartó; con pulsador o con poca
  precisión, desplazar es un gesto más y se pierde de vista dónde se está.
- **Calcular en el servidor cuántos caben:** depende del dispositivo, de la letra (16 a 32 px) y del
  tamaño de los botones del perfil; solo el navegador lo sabe.
- **Pestañas en lugar de «Anterior / Siguiente»:** más paradas de barrido y cada pantalla de
  formulario tendría que tener nombre propio.

## Consecuencias

- Las pruebas en navegador que rellenan formularios tienen que pasar de pantalla:
  `tests/e2e/ayudas.py` (`ir_a`) pulsa «Anterior / Siguiente» hasta que se ve el elemento.
- Herramienta de medida usada en la revisión: todas las pantallas a 360×640, 768×1024, 1024×768,
  1280×800 y 1366×768 sin desplazamiento, también con errores, con el formulario plegable abierto y
  con varios pasos añadidos.
- **Ampliación (19/11, decisión 0007):** se añaden 393×659 (iPhone 15 con las barras de Safari) y
  412×780 (Android con las barras de Chrome), y el peor perfil del estudiante (letra 32, botones 80,
  alto contraste). Las comprobaciones comunes están en `tests/e2e/ayudas.py` (`revisar`).
