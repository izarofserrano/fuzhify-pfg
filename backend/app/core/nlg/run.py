# -*- coding: utf-8 -*-
import argparse

import pandas as pd

from .pipeline import generar_informe, NLGConfig


def main():
    parser = argparse.ArgumentParser(
        description="Genera un informe Markdown a partir de reglas y CSV fuzzificado."
    )
    parser.add_argument("--reglas", required=True,
                        help="CSV de reglas (salida de src02 / minar_reglas)")
    parser.add_argument("--fuzzy",  required=True,
                        help="CSV fuzzificado (salida de src01)")
    parser.add_argument("--out",    required=True,
                        help="Ruta del fichero Markdown de salida")

    # NLGConfig overrides
    parser.add_argument("--dataset",        default="",
                        help="Nombre del dataset (si vacío, se usa el nombre de la métrica)")
    parser.add_argument("--metrica",        default="",
                        help="Nombre de la columna métrica (si vacío, se auto-detecta)")
    parser.add_argument("--var-tiempo",     default="",
                        help="Columna temporal (si vacío, se auto-detecta)")
    parser.add_argument("--min-reglas-grupo", type=int, default=2,
                        help="Mínimo de reglas para generar párrafo agrupado (default: 2)")

    args = parser.parse_args()

    df_reglas = pd.read_csv(args.reglas)
    df_fuzzy  = pd.read_csv(args.fuzzy)

    config = NLGConfig(
        nombre_dataset  = args.dataset,
        metrica         = args.metrica,
        var_tiempo      = args.var_tiempo,
        min_reglas_grupo= args.min_reglas_grupo,
    )

    informe = generar_informe(df_reglas, df_fuzzy, config)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(informe)

    print(f"Informe guardado en {args.out}")


if __name__ == "__main__":
    main()
