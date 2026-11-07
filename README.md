# Despega · Agenda accesible

Aplicación web para que el alumnado del Colegio de Educación Especial Purísima Concepción organice su tiempo y sus tareas, y para que tutores, profesionales y familias la configuren y la sigan. Proyecto de DGP y MDA (Universidad de Granada) de **Despega Team**.

> **Estado: iteración 1 (diseño).** El repositorio solo contiene la infraestructura para empezar a desarrollar. No hay ninguna funcionalidad implementada: las pantallas y los modelos se programan a partir de la iteración 2, sobre los bocetos y el modelo de datos acordados en esta.

## Tecnologías

| Capa | Herramienta |
| --- | --- |
| Servidor | Python 3.12 + Django 5.2 LTS (Django REST Framework solo para endpoints JSON) |
| Interfaz | Plantillas de Django + HTMX + CSS propio con variables |
| Base de datos | PostgreSQL 16 |
| Seguridad | Argon2, django-axes, HTTPS con Caddy |
| Contenedores | Docker + Docker Compose |
| Pruebas | pytest-django, Playwright + axe-core, Lighthouse |
| Calidad | GitHub Actions, ruff, pre-commit |

Justificación completa en la Propuesta Técnica (apartado 5.2) y en [docs/decisiones/0001-stack.md](docs/decisiones/0001-stack.md).

## Empezar

Guías paso a paso (al principio de cada una hay una tabla para saber qué camino te toca según tu versión):

- [Ubuntu 20.04 / 22.04 / 24.04](docs/instalacion/ubuntu.md)
- [Windows 10 / 11](docs/instalacion/windows.md)

| Sistema | Camino recomendado |
| --- | --- |
| Ubuntu 22.04 o 24.04 | Docker |
| Ubuntu 20.04 | Actualizar a 22.04 (ver guía) |
| Windows 11 23H2 o posterior | Docker Desktop |
| Windows 10 | Sin Docker (Python y PostgreSQL instalados) |

Resumen con Docker:

```bash
# Si ya tienes el repositorio: git switch main && git pull   (en lugar de clonar)
git clone https://github.com/tomaas05/App-Colegio-Accesible.git
cd App-Colegio-Accesible
cp .env.example .env
docker compose up --build
```

Abre <http://localhost:8000>: debe aparecer «El entorno de desarrollo funciona».

## Estructura

```text
App-Colegio-Accesible/
├── apps/                    # Una app de Django por módulo del reparto de la iteración 1
│   ├── usuarios/            #   Usuario, clase, estudiante, atención            (Manu)
│   ├── agenda/              #   Ejecución y avance de pasos                     (Tomás)
│   ├── tareas/              #   Tarea, paso, asignación                         (Úrsula)
│   ├── perfil/              #   Perfil visual y temporizador                    (Jorge)
│   ├── horario/             #   Franja, asignatura, horario de clase            (Javi)
│   ├── centro/              #   Tareas del centro (iteración 2)
│   ├── seguimiento/         #   Seguimiento y bienestar (iteración 2)
│   └── comun/               #   Comando cargar_datos_prueba
│       ├── models.py        #     tablas de la app (ver docs/iteracion-1/base-datos/)
│       ├── admin.py         #     cómo se ven en /admin/
│       ├── migrations/
│       ├── templates/<app>/ #     plantillas propias de la app
│       └── tests/
├── config/                  # Proyecto Django
│   ├── settings/            #   base.py · dev.py · test.py
│   └── urls.py
├── templates/               # base.html (estructura accesible común) e inicio provisional
├── static/
│   ├── css/                 #   tokens.css (paleta y tamaños) · base.css (foco, botones…)
│   ├── fonts/               #   Open Sans y Nunito servidas por nosotros (RNF1.1.2)
│   ├── js/
│   └── vendor/htmx/
├── tests/                   # Pruebas de humo, de la base de datos y e2e de accesibilidad
├── docker/                  # entrypoint.sh y Caddyfile (HTTPS para la demo)
├── docs/
│   ├── instalacion/         #   Guías Ubuntu y Windows
│   ├── iteracion-1/         #   Bocetos y diseño de la base de datos (entregables It1)
│   ├── decisiones/          #   Registro de decisiones técnicas (ADR)
│   ├── actas/               #   Actas de reunión
│   ├── manual-coordinacion.md
│   ├── contribuir.md        #   Ramas, commits y pull requests
│   └── demo-https.md        #   Cómo montar la demo en la Wi-Fi del aula
├── requirements/            # base.txt (ejecución) · dev.txt (pruebas y calidad)
├── Dockerfile · docker-compose.yml
└── pyproject.toml           # Configuración de ruff y pytest
```

## Órdenes habituales

| Para… | Con Docker | Sin Docker (entorno virtual activado) |
| --- | --- | --- |
| Arrancar | `docker compose up` | `python manage.py runserver` |
| Pruebas | `docker compose exec web pytest` | `pytest` |
| Accesibilidad | — (necesita navegador, hazlo sin Docker) | `pytest -m e2e` |
| Migraciones | `docker compose exec web python manage.py makemigrations` | `python manage.py makemigrations` |
| Cargar datos de prueba | `docker compose exec web python manage.py cargar_datos_prueba` | `python manage.py cargar_datos_prueba` |
| Volver a cargarlos desde cero | `… cargar_datos_prueba --reiniciar` | ídem |
| Tarea para Lucía en 1 minuto | `… cargar_datos_prueba --tarea-ahora` | ídem |
| Revisar estilo | `docker compose exec web ruff check .` | `ruff check .` |

## Datos de prueba

`cargar_datos_prueba` crea usuarios, dos clases, el horario, cinco tareas con pasos y sus asignaciones. Todo es ficticio, y las imágenes son marcadores de posición generados al vuelo. **Contraseña de todos los adultos: `despega2026`.**

| Usuario | Quién es |
| --- | --- |
| `admin` | Administración; también entra en <http://localhost:8000/admin/> |
| `tutor` | Ana, tutora de PTVAL 1 (Lucía, Mateo, Sofía, Hugo, Martina y Leo) |
| `tutor2` | Pedro, tutor de PTVAL 2 (Daniela, Pablo y Vega) |
| `profesional` | Luis, logopeda; atiende a Lucía y a Hugo |
| `familiar` | Carmen, familiar de Lucía |
| `familiar2` | Javier, familiar de Daniela |

Los estudiantes pulsan su avatar y después, según su perfil, eligen 3 imágenes (**perro, sol y flor**, en cualquier orden) o, en el caso de **Mateo**, escriben la contraseña **`mateo2026`**. Sofía tiene marcado que usa lector de pantalla. Las tareas de PTVAL 1 son a las 9:00, 10:30, 12:00 y 17:00, todos los días (también el fin de semana, para poder probar cualquier día). Lucía tiene además ejecuciones de ayer y una tarea de casa a las 20:00. Lucía, Mateo y Sofía tienen perfiles distintos del de por defecto.

## Documentación del equipo

- [Manual de Coordinación](docs/manual-coordinacion.md)
- [Cómo contribuir](docs/contribuir.md)
- [Iteración 1: bocetos y base de datos](docs/iteracion-1/README.md)
