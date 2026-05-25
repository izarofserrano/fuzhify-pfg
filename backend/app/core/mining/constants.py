import numpy as np

# ── Umbrales del pipeline de minería ─────────────────────────────────────────
MIN_SOPORTE         = 0.005
MIN_CONFIANZA       = 0.50
MAX_PROF            = 3
K_BEAM              = 10
TOP_POR_CONSECUENTE = 10

# Niveles de lift con sus etiquetas para el selector de la interfaz.
# Clave = valor numérico, valor = etiqueta legible.
LIFT_MINIMO = {
    1.0: "Incluir todas",
    1.5: "Algo sorprendentes",
    2.0: "Sorprendentes",
    3.0: "Muy sorprendentes",
}

# ── Meses por estación (para validación semántica de reglas) ─────────────────
MESES_POR_ESTACION = {
    "t_Invierno":  {"t_Dic", "t_Ene", "t_Feb"},
    "t_Primavera": {"t_Marz", "t_Abr", "t_May"},
    "t_Verano":    {"t_Jun", "t_Jul", "t_Ago"},
    "t_Otonio":    {"t_Sep", "t_Oct", "t_Nov"},
}
