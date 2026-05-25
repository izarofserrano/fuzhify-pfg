"""
Test de paridad src02: verifica que minar_reglas() produce exactamente las
mismas reglas que el notebook, sobre los 3 datasets de referencia.

Variables de entorno requeridas por dataset (o usar los paths por defecto):
  PARIDAD_FUZZY_DELHI   / PARIDAD_REF_DELHI
  PARIDAD_FUZZY_3600    / PARIDAD_REF_3600
  PARIDAD_FUZZY_6823    / PARIDAD_REF_6823

Ejecución con defaults (asume que los CSVs están en data/notebook_outputs/):
  cd backend
  pytest tests/test_paridad_mining.py -v

Ejecución con paths explícitos:
  PARIDAD_FUZZY_DELHI=../data/notebook_outputs/DailyDelhiClimateTrain_meantemp_fuzzy.csv \
  PARIDAD_REF_DELHI=../data/notebook_outputs/DailyDelhiClimateTrain_meantemp_reglas.csv \
  pytest tests/test_paridad_mining.py -v
"""
import os
import pytest
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.mining import minar_reglas, MinerConfig

# ── Paths de referencia (con fallback a los de data/notebook_outputs/) ────────
_BASE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "notebook_outputs")

_DATASETS = [
    {
        "nombre":    "DailyDelhiClimateTrain_meantemp",
        "fuzzy":     os.environ.get("PARIDAD_FUZZY_DELHI",
                        os.path.join(_BASE, "DailyDelhiClimateTrain_meantemp_fuzzy.csv")),
        "ref":       os.environ.get("PARIDAD_REF_DELHI",
                        os.path.join(_BASE, "DailyDelhiClimateTrain_meantemp_reglas.csv")),
        # El notebook usó _LIFT_LABEL = "Sorprendentes" → 2.0
        "lift_minimo": 2.0,
    },
    {
        "nombre":    "3600_intensidad",
        "fuzzy":     os.environ.get("PARIDAD_FUZZY_3600",
                        os.path.join(_BASE, "3600_intensidad_fuzzy.csv")),
        "ref":       os.environ.get("PARIDAD_REF_3600",
                        os.path.join(_BASE, "3600_intensidad_reglas.csv")),
        "lift_minimo": 2.0,
    },
    {
        "nombre":    "6823_ocupacion",
        "fuzzy":     os.environ.get("PARIDAD_FUZZY_6823",
                        os.path.join(_BASE, "6823_ocupacion_fuzzy.csv")),
        "ref":       os.environ.get("PARIDAD_REF_6823",
                        os.path.join(_BASE, "6823_ocupacion_reglas.csv")),
        "lift_minimo": 2.0,
    },
]

_COLS_CLAVE = ["antecedente", "consecuente"]
_COLS_NUMERICAS = ["soporte", "confianza", "lift"]


@pytest.mark.parametrize("dataset", _DATASETS, ids=[d["nombre"] for d in _DATASETS])
def test_paridad_mining(dataset):
    fuzzy_path = dataset["fuzzy"]
    ref_path   = dataset["ref"]

    if not os.path.exists(fuzzy_path):
        pytest.skip(f"CSV fuzzy no encontrado: {fuzzy_path}")
    if not os.path.exists(ref_path):
        pytest.skip(f"CSV de referencia no encontrado: {ref_path}")

    df_fuzzy = pd.read_csv(fuzzy_path)
    df_ref   = pd.read_csv(ref_path)

    config = MinerConfig(lift_minimo=dataset["lift_minimo"])
    df_out = minar_reglas(df_fuzzy, config)

    # ── Mismo conjunto de columnas ────────────────────────────────────────────
    assert set(df_out.columns) == set(df_ref.columns), (
        f"Columnas distintas.\n  módulo: {sorted(df_out.columns)}\n"
        f"  notebook: {sorted(df_ref.columns)}"
    )

    # ── Mismas filas (ordenar por clave antes de comparar) ───────────────────
    df_out_s = (df_out.sort_values(_COLS_CLAVE)
                      .reset_index(drop=True))
    df_ref_s = (df_ref.sort_values(_COLS_CLAVE)
                      .reset_index(drop=True))

    assert len(df_out_s) == len(df_ref_s), (
        f"[{dataset['nombre']}] Número de reglas distinto: "
        f"módulo={len(df_out_s)}, notebook={len(df_ref_s)}\n"
        f"  Sólo en módulo:   {set(df_out_s['antecedente']+' -> '+df_out_s['consecuente']) - set(df_ref_s['antecedente']+' -> '+df_ref_s['consecuente'])}\n"
        f"  Sólo en notebook: {set(df_ref_s['antecedente']+' -> '+df_ref_s['consecuente']) - set(df_out_s['antecedente']+' -> '+df_out_s['consecuente'])}"
    )

    # ── Mismas claves (antecedente, consecuente) ──────────────────────────────
    claves_out = set(zip(df_out_s["antecedente"], df_out_s["consecuente"]))
    claves_ref = set(zip(df_ref_s["antecedente"], df_ref_s["consecuente"]))
    solo_modulo   = claves_out - claves_ref
    solo_notebook = claves_ref - claves_out
    assert claves_out == claves_ref, (
        f"[{dataset['nombre']}] Reglas distintas.\n"
        f"  Sólo en módulo:   {sorted(solo_modulo)}\n"
        f"  Sólo en notebook: {sorted(solo_notebook)}"
    )

    # ── Valores numéricos con tolerancia atol=1e-4 ───────────────────────────
    for col in _COLS_NUMERICAS:
        max_diff = np.abs(df_out_s[col].values - df_ref_s[col].values).max()
        assert max_diff <= 1e-4, (
            f"[{dataset['nombre']}] Columna '{col}' diverge: max_diff={max_diff:.2e}"
        )

    # ── n_vars coherente ─────────────────────────────────────────────────────
    assert (df_out_s["n_vars"] == df_ref_s["n_vars"]).all(), (
        f"[{dataset['nombre']}] n_vars difiere en algunas reglas"
    )
