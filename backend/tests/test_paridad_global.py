"""
Test de paridad src04: verifica que construir_informe_global() produce
exactamente el mismo Markdown que la referencia aprobada (informe_global_madrid_v2.md),
sobre los 2 CSVs de reglas de Madrid (3600 + 6823).

La línea "*Generado el …" se excluye de la comparación: contiene la fecha
de ejecución y cambia en cada llamada.

Ejecución con defaults (asume que los archivos están en data/notebook_outputs/):
  cd backend
  pytest tests/test_paridad_global.py -v

Variables de entorno opcionales para sobreescribir paths:
  PARIDAD_REGLAS_3600_GLOBAL   PARIDAD_REGLAS_6823_GLOBAL   PARIDAD_REF_GLOBAL
"""
import os

import pytest

from app.core.global_report import construir_informe_global

_BASE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "notebook_outputs")

_REGLAS_3600 = os.environ.get(
    "PARIDAD_REGLAS_3600_GLOBAL",
    os.path.join(_BASE, "3600_intensidad_reglas.csv"),
)
_REGLAS_6823 = os.environ.get(
    "PARIDAD_REGLAS_6823_GLOBAL",
    os.path.join(_BASE, "6823_ocupacion_reglas.csv"),
)
_REF = os.environ.get(
    "PARIDAD_REF_GLOBAL",
    os.path.join(_BASE, "informe_global_madrid_v2.md"),
)


def _filtrar(lineas):
    """Elimina la línea de fecha dinámica antes de comparar."""
    return [l for l in lineas if not l.lstrip().startswith("*Generado el")]


def test_paridad_global():
    """
    construir_informe_global() sobre 3600 + 6823 debe producir el mismo
    Markdown que informe_global_madrid_v2.md (excluyendo la línea de fecha).
    """
    if not os.path.exists(_REGLAS_3600):
        pytest.skip(f"CSV de reglas no encontrado: {_REGLAS_3600}")
    if not os.path.exists(_REGLAS_6823):
        pytest.skip(f"CSV de reglas no encontrado: {_REGLAS_6823}")
    if not os.path.exists(_REF):
        pytest.skip(f"Referencia no encontrada: {_REF}")

    informe = construir_informe_global([_REGLAS_3600, _REGLAS_6823])

    with open(_REF, encoding="utf-8") as f:
        ref_texto = f.read()

    lineas_out = _filtrar([l.rstrip() for l in informe.splitlines()])
    lineas_ref = _filtrar([l.rstrip() for l in ref_texto.splitlines()])

    assert len(lineas_out) == len(lineas_ref), (
        f"Número de líneas distinto (sin línea de fecha): "
        f"módulo={len(lineas_out)}, ref={len(lineas_ref)}"
    )

    for i, (got, exp) in enumerate(zip(lineas_out, lineas_ref), start=1):
        assert got == exp, (
            f"Diferencia en línea {i} (sin línea de fecha):\n"
            f"  módulo: {repr(got)}\n"
            f"  ref:    {repr(exp)}"
        )
