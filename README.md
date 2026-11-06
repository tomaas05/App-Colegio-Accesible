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

Guías paso a paso:

- [Ubuntu](docs/instalacion/ubuntu.md)
- [Windows](docs/instalacion/windows.md)

Resumen con Docker (la opción recomendada en los dos sistemas):

```bash
git clone https://github.com/tomaas05/App-Colegio-Accesible.git
cd App-Colegio-Accesible
cp .env.example .env
docker compose up --build
```

Abre <http://localhost:8000>: debe aparecer «El entorno de desarrollo funciona».

## Estructura

```text
App-Colegio-Accesible/
├── apps/                    # Una app de Django por objetivo de la Propuesta Técnica
│   ├── cuentas/             #   Obj. 1 · Usuarios, acceso y permisos      (Manuel Jesús)
│   ├── agenda/              #   Obj. 2 · Agenda del estudiante            (Tomás)
│   ├── planificacion/       #   Obj. 3 · Creación y planificación         (Úrsula)
│   ├── perfiles/            #   Obj. 4 · Personalización y accesibilidad  (Kaya)
│   ├── centro/              #   Obj. 5 · Tareas del centro                (Javier)
│   └── seguimiento/         #   Obj. 6 · Seguimiento y bienestar          (Jorge)
│       ├── models.py        #     vacío: indica qué RI y entidades le tocan
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
├── tests/                   # Pruebas de humo y e2e de accesibilidad (axe + resoluciones)
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
| Crear administrador | `docker compose exec web python manage.py createsuperuser` | `python manage.py createsuperuser` |
| Revisar estilo | `docker compose exec web ruff check .` | `ruff check .` |

## Documentación del equipo

- [Manual de Coordinación](docs/manual-coordinacion.md)
- [Cómo contribuir](docs/contribuir.md)
- [Iteración 1: bocetos y base de datos](docs/iteracion-1/README.md)
