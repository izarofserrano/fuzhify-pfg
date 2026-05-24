"""
Test de paridad: verifica que fuzzificar() produce el mismo CSV (byte a byte en
columnas numéricas, igualdad exacta en categóricas) que el notebook de referencia.

Variables de entorno necesarias por caso:
  PARIDAD_INPUT  → ruta al CSV de entrada  (ej: data/raw/3600.csv)
  PARIDAD_REF    → ruta al CSV de referencia generado por el notebook
  PARIDAD_METRICA → nombre de la columna métrica (override, evita LLM en CI)

Para ejecutar un caso concreto:
  PARIDAD_INPUT=data/raw/3600.csv \\
  PARIDAD_REF=data/notebook_outputs/3600_intensidad_fuzzy.csv \\
  PARIDAD_METRICA=intensidad \\
  pytest backend/tests/test_paridad_fuzzy.py -v

Los tres casos de paridad requeridos:
  1. data/raw/3600.csv              + 3600_intensidad_fuzzy.csv   (Madrid, 15 min)
  2. data/raw/6823.csv              + 6823_ocupacion_fuzzy.csv    (Madrid, 15 min)
  3. data/raw/DailyDelhiClimateTrain.csv + DailyDelhiClimateTrain_meantemp_fuzzy.csv  (diaria)
"""

import os

import numpy as np
import pandas as pd
import pytest

from app.core.fuzzy import FuzzyConfig, fuzzificar

PARIDAD_INPUT   = os.environ.get("PARIDAD_INPUT")
PARIDAD_REF     = os.environ.get("PARIDAD_REF")
PARIDAD_METRICA = os.environ.get("PARIDAD_METRICA")


@pytest.mark.skipif(
    not PARIDAD_INPUT or not PARIDAD_REF,
    reason="PARIDAD_INPUT y PARIDAD_REF no definidas",
)
def test_paridad_fuzzy():
    """El CSV producido por fuzzificar() debe ser idéntico al del notebook."""

    df_in = pd.read_csv(PARIDAD_INPUT)

    config = FuzzyConfig(
        var_metrica_override=PARIDAD_METRICA or None,
        usar_llm_fallback=False,   # en CI no hay API key
    )

    df_resultado = fuzzificar(df_in, config)
    df_ref       = pd.read_csv(PARIDAD_REF)

    # ── Mismo conjunto de columnas ────────────────────────────────────────────
    cols_resultado = sorted(df_resultado.columns.tolist())
    cols_ref       = sorted(df_ref.columns.tolist())
    assert cols_resultado == cols_ref, (
        f"Columnas diferentes.\n"
        f"  Solo en resultado: {set(cols_resultado) - set(cols_ref)}\n"
        f"  Solo en referencia: {set(cols_ref) - set(cols_resultado)}"
    )

    # ── Mismo número de filas ─────────────────────────────────────────────────
    assert len(df_resultado) == len(df_ref), (
        f"Filas: resultado={len(df_resultado)}, referencia={len(df_ref)}"
    )

    # ── Mismo orden de columnas ───────────────────────────────────────────────
    df_resultado = df_resultado[df_ref.columns]

    # ── Verificación por columna ──────────────────────────────────────────────
    cols_num = df_ref.select_dtypes(include=[np.number]).columns.tolist()
    cols_cat = [c for c in df_ref.columns if c not in cols_num]

    # Columnas numéricas: np.allclose con tolerancia 1e-9
    for col in cols_num:
        r = df_resultado[col].to_numpy(dtype=float)
        e = df_ref[col].to_numpy(dtype=float)
        assert np.allclose(r, e, atol=1e-9, rtol=0, equal_nan=True), (
            f"Columna numérica '{col}' no coincide.\n"
            f"  max diferencia absoluta: {np.abs(r - e).max():.2e}"
        )

    # Columnas categóricas / texto: igualdad exacta
    for col in cols_cat:
        dif = df_resultado[col].reset_index(drop=True) != df_ref[col].reset_index(drop=True)
        assert not dif.any(), (
            f"Columna categórica '{col}' no coincide en {dif.sum()} filas."
        )
