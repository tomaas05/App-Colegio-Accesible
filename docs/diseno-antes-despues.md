# Diseño · antes y después (acta del 19/11)

Rama `diseno/encuadre-responsive`. Esta página es para que el equipo lo apruebe antes de fusionar con `main`.

El 19/11 probamos la app en una tableta y en dos móviles reales, y salieron fallos visuales (acta del 19/11). Aquí está cada uno, antes y después, en tres tamaños. La explicación técnica está en la [decisión 0007](decisiones/0007-letra-del-perfil-y-encuadre.md), y la guía para el equipo en [.claude/skills/despega-maquetacion](../.claude/skills/despega-maquetacion/SKILL.md).

> **Sobre las capturas:** la auditoría de la iteración 1 decidió no subir capturas al repositorio. Esta página es una excepción, solo para esta revisión: es una selección en WebP (unos 2,8 MB). El juego completo (23 pantallas × 6 tamaños × 2 perfiles) se genera en local en `capturas/`, que no se sube.

## Lo que había detrás

1. **La letra del perfil no llegaba a casi nada.** `data-letra` (16, 20, 24 o 32 px) solo cambiaba la letra del cuerpo, y **108 tamaños estaban en `rem`**, que no siguen al perfil. Ahora hay una escala `--letra-xs … --letra-2xl` en `tokens.css` que sale de la letra del perfil, con 16 px como mínimo. Con la letra por defecto, los tamaños son prácticamente los de antes.
2. **Cuando nada cabía, a veces se solapaba en lugar de desplazarse.** Había dos causas, en `paginar.js` y en `base.css`:
   - dos listas en la misma zona se quitaban la marca la una a la otra;
   - las zonas que contienen otra que no cabe no crecían.
3. **Textos ocultos a la vista que alargaban la página.** Los `position: absolute` se colocaban respecto a la ventana y no respecto a `<main>`.

## En cifras

Medido sobre 23 pantallas en 6 tamaños (360×640, 393×659, 412×780, 1024×768, 1280×800 y 1366×768), con dos perfiles:

- el perfil por defecto;
- el peor perfil: en el estudiante, Sofía (letra 32, botones 80 y alto contraste); en las pantallas de adulto, la letra del navegador a 32 px.

| Qué | Antes | Después |
| --- | --- | --- |
| Textos por debajo del 80 % de la letra del perfil | 421 | **0** |
| La página entera se desplaza y no se llega a lo de abajo | 48 | **0** |
| Botones a menos de 8 px de otro | 65 | 6 |
| Pantallas del estudiante con el peor perfil que desplazan `<main>` (pantalla y tamaño) | 2: la agenda a 360 y 393 | 3: la tarea en marcha a 360, 393 y 412 (ver «Pendiente») |

Con el perfil por defecto, ninguna pantalla se desplaza en ningún tamaño, ni antes ni después. Antes, la tarea en marcha cabía con el peor perfil porque su letra no crecía (se quedaba en 16–20 px aunque el perfil pidiera 32). Las 6 separaciones que quedan son de «Mis estudiantes», donde la medida cuenta la casilla dentro de su propia etiqueta: no es un fallo.

## a · Mi horario del estudiante crece con su letra

Con la letra y los botones al máximo, la barra de título, la fecha y los días se quedaban en 16–21 px. Ahora salen de la letra del perfil: el título, la fecha (80 %), las formas de los días (en `em`) y los botones de 80 px. En el móvil, las cinco píldoras se reparten el ancho sin bajar de 48 px, y la forma del día no se sale de su botón.

**Mi horario**, peor perfil (Sofía: letra 32, botones 80, alto contraste)

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Mi horario, peor perfil, iPhone 15 con Safari (393×659), antes](diseno/capturas/mi-horario__peor__393x659__antes.webp) | ![Mi horario, peor perfil, iPhone 15 con Safari (393×659), después](diseno/capturas/mi-horario__peor__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Mi horario, peor perfil, Tableta horizontal (1024×768), antes](diseno/capturas/mi-horario__peor__1024x768__antes.webp) | ![Mi horario, peor perfil, Tableta horizontal (1024×768), después](diseno/capturas/mi-horario__peor__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Mi horario, peor perfil, Tableta grande (1280×800), antes](diseno/capturas/mi-horario__peor__1280x800__antes.webp) | ![Mi horario, peor perfil, Tableta grande (1280×800), después](diseno/capturas/mi-horario__peor__1280x800__despues.webp) |

