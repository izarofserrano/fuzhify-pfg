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

— dos bugs de entorno encontrados y resueltos en la auditoría de fase 1:

Python 3.14 + pandas: dtype == object falla para columnas string → fix: pd.api.types.is_string_dtype().
holidays no estaba en requirements.txt → t_Festivo siempre 0 → eliminada como constante → fallo de paridad. Fix: pip install holidays + añadir al requirements.
Ambos son bugs de entorno, no de lógica. La lógica del módulo es fiel al notebook.