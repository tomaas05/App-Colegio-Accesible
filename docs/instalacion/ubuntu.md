# Instalación en Ubuntu

Hay dos caminos:

- **A. Con Docker (recomendado).** No instalas Python ni PostgreSQL en tu equipo; todos tenemos exactamente el mismo entorno.
- **B. Sin Docker.** Útil si tu portátil va justo de memoria o quieres depurar con el IDE más cómodamente.

Elige uno. En los dos, la comprobación final es la misma: abrir <http://localhost:8000> y ver «El entorno de desarrollo funciona».

## ¿Qué versión de Ubuntu tengo?

```bash
lsb_release -d
```

| Versión | Camino A (Docker) | Camino B (sin Docker) |
| --- | --- | --- |
| **24.04** | Sí | Sí, lo más sencillo: Python 3.12 y PostgreSQL 16 vienen de serie |
| **22.04** | Sí | Sí, añadiendo dos repositorios (se explica en B.1 y B.2) |
| **20.04** | Probablemente, sin garantía | No recomendado |

### Si tienes Ubuntu 20.04

Ubuntu 20.04 dejó de tener soporte en mayo de 2025, y eso se nota en este proyecto:

- Docker ya no lo incluye entre las versiones soportadas, aunque los comandos del camino A deberían seguir instalando la última versión que publicaron para 20.04.
- El repositorio *deadsnakes* retiró los paquetes de 20.04, así que no hay una forma sencilla con `apt` de instalar Python 3.12.
- Trae PostgreSQL 12, y Django 5.2 necesita PostgreSQL 14 o superior.

**Lo recomendado es actualizar a 22.04** (haz copia de seguridad antes; tarda en torno a una hora):

```bash
sudo apt update && sudo apt full-upgrade -y
sudo do-release-upgrade
```

Si no puedes actualizar, prueba el camino A tal cual. Si el `apt install` de A.1 falla, avisa al coordinador antes de seguir: no merece la pena perder la tarde peleándote con la instalación.

---

## 0. Requisitos comunes

```bash
sudo apt update
sudo apt install -y git
git config --global user.name "Tu Nombre"
git config --global user.email "tu-correo@correo.ugr.es"
```

Clona el repositorio (si ya lo tenías, haz `git pull` en su lugar):

```bash
cd ~/Documentos/4oCARRERA
git clone https://github.com/tomaas05/App-Colegio-Accesible.git
cd App-Colegio-Accesible
cp .env.example .env
```

---

## A. Con Docker

### A.1 Instalar Docker Engine y Compose

```bash
# Repositorio oficial de Docker
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Usar docker sin sudo (cierra sesión y vuelve a entrar después)
sudo usermod -aG docker $USER
```

Comprueba: `docker compose version` debe mostrar la versión 2.x.

### A.2 Arrancar

```bash
docker compose up --build
```

La primera vez tarda unos minutos (descarga imágenes e instala dependencias). Verás que aplica las migraciones y luego `Starting development server at http://0.0.0.0:8000/`.

Abre <http://localhost:8000>.

### A.3 Crear tu usuario administrador

En otra terminal:

```bash
docker compose exec web python manage.py createsuperuser
```

Entra en <http://localhost:8000/admin/>.

### A.4 Pruebas

```bash
docker compose exec web pytest
```

Las pruebas de accesibilidad en navegador (`pytest -m e2e`) necesitan Chromium; ejecútalas con el camino B o déjalas a GitHub Actions.

### A.5 Parar

`Ctrl+C` y después `docker compose down`. Para borrar también la base de datos: `docker compose down -v`.

---

## B. Sin Docker

### B.1 Python 3.12

Ubuntu 24.04 ya trae Python 3.12:

```bash
sudo apt install -y python3.12 python3.12-venv python3-pip
```

En Ubuntu 22.04 hay que añadir el PPA *deadsnakes*:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv
```

### B.2 PostgreSQL 16

Ubuntu 24.04 trae PostgreSQL 16 directamente:

```bash
sudo apt install -y postgresql
```

En Ubuntu 22.04 (trae la 14) usa el repositorio oficial:

```bash
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo apt install -y postgresql-16
```

Crea el usuario y la base de datos del proyecto (los mismos valores que `.env.example`):

```bash
sudo -u postgres psql -c "CREATE ROLE despega LOGIN PASSWORD 'despega' CREATEDB;"
sudo -u postgres createdb -O despega despega
```

`CREATEDB` hace falta porque pytest crea su propia base de datos de pruebas.

### B.3 Entorno virtual y dependencias

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
```

Edita `.env` y cambia **una línea**:

```text
POSTGRES_HOST=localhost
```

### B.4 Base de datos y arranque

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre <http://localhost:8000>.

### B.5 Pruebas

```bash
pytest                              # pruebas normales
playwright install --with-deps chromium   # solo la primera vez
pytest -m e2e                       # accesibilidad: axe + sin scroll a 360×640, 1280×800, 1366×768
```

Si ya tienes Google Chrome instalado puedes saltarte `playwright install` y usar `pytest -m e2e --browser-channel chrome`.

Lighthouse (opcional, necesita Node.js y el servidor arrancado):

```bash
npx lighthouse http://localhost:8000 --only-categories=accessibility --view
```

---

## Último paso (los dos caminos): pre-commit

Revisa el estilo antes de cada commit. Se instala una vez:

```bash
# Con el camino B ya lo tienes en el entorno virtual. Con el A:
sudo apt install -y pipx && pipx install pre-commit

pre-commit install
```

---

## Problemas frecuentes

| Síntoma | Solución |
| --- | --- |
| `permission denied while trying to connect to the Docker daemon` | No has cerrado sesión tras `usermod -aG docker`. Cierra sesión o ejecuta `newgrp docker`. |
| `port is already allocated` en el 5432 | Tienes PostgreSQL nativo además de Docker. El contenedor no publica el 5432 salvo que lo descomentes; si lo hiciste, para el nativo: `sudo systemctl stop postgresql`. |
| `port is already allocated` en el 8000 | Otro `runserver` sigue abierto. Ciérralo o usa `python manage.py runserver 8001`. |
| `connection refused` a PostgreSQL (camino B) | `POSTGRES_HOST` sigue en `db`. Cámbialo a `localhost` en `.env`. |
| `password authentication failed for user "despega"` | El rol no existe o tiene otra contraseña. Repite B.2. |
| `permission denied for database` al lanzar pytest | Falta `CREATEDB`: `sudo -u postgres psql -c "ALTER ROLE despega CREATEDB;"` |
| Errores de permisos en `staticfiles/` con Docker | Tu usuario no es el UID 1000. Ejecuta `sudo chown -R $USER staticfiles`. |
