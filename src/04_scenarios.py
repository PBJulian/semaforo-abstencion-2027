"""
04_scenarios.py
Escenarios 2027 y semáforo de riesgo territorial de abstención.

Nivel 2027 = abstención estatal de la última intermedia (2021, concurrente en las 32
entidades) + desviación municipal proyectada por el modelo (03_model.py).

Escenarios:
  E0 Inercial     : sin intervención.
  E1 Focalizado   : campaña de promoción juvenil (18-29) que eleva X pp su participación,
                    solo en municipios en rojo y naranja del escenario inercial.
  E2 Uniforme     : el mismo presupuesto (personas jóvenes alcanzadas) repartido de forma
                    proporcional en todo el país.

Semáforo: umbrales absolutos fijados con la distribución del escenario inercial, de modo que
una intervención sí puede mover a un municipio de color. El color depende solo del nivel
proyectado; el cambio respecto a 2021 se reporta aparte. (Una regla que subía de nivel a los
municipios que "empeoraban" 5 pp se descartó: reflejaba sobre todo regresión a la media de
municipios con una abstención atípicamente baja en 2021, no una tendencia de deterioro.)

Probabilidad de quedar en rojo: empírica, con los residuos del backtest de la intermedia 2021
del mismo tercil de tamaño (03_model.py).

Salidas:
  data/processed/escenarios_2027.parquet
  outputs/resumen_escenarios.csv, outputs/sensibilidad_efecto.csv, outputs/umbrales_semaforo.csv,
  outputs/curva_presupuesto.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUTS = ROOT / "outputs"

EFECTO_BASE = 0.05            # +5 pp de participación juvenil en zonas intervenidas
EFECTOS_SENS = [0.02, 0.035, 0.05, 0.075, 0.10]
PRESUPUESTOS = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.75, 1.00]   # fracción de jóvenes del país alcanzados
COLORES = ["Verde", "Amarillo", "Naranja", "Rojo"]


def umbrales(abst):
    """Cortes absolutos (redondeados a 1 pp) en los percentiles 50, 75 y 90 del inercial."""
    return np.round(np.quantile(abst, [0.50, 0.75, 0.90]), 2)


def semaforo(abst, cortes):
    return np.digitize(abst, cortes)


def prob_superar(d, corte, res):
    """P(abstención real >= corte) con la distribución empírica de residuos del mismo tercil de tamaño."""
    prob = np.zeros(len(d))
    for tam, r in res.groupby("TAM").RES:
        r = np.sort(r.values)
        m = (d.TAM == tam).values
        prob[m] = 1 - np.searchsorted(r, corte - d.ABST_E0.values[m], side="left") / len(r)
    return prob


def proyectar(pred, est, hist):
    d = pred.merge(est.loc[2021, ["ABST_NIV"]].rename(columns={"ABST_NIV": "ABST_EST_2021"}),
                   left_on="EDOCVE", right_index=True, how="left")
    d = d.merge(hist, on=["EDOCVE", "MPIO24"], how="left")
    d["ABST_E0"] = (d.ABST_EST_2021 + d.DEV_2027).clip(0.05, 0.95)
    # Brecha juvenil: cuánto más se abstienen los jóvenes que el total (promedio 2021-2024)
    d["BRECHA_JOV_27"] = d[["BRECHA_JOV_2021", "BRECHA_JOV_2024"]].mean(axis=1).fillna(0)
    d["ABST_JOV_E0"] = (d.ABST_E0 + d.BRECHA_JOV_27).clip(0.05, 0.98)
    d["SH_JOV_27"] = d.SH_JOV1
    d["LN_27"] = d.LN1
    d["LN_JOV_27"] = d.LN_27 * d.SH_JOV_27
    d["CAMBIO_VS_2021"] = d.ABST_E0 - d.ABST_2021
    d["CAMBIO_VS_2021"] = d.CAMBIO_VS_2021.fillna(0)
    # Intervalo conformal 90%
    d["ABST_E0_LI90"] = (d.ABST_E0 - d.Q90).clip(0, 1)
    d["ABST_E0_LS90"] = (d.ABST_E0 + d.Q90).clip(0, 1)
    return d


def intervenir(d, mask, efecto):
    """Aplica +efecto pp de participación juvenil donde mask (fracción 0-1 de cobertura)."""
    efecto_jov = np.minimum(efecto * mask, d.ABST_JOV_E0)
    abst = d.ABST_E0 - efecto_jov * d.SH_JOV_27
    votos = efecto_jov * d.LN_JOV_27
    return abst, votos


def correr(d, cortes, efecto):
    nivel0 = semaforo(d.ABST_E0, cortes)
    foco = (nivel0 >= 2).astype(float)                         # rojo + naranja
    presupuesto = (d.LN_JOV_27 * foco).sum()                   # jóvenes alcanzados en E1
    cobertura = presupuesto / d.LN_JOV_27.sum()                # misma cantidad, repartida
    a1, v1 = intervenir(d, foco, efecto)
    a2, v2 = intervenir(d, np.full(len(d), cobertura), efecto)
    out = {"E0": (d.ABST_E0, np.zeros(len(d))), "E1": (a1, v1), "E2": (a2, v2)}
    res = {k: (a, v, semaforo(a, cortes)) for k, (a, v) in out.items()}
    return res, foco, cobertura


def priorizar(d, presupuesto):
    """Cobertura por municipio al asignar el presupuesto en orden de riesgo (mayor abstención proyectada primero)."""
    orden = np.argsort(-d.ABST_E0.values)
    jov = d.LN_JOV_27.values[orden]
    restante = presupuesto * jov.sum() - np.concatenate([[0], np.cumsum(jov)[:-1]])
    cob = np.clip(restante / np.maximum(jov, 1), 0, 1)
    out = np.empty(len(d))
    out[orden] = cob
    return out


def curva_presupuesto(d, cortes, efecto):
    """Priorizado por riesgo vs uniforme, para distintos tamaños de presupuesto."""
    riesgo = semaforo(d.ABST_E0, cortes) >= 2
    filas = []
    for b in PRESUPUESTOS:
        for nombre, cob in [("Priorizado", priorizar(d, b)), ("Uniforme", np.full(len(d), b))]:
            a, v = intervenir(d, cob, efecto)
            filas.append({"Presupuesto_%jov": 100 * b, "Estrategia": nombre, "Votos_recuperados": v.sum(),
                          "Reduccion_abst_zona_riesgo_pp": 100 * np.average(d.ABST_E0[riesgo] - a[riesgo], weights=d.LN_27[riesgo]),
                          "Mun_Rojo": int((semaforo(a, cortes) == 3).sum()),
                          "LN_Rojo_mill": d.LN_27[semaforo(a, cortes) == 3].sum() / 1e6,
                          "Desv_est_abst_pp": 100 * np.sqrt(np.cov(a, aweights=d.LN_27))})
    return pd.DataFrame(filas)


def resumen(d, res, efecto):
    filas = []
    riesgo = res["E0"][2] >= 2                  # población en rojo o naranja del escenario inercial
    for k, (a, v, niv) in res.items():
        fila = {"Escenario": k, "Efecto_pp": 100 * efecto,
                "Abst_nacional_%": 100 * np.average(a, weights=d.LN_27),
                "Abst_zona_riesgo_%": 100 * np.average(a[riesgo], weights=d.LN_27[riesgo]),
                "Abst_resto_%": 100 * np.average(a[~riesgo], weights=d.LN_27[~riesgo]),
                "Votos_recuperados": v.sum(),
                "Desv_est_abst_pp": 100 * np.sqrt(np.cov(a, aweights=d.LN_27)),
                "Brecha_p90_p10_pp": 100 * (np.quantile(a, 0.9) - np.quantile(a, 0.1))}
        for i, c in enumerate(COLORES):
            fila[f"Mun_{c}"] = int((niv == i).sum())
            fila[f"LN_{c}_mill"] = d.LN_27[niv == i].sum() / 1e6
        filas.append(fila)
    return pd.DataFrame(filas)


def main():
    pred = pd.read_parquet(PROC / "pred_2027.parquet")
    est = pd.read_csv(OUTS / "abstencion_estatal.csv", index_col=["AELEC", "EDOCVE"])
    panel = pd.read_parquet(PROC / "panel_municipal_dev.parquet")
    cat = pd.read_parquet(PROC / "municipios_2024.parquet")

    hist = (panel[panel.AELEC.isin([2015, 2018, 2021, 2024])]
            .pivot_table(index=["EDOCVE", "MPIO24"], columns="AELEC", values=["ABST", "BRECHA_JOV", "PART_JOV"]))
    hist.columns = [f"{a}_{b}" for a, b in hist.columns]
    hist = hist.reset_index()

    res_bt = pd.read_parquet(PROC / "residuos_backtest.parquet")
    d = proyectar(pred, est, hist)
    cortes = umbrales(d.ABST_E0)
    print("Umbrales del semáforo (abstención proyectada):", dict(zip(COLORES[1:], 100 * cortes)))
    pd.DataFrame({"Color": COLORES, "Desde_%": [0, *100 * cortes], "Hasta_%": [*100 * cortes, 100]}).to_csv(
        OUTS / "umbrales_semaforo.csv", index=False)
    d["PROB_ROJO"] = prob_superar(d, cortes[2], res_bt[res_bt.AELEC == 2021])

    res, foco, cobertura = correr(d, cortes, EFECTO_BASE)
    for k, (a, v, niv) in res.items():
        d[f"ABST_{k}"] = a
        d[f"VOTOS_REC_{k}"] = v
        d[f"NIVEL_{k}"] = niv
        d[f"SEMAFORO_{k}"] = pd.Categorical.from_codes(niv, COLORES)
    d["INTERVENIDO_E1"] = foco.astype(int)
    d["COBERTURA_E2"] = cobertura

    tab = resumen(d, res, EFECTO_BASE)
    tab.round(3).to_csv(OUTS / "resumen_escenarios.csv", index=False)
    print(tab.round(2).T.to_string())
    print(f"Cobertura uniforme equivalente en E2: {100 * cobertura:.1f}% de los jóvenes de cada municipio")

    sens = pd.concat([resumen(d, correr(d, cortes, e)[0], e) for e in EFECTOS_SENS])
    sens.round(3).to_csv(OUTS / "sensibilidad_efecto.csv", index=False)
    curva = curva_presupuesto(d, cortes, EFECTO_BASE)
    curva.round(3).to_csv(OUTS / "curva_presupuesto.csv", index=False)
    print(curva.round(2).to_string(index=False))
    print(sens[["Escenario", "Efecto_pp", "Abst_nacional_%", "Votos_recuperados", "Mun_Rojo", "LN_Rojo_mill"]]
          .round(2).to_string(index=False))

    d = d.merge(cat[["EDOCVE", "MPIO24", "NOM24", "CVEGEO", "MATCH", "IMPUTADO_CONEVAL", "POB2020", "GRADO_RS"]],
                on=["EDOCVE", "MPIO24"], how="left")
    d.to_parquet(PROC / "escenarios_2027.parquet", index=False)

    print("\nTop 15 municipios por riesgo (E0, LN >= 20k):")
    top = d[d.LN_27 >= 20000].sort_values("ABST_E0", ascending=False).head(15)
    print(top[["EDOCVE", "NOM24", "LN_27", "ABST_2021", "ABST_E0", "SEMAFORO_E0", "PROB_ROJO"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
