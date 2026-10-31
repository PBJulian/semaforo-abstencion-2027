"""
06_maps.py
Mapa de escenarios: tablero interactivo que compara la situación sin intervención y con
intervención (focalizada o uniforme), con efecto y presupuesto ajustables.

La simulación corre en el navegador con las mismas fórmulas que 04_scenarios.py; la
verificación está en verificar_tablero() (las cifras por defecto deben coincidir con E1).

Busca el shapefile de municipios del Marco Geoestadístico INEGI en data/raw/geo
(cualquier archivo cuyo nombre termine en 'mun.shp', p.ej. 00mun.shp) y lo une por CVEGEO.

Salidas:
  entregables/mapa_escenarios_2027.html          (tablero autocontenido: Leaflet 1.9.4 incrustado; solo el mapa
                                                  base de fondo requiere internet)
  entregables/geo/riesgo_abstencion_2027.geojson
  entregables/geo/riesgo_abstencion_2027.gpkg
"""
import json
import sys
from importlib import import_module
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GEO_RAW = ROOT / "data" / "raw" / "geo"
PROC = ROOT / "data" / "processed"
OUTS = ROOT / "outputs"
ENT = ROOT / "entregables"
TEMPLATE = Path(__file__).resolve().parent / "tablero_template.html"
VENDOR = Path(__file__).resolve().parent / "vendor"
LEAFLET_CSS = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">'
LEAFLET_JS = '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>'
sys.path.insert(0, str(Path(__file__).resolve().parent))

ESTADOS = import_module("05_export_figures").ESTADOS
ANIOS = [2009, 2012, 2015, 2018, 2021, 2024]


def find_shapefile():
    cands = sorted(GEO_RAW.rglob("*mun.shp")) + sorted(GEO_RAW.rglob("*mun*.gpkg"))
    if not cands:
        sys.exit(f"No se encontró el shapefile de municipios (*mun.shp) en {GEO_RAW}")
    return cands[0]


def load_geo():
    g = gpd.read_file(find_shapefile()).to_crs(4326)
    if "CVEGEO" not in g.columns:
        g["CVEGEO"] = g["CVE_ENT"].astype(str).str.zfill(2) + g["CVE_MUN"].astype(str).str.zfill(3)
    return g[["CVEGEO", "NOMGEO", "geometry"]]


def capas_sig(d, g):
    cols = ["CVEGEO", "EDOCVE", "MPIO24", "NOM24", "LN_27", "ABST_2021", "ABST_E0", "ABST_E0_LI90", "ABST_E0_LS90",
            "PROB_ROJO", "SEMAFORO_E0", "ABST_E1", "SEMAFORO_E1", "VOTOS_REC_E1", "INTERVENIDO_E1",
            "ABST_E2", "SEMAFORO_E2", "VOTOS_REC_E2"]
    x = d[cols].copy()
    for c in ["SEMAFORO_E0", "SEMAFORO_E1", "SEMAFORO_E2"]:
        x[c] = x[c].astype(str)
    x = x.dropna(subset=["CVEGEO"])
    out = g.assign(geometry=g.geometry.simplify(0.002, preserve_topology=True)).merge(x, on="CVEGEO", how="left")
    print(f"Capas SIG: {len(out)} polígonos, {out.NOM24.notna().sum()} con datos")
    (ENT / "geo").mkdir(parents=True, exist_ok=True)
    out.to_file(ENT / "geo" / "riesgo_abstencion_2027.gpkg", driver="GPKG")
    out.to_file(ENT / "geo" / "riesgo_abstencion_2027.geojson", driver="GeoJSON")


def datos_tablero(d, g):
    panel = pd.read_parquet(PROC / "panel_municipal_dev.parquet")
    hist = panel.pivot_table(index=["EDOCVE", "MPIO24"], columns="AELEC", values="ABST").reindex(columns=ANIOS)
    d = d.sort_values(["EDOCVE", "MPIO24"]).reset_index(drop=True)
    h = hist.reindex(pd.MultiIndex.from_frame(d[["EDOCVE", "MPIO24"]]))
    # Nombre oficial del INEGI cuando hay cruce (la fuente del INE trae errores de captura, p.ej. "Hopelche}én")
    nombre = d.CVEGEO.map(g.set_index("CVEGEO").NOMGEO).fillna(d.NOM24)
    umb = pd.read_csv(OUTS / "umbrales_semaforo.csv")
    r4 = lambda s: [None if pd.isna(v) else round(float(v), 4) for v in s]
    acc = pd.read_parquet(PROC / "acciones_2027.parquet")
    d = d.merge(acc, on=["EDOCVE", "MPIO24"], how="left")
    exp = [c for c in d.columns if c.startswith("EXP_")]
    acciones = ["Monitoreo ordinario", "Vigilancia y acciones de bajo costo", "Enfoque intercultural",
                "Actualización de domicilio y campaña digital", "Retención del voto juvenil (20-29)",
                "Movilización general con el OPL"]
    D = {
        "nom": nombre.tolist(), "edo": d.EDOCVE.astype(int).tolist(),
        "ln": d.LN_27.astype(int).tolist(), "lnj": r4(d.LN_JOV_27), "shj": r4(d.SH_JOV_27),
        "a0": r4(d.ABST_E0), "li": r4(d.ABST_E0_LI90), "ls": r4(d.ABST_E0_LS90), "pr": r4(d.PROB_ROJO),
        "aj": r4(d.ABST_JOV_E0), "a21": r4(d.ABST_2021),
        "hist": [r4(row) for row in h.values],
        "anios": ANIOS,
        "cortes": (umb["Desde_%"].values[1:] / 100).round(4).tolist(),
        "efecto_base": 0.05,
        "pres_e1": round(float((d.LN_JOV_27 * d.INTERVENIDO_E1).sum() / d.LN_JOV_27.sum()), 6),
        "edos": {int(k): v for k, v in ESTADOS.items()},
        "acciones": acciones, "acc": d.ACCION.map({a: k for k, a in enumerate(acciones)}).fillna(0).astype(int).tolist(),
        "mh": d.MARCA_HOMBRES_JOVENES.fillna(0).astype(int).tolist(),
        "fams": [c[4:] for c in exp], "exp": [[round(float(v), 2) for v in row] for row in d[exp].fillna(0).values],
        "nacoe": r4(d.PCT_NACOE), "resoe": r4(d.PCT_RESOE15), "hli": r4(d.PCT_HLI),
    }
    D.update(distritos(nombre, d))
    idx = dict(zip(d.CVEGEO, d.index))
    geo = g[g.CVEGEO.isin(idx)].copy()
    geo["i"] = geo.CVEGEO.map(idx).astype(int)
    geo["geometry"] = geo.geometry.simplify(0.006, preserve_topology=True).set_precision(1e-3)
    geo = geo[~geo.geometry.is_empty]
    return D, json.loads(geo[["i", "geometry"]].to_json(drop_id=True)), d