## b · Comedor: «Pendiente» en una línea · Perfil visual: la vista previa, en su tarjeta

La píldora ya no se parte (`nowrap`) y su borde es petróleo: el naranja es solo adorno y no llega a 3:1. Si la tarjeta es estrecha para la letra, dice solo «Pendiente», como en el móvil (*container query*). La vista previa del perfil (letra y botones del estudiante) se queda dentro de su tarjeta. Las pruebas lo comprueban con Lucía (64 px) y con Sofía (80 px) en los 6 tamaños.

**Comedor y menú**, perfil por defecto

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Comedor y menú, perfil por defecto, iPhone 15 con Safari (393×659), antes](diseno/capturas/comedor__defecto__393x659__antes.webp) | ![Comedor y menú, perfil por defecto, iPhone 15 con Safari (393×659), después](diseno/capturas/comedor__defecto__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Comedor y menú, perfil por defecto, Tableta horizontal (1024×768), antes](diseno/capturas/comedor__defecto__1024x768__antes.webp) | ![Comedor y menú, perfil por defecto, Tableta horizontal (1024×768), después](diseno/capturas/comedor__defecto__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Comedor y menú, perfil por defecto, Tableta grande (1280×800), antes](diseno/capturas/comedor__defecto__1280x800__antes.webp) | ![Comedor y menú, perfil por defecto, Tableta grande (1280×800), después](diseno/capturas/comedor__defecto__1280x800__despues.webp) |

**Perfil visual · Botones**, perfil por defecto

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Perfil visual · Botones, perfil por defecto, iPhone 15 con Safari (393×659), antes](diseno/capturas/perfil-botones__defecto__393x659__antes.webp) | ![Perfil visual · Botones, perfil por defecto, iPhone 15 con Safari (393×659), después](diseno/capturas/perfil-botones__defecto__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Perfil visual · Botones, perfil por defecto, Tableta horizontal (1024×768), antes](diseno/capturas/perfil-botones__defecto__1024x768__antes.webp) | ![Perfil visual · Botones, perfil por defecto, Tableta horizontal (1024×768), después](diseno/capturas/perfil-botones__defecto__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Perfil visual · Botones, perfil por defecto, Tableta grande (1280×800), antes](diseno/capturas/perfil-botones__defecto__1280x800__antes.webp) | ![Perfil visual · Botones, perfil por defecto, Tableta grande (1280×800), después](diseno/capturas/perfil-botones__defecto__1280x800__despues.webp) |

## c · Tarea en tablet horizontal: sin hueco y el aviso grande

«Qué es» se centra en su columna y, si la tarea no tiene pasos, «Podrás empezar a las…» va a la misma altura, en el sitio donde aparecerá «Empezar». Es 1,2 veces la letra del perfil, en una caja menta que no parece un botón.

**Tarea antes de la hora**, perfil por defecto

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Tarea antes de la hora, perfil por defecto, iPhone 15 con Safari (393×659), antes](diseno/capturas/tarea-antes-de-la-hora__defecto__393x659__antes.webp) | ![Tarea antes de la hora, perfil por defecto, iPhone 15 con Safari (393×659), después](diseno/capturas/tarea-antes-de-la-hora__defecto__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Tarea antes de la hora, perfil por defecto, Tableta horizontal (1024×768), antes](diseno/capturas/tarea-antes-de-la-hora__defecto__1024x768__antes.webp) | ![Tarea antes de la hora, perfil por defecto, Tableta horizontal (1024×768), después](diseno/capturas/tarea-antes-de-la-hora__defecto__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Tarea antes de la hora, perfil por defecto, Tableta grande (1280×800), antes](diseno/capturas/tarea-antes-de-la-hora__defecto__1280x800__antes.webp) | ![Tarea antes de la hora, perfil por defecto, Tableta grande (1280×800), después](diseno/capturas/tarea-antes-de-la-hora__defecto__1280x800__despues.webp) |

