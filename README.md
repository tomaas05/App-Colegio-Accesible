# Despega · Agenda accesible

Aplicación web para que el alumnado del Colegio de Educación Especial Purísima Concepción organice su tiempo y sus tareas, y para que tutores, profesionales y familias la configuren y la sigan. Proyecto de DGP y MDA (Universidad de Granada) de **Despega Team**.

> **Estado: iteración 1 (implementación).** Están en `main` la base de datos, los datos de prueba y las primeras historias de usuario. La Entrega 1 vence el miércoles 11/11/2026 a las 23:59.

### Qué funciona ya

| Dirección | Pantalla | HU | Responsable |
| --- | --- | --- | --- |
| `/` | Portada «¿Quién eres?»: Estudiante o Adulto (B01). Aquí llega quien no ha entrado | HU-01-06 | Manu |
| `/estudiante/` | ¿Cuál es tu clase? (B02) → avatares de la clase (B03) → 3 imágenes o contraseña | HU-01-06 | Manu |
| `/entrar/` | Entrar como tutor, profesional, familiar o administrador (B12), con bloqueo tras 5 fallos | HU-01-07 | Manu |
| `/panel/` | Pantalla principal del adulto, con su nombre y sus opciones (B13) | HU-01-07 | Manu |
| `/usuarios/` | Cuentas con filtros (B20), crear cuenta (B21) y cargar una lista de estudiantes desde un CSV. Solo el administrador | HU-01-01 | Manu |
| `/agenda/` | Agenda del día del estudiante | HU-02-01 a HU-02-04 | Tomás |
| `/agenda/tarea/<id>/` | Detalle de una tarea: pasos, Empezar y Terminar | HU-02-02 a HU-02-04 | Tomás |
| `/tareas/crear/` · `/tareas/catalogo/` | Crear una tarea y ver las creadas | HU-03-01 | Úrsula |
| `/perfil/` · `/perfil/<codigo>/` | Elegir estudiante y configurar su perfil visual (B52) | HU-04-01 | Jorge |
| `/panel/mis-estudiantes/` | El profesional elige en la lista del centro los estudiantes que atiende (B26) | HU-01-08 | Javi |

Cuando se fusione tu historia, añade aquí sus pantallas.

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

Abre <http://localhost:8000>: debe aparecer la portada «¿Quién eres?». Después carga los datos de prueba (`docker compose exec web python manage.py cargar_datos_prueba`) y entra como estudiante o como adulto (ver [Datos de prueba](#datos-de-prueba)).

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
├── templates/               # base.html (estructura accesible común)
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
| Desbloquear a quien ha fallado 5 veces | `docker compose exec web python manage.py axes_reset` | `python manage.py axes_reset` |

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

Los adultos entran en <http://localhost:8000/entrar/> y llegan a su pantalla principal (`/panel/`). Tras **5 intentos fallidos seguidos**, ese usuario queda bloqueado **5 minutos** en ese equipo; los demás pueden seguir entrando (ver [docs/decisiones/0002-entrada-y-sesion.md](docs/decisiones/0002-entrada-y-sesion.md)). Para no esperar mientras pruebas: `axes_reset` (tabla de arriba).

Los estudiantes entran desde la portada: **Estudiante → su clase → su avatar** y después, según su perfil, eligen 3 imágenes (**perro, sol y flor**, en cualquier orden) o, en el caso de **Mateo**, escriben la contraseña **`mateo2026`**. Sofía tiene marcado que usa lector de pantalla. Las tareas de PTVAL 1 son a las 9:00, 10:30, 12:00 y 17:00, todos los días (también el fin de semana, para poder probar cualquier día). Lucía tiene además ejecuciones de ayer y una tarea de casa a las 20:00. Lucía, Mateo y Sofía tienen perfiles distintos del de por defecto.

> Por ejemplo, Lucía: <http://localhost:8000> → Estudiante → PTVAL 1 → Lucía → perro, sol y flor → su agenda. Al equivocarse sale «No es correcto. Vuelve a intentarlo.» y puede repetir sin límite: a los estudiantes no se les bloquea (ver la decisión 0002).
>
> El atajo de desarrollo `/agenda/?como=A01` (con `AGENDA_ENTRAR_COMO=1` en el `.env`) ya no hace falta y se quitará.

### Crear cuentas y cargar una lista de estudiantes

Entra como `admin` → **Usuarios**. Desde ahí, **Crear cuenta** da de alta a un estudiante (clase, avatar, código automático y 3 imágenes o contraseña) o a un adulto (usuario y contraseña inicial). Un administrador creado así también entra en <http://localhost:8000/admin/>, igual que `admin`. Los usuarios que empiezan por `est-` están reservados a los estudiantes (`est-a01` es Lucía por dentro). **Cargar lista de estudiantes** crea una clase entera desde un CSV con estas columnas (hay una plantilla para descargar en la propia pantalla):

```text
nombre;apellidos;imagenes;contrasena
Lucía;García Pérez;perro sol flor;
Mateo;López Ruiz;;mateo2026
```

En `imagenes` van 3 palabras de la rejilla separadas por espacios; si el estudiante entra con contraseña, se rellena `contrasena` y se deja `imagenes` vacía. Vale `;` (lo que guarda Excel en español) o `,`. Las filas correctas se crean y las que tienen algún error se listan con su número y el motivo, para corregirlas y cargarlas aparte. Las clases se siguen creando desde <http://localhost:8000/admin/>.

## Documentación del equipo

- [Manual de Coordinación](docs/manual-coordinacion.md)
- [Cómo contribuir](docs/contribuir.md)
- [Iteración 1: bocetos y base de datos](docs/iteracion-1/README.md)
