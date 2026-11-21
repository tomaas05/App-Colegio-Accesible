---
name: despega-maquetacion
description: Reglas y patrones de maquetación de Despega (agenda accesible). Pantallas sin desplazamiento (paginar.js), letra que sale del perfil del estudiante, dvh, rejillas auto-fit y cómo comprobarlo en 6 tamaños con el peor perfil. Úsala siempre que cambies CSS o plantillas, o al revisar por qué una pantalla se desborda, se descuadra o no escala.
---

# Maquetación de Despega

Despega la usan estudiantes con pulsador (barrido), poca precisión o dificultades cognitivas. Un desborde o un botón que se sale de la pantalla puede impedir que un alumno haga su tarea. Por eso estas reglas **mandan sobre cualquier otra guía**, también sobre la skill `responsive-design`.

## Reglas (obligatorias)

### 1. Sin desplazamiento ([decisión 0005](../../../docs/decisiones/0005-sin-desplazamiento-y-revision-profesora.md))

- Con JavaScript, `body` mide `100dvh` y no se desplaza. La barra va arriba, `.encaja` se queda el alto que sobra y el pie lleva `_paginador.html`.
- Lo que no cabe **se pagina**:

  ```html
  <div class="encaja">
    <ol id="tareas" data-paginar> … </ol>   <!-- cada hijo es un elemento -->
  </div>
  {% include "_paginador.html" with de="tareas" que="Más tareas" only %}
  ```

- Atributos de la lista:
  - elementos de alto distinto (bloques de formulario, días de la semana): `data-pag-variable`;
  - elementos que no son hijos directos: `data-items=".selector"`;
  - número fijo por página: `data-por-pagina` / `data-max`;
  - página inicial: `aria-current` o `data-pag-inicio` en un elemento.
- **Prohibido:** `overflow: auto/scroll` en contenedores del estudiante, listas que se desplazan, `loading="lazy"` (lo que está oculto en otra página debe estar cargado cuando se enseña) y carruseles.
- Último recurso (lo pone `paginar.js`, no tú): si ni un elemento cabe, `.sin-encaje` deja desplazar `<main>`. El texto nunca se corta (RNF4.1.6).

### 2. Accesibilidad (WCAG 2.2 AA como mínimo)

| Qué | Valor | Cómo |
| --- | --- | --- |
| Objetivo táctil | ≥ 48 px (perfil: 48, 64 u 80) | `min-width/min-height: var(--toque)` o `var(--toque-grande)` |
| Separación entre objetivos | ≥ 12 px | `gap: var(--separacion)` |
| Foco | 4 px visible | ya en `base.css` (`:focus-visible`); no lo quites ni lo tapes con `overflow: hidden` sin dejar margen |
| Contraste | 4,5:1 texto · 3:1 iconos, bordes de control y foco | solo tokens de color (`tokens.css` documenta los ratios); `--verde` y `--naranja` nunca para texto ni para transmitir estado |
| Color | nunca la única señal | símbolo + texto, forma (`_dia_forma.html`), borde discontinuo… |
| Orden | DOM = visual = barrido | **sin `order`, sin `flex-direction: *-reverse` para reordenar, sin `tabindex` positivo**, sin `position: absolute` para recolocar controles |
| Solo icono | nombre accesible | `aria-label` que empiece por el texto visible si lo hay (2.5.3); el SVG con `aria-hidden="true" focusable="false"` |

### 3. Letra que sale del perfil

- `data-letra` (16/20/24/32) solo cambia `--tamano-base`. El `rem` **no** cambia con el perfil: una letra en `rem` se queda igual con letra 32.
- En componentes, `font-size` solo con:
  - los tokens `--letra-*` de `tokens.css` (escala sobre `--tamano-base`, con suelo de 16 px);
  - `em` (relativo al padre, que ya hereda del perfil);
  - `calc(var(--tamano-base) * x)`, con `max(1rem, …)` si `x < 1`.
- **Prohibido:** `font-size` en `px` o `rem` en componentes. `clamp()` en letra solo si mezcla rem y vw (`clamp(1rem, 0.9rem + 0.5vw, 1.25rem)`), nunca solo `vw` ni `cqi`, para que el zoom del navegador siga funcionando (1.4.4).
- Iconos, formas de día y avatares que acompañan a un texto: en `em`, para que crezcan con él.
- Espacios, bordes, radios y anchos de rejilla: `rem` vale. Si deben crecer con la letra (ancho mínimo de una tarjeta con texto), usa `em`.

### 4. Alto de pantalla

- `height: 100vh; height: 100dvh;` (la primera línea es el respaldo). Nunca solo `vh`: en móvil la barra del navegador tapa el pie.
- Imágenes que deben caber en alto: `min(9rem, 22dvh)`, como en `agenda.css`.

## Patrones adoptados

