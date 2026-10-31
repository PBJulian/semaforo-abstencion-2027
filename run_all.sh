#!/usr/bin/env bash
# Reproduce todo el pipeline desde los datos crudos.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-.venv/bin/python}
for s in 01_ingest 02_panel 02b_censo 03_model 03b_robustez 04_scenarios 04b_retro 04c_operativo 05_export_figures 06_maps 07_report 08_presentacion; do
  echo "=== $s"
  $PY -W ignore src/$s.py
done
# PDF del reporte (requiere LibreOffice)
SOFFICE=${SOFFICE:-/Applications/LibreOffice.app/Contents/MacOS/soffice}
if [ -x "$SOFFICE" ]; then
  "$SOFFICE" --headless --convert-to pdf --outdir entregables entregables/Reporte_metodologico_preventivo_DataInsert.docx >/dev/null
fi
if [ -x "$SOFFICE" ]; then
  "$SOFFICE" --headless --convert-to pdf --outdir entregables entregables/Presentacion_ejecutiva_DataInsert.pptx >/dev/null
fi