def distritos(nombre, d):
    """Vista por distrito federal (marco 2023): resumen y 12 secciones prioritarias por distrito."""
    dist = pd.read_parquet(PROC / "distritos_2027.parquet").sort_values(["EDOCVE", "DEF"]).reset_index(drop=True)
    sec = pd.read_parquet(PROC / "secciones_2027.parquet")
    nom = dict(zip(zip(d.EDOCVE, d.MPIO24), nombre))
    sec["MUN"] = [nom.get(k, "") for k in zip(sec.EDOCVE, sec.MPIO24)]
    top = sec[sec.PRIORIDAD_EN_DISTRITO <= 12].sort_values(["EDOCVE", "DEF", "PRIORIDAD_EN_DISTRITO"])
    tops = {k: [[int(r.SECCION), r.MUN, r.TIPOSEC, int(r.LN_J), round(float(r.ABST_J_2027), 3), int(round(r.JOV_ABST_ESP)),
                 int(r.NIVEL_2027)] for r in g.itertuples()] for k, g in top.groupby(["EDOCVE", "DEF"])}
    return {"dist": {
        "edo": dist.EDOCVE.astype(int).tolist(), "def": dist.DEF.astype(int).tolist(), "ln": dist.LN.astype(int).tolist(),
        "abst": [round(float(v), 4) for v in dist.ABST_2027], "niv": dist.NIVEL_2027.astype(int).tolist(),
        "jab": dist.JOV_ABST_ESP.round().astype(int).tolist(), "sec": dist.SECCIONES.astype(int).tolist(),
        "secr": dist.SECCIONES_ROJAS.astype(int).tolist(), "mitad": dist.SECC_MITAD_JOV_ABST.astype(int).tolist(),
        "muns": dist.MUNICIPIOS.tolist(),
        "top": [tops.get((e, f), []) for e, f in zip(dist.EDOCVE, dist.DEF)],
    }}


def verificar_tablero(D, d):
    """Replica en Python la simulación del tablero con los valores por defecto y la compara con E1 de 04_scenarios.py."""
    n = len(D["a0"])
    a0, lnj, shj, aj = (np.array(D[k], dtype=float) for k in ["a0", "lnj", "shj", "aj"])
    orden = np.argsort(-a0, kind="stable")
    rest = D["pres_e1"] * lnj.sum() - np.concatenate([[0], np.cumsum(lnj[orden])[:-1]])
    cob = np.empty(n)
    cob[orden] = np.clip(rest / np.maximum(lnj[orden], 1), 0, 1)
    ej = np.minimum(D["efecto_base"] * cob, aj)
    a = a0 - ej * shj
    rojo = int((a >= D["cortes"][2]).sum())
    esperado = int((d.SEMAFORO_E1 == "Rojo").sum())
    votos = (ej * lnj).sum()
    print(f"Verificación tablero vs pipeline: rojos {rojo} vs {esperado}; votos {votos:,.0f} vs {d.VOTOS_REC_E1.sum():,.0f}")
    assert abs(rojo - esperado) <= 1 and abs(votos - d.VOTOS_REC_E1.sum()) / d.VOTOS_REC_E1.sum() < 0.002


def build():
    d = pd.read_parquet(PROC / "escenarios_2027.parquet")
    g = load_geo()
    capas_sig(d, g)
    D, GEO, d = datos_tablero(d, g)
    verificar_tablero(D, d)
    html = TEMPLATE.read_text(encoding="utf-8")
    # Leaflet incrustado para que el tablero funcione sin conexión (si existe la copia local)
    if (VENDOR / "leaflet.min.js").exists():
        html = html.replace(LEAFLET_CSS, "<style>" + (VENDOR / "leaflet.min.css").read_text(encoding="utf-8") + "</style>")
        html = html.replace(LEAFLET_JS, "<script>" + (VENDOR / "leaflet.min.js").read_text(encoding="utf-8") + "</script>")
    html = html.replace("/*__DATA__*/null", json.dumps(D, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("/*__GEO__*/null", json.dumps(GEO, separators=(",", ":")))
    out = ENT / "mapa_escenarios_2027.html"
    out.write_text(html, encoding="utf-8")
    print("Tablero:", out, f"{out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    build()