- **Encuadre:** el contenido no se arrima arriba. Pantallas de una sola cosa (entrar, contraseña, vacío): `.encaja.encaja--centro` (`justify-content: safe center`). Pantallas con zona principal y botón: columna en rejilla `grid-template-rows: auto 1fr auto`, con el botón principal siempre abajo y en el mismo sitio.
- **Listas de tarjetas:** `grid-template-columns: repeat(auto-fit, minmax(min(100%, 14em), 1fr))`. El ancho mínimo va en `em` para que con letra 32 haya menos columnas, no texto partido. `auto-fill` solo si quieres conservar los huecos de las columnas vacías.
- **Container queries en `em` para cambiar de disposición según la letra.** Una media query en `rem` mira la pantalla. Con letra 32, una tableta de 1024 px tiene el sitio de una de 640. En la condición de una container query, el `em` es la letra del contenedor, es decir, la del perfil:

  ```css
  .semana-zona { container: semana / inline-size; }          /* en el padre */
  @container semana (min-width: 48em) { .semana { grid-template-columns: 5fr 2fr; } }
  ```

  Ejemplos: «Mi semana» (7 columnas solo si caben con esa letra) y el pie de la agenda (el icono de «Mi semana» se oculta si el botón mide menos de 7 veces su letra, salvo en el perfil «solo imagen»).
- **Paginador sin sitio** (`.paginador--apilado`, lo pone `paginar.js`): el texto «2 de 4» se sigue leyendo pero no se ve, y los dos botones quedan en una fila. No se usa `order`.
- **Píldoras y chips de estado:** `white-space: nowrap` y `width: fit-content`. El borde va con `--petroleo` o `--error`, nunca con `--naranja`. Si no caben, se acorta el texto visible (`.solo-ancho`) y el nombre completo se sigue leyendo.
- **Aviso en el sitio del botón** («Podrás empezar a las…»): `.estado-grande` (`--letra-l`, caja menta sin forma de píldora, para que no parezca un botón).
- **Iconos:** SVG de `templates/_icono.html` (trazos de Lucide), nunca emojis ni glifos Unicode raros en `::before`: en Android salen como un cuadrado vacío (pasó con «⏻ Salir»). Dentro de un botón:

  ```html
  <button …><span class="icono-boton" aria-hidden="true">{% include "_icono.html" with nombre="salir" only %}</span> Salir</button>
  ```

  `.icono-boton` mide en `em`. El perfil «solo texto» lo oculta y «solo imagen» deja solo el icono.
- **Acción destructiva («Quitar»):** papelera roja con todo su nombre en un texto oculto a la vista (no en `aria-label`, así un texto que cambia con JavaScript sigue valiendo):

  ```html
  <button class="boton--aux boton--papelera" …><span class="icono-boton" aria-hidden="true">{% include "_icono.html" with nombre="papelera" only %}</span><span class="visualmente-oculto">Quitar Música del lunes a las 09:00</span></button>
  ```

  Mide ≥ `var(--toque)`, va en `--error` (5,4:1 sobre blanco) y se separa de la acción principal con `--separacion`. No añade confirmación (el boceto solo permite ventanas en 3 casos).
- **Listas paginadas de alto muy distinto** (las partes de una tarea): `data-pag-variable`, para
  que cada una se mida sola. Sin él, `paginar.js` mide con la primera y la grande se desborda.
  Dos listas pueden compartir una `.encaja`: cada una lleva su propio «no cabe».
- **Textos «solo para el lector» dentro de `<main>`:** `.js main` es `position: relative`. Si no, un `position: absolute` por debajo del pliegue alarga el documento.
- **Días de la semana:** siempre `_dia_forma.html` (letra + forma + color), que mide en `em`.

## Qué no aplicar de `responsive-design`

| Dice | Aquí |
| --- | --- |
| Objetivos de 44 px | 48 px mínimo, y lo que diga el perfil |
| Lazy-load de lo que está fuera de pantalla | Prohibido: lo «fuera de pantalla» está en otra página del paginador |
| Letra fluida con `vw` o `cqi` | Solo `--tamano-base` del perfil; `clamp()` con rem + vw como mucho |
| `100vh` / `svh` / `lvh` | `100dvh` con respaldo `100vh` |
| Desplazamiento horizontal de tablas | `.tabla--tarjetas` (cada fila es una tarjeta) o paginar |

Si quieres consultarla: `npx skills add https://github.com/wshobson/agents --skill responsive-design` (se instala en `.agents/`, que no se sube).

## Cómo comprobarlo

- **Tamaños:** 360×640, 393×659 (iPhone 15 con barras de Safari), 412×780 (Android con barras de Chrome), 768×1024, 1024×768, 1280×800 y 1366×768.
- **Perfiles:**
  - por defecto;
  - **peor perfil**: Sofía, A03 en los datos de prueba (letra 32, botones 80, alto contraste);
  - en pantallas de adulto, letra del navegador a 32 px (`--blink-settings=defaultFontSize=32`).
- **En cada combinación:**
  - axe sin fallos (etiquetas `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`);
  - `document.scrollingElement` y `<main>` sin desplazamiento;
  - ningún elemento se sale de su caja;
  - objetivos ≥ 48 px y ningún par de objetivos se tapa.
  
  Las ayudas comunes están en `tests/e2e/ayudas.py`.
- Antes de dar una pantalla por buena: skill `a11y-colegio` (en Windows, `CHROME_PATH` al Chrome instalado; la salida va a `a11y-informe/`, que no se sube) y mira el orden de barrido numerado.
