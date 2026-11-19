# Memorama PvP

Juego de memorama multijugador (jugador contra jugador) en la web. Dos jugadores entran a una sala,
eligen categoría y dificultad, y compiten en tiempo real para encontrar más pares.

Proyecto final de DevOps — ITSON.

## Stack

| Tecnología | Uso |
|---|---|
| Flask + Jinja2 | Rutas y plantillas HTML |
| Flask-SocketIO | Comunicación en tiempo real entre los dos jugadores |
| SQLAlchemy + Flask-Migrate | Modelos y migraciones sobre MySQL |
| MySQL 8.4 | Usuarios, categorías, cartas, salas y partidas |
| Docker / Docker Compose | Contenedores de la app y de MySQL |
| pytest + flake8 | Pruebas unitarias y estilo de código |
| GitHub Actions | CI (pruebas) y CD (despliegue a la VM de Azure) |

## Estructura

```
.
├── main.py                     # App Flask: config, rutas y eventos (una sección por módulo)
├── templates/                  # Plantillas Jinja2 (base.html + páginas)
├── static/
│   ├── css/styles.css          # Estilos globales
│   ├── js/main.js              # JS compartido (cliente Socket.IO cargado en base.html)
│   └── uploads/                # Imágenes subidas (volumen Docker, no se versiona)
├── tests/                      # Pruebas unitarias (pytest)
├── requirements.txt            # Dependencias de producción
├── requirements-dev.txt        # + pytest, pytest-cov, flake8
├── Dockerfile
├── docker-compose.yml          # Desarrollo: app + MySQL
├── docker-compose.prod.yml     # Producción en la VM (imagen de GHCR)
├── .devcontainer/              # Dev Container de VS Code
├── .github/workflows/
│   ├── ci.yml                  # Lint + pruebas + build de imagen
│   └── deploy.yml              # Pruebas -> imagen a GHCR -> deploy en VM -> health check
└── .env.example                # Plantilla de variables de entorno
```

## Correr en local

### Opción 1: Docker Compose (recomendada)

Requiere Docker Desktop.

```powershell
Copy-Item .env.example .env
```

```powershell
docker compose up --build
```

La app queda en http://localhost:8000 y MySQL en `localhost:3307` (se cambia con
`MYSQL_HOST_PORT` en `.env`; dentro de Docker sigue siendo `db:3306`). El código está montado
como volumen, así que los cambios se recargan solos.

### Opción 2: Dev Container

1. Instala la extensión **Dev Containers** en VS Code.
2. Crea el `.env` a partir de `.env.example`.
3. `Ctrl+Shift+P` → **Dev Containers: Reopen in Container**.
4. En la terminal del contenedor: `python main.py`.

### Opción 3: Python directo (sin MySQL)

