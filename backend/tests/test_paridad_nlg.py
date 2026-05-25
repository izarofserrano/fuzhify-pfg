"""
Test de paridad src03: verifica que generar_informe() produce exactamente el
mismo Markdown que el módulo genérico sobre los 3 datasets de referencia.

Las referencias (_v2.md) fueron generadas por el propio módulo portado,
NO por el notebook original con hardcodes de sensor (Historia B: módulo genérico).

Ejecución con defaults (asume que los archivos están en data/notebook_outputs/):
  cd backend
  pytest tests/test_paridad_nlg.py -v

Variables de entorno opcionales para sobreescribir paths:
  PARIDAD_REGLAS_DELHI / PARIDAD_FUZZY_DELHI / PARIDAD_REF_DELHI
  PARIDAD_REGLAS_3600  / PARIDAD_FUZZY_3600  / PARIDAD_REF_3600
  PARIDAD_REGLAS_6823  / PARIDAD_FUZZY_6823  / PARIDAD_REF_6823
"""
import os

import pandas as pd
import pytest

from app.core.nlg import generar_informe, NLGConfig

# ── Paths de referencia (con fallback a data/notebook_outputs/) ───────────────
_BASE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "notebook_outputs")

_DATASETS = [
    {
        "nombre":         "DailyDelhiClimateTrain_meantemp",
        "nombre_dataset": "delhi",
        "reglas":  os.environ.get("PARIDAD_REGLAS_DELHI",
                       os.path.join(_BASE, "DailyDelhiClimateTrain_meantemp_reglas.csv")),
        "fuzzy":   os.environ.get("PARIDAD_FUZZY_DELHI",
                       os.path.join(_BASE, "DailyDelhiClimateTrain_meantemp_fuzzy.csv")),
        "ref":     os.environ.get("PARIDAD_REF_DELHI",
                       os.path.join(_BASE, "DailyDelhiClimateTrain_meantemp_resumen_v2.md")),
    },
    {
        "nombre":         "3600_intensidad",
        "nombre_dataset": "3600",
        "reglas":  os.environ.get("PARIDAD_REGLAS_3600",
                       os.path.join(_BASE, "3600_intensidad_reglas.csv")),
        "fuzzy":   os.environ.get("PARIDAD_FUZZY_3600",
                       os.path.join(_BASE, "3600_intensidad_fuzzy.csv")),
        "ref":     os.environ.get("PARIDAD_REF_3600",
                       os.path.join(_BASE, "3600_intensidad_resumen_v2.md")),
    },
    {
        "nombre":         "6823_ocupacion",
        "nombre_dataset": "6823",
        "reglas":  os.environ.get("PARIDAD_REGLAS_6823",
                       os.path.join(_BASE, "6823_ocupacion_reglas.csv")),
        "fuzzy":   os.environ.get("PARIDAD_FUZZY_6823",
                       os.path.join(_BASE, "6823_ocupacion_fuzzy.csv")),
        "ref":     os.environ.get("PARIDAD_REF_6823",
                       os.path.join(_BASE, "6823_ocupacion_resumen_v2.md")),
    },
]


@pytest.mark.parametrize("dataset", _DATASETS, ids=[d["nombre"] for d in _DATASETS])
def test_paridad_nlg(dataset):
    """
    Ejecuta generar_informe() sobre los CSVs de referencia y compara el
    Markdown resultante línea a línea con la referencia _v2.md del módulo.
    """
    reglas_path = dataset["reglas"]
    fuzzy_path  = dataset["fuzzy"]
    ref_path    = dataset["ref"]

    if not os.path.exists(reglas_path):
        pytest.skip(f"CSV de reglas no encontrado: {reglas_path}")
    if not os.path.exists(fuzzy_path):
        pytest.skip(f"CSV fuzzy no encontrado: {fuzzy_path}")
    if not os.path.exists(ref_path):
        pytest.skip(f"Referencia _v2.md no encontrada: {ref_path}")

    df_reglas = pd.read_csv(reglas_path)
    df_fuzzy  = pd.read_csv(fuzzy_path)

    config  = NLGConfig(nombre_dataset=dataset["nombre_dataset"])
    informe = generar_informe(df_reglas, df_fuzzy, config)

    with open(ref_path, encoding="utf-8") as f:
        ref_texto = f.read()

    lineas_out = [l.rstrip() for l in informe.splitlines()]
    lineas_ref = [l.rstrip() for l in ref_texto.splitlines()]

    assert len(lineas_out) == len(lineas_ref), (
        f"[{dataset['nombre']}] Número de líneas distinto: "
        f"módulo={len(lineas_out)}, ref={len(lineas_ref)}"
    )
    for i, (got, exp) in enumerate(zip(lineas_out, lineas_ref), start=1):
        assert got == exp, (
            f"[{dataset['nombre']}] Diferencia en línea {i}:\n"
            f"  módulo: {repr(got)}\n"
            f"  ref:    {repr(exp)}"
        )