**Tarea antes de la hora**, peor perfil (Sofía: letra 32, botones 80, alto contraste)

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Tarea antes de la hora, peor perfil, iPhone 15 con Safari (393×659), antes](diseno/capturas/tarea-antes-de-la-hora__peor__393x659__antes.webp) | ![Tarea antes de la hora, peor perfil, iPhone 15 con Safari (393×659), después](diseno/capturas/tarea-antes-de-la-hora__peor__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Tarea antes de la hora, peor perfil, Tableta horizontal (1024×768), antes](diseno/capturas/tarea-antes-de-la-hora__peor__1024x768__antes.webp) | ![Tarea antes de la hora, peor perfil, Tableta horizontal (1024×768), después](diseno/capturas/tarea-antes-de-la-hora__peor__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Tarea antes de la hora, peor perfil, Tableta grande (1280×800), antes](diseno/capturas/tarea-antes-de-la-hora__peor__1280x800__antes.webp) | ![Tarea antes de la hora, peor perfil, Tableta grande (1280×800), después](diseno/capturas/tarea-antes-de-la-hora__peor__1280x800__despues.webp) |

## d · Perfil › Temporizador en tres grupos

Tres `fieldset` con su `legend`: «Tipo de temporizador», «Avisos» y «Qué ve el estudiante». El lector de pantalla dice el grupo al entrar. Se pagina por opciones, y el título del grupo sale en cada pantalla donde hay una opción suya.

**Perfil visual · Temporizador**, perfil por defecto

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Perfil visual · Temporizador, perfil por defecto, iPhone 15 con Safari (393×659), antes](diseno/capturas/perfil-temporizador__defecto__393x659__antes.webp) | ![Perfil visual · Temporizador, perfil por defecto, iPhone 15 con Safari (393×659), después](diseno/capturas/perfil-temporizador__defecto__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Perfil visual · Temporizador, perfil por defecto, Tableta horizontal (1024×768), antes](diseno/capturas/perfil-temporizador__defecto__1024x768__antes.webp) | ![Perfil visual · Temporizador, perfil por defecto, Tableta horizontal (1024×768), después](diseno/capturas/perfil-temporizador__defecto__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Perfil visual · Temporizador, perfil por defecto, Tableta grande (1280×800), antes](diseno/capturas/perfil-temporizador__defecto__1280x800__antes.webp) | ![Perfil visual · Temporizador, perfil por defecto, Tableta grande (1280×800), después](diseno/capturas/perfil-temporizador__defecto__1280x800__despues.webp) |

## e · Mi semana en el móvil: los días ya no se montan

Las filas encogían por debajo de su contenido y el viernes quedaba tapado por el sábado. Ahora los días que no caben pasan de pantalla con «Anterior / Siguiente». Con la letra 32, la tableta ya no aprieta los 7 días en columnas: la disposición depende de cuánto texto cabe (*container query* en `em`), no del tamaño de la pantalla.

**Mi semana**, perfil por defecto

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Mi semana, perfil por defecto, iPhone 15 con Safari (393×659), antes](diseno/capturas/semana__defecto__393x659__antes.webp) | ![Mi semana, perfil por defecto, iPhone 15 con Safari (393×659), después](diseno/capturas/semana__defecto__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Mi semana, perfil por defecto, Tableta horizontal (1024×768), antes](diseno/capturas/semana__defecto__1024x768__antes.webp) | ![Mi semana, perfil por defecto, Tableta horizontal (1024×768), después](diseno/capturas/semana__defecto__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Mi semana, perfil por defecto, Tableta grande (1280×800), antes](diseno/capturas/semana__defecto__1280x800__antes.webp) | ![Mi semana, perfil por defecto, Tableta grande (1280×800), después](diseno/capturas/semana__defecto__1280x800__despues.webp) |

