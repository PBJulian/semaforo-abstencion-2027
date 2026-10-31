"""
02b_censo.py
Indicadores municipales del Censo de Población y Vivienda 2020 (INEGI, Principales resultados por
localidad, ITER): migración interna, lengua indígena y escolaridad.

Se usan para el diagnóstico y la matriz de acción, no como variables del modelo: el censo 2020 no
estaba disponible para las elecciones anteriores a 2021, así que incluirlo en el backtest sería fuga.

Salida: data/processed/censo2020_mun.parquet (por CVEGEO)
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "inegi" / "iter2020"
PROC = ROOT / "data" / "processed"
VARS = ["POBTOT", "P_3YMAS", "P_5YMAS", "PNACOE", "PRESOE15", "P3YM_HLI", "GRAPROES"]


def main():
    f = next(RAW.rglob("conjunto_de_datos_iter_00CSV20.csv"))
    x = pd.read_csv(f, encoding="utf-8-sig", usecols=["ENTIDAD", "MUN", "LOC"] + VARS, dtype=str)
    x = x[(x.LOC.astype(int) == 0) & (x.MUN.astype(int) != 0)].copy()     # filas de total municipal
    for c in VARS:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x["CVEGEO"] = x.ENTIDAD.str.zfill(2) + x.MUN.str.zfill(3)
    x["PCT_NACOE"] = x.PNACOE / x.POBTOT                 # nacida en otra entidad
    x["PCT_RESOE15"] = x.PRESOE15 / x.P_5YMAS            # vivía en otra entidad en 2015 (migración reciente)
    x["PCT_HLI"] = x.P3YM_HLI / x.P_3YMAS                # habla lengua indígena
    out = x[["CVEGEO", "POBTOT", "PCT_NACOE", "PCT_RESOE15", "PCT_HLI", "GRAPROES"]]
    out.to_parquet(PROC / "censo2020_mun.parquet", index=False)
    print(f"Censo 2020: {len(out)} municipios")
    print(out.describe().round(3).to_string())


if __name__ == "__main__":
    main()
