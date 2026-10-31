"""
03_model.py
Modelo de riesgo de abstención municipal y proyección a la elección intermedia 2027.

Objetivo: DEV_T = abstención municipal en T - abstención de su entidad en T.
El nivel estatal es un choque común a los municipios de cada entidad (concurrencia con
elecciones locales, contexto político) que no se puede inferir de datos territoriales;
el modelo predice la parte intra-estatal, que es estructural y estable, y el nivel
estatal entra como supuesto de escenario (ver 04_scenarios.py).

Modelo híbrido: 1/2 ensamble ML (Ridge + Gradient Boosting) + 1/4 persistencia T-3
+ 1/4 persistencia T-6 (combinación de pronósticos, Bates & Granger 1969).

Sin fuga de información: cada elección T se modela solo con datos publicados antes de T
(rezagos electorales T-3/T-6, edición CONEVAL vigente, rezago espacial de los vecinos en T-3/T-6).

Validación temporal (backtest): se entrena solo con elecciones anteriores a la evaluada.
  - entrenar {2012, 2015, 2018}       -> predecir 2021 (intermedia)
  - entrenar {2012, 2015, 2018, 2021} -> predecir 2024 (presidencial)

Salidas:
  outputs/metricas_backtest.csv, outputs/importancia_variables.csv, outputs/conformal.csv
  data/processed/pred_2027.parquet, data/processed/residuos_backtest.parquet
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUTS = ROOT / "outputs"

ELECTIONS = [2009, 2012, 2015, 2018, 2021, 2024]
MIDTERMS = {2009, 2015, 2021, 2027}
TARGETS = [2012, 2015, 2018, 2021, 2024]
BACKTESTS = [(2021, [2012, 2015, 2018]), (2024, [2012, 2015, 2018, 2021])]
# Edición CONEVAL publicada antes de cada elección (la 2015 salió en 2016 y la 2020 en 2021)
CONEVAL_EDICION = {2012: 2010, 2015: 2010, 2018: 2015, 2021: 2015, 2024: 2020, 2027: 2020}
CONEVAL_VARS = ["IRS", "ANALF", "EDU_BASICA_INC", "SIN_SALUD", "PISO_TIERRA",
                "SIN_AGUA", "SIN_DRENAJE", "SIN_LUZ", "SIN_REFRI"]
BASE_FEATURES = ["DEV1", "DEV2", "DEVMEAN", "DEVJ1", "DEVJ2", "DDEV", "BRECHA_JOV1", "BRECHA_SEXO1",
                 "SH_JOV1", "SH_60M1", "SH_RUR1", "SH_URB1", "SH_NS1", "LOG_LN1", "CREC_LN",
                 "MIDTERM", "MID_X_DEV1", "MID_X_DEV2"]
ESPACIAL_VARS = ["VEC_DEV1", "VEC_DEV2"]
CAT_FEATURES = ["EDOCVE"]
SEED = 42

# Configuración final, elegida con el análisis de robustez (03b_robustez.py)
CONFIG = {"coneval": "edicion", "espacial": True, "pesos": True}


def level(panel: pd.DataFrame, by) -> pd.DataFrame:
    """Abstención agregada (total y jóvenes 18-29) por año y nivel territorial."""
    d = panel.assign(SVJ=panel.PART_JOV.fillna(panel.PART) * panel.LN_JOV)
    g = d.groupby(by)
    return pd.DataFrame({
        "ABST_NIV": g.NV.sum() / (g.SV.sum() + g.NV.sum()),
        "ABST_JOV_NIV": 1 - g.SVJ.sum() / g.LN_JOV.sum(),
    })


def with_dev(panel, est):
    """Desviación de cada municipio respecto a la abstención de su entidad en el mismo año."""
    d = panel.merge(est.reset_index(), on=["AELEC", "EDOCVE"], how="left")
    d["DEV"] = d.ABST - d.ABST_NIV
    d["DEVJ"] = (1 - d.PART_JOV) - d.ABST_JOV_NIV
    return d


def contexto():
    panel = pd.read_parquet(PROC / "panel_municipal.parquet")
    nat = level(panel, "AELEC")
    est = level(panel, ["AELEC", "EDOCVE"])
    return {"panel": with_dev(panel, est), "nat": nat, "est": est,
            "coneval": pd.read_parquet(PROC / "coneval_ediciones.parquet"),
            "vecinos": pd.read_parquet(PROC / "vecinos.parquet")}


def lag_espacial(ctx, y):
    """Promedio de la abstención relativa de los municipios vecinos en y, ponderado por lista nominal."""
    p = ctx["panel"]
    d = p[p.AELEC == y][["EDOCVE", "MPIO24", "DEV", "LN"]].dropna()
    d = d.rename(columns={"EDOCVE": "V_EDOCVE", "MPIO24": "V_MPIO24"})
    m = ctx["vecinos"].merge(d, on=["V_EDOCVE", "V_MPIO24"])
    m["W"] = m.DEV * m.LN
    g = m.groupby(["EDOCVE", "MPIO24"])[["W", "LN"]].sum()
    return g.W / g.LN


def features(cfg):
    f = BASE_FEATURES.copy()
    if cfg["coneval"] != "sin":
        f += CONEVAL_VARS
    if cfg["espacial"]:
        f += ESPACIAL_VARS
    return f


def make_features(ctx, T, cfg=CONFIG):
    """Variables disponibles antes de la elección T."""
    panel = ctx["panel"]

    def lag(y, cols):
        return panel[panel.AELEC == y].set_index(["EDOCVE", "MPIO24"])[cols]

    l1 = lag(T - 3, ["DEV", "DEVJ", "BRECHA_JOV", "BRECHA_SEXO", "SH_JOV", "SH_60M",
                     "SH_RUR", "SH_URB", "SH_NS", "LN"]).add_suffix("1")
    l2 = lag(T - 6, ["DEV", "DEVJ", "LN"]).add_suffix("2")
    X = l1.join(l2, how="left")
    hist = panel[panel.AELEC < T].groupby(["EDOCVE", "MPIO24"])["DEV"].mean().rename("DEVMEAN")
    X = X.join(hist, how="left")
    # 12 municipios sin registros de votación capturados en 2024: se usan con su historial
    X["SIN_DATO_T3"] = X.DEV1.isna().astype(int)
    X["DEV1"] = X.DEV1.fillna(X.DEVMEAN)
    X["DEVMEAN"] = X.DEVMEAN.fillna(X.DEV1)
    X["DEV2"] = X.DEV2.fillna(X.DEV1)            # municipios sin historia T-6
    X["DEVJ2"] = X.DEVJ2.fillna(X.DEVJ1)
    X["DDEV"] = X.DEV1 - X.DEV2
    X["LOG_LN1"] = np.log(X.LN1)
    X["CREC_LN"] = (X.LN1 / X.LN2 - 1).fillna(0).clip(-0.5, 1)
    X["MIDTERM"] = int(T in MIDTERMS)
    X["MID_X_DEV1"] = X.MIDTERM * X.DEV1
    X["MID_X_DEV2"] = X.MIDTERM * X.DEV2
    if cfg["espacial"]:
        X["VEC_DEV1"] = lag_espacial(ctx, T - 3).reindex(X.index).fillna(X.DEV1)
        v2 = lag_espacial(ctx, T - 6) if (T - 6) in ELECTIONS else X.VEC_DEV1
        X["VEC_DEV2"] = v2.reindex(X.index).fillna(X.VEC_DEV1)
    X = X.reset_index()
    if cfg["coneval"] != "sin":
        ed = CONEVAL_EDICION[T] if cfg["coneval"] == "edicion" else 2020
        cn = ctx["coneval"][ctx["coneval"].EDICION == ed][["EDOCVE", "MPIO24"] + CONEVAL_VARS]
        X = X.merge(cn, on=["EDOCVE", "MPIO24"], how="left")
    X["AELEC"] = T
    for c in ["BRECHA_JOV1", "BRECHA_SEXO1", "DEVJ1", "DEVJ2"]:
        X[c] = X[c].fillna(0)
    if T in ELECTIONS:
        y = panel[panel.AELEC == T].set_index(["EDOCVE", "MPIO24"])["DEV"].rename("DEV_T")
        X = X.merge(y.reset_index(), on=["EDOCVE", "MPIO24"], how="left")
    return X


def models(cols):
    pre = ColumnTransformer([
        ("num", StandardScaler(), cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES),
    ])
    ridge = make_pipeline(pre, RidgeCV(alphas=np.logspace(-2, 3, 30)))
    hgb = HistGradientBoostingRegressor(
        max_iter=600, learning_rate=0.04, max_leaf_nodes=31, min_samples_leaf=30,
        l2_regularization=1.0, categorical_features=[len(cols)], random_state=SEED)
    return {"Ridge": ridge, "GBM": hgb}


def fit_models(train, cfg=CONFIG):
    cols = features(cfg)
    w = np.sqrt(train.LN1.values) if cfg["pesos"] else None
    fitted = {}
    for name, m in models(cols).items():
        kw = ({"ridgecv__sample_weight": w} if name == "Ridge" else {"sample_weight": w}) if w is not None else {}
        m.fit(train[cols + CAT_FEATURES], train.DEV_T, **kw)
        fitted[name] = m
    return fitted


def fit_predict(train, test, cfg=CONFIG):
    cols = features(cfg) + CAT_FEATURES
    preds = {name: m.predict(test[cols]) for name, m in fit_models(train, cfg).items()}
    preds["Ensamble"] = (preds["Ridge"] + preds["GBM"]) / 2
    preds["Ingenuo_T-3"] = test.DEV1.values      # persistencia de la elección anterior
    preds["Ingenuo_T-6"] = test.DEV2.values      # persistencia de la elección del mismo tipo
    preds["Ingenuo_promedio"] = test.DEVMEAN.values  # promedio histórico
    preds["Hibrido"] = preds["Ensamble"] / 2 + (preds["Ingenuo_T-3"] + preds["Ingenuo_T-6"]) / 4
    return preds


def metrics(y, p, w, top=0.2):
    k = int(len(y) * top)
    top_true = np.argsort(-y)[:k]
    top_pred = np.argsort(-p)[:k]
    inter = np.intersect1d(top_true, top_pred)
    return {
        "MAE_pp": 100 * np.mean(np.abs(y - p)),
        "MAE_pond_LN_pp": 100 * np.average(np.abs(y - p), weights=w),
        "RMSE_pp": 100 * np.sqrt(np.mean((y - p) ** 2)),
        "R2": 1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2),
        "Spearman": spearmanr(y, p).correlation,
        "Precision_top20": len(inter) / k,
        # Misma métrica en personas: % de la lista nominal del quintil real de riesgo que el modelo identifica
        "Precision_top20_LN": w[inter].sum() / w[top_true].sum(),
    }


def datos(ctx, cfg=CONFIG):
    return {T: make_features(ctx, T, cfg).dropna(subset=["DEV_T", "DEV1"]) for T in TARGETS}


def backtest(data, cfg=CONFIG):
    rows, residuals = [], []
    for test_T, train_Ts in BACKTESTS:
        train = pd.concat([data[t] for t in train_Ts])
        test = data[test_T]
        preds = fit_predict(train, test, cfg)
        for name, p in preds.items():
            rows.append({"Evaluacion": test_T, "Modelo": name, **metrics(test.DEV_T.values, p, test.LN1.values)})
        residuals.append(pd.DataFrame({"AELEC": test_T, "EDOCVE": test.EDOCVE.values, "MPIO24": test.MPIO24.values,
                                       "LN1": test.LN1.values, "PRED": preds["Hibrido"],
                                       "RES": test.DEV_T.values - preds["Hibrido"]}))
    return pd.DataFrame(rows), pd.concat(residuals, ignore_index=True)


def conformal(res, alpha=0.10):
    """Cuantiles conformales por terciles de tamaño (Mondrian) y su cobertura fuera de muestra."""
    edges = np.quantile(res.LN1, [0, 1 / 3, 2 / 3, 1])
    edges[0], edges[-1] = 0, np.inf
    res = res.assign(TAM=pd.cut(res.LN1, edges, labels=False))
    q = lambda r: np.quantile(np.abs(r), 1 - alpha)
    filas = []
    # Validación cruzada temporal: calibrar con una elección y medir cobertura en la otra
    for cal, ev in [(2021, 2024), (2024, 2021)]:
        qc = res[res.AELEC == cal].groupby("TAM").RES.apply(q)
        e = res[res.AELEC == ev]
        cub = (e.RES.abs() <= e.TAM.map(qc)).mean()
        filas.append({"Calibracion": cal, "Evaluacion": ev, "Cobertura_%": 100 * cub,
                      "Semiamplitud_media_pp": 100 * e.TAM.map(qc).mean()})
    val = pd.DataFrame(filas)
    # Los errores dependen del tipo de elección (2021 intermedia: mayores; 2024 presidencial: menores).
    # Como 2027 es intermedia, los intervalos se calibran con los residuos de la intermedia 2021.
    q90 = res[res.AELEC == 2021].groupby("TAM").RES.apply(q)
    return edges, q90, val, res


def importancia(data, cfg=CONFIG):
    """Importancia por permutación fuera de muestra: entrenar hasta 2021, permutar sobre 2024."""
    train = pd.concat([data[t] for t in [2012, 2015, 2018, 2021]])
    test = data[2024]
    cols = features(cfg) + CAT_FEATURES
    imp = []
    fitted = fit_models(train, cfg)
    for name, m in fitted.items():
        pi = permutation_importance(m, test[cols], test.DEV_T, n_repeats=5,
                                    random_state=SEED, scoring="neg_mean_absolute_error")
        imp.append(pd.DataFrame({"Variable": cols, "Modelo": name, "Importancia_MAE_pp": 100 * pi.importances_mean}))
    imp = pd.concat(imp).pivot(index="Variable", columns="Modelo", values="Importancia_MAE_pp")
    ridge = fitted["Ridge"]
    coef = pd.Series(ridge[-1].coef_, index=ridge[0].get_feature_names_out())
    coef = coef[coef.index.str.startswith("num__")].rename(lambda s: s[5:])
    imp["Coef_Ridge_estandarizado_pp"] = 100 * coef
    return imp.sort_values("GBM", ascending=False).round(3)


FAMILIAS = {
    "Historial de abstención": ["DEV1", "DEV2", "DEVMEAN", "DDEV", "MID_X_DEV1", "MID_X_DEV2", "MIDTERM"],
    "Abstención juvenil": ["DEVJ1", "DEVJ2", "BRECHA_JOV1"],
    "Municipios vecinos": ESPACIAL_VARS,
    "Rezago social": CONEVAL_VARS,
    "Estructura de la lista nominal": ["SH_JOV1", "SH_60M1", "LOG_LN1", "CREC_LN"],
    "Urbano / rural": ["SH_RUR1", "SH_URB1"],
    "Brecha de género": ["BRECHA_SEXO1"],
    "Calidad del registro": ["SH_NS1"],
}


def explicar(ridge, X, cfg=CONFIG):
    """Contribución de cada familia de variables a la desviación proyectada (componente lineal, en pp),
    respecto a un municipio promedio de la muestra de entrenamiento (variables estandarizadas)."""
    cols = features(cfg) + CAT_FEATURES
    Xt = ridge[0].transform(X[cols])
    Xt = Xt.toarray() if hasattr(Xt, "toarray") else np.asarray(Xt)
    contrib = pd.DataFrame(Xt * ridge[-1].coef_, columns=ridge[0].get_feature_names_out())
    out = pd.DataFrame(index=X.index)
    for fam, vs in FAMILIAS.items():
        vs = [f"num__{v}" for v in vs if f"num__{v}" in contrib.columns]
        out["EXP_" + fam] = 100 * contrib[vs].sum(axis=1).values
    return out


def main():
    ctx = contexto()
    print("Abstención nacional (%):\n", (100 * ctx["nat"]).round(2))
    ctx["nat"].to_csv(OUTS / "abstencion_nacional.csv")
    ctx["est"].to_csv(OUTS / "abstencion_estatal.csv")
    ctx["panel"].to_parquet(PROC / "panel_municipal_dev.parquet", index=False)

    data = datos(ctx)
    met, res = backtest(data)
    met.round(3).to_csv(OUTS / "metricas_backtest.csv", index=False)
    print(met.round(3).to_string(index=False))

    edges, q90, val, res = conformal(res)
    res.to_parquet(PROC / "residuos_backtest.parquet", index=False)
    pd.DataFrame({"TAM": q90.index, "LN_desde": edges[:-1], "LN_hasta": edges[1:], "Q90_pp": 100 * q90.values}).to_csv(
        OUTS / "conformal.csv", index=False)
    val.round(2).to_csv(OUTS / "conformal_validacion.csv", index=False)
    print("Semiamplitud conformal 90% (pp) por terciles de tamaño:", (100 * q90).round(2).to_dict())
    print("Cobertura fuera de muestra:\n", val.round(2).to_string(index=False))

    # --- Modelo final y proyección 2027 ---
    train = pd.concat(data.values())
    X27 = make_features(ctx, 2027)
    X27 = X27.rename(columns={"SIN_DATO_T3": "SIN_DATO_2024"})
    assert X27[features(CONFIG)].notna().all().all(), X27[features(CONFIG)].isna().sum()[lambda s: s > 0]
    preds = fit_predict(train, X27)
    X27["DEV_2027"] = preds["Hibrido"]
    X27["DEV_RIDGE"], X27["DEV_GBM"] = preds["Ridge"], preds["GBM"]
    X27["TAM"] = pd.cut(X27.LN1, edges, labels=False)
    X27["Q90"] = X27.TAM.map(q90)
    X27 = X27.join(explicar(fit_models(train)["Ridge"], X27))
    X27.to_parquet(PROC / "pred_2027.parquet", index=False)

    imp = importancia(data)
    imp.to_csv(OUTS / "importancia_variables.csv")
    print(imp.head(15).to_string())
    print("Municipios proyectados 2027:", len(X27))


if __name__ == "__main__":
    main()
