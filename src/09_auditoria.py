"""
09_auditoria.py
Control de calidad final: verifica que las cifras clave, calculadas desde los resultados, aparezcan
igual en el reporte (PDF), la presentación (PDF), la base de datos (CSV) y el tablero (HTML).
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTS = ROOT / "outputs"
ENT = ROOT / "entregables"


def texto_pdf(path):
    t = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True).stdout
    return re.sub(r"\s+", " ", t)


def main():
    res = pd.read_csv(OUTS / "resumen_escenarios.csv").set_index("Escenario")
    retro = pd.read_csv(OUTS / "retro_semaforo.csv").query("Semaforo == 'Modelo híbrido'").set_index("Eleccion")
    met = pd.read_csv(OUTS / "metricas_backtest.csv").query("Modelo == 'Hibrido'").set_index("Evaluacion")
    dist = pd.read_csv(ENT / "base_datos" / "distritos_2027.csv")
    esc = pd.read_csv(ENT / "base_datos" / "escenarios_2027_municipal.csv")
    z = [res.loc[k, "Abst_zona_riesgo_%"] for k in ["E0", "E1", "E2"]]

    cifras = {
        "Municipios en rojo": f"{int(res.loc['E0', 'Mun_Rojo'])}",
        "Electores en rojo (M)": f"{res.loc['E0', 'LN_Rojo_mill']:.1f}",
        "Municipios en naranja": f"{int(res.loc['E0', 'Mun_Naranja'])}",
        "Abstención 2027 (%)": f"{np.average(esc.ABST_E0, weights=esc.LN_2024) * 100:.1f}",
        "Veces más (priorizar)": f"{(z[0] - z[1]) / (z[0] - z[2]):.1f}",
        "Reducción priorizada (pp)": f"{z[0] - z[1]:.2f}",
        "Reducción uniforme (pp)": f"{z[0] - z[2]:.2f}",
        "Retro 2021 rojo/naranja (%)": f"{retro.loc[2021, 'Decil_real_en_rojo_o_naranja_%']:.0f}",
        "Retro 2024 rojo/naranja (%)": f"{retro.loc[2024, 'Decil_real_en_rojo_o_naranja_%']:.0f}",
        "Error 2021 (pp)": f"{met.loc[2021, 'MAE_pond_LN_pp']:.1f}",
        "Error 2024 (pp)": f"{met.loc[2024, 'MAE_pond_LN_pp']:.1f}",
        "Distritos en rojo": f"{int((dist.SEMAFORO_2027 == 'Rojo').sum())}",
        "Distritos en naranja": f"{int((dist.SEMAFORO_2027 == 'Naranja').sum())}",
        "Secciones mitad (mediana)": f"{dist.SECC_MITAD_JOV_ABST.median():.0f} de {dist.SECCIONES.median():.0f}",
    }
    docs = {"Reporte": texto_pdf(ENT / "Reporte_metodologico_preventivo_DataInsert.pdf"),
            "Presentación": texto_pdf(ENT / "Presentacion_ejecutiva_DataInsert.pdf")}

    # Base de datos: recalcular desde el CSV entregado
    base = {"Municipios en rojo": str(int((esc.SEMAFORO_E0 == "Rojo").sum())),
            "Electores en rojo (M)": f"{esc.LN_2024[esc.SEMAFORO_E0 == 'Rojo'].sum() / 1e6:.1f}",
            "Municipios en naranja": str(int((esc.SEMAFORO_E0 == "Naranja").sum()))}
    # Tablero: recalcular desde los datos incrustados en el HTML
    html = (ENT / "mapa_escenarios_2027.html").read_text(encoding="utf-8")
    D = json.loads(re.search(r"const D = (\{.*?\});\nconst GEO", html, re.S).group(1))
    a0, ln, cut = np.array(D["a0"]), np.array(D["ln"]), D["cortes"]
    tablero = {"Municipios en rojo": str(int((a0 >= cut[2]).sum())),
               "Electores en rojo (M)": f"{ln[a0 >= cut[2]].sum() / 1e6:.1f}",
               "Municipios en naranja": str(int(((a0 >= cut[1]) & (a0 < cut[2])).sum()))}

    filas = []
    for nombre, v in cifras.items():
        fila = {"Cifra": nombre, "Valor": v}
        for doc, t in docs.items():
            ok = v in t
            fila[doc] = "✓" if ok else "✗"
        fila["Base CSV"] = ("✓" if base[nombre] == v else f"✗ {base[nombre]}") if nombre in base else "—"
        fila["Tablero"] = ("✓" if tablero[nombre] == v else f"✗ {tablero[nombre]}") if nombre in tablero else "—"
        filas.append(fila)
    t = pd.DataFrame(filas)
    print(t.to_string(index=False))
    return t


if __name__ == "__main__":
    main()
