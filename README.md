# Fuzhify

Sistema de generación automática de resúmenes en lenguaje natural sobre series temporales, basado en lógica difusa y minería de reglas de asociación. Desarrollado como Trabajo de Fin de Grado.

El sistema acepta cualquier CSV con una serie temporal, detecta automáticamente la variable temporal y la métrica de interés, ejecuta un pipeline de tres fases y produce un informe estructurado en Markdown (y PDF) listo para leer.

---

## Pipeline

```
CSV (serie temporal)
       │
       ▼
  Fuzzificación  →  fuzzy.csv      (variables difusas t_* y v_*)
       │
       ▼
  Minería de     →  reglas.csv     (antecedente, consecuente, soporte, confianza, lift)
  reglas (beam)
       │
       ▼
  NLG            →  informe.md     (resumen en lenguaje natural)
                 →  informe.pdf    (versión imprimible)
```

---

## Stack tecnológico

| Capa       | Tecnología                              |
|------------|-----------------------------------------|
| Backend    | Python 3.11 · FastAPI · uvicorn         |
| Base datos | PostgreSQL 16 · SQLAlchemy async        |
| Frontend   | Vue 3 · Vite · Axios                    |
| PDF        | WeasyPrint · matplotlib                 |
| Tests      | Pytest · Coverage.py                    |
| Infra      | Docker · Docker Compose                 |

---

## Requisitos previos

- **Docker Desktop** ≥ 24
- **Docker Compose** ≥ 2.24

No es necesario tener Python, Node ni ninguna otra herramienta instalada en el host.

---

## Puesta en marcha

### Primera vez en un ordenador nuevo

```bash
# 1. Variables de entorno
cp backend/.env.example .env
cp frontend/.env.example frontend/.env.local

# 2. Levantar los tres servicios (build incluido)
docker compose up --build -d

# 3. Aplicar la migración de base de datos
#    IMPORTANTE: debe ejecutarse dentro del contenedor.
#    El hostname "postgres" solo resuelve desde la red Docker.
docker compose exec backend alembic upgrade head
```

### Arranques posteriores

```bash
docker compose up -d

# Solo si hay migraciones nuevas en alembic/versions/:
docker compose exec backend alembic upgrade head
```## Configuración del fallback LLM (opcional)

El sistema detecta automáticamente la columna temporal y la métrica candidata mediante heurística estadística. En casos ambiguos puede apoyarse en un modelo de lenguaje externo. Esta funcionalidad está **desactivada por defecto** y el sistema funciona correctamente sin ella.

Si quieres activarla, edita el fichero `.env`:

```bash
# Activa el fallback LLM (false por defecto)
USAR_LLM_FALLBACK=true

# Proveedor: "gemini", "anthropic" u "openai"
PROVEEDOR_LLM=gemini
```

Según el proveedor elegido, añade la variable de entorno correspondiente:

```bash
# Si usas Gemini
GEMINI_API_KEY=tu_api_key_aqui

# Si usas Anthropic
ANTHROPIC_API_KEY=tu_api_key_aqui

# Si usas OpenAI
OPENAI_API_KEY=tu_api_key_aqui
```

### Dónde obtener cada API key

| Proveedor | URL |
|---|---|
| Gemini | https://aistudio.google.com/app/apikey |
| Anthropic | https://console.anthropic.com/settings/keys |
| OpenAI | https://platform.openai.com/api-keys |

> Solo es necesaria la key del proveedor seleccionado en `PROVEEDOR_LLM`. Si `USAR_LLM_FALLBACK=false`, esta configuración se ignora por completo.

### Servicios disponibles

| Servicio                  | URL                              |
|---------------------------|----------------------------------|
| Frontend                  | http://localhost:5173            |
| Backend (API REST)        | http://localhost:8001            |
| Swagger UI (API docs)     | http://localhost:8001/docs       |
| Healthcheck               | http://localhost:8001/health     |
| PostgreSQL                | localhost:5432                   |

### Parar los servicios

```bash
docker compose down          # para los contenedores, conserva datos
docker compose down -v       # para y borra también el volumen de PostgreSQL
```

