"""
CLI de fuzzificación.

Uso:
    python -m app.core.fuzzy.run --csv data/raw/3600.csv --out data/3600_fuzzy.csv
    python -m app.core.fuzzy.run --csv data/raw/3600.csv --out data/out.csv \\
        --metrica intensidad --pais ES --subdiv MD
"""

import argparse
import sys

import pandas as pd

from .pipeline import FuzzyConfig, fuzzificar


def main():
    parser = argparse.ArgumentParser(description="Fuzzifica un CSV de serie temporal.")
    parser.add_argument("--csv",     required=True,  help="Ruta del CSV de entrada")
    parser.add_argument("--out",     required=True,  help="Ruta del CSV de salida")
    parser.add_argument("--tiempo",  default=None,   help="Nombre columna temporal (override)")
    parser.add_argument("--metrica", default=None,   help="Nombre columna métrica (override)")
    parser.add_argument("--pais",    default="ES",   help="País para festivos (ISO 3166)")
    parser.add_argument("--subdiv",  default="MD",   help="Subdivisión para festivos")
    parser.add_argument("--no-llm",  action="store_true", help="Desactiva el fallback LLM")

    args = parser.parse_args()

    config = FuzzyConfig(
        var_tiempo_override=args.tiempo,
        var_metrica_override=args.metrica,
        pais_festivos=args.pais,
        subdiv_festivos=args.subdiv if args.subdiv else None,
        usar_llm_fallback=not args.no_llm,
    )

    print(f"Cargando {args.csv} …")
    df = pd._leer_csv(args.csv)

    df_fuzzy = fuzzificar(df, config)

    df_fuzzy.to_csv(args.out, index=False)
    print(f"\nGuardado en: {args.out}")
    print(f"Shape: {df_fuzzy.shape}  ({df_fuzzy.shape[0]:,} filas × {df_fuzzy.shape[1]} columnas)")


if __name__ == "__main__":
    main()
