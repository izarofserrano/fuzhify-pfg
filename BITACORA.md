# Bitácora Fuzhify

## 2026-05-25 — Fases 0, 1 y 2
- Setup completo, docker compose levanta limpio.
- Fase 1 (src01 → core/fuzzy): paridad verde con 3 datasets.
- Fase 2 (src02 → core/mining): paridad verde con 3 datasets.
- Pendiente: hacer commits de las 3 fases.

## 2026-05-25 (tarde) — Fase 3 intento 1: fallido
- Sesión de Claude Code cortada por error de servidor a mitad de pipeline.py.
- Archivos escritos antes del corte: constants.py, templates.py,
  detection.py, verbalize.py (4 de 6 archivos).
- Diagnóstico: archivos parciales íntegros (verificado manualmente con
  ast.parse y revisión de imports).
- Decisión: continuar (camino A) en vez de regenerar, mejorando el
  prompt con validación AST por archivo y check de import final para
  evitar repetición del problema.

  ## Decisión de diseño — Plantillas del informe NLG
Decidido módulo genérico en lugar de paridad bit-a-bit con el notebook.
Razón: el abstract del TFG promete "infraestructura de dominio independiente";
los hardcodes del notebook ("Sensor 3600", "Niveles de tráfico", "Ocupación
de la vía") contradicen esa promesa. Test de paridad ajustado para verificar
equivalencia semántica (mismas reglas, mismos párrafos, mismo orden) en lugar
de paridad textual estricta.

## Auditoría de tests de paridad (post-fase 5 interrumpida)
Hallazgos:
- Fase 1 (fuzzy): test correcto, requiere ejecución manual por dataset.
- Fase 2 (mining): test correcto y autocontenido (3 datasets parametrizados).
- Fase 3 (NLG): test con modo "strict=False" para Madrid que solo verifica
  presencia de strings genéricas. INVÁLIDO como test de regresión. Causa
  raíz: el módulo es genérico (decisión consciente, Historia B) pero las
  referencias eran del notebook con hardcodes. Claude Code optó por
  relajar el test en vez de regenerar las referencias.
- Fase 4 (global): test no existe. Módulo no verificado.
Acción correctiva: regenerar referencias con el módulo nuevo, test estricto
contra esas, e implementar test de fase 4 desde cero.

## 2026-05-26 — Auditoría completa y cierre de fases 1+2
Bugs encontrados y resueltos:
1. Python 3.14: dtype str != object → fix is_string_dtype()
2. holidays no en requirements → t_Festivo=0 → eliminada → fallo paridad
Resultado: fase 1 (3/3) y fase 2 (3/3) certificadas con paridad real.
Siguiente: rediseñar test fase 3 con referencias v2 (módulo genérico).

## 2026-05-26 — Auditoría completa + cierre de fases 1-4
Todos los módulos core certificados con tests de paridad reales:
- Fase 1 (fuzzy):  3/3 passed — 2 bugs de entorno encontrados y resueltos
  (Python 3.14 dtype, holidays no instalada)
- Fase 2 (mining): 3/3 passed — test autocontenido, limpio desde el inicio
- Fase 3 (nlg):    3/3 passed — test trampa detectado y reescrito,
  referencias regeneradas con módulo genérico (Historia B)
- Fase 4 (global): 1/1 passed — referencia regenerada con inputs correctos
  (Madrid 2 sensores, no Delhi)
Siguiente sesión: fase 5 (Alembic) y fase 6 (endpoints FastAPI).

## 2026-05-26 — Fase 5 completada
- Alembic configurado con async engine.
- Nota operacional: alembic revision --autogenerate y upgrade head
  deben ejecutarse DENTRO del contenedor (docker compose exec backend)
  porque el hostname 'postgres' solo resuelve desde la red Docker,
  no desde el host Windows.
- Tabla jobs creada en PostgreSQL con 16 columnas, JSONB, UUID, timestamps con tz.



## 2026-05-26 — Fase 6: endpoints FastAPI

### Lo que se hizo
- Creados: pipeline_service.py, api/routes/jobs.py, api/routes/health.py
- Actualizado: main.py con routers + CORS (solo localhost:5173)
- Flujo de 2 pasos implementado: POST /detect-metric → POST /jobs/{id}/run

### Bugs encontrados y resueltos

**Bug 1 — MissingGreenlet en serialización Pydantic**
Causa: JobStatus.model_validate(job) accedía a atributos lazy del
objeto SQLAlchemy fuera de la sesión async. Pydantic serializa en el
momento del return, que puede ocurrir después del commit.
Fix: función helper _job_to_dict(job) que materializa todos los campos
a dict Python puro DENTRO de la sesión, antes de cerrarla.
Aplicado en: run_job, get_job, list_jobs.

**Bug 2 — MissingGreenlet en BackgroundTask**
Causa: ejecutar_pipeline usaba una sola sesión async para todo el
pipeline (fuzzy → mining → nlg). asyncio.to_thread() interrumpe el
contexto async y la sesión queda inválida para las queries siguientes.
Fix: patrón _actualizar_job(job_id, **campos) — cada actualización de
estado abre y cierra su propia sesión independiente. Las operaciones
CPU-bound (pandas) van a asyncio.to_thread() sin tocar la BD.
El BackgroundTask se lanza con asyncio.create_task() en vez de
background_tasks.add_task() para preservar el event loop de uvicorn.

### Decisión de arquitectura relevante para defensa
"Las operaciones CPU-bound del pipeline (fuzzificación, minería,
NLG) se delegan a un thread pool mediante asyncio.to_thread() para
no bloquear el event loop de uvicorn. Cada actualización de estado
en BD abre su propia sesión async autocontenida para evitar el error
MissingGreenlet de SQLAlchemy async, que ocurre cuando se intenta
usar una sesión fuera del contexto greenlet donde fue creada."

### Pendiente
- Test end-to-end completo (detect-metric → run → polling → resultados)
- Commit de fase 6 (después de verificar que el pipeline completa)

## 2026-05-26 — Fase 6 completada

Bugs encontrados y resueltos (3 en total):

1. MissingGreenlet en serialización Pydantic
   Fix: _job_to_dict() materializa atributos dentro de la sesión.

2. MissingGreenlet en BackgroundTask
   Fix: NullPool en engine + background_tasks.add_task(asyncio.run, ...)
   + sesiones async autocontenidas en pipeline_service.py.

3. MissingGreenlet en run_job tras commit
   Fix: await session.refresh(job) después del commit, antes de
   _job_to_dict(). Fuerza recarga dentro del contexto async antes
   de que SQLAlchemy intente lazy-load fuera de él.

Decisión clave para defensa:
"asyncpg solo puede operar dentro de contextos greenlet gestionados
por SQLAlchemy. Cualquier acceso a atributos ORM fuera de ese contexto
lanza MissingGreenlet. La solución es NullPool (sin estado compartido
entre conexiones) + sesiones autocontenidas por operación + refresh
explícito antes de leer atributos post-commit."

Test end-to-end manual verificado:
detect-metric → run → completado en 2.5 min → 33 reglas → informe MD.