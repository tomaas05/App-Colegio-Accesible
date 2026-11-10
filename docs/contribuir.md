# Cómo contribuir

## Ramas

- `main` está **protegida**: no se hace push directo. Todo entra por pull request con al menos una revisión y la CI en verde.
- **Una rama por historia de usuario**, con su identificador y un nombre corto, creada desde `main` actualizada:

```bash
git switch main && git pull
git switch -c HU-01-06-entrar-como-estudiante
```

| Rama | Para |
| --- | --- |
| `HU-xx-yy-nombre` | Una historia de usuario |
| `fix/nombre` | Corrección de un error |
| `docs/nombre` | Documentación (bocetos, modelo de datos, actas…) |
| `infra/nombre` | Docker, CI, configuración |

## Commits

Mensajes en español, en presente y con la clave de Jira de la HU al principio (`AGENDA-xxx`); así Jira enlaza los commits con la historia:

```text
AGENDA-144 Añade la pantalla de selección de avatar
AGENDA-182 Corrige el contraste del botón Terminar
```

`pre-commit` revisa el estilo antes de cada commit. Si falla, corrige (muchas veces lo arregla solo), vuelve a hacer `git add` y repite el commit.

## Pull requests

1. `git push -u origin <tu-rama>` y abre el PR en GitHub hacia `main`.
2. Rellena la plantilla: qué cambia, requisitos que cubre (RF/RNF) y cómo probarlo.
3. Espera a que la CI pase (estilo, pruebas y accesibilidad). **Mientras GitHub Actions no se ejecute** (facturación bloqueada), pásalo tú en local antes de abrir el PR y pega el resultado en la descripción: `pytest`, `ruff check .` y `pytest -m e2e`.
4. Revisión: un compañero y la Gestora de Calidad (Úrsula) revisan cada PR. Las Gestoras de Accesibilidad (Lara-Marie y Kaya) revisan la accesibilidad de todas las pantallas al cerrar la iteración.
5. Fusiona con **Squash and merge** y borra la rama.

## Dónde va cada cosa

- Modelos, vistas y plantillas: en la app de su dueño dentro de `apps/` (ver tabla del README). **Cada uno solo cambia su app**; si necesitas un cambio en una tabla de otro, pídeselo en Jira.
- Si cambias un modelo, incluye la migración en el mismo PR y avisa al grupo para que ejecute `migrate`.
- Lo que comparten varias apps (plantilla base, estilos comunes): `templates/` y `static/`.
- Cada pantalla nueva se añade a `PANTALLAS` en `tests/e2e/test_accesibilidad.py` para que axe la revise en las tres resoluciones. Si la pantalla pide sesión, haz como `tests/e2e/test_accesibilidad_usuarios.py` (entra con `force_login` y pasa la cookie al navegador).
- **Sesión y permisos** (ver [decisiones/0002-entrada-y-sesion.md](decisiones/0002-entrada-y-sesion.md)): una vista que pide sesión lleva `@login_required`, que manda a la portada «¿Quién eres?» (`/`) a quien no ha entrado, y después de entrar le devuelve a la pantalla que pedía. Que haya sesión no basta: comprueba también el rol en el servidor (`request.user.rol`, `request.user.es_adulto`, `request.user.es_estudiante`) y que el usuario puede ver ese estudiante o esa tarea.
- **Panel del adulto** (`/panel/`): para que tu pantalla aparezca en la pantalla principal de un rol, añade una línea a `OPCIONES_POR_ROL` en `apps/usuarios/views.py` dentro de tu PR y avisa a Manu. Es la única excepción a «cada uno solo cambia su app».
- Colores, tamaños y fuentes: siempre con las variables de `static/css/tokens.css` y en `rem`, nunca valores sueltos. Es lo que permitirá aplicar el perfil de cada estudiante (RF4.1.x).
- Decisiones técnicas que afecten a todo el equipo: un archivo nuevo en `docs/decisiones/`.

## Configurar la protección de `main` (una vez, el coordinador)

GitHub → *Settings → Branches → Add branch ruleset*:

- Target: `main`
- Require a pull request before merging (1 aprobación)
- Require status checks to pass: `Estilo (ruff)` y `Pruebas (pytest + PostgreSQL)`
- Block force pushes
