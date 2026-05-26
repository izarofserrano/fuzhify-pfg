# Fuzhify

Sistema de generación automática de resúmenes lingüísticos sobre series temporales. A partir de un CSV con medidas de un sensor, el pipeline aplica lógica difusa para codificar el tiempo y la métrica, extrae reglas de asociación mediante búsqueda en haz y produce un informe técnico en Markdown con lenguaje natural estructurado.

## Pipeline

```
CSV de entrada
     │
     ▼
┌──────────────────────────────────────────────┐
│  Paso 1 – POST /api/v1/detect-metric         │
│  detecta columna temporal y métricas         │
│  candidatas; crea job «esperando_metrica»    │
└──────────────────┬───────────────────────────┘
                   │  usuario confirma métrica en el modal
                   ▼
┌──────────────────────────────────────────────┐
│  Paso 2 – POST /api/v1/jobs/{id}/run         │
│  confirma métrica → lanza BackgroundTask     │
└──────────────────┬───────────────────────────┘
                   │
     ┌─────────────▼──────────────────────────────┐
     │  asyncio.to_thread  (CPU-bound)            │
     │                                            │
     │  Fase 1  fuzzificación    →  fuzzy.csv     │
     │    │                                       │
     │  Fase 2  minería de reglas →  reglas.csv   │
     │    │                                       │
     │  Fase 3  NLG              →  informe.md    │
     └────────────────────────────────────────────┘
                   │
     Frontend polling  GET /api/v1/jobs/{id}
     hasta  estado = «completado»
```

## Requisitos

- Docker Desktop >= 24
- Docker Compose >= 2.24

## Levantar el proyecto

```bash
# 1. Variables de entorno (solo la primera vez)
cp backend/.env.example .env

# 2. Construir e iniciar los tres servicios
docker compose up --build
```

| Servicio   | URL                         |
|------------|-----------------------------|
| Frontend   | http://localhost:5173       |
| Backend    | http://localhost:8001       |
| API docs   | http://localhost:8001/docs  |
| PostgreSQL | localhost:5432              |

## Correr los tests

```bash
docker compose exec backend pytest
```

Un módulo concreto con salida detallada:

```bash
docker compose exec backend pytest tests/test_paridad_fuzzy.py -v
```

## Variables de entorno

Fichero: `.env` en la raíz del repo (copiar desde `backend/.env.example`).

| Variable            | Descripción                        | Valor por defecto |
|---------------------|------------------------------------|-------------------|
| `POSTGRES_USER`     | Usuario de PostgreSQL              | `fuzhify`         |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL           | `fuzhify`         |
| `POSTGRES_DB`       | Nombre de la base de datos         | `fuzhify`         |
| `DATABASE_URL`      | URL de conexión asyncpg (derivada) | *(construida por compose)* |

## Cargar datos de ejemplo

Coloca CSVs de prueba en `data/raw/` y ejecuta:

```bash
bash seed/cargar_ejemplos.sh
```

Los archivos se copian a `data/` para subirlos desde la interfaz o via API.

## Parar los servicios

```bash
docker compose down        # para los contenedores
docker compose down -v     # elimina también el volumen de PostgreSQL
```

## Estructura del proyecto

```
fuzhify-pfg/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # Endpoints FastAPI (health, jobs)
│   │   ├── core/
│   │   │   ├── fuzzy/         # Fase 1 – fuzzificación
│   │   │   ├── mining/        # Fase 2 – minería de reglas (beam search)
│   │   │   ├── nlg/           # Fase 3 – generación de lenguaje natural
│   │   │   └── global_report/ # Fase 4 – informe multi-sensor
│   │   ├── models/            # ORM SQLAlchemy (tabla jobs)
│   │   ├── schemas/           # Validación Pydantic
│   │   └── services/          # Orquestación del pipeline
│   ├── data/jobs/             # Archivos por job (generado en runtime)
│   ├── tests/                 # Tests de paridad con los notebooks
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/             # Home, JobStatus, Informe, Reglas, Comparador
│   │   ├── components/        # MetricaModal, ProgressPipeline
│   │   └── stores/            # Estado Pinia (jobs)
│   └── Dockerfile
├── notebooks/                 # Implementaciones de referencia (src01–src04)
├── data/
│   └── raw/                   # CSVs de prueba (no versionados)
├── seed/
│   └── cargar_ejemplos.sh     # Copia data/raw/*.csv → data/
├── docker-compose.yml
├── docker-compose.override.yml.example
├── ARQUITECTURA.md
└── .env                       # No versionado — copiar de backend/.env.example
```

## Deuda técnica conocida

Los `print()` listados a continuación están en módulos del pipeline que en producción corren dentro del servidor. Deberían convertirse a `logger.debug()` pero no afectan al funcionamiento.

**`core/fuzzy/pipeline.py`** — L173, L177, L189, L197, L201-202, L207, L212, L214-215, L217, L236
Trazas de detección de `var_tiempo` / `var_metrica` y fallback LLM.

**`core/fuzzy/heuristic.py`** — L77, L81, L84, L137, L146-147, L149, L152, L183, L202-203, L206, L215, L224, L231, L236
Trazas del módulo heurístico (detección de columna temporal y llamadas al LLM).

**`core/fuzzy/blocks.py`** — L162, L165, L469
Avisos sobre la librería `holidays` y columnas constantes eliminadas.

**`core/nlg/pipeline.py`** — L583
Recuento de reglas eliminadas por combinación inválida.

> Los `print()` en `*/run.py` son **intencionales**: son scripts CLI independientes y su salida es el feedback de progreso al usuario.
