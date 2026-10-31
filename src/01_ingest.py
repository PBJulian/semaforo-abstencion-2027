"""
01_ingest.py
Lee los Conteos Censales de Participación Ciudadana (CCPC) 2009-2024 del INE
(sección x sexo x edad simple) y los agrega a sección x sexo x grupo de edad.

Salida: data/processed/ccpc_seccion.parquet
"""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ccpc"
OUT = ROOT / "data" / "processed"

YEARS = [2009, 2012, 2015, 2018, 2021, 2024]
AGE_BINS = [17, 19, 24, 29, 39, 49, 59, 200]
AGE_LABELS = ["18-19", "20-24", "25-29", "30-39", "40-49", "50-59", "60+"]

DTYPES = {
    "AELEC": "int16", "EDOCVE": "int8", "MPIOCVE": "int16", "MPIONOM": "string",
    "SECCION": "int32", "TIPOSEC": "string", "DEF": "float32", "SEXO": "int8",
    "EDAD": "int16", "LN": "int32", "SV": "int32", "NV": "int32", "NS": "int32",
}


def read_one(path: Path) -> pd.DataFrame:
    # Algunos archivos traen celdas con espacios: se lee todo como texto y se convierte
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df.columns = df.columns.str.strip()
    df = df[list(DTYPES)]
    for col, dt in DTYPES.items():
        if dt == "string":
            df[col] = df[col].str.strip()
        else:
            df[col] = pd.to_numeric(df[col].str.strip(), errors="coerce")
    bad = df[["AELEC", "EDOCVE", "MPIOCVE", "SECCION", "SEXO", "EDAD", "LN"]].isna().any(axis=1)
    if bad.any():
        print(f"{path.name}: {bad.sum()} filas descartadas por claves vacías")
    df = df[~bad]
    df[["SV", "NV", "NS"]] = df[["SV", "NV", "NS"]].fillna(0)
    df["TIPOSEC"] = df["TIPOSEC"].str.strip().str.upper().str[0]
    df["GEDAD"] = pd.cut(df["EDAD"], AGE_BINS, labels=AGE_LABELS)
    keys = ["AELEC", "EDOCVE", "MPIOCVE", "SECCION", "TIPOSEC", "SEXO", "GEDAD"]
    agg = (df.groupby(keys, observed=True, dropna=False)[["LN", "SV", "NV", "NS"]]
             .sum().reset_index())
    # Nombre y distrito del municipio/sección (el más frecuente)
    names = df.groupby(["EDOCVE", "MPIOCVE"])["MPIONOM"].agg(lambda s: s.mode().iat[0])
    agg["MPIONOM"] = pd.MultiIndex.from_frame(agg[["EDOCVE", "MPIOCVE"]]).map(names)
    defs = df.groupby("SECCION")["DEF"].agg(lambda s: s.mode().iat[0] if s.notna().any() else np.nan)
    agg["DEF"] = agg["SECCION"].map(defs)
    return agg


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(f for y in YEARS for f in (RAW / f"DatosAbiertos_DECEyEC_ConteosCensales{y}").glob("*.csv"))
    print(f"{len(files)} archivos")
    with ProcessPoolExecutor() as ex:
        parts = list(ex.map(read_one, files))
    df = pd.concat(parts, ignore_index=True)
    df["GEDAD"] = df["GEDAD"].astype(pd.CategoricalDtype(AGE_LABELS, ordered=True))
    df.to_parquet(OUT / "ccpc_seccion.parquet", index=False)

    tot = df.groupby("AELEC")[["LN", "SV", "NV", "NS"]].sum()
    tot["PART_%"] = (100 * tot.SV / (tot.SV + tot.NV)).round(2)
    tot["NS_%"] = (100 * tot.NS / tot.LN).round(2)
    print(tot)
    print("Secciones por año:", df.groupby("AELEC")[["EDOCVE", "SECCION"]].apply(lambda d: len(d.drop_duplicates())).to_dict())


if __name__ == "__main__":
    main()
