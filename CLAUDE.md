# Despega · Instrucciones para Claude Code

Agenda accesible para el alumnado del Colegio de Educación Especial Purísima Concepción (Django 5.2 + plantillas + HTMX + CSS propio, PostgreSQL, Docker Compose). Lo usan estudiantes con pulsador (barrido), teclado adaptado, poca precisión o dificultades cognitivas, y los adultos que les configuran la agenda. **La accesibilidad manda sobre la estética.**

Lee antes de tocar nada: [README.md](README.md), [docs/contribuir.md](docs/contribuir.md) y [docs/decisiones/](docs/decisiones/README.md), sobre todo la 0003 (estructura), la 0005 (sin desplazamiento) y la 0006 (planificación).

## Reglas obligatorias

1. **Git:** no hagas commits, push ni PR salvo que te lo pidan. Al acabar un paso, da el título y la descripción del commit (`AGENDA-xxx Verbo en presente…`, en español). `main` está protegida: se trabaja en una rama.
2. **Una rama por trabajo**, creada desde `main` actualizada ([docs/contribuir.md](docs/contribuir.md)).
3. **Sin desplazamiento** ([decisión 0005](docs/decisiones/0005-sin-desplazamiento-y-revision-profesora.md)). El estudiante nunca hace scroll. Lo que no cabe se pagina con `static/js/paginar.js` (`data-paginar`, `data-pag-variable`, `templates/_paginador.html`). Nada de `loading="lazy"` ni de listas que se desplazan.
4. **WCAG 2.2 AA como mínimo:**
   - botones de 48 px o más (`var(--toque)`; el perfil los pone a 48, 64 u 80) y 12 px de separación (`var(--separacion)`);
   - foco visible de 4 px;
   - contraste de 4,5:1 en texto y de 3:1 en iconos y controles; nunca solo color;
   - orden del DOM = orden visual = orden de barrido (sin `order` de CSS ni `tabindex` positivo);
   - nombre accesible en todo lo que solo tenga icono.
5. **La letra sale del perfil del estudiante** (`--tamano-base`, `data-letra` 16/20/24/32 en `static/css/tokens.css`). Prohibidos los `font-size` fijos en px o rem en los componentes: usa los tokens `--letra-*`, `em` o `calc(var(--tamano-base) * x)`. Usa los tokens existentes (colores, `--toque`, `--separacion`, radios); no inventes colores.
6. **Alto de pantalla con `dvh`** (`vh` solo de respaldo). `clamp()` en la letra solo si mezcla rem y vw, para que el zoom siga funcionando.
7. **No cambies la funcionalidad ni los textos de las HU** sin que te lo pidan. Respeta los bocetos (`docs/iteracion-1/bocetos/despega_mockup_v3.html`) y la decisión 0003.

Más convenciones del equipo en [docs/contribuir.md](docs/contribuir.md): sin `style=` ni `onclick=`, parciales con `only`, `estudiantes_de()` para listar estudiantes, pictogramas siempre por `apps/comun/pictogramas.py`, y cada uno solo cambia su app.

## Skills

- `.claude/skills/despega-maquetacion/`: reglas de maquetación y patrones del proyecto. Úsala para cualquier cambio de CSS o de plantilla.
- `a11y-colegio`: auditoría con axe, Lighthouse y recorrido de barrido. Úsala antes de dar por buena una pantalla.
- `responsive-design` (de terceros, opcional: `npx skills add https://github.com/wshobson/agents --skill responsive-design`). Úsala solo como apoyo y nunca por encima de estas reglas.

## Dónde está cada cosa

| Qué | Dónde |
| --- | --- |
| Paleta, letra, botones y perfil (`data-*`) | `static/css/tokens.css` |
| Estructura, barra, `.encaja`, `.partes`, paginador, `.linea`, `.dia-forma` | `static/css/base.css` |
| Esqueleto y barra de título | `templates/base.html` + parciales `templates/_*.html` |
| Paginar en lugar de desplazarse | `static/js/paginar.js` |
| Cada pantalla | `apps/<app>/templates/<app>/` + `static/css/<app>.css` (dueños en el README) |
| Pruebas de navegador (axe, sin scroll) | `tests/e2e/` (ayudas comunes en `tests/e2e/ayudas.py`) |

## Cómo se prueba

```bash
docker compose up -d
docker compose exec web python manage.py cargar_datos_prueba --reiniciar
docker compose exec web pytest                 # unitarias
docker compose exec web ruff check .
docker compose exec web ruff format --check .
```

La imagen `web` no trae navegador. `pytest -m e2e` se lanza en local con Python 3.12 (camino B de `docs/instalacion/`) o en la imagen oficial `mcr.microsoft.com/playwright/python` conectada a la red del compose.

**Peor perfil para probar:** Sofía (A03): letra 32, botones 80 y alto contraste. Tamaños de revisión: 360×640, 393×659, 412×780, 768×1024, 1024×768, 1280×800 y 1366×768.