**Mi semana**, peor perfil (Sofía: letra 32, botones 80, alto contraste)

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Mi semana, peor perfil, iPhone 15 con Safari (393×659), antes](diseno/capturas/semana__peor__393x659__antes.webp) | ![Mi semana, peor perfil, iPhone 15 con Safari (393×659), después](diseno/capturas/semana__peor__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Mi semana, peor perfil, Tableta horizontal (1024×768), antes](diseno/capturas/semana__peor__1024x768__antes.webp) | ![Mi semana, peor perfil, Tableta horizontal (1024×768), después](diseno/capturas/semana__peor__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Mi semana, peor perfil, Tableta grande (1280×800), antes](diseno/capturas/semana__peor__1280x800__antes.webp) | ![Mi semana, peor perfil, Tableta grande (1280×800), después](diseno/capturas/semana__peor__1280x800__despues.webp) |

## f · Tutor › Alumnos: la rejilla aprovecha el ancho

`auto-fit` y ancho mínimo en `em`: las columnas vacías no ocupan sitio, las tarjetas se reparten el ancho y son más grandes (avatar de hasta 7 rem). Con letra grande hay menos columnas en lugar de texto partido.

**Alumnos**, perfil por defecto

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Alumnos, perfil por defecto, iPhone 15 con Safari (393×659), antes](diseno/capturas/alumnos__defecto__393x659__antes.webp) | ![Alumnos, perfil por defecto, iPhone 15 con Safari (393×659), después](diseno/capturas/alumnos__defecto__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Alumnos, perfil por defecto, Tableta horizontal (1024×768), antes](diseno/capturas/alumnos__defecto__1024x768__antes.webp) | ![Alumnos, perfil por defecto, Tableta horizontal (1024×768), después](diseno/capturas/alumnos__defecto__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Alumnos, perfil por defecto, Tableta grande (1280×800), antes](diseno/capturas/alumnos__defecto__1280x800__antes.webp) | ![Alumnos, perfil por defecto, Tableta grande (1280×800), después](diseno/capturas/alumnos__defecto__1280x800__despues.webp) |

## g · Agenda en el móvil con letra grande

«Salir» lleva un SVG: en Android, el glifo «⏻» salía como un cuadrado vacío. El título comparte fila con «Salir». «Mi semana» y «Mi horario» van en dos columnas iguales; si no caben con su icono, el icono deja sitio al texto (salvo en el perfil «solo imagen»). Con el peor perfil, la agenda cabe entera en 360×640 sin desplazarse.

**Tareas de hoy**, peor perfil (Sofía: letra 32, botones 80, alto contraste)

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Tareas de hoy, peor perfil, iPhone 15 con Safari (393×659), antes](diseno/capturas/agenda__peor__393x659__antes.webp) | ![Tareas de hoy, peor perfil, iPhone 15 con Safari (393×659), después](diseno/capturas/agenda__peor__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Tareas de hoy, peor perfil, Tableta horizontal (1024×768), antes](diseno/capturas/agenda__peor__1024x768__antes.webp) | ![Tareas de hoy, peor perfil, Tableta horizontal (1024×768), después](diseno/capturas/agenda__peor__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Tareas de hoy, peor perfil, Tableta grande (1280×800), antes](diseno/capturas/agenda__peor__1280x800__antes.webp) | ![Tareas de hoy, peor perfil, Tableta grande (1280×800), después](diseno/capturas/agenda__peor__1280x800__despues.webp) |

**Tareas de hoy**, perfil por defecto

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Tareas de hoy, perfil por defecto, iPhone 15 con Safari (393×659), antes](diseno/capturas/agenda__defecto__393x659__antes.webp) | ![Tareas de hoy, perfil por defecto, iPhone 15 con Safari (393×659), después](diseno/capturas/agenda__defecto__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Tareas de hoy, perfil por defecto, Tableta horizontal (1024×768), antes](diseno/capturas/agenda__defecto__1024x768__antes.webp) | ![Tareas de hoy, perfil por defecto, Tableta horizontal (1024×768), después](diseno/capturas/agenda__defecto__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Tareas de hoy, perfil por defecto, Tableta grande (1280×800), antes](diseno/capturas/agenda__defecto__1280x800__antes.webp) | ![Tareas de hoy, perfil por defecto, Tableta grande (1280×800), después](diseno/capturas/agenda__defecto__1280x800__despues.webp) |

