"""
03b_robustez.py
Análisis de robustez del modelo: compara variantes con el mismo backtest temporal.

  A  CONEVAL 2020 fijo (versión inicial; usa información posterior a 2012-2018)
  B  Sin CONEVAL
  C  CONEVAL por edición vigente (sin fuga temporal)
  D  C + rezago espacial (abstención relativa de municipios vecinos)
  E  D + ponderación por tamaño de lista nominal (raíz cuadrada)

Salida: outputs/robustez_modelo.csv
"""
import importlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
M = importlib.import_module("03_model")

VARIANTES = {
    "A · CONEVAL 2020 fijo": {"coneval": "fija2020", "espacial": False, "pesos": False},
    "B · Sin CONEVAL": {"coneval": "sin", "espacial": False, "pesos": False},
    "C · CONEVAL por edición": {"coneval": "edicion", "espacial": False, "pesos": False},
    "D · C + rezago espacial": {"coneval": "edicion", "espacial": True, "pesos": False},
    "E · D + ponderación": {"coneval": "edicion", "espacial": True, "pesos": True},
}


def main():
    ctx = M.contexto()
    filas = []
    for nombre, cfg in VARIANTES.items():
        met, _ = M.backtest(M.datos(ctx, cfg), cfg)
        met = met[met.Modelo.isin(["Ensamble", "Hibrido"])]
        for _, r in met.iterrows():
            filas.append({"Variante": nombre, **r.to_dict()})
        print(nombre, "listo")
    t = pd.DataFrame(filas)
    t.round(3).to_csv(M.OUTS / "robustez_modelo.csv", index=False)
    piv = t.pivot_table(index=["Variante", "Modelo"], columns="Evaluacion",
                        values=["MAE_pond_LN_pp", "MAE_pp", "Precision_top20", "Precision_top20_LN"])
    piv[("MAE_pond_LN_pp", "prom")] = piv["MAE_pond_LN_pp"].mean(axis=1)
    print(piv.round(3).to_string())


if __name__ == "__main__":
    main()