---

## Uso del sistema

1. Abre el frontend en http://localhost:5173.
2. **Sube un CSV** con una serie temporal. El sistema detecta automáticamente la columna temporal y propone métricas candidatas.
3. **Selecciona la métrica** a analizar y ajusta los parámetros del pipeline si lo necesitas (umbrales de soporte, confianza, lift, etc.).
4. El pipeline se ejecuta en segundo plano. Una barra de progreso muestra las tres fases en tiempo real.
5. Al terminar, accede al **informe en Markdown**, descárgalo como **PDF** o consulta las **reglas extraídas** en formato tabla.
6. Desde el **Comparador**, selecciona varios análisis completados y genera un **informe global** comparativo.

---

## Estructura del proyecto

```
fuzhify-pfg/
├── backend/
│   ├── app/
│   │   ├── api/routes/       Endpoints FastAPI (jobs, health)
│   │   ├── core/
│   │   │   ├── fuzzy/        Fase 1: fuzzificación (src01)
│   │   │   ├── mining/       Fase 2: beam search (src02)
│   │   │   ├── nlg/          Fase 3: generación de lenguaje (src03)
│   │   │   ├── global_report/ Informe comparativo (src04)
│   │   │   └── pdf_export/   Exportación a PDF (WeasyPrint)
│   │   ├── models/           Modelos SQLAlchemy
│   │   ├── schemas/          Schemas Pydantic
│   │   └── services/         Orquestación del pipeline
│   ├── alembic/              Migraciones de base de datos
│   ├── tests/                Tests de paridad
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/            HomeView, JobStatusView, ComparadorView, …
│   │   ├── components/       ProgressPipeline, MetricaModal, …
│   │   └── api/              Cliente Axios
│   └── Dockerfile
├── notebooks/                Notebooks de referencia (src01–src04)
├── ejemplos/                 CSVs y salidas de ejemplo para tests
├── data/                     Archivos generados por job (ignorado en git)
├── docker-compose.yml
├── CONTEXTO.md               Reglas del proyecto y lógica de negocio
└── ARQUITECTURA.md           Decisiones de diseño y diagramas de secuencia
```

---

## API — Endpoints principales

| Método | Ruta                                | Descripción                                      |
|--------|-------------------------------------|--------------------------------------------------|
| POST   | `/api/v1/detect-metric`             | Sube CSV y detecta métricas candidatas           |
| POST   | `/api/v1/jobs/{id}/run`             | Confirma métrica y lanza el pipeline             |
| GET    | `/api/v1/jobs/{id}`                 | Consulta estado del job (polling)                |
| GET    | `/api/v1/jobs`                      | Lista jobs recientes (filtro por estado)         |
| GET    | `/api/v1/jobs/{id}/informe`         | Descarga el informe en Markdown                  |
| GET    | `/api/v1/jobs/{id}/informe.pdf`     | Genera y descarga el informe en PDF              |
| GET    | `/api/v1/jobs/{id}/reglas`          | Lista las reglas extraídas (paginado)            |
| GET    | `/api/v1/jobs/{id}/descargar/{tipo}`| Descarga archivos del job (entrada/fuzzy/reglas) |
| POST   | `/api/v1/informe-global`            | Genera informe global comparativo                |

La documentación interactiva completa está en http://localhost:8001/docs.

---

## Tests

Los tests verifican la paridad de cada módulo del pipeline respecto a los notebooks de referencia: los mismos datos de entrada deben producir la misma salida, columna a columna.

```bash
# Ejecutar dentro del contenedor del backend
docker compose exec backend python -m pytest tests/ -v
```

---

## Documentación adicional

- **`CONTEXTO.md`** — lógica de negocio, umbrales críticos, reglas de migración y decisiones ya tomadas.
- **`ARQUITECTURA.md`** — diagramas de secuencia del pipeline, máquina de estados del job y razonamiento detrás de cada decisión de arquitectura (BackgroundTasks vs Celery, NullPool, `asyncio.to_thread`, etc.).
