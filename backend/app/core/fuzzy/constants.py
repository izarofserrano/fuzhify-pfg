# Constantes del pipeline de fuzzificación (src01).
# NO modificar valores: están calibrados para los datasets de referencia.

# ── Tolerancia por defecto ────────────────────────────────────────────────────
TOLERANCIA = 0.2

# ── Tolerancias específicas por bloque temporal ───────────────────────────────
TOL_ANIOS      = None
TOL_MESES      = None
TOL_SEMANAS    = 0.05
TOL_HORAS      = 0.5
TOL_QUINCENAS  = None
TOL_ESTACIONES = None
TOL_ABSOLUTAS  = None

# ── Muestras mínimas en la rampa ──────────────────────────────────────────────
N_MUESTRAS_RAMPA = 3

# ── LLM fallback ─────────────────────────────────────────────────────────────
USAR_LLM_FALLBACK = True
PROVEEDOR_LLM     = "gemini"

_MODELO_LLM = {
    "gemini":    "gemini-2.5-flash",
    "anthropic": "claude-opus-4-5",
    "openai":    "gpt-4o",
    "ninguno":   None,
}

# ── Festivos ──────────────────────────────────────────────────────────────────
PAIS_FESTIVOS   = "ES"
SUBDIV_FESTIVOS = "MD"

# ── Nombres de meses (orden y grafía verbatim del notebook) ──────────────────
NOMBRES_MESES = ["Ene", "Feb", "Marz", "Abr", "May", "Jun",
                 "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# ── Sets de clasificación semántica de columnas ───────────────────────────────
_NO_METRICA = {
    'id', 'codigo', 'code', 'cod', 'clave', 'key',
    'nombre', 'name', 'descripcion', 'description', 'label', 'tag',
    'utm', 'lon', 'lat', 'longitud', 'latitud', 'coordenada',
    'coord', 'norte', 'este', 'x', 'y', 'z',
    'distrito', 'zona', 'area', 'region', 'municipio', 'ciudad',
    'sensor', 'estacion', 'punto', 'ubicacion', 'location',
    'tipo', 'type', 'categoria', 'category', 'clase', 'class',
    'flag', 'estado', 'status', 'activo', 'active',
}

_METRICA_POSITIVA = {
    'intensidad', 'ocupacion', 'flujo', 'velocidad', 'volumen', 'caudal',
    'temperatura', 'presion', 'humedad', 'concentracion', 'nivel',
    'consumo', 'potencia', 'energia', 'demanda', 'produccion',
    'ventas', 'precio', 'importe', 'valor', 'medida', 'lectura',
    'indice', 'tasa', 'ratio', 'porcentaje', 'trafico', 'carga',
    'uso', 'rendimiento', 'eficiencia',
}
