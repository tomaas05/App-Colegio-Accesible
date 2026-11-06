# 0001 · Stack tecnológico

- **Estado:** aceptada
- **Fecha:** 2026-10-23 (tarea T2 de la iteración 1)
- **Responsable:** Tomás Serrano

## Contexto

Siete personas, tres iteraciones y un cliente que exige WCAG 2.2 AA demostrable y privacidad estricta de los datos de los estudiantes. El riesgo principal es el tiempo, no la tecnología.

## Decisión

Aplicación web con páginas generadas en el servidor y JavaScript solo donde hace falta (temporizador y avisos):

- Python 3.12 + Django 5.2 LTS; Django REST Framework solo para los pocos endpoints JSON.
- Plantillas de Django + HTMX + CSS propio con variables para la personalización por estudiante.
- PostgreSQL 16.
- Argon2, django-axes y HTTPS con Caddy.
- Docker Compose para que todo el equipo tenga el mismo entorno.
- pytest-django, Playwright + axe-core y Lighthouse para las pruebas; ruff, pre-commit y GitHub Actions para la calidad.
- Fuentes, librerías y pictogramas servidos desde nuestro servidor (RNF1.1.2).

## Alternativas descartadas

- **Flutter Web:** dibuja la interfaz en un lienzo; es más difícil demostrar WCAG con herramientas estándar.
- **Spring Boot:** solo lo conoce una persona.
- **Vercel:** su modelo sin servidor no encaja con una base de datos propia.
- **Funcionamiento sin conexión:** añade complejidad y el centro tiene Wi-Fi en aulas y comedor.

## Consecuencias

- HTML semántico por defecto, verificable con axe en cada pull request.
- Un solo lenguaje en el servidor; la curva de aprendizaje se concentra en Django.
- La interactividad en tiempo real (panel del tutor) se resuelve con sondeo HTMX; SSE solo si hiciera falta.
