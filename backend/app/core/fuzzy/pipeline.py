"""Orquestador del pipeline de fuzzificación (src01)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from .constants import (
    TOLERANCIA, TOL_ANIOS, TOL_MESES, TOL_SEMANAS, TOL_HORAS,
    TOL_QUINCENAS, TOL_ESTACIONES, TOL_ABSOLUTAS,
    N_MUESTRAS_RAMPA, USAR_LLM_FALLBACK, PROVEEDOR_LLM,
    PAIS_FESTIVOS, SUBDIV_FESTIVOS,
)
from .heuristic import _detectar_var_tiempo, _heuristica, _detectar_metrica_via_llm
from .blocks import (
    gen_t_anios, gen_t_meses, gen_t_dias, gen_t_horas,
    gen_t_laborables, gen_t_festivos, gen_t_quincenas,
    gen_t_estaciones, gen_t_franjas, gen_t_minutos,
    gen_v_metrica, filtrar_variables_constantes,
)


@dataclass
class FuzzyConfig:
    """Parámetros del pipeline. Defaults = mismos valores que el notebook."""

    # Overrides manuales de columnas
    var_tiempo_override:  Optional[str] = None
    var_metrica_override: Optional[str] = None

    # Tolerancias
    tolerancia:     float         = TOLERANCIA
    tol_anios:      Optional[float] = TOL_ANIOS
    tol_meses:      Optional[float] = TOL_MESES
    tol_semanas:    float         = TOL_SEMANAS
    tol_horas:      float         = TOL_HORAS
    tol_quincenas:  Optional[float] = TOL_QUINCENAS
    tol_estaciones: Optional[float] = TOL_ESTACIONES
    tol_absolutas:  Optional[float] = TOL_ABSOLUTAS

    # Muestras mínimas en la rampa
    n_muestras_rampa: int = N_MUESTRAS_RAMPA

    # Bloques GEN_* (None = decisión automática según granularidad)
    gen_anios:      Optional[bool] = None
    gen_meses:      Optional[bool] = None
    gen_estaciones: Optional[bool] = None
    gen_quincenas:  Optional[bool] = None
    gen_dias:       Optional[bool] = None
    gen_laborables: Optional[bool] = None
    gen_franjas:    Optional[bool] = None
    gen_horas:      Optional[bool] = None
    gen_minutos:    Optional[bool] = None
    gen_min_finos:  Optional[bool] = None
    gen_festivos:   Optional[bool] = None

    # Festivos
    pais_festivos:   str           = PAIS_FESTIVOS
    subdiv_festivos: Optional[str] = SUBDIV_FESTIVOS

    # LLM fallback
    usar_llm_fallback: bool         = USAR_LLM_FALLBACK
    proveedor_llm:     str          = PROVEEDOR_LLM
    llm_api_key:       Optional[str] = None

    # Calculado en tiempo de ejecución (no expuesto al usuario)
    granularidad_s: float = field(default=0.0, repr=False)


def _resolver_gen(flag_usuario, valor_auto):
    """None → decisión automática; True/False → el usuario fuerza."""
    return valor_auto if flag_usuario is None else bool(flag_usuario)


def _calcular_gen_flags(config: FuzzyConfig, df, var_tiempo) -> FuzzyConfig:
    """Rellena los GEN_* None con la decisión automática."""
    t_min, t_max = df[var_tiempo].min(), df[var_tiempo].max()
    cobertura_s    = (t_max - t_min).total_seconds()
    cobertura_dias = cobertura_s / 86400
    gran           = config.granularidad_s
    n_anios        = df[var_tiempo].dt.year.nunique()
    n_meses        = df[var_tiempo].dt.to_period("M").nunique()

    _auto = {
        "ANIOS":      n_anios >= 2,
        "MESES":      gran <= 86400    and n_meses >= 2,
        "ESTACIONES": gran <= 604800   and cobertura_dias >= 90,
        "QUINCENAS":  gran <= 86400    and cobertura_dias >= 30,
        "DIAS":       gran <= 86400     and cobertura_dias >= 7,
        "LABORABLES": gran <= 86400     and cobertura_dias >= 7,
        "FRANJAS":    gran <= 3600     and cobertura_dias >= 1,
        "HORAS":      gran <= 3600     and cobertura_dias >= 1,
        "MIN_FINOS":  gran < 60        and cobertura_s   >= 3600,
        "MINUTOS":    gran < 900       and cobertura_s   >= 3600,
        "FESTIVOS":   gran <= 86400    and cobertura_dias >= 1,
    }

    config.gen_anios      = _resolver_gen(config.gen_anios,      _auto["ANIOS"])
    config.gen_meses      = _resolver_gen(config.gen_meses,      _auto["MESES"])
    config.gen_estaciones = _resolver_gen(config.gen_estaciones, _auto["ESTACIONES"])
    config.gen_quincenas  = _resolver_gen(config.gen_quincenas,  _auto["QUINCENAS"])
    config.gen_dias       = _resolver_gen(config.gen_dias,       _auto["DIAS"])
    config.gen_laborables = _resolver_gen(config.gen_laborables, _auto["LABORABLES"])
    config.gen_franjas    = _resolver_gen(config.gen_franjas,    _auto["FRANJAS"])
    config.gen_horas      = _resolver_gen(config.gen_horas,      _auto["HORAS"])
    config.gen_minutos    = _resolver_gen(config.gen_minutos,    _auto["MINUTOS"])
    config.gen_min_finos  = _resolver_gen(config.gen_min_finos,  _auto["MIN_FINOS"])
    config.gen_festivos   = _resolver_gen(config.gen_festivos,   _auto["FESTIVOS"])

    return config


def detectar_metricas_candidatas(df: pd.DataFrame, config: FuzzyConfig) -> dict:
    """
    Ejecuta solo la fase de detección (var_tiempo + métrica) SIN fuzzificar.
    Devuelve:
    {
        "var_tiempo": "fecha",
        "candidatas": [
            {"nombre": "intensidad", "sugerida": True,  "razon": "heuristica_cv"},
            {"nombre": "ocupacion",  "sugerida": False, "razon": "heuristica_cv"},
        ],
        "granularidad_s": 900,
    }
    """
    df_raw = df.copy()

    # Detectar variable temporal
    if config.var_tiempo_override is not None:
        var_tiempo = config.var_tiempo_override
    else:
        var_tiempo, df_raw = _detectar_var_tiempo(df_raw)

    if var_tiempo is None:
        return {"var_tiempo": None, "candidatas": [], "granularidad_s": None}

    # Calcular granularidad
    df_raw[var_tiempo] = pd.to_datetime(df_raw[var_tiempo])
    df_sorted = df_raw.sort_values(var_tiempo)
    _diffs = df_sorted[var_tiempo].diff().dt.total_seconds().dropna()
    granularidad_s = float(_diffs.median()) if len(_diffs) else 3600.0

    # Ejecutar heurística
    claras, ambiguas, info = _detectar_var_metrica(df_raw, var_tiempo)

    candidatas = []
    for col in claras:
        candidatas.append({"nombre": col, "sugerida": True, "razon": "heuristica_cv"})
    for col in ambiguas:
        candidatas.append({"nombre": col, "sugerida": False, "razon": "heuristica_cv"})

    return {
        "var_tiempo":    var_tiempo,
        "candidatas":    candidatas,
        "granularidad_s": granularidad_s,
    }


def _leer_csv(ruta_o_buffer) -> pd.DataFrame:
    """
    Lee un CSV tolerando separadores coma, punto y coma y tabulador,
    y convierte columnas objeto con coma decimal a float.
    Acepta tanto rutas de fichero como objetos BytesIO.
    """
    for sep in [',', ';', '\t']:
        try:
            if hasattr(ruta_o_buffer, 'seek'):
                ruta_o_buffer.seek(0)
            df = pd.read_csv(ruta_o_buffer, sep=sep,
                             encoding='utf-8',
                             on_bad_lines='skip')
            if df.shape[1] <= 1:
                continue
            # Convertir comas decimales en columnas objeto
            for col in df.columns:
                if df[col].dtype == object:
                    conv = pd.to_numeric(
                        df[col].astype(str)
                            .str.replace(',', '.', regex=False),
                        errors='coerce'
                    )
                    if conv.notna().mean() > 0.7:
                        df[col] = conv
            return df
        except Exception:
            continue
    raise ValueError(
        "No se ha podido leer el CSV. Separadores soportados: "
        "coma, punto y coma, tabulador."
    )


def _limpiar_metrica(serie: pd.Series, centinelas: list = None) -> pd.Series:
    """
    Limpia la columna de métrica antes de fuzzificar.
    1. Elimina NaN reales.
    2. Elimina valores centinela (por defecto: -1, -200, 9999, -9999).
    Devuelve la serie limpia. Si queda vacía, lanza ValueError
    con mensaje descriptivo.
    """
    if centinelas is None:
        centinelas = [-1, -200, 9999, -9999]

    # Paso 1: NaN
    serie = serie.dropna()

    # Paso 2: centinelas
    serie = serie[~serie.isin(centinelas)]

    if serie.empty:
        raise ValueError(
            f"La columna de métrica se ha quedado vacía tras la limpieza. "
            f"Revisa que el CSV no tenga solo valores nulos o centinela."
        )

    return serie


def fuzzificar(df: pd.DataFrame, config: FuzzyConfig) -> pd.DataFrame:
    """
    Pipeline completo de fuzzificación.

    Entrada:  DataFrame con columna temporal y métrica.
    Salida:   DataFrame con t_* y v_* añadidas, columnas constantes eliminadas.
    """
    df_raw = df.copy()

    # ── Paso 1: detectar / confirmar variable temporal ────────────────────────
    if config.var_tiempo_override is not None:
        var_tiempo = config.var_tiempo_override
        print(f"VAR_TIEMPO forzado manualmente: {var_tiempo!r}")
    else:
        var_tiempo, df_raw = _detectar_var_tiempo(df_raw)
        if var_tiempo:
            print(f"VAR_TIEMPO detectado: {var_tiempo!r}")

    if var_tiempo is None:
        raise ValueError("No se pudo detectar la variable temporal. "
                         "Especifica var_tiempo_override en FuzzyConfig.")

    # ── Paso 2: detectar / confirmar variable métrica ─────────────────────────
    claras, ambiguas, info_heur = _detectar_var_metrica(df_raw, var_tiempo)
    _todas = claras + ambiguas

    if config.var_metrica_override is not None:
        var_metrica = config.var_metrica_override
        print(f"Override manual: VAR_METRICA = {var_metrica!r}")

    elif len(_todas) == 0:
        raise ValueError("No se detectó ninguna métrica candidata. "
                         "Especifica var_metrica_override en FuzzyConfig.")

    elif len(_todas) == 1:
        var_metrica = _todas[0]
        print(f"Detección automática unívoca: VAR_METRICA = {var_metrica!r}")

    elif len(ambiguas) == 0:
        var_metrica = claras[0]
        print(f"Varias métricas detectadas: {claras}")
        print(f"  Usando: {var_metrica!r}")

    else:
        _metricas_llm = None
        if config.usar_llm_fallback and not claras:
            print("    → Intentando desambiguar con el LLM...")
            _metricas_llm = _detectar_metrica_via_llm(df_raw, var_tiempo, _todas, config)

        if _metricas_llm:
            var_metrica = _metricas_llm[0]
            print(f"Métrica seleccionada por LLM: VAR_METRICA = {var_metrica!r}")
        else:
            print(f"Columnas ambiguas: {ambiguas}")
            print(f"    Especifica: var_metrica_override = 'nombre_columna'")
            var_metrica = claras[0] if claras else ambiguas[0]
            print(f"    Usando por defecto: {var_metrica!r}")

    # ── Paso 3: construir df de trabajo ───────────────────────────────────────
    result = df_raw[[var_tiempo, var_metrica]].copy()
    result[var_tiempo] = pd.to_datetime(result[var_tiempo], errors='coerce')
    result = result.dropna(subset=[var_tiempo])

    # Limpiar métrica antes de fuzzificar
    try:
        result[var_metrica] = _limpiar_metrica(result[var_metrica])
    except ValueError as e:
        raise ValueError(str(e)) from e

    n_original = len(result)
    result = result.dropna(subset=[var_metrica])
    n_limpio = len(result)
    if n_original != n_limpio:
        print(f"  Limpieza de métrica: {n_original - n_limpio} "
              f"filas eliminadas ({n_original} → {n_limpio})")

    result = result.sort_values(var_tiempo).reset_index(drop=True)

    t0    = result[var_tiempo].min()
    segundos = (result[var_tiempo] - t0).dt.total_seconds()
    result["segundos"] = segundos.fillna(0).astype(int)
    x     = result["segundos"].to_numpy()
    x_max = int(result["segundos"].max())

    anio_inicio = result[var_tiempo].min().year
    anio_fin    = result[var_tiempo].max().year

    _diffs_tmp = result[var_tiempo].diff().dt.total_seconds().dropna()
    config.granularidad_s = float(_diffs_tmp.median()) if len(_diffs_tmp) else 3600.0
    del _diffs_tmp

    print(f"\nDataset: {len(result):,} filas | métrica: {var_metrica!r} "
          f"| granularidad: {config.granularidad_s:.0f}s")

    # ── Paso 4: resolver flags GEN_* ──────────────────────────────────────────
    config = _calcular_gen_flags(config, result, var_tiempo)

    # ── Paso 5: generar t_* ───────────────────────────────────────────────────
    if config.gen_anios:
        result = gen_t_anios(result, x, t0, x_max, anio_inicio, anio_fin, config)

    if config.gen_meses:
        result = gen_t_meses(result, x, t0, x_max, anio_inicio, anio_fin, config)

    if config.gen_dias:
        result = gen_t_dias(result, x, t0, x_max, var_tiempo, config)

    if config.gen_laborables:
        # Depende de gen_dias
        if not config.gen_dias:
            result = gen_t_dias(result, x, t0, x_max, var_tiempo, config)
        result = gen_t_laborables(result, config)

    if config.gen_festivos:
        result = gen_t_festivos(result, var_tiempo, anio_inicio, anio_fin, config)

    if config.gen_quincenas:
        result = gen_t_quincenas(result, x, t0, x_max, anio_inicio, anio_fin, config)

    if config.gen_estaciones:
        result = gen_t_estaciones(result, x, t0, x_max, anio_inicio, anio_fin, config)

    if config.gen_horas:
        result = gen_t_horas(result, x, t0, x_max, var_tiempo, config)

    if config.gen_franjas:
        # Depende de gen_horas
        if not config.gen_horas:
            result = gen_t_horas(result, x, t0, x_max, var_tiempo, config)
        result = gen_t_franjas(result, config)

    if config.gen_minutos:
        result = gen_t_minutos(result, x, t0, x_max, var_tiempo, config)

    # ── Paso 6: generar v_* ───────────────────────────────────────────────────
    result = gen_v_metrica(result, var_metrica, config)

    # ── Paso 7: eliminar columnas constantes ──────────────────────────────────
    result = filtrar_variables_constantes(result)

    return result
