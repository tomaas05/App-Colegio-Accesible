# 0003 · Estructura común y navegación

- **Estado:** propuesta (rama `mejora-ui-bocetos`, pendiente de revisión del equipo)
- **Fecha:** 2026-11-11
- **Responsable:** Manu Izquierdo (usuarios y plantilla base)

## Contexto

Cada plantilla repetía su cabecera (15 bloques `cabecera` distintos): unas con «Salir», otras con
«Volver», el estudiante sin «Salir» y ninguna con el logotipo. Los bocetos aprobados (v3) llevan el
logotipo en todas las pantallas, y la profesora pidió que el logotipo fuera la navegación principal.
La mayoría de usuarios usa móvil o tableta, con el dedo.

## Decisión

- **Un esqueleto único** en `templates/base.html` con dos parciales: `_cabecera.html` y `_aside.html`.
  Las plantillas ya no tienen bloque `cabecera`. Se conserva «Saltar al contenido».
- **Como en los bocetos, la barra superior es solo de los adultos** (`header`, `aside` > `nav` y `main`).
  Las pantallas de entrada (B01 a B03) y las del estudiante van **sin barra**: solo `main`, con su fila
  de título. En la portada el logotipo va junto a «¿Quién eres?». No hay pie.
- **El logotipo de la barra es un enlace** con el nombre accesible «Despega, ir al inicio» que lleva al
  adulto a `usuarios:panel`. `inicio_de()` (`apps/usuarios/navegacion.py`) da también el inicio del
  estudiante (`agenda:dia`) y de quien no ha entrado (`/`): lo usan las páginas de error.
- **Logotipo e icono** salen del boceto v3 (PNG en base64): `static/img/logo-despega.webp` (337×140,
  6 kB), `icono-despega.png` y `favicon.ico`. No es SVG porque no tenemos el original vectorial.
- **Panel lateral solo para adultos**: `<aside id="lateral">` con `<nav aria-label="Principal">`.
  Tiene «Inicio», las opciones del rol y, al final, «Salir» (POST con CSRF, decisión 0002).
- **Una sola lista de opciones:** `OPCIONES_POR_ROL` pasa de `views.py` a `apps/usuarios/navegacion.py`.
  El context processor `apps.usuarios.context_processors.navegacion` la da al panel lateral y la vista
  `panel` a las tarjetas, así no se desincronizan. Si una URL no existe, la opción no se enseña.
  No hace consultas a la base de datos.
- **Página actual:** `aria-current="page"` solo en la opción cuya dirección es la de la página. En una
  pantalla interior (por ejemplo `/usuarios/nueva/`) se marca la sección con borde y barra, sin
  `aria-current`. La marca no depende solo del color.
- **Comportamiento:** a partir de `64rem` el panel se ve siempre, a la izquierda. Por debajo, un botón
  con el texto «Menú» (48 px) lo abre y lo cierra: `aria-expanded`, `aria-controls`, Escape lo cierra
  y devuelve el foco al botón. No es un modal y no atrapa el foco. El corte está en rem: con la letra
  del navegador a 32 px equivale a 2048 px, así que el panel se pliega y no quita sitio.
- **Sin JavaScript** el panel se ve siempre (encima del contenido en pantallas estrechas) y el botón
  no aparece. `static/js/base.js` (1 kB) se carga sin `defer` para poner `html.js` antes de pintar:
  así nada cambia de sitio al cargar (CLS 0,002).
- **El estudiante no tiene barra ni panel lateral.** «Salir» está al principio de la fila del título de
  su agenda (`templates/_salir_estudiante.html`), donde el boceto B06 pone «‹ Menú», junto a su nombre.
- **«Volver»** deja la cabecera y pasa al principio del contenido en las 4 pantallas que lo tenían arriba.
- **Sin pie.** La atribución que exige la licencia de ARASAAC va, como texto, al final del panel
  lateral de los adultos y en el README. El estudiante no la ve: no le aporta nada.
- **Tarjetas de entrada como en B01 a B03:** fondo menta con borde, el dibujo en un recuadro blanco y
  el nombre debajo; la rejilla se centra en la pantalla. En la portada, dos tarjetas una al lado de
  otra si caben y, si no, una debajo de otra.
- **CSS primero móvil:** la base es una columna; `min-width` en rem añade la segunda. `100dvh`,
  `viewport-fit=cover` y `env(safe-area-inset-*)` en cabecera, panel y contenido.
- Foco de 4 px (`--foco-grosor`), como dicen los bocetos.

## Alternativas descartadas

- **Icono de tres barras:** un icono solo no dice qué hace. Queda como pregunta para el cliente.
- **Menú como modal o cajón que tapa:** atrapa el foco y añade un gesto; con pulsador es peor.
- **`<details>` sin JavaScript:** no da `aria-expanded` sobre un botón ni permite cerrar con Escape.
- **Guardar el estado en `localStorage`:** en móvil debe empezar cerrado y en ordenador se ve siempre.
- **Panel lateral también para el estudiante:** más elementos y más paradas de barrido.

## Consecuencias

- Añadir una opción al panel sigue siendo una línea en `OPCIONES_POR_ROL`, ahora en `navegacion.py`.
- Una pantalla nueva no escribe cabecera: extiende `base.html` y rellena `titulo`, `estilos`, `contenido` y `scripts`.
- Pruebas: `tests/test_estructura_comun.py` y `tests/e2e/test_accesibilidad_estructura.py` (axe con el
  panel cerrado y abierto, a 360×640, 768×1024, 1024×768 y 1366×768, con letra de 32 px y con teclado).