## h · Horario escolar: un día cada vez

En lugar de una franja con los cinco días, se elige el día con L, M, X, J y V, como en «Mi horario» (enlaces con `aria-current` que funcionan sin JavaScript). Cada día enseña todas sus franjas, también las libres. «Poner» propone el día que se está viendo y, en pantallas anchas, va en una columna a la derecha. En el DOM va después de la lista, que es el orden del barrido.

**Horario escolar**, perfil por defecto

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Horario escolar, perfil por defecto, iPhone 15 con Safari (393×659), antes](diseno/capturas/horario-escolar__defecto__393x659__antes.webp) | ![Horario escolar, perfil por defecto, iPhone 15 con Safari (393×659), después](diseno/capturas/horario-escolar__defecto__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Horario escolar, perfil por defecto, Tableta horizontal (1024×768), antes](diseno/capturas/horario-escolar__defecto__1024x768__antes.webp) | ![Horario escolar, perfil por defecto, Tableta horizontal (1024×768), después](diseno/capturas/horario-escolar__defecto__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Horario escolar, perfil por defecto, Tableta grande (1280×800), antes](diseno/capturas/horario-escolar__defecto__1280x800__antes.webp) | ![Horario escolar, perfil por defecto, Tableta grande (1280×800), después](diseno/capturas/horario-escolar__defecto__1280x800__despues.webp) |

## i · Entrada y contraseña centradas también en tableta y ordenador

Centradas en vertical y en horizontal en todos los tamaños. Con `justify-content: safe center`, si no caben empiezan arriba y no se corta nada.

**Entrar (adultos)**, perfil por defecto

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Entrar (adultos), perfil por defecto, iPhone 15 con Safari (393×659), antes](diseno/capturas/entrar-adulto__defecto__393x659__antes.webp) | ![Entrar (adultos), perfil por defecto, iPhone 15 con Safari (393×659), después](diseno/capturas/entrar-adulto__defecto__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Entrar (adultos), perfil por defecto, Tableta horizontal (1024×768), antes](diseno/capturas/entrar-adulto__defecto__1024x768__antes.webp) | ![Entrar (adultos), perfil por defecto, Tableta horizontal (1024×768), después](diseno/capturas/entrar-adulto__defecto__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Entrar (adultos), perfil por defecto, Tableta grande (1280×800), antes](diseno/capturas/entrar-adulto__defecto__1280x800__antes.webp) | ![Entrar (adultos), perfil por defecto, Tableta grande (1280×800), después](diseno/capturas/entrar-adulto__defecto__1280x800__despues.webp) |

**Contraseña del estudiante**, perfil por defecto

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Contraseña del estudiante, perfil por defecto, iPhone 15 con Safari (393×659), antes](diseno/capturas/entrar-contrasena__defecto__393x659__antes.webp) | ![Contraseña del estudiante, perfil por defecto, iPhone 15 con Safari (393×659), después](diseno/capturas/entrar-contrasena__defecto__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Contraseña del estudiante, perfil por defecto, Tableta horizontal (1024×768), antes](diseno/capturas/entrar-contrasena__defecto__1024x768__antes.webp) | ![Contraseña del estudiante, perfil por defecto, Tableta horizontal (1024×768), después](diseno/capturas/entrar-contrasena__defecto__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Contraseña del estudiante, perfil por defecto, Tableta grande (1280×800), antes](diseno/capturas/entrar-contrasena__defecto__1280x800__antes.webp) | ![Contraseña del estudiante, perfil por defecto, Tableta grande (1280×800), después](diseno/capturas/entrar-contrasena__defecto__1280x800__despues.webp) |

## j · «Quitar» es una papelera roja

