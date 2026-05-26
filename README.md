# Fuzhify

Sistema de generación automática de resúmenes en lenguaje natural
sobre series temporales mediante lógica difusa y minería de reglas
de asociación. Proyecto Fin de Grado — Grado en Ingeniería
Informática, Universidad de Deusto.

## Descripción

Fuzhify recibe como entrada un fichero CSV con medidas de un sensor
o contador (tráfico, ocupación, consumo eléctrico…) y produce
automáticamente un informe técnico en lenguaje natural. El usuario
no necesita programar ni configurar umbrales: sube el CSV, elige
qué variable analizar y el sistema hace el resto.

El proceso se divide en tres fases encadenadas. Primero, la
**fuzzificación** (src01) codifica el tiempo y la métrica en variables
lingüísticas difusas: horas del día, franjas horarias, días de la
semana, festivos, estaciones, quincenas, etc. A continuación, la
**minería de reglas** (src02) aplica un algoritmo de búsqueda en haz
para extraer asociaciones del tipo «cuando es tarde por la noche en
laborable, la ocupación suele ser alta». Por último, el módulo de
**generación de lenguaje natural** (src03) agrupa las reglas por patrón
semántico y redacta párrafos en castellano listos para incluir en un
informe técnico o una memoria de TFG.

El sistema también incluye un **comparador** (src04) que recibe varios
análisis completados y genera un informe global que destaca patrones
comunes, anomalías y diferencias entre conjuntos de datos. Toda la
lógica analítica está portada directamente desde notebooks de referencia
(Jupyter) y verificada mediante tests de paridad que garantizan
resultados idénticos.

## Requisitos

- Docker Desktop
- Git

No se necesita Python ni Node.js instalados localmente.
Todo corre dentro de los contenedores.

## Levantar el proyecto en local

```bash
git clone <url-del-repo>
cd fuzhify-pfg

# Copiar variables de entorno
cp backend/.env.example .env
cp frontend/.env.example frontend/.env.local

# Levantar los 3 servicios
docker compose up --build

# En otra terminal, aplicar la migración de base de datos
docker compose exec backend alembic upgrade head
```

La aplicación estará disponible en:
- Frontend: http://localhost:5173
- API: http://localhost:8001/api/v1
- Documentación API: http://localhost:8001/docs

## Correr los tests de paridad

```bash
docker compose exec backend pytest tests/ -v
```

Para un módulo concreto:

```bash
docker compose exec backend pytest tests/test_paridad_fuzzy.py -v
docker compose exec backend pytest tests/test_paridad_mining.py -v
docker compose exec backend pytest tests/test_paridad_nlg.py -v
docker compose exec backend pytest tests/test_paridad_global.py -v
```

## Estructura del proyecto

```
fuzhify-pfg/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── health.py              ← healthcheck
│   │   │   └── jobs.py                ← endpoints de jobs y pipeline
│   │   ├── core/
│   │   │   ├── fuzzy/                 ← Fase 1: fuzzificación (src01)
│   │   │   ├── mining/                ← Fase 2: minería beam search (src02)
│   │   │   ├── nlg/                   ← Fase 3: lenguaje natural (src03)
│   │   │   ├── global_report/         ← Fase 4: informe comparativo (src04)
│   │   │   └── pdf_export/            ← exportación a PDF con WeasyPrint
│   │   ├── models/                    ← ORM SQLAlchemy (tabla jobs)
│   │   ├── schemas/                   ← validación Pydantic
│   │   ├── services/                  ← orquestación del pipeline
│   │   ├── config.py                  ← configuración vía variables de entorno
│   │   ├── db.py                      ← motor async y sesiones SQLAlchemy
│   │   └── main.py                    ← aplicación FastAPI
│   ├── tests/
│   │   ├── test_paridad_fuzzy.py      ← paridad src01 (3 datasets)
│   │   ├── test_paridad_mining.py     ← paridad src02 (3 datasets)
│   │   ├── test_paridad_nlg.py        ← paridad src03 (módulo genérico)
│   │   └── test_paridad_global.py     ← paridad src04
│   ├── alembic/                       ← migraciones de base de datos
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.js              ← cliente Axios con baseURL configurable
│   │   ├── components/
│   │   │   ├── MetricaModal.vue       ← modal de selección de métrica
│   │   │   └── ProgressPipeline.vue   ← barra de progreso por fases
│   │   ├── router/index.js            ← rutas de la SPA
│   │   ├── stores/jobs.js             ← estado global con Pinia
│   │   └── views/                     ← Home, JobStatus, Informe, Reglas, Comparador
│   ├── Dockerfile
│   └── package.json
├── notebooks/                         ← implementaciones de referencia (src01–src04)
├── docker-compose.yml
├── ARQUITECTURA.md                    ← diagramas y decisiones de diseño
└── CONTEXTO.md                        ← guía de desarrollo del TFG
```

## Pipeline de análisis

```
CSV de entrada (sensor)
        │
        ▼
POST /api/v1/detect-metric
  ├── detecta columna temporal (4 estrategias automáticas)
  ├── detecta métricas candidatas (heurística estadística)
  └── crea job  →  estado: esperando_metrica
        │
        │  usuario confirma métrica en el modal
        ▼
POST /api/v1/jobs/{id}/run
  └── lanza BackgroundTask  →  estado: pendiente
        │
        ├──► Fase 1 — Fuzzificación (src01)
        │       columnas t_* (franja, día, mes, festivo…)
        │       columnas v_* (nivel alto/bajo/medio…)
        │       → fuzzy.csv
        │
        ├──► Fase 2 — Minería de reglas (src02)
        │       beam search con poda por confianza
        │       filtra y ordena por lift
        │       → reglas.csv  [antecedente, consecuente, soporte, confianza, lift]
        │
        └──► Fase 3 — Lenguaje natural (src03)
                agrupa reglas por franja horaria y tipo de día
                verbaliza con escala adverbial (lift → adverbio)
                → informe.md

Frontend: polling GET /api/v1/jobs/{id} cada 2 s hasta estado=completado
```

## Stack tecnológico

| Capa           | Tecnología              | Versión  | Función                                      |
|----------------|-------------------------|----------|----------------------------------------------|
| API            | FastAPI + Uvicorn       | latest   | Framework web async + servidor ASGI          |
| ORM            | SQLAlchemy (async)      | latest   | Acceso a BD con asyncpg                      |
| Base de datos  | PostgreSQL              | 16       | Persistencia de jobs y metadatos             |
| Migraciones    | Alembic                 | latest   | Versionado del esquema de BD                 |
| Análisis       | pandas + numpy          | latest   | Procesamiento de series temporales           |
| Festivos       | holidays                | ≥ 0.97   | Detección de festivos por país/subdivisión   |
| PDF            | WeasyPrint + Jinja2     | latest   | Exportación del informe a PDF                |
| Frontend       | Vue 3                   | 3.4.0    | SPA con componentes reactivos                |
| Build          | Vite                    | 5.2.0    | Bundler del frontend                         |
| Estado         | Pinia                   | 3.0.4    | Store reactivo global                        |
| Enrutado       | Vue Router              | 4.6.4    | Navegación en la SPA                         |
| HTTP           | Axios                   | 1.7.0    | Cliente HTTP del frontend                    |
| Infraestructura| Docker Compose          | v2       | Orquestación de tres contenedores            |
| Tests          | pytest                  | latest   | Tests de paridad contra notebooks originales |
