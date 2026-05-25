# -*- coding: utf-8 -*-
"""
Test de paridad para el módulo nlg.

Uso — una variable de entorno por caso:
  PARIDAD_REGLAS   ruta al CSV de reglas (salida de src02 / minar_reglas)
  PARIDAD_FUZZY    ruta al CSV fuzzificado (salida de src01)
  PARIDAD_REF_MD   ruta al fichero Markdown de referencia (generado por el notebook)

Ejemplo (PowerShell):
  $env:PARIDAD_REGLAS = "../data/DailyDelhiClimateTrain_meantemp_reglas.csv"
  $env:PARIDAD_FUZZY  = "../data/DailyDelhiClimateTrain_meantemp_fuzzy.csv"
  $env:PARIDAD_REF_MD = "../data/DailyDelhiClimateTrain_meantemp_NLG.md"
  cd backend; .venv\\Scripts\\pytest.exe tests/test_paridad_nlg.py -v
"""

import os

import pandas as pd
import pytest

from app.core.nlg import generar_informe, NLGConfig


# ---------------------------------------------------------------------------
# Datasets parametrizados
# ---------------------------------------------------------------------------

DATASETS = [
    {
        "id":           "delhi",
        "env_reglas":   "PARIDAD_REGLAS_DELHI",
        "env_fuzzy":    "PARIDAD_FUZZY_DELHI",
        "env_ref":      "PARIDAD_REF_DELHI",
        "nombre_dataset": "DailyDelhiClimateTrain",
        "strict":       True,  # referencia generada con la versión actual del notebook
    },
    {
        "id":           "3600",
        "env_reglas":   "PARIDAD_REGLAS_3600",
        "env_fuzzy":    "PARIDAD_FUZZY_3600",
        "env_ref":      "PARIDAD_REF_3600",
        "nombre_dataset": "3600_intensidad",
        "strict":       False,  # referencia de versión antigua del notebook (plantillas distintas)
    },
    {
        "id":           "6823",
        "env_reglas":   "PARIDAD_REGLAS_6823",
        "env_fuzzy":    "PARIDAD_FUZZY_6823",
        "env_ref":      "PARIDAD_REF_6823",
        "nombre_dataset": "6823_ocupacion",
        "strict":       False,  # referencia de versión antigua del notebook (plantillas distintas)
    },
]

# Fallback: env vars genéricas PARIDAD_REGLAS / PARIDAD_FUZZY / PARIDAD_REF_MD
# permiten apuntar al único dataset que se quiere probar sin modificar el código.
GENERIC = {
    "id":           "generic",
    "env_reglas":   "PARIDAD_REGLAS",
    "env_fuzzy":    "PARIDAD_FUZZY",
    "env_ref":      "PARIDAD_REF_MD",
    "nombre_dataset": "",   # se auto-detecta
    "strict":       True,
}


def _build_params():
    params = []
    # Genérico primero (si está definido)
    if os.environ.get(GENERIC["env_reglas"]):
        params.append(pytest.param(GENERIC, id="generic"))
    for ds in DATASETS:
        if os.environ.get(ds["env_reglas"]):
            params.append(pytest.param(ds, id=ds["id"]))
    return params


def _skip_if_no_env(ds):
    reglas = os.environ.get(ds["env_reglas"], "")
    fuzzy  = os.environ.get(ds["env_fuzzy"],  "")
    ref    = os.environ.get(ds["env_ref"],    "")
    if not reglas or not fuzzy or not ref:
        pytest.skip(
            f"Variables de entorno no definidas: "
            f"{ds['env_reglas']}, {ds['env_fuzzy']}, {ds['env_ref']}"
        )
    return reglas, fuzzy, ref


# ---------------------------------------------------------------------------
# Test principal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ds", [
    pytest.param(GENERIC, id="generic"),
    *[pytest.param(ds, id=ds["id"]) for ds in DATASETS],
])
def test_paridad_nlg(ds):
    """
    Ejecuta generar_informe() sobre los ficheros de referencia y compara
    el Markdown resultante línea a línea con el generado por el notebook.
    """
    reglas_path, fuzzy_path, ref_path = _skip_if_no_env(ds)

    df_reglas = pd.read_csv(reglas_path)
    df_fuzzy  = pd.read_csv(fuzzy_path)

    config = NLGConfig(nombre_dataset=ds["nombre_dataset"])
    informe = generar_informe(df_reglas, df_fuzzy, config)

    with open(ref_path, encoding="utf-8") as f:
        ref_texto = f.read()

    lineas_out = [l.rstrip() for l in informe.splitlines()]
    lineas_ref = [l.rstrip() for l in ref_texto.splitlines()]

    if ds["strict"]:
        # Comparación estricta línea a línea
        assert len(lineas_out) == len(lineas_ref), (
            f"Número de líneas distinto: módulo={len(lineas_out)}, ref={len(lineas_ref)}"
        )
        for i, (got, exp) in enumerate(zip(lineas_out, lineas_ref), start=1):
            assert got == exp, (
                f"Diferencia en línea {i}:\n"
                f"  módulo: {repr(got)}\n"
                f"  ref:    {repr(exp)}"
            )
    else:
        # Comparación no-estricta: solo se verifica la estructura de alto nivel
        # (La referencia es de una versión antigua del notebook con plantillas distintas.)
        secciones_esperadas = [
            "# Resumen de comportamiento",
            "## Apéndice",
            "## Estadísticas globales",
        ]
        for seccion in secciones_esperadas:
            assert any(seccion in l for l in lineas_out), (
                f"Sección esperada no encontrada en el informe: {repr(seccion)}"
            )
        # El número de reglas debe coincidir con las del CSV
        n_reglas = len(df_reglas)
        assert f"**Total de reglas analizadas:** {n_reglas}" in informe or \
               any(str(n_reglas) in l for l in lineas_out[:20]), (
            f"El número de reglas ({n_reglas}) no aparece en la cabecera del informe."
        )
