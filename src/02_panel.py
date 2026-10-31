"""
02_panel.py
Construye el panel municipio x elección (2009-2024) en el marco geográfico 2024.

Las claves municipales del INE cambian entre años (municipios nuevos, reasignaciones),
así que cada sección histórica se asigna al municipio al que pertenece en 2024.
Si la sección ya no existe en 2024, se usa el nombre del municipio en ese año.

Además cruza los indicadores de rezago social CONEVAL (clave INEGI) por nombre. Se cruzan las
tres ediciones (2010, 2015, 2020) para que cada elección se modele solo con la edición que ya
estaba publicada antes de ella (sin fuga de información del futuro).

Salidas:
  data/processed/panel_municipal.parquet    (municipio x elección)
  data/processed/municipios_2024.parquet    (catálogo + CONEVAL 2020)
  data/processed/coneval_ediciones.parquet  (municipio x edición CONEVAL 2010/2015/2020)
  data/processed/vecinos.parquet            (pares de municipios colindantes, Marco Geoestadístico INEGI)
"""
import re
from difflib import get_close_matches
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from unidecode import unidecode

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
GEO = ROOT / "data" / "raw" / "geo"
CONEVAL = ROOT / "data" / "raw" / "coneval" / "IRS_entidades_mpios_{}.xlsx"
IND = ["POB", "ANALF", "NO_ESC_6_14", "EDU_BASICA_INC", "SIN_SALUD", "PISO_TIERRA",
       "SIN_EXCUSADO", "SIN_AGUA", "SIN_DRENAJE", "SIN_LUZ", "SIN_LAVADORA", "SIN_REFRI", "IRS"]

MIDTERM = {2009: 1, 2012: 0, 2015: 1, 2018: 0, 2021: 1, 2024: 0}
YOUTH = ["18-19", "20-24", "25-29"]


