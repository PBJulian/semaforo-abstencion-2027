"""
04c_operativo.py
Del semáforo municipal a la operación: proyección 2027 por sección electoral y por distrito federal
(marco distrital 2023, vigente para 2027), y lista de secciones prioritarias para cada Junta Distrital.

Abstención 2027 de la sección s del municipio m:
  ABST_s = ABST_E0(m) + desviación persistente de s dentro de m
donde la desviación es el promedio de 2021 y 2024 (abstención de la sección menos la de su municipio),
contraída hacia cero en secciones pequeñas (LN / (LN + K), K elegido validando con 2024) y recentrada para
que el promedio ponderado de las secciones reproduzca la proyección municipal. Igual para jóvenes.

Prioridad para una campaña juvenil: jóvenes que se abstendrían = LN 18-29 (2024) x abstención juvenil proyectada.

Salidas:
  entregables/base_datos/secciones_2027.csv, entregables/base_datos/distritos_2027.csv
  outputs/validacion_secciones.csv
  data/processed/secciones_2027.parquet, data/processed/distritos_2027.parquet, data/processed/acciones_2027.parquet

Matriz de acción (municipios rojos y naranjas), reglas transparentes en orden de prioridad:
  1. ≥ 40% de la población habla una lengua indígena (Censo 2020)  -> enfoque intercultural
  2. alta movilidad: nacida en otra entidad ≥ nivel nacional o ≥ 4% vivía en otra entidad en 2015
                                                                   -> actualización de domicilio y campaña digital
  3. brecha juvenil ≥ mediana de los municipios en riesgo          -> retención del voto juvenil (20-29)
  4. resto                                                         -> movilización general con el OPL
  Marca adicional: brecha mujeres-hombres en el cuartil superior    -> + mensajes para hombres jóvenes
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUTS = ROOT / "outputs"
BD = ROOT / "entregables" / "base_datos"
YOUTH = ["18-19", "20-24", "25-29"]
K_GRID = [0, 100, 250, 500, 1000, 2000]


def secciones(sec):
    """Abstención total y juvenil por sección y año (secciones identificadas por entidad + número)."""
    sec = sec.assign(JOV=sec.GEDAD.isin(YOUTH))
    k = ["AELEC", "EDOCVE", "SECCION"]
    t = sec.groupby(k)[["LN", "SV", "NV"]].sum()
    j = sec[sec.JOV].groupby(k)[["LN", "SV", "NV"]].sum().add_suffix("_J")
    s = t.join(j).fillna(0).reset_index()
    s["ABST"] = s.NV / (s.SV + s.NV).replace(0, np.nan)
    s["ABST_J"] = s.NV_J / (s.SV_J + s.NV_J).replace(0, np.nan)
    return s


def desviaciones(s, marco):
    """Desviación de cada sección respecto a su municipio (marco 2024) en cada año."""
    s = s.merge(marco[["EDOCVE", "SECCION", "MPIO24"]], on=["EDOCVE", "SECCION"], how="inner")
    g = s.groupby(["AELEC", "EDOCVE", "MPIO24"])[["SV", "NV", "SV_J", "NV_J"]].sum()
    g["ABST_M"] = g.NV / (g.SV + g.NV)
    g["ABST_J_M"] = g.NV_J / (g.SV_J + g.NV_J)
    s = s.merge(g[["ABST_M", "ABST_J_M"]].reset_index(), on=["AELEC", "EDOCVE", "MPIO24"])
    s["DEV_S"] = s.ABST - s.ABST_M
    s["DEV_SJ"] = s.ABST_J - s.ABST_J_M
    return s


def contraer(dev, ln, K):
    return dev * ln / (ln + K) if K else dev


def validar(dv):
    """Elegir K: predecir la desviación seccional de 2024 con el promedio de 2018 y 2021."""
    w = dv.pivot_table(index=["EDOCVE", "SECCION"], columns="AELEC", values=["DEV_S", "LN"])
    w = w.dropna(subset=[("DEV_S", 2018), ("DEV_S", 2021), ("DEV_S", 2024)])
    y, ln = w[("DEV_S", 2024)], w[("LN", 2024)]
    filas = [{"K": "Sin desviación (todas iguales al municipio)", "MAE_pond_pp": 100 * np.average(y.abs(), weights=ln),
              "Correlacion": np.nan}]
    for K in K_GRID:
        p = (contraer(w[("DEV_S", 2018)], w[("LN", 2018)], K) + contraer(w[("DEV_S", 2021)], w[("LN", 2021)], K)) / 2
        filas.append({"K": K, "MAE_pond_pp": 100 * np.average((y - p).abs(), weights=ln), "Correlacion": np.corrcoef(y, p)[0, 1]})
    v = pd.DataFrame(filas)
    v["Secciones"] = len(w)
    print(v.round(3).to_string(index=False))
    best = v.iloc[1:].sort_values("MAE_pond_pp").K.iloc[0]
    return int(best), v


def recentrar(df, col, w):
    m = df.groupby(["EDOCVE", "MPIO24"]).apply(lambda g: np.average(g[col], weights=g[w]) if g[w].sum() else 0)
    return df[col] - pd.MultiIndex.from_frame(df[["EDOCVE", "MPIO24"]]).map(m).values


ACCIONES = ["Enfoque intercultural", "Actualización de domicilio y campaña digital",
            "Retención del voto juvenil (20-29)", "Movilización general con el OPL"]


def matriz_accion():
    d = pd.read_parquet(PROC / "escenarios_2027.parquet")
    censo = pd.read_parquet(PROC / "censo2020_mun.parquet")
    panel = pd.read_parquet(PROC / "panel_municipal_dev.parquet")
    sexo = panel[panel.AELEC == 2024][["EDOCVE", "MPIO24", "BRECHA_SEXO"]]
    d = d.merge(censo, on="CVEGEO", how="left").merge(sexo, on=["EDOCVE", "MPIO24"], how="left")
    w = d.POBTOT.fillna(0)
    nacoe_nal = np.average(d.PCT_NACOE.fillna(0), weights=w)
    riesgo = d.NIVEL_E0 >= 2
    br_med = d.BRECHA_JOV_27[riesgo].median()
    sx_p75 = d.BRECHA_SEXO.quantile(0.75)
    regla = np.select(
        [d.PCT_HLI >= 0.40, (d.PCT_NACOE >= nacoe_nal) | (d.PCT_RESOE15 >= 0.04), d.BRECHA_JOV_27 >= br_med],
        ACCIONES[:3], ACCIONES[3])
    d["ACCION"] = np.where(riesgo, regla, np.where(d.NIVEL_E0 == 1, "Vigilancia y acciones de bajo costo", "Monitoreo ordinario"))
    d["MARCA_HOMBRES_JOVENES"] = (riesgo & (d.BRECHA_SEXO >= sx_p75)).astype(int)
    a = d[["EDOCVE", "MPIO24", "ACCION", "MARCA_HOMBRES_JOVENES", "PCT_NACOE", "PCT_RESOE15", "PCT_HLI", "GRAPROES"]]
    a.to_parquet(PROC / "acciones_2027.parquet", index=False)
    t = d[riesgo].groupby("ACCION").agg(Municipios=("NOM24", "size"), Electores_mill=("LN_27", lambda x: x.sum() / 1e6),
                                         Rojos=("NIVEL_E0", lambda x: int((x == 3).sum())))
    t.round(2).to_csv(OUTS / "matriz_accion.csv")
    print(f"Umbrales: nacida en otra entidad ≥ {100 * nacoe_nal:.1f}% (nacional) o ≥ 4% reciente; brecha juvenil ≥ {100 * br_med:.1f} pp")
    print(t.round(2).to_string())


def main():
    matriz_accion()
    sec = pd.read_parquet(PROC / "ccpc_seccion.parquet",
                          columns=["AELEC", "EDOCVE", "MPIOCVE", "SECCION", "TIPOSEC", "DEF", "SEXO", "GEDAD", "LN", "SV", "NV"])
    sec = sec[sec.AELEC.isin([2018, 2021, 2024])]
    # Marco 2024: municipio (clave INE 2024), distrito federal (marco 2023, vigente en 2027) y tipo de sección
    marco = (sec[sec.AELEC == 2024].groupby(["EDOCVE", "SECCION"])
             .agg(MPIO24=("MPIOCVE", "first"), DEF=("DEF", "first"), TIPOSEC=("TIPOSEC", "first")).reset_index())
    marco["DEF"] = marco.DEF.astype(int)
    s = secciones(sec)
    dv = desviaciones(s, marco)

    K, val = validar(dv)
    val.round(4).to_csv(OUTS / "validacion_secciones.csv", index=False)
    print("K elegido:", K)

    w = dv[dv.AELEC.isin([2021, 2024])].copy()
    w["DEV_C"] = contraer(w.DEV_S.fillna(0), w.LN, K)
    w["DEV_JC"] = contraer(w.DEV_SJ.fillna(0), w.LN_J, K)
    p = w.groupby(["EDOCVE", "SECCION"])[["DEV_C", "DEV_JC"]].mean().reset_index()
    s24 = s[s.AELEC == 2024][["EDOCVE", "SECCION", "LN", "LN_J", "ABST", "ABST_J"]].rename(
        columns={"ABST": "ABST_2024", "ABST_J": "ABST_J_2024"})
    out = marco.merge(s24, on=["EDOCVE", "SECCION"], how="left").merge(p, on=["EDOCVE", "SECCION"], how="left")
    out[["DEV_C", "DEV_JC"]] = out[["DEV_C", "DEV_JC"]].fillna(0)

    mun = pd.read_parquet(PROC / "escenarios_2027.parquet")[["EDOCVE", "MPIO24", "NOM24", "ABST_E0", "ABST_JOV_E0", "SEMAFORO_E0", "NIVEL_E0"]]
    out = out.merge(mun, on=["EDOCVE", "MPIO24"], how="left")
    out["DEV_C"] = recentrar(out, "DEV_C", "LN")
    out["DEV_JC"] = recentrar(out, "DEV_JC", "LN_J")
    out["ABST_2027"] = (out.ABST_E0 + out.DEV_C).clip(0.02, 0.98)
    out["ABST_J_2027"] = (out.ABST_JOV_E0 + out.DEV_JC).clip(0.02, 0.98)
    out["JOV_ABST_ESP"] = out.LN_J * out.ABST_J_2027        # jóvenes que se abstendrían
    cortes = pd.read_csv(OUTS / "umbrales_semaforo.csv")["Desde_%"].values[1:] / 100
    out["NIVEL_2027"] = np.digitize(out.ABST_2027, cortes)
    out["SEMAFORO_2027"] = pd.Categorical.from_codes(out.NIVEL_2027, ["Verde", "Amarillo", "Naranja", "Rojo"])
    out["PRIORIDAD_EN_DISTRITO"] = out.groupby(["EDOCVE", "DEF"]).JOV_ABST_ESP.rank(ascending=False, method="first").astype(int)
    out.to_parquet(PROC / "secciones_2027.parquet", index=False)

    # Distritos federales
    g = out.assign(W=out.ABST_2027 * out.LN, WJ=out.ABST_J_2027 * out.LN_J).groupby(["EDOCVE", "DEF"])
    dist = pd.DataFrame({
        "LN": g.LN.sum(), "LN_JOV": g.LN_J.sum(), "SECCIONES": g.size(),
        "ABST_2027": g.W.sum() / g.LN.sum(), "ABST_JOV_2027": g.WJ.sum() / g.LN_J.sum(),
        "JOV_ABST_ESP": g.JOV_ABST_ESP.sum(),
        "SECCIONES_ROJAS": g.NIVEL_2027.apply(lambda x: int((x == 3).sum())),
        "MUNICIPIOS": g.NOM24.apply(lambda x: ", ".join(x.value_counts().index[:4])),
    }).reset_index()
    dist["NIVEL_2027"] = np.digitize(dist.ABST_2027, cortes)
    dist["SEMAFORO_2027"] = pd.Categorical.from_codes(dist.NIVEL_2027, ["Verde", "Amarillo", "Naranja", "Rojo"])
    # Concentración: cuántas secciones reúnen la mitad de los jóvenes abstencionistas esperados del distrito
    def mitad(x):
        v = np.sort(x.values)[::-1]
        return int(np.searchsorted(np.cumsum(v), v.sum() / 2) + 1)
    dist["SECC_MITAD_JOV_ABST"] = g.JOV_ABST_ESP.apply(mitad).values
    dist.to_parquet(PROC / "distritos_2027.parquet", index=False)

    BD.mkdir(parents=True, exist_ok=True)
    cols = ["EDOCVE", "DEF", "MPIO24", "NOM24", "SECCION", "TIPOSEC", "LN", "LN_J", "ABST_2024", "ABST_2027",
            "ABST_J_2027", "JOV_ABST_ESP", "SEMAFORO_2027", "PRIORIDAD_EN_DISTRITO"]
    out[cols].rename(columns={"LN": "LN_2024", "LN_J": "LN_18_29", "DEF": "DISTRITO_FEDERAL", "NOM24": "MUNICIPIO"}).sort_values(
        ["EDOCVE", "DISTRITO_FEDERAL", "PRIORIDAD_EN_DISTRITO"]).round(4).to_csv(BD / "secciones_2027.csv", index=False, encoding="utf-8-sig")
    dist.rename(columns={"DEF": "DISTRITO_FEDERAL"}).round(4).to_csv(BD / "distritos_2027.csv", index=False, encoding="utf-8-sig")

    print(f"Secciones: {len(out):,}; distritos: {len(dist)}")
    print("Distritos por color:", dist.SEMAFORO_2027.value_counts().to_dict())
    print("Secciones por color:", out.SEMAFORO_2027.value_counts().to_dict())
    print("Mediana de secciones que concentran la mitad de los jóvenes abstencionistas esperados por distrito:",
          dist.SECC_MITAD_JOV_ABST.median(), "de", dist.SECCIONES.median())
    chk = out.groupby(["EDOCVE", "MPIO24"]).apply(lambda x: np.average(x.ABST_2027, weights=x.LN)) - \
          out.groupby(["EDOCVE", "MPIO24"]).ABST_E0.first()
    print("Consistencia sección→municipio (máx. diferencia, pp):", round(100 * chk.abs().max(), 3))


if __name__ == "__main__":
    main()
