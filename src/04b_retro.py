"""
04b_retro.py
Retro-semáforo: ¿qué habría anticipado el semáforo si el INE lo hubiera usado antes de 2021 y de 2024?

Para cada elección evaluada T se repite exactamente el procedimiento de 2027 con datos anteriores a T:
  abstención proyectada = abstención estatal de la elección previa del mismo tipo (T-6)
                          + desviación municipal predicha por el modelo híbrido entrenado hasta T-3
y se clasifica con cortes en los percentiles 50/75/90 de la proyección. Se compara con lo que ocurrió.
Referencia: el mismo semáforo construido con la regla simple de persistencia (desviación de T-3).

Salida: outputs/retro_semaforo.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUTS = ROOT / "outputs"


def evaluar(T, res, panel, est):
    k = ["EDOCVE", "MPIO24"]
    r = res[res.AELEC == T][k + ["PRED", "LN1"]]
    real = panel[panel.AELEC == T][k + ["ABST", "LN"]].dropna()
    prev = panel[panel.AELEC == T - 3][k + ["DEV"]].rename(columns={"DEV": "DEV_T3"})
    d = r.merge(real, on=k).merge(prev, on=k, how="left")
    nivel_previo = est[est.AELEC == T - 6].set_index("EDOCVE").ABST_NIV
    d["BASE"] = d.EDOCVE.map(nivel_previo)
    filas = []
    for nombre, dev in [("Modelo híbrido", d.PRED), ("Persistencia T-3", d.DEV_T3.fillna(0))]:
        proy = d.BASE + dev
        cortes = np.round(np.quantile(proy, [0.50, 0.75, 0.90]), 2)
        nivel = np.digitize(proy, cortes)
        # "Alto riesgo real": decil y cuartil superiores de la abstención observada en T
        top10 = d.ABST >= np.quantile(d.ABST, 0.90)
        top25 = d.ABST >= np.quantile(d.ABST, 0.75)
        filas.append({
            "Eleccion": T, "Semaforo": nombre, "Municipios_decil_real": int(top10.sum()),
            "Decil_real_en_rojo_%": 100 * (nivel[top10] == 3).mean(),
            "Decil_real_en_rojo_o_naranja_%": 100 * (nivel[top10] >= 2).mean(),
            "Decil_real_en_rojo_o_naranja_%LN": 100 * d.LN[top10 & (nivel >= 2)].sum() / d.LN[top10].sum(),
            "Cuartil_real_en_rojo_o_naranja_%": 100 * (nivel[top25] >= 2).mean(),
            "Rojos_que_quedaron_en_cuartil_real_%": 100 * top25[nivel == 3].mean(),
            "Verdes_que_quedaron_en_decil_real_%": 100 * top10[nivel == 0].mean(),
        })
    return filas


def main():
    res = pd.read_parquet(PROC / "residuos_backtest.parquet")
    panel = pd.read_parquet(PROC / "panel_municipal_dev.parquet")
    est = pd.read_csv(OUTS / "abstencion_estatal.csv")
    t = pd.DataFrame([f for T in [2021, 2024] for f in evaluar(T, res, panel, est)])
    t.round(1).to_csv(OUTS / "retro_semaforo.csv", index=False)
    print(t.round(1).T.to_string())


if __name__ == "__main__":
    main()
