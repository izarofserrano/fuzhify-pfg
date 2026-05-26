# Arquitectura de Fuzhify

Documento de referencia para la defensa del TFG. Describe el flujo
completo del sistema y las decisiones de diseño más relevantes.

---

## Visión general

```
┌─────────┐    HTTP     ┌──────────────────────┐    asyncpg    ┌──────────────┐
│ Vue 3   │◄──────────►│ FastAPI (uvicorn)     │◄────────────►│ PostgreSQL   │
│ Vite    │            │                      │               │ tabla: jobs  │
│ Pinia   │            │  core/fuzzy           │               └──────────────┘
└─────────┘            │  core/mining          │
localhost:5173         │  core/nlg             │    filesystem
                       │  core/global_report   │◄────────────►  data/jobs/
                       └──────────────────────┘                {id}/entrada.csv
                       localhost:8001                           {id}/fuzzy.csv
                                                               {id}/reglas.csv
                                                               {id}/informe.md
```

---

## Flujo de análisis (diagrama de secuencia)

### PASO 1 — Detección de métrica (`POST /api/v1/detect-metric`)

```
Usuario          Frontend            Backend                     BD
  │                  │                   │                        │
  │  sube CSV        │                   │                        │
  │─────────────────►│                   │                        │
  │                  │  POST /detect-metric                       │
  │                  │   (multipart: csv + parámetros)            │
  │                  │──────────────────►│                        │
  │                  │                   │                        │
  │                  │                   │  detectar_metricas_    │
  │                  │                   │  candidatas(df)        │
  │                  │                   │  [heurística + LLM     │
  │                  │                   │   opcional]            │
  │                  │                   │                        │
  │                  │                   │  INSERT Job            │
  │                  │                   │  estado: esperando_    │
  │                  │                   │  metrica               │
  │                  │                   │───────────────────────►│
  │                  │                   │                        │
  │                  │  {job_id,         │                        │
  │                  │   var_tiempo,     │                        │
  │                  │   candidatas[],   │                        │
  │                  │   granularidad_s} │                        │
  │                  │◄──────────────────│                        │
  │                  │                   │                        │
  │  Modal con       │                   │                        │
  │  métricas        │                   │                        │
  │◄─────────────────│                   │                        │
  │                  │                   │                        │
  │  selecciona      │                   │                        │
  │  métrica         │                   │                        │
  │─────────────────►│                   │                        │
```

**Resultado**: job creado en BD, CSV guardado en `data/jobs/{job_id}/entrada.csv`.

---

### PASO 2 — Confirmar métrica y lanzar pipeline (`POST /api/v1/jobs/{id}/run`)

```
Usuario          Frontend            Backend                     BD            Worker
  │                  │                   │                        │               │
  │                  │  POST /jobs/{id}/run                       │               │
  │                  │   {metrica_seleccionada,                   │               │
  │                  │    parametros}    │                        │               │
  │                  │──────────────────►│                        │               │
  │                  │                   │  valida candidatas     │               │
  │                  │                   │                        │               │
  │                  │                   │  UPDATE Job            │               │
  │                  │                   │  estado: pendiente     │               │
  │                  │                   │───────────────────────►│               │
  │                  │                   │                        │               │
  │                  │                   │  asyncio.create_task(  │               │
  │                  │                   │    ejecutar_pipeline)  │               │
  │                  │                   │───────────────────────────────────────►│
  │                  │                   │                        │               │
  │                  │  202 Accepted     │                        │               │
  │                  │  {estado:         │                        │               │
  │                  │   pendiente}      │                        │               │
  │                  │◄──────────────────│                        │               │
  │◄─────────────────│                   │                        │               │
```

---

### PASO 2 (continuación) — Ejecución del pipeline (BackgroundTask)

