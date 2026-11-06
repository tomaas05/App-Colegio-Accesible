#!/bin/sh
# Se ejecuta cada vez que arranca el contenedor "web".
set -e

# Aplica las migraciones pendientes (la base de datos ya está lista:
# docker-compose espera al healthcheck de "db").
python manage.py migrate --noinput

# Copia los estáticos a staticfiles/ para que Caddy los sirva en la demo.
python manage.py collectstatic --noinput --verbosity 0

exec "$@"
