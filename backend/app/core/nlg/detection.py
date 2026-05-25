import re

import numpy as np
import pandas as pd


def detectar_bloques(df_fuzzy):
    """
    Detecta qué bloques temporales están disponibles en el CSV fuzzificado.
    Devuelve un dict con flags HAY_*.
    """
    cols = set(df_fuzzy.columns)
    return {
        "HAY_ANIOS":      any(re.match(r'^t_\d{4}$', c) for c in cols),
        "HAY_MESES":      any(c in cols for c in ["t_Ene","t_Feb","t_Marz"]),
        "HAY_ESTACIONES": any(c in cols for c in ["t_Primavera","t_Verano","t_Otonio","t_Invierno"]),
        "HAY_QUINCENAS":  any(c in cols for c in ["t_Q1mes","t_Q2mes"]),
        "HAY_DIAS":       any(c in cols for c in ["t_Lun","t_Mar","t_Mie","t_Jue","t_Vie","t_Sab","t_Dom"]),
        "HAY_LABORABLES": any(c in cols for c in ["t_Laborable","t_FinSemana"]),
        "HAY_FRANJAS":    any(c in cols for c in ["t_Madrugada","t_Mañana","t_Tarde","t_Noche"]),
        "HAY_HORAS":      any(c.startswith("t_H") for c in cols),
        "HAY_MINUTOS":    any(
            c.startswith("t_M") and c[2:].isdigit() and int(c[2:]) % 15 == 0
            for c in cols
        ),
        "HAY_MIN_FINOS":  any(
            c.startswith("t_M") and c[2:].isdigit() and int(c[2:]) % 15 != 0
            for c in cols
        ),
        "HAY_FESTIVOS":   "t_Festivo" in cols,
    }


def detectar_granularidad(df_fuzzy, var_tiempo):
    """
    Calcula la granularidad mediana del dataset y su descripción legible.
    Devuelve (GRANULARIDAD_S, granularidad_desc).
    """
    GRANULARIDAD_S = 3600.0
    granularidad_desc = "desconocida"

    if var_tiempo and var_tiempo in df_fuzzy.columns:
        _col = pd.to_datetime(df_fuzzy[var_tiempo], errors="coerce")
        _diffs = _col.diff().dt.total_seconds().dropna()
        if len(_diffs) > 0:
            GRANULARIDAD_S = float(_diffs.median())

    if   GRANULARIDAD_S >= 86400:  granularidad_desc = "diaria"
    elif GRANULARIDAD_S >= 3600:   granularidad_desc = "horaria"
    elif GRANULARIDAD_S >= 900:    granularidad_desc = "de 15 minutos"
    else:                          granularidad_desc = f"de {int(GRANULARIDAD_S)}s"

    return GRANULARIDAD_S, granularidad_desc


def detectar_var_tiempo(df_fuzzy):
    """
    Auto-detecta la columna temporal en el CSV fuzzificado.
    Prueba las columnas no-t_, no-v_, no-segundos y devuelve la primera
    que sea parseable como datetime. Devuelve '' si no encuentra ninguna.
    """
    candidatas = [
        c for c in df_fuzzy.columns
        if not c.startswith("t_")
        and not c.startswith("v_")
        and c != "segundos"
    ]
    for col in candidatas:
        try:
            parsed = pd.to_datetime(df_fuzzy[col].head(20), errors="coerce")
            if parsed.notna().sum() >= 5:
                return col
        except Exception:
            pass
    return ""


def _construir_grupos_src03(cols_disponibles):
    """
    Genera los grupos mutuamente excluyentes filtrando solo las columnas
    que realmente existen en el CSV fuzzificado.
    """
    cols = set(cols_disponibles)
    candidatos = [
        {"t_Ene","t_Feb","t_Marz","t_Abr","t_May","t_Jun",
         "t_Jul","t_Ago","t_Sep","t_Oct","t_Nov","t_Dic"},
        {"t_Primavera","t_Verano","t_Otonio","t_Invierno"},
        {f"t_H{h:02d}" for h in range(24)},
        {"t_Madrugada","t_Mañana","t_Tarde","t_Noche"},
        {"t_Lun","t_Mar","t_Mie","t_Jue","t_Vie","t_Sab","t_Dom"},
        {"t_Laborable","t_FinSemana"},
        {c for c in cols if c.startswith("t_20")},  # años dinámicos
        {"t_Q1mes","t_Q2mes"},
        {"t_M00","t_M15","t_M30","t_M45"},
        {"t_Laborable","t_Sab","t_Dom"},
        {"t_FinSemana","t_Lun","t_Mar","t_Mie","t_Jue","t_Vie"},
    ]
    return [g & cols for g in candidatos if len(g & cols) >= 2]
