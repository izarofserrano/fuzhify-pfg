# -*- coding: utf-8 -*-
"""
CLI para el módulo de informe global.

Uso:
  python -m app.core.global_report.run \\
      --reglas data/3600_intensidad_reglas.csv data/6823_ocupacion_reglas.csv \\
      --out data/informe_global.md \\
      --nombre-conjunto "Sensores de tráfico de Madrid"
"""
import argparse

from .pipeline import construir_informe_global


def main():
    parser = argparse.ArgumentParser(
        description="Genera un informe global comparativo a partir de varios CSVs de reglas."
    )
    parser.add_argument(
        "--reglas", nargs="+", required=True,
        help="CSVs de reglas (salida de src02), uno por sensor/métrica",
    )
    parser.add_argument(
        "--out", required=True,
        help="Ruta del fichero Markdown de salida",
    )
    parser.add_argument(
        "--nombre-conjunto", default="",
        help="Etiqueta descriptiva del conjunto de datos (p.ej. 'Madrid')",
    )
    args = parser.parse_args()

    informe = construir_informe_global(
        rutas_reglas    = args.reglas,
        nombre_conjunto = args.nombre_conjunto,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(informe)

    print(f"Informe global guardado en {args.out}")


if __name__ == "__main__":
    main()
