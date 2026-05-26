# Arquitectura de Fuzhify

Documento de referencia para la defensa del PFG. Describe el flujo completo del sistema mediante diagramas de secuencia en texto.

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

## Diagrama de secuencia — flujo completo

### PASO 1: Detección de métrica (`POST /api/v1/detect-metric`)

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

### PASO 2: Confirmar métrica y lanzar pipeline (`POST /api/v1/jobs/{id}/run`)

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
  │                  │                   │  BackgroundTask(       │               │
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

### PASO 2 (continuación): Ejecución del pipeline (BackgroundTask)

```
                                                                  BD            Worker
                                                                   │               │
                                                                   │  UPDATE fase: │
                                                                   │  ejecutando/  │
                                                                   │  fuzzy        │
                                                                   │◄──────────────│
                                                                   │               │
                                         ┌─────────────────────────────────────────┤
                                         │  Fase 1 – Fuzzificación                 │
                                         │  asyncio.to_thread(_fuzzificar)         │
                                         │                                         │
                                         │  pd.read_csv(entrada.csv)               │
                                         │  FuzzyConfig(var_metrica, pais, subdiv) │
                                         │  fuzzificar(df, cfg)                    │
                                         │   ├── detecta var_tiempo                │
                                         │   ├── calcula granularidad              │
                                         │   ├── genera t_* (temporal fuzzy)       │
                                         │   └── genera v_* (nivel de métrica)     │
                                         │  → escribe fuzzy.csv                    │
                                         └─────────────────────────────────────────┤
                                                                   │               │
                                                                   │  UPDATE fase: │
                                                                   │  mining       │
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
                                                                   │  UPDATE        │
                                                                   │  estado:      │
                                                                   │  completado   │
                                                                   │◄──────────────│
```

---

### PASO 3: Polling del frontend

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
  │                  │                   │  [hasta completado]    │
  │                  │                   │                        │
  │                  │  GET /jobs/{id}/informe                    │
  │                  │──────────────────►│  lee informe.md        │
  │                  │◄── text/markdown──│                        │
  │  muestra informe │                   │                        │
  │◄─────────────────│                   │                        │
```

---

## Estados del job

```
upload CSV
    │
    ▼
esperando_metrica ──► [usuario confirma métrica]
    │
    ▼
pendiente ──► BackgroundTask lanzado
    │
    ▼
ejecutando
    │  fase_actual: fuzzy → mining → nlg
    ▼
completado
    │
    (o en cualquier fase)
    ▼
error  (error_mensaje disponible via GET /jobs/{id})
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

## Decisiones de diseño relevantes

| Decisión | Motivo |
|---|---|
| `asyncio.to_thread()` para las fases del pipeline | Las tres fases son CPU-bound (pandas + lógica difusa). Moverlas a un thread evita bloquear el event loop de FastAPI. |
| Cada actualización de BD abre su propia sesión | El contexto async no se puede compartir entre el hilo del request y el hilo del worker. Sesiones autocontenidas evitan `MissingGreenlet`. |
| Detección automática de `var_tiempo` y `var_metrica` | El pipeline no asume nombres de columna; funciona con cualquier CSV de series temporales. LLM como fallback opcional. |
| Thresholds en `constants.py` (inmutables) | Los valores (`MIN_SOPORTE`, `MIN_CONFIANZA`, etc.) están calibrados empíricamente. El usuario puede ajustar `lift_minimo` desde la UI; el resto permanece fijo. |
| Grupos semánticos exclusivos construidos dinámicamente | Las restricciones "hora X no coexiste con hora Y" se derivan de las columnas presentes, no de una lista estática, para generalizar a cualquier granularidad. |
