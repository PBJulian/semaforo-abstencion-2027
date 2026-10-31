"""
05_export_figures.py
Exporta la base de datos anonimizada (CSV + XLSX con diccionario) y las figuras del reporte.

Salidas:
  entregables/base_datos/escenarios_2027_municipal.csv
  entregables/base_datos/base_riesgo_abstencion_2027.xlsx
  outputs/figures/*.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUTS = ROOT / "outputs"
FIG = OUTS / "figures"
BD = ROOT / "entregables" / "base_datos"

ESTADOS = {1: "Aguascalientes", 2: "Baja California", 3: "Baja California Sur", 4: "Campeche",
           5: "Coahuila", 6: "Colima", 7: "Chiapas", 8: "Chihuahua", 9: "Ciudad de México",
           10: "Durango", 11: "Guanajuato", 12: "Guerrero", 13: "Hidalgo", 14: "Jalisco",
           15: "México", 16: "Michoacán", 17: "Morelos", 18: "Nayarit", 19: "Nuevo León",
           20: "Oaxaca", 21: "Puebla", 22: "Querétaro", 23: "Quintana Roo", 24: "San Luis Potosí",
           25: "Sinaloa", 26: "Sonora", 27: "Tabasco", 28: "Tamaulipas", 29: "Tlaxcala",
           30: "Veracruz", 31: "Yucatán", 32: "Zacatecas"}

# Paleta: semáforo = estados (siempre con etiqueta); series = categórica en orden fijo
SEMAFORO = {"Verde": "#0ca30c", "Amarillo": "#fab219", "Naranja": "#ec835a", "Rojo": "#d03b3b"}
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "axes.facecolor": SURF, "figure.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- base de datos
DICCIONARIO = [
    ("EDOCVE", "Clave INE de la entidad federativa"),
    ("ENTIDAD", "Nombre de la entidad federativa"),
    ("MPIO24", "Clave INE del municipio (marco geográfico 2024)"),
    ("MUNICIPIO", "Nombre del municipio (INE 2024)"),
    ("CVEGEO", "Clave geoestadística INEGI (cruce por nombre con CONEVAL 2020)"),
    ("LN_2024", "Lista nominal en cuadernillos, elección 2024"),
    ("ABST_2015 / 2018 / 2021 / 2024", "Tasa de abstención observada = NV / (SV + NV)"),
    ("PART_JOV_2021 / 2024", "Tasa de participación de personas de 18 a 29 años"),
    ("SH_JOV_27", "Proporción de la lista nominal con 18 a 29 años (2024)"),
    ("IRS / GRADO_RS", "Índice y grado de rezago social CONEVAL 2020"),
    ("DEV_2027", "Desviación proyectada de la abstención municipal respecto a su entidad (modelo híbrido)"),
    ("ABST_E0", "Abstención proyectada 2027, escenario inercial (sin intervención)"),
    ("ABST_E0_LI90 / LS90", "Intervalo conformal al 90% de ABST_E0"),
    ("PROB_ROJO", "Probabilidad de superar el umbral rojo (empírica, con errores del backtest 2021 del mismo tamaño)"),
    ("CAMBIO_VS_2021", "ABST_E0 - ABST_2021 (positivo = más abstención que en 2021)"),
    ("SEMAFORO_E0 / E1 / E2", "Nivel de riesgo: Verde, Amarillo, Naranja, Rojo"),
    ("ABST_E1", "Abstención proyectada con intervención juvenil focalizada en rojo y naranja"),
    ("ABST_E2", "Abstención proyectada con el mismo presupuesto repartido uniformemente"),
    ("VOTOS_REC_E1 / E2", "Votos adicionales esperados por la intervención"),
    ("INTERVENIDO_E1", "1 si el municipio recibe la intervención focalizada"),
    ("ACCION", "Acción sugerida por la matriz de acción (municipios rojos y naranjas)"),
    ("MARCA_HOMBRES_JOVENES", "1 si la brecha de participación mujeres-hombres está en el cuartil superior"),
    ("PCT_NACOE / PCT_RESOE15", "% de población nacida en otra entidad / que vivía en otra entidad en 2015 (Censo 2020)"),
    ("PCT_HLI / GRAPROES", "% de población de 3+ años hablante de lengua indígena / grado promedio de escolaridad (Censo 2020)"),
    ("EXP_<familia>", "Contribución (pp) de cada familia de variables a la desviación proyectada (componente lineal)"),
    ("secciones_2027.csv", "Archivo aparte: proyección por sección electoral y prioridad dentro de cada distrito federal"),
    ("SIN_DATO_2024", "1 si en 2024 no hubo registros de votación capturados (se proyecta con su historial)"),
    ("IMPUTADO_CONEVAL", "1 si el municipio no existe en CONEVAL 2020 (mediana estatal)"),
]


def export(d, panel):
    BD.mkdir(parents=True, exist_ok=True)
    d = d.assign(ENTIDAD=d.EDOCVE.map(ESTADOS), MUNICIPIO=d.NOM24, LN_2024=d.LN_27)
    d = d.merge(pd.read_parquet(PROC / "acciones_2027.parquet"), on=["EDOCVE", "MPIO24"], how="left")
    exp = [c for c in d.columns if c.startswith("EXP_")]
    cols = ["EDOCVE", "ENTIDAD", "MPIO24", "MUNICIPIO", "CVEGEO", "LN_2024", "SH_JOV_27",
            "ABST_2015", "ABST_2018", "ABST_2021", "ABST_2024", "PART_JOV_2021", "PART_JOV_2024",
            "IRS", "GRADO_RS", "DEV_2027", "ABST_E0", "ABST_E0_LI90", "ABST_E0_LS90", "PROB_ROJO",
            "CAMBIO_VS_2021", "SEMAFORO_E0", "INTERVENIDO_E1", "ABST_E1", "SEMAFORO_E1", "VOTOS_REC_E1",
            "ABST_E2", "SEMAFORO_E2", "VOTOS_REC_E2", "ACCION", "MARCA_HOMBRES_JOVENES",
            "PCT_NACOE", "PCT_RESOE15", "PCT_HLI", "GRAPROES"] + exp + ["SIN_DATO_2024", "IMPUTADO_CONEVAL"]
    esc = d[cols].sort_values(["EDOCVE", "MPIO24"])
    for c in esc.select_dtypes("float").columns:
        esc[c] = esc[c].round(4)
    esc.to_csv(BD / "escenarios_2027_municipal.csv", index=False, encoding="utf-8-sig")

    hist = panel.assign(ENTIDAD=panel.EDOCVE.map(ESTADOS))[
        ["AELEC", "EDOCVE", "ENTIDAD", "MPIO24", "LN", "SV", "NV", "NS", "PART", "ABST", "PART_JOV",
         "PART_1819", "PART_60M", "PART_MUJ", "PART_HOM", "SH_JOV", "SH_RUR", "BRECHA_JOV", "DEV"]].round(4)
    hist.to_csv(BD / "panel_historico_municipal_2009_2024.csv", index=False, encoding="utf-8-sig")

    with pd.ExcelWriter(BD / "base_riesgo_abstencion_2027.xlsx") as xw:
        pd.DataFrame(DICCIONARIO, columns=["Variable", "Descripción"]).to_excel(xw, sheet_name="Diccionario", index=False)
        esc.to_excel(xw, sheet_name="Escenarios_2027", index=False)
        hist.to_excel(xw, sheet_name="Panel_2009_2024", index=False)
        pd.read_csv(OUTS / "resumen_escenarios.csv").to_excel(xw, sheet_name="Resumen_escenarios", index=False)
        pd.read_csv(OUTS / "sensibilidad_efecto.csv").to_excel(xw, sheet_name="Sensibilidad", index=False)
        pd.read_csv(OUTS / "metricas_backtest.csv").to_excel(xw, sheet_name="Validacion_modelo", index=False)
        pd.read_csv(OUTS / "umbrales_semaforo.csv").to_excel(xw, sheet_name="Umbrales_semaforo", index=False)
        estatal(d).to_excel(xw, sheet_name="Resumen_estatal", index=False)
        pd.read_csv(BD / "distritos_2027.csv").to_excel(xw, sheet_name="Distritos_2027", index=False)
        pd.read_csv(OUTS / "matriz_accion.csv").to_excel(xw, sheet_name="Matriz_accion", index=False)
        pd.read_csv(OUTS / "retro_semaforo.csv").to_excel(xw, sheet_name="Retro_semaforo", index=False)
        pd.read_csv(OUTS / "robustez_modelo.csv").to_excel(xw, sheet_name="Robustez_modelo", index=False)
        pd.read_csv(OUTS / "validacion_secciones.csv").to_excel(xw, sheet_name="Validacion_secciones", index=False)
    print("Base exportada:", len(esc), "municipios,", len(hist), "filas históricas")


def estatal(d):
    g = d.groupby("EDOCVE")
    t = pd.DataFrame({
        "Entidad": g.EDOCVE.first().map(ESTADOS),
        "LN_2024": g.LN_27.sum(),
        "Abst_2021_%": 100 * g.apply(lambda x: np.average(x.ABST_2021.fillna(x.ABST_E0), weights=x.LN_27)),
        "Abst_E0_%": 100 * g.apply(lambda x: np.average(x.ABST_E0, weights=x.LN_27)),
        "Abst_E1_%": 100 * g.apply(lambda x: np.average(x.ABST_E1, weights=x.LN_27)),
        "Mun_rojo_E0": g.apply(lambda x: (x.SEMAFORO_E0 == "Rojo").sum()),
        "Mun_rojo_E1": g.apply(lambda x: (x.SEMAFORO_E1 == "Rojo").sum()),
        "%LN_rojo_naranja_E0": 100 * g.apply(lambda x: x.LN_27[x.NIVEL_E0 >= 2].sum() / x.LN_27.sum()),
    }).reset_index()
    return t.round(2).sort_values("%LN_rojo_naranja_E0", ascending=False)


# ---------------------------------------------------------------- figuras
def fig_nacional():
    nat = pd.read_csv(OUTS / "abstencion_nacional.csv")
    fig, ax = plt.subplots(figsize=(8, 4))
    for col, c, lab in [("ABST_JOV_NIV", S2, "Jóvenes 18-29"), ("ABST_NIV", S1, "Total")]:
        ax.plot(nat.AELEC, 100 * nat[col], color=c, lw=2, marker="o", ms=7, mec=SURF, mew=2)
        ax.annotate(lab, (nat.AELEC.iat[-1], 100 * nat[col].iat[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", color=INK, fontsize=9)
    for y in [2009, 2015, 2021]:
        ax.axvspan(y - 0.8, y + 0.8, color=GRID, alpha=0.6, lw=0)
    ax.text(2009, 30.5, "Intermedias sombreadas", color=INK2, fontsize=8)
    ax.set_xticks(nat.AELEC)
    ax.set_xlim(2008, 2026.5)
    ax.set_ylim(30, 70)
    ax.set_ylabel("Abstención (%)")
    ax.set_title("La abstención sube en intermedias y es mayor entre jóvenes")
    save(fig, "f1_abstencion_nacional.png")


def fig_edad():
    sec = pd.read_parquet(PROC / "ccpc_seccion.parquet", columns=["AELEC", "GEDAD", "SV", "NV"])
    g = sec.groupby(["AELEC", "GEDAD"], observed=True)[["SV", "NV"]].sum()
    g["ABST"] = 100 * g.NV / (g.SV + g.NV)
    t = g.ABST.unstack("AELEC")
    fig, ax = plt.subplots(figsize=(8, 4))
    for y, c in [(2021, S2), (2024, S1)]:
        ax.plot(t.index.astype(str), t[y], color=c, lw=2, marker="o", ms=7, mec=SURF, mew=2)
        ax.annotate(str(y), (len(t) - 1, t[y].iat[-1]), xytext=(8, 0), textcoords="offset points",
                    va="center", color=INK, fontsize=9)
    ax.set_ylabel("Abstención (%)")
    ax.set_xlabel("Grupo de edad")
    ax.set_title("Abstención por edad: la brecha juvenil se mantiene")
    save(fig, "f2_abstencion_edad.png")
    return t


def fig_backtest():
    m = pd.read_csv(OUTS / "metricas_backtest.csv")
    orden = ["Ingenuo_T-3", "Ingenuo_T-6", "Ingenuo_promedio", "Ridge", "GBM", "Ensamble", "Hibrido"]
    etiquetas = ["Persistencia T-3", "Persistencia T-6", "Promedio histórico", "Ridge", "Gradient Boosting",
                 "Ensamble ML", "Híbrido (final)"]
    p = m.pivot(index="Modelo", columns="Evaluacion", values="MAE_pond_LN_pp").loc[orden]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = np.arange(len(orden))
    h = 0.38
    for i, (yr, c) in enumerate([(2021, S2), (2024, S1)]):
        ax.barh(y + (i - 0.5) * h, p[yr], height=h - 0.04, color=c, label=f"Evaluación {yr}")
        for yy, v in zip(y + (i - 0.5) * h, p[yr]):
            ax.text(v + 0.03, yy, f"{v:.2f}", va="center", fontsize=8, color=INK2)
    ax.set_yticks(y, etiquetas)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Error absoluto medio ponderado por lista nominal (pp)")
    ax.set_xlim(0, p.values.max() * 1.12)
    ax.legend(frameon=False, ncol=2, loc="lower left", bbox_to_anchor=(0, 1.0))
    ax.set_title("Backtest temporal: el híbrido es el más estable", pad=28)
    save(fig, "f3_backtest.png")


def fig_importancia():
    imp = pd.read_csv(OUTS / "importancia_variables.csv", index_col=0)
    nombres = {"DEVMEAN": "Abstención relativa promedio histórica", "DEV2": "Abstención relativa intermedia previa",
               "DEV1": "Abstención relativa elección previa", "EDOCVE": "Entidad federativa",
               "LOG_LN1": "Tamaño de la lista nominal (log)", "DEVJ1": "Abstención juvenil relativa previa",
               "EDU_BASICA_INC": "Educación básica incompleta (CONEVAL)", "DEVJ2": "Abstención juvenil relativa intermedia",
               "SH_JOV1": "% de lista nominal joven", "BRECHA_SEXO1": "Brecha de participación por sexo",
               "BRECHA_JOV1": "Brecha de participación juvenil", "SIN_REFRI": "Viviendas sin refrigerador",
               "VEC_DEV1": "Abstención relativa de municipios vecinos", "VEC_DEV2": "Abst. relativa de vecinos (intermedia)",
               "CREC_LN": "Crecimiento de la lista nominal", "ANALF": "Analfabetismo (CONEVAL)",
               "SH_URB1": "% de lista nominal urbana", "SH_RUR1": "% de lista nominal rural",
               "SH_60M1": "% de lista nominal de 60+ años", "SH_NS1": "% de registros no especificados",
               "DDEV": "Cambio reciente de abstención relativa", "IRS": "Índice de rezago social (CONEVAL)"}
    t = imp[["GBM", "Ridge"]].clip(lower=0).mean(axis=1).sort_values(ascending=False).head(10)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.barh([nombres.get(i, i) for i in t.index], t.values, color=S1, height=0.6)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Aumento del error al permutar la variable (pp, promedio Ridge y GBM)")
    ax.set_title("Variables con mayor peso en la predicción")
    save(fig, "f4_importancia.png")


def fig_semaforo(d):
    esc = {"E0": "Inercial", "E1": "Focalizado", "E2": "Uniforme"}
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
    for ax, (medida, lab) in zip(axes, [("n", "Municipios"), ("ln", "Lista nominal (millones)")]):
        left = np.zeros(3)
        for color in SEMAFORO:
            vals = np.array([(d[f"SEMAFORO_{k}"] == color).sum() if medida == "n"
                             else d.LN_27[d[f"SEMAFORO_{k}"] == color].sum() / 1e6 for k in esc])
            ax.barh(list(esc.values()), vals, left=left, color=SEMAFORO[color], height=0.6,
                    edgecolor=SURF, linewidth=2, label=color)
            for i, v in enumerate(vals):
                if v > (220 if medida == "n" else 8):
                    ax.text(left[i] + v / 2, i, f"{v:,.0f}" if medida == "n" else f"{v:.1f}", ha="center",
                            va="center", fontsize=8, color=INK if color == "Amarillo" else "#ffffff")
            left += vals
        ax.set_title(lab, fontsize=10)
        ax.grid(axis="y", visible=False)
    axes[0].invert_yaxis()
    fig.legend(*axes[0].get_legend_handles_labels(), frameon=False, ncol=4, loc="lower center")
    fig.suptitle("Semáforo de riesgo 2027 por escenario (efecto +5 pp juvenil)", x=0.02, ha="left",
                 fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(FIG / "f5_semaforo_escenarios.png", dpi=200)
    plt.close(fig)


def fig_presupuesto():
    c = pd.read_csv(OUTS / "curva_presupuesto.csv")
    fig, ax = plt.subplots(figsize=(8, 4))
    for k, col, lab in [("Priorizado", S1, "Priorizado por el semáforo"), ("Uniforme", S2, "Uniforme")]:
        t = c[c.Estrategia == k]
        ax.plot(t["Presupuesto_%jov"], t.Reduccion_abst_zona_riesgo_pp, color=col, lw=2, marker="o", ms=7,
                mec=SURF, mew=2)
        fila = t[t["Presupuesto_%jov"] == 30].iloc[0]
        ax.annotate(lab, (30, fila.Reduccion_abst_zona_riesgo_pp), xytext=(-8, 10) if k == "Priorizado" else (8, -14),
                    textcoords="offset points", ha="right" if k == "Priorizado" else "left", color=INK, fontsize=9)
    ax.set_xlabel("Presupuesto: % de las personas jóvenes del país alcanzadas por la campaña")
    ax.set_ylabel("Reducción de la abstención (pp)")
    ax.set_title("Mismo presupuesto, el doble de efecto donde más se necesita")
    ax.set_ylim(0, None)
    ax.text(0.99, 0.03, "Población de municipios rojo y naranja del escenario inercial; efecto +5 pp juvenil",
            transform=ax.transAxes, ha="right", fontsize=8, color=INK2)
    save(fig, "f6_presupuesto.png")


def fig_estados(d):
    t = estatal(d).head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(t.Entidad, t["%LN_rojo_naranja_E0"], color=SEMAFORO["Rojo"], height=0.6)
    for y, v in enumerate(t["%LN_rojo_naranja_E0"]):
        ax.text(v + 1, y, f"{v:.0f}%", va="center", fontsize=8, color=INK2)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("% de la lista nominal en municipios rojo o naranja (escenario inercial)")
    ax.set_title("Entidades con mayor población en riesgo alto de abstención")
    save(fig, "f7_entidades_riesgo.png")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    d = pd.read_parquet(PROC / "escenarios_2027.parquet")
    panel = pd.read_parquet(PROC / "panel_municipal_dev.parquet")
    export(d, panel)
    fig_nacional()
    t = fig_edad()
    print((t.round(1)).to_string())
    fig_backtest()
    fig_importancia()
    fig_semaforo(d)
    fig_presupuesto()
    fig_estados(d)
    print(estatal(d).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
