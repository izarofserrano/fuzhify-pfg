#!/usr/bin/env bash
# Copia los CSVs de data/raw/ a data/ para que estén disponibles como
# archivos de prueba en la interfaz o via API.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RAW_DIR="$REPO_ROOT/data/raw"
DATA_DIR="$REPO_ROOT/data"

if [ ! -d "$RAW_DIR" ]; then
  echo "ERROR: No existe data/raw/. Crea el directorio y coloca tus CSVs."
  exit 1
fi

shopt -s nullglob
csvs=("$RAW_DIR"/*.csv)

if [ ${#csvs[@]} -eq 0 ]; then
  echo "No hay CSVs en data/raw/. Coloca al menos un fichero .csv y vuelve a ejecutar."
  exit 0
fi

count=0
for f in "${csvs[@]}"; do
  cp "$f" "$DATA_DIR/"
  echo "  Copiado: $(basename "$f")"
  count=$((count + 1))
done

echo ""
echo "Listo: $count CSV(s) disponibles en data/."
echo "Puedes subirlos desde http://localhost:5173 o via:"
echo "  curl -F 'csv=@data/<fichero>.csv' http://localhost:8001/api/v1/detect-metric"
