# Instalación en Windows

Hay dos caminos:

- **A. Con Docker Desktop.** Mismo entorno que el resto del equipo, sin instalar Python ni PostgreSQL.
- **B. Sin Docker.** Python y PostgreSQL instalados directamente en Windows. Funciona en Windows 10 y 11.

Las órdenes son para **PowerShell**. La comprobación final en los dos caminos: abrir <http://localhost:8000> y ver «El entorno de desarrollo funciona».

## ¿Qué camino elijo?

Mira tu versión: pulsa `Win + R`, escribe `winver` e Intro.

| Tu Windows | Camino |
| --- | --- |
| **Windows 11 23H2 o posterior** (compilación 22631 o mayor) | **A**, Docker Desktop |
| **Windows 11 22H2 o anterior** | Actualiza Windows (*Configuración → Windows Update*) y usa **A**; si no puedes, **B** |
| **Windows 10** | **B**, sin Docker |

**Por qué Windows 10 va sin Docker:** Windows 10 ya no recibe soporte de Microsoft y Docker Desktop está dejando de funcionar en él (las versiones nuevas piden Windows 11 23H2). El camino B no tiene ese problema: Python 3.12 y PostgreSQL 16 se instalan sin complicaciones en Windows 10.

Si en Windows 10 quieres usar Docker de todas formas, la alternativa es instalar Ubuntu dentro de Windows (`wsl --install -d Ubuntu-24.04` como administrador), abrir esa terminal de Ubuntu y seguir la [guía de Ubuntu](ubuntu.md) completa. Docker Engine funciona dentro de WSL sin necesidad de Docker Desktop.

---

## 0. Requisitos comunes

### 0.1 Git

