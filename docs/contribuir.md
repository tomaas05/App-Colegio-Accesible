# Cómo contribuir

## Ramas

- `main` está **protegida**: no se hace push directo. Todo entra por pull request con al menos una revisión y la CI en verde.
- Una rama por tarea o historia de Jira, creada desde `main` actualizada:

```bash
git switch main && git pull
git switch -c feature/DES-12-entrada-estudiante
```

| Prefijo | Para |
| --- | --- |
| `feature/` | Historia de usuario o funcionalidad nueva |
| `fix/` | Corrección de un error |
| `docs/` | Documentación (bocetos, modelo de datos, actas…) |
| `infra/` | Docker, CI, configuración |

Incluye siempre la clave de Jira (`DES-12`): así Jira enlaza la rama, los commits y el PR con la tarea.

## Commits

Mensajes en español, en presente y con la clave de Jira al principio:

```text
DES-12 Añade la pantalla de selección de avatar
DES-30 Corrige el contraste del botón Terminar
```

`pre-commit` revisa el estilo antes de cada commit. Si falla, corrige (muchas veces lo arregla solo), vuelve a hacer `git add` y repite el commit.

## Pull requests

1. `git push -u origin <tu-rama>` y abre el PR en GitHub hacia `main`.
2. Rellena la plantilla: qué cambia, requisitos que cubre (RF/RNF) y cómo probarlo.
3. Espera a que la CI pase (estilo, pruebas y accesibilidad).
4. Revisión: Gestora de Calidad (Úrsula) en lo general; Gestoras de Accesibilidad (Lara-Marie, Kaya) cuando haya pantallas.
5. Fusiona con **Squash and merge** y borra la rama.

## Dónde va cada cosa

- Modelos, vistas y plantillas de un objetivo: en su app de `apps/` (ver tabla del README).
- Lo que comparten varias apps (plantilla base, estilos comunes): `templates/` y `static/`.
- Cada pantalla nueva se añade a `PANTALLAS` en `tests/e2e/test_accesibilidad.py` para que axe la revise en las tres resoluciones.
- Colores, tamaños y fuentes: siempre con las variables de `static/css/tokens.css` y en `rem`, nunca valores sueltos. Es lo que permitirá aplicar el perfil de cada estudiante (RF4.1.x).
- Decisiones técnicas que afecten a todo el equipo: un archivo nuevo en `docs/decisiones/`.

## Configurar la protección de `main` (una vez, el coordinador)

GitHub → *Settings → Branches → Add branch ruleset*:

- Target: `main`
- Require a pull request before merging (1 aprobación)
- Require status checks to pass: `Estilo (ruff)` y `Pruebas (pytest + PostgreSQL)`
- Block force pushes