def norm(s: str) -> str:
    s = unidecode(str(s)).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\bdr\b", "doctor", s)
    s = re.sub(r"\bgral\b", "general", s)
    s = re.sub(r"\b(de|del|la|las|los|el|y|heroica|ciudad)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def assign_marco_2024(df: pd.DataFrame) -> pd.DataFrame:
    ref = (df[df.AELEC == 2024]
           .groupby(["EDOCVE", "SECCION"])["MPIOCVE"].agg(lambda s: s.mode().iat[0])
           .rename("MPIO24").reset_index())
    names24 = (df[df.AELEC == 2024].groupby(["EDOCVE", "MPIOCVE"])["MPIONOM"].first()
               .reset_index().rename(columns={"MPIOCVE": "MPIO24", "MPIONOM": "NOM24"}))
    names24["KEY"] = names24["NOM24"].map(norm)

    df = df.merge(ref, on=["EDOCVE", "SECCION"], how="left")

    # Respaldo por nombre para secciones que desaparecieron
    miss = df["MPIO24"].isna()
    fb = df.loc[miss, ["EDOCVE", "MPIONOM"]].drop_duplicates()
    fb["KEY"] = fb["MPIONOM"].map(norm)
    fb = fb.merge(names24[["EDOCVE", "KEY", "MPIO24"]].drop_duplicates(["EDOCVE", "KEY"]),
                  on=["EDOCVE", "KEY"], how="left")
    fb_map = fb.set_index(["EDOCVE", "MPIONOM"])["MPIO24"]
    fb_map = fb_map[~fb_map.index.duplicated()]
    df.loc[miss, "MPIO24"] = pd.MultiIndex.from_frame(df.loc[miss, ["EDOCVE", "MPIONOM"]]).map(fb_map)

    cov = df.groupby("AELEC").apply(lambda d: d.loc[d.MPIO24.notna(), "LN"].sum() / d.LN.sum())
    print("Cobertura de LN asignada al marco 2024:", (100 * cov).round(2).to_dict())
    df = df[df.MPIO24.notna()].copy()
    df["MPIO24"] = df["MPIO24"].astype(int)
    return df, names24


def rate(sv, nv):
    return np.where((sv + nv) > 0, sv / (sv + nv), np.nan)


def build_panel(df: pd.DataFrame) -> pd.DataFrame:
    k = ["AELEC", "EDOCVE", "MPIO24"]
    cols = ["LN", "SV", "NV", "NS"]
    tot = df.groupby(k)[cols].sum()

    def part_of(mask, suffix):
        g = df[mask].groupby(k)[cols].sum()
        return pd.DataFrame({f"PART_{suffix}": rate(g.SV, g.NV), f"LN_{suffix}": g.LN}, index=g.index)

    p = tot.copy()
    p["PART"] = rate(p.SV, p.NV)
    p["ABST"] = 1 - p["PART"]
    p = p.join(part_of(df.GEDAD.isin(YOUTH), "JOV"))
    p = p.join(part_of(df.GEDAD == "18-19", "1819"))
    p = p.join(part_of(df.GEDAD == "60+", "60M"))
    p = p.join(part_of(df.SEXO == 1, "MUJ"))
    p = p.join(part_of(df.SEXO == 0, "HOM"))
    p = p.join(part_of(df.TIPOSEC == "R", "RUR"))
    p = p.join(part_of(df.TIPOSEC == "U", "URB"))
    for c in ["LN_JOV", "LN_1819", "LN_60M", "LN_RUR", "LN_URB"]:
        p[c] = p[c].fillna(0)
    p["SH_JOV"] = p.LN_JOV / p.LN
    p["SH_60M"] = p.LN_60M / p.LN
    p["SH_RUR"] = p.LN_RUR / p.LN
    p["SH_URB"] = p.LN_URB / p.LN
    p["SH_NS"] = p.NS / p.LN
    p["BRECHA_JOV"] = p.PART - p.PART_JOV          # cuánto menos votan los jóvenes
    p["BRECHA_SEXO"] = p.PART_MUJ - p.PART_HOM
    p = p.drop(columns=["LN_MUJ", "LN_HOM"]).reset_index()
    p["INTERMEDIA"] = p.AELEC.map(MIDTERM)
    return p


def load_coneval(year=2020) -> pd.DataFrame:
    x = pd.read_excel(str(CONEVAL).format(year), sheet_name="Municipios", header=None, skiprows=7,
                      dtype={0: str, 2: str})
    x = x.iloc[:, :19]
    x.columns = ["CVE_ENT", "ENTIDAD", "CVEGEO", "MUNICIPIO", "POB",
                 "ANALF", "NO_ESC_6_14", "EDU_BASICA_INC", "SIN_SALUD", "PISO_TIERRA",
                 "SIN_EXCUSADO", "SIN_AGUA", "SIN_DRENAJE", "SIN_LUZ", "SIN_LAVADORA",
                 "SIN_REFRI", "IRS", "GRADO_RS", "LUGAR_RS"]
    x = x[x.CVEGEO.str.fullmatch(r"\d{5}", na=False)].copy()
    x["EDOCVE"] = x.CVE_ENT.astype(int)
    for c in x.columns[4:17]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x["KEY"] = x.MUNICIPIO.map(norm)
    return x


def match_coneval(names24: pd.DataFrame, cn: pd.DataFrame, verbose=True) -> pd.DataFrame:
    out = []
    for edo, g in names24.groupby("EDOCVE"):
        c = cn[cn.EDOCVE == edo]
        keys = dict(zip(c.KEY, c.CVEGEO))
        # Nombres repetidos dentro de una entidad (ej. dos "San Juan Mixtepec" en Oaxaca):
        # se emparejan en orden de clave, que INE e INEGI comparten dentro de la entidad
        dup = {k: sorted(v) for k, v in c.groupby("KEY").CVEGEO if len(v) > 1}
        for _, r in g.sort_values("MPIO24").iterrows():
            cve = dup[r.KEY].pop(0) if dup.get(r.KEY) else keys.get(r.KEY)
            how = "exacto"
            if cve is None:
                # Un nombre contiene al otro (ej. "Jonacatepec" / "Jonacatepec de Leandro Valle")
                cont = [k for k in keys if k and (r.KEY in k or k in r.KEY)]
                if cont:
                    cve, how = keys[max(cont, key=len)], "subcadena"
            if cve is None:
                m = get_close_matches(r.KEY, list(keys), n=1, cutoff=0.85)
                cve, how = (keys[m[0]], "difuso") if m else (None, "sin_match")
            out.append((edo, r.MPIO24, r.NOM24, cve, how))
    m = pd.DataFrame(out, columns=["EDOCVE", "MPIO24", "NOM24", "CVEGEO", "MATCH"])
    print("Cruce INE-CONEVAL:", m.MATCH.value_counts().to_dict())
    if verbose:
        print(m[m.MATCH != "exacto"].merge(cn[["CVEGEO", "MUNICIPIO"]], on="CVEGEO", how="left")
            [["EDOCVE", "NOM24", "MUNICIPIO", "MATCH"]].to_string())
    return m


def build_vecinos(cat: pd.DataFrame) -> pd.DataFrame:
    """Pares de municipios que comparten frontera (contigüidad tipo reina)."""
    shp = sorted(GEO.rglob("*mun.shp"))
    if not shp:
        print("Sin shapefile de municipios: se omite la matriz de vecindad")
        return pd.DataFrame(columns=["EDOCVE", "MPIO24", "V_EDOCVE", "V_MPIO24"])
    g = gpd.read_file(shp[0])[["CVEGEO", "geometry"]]
    g["geometry"] = g.geometry.simplify(50).buffer(10)     # metros; tolera pequeños huecos entre polígonos
    pares = gpd.sjoin(g, g, predicate="intersects")
    pares = pares[pares.CVEGEO_left != pares.CVEGEO_right][["CVEGEO_left", "CVEGEO_right"]]
    k = cat.dropna(subset=["CVEGEO"]).set_index("CVEGEO")[["EDOCVE", "MPIO24"]]
    v = (pares.join(k, on="CVEGEO_left").join(k.add_prefix("V_"), on="CVEGEO_right")
         .dropna()[["EDOCVE", "MPIO24", "V_EDOCVE", "V_MPIO24"]].astype(int))
    n = v.groupby(["EDOCVE", "MPIO24"]).size()
    print(f"Vecindad: {len(n)} municipios con vecinos, mediana {n.median():.0f} vecinos")
    return v


def main():
    df = pd.read_parquet(PROC / "ccpc_seccion.parquet")
    df, names24 = assign_marco_2024(df)
    panel = build_panel(df)

    # El cruce por nombre se hace una sola vez contra la edición 2020 (revisado caso por caso);
    # las ediciones 2010 y 2015 se unen por CVEGEO, que INEGI no reasigna entre ediciones.
    m = match_coneval(names24, load_coneval(2020))
    ediciones = []
    for year in [2010, 2015, 2020]:
        cn = load_coneval(year)
        cat = m.merge(cn.drop(columns=["EDOCVE", "KEY"]), on="CVEGEO", how="left")
        print(f"CONEVAL {year}: {cat.IRS.notna().sum()} municipios con dato")
        # Municipios sin dato (creados después de la edición, o sin levantamiento): mediana estatal
        cat["IMPUTADO_CONEVAL"] = cat["IRS"].isna().astype(int)
        for c in IND:
            cat[c] = cat[c].fillna(cat.groupby("EDOCVE")[c].transform("median"))
        cat["EDICION"] = year
        ediciones.append(cat)
    cat = ediciones[-1].rename(columns={"POB": "POB2020"}).drop(columns="EDICION")
    cat.to_parquet(PROC / "municipios_2024.parquet", index=False)
    pd.concat(ediciones)[["EDICION", "EDOCVE", "MPIO24", "IMPUTADO_CONEVAL"] + IND].to_parquet(
        PROC / "coneval_ediciones.parquet", index=False)
    build_vecinos(cat).to_parquet(PROC / "vecinos.parquet", index=False)
    panel.to_parquet(PROC / "panel_municipal.parquet", index=False)

    print(panel.groupby("AELEC")[["PART", "PART_JOV", "PART_60M", "BRECHA_JOV", "SH_JOV"]].median().round(3))
    print("Municipios por año:", panel.groupby("AELEC").size().to_dict())


if __name__ == "__main__":
    main()