Instala Git con `winget` (o descárgalo de <https://git-scm.com/download/win>):

```powershell
winget install --id Git.Git -e
```

Cierra y vuelve a abrir PowerShell. Después:

```powershell
git config --global user.name "Tu Nombre"
git config --global user.email "tu-correo@correo.ugr.es"
# Importante: el repositorio usa finales de línea LF (ver .gitattributes)
git config --global core.autocrlf input
```

> **Por qué `core.autocrlf input`:** si Git convierte los archivos a CRLF, `docker/entrypoint.sh` deja de funcionar dentro del contenedor (`sh: 1: set: Illegal option -`). El `.gitattributes` del repositorio ya lo fuerza, pero así te evitas sorpresas en otros proyectos.

### 0.2 Clonar

```powershell
cd $HOME\Documents
git clone https://github.com/tomaas05/App-Colegio-Accesible.git
cd App-Colegio-Accesible
Copy-Item .env.example .env
```

### 0.3 Editor

VS Code: `winget install --id Microsoft.VisualStudioCode -e`. Al abrir la carpeta te propondrá las extensiones recomendadas del proyecto (`.vscode/extensions.json`): acéptalas.

---

## A. Con Docker Desktop

> Solo para Windows 11 23H2 o posterior. En Windows 10, ve al [camino B](#b-sin-docker).

### A.1 Activar WSL 2

En PowerShell **como administrador**:

```powershell
wsl --install
```

Reinicia el equipo cuando lo pida.

### A.2 Instalar Docker Desktop

```powershell
winget install --id Docker.DockerDesktop -e
```

Ábrelo una vez, acepta las condiciones y comprueba en *Settings → General* que está marcado **Use the WSL 2 based engine**. Espera a que el icono de la ballena diga *Engine running*.

Comprueba en PowerShell: `docker compose version`.

### A.3 Arrancar

```powershell
docker compose up --build
```

La primera vez tarda unos minutos. Cuando veas `Starting development server at http://0.0.0.0:8000/`, abre <http://localhost:8000>.

### A.4 Administrador y pruebas

En otra ventana de PowerShell, dentro de la carpeta del proyecto:

```powershell
docker compose exec web python manage.py createsuperuser
docker compose exec web pytest
```

Las pruebas de accesibilidad en navegador (`pytest -m e2e`) se ejecutan con el camino B o en GitHub Actions.

### A.5 Parar

`Ctrl+C` y `docker compose down` (`docker compose down -v` borra también la base de datos).

> **Rendimiento:** si la recarga automática va lenta, clona el repositorio dentro de WSL (`\\wsl$\Ubuntu\home\<usuario>\`) y sigue la [guía de Ubuntu](ubuntu.md) desde una terminal de WSL. Docker Desktop funciona igual desde ahí.

---

## B. Sin Docker

### B.1 Python 3.12

```powershell
winget install --id Python.Python.3.12 -e
```

O el instalador de <https://www.python.org/downloads/windows/>, marcando **Add python.exe to PATH**. Comprueba con `py -3.12 --version`.

### B.2 PostgreSQL 16

```powershell
winget install --id PostgreSQL.PostgreSQL.16 -e
```

O el instalador de EDB (<https://www.postgresql.org/download/windows/>). Durante la instalación:

- Apunta la contraseña que pongas al usuario `postgres`.
- Deja el puerto en **5432**.
- Stack Builder no hace falta.

Crea el usuario y la base de datos del proyecto con **SQL Shell (psql)** (está en el menú Inicio; pulsa Intro en todo y escribe la contraseña de `postgres`):

```sql
CREATE ROLE despega LOGIN PASSWORD 'despega' CREATEDB;
CREATE DATABASE despega OWNER despega;
\q
```

### B.3 Entorno virtual y dependencias

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements\dev.txt
```

Si PowerShell responde que *la ejecución de scripts está deshabilitada*, ejecuta una vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Edita `.env` y cambia **una línea**:

```text
POSTGRES_HOST=localhost
```

### B.4 Base de datos y arranque

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre <http://localhost:8000>.

### B.5 Pruebas

```powershell
pytest
playwright install chromium     # solo la primera vez
pytest -m e2e                   # accesibilidad: axe + sin scroll a 360×640, 1280×800, 1366×768
```

Con Google Chrome ya instalado puedes saltarte `playwright install` y usar `pytest -m e2e --browser-channel chrome`.

Lighthouse (opcional; necesita Node.js: `winget install OpenJS.NodeJS.LTS`):

```powershell
npx lighthouse http://localhost:8000 --only-categories=accessibility --view
```

---

## Último paso (los dos caminos): pre-commit

```powershell
# Con el camino B ya está en el entorno virtual. Con el A:
py -3.12 -m pip install --user pre-commit

pre-commit install
```

---

## Problemas frecuentes

| Síntoma | Solución |
| --- | --- |
| El instalador de Docker Desktop dice que tu versión de Windows no es compatible | Usa el camino B. Docker Desktop pide Windows 11 23H2 o posterior. |
| `sh: 1: set: Illegal option -` o `exec format error` al arrancar `web` | `docker/entrypoint.sh` tiene finales CRLF. `git config --global core.autocrlf input`, borra la carpeta y vuelve a clonar. |
| `docker: error during connect` / `Cannot connect to the Docker daemon` | Docker Desktop no está abierto o sigue arrancando. |
| `WSL 2 installation is incomplete` | Ejecuta `wsl --update` como administrador y reinicia. |
| `py` no se reconoce | Cierra y abre PowerShell tras instalar Python, o reinstala marcando *Add to PATH*. |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `pg_config executable not found` al instalar dependencias | Estás en otra versión de Python. Usa `py -3.12` al crear el entorno virtual (`psycopg[binary]` trae todo lo necesario para 3.12). |
| `connection refused` a PostgreSQL (camino B) | `POSTGRES_HOST` sigue en `db`, o el servicio *postgresql-x64-16* está parado (Servicios de Windows). |
| `port is already allocated` en el 5432 o el 8000 | Tienes PostgreSQL nativo o otro servidor ocupando el puerto. Para el servicio o usa otro puerto. |
