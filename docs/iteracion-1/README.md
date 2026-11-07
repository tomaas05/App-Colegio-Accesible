# Iteración 1 · Diseño

**22 de octubre – 11 de noviembre de 2026.** En esta iteración se diseña la aplicación antes de programarla: bocetos de todas las pantallas y diseño de la base de datos. **No se programa funcionalidad.**

## Qué va en cada carpeta

| Carpeta | Contenido | Tareas |
| --- | --- | --- |
| [bocetos/](bocetos/) | Mockup HTML navegable y su documento de contexto | T5–T12 |
| [base-datos/](base-datos/) | Modelo entidad-relación, modelo relacional y diccionario de datos | T13–T18 |
| [../actas/](../actas/) | Actas de las reuniones de los viernes | T19 |

Los documentos formales (Planificación, Propuesta Técnica, Manual de Coordinación…) se mantienen en el proyecto compartido y se entregan en PDF.

## Qué deja preparado esta iteración para la 2

- El repositorio con su estructura, Docker, pruebas e integración continua (T3).
- Una app de Django por objetivo, vacía; su `models.py` indica qué requisitos de información le corresponden.
- La base de datos completa de la iteración 1 (modelos, migraciones, admin y datos de prueba), según el [diseño](base-datos/README.md).
- La plantilla base accesible y las variables CSS con la paleta del boceto.
- La prueba automática de accesibilidad (axe + resoluciones), lista para añadirle cada pantalla.

## Cómo pasar de esta iteración a la 2

1. Los modelos ya están creados. Si una HU necesita cambiar una tabla, lo hace su dueño en su app y genera la migración (`python manage.py makemigrations <app>`).
2. Cada pantalla del boceto se convierte en una plantilla dentro de `apps/<app>/templates/<app>/`, reutilizando `base.html` y las variables de `tokens.css`.
3. Cada pantalla nueva se añade a `tests/e2e/test_accesibilidad.py`.