Sin `DATABASE_URL` la app usa SQLite local, útil para probar rápido.

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\Activate.ps1
```

```powershell
pip install -r requirements-dev.txt
```

```powershell
python main.py
```

## Pruebas

```powershell
pytest
```

```powershell
flake8 .
```

Las pruebas usan SQLite en memoria, así que no necesitan MySQL ni Docker. Cada módulo
agrega su archivo en `tests/` (por ejemplo `tests/test_salas.py`). Los fixtures
`client` y `socket_client` están en `tests/conftest.py`.

## Ramas (GitHub Flow)

| Rama | Uso |
|---|---|
| `main` | Siempre desplegable. Cada merge despliega a la VM. Nadie hace push directo. |
| `feature/<descripcion>` | Una rama por funcionalidad, creada desde `main` (ej. `feature/lista-salas`, `feature/crud-categorias`, `fix/turnos`). |

Flujo para cada funcionalidad:

```powershell
git switch main
```

```powershell
git pull
```

```powershell
git switch -c feature/lista-salas
```

1. Haz commits en tu rama y súbela con `git push -u origin feature/lista-salas`.
2. Abre un Pull Request hacia `main`. El workflow **CI** corre flake8, pytest y el build de la imagen.
3. Cuando el CI está en verde y alguien del equipo aprobó, se hace merge y se borra la rama.
4. El merge a `main` dispara **CD**: las pruebas corren otra vez y, si pasan, se despliega.

Mantén las ramas cortas (una funcionalidad, pocos días) y actualízalas con `main` seguido
(`git pull origin main`) para evitar conflictos grandes.

**Protección de `main`** (*Settings → Branches → Add branch ruleset*, o *Branch protection rule*):

- Requerir Pull Request antes de mergear (mínimo 1 aprobación).
- Requerir que pase el check **Lint y pruebas** y que la rama esté actualizada con `main`.
- Bloquear push directo y force push.

## CI/CD

```
push a feature/* o PR a main ──► CI: flake8 + pytest + build de imagen

merge a main ──► CI (pytest) ──► build y push a ghcr.io ──► deploy por SSH ──► GET /health
                  │ falla                                                    │ falla
                  └──► no se despliega                                       └──► el job queda en rojo
```

Si las pruebas fallan, los jobs de build y deploy no se ejecutan. En cada despliegue la
VM guarda la versión anterior en `~/memorama/.previous_tag`.

### Configuración única de la VM de Azure

La VM actual ya está creada:

| Dato | Valor |
|---|---|
| Suscripción | Azure for Students |
| Grupo de recursos | `rg-memorama` |
| VM | `vm-memorama`, Ubuntu 24.04 **ARM64**, `Standard_B2pts_v2` (2 vCPU, 1 GB RAM + 2 GB swap) |
| Región | Canada Central (la permitida más cercana a México) |
| Usuario SSH | `azureuser` |
| Puertos abiertos | 22 (SSH) y 80 (HTTP) |

Azure for Students solo permite desplegar en `swedencentral`, `belgiumcentral`, `norwayeast`,
`francecentral` y `canadacentral`, y en Canadá solo hay tamaños B pequeños con procesador ARM.
Por eso `deploy.yml` construye la imagen para `linux/amd64` y `linux/arm64`.

Para recrearla desde cero (requiere [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
y una llave `~/.ssh/memorama_azure`):

```bash
az group create --name rg-memorama --location canadacentral
az vm create --resource-group rg-memorama --name vm-memorama --location canadacentral \
  --image Canonical:ubuntu-24_04-lts:server-arm64:latest --size Standard_B2pts_v2 \
  --security-type Standard --admin-username azureuser \
  --ssh-key-values ~/.ssh/memorama_azure.pub --os-disk-size-gb 30 --storage-sku StandardSSD_LRS \
  --public-ip-sku Standard --public-ip-address-allocation static \
  --custom-data deploy/cloud-init.yml
az vm open-port --resource-group rg-memorama --name vm-memorama --port 80 --priority 1010
```

[deploy/cloud-init.yml](deploy/cloud-init.yml) instala Docker, agrega el swap y crea
`~/memorama` en el primer arranque. Después solo falta crear `~/memorama/.env` en la VM
(con `.env.example` como guía y contraseñas distintas a las de desarrollo, `chmod 600`).

Para pausar la VM y no gastar crédito: `az vm deallocate -g rg-memorama -n vm-memorama`
(se reanuda con `az vm start`; la IP es estática y no cambia).

### Configuración en GitHub

En *Settings → Environments* crea el environment **production** con:

| Tipo | Nombre | Valor |
|---|---|---|
| Variable | `VM_HOST` | IP pública de la VM |
| Secret | `VM_USER` | Usuario SSH (ej. `azureuser`) |
| Secret | `VM_SSH_KEY` | Contenido de la llave privada SSH |

La imagen se publica en `ghcr.io/aleishis/examen-final-devops` usando el `GITHUB_TOKEN`
del workflow; no necesitas crear otro token.

## Variables de entorno

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Llave de sesiones de Flask |
| `FLASK_DEBUG` | `1` para modo debug (solo desarrollo) |
| `PORT` | Puerto interno de la app (8000) |
| `MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD` | Credenciales de MySQL |
| `MYSQL_HOST_PORT` | Puerto de MySQL en tu máquina en desarrollo (por defecto 3307) |
| `DATABASE_URL` | Solo fuera de Docker; compose la arma a partir de las variables `MYSQL_*` |

## Notas técnicas

- En producción gunicorn corre con **un solo worker** (`--workers 1 --threads 100`): las
  salas de Socket.IO viven en memoria del proceso. Escalar a varios workers requeriría Redis
  como *message queue*.
- `GET /health` responde `200` si la app y la base de datos están bien, o `503` si la base de
  datos no responde. Lo usan el `HEALTHCHECK` de Docker y el pipeline de despliegue.
