# Imagen de desarrollo de Despega (Python 3.12 + Django 5.2 LTS)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Cliente de PostgreSQL para poder usar "manage.py dbshell"
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install -r requirements/dev.txt

COPY . .

# Usuario sin privilegios
RUN useradd --create-home despega && chown -R despega /app
USER despega

ENTRYPOINT ["sh", "docker/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
