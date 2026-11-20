# 0007 · La letra sale del perfil y las pantallas se encuadran

- **Estado:** propuesta (rama `diseno/encuadre-responsive`, pendiente de revisión del equipo)
- **Fecha:** 2026-11-19
- **Responsable:** Manu Izquierdo (con los dueños de cada pantalla)

## Contexto

El 19/11 probamos la app en una tableta y en dos móviles reales (Oppo A74 e iPhone 15); ver el
acta del 19/11. Con la letra y los botones más grandes del perfil, la barra de título, la
fecha, las horas, los chips de estado y los días de la semana seguían pequeños. Además había
días de «Mi semana» montados unos sobre otros, huecos vacíos en la tableta y la entrada pegada
arriba.

La causa principal: `data-letra` (16, 20, 24 o 32 px, RF4.1.2) solo cambia `--tamano-base`, y
eso solo lo usan `body` y la tarjeta del perfil visual. Los otros **108 `font-size` estaban en
`rem`**, y el `rem` se mide contra la raíz del navegador (16 px), no contra el perfil.
`docs/contribuir.md` pedía «siempre en rem», que estaba bien para respetar el zoom pero no
servía para el perfil.

## Decisión

- **Escala de letra en `tokens.css`** sobre `--tamano-base`. Con la letra por defecto (20 px):

  | Token | Cálculo | Tamaño |
  | --- | --- | --- |
  | `--letra-xs` | `max(1rem, base × 0,8)` | 16 px |
  | `--letra-s` | `max(1rem, base × 0,9)` | 18 px |
  | `--letra-m` | base | 20 px |
  | `--letra-l` | base × 1,2 | 24 px |
  | `--letra-xl` | base × 1,3 | 26 px |
  | `--letra-2xl` | base × 1,4 | 28 px |

  - Con la letra por defecto los tamaños son prácticamente los de antes, así que los adultos no
    notan el cambio.
  - Con la letra 32, todo crece en proporción.
  - El suelo `max(1rem, …)` mantiene los 16 px mínimos (RNF4.1.6) también con la letra 16.
- **Se declara en `:root, [data-letra]`.** Una variable con `var()` se resuelve en el elemento
  donde se declara. Así, la tarjeta del perfil visual, que lleva su propio `data-letra`, recalcula
  la escala al elegir otro tamaño.
- **Regla:** en los componentes, `font-size` solo con `--letra-*`, `em` o
  `calc(var(--tamano-base) * x)`. Nunca `px` ni `rem`. `--tamano-base` está en `rem`, así que el
  zoom del navegador sigue funcionando (1.4.4). `clamp()` en la letra, solo mezclando rem y vw.
- **Lo que acompaña a un texto va en `em`** para que crezca con él: la forma del día
  (`.dia-forma`), las marcas de los pasos y el avatar de la barra.
- **Alto de pantalla:** `100dvh`, con `100vh` delante como respaldo.
- **Sin `order` de CSS.** El paginador apilado (letra grande en el móvil) ya no sube el texto con
  `order: -1`. Ahora «Anterior» y el texto van en la primera fila y «Siguiente» debajo, a la
  derecha. El orden visual es el del DOM y el del barrido.
- **Sin `loading="lazy"`.** Lo que no se ve está en otra página del paginador y tiene que estar
  cargado cuando se pasa a ella.
- **Pruebas comunes.** `tests/e2e/ayudas.py` tiene `RESOLUCIONES` (los 6 tamaños de revisión, con
  393×659 y 412×780 de los móviles del acta) y `revisar(page, letra=…)`, que comprueba:
  - axe sin fallos;
  - sin desplazamiento de la página ni de `<main>`;
  - nada fuera de la pantalla ni de su caja;
  - los elementos de una lista no se montan;
  - objetivos de 48 px o más;
  - con el peor perfil, ningún texto por debajo del 80 % de la letra del perfil.

  `tests/e2e/test_encuadre.py` lo aplica a las pantallas del estudiante con el perfil por
  defecto (Hugo) y con el peor (Sofía: letra 32, botones 80 y alto contraste), a las de entrada y
  a las de adultos del acta.
- **Container queries en `em`** cuando la disposición depende de cuánto texto cabe, no del tamaño
  de la pantalla. En la condición, el `em` es la letra del contenedor (la del perfil). Así, «Mi
  semana» con la letra 32 no se aprieta en 7 columnas en una tableta.
- **Paginador sin sitio:** con letra y botones muy grandes en el móvil, «2 de 4» se sigue
  leyendo pero no se ve, y «Anterior / Siguiente» quedan en una fila. Así cabe al menos una
  tarjeta en 360×640.
- **`paginar.js`: dos listas en la misma zona.** Una tarea tiene sus partes («Qué es /
  Hacerla») y, dentro, sus pasos, las dos en la misma `.encaja`. La segunda lista quitaba la
  marca `sin-encaje` que había puesto la primera, y «Hacerla» se montaba sobre el paginador. Ahora
  cada lista guarda si no cabe, y la zona lleva la marca si alguna lo necesita. Las zonas que
  contienen una `sin-encaje` también crecen (`.encaja:has(.sin-encaje)`). Las partes de la tarea
  se miden una a una (`data-pag-variable`), porque miden muy distinto.
- **Iconos en SVG** (`_icono.html`), nunca glifos en `::before`: «⏻ Salir» salía como un
  cuadrado vacío en Android. La papelera de «Quitar» lleva su nombre completo en un texto oculto
  a la vista, en `--error` y de 48 px como mínimo.
- La guía para el equipo y para Claude Code está en `.claude/skills/despega-maquetacion/SKILL.md`.

## Alternativas descartadas

- **Cambiar `html { font-size }` según el perfil:** todo lo que está en `rem` crecería, también
  los márgenes, los anchos y los cortes de las media queries. La pantalla de 360 px se comportaría
  como una de 180 y se perdería el control de qué crece y qué no.
- **Letra fluida solo con `vw` o `cqi`:** no responde al zoom del navegador (1.4.4) y no tiene
  nada que ver con lo que eligió el tutor.
- **Un token por cada valor que había** (14 tamaños): demasiados para elegir bien. Seis cubren
  todos los usos.

## Consecuencias

- Con la letra 32 caben menos cosas en cada pantalla. Lo que no cabe se pagina (decisión 0005), y
  las pantallas del acta se ajustan una a una en esta misma rama.
- **Pendiente (Tomás):** con letra 32 y botones de 80, la parte «Hacerla» de una tarea en marcha
  mide más que un móvil de 360×640, 393×659 o 412×780. Incluye los pasos, el paso con «Hecho»,
  el aviso y «No puedo hacerla». Ahí se desplaza `<main>` (último recurso de la decisión 0005). Para
  quitarlo hay que partir «Hacerla» en más pantallas. Está marcado como fallo conocido en
  `tests/e2e/test_encuadre.py` (`PENDIENTES`).
- **Pantallas de adulto con la letra del navegador a 32 px:** se acepta que `<main>` se desplace
  (último recurso). Nada queda fuera de alcance.
- Un `font-size` en `rem` nuevo vuelve a romper el perfil. Lo detecta `test_encuadre.py` en las
  pantallas del estudiante. En la revisión de cada PR hay que mirar también las de adultos.
- `docs/contribuir.md` y los comentarios de cabecera de cada CSS ya dicen la regla nueva.