```
                                                                  BD            Worker
                                                                   │               │
                                                                   │  UPDATE fase: │
                                                                   │  fuzzificacion│
                                                                   │◄──────────────│
                                                                   │               │
                                         ┌─────────────────────────────────────────┤
                                         │  Fase 1 – Fuzzificación                 │
                                         │  asyncio.to_thread(_fuzzificar)         │
                                         │                                         │
                                         │  pd.read_csv(entrada.csv)               │
                                         │  FuzzyConfig(var_metrica, pais, subdiv) │
                                         │  fuzzificar(df, cfg)                    │
                                         │   ├── detecta var_tiempo (4 estrategias)│
                                         │   ├── calcula granularidad (mediana)    │
                                         │   ├── genera t_* (tiempo difuso)        │
                                         │   └── genera v_* (nivel de métrica)     │
                                         │  → escribe fuzzy.csv                    │
                                         └─────────────────────────────────────────┤
                                                                   │               │
                                                                   │  UPDATE fase: │
                                                                   │  mineria      │
                                                                   │◄──────────────│
                                                                   │               │
                                         ┌─────────────────────────────────────────┤
                                         │  Fase 2 – Minería de reglas             │
                                         │  asyncio.to_thread(_minar)              │
                                         │                                         │
                                         │  MinerConfig(min_soporte, min_         │
                                         │    confianza, lift_minimo, …)           │
                                         │  minar_reglas(df_fuzzy, cfg)            │
                                         │   ├── construye grupos semánticos       │
                                         │   ├── beam_search_reglas()              │
                                         │   │    profundidad 1..MAX_PROF          │
                                         │   │    K_BEAM candidatos por nivel      │
                                         │   └── filtra redundantes               │
                                         │  → escribe reglas.csv                  │
                                         └─────────────────────────────────────────┤
                                                                   │               │
                                                                   │  UPDATE fase: │
                                                                   │  nlg          │
                                                                   │◄──────────────│
                                                                   │               │
                                         ┌─────────────────────────────────────────┤
                                         │  Fase 3 – Generación de lenguaje        │
                                         │  asyncio.to_thread(_generar)            │
                                         │                                         │
                                         │  NLGConfig(nombre_dataset, metrica)     │
                                         │  generar_informe(df_reglas, df_fuzzy)   │
                                         │   ├── detecta patrones horarios/        │
                                         │   │   estacionales                      │
                                         │   ├── verbaliza antecedentes            │
                                         │   ├── párrafos coloquiales por franja   │
                                         │   └── secciones técnicas + apéndice    │
                                         │  → escribe informe.md                  │
                                         └─────────────────────────────────────────┤
                                                                   │               │
                                                                   │  UPDATE       │
                                                                   │  estado:      │
                                                                   │  completado   │
                                                                   │◄──────────────│
```

---

### PASO 3 — Polling del frontend y descarga de resultados

```
Usuario          Frontend            Backend                     BD
  │                  │                   │                        │
  │                  │  GET /jobs/{id}   │  [cada ~2 s]           │
  │                  │──────────────────►│                        │
  │                  │                   │  SELECT job            │
  │                  │                   │───────────────────────►│
  │                  │                   │◄───────────────────────│
  │                  │  {estado,         │                        │
  │                  │   fase_actual}    │                        │
  │                  │◄──────────────────│                        │
  │  ProgressPipeline│                   │                        │
  │  actualizado     │                   │                        │
  │◄─────────────────│                   │                        │
  │                  │   [hasta estado = completado]              │
  │                  │                   │                        │
  │  clic "Ver informe"                  │                        │
  │─────────────────►│                   │                        │
  │                  │  GET /jobs/{id}/informe                    │
  │                  │──────────────────►│  lee informe.md        │
  │                  │◄── text/markdown──│                        │
  │                  │                   │                        │
  │                  │  GET /jobs/{id}/informe.pdf                │
  │                  │──────────────────►│  WeasyPrint → PDF      │
  │                  │◄── application/pdf│                        │
  │  abre/descarga   │                   │                        │
  │◄─────────────────│                   │                        │
```

---

## Estados del job

```
upload CSV
    │
    ▼
esperando_metrica ──► [usuario confirma métrica en modal]
    │
    ▼
pendiente ──► BackgroundTask lanzado
    │
    ▼
fuzzificacion
    │
    ▼
mineria
    │
    ▼
nlg
    │
    ▼
completado
    │
    (o en cualquier fase anterior)
    ▼
error  (error_mensaje disponible vía GET /jobs/{id})
```

---

## Archivos generados por job

```
backend/data/jobs/{job_id}/
├── entrada.csv    CSV original subido por el usuario
├── fuzzy.csv      Salida de Fase 1: columnas t_* y v_* (lógica difusa)
├── reglas.csv     Salida de Fase 2: antecedente, consecuente, soporte, confianza, lift
└── informe.md     Salida de Fase 3: informe en Markdown (~2 000–3 000 líneas)
```

---

## Decisiones de arquitectura

### 1. BackgroundTasks vs Celery

**Contexto:** El pipeline (fuzzificación + minería + NLG) tarda entre
30 segundos y varios minutos según el tamaño del CSV. La API no puede
bloquear el hilo del request durante ese tiempo. Había que elegir entre
un sistema de colas externo (Celery + Redis/RabbitMQ) y la opción
nativa de FastAPI.

**Decisión:** Se usa `asyncio.create_task()` (equivalente a
`BackgroundTasks` pero en el event loop de uvicorn) para ejecutar el
pipeline de forma asíncrona dentro del mismo proceso.

**Por qué:** El TFG tiene un único servidor sin necesidad de workers
distribuidos. Celery añadiría dos contenedores extra (broker + worker),
complejidad de despliegue y un protocolo de serialización de tareas.
Para un pipeline de un solo usuario concurrente, la solución nativa
es suficiente y mantiene la arquitectura simple y explicable en la
defensa.

---

### 2. NullPool en el motor async de SQLAlchemy