Los 9 «Quitar» (3 del comedor, reprografía, horario, paso de tarea, plan B, mis estudiantes y vínculos) son una papelera SVG en `--error` (5,4:1 sobre blanco), de 48 px como mínimo. El nombre accesible completo («Quitar Música del lunes a las 09:00») va en un texto oculto a la vista. La confirmación queda como estaba: no se añade ninguna. «Quitar filtros» no cambia, porque no borra nada.

**Horario escolar**, perfil por defecto

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Horario escolar, perfil por defecto, iPhone 15 con Safari (393×659), antes](diseno/capturas/horario-escolar__defecto__393x659__antes.webp) | ![Horario escolar, perfil por defecto, iPhone 15 con Safari (393×659), después](diseno/capturas/horario-escolar__defecto__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Horario escolar, perfil por defecto, Tableta horizontal (1024×768), antes](diseno/capturas/horario-escolar__defecto__1024x768__antes.webp) | ![Horario escolar, perfil por defecto, Tableta horizontal (1024×768), después](diseno/capturas/horario-escolar__defecto__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Horario escolar, perfil por defecto, Tableta grande (1280×800), antes](diseno/capturas/horario-escolar__defecto__1280x800__antes.webp) | ![Horario escolar, perfil por defecto, Tableta grande (1280×800), después](diseno/capturas/horario-escolar__defecto__1280x800__despues.webp) |

## Pendiente: tarea en marcha con el peor perfil en el móvil (Tomás)

Con la letra 32 y los botones de 80, la parte «Hacerla» de una tarea en marcha mide ella sola más que un móvil de 360×640, 393×659 o 412×780. Incluye la cabecera de pasos, el paso con «Hecho», el aviso y «No puedo hacerla». En esos casos se desplaza `<main>`, que es el último recurso de la decisión 0005; ya no se solapa nada. Para quitarlo del todo hay que partir «Hacerla» en más pantallas, y eso cambia la pantalla de la tarea. Está marcado como fallo conocido en `tests/e2e/test_encuadre.py` (`PENDIENTES`): si alguien lo arregla, la prueba avisa de que hay que quitar la marca.

| Tamaño | Antes | Después |
| --- | --- | --- |
| iPhone 15 con Safari (393×659) | ![Tarea en marcha, peor perfil, iPhone 15 con Safari (393×659), antes](diseno/capturas/tarea-en-curso__peor__393x659__antes.webp) | ![Tarea en marcha, peor perfil, iPhone 15 con Safari (393×659), después](diseno/capturas/tarea-en-curso__peor__393x659__despues.webp) |
| Tableta horizontal (1024×768) | ![Tarea en marcha, peor perfil, Tableta horizontal (1024×768), antes](diseno/capturas/tarea-en-curso__peor__1024x768__antes.webp) | ![Tarea en marcha, peor perfil, Tableta horizontal (1024×768), después](diseno/capturas/tarea-en-curso__peor__1024x768__despues.webp) |
| Tableta grande (1280×800) | ![Tarea en marcha, peor perfil, Tableta grande (1280×800), antes](diseno/capturas/tarea-en-curso__peor__1280x800__antes.webp) | ![Tarea en marcha, peor perfil, Tableta grande (1280×800), después](diseno/capturas/tarea-en-curso__peor__1280x800__despues.webp) |

## Cómo volver a generar las pruebas en navegador

Con Docker Desktop abierto y el compose arrancado:

```bash
docker run -d --name despega-e2e --network app-colegio-accesible_default -v "$PWD:/app" -w /app \
  --env-file .env -e POSTGRES_HOST=db mcr.microsoft.com/playwright/python:v1.65.0-noble sleep infinity
docker exec despega-e2e pip install -r requirements/dev.txt playwright==1.65.0
docker exec -e DJANGO_ALLOW_ASYNC_UNSAFE=true despega-e2e python -m pytest -m e2e
```

El script de capturas de esta revisión está en `capturas/`, que es local. Si el equipo lo quiere para otras revisiones, se puede subir aparte.
