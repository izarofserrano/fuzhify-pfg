"""
CLI para el módulo de minería de reglas.

Uso:
  python -m app.core.mining.run --fuzzy data/X_fuzzy.csv --out data/X_reglas.csv

Opciones avanzadas (sobreescriben los defaults de MinerConfig):
  --min-soporte FLOAT        (default 0.005)
  --min-confianza FLOAT      (default 0.50)
  --lift-minimo FLOAT        (default 2.0)
  --max-prof INT             (default 3)
  --k-beam INT               (default 10)
  --top-por-consecuente INT  (default 10)
"""
import argparse

import pandas as pd

from .pipeline import minar_reglas, MinerConfig


def main():
    parser = argparse.ArgumentParser(
        description="Minería de reglas de asociación difusas (src02)"
    )
    parser.add_argument("--fuzzy", required=True, help="CSV fuzzificado de entrada")
    parser.add_argument("--out",   required=True, help="CSV de reglas de salida")
    parser.add_argument("--min-soporte",       type=float, default=None)
    parser.add_argument("--min-confianza",     type=float, default=None)
    parser.add_argument("--lift-minimo",       type=float, default=None)
    parser.add_argument("--max-prof",          type=int,   default=None)
    parser.add_argument("--k-beam",            type=int,   default=None)
    parser.add_argument("--top-por-consecuente", type=int, default=None)
    args = parser.parse_args()

    config = MinerConfig()
    if args.min_soporte        is not None: config.min_soporte        = args.min_soporte
    if args.min_confianza      is not None: config.min_confianza      = args.min_confianza
    if args.lift_minimo        is not None: config.lift_minimo        = args.lift_minimo
    if args.max_prof           is not None: config.max_prof           = args.max_prof
    if args.k_beam             is not None: config.k_beam             = args.k_beam
    if args.top_por_consecuente is not None: config.top_por_consecuente = args.top_por_consecuente

    df_fuzzy = pd.read_csv(args.fuzzy)
    df_reglas = minar_reglas(df_fuzzy, config)
    df_reglas.to_csv(args.out, index=False)
    print(f"Reglas guardadas en: {args.out}  ({len(df_reglas)} reglas)")


if __name__ == "__main__":
    main()