**Contexto:** FastAPI con asyncpg usa un motor `create_async_engine()`
con pool de conexiones. Cuando el pipeline corre en un `BackgroundTask`
lanzado con `asyncio.create_task()`, el contexto del event loop cambia
y las conexiones del pool pueden quedar asociadas al contexto incorrecto,
lanzando `MissingGreenlet`.

**Decisión:** El motor se crea con `poolclass=NullPool`, lo que
desactiva el pool de conexiones: cada operación abre y cierra su propia
conexión.

**Por qué:** `NullPool` elimina el estado compartido entre conexiones.
El coste (abrir una conexión TCP por operación de BD) es insignificante
para el patrón de uso del sistema (pocas escrituras por job). A cambio,
desaparece completamente la clase de errores `MissingGreenlet` asociada
al pool.

---

### 3. Sesiones async autocontenidas por operación

**Contexto:** El pipeline ejecuta tres fases CPU-bound en
`asyncio.to_thread()`. Cada fase necesita actualizar el estado del job
en PostgreSQL. Una sesión SQLAlchemy abierta antes del `to_thread()`
no puede usarse después porque el contexto greenlet ya no es el mismo.

**Decisión:** Cada actualización de estado llama a la función helper
`_actualizar_job(job_id, **campos)`, que abre una sesión async nueva,
hace el UPDATE y la cierra, todo dentro de un mismo `async with`.

**Por qué:** Una sesión SQLAlchemy async está ligada al contexto
greenlet donde fue creada. Al cruzar un `to_thread()`, ese contexto
cambia. La sesión autocontenida garantiza que apertura, uso y cierre
ocurren siempre en el mismo contexto, evitando `MissingGreenlet` sin
importar desde qué hilo se llame.

---

### 4. Módulo NLG genérico frente a paridad textual estricta (Historia B)

**Contexto:** Los notebooks de referencia (src03) contienen hardcodes
específicos del dataset de prueba: nombres de sensores concretos
("Sensor 3600"), etiquetas de dominio ("Niveles de tráfico",
"Ocupación de la vía"). Portarlos verbatim produciría un módulo que
solo funciona con ese dataset, contradiciendo el abstract del TFG,
que promete "infraestructura de dominio independiente".

**Decisión:** El módulo `core/nlg/` se implementa como infraestructura
genérica. Las plantillas de frases y la escala adverbial (Historia A)
se portan literalmente; los textos de dominio específico se eliminan.
Los tests de paridad verifican equivalencia semántica (mismas reglas,
mismo orden, mismo estilo lingüístico) en lugar de igualdad textual
estricta.

**Por qué:** El TFG defiende la generalidad del sistema. Un módulo que
solo funciona con un dataset de tráfico de Madrid no cumple ese
objetivo. La paridad semántica es el criterio correcto: lo que importa
es que las mismas reglas produzcan el mismo tipo de verbalización, no
que el texto sea idéntico al notebook con sus particularidades de
dominio.

---

### 5. `asyncio.to_thread()` para operaciones CPU-bound

**Contexto:** Las tres fases del pipeline (fuzzificación, minería y NLG)
hacen un uso intensivo de pandas y numpy. Ejecutarlas directamente en
una `async def` bloquearía el event loop de uvicorn, impidiendo que el
servidor respondiera a otras peticiones (incluyendo los polls de estado
del frontend) mientras el pipeline está en curso.

**Decisión:** Cada fase se envuelve en `asyncio.to_thread(función_síncrona,
*args)`, delegando la ejecución al thread pool del sistema operativo.

**Por qué:** Python tiene el GIL, pero `asyncio.to_thread()` libera el
event loop mientras el hilo trabaja. El event loop puede seguir
atendiendo peticiones HTTP (polls, healthchecks) sin esperar a que
pandas termine. Es la solución canónica de FastAPI/asyncio para
operaciones CPU-bound sin introducir multiprocessing ni un sistema de
colas externo.

---

### 6. Detección automática de `var_tiempo` y `var_metrica`

**Contexto:** Los notebooks de referencia hardcodeaban `var_tiempo="fecha"`
y `var_metrica="intensidad"`. Un sistema genérico no puede asumir estos
nombres: cada cliente puede tener columnas con nombres distintos.

**Decisión:** La función `_detectar_var_tiempo()` aplica cuatro
estrategias en orden (datetime directo, par fecha+hora, unix timestamp,
fallback por formato). La función `_heuristica()` selecciona
`var_metrica` por distribución estadística de las columnas numéricas.
Ambas tienen fallback opcional a un LLM (Gemini/Anthropic/OpenAI).

**Por qué:** El sistema debe funcionar con cualquier CSV de series
temporales sin intervención manual. La detección automática es el
contrato principal con el usuario: "sube tu CSV y el sistema lo
entiende". El LLM como fallback permite resolver casos ambiguos sin
bloquear el flujo.
