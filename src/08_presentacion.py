"""
08_presentacion.py
Presentación ejecutiva (10 diapositivas, estilo consultoría: títulos de acción, una idea por lámina,
fuente al pie). Las cifras se leen de los resultados del pipeline; las notas de cada lámina traen
el guion del pitch.

Salida: entregables/Presentacion_ejecutiva_DataInsert.pptx (+ PDF si hay LibreOffice)
"""
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUTS = ROOT / "outputs"
FIG = OUTS / "figures"
OUT = ROOT / "entregables" / "Presentacion_ejecutiva_DataInsert.pptx"

NAVY, INK, GRAY, LIGHT, RULE = "0B2545", "1A1A1A", "5F6670", "F2F4F7", "D5D9E0"
BLUE = "3B6FB6"
SEM = {"Verde": "0CA30C", "Amarillo": "FAB219", "Naranja": "EC835A", "Rojo": "D03B3B"}
FONT = "Arial"
W, H = 13.333, 7.5
X0, TW = 0.6, 12.13               # margen izquierdo y ancho útil

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#8a9099", "axes.labelcolor": "#5F6670",
                     "xtick.color": "#5F6670", "ytick.color": "#5F6670", "axes.grid": True, "grid.color": "#E3E6EB",
                     "grid.linewidth": 0.8, "figure.facecolor": "white", "axes.facecolor": "white"})


def rgb(h):
    return RGBColor.from_string(h)


def sinestilo(shape):
    """Quita el estilo de tema (sombra y contorno) que python-pptx aplica por defecto a formas y conectores."""
    st = shape._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}style")
    if st is not None:
        shape._element.remove(st)


# ------------------------------------------------------------------ cifras
def cifras():
    d = pd.read_parquet(PROC / "escenarios_2027.parquet")
    res = pd.read_csv(OUTS / "resumen_escenarios.csv").set_index("Escenario")
    nat = pd.read_csv(OUTS / "abstencion_nacional.csv").set_index("AELEC")
    met = pd.read_csv(OUTS / "metricas_backtest.csv")
    retro = pd.read_csv(OUTS / "retro_semaforo.csv").query("Semaforo == 'Modelo híbrido'").set_index("Eleccion")
    mat = pd.read_csv(OUTS / "matriz_accion.csv").set_index("ACCION")
    dist = pd.read_parquet(PROC / "distritos_2027.parquet")
    curva = pd.read_csv(OUTS / "curva_presupuesto.csv")
    censo = pd.read_parquet(PROC / "censo2020_mun.parquet")
    c = {"d": d, "res": res, "nat": nat, "retro": retro, "mat": mat, "dist": dist, "curva": curva}
    hib = met[met.Modelo == "Hibrido"].set_index("Evaluacion")
    c["mae21"], c["mae24"] = hib.loc[2021, "MAE_pond_LN_pp"], hib.loc[2024, "MAE_pond_LN_pp"]
    c["prec_ln"] = 100 * hib.Precision_top20_LN.min()
    c["abst27"] = 100 * np.average(d.ABST_E0, weights=d.LN_27)
    z0, z1, z2 = (res.loc[k, "Abst_zona_riesgo_%"] for k in ["E0", "E1", "E2"])
    c["red1"], c["red2"] = z0 - z1, z0 - z2
    c["pres_rojo"] = 100 * d.LN_JOV_27[d.NIVEL_E0 == 3].sum() / d.LN_JOV_27.sum()
    rojo = d[d.NIVEL_E0 == 3]
    urb, peq = rojo[rojo.LN_27 >= 20000], rojo[rojo.LN_27 < 5000]
    c["urb_n"], c["urb_share"], c["urb_ln"] = len(urb), 100 * urb.LN_27.sum() / rojo.LN_27.sum(), urb.LN_27.sum() / 1e6
    c["peq_oax"], c["peq_ln"] = int((peq.EDOCVE == 20).sum()), peq.LN_27.sum() / 1e3
    dc = d.merge(censo, on="CVEGEO")
    wv = lambda m, v: 100 * np.average(dc.loc[m, v], weights=dc.loc[m, "POBTOT"])
    mu = (dc.NIVEL_E0 == 3) & (dc.LN_27 >= 20000)
    mp = (dc.NIVEL_E0 == 3) & (dc.LN_27 < 5000)
    allm = dc.LN_27 > 0
    c["nacoe_u"], c["nacoe_n"] = wv(mu, "PCT_NACOE"), wv(allm, "PCT_NACOE")
    c["resoe_u"], c["resoe_n"] = wv(mu, "PCT_RESOE15"), wv(allm, "PCT_RESOE15")
    c["hli_p"], c["hli_n"] = wv(mp, "PCT_HLI"), wv(allm, "PCT_HLI")
    panel = pd.read_parquet(PROC / "panel_municipal_dev.parquet")
    ln = panel.pivot_table(index=["EDOCVE", "MPIO24"], columns="AELEC", values="LN")
    u = ln.loc[urb.set_index(["EDOCVE", "MPIO24"]).index]
    c["crec_u"], c["crec_n"] = 100 * (u[2024].sum() / u[2012].sum() - 1), 100 * (ln[2024].sum() / ln[2012].sum() - 1)
    c["dist_n"] = dist.SEMAFORO_2027.value_counts()
    c["mitad"], c["secc"] = dist.SECC_MITAD_JOV_ABST.median(), dist.SECCIONES.median()
    c["dtop"] = dist.sort_values("JOV_ABST_ESP", ascending=False).iloc[0]
    return c


# ------------------------------------------------------------------ gráficas del deck
def fig_tendencia(c):
    nat = c["nat"]
    fig, ax = plt.subplots(figsize=(7.6, 4.3), dpi=220)
    yrs = nat.index.values
    for y in [2009, 2015, 2021]:
        ax.axvspan(y - 1, y + 1, color="#EEF1F5", lw=0, zorder=0)
    ax.plot(yrs, 100 * nat.ABST_JOV_NIV, color="#" + BLUE, lw=2.5, marker="o", ms=7, mec="white", mew=1.5, zorder=3)
    ax.plot(yrs, 100 * nat.ABST_NIV, color="#" + NAVY, lw=2.5, marker="o", ms=7, mec="white", mew=1.5, zorder=3)
    ax.annotate("Jóvenes 18–29", (2024, 100 * nat.ABST_JOV_NIV[2024]), xytext=(8, 0), textcoords="offset points", va="center", color="#" + BLUE, fontsize=12, fontweight="bold")
    ax.annotate("Total", (2024, 100 * nat.ABST_NIV[2024]), xytext=(8, 0), textcoords="offset points", va="center", color="#" + NAVY, fontsize=12, fontweight="bold")
    for y in [2009, 2015, 2021]:
        ax.text(y, 31.5, "Intermedia", ha="center", fontsize=10, color="#5F6670")
    ax.set_xticks(yrs)
    ax.set_xlim(2007.5, 2027.5)
    ax.set_ylim(30, 70)
    ax.set_ylabel("Abstención (%)")
    fig.tight_layout()
    fig.savefig(FIG / "deck_tendencia.png")
    plt.close(fig)


def fig_mapa(c):
    shp = next((ROOT / "data" / "raw" / "geo").rglob("*mun.shp"))
    g = gpd.read_file(shp)[["CVEGEO", "geometry"]]
    g["geometry"] = g.geometry.simplify(800)
    d = c["d"][["CVEGEO", "SEMAFORO_E0"]].dropna()
    g = g.merge(d, on="CVEGEO", how="left")
    fig, ax = plt.subplots(figsize=(8.2, 5.4), dpi=220)
    g.plot(ax=ax, color=g.SEMAFORO_E0.astype(str).map({k: "#" + v for k, v in SEM.items()}).fillna("#D9D7DE"),
           edgecolor="white", linewidth=0.08)
    ax.set_axis_off()
    fig.tight_layout(pad=0)
    fig.savefig(FIG / "deck_mapa.png", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def fig_presupuesto(c):
    cv = c["curva"]
    fig, ax = plt.subplots(figsize=(7.6, 4.4), dpi=220)
    for k, col, lab, x_lab, off in [("Priorizado", NAVY, "Priorizado con el semáforo", 50, (4, 10)), ("Uniforme", "8A9099", "Uniforme", 75, (10, -16))]:
        t = cv[cv.Estrategia == k]
        ax.plot(t["Presupuesto_%jov"], t.Reduccion_abst_zona_riesgo_pp, color="#" + col, lw=2.8, marker="o", ms=6, mec="white", mew=1.2)
        r = t[t["Presupuesto_%jov"] == x_lab].iloc[0]
        ax.annotate(lab, (x_lab, r.Reduccion_abst_zona_riesgo_pp), xytext=off, textcoords="offset points",
                    ha="left", color="#" + col, fontsize=12, fontweight="bold")
    ax.set_xlabel("Presupuesto: % de jóvenes del país alcanzados")
    ax.set_ylabel("Reducción de abstención (pp)")
    ax.set_ylim(0, 1.6)
    fig.tight_layout()
    fig.savefig(FIG / "deck_presupuesto.png")
    plt.close(fig)


# ------------------------------------------------------------------ utilidades de lámina
class Deck:
    def __init__(self):
        self.p = Presentation()
        self.p.slide_width, self.p.slide_height = Inches(W), Inches(H)
        self.n = 0

    def slide(self, dark=False):
        s = self.p.slides.add_slide(self.p.slide_layouts[6])
        self.n += 1
        if dark:
            bg = s.background.fill
            bg.solid()
            bg.fore_color.rgb = rgb(NAVY)
        return s

    def text(self, s, x, y, w, h, runs, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             spacing=1.1, name=None):
        """runs: str, o lista de párrafos; cada párrafo es str o lista de (texto, {bold, color, size})."""
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        if name:
            tb.name = name
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        paras = runs if isinstance(runs, list) else [runs]
        for i, par in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            p.line_spacing = spacing
            for t, o in ([(par, {})] if isinstance(par, str) else par):
                r = p.add_run()
                r.text = t
                f = r.font
                f.name = FONT
                f.size = Pt(o.get("size", size))
                f.bold = o.get("bold", bold)
                f.color.rgb = rgb(o.get("color", color))
        return tb

    def box(self, s, x, y, w, h, fill=LIGHT, line=None, shape=MSO_SHAPE.RECTANGLE):
        b = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        b.fill.solid()
        b.fill.fore_color.rgb = rgb(fill)
        if line:
            b.line.color.rgb = rgb(line)
            b.line.width = Pt(0.75)
        else:
            b.line.fill.background()
        sinestilo(b)
        return b

    def rule(self, s, x, y, w):
        ln = s.shapes.add_connector(1, Inches(x), Inches(y), Inches(x + w), Inches(y))
        sinestilo(ln)
        ln.line.color.rgb = rgb(RULE)
        ln.line.width = Pt(0.75)

    def chrome(self, s, seccion, titulo, fuente):
        """Etiqueta de sección, título de acción, fuente y número de página (posiciones fijas en todo el deck)."""
        self.text(s, X0, 0.38, 8, 0.3, seccion.upper(), size=11, color=BLUE, bold=True, name="Seccion")
        self.text(s, X0, 0.68, TW, 1.05, titulo, size=24, color=NAVY, bold=True, spacing=1.0, name="Titulo")
        self.text(s, X0, 6.95, 10.8, 0.3, "Fuente: " + fuente, size=10, color=GRAY, name="Fuente")
        self.text(s, W - X0 - 0.6, 6.95, 0.6, 0.3, str(self.n), size=10, color=GRAY, align=PP_ALIGN.RIGHT, name="Pagina")

    def stat(self, s, x, y, w, big, label, color=NAVY, big_size=40, label_size=14):
        self.text(s, x, y, w, 0.75, big, size=big_size, color=color, bold=True)
        self.text(s, x, y + 0.78, w, 0.9, label, size=label_size, color=INK)

    def image(self, s, path, x, y, w=None, h=None):
        kw = {}
        if w:
            kw["width"] = Inches(w)
        if h:
            kw["height"] = Inches(h)
        return s.shapes.add_picture(str(path), Inches(x), Inches(y), **kw)


# ------------------------------------------------------------------ láminas
def main():
    c = cifras()
    fig_tendencia(c)
    fig_mapa(c)
    fig_presupuesto(c)
    res, retro, mat = c["res"], c["retro"], c["mat"]
    D = Deck()
    FUENTE_CCPC = "INE, Conteos Censales de Participación Ciudadana 2009–2024; análisis Data Insert"

    # 1. Portada
    s = D.slide(dark=True)
    D.text(s, X0, 0.6, 10, 0.4, "HACKEA LA PARTICIPACIÓN · RETO 2: PREDICCIÓN Y ESCENARIOS DE RIESGO DE ABSTENCIÓN", size=12, color="AFC3E0", bold=True)
    D.text(s, X0, 1.9, TW, 0.9, "Semáforo de Riesgo de Abstención 2027", size=40, color="FFFFFF", bold=True)
    D.text(s, X0, 3.1, 11.0, 1.2, "Con el mismo presupuesto, el INE puede duplicar el efecto de sus acciones contra la abstención si decide dónde actuar con datos",
           size=20, color="D6E0EE", spacing=1.15)
    D.text(s, X0, 5.35, 11.5, 0.4, "Equipo Data Insert", size=16, color="FFFFFF", bold=True)
    D.text(s, X0, 5.75, 11.5, 0.4, "Aldo Sebastian Altamirano Vázquez · Carlo Kiliano Ferrera Guadarrama · Isaac Pancardo Botello · José Julián Pérez Bustamante",
           size=13, color="AFC3E0")
    D.text(s, X0, 6.6, 6, 0.3, "31 de octubre de 2026", size=12, color="AFC3E0")
    s.notes_slide.notes_text_frame.text = (
        "Somos Data Insert. En 2027 México tendrá una elección intermedia, que es cuando más gente deja de votar. "
        "Nuestra propuesta: con el mismo presupuesto, el INE puede duplicar el efecto de sus acciones contra la abstención "
        "si decide dónde actuar con datos. Les mostramos dónde, por qué, qué hacer y cuánto rinde.")

    # 2. Resumen ejecutivo
    s = D.slide()
    D.chrome(s, "Resumen ejecutivo",
             "Un semáforo municipal y seccional permite al INE anticipar la abstención de 2027 y dirigir sus herramientas a donde más rinden",
             FUENTE_CCPC + "; CONEVAL; INEGI, Censo 2020")
    filas = [
        ("Dónde", f"{int(res.loc['E0', 'Mun_Rojo'])} municipios con {res.loc['E0', 'LN_Rojo_mill']:.1f} millones de electores superarían 58% de abstención en 2027 si no se interviene."),
        ("Por qué", f"Dos perfiles: el {c['urb_share']:.0f}% de esos electores vive en ciudades de alta movilidad; el resto, en municipios indígenas de Oaxaca."),
        ("Qué tan confiable", f"Probado hacia atrás: con datos hasta 2018 habría anticipado el {retro.loc[2021, 'Decil_real_en_rojo_o_naranja_%']:.0f}% de los municipios de mayor abstención de 2021."),
        ("Qué hacer", "Usar las herramientas que el INE ya tiene —módulos itinerantes, educación cívica, enfoque intercultural, coordinación con OPL— donde el semáforo las indica."),
        ("Cuánto rinde", f"Con el mismo presupuesto, priorizar reduce {c['red1'] / c['red2']:.1f} veces más la abstención de la población en riesgo que repartir parejo."),
    ]
    y = 1.95
    for k, (lab, txt) in enumerate(filas):
        D.text(s, X0, y, 2.6, 0.8, lab, size=16, color=NAVY, bold=True, anchor=MSO_ANCHOR.MIDDLE)
        D.text(s, X0 + 2.8, y, TW - 2.8, 0.8, txt, size=15, color=INK, anchor=MSO_ANCHOR.MIDDLE)
        if k < len(filas) - 1:
            D.rule(s, X0, y + 0.92, TW)
        y += 0.98
    s.notes_slide.notes_text_frame.text = (
        "Empezamos por la respuesta. Dónde: 238 municipios en rojo. Por qué: dos perfiles muy distintos. "
        "Qué tan confiable: lo probamos hacia atrás. Qué hacer: herramientas que el INE ya tiene. "
        "Cuánto rinde: más del doble con el mismo presupuesto. El resto de la presentación respalda cada punto.")

    # 3. Situación
    s = D.slide()
    nat = c["nat"]
    D.chrome(s, "Situación",
             "2027 será una elección intermedia, el tipo de elección en el que más gente deja de votar, sobre todo entre jóvenes",
             FUENTE_CCPC + "; La Jornada y El Congresista (2026)")
    D.image(s, FIG / "deck_tendencia.png", X0, 1.95, w=7.4)
    xs = X0 + 7.9
    D.stat(s, xs, 1.95, 4.2, f"{100 * nat.ABST_NIV[[2009, 2015, 2021]].min():.0f}–{100 * nat.ABST_NIV[[2009, 2015, 2021]].max():.0f}%",
           f"de abstención en las intermedias, contra {100 * nat.ABST_NIV[[2012, 2018, 2024]].min():.0f}–{100 * nat.ABST_NIV[[2012, 2018, 2024]].max():.0f}% en las presidenciales")
    D.stat(s, xs, 3.55, 4.2, f"+{100 * (nat.ABST_JOV_NIV - nat.ABST_NIV).min():.0f} a {100 * (nat.ABST_JOV_NIV - nat.ABST_NIV).max():.0f} pp",
           "más abstención entre jóvenes de 18 a 29 años en cada elección", color=BLUE)
    D.stat(s, xs, 5.15, 4.2, "17", "gubernaturas concurrentes en 2027; la elección judicial se pospuso a 2028")
    s.notes_slide.notes_text_frame.text = (
        "La abstención sube en cada intermedia: 56, 53 y 48 por ciento, contra 38 a 40 en presidenciales. "
        "Los jóvenes siempre están 8 a 11 puntos arriba. 2027 es intermedia, con 17 gubernaturas concurrentes: "
        "es justo el momento en que una estrategia preventiva tiene más margen.")

    # 4. Dónde
    s = D.slide()
    D.chrome(s, "Dónde",
             f"Sin intervención, {int(res.loc['E0', 'Mun_Rojo'])} municipios con {res.loc['E0', 'LN_Rojo_mill']:.1f} millones de electores superarían 58% de abstención en 2027",
             FUENTE_CCPC + "; INEGI, Marco Geoestadístico. Proyección del modelo híbrido, escenario inercial")
    D.image(s, FIG / "deck_mapa.png", X0, 1.9, h=4.85)
    xt = 8.35
    D.text(s, xt, 1.95, 4.4, 0.35, [[("Nivel", {"bold": True, "color": GRAY}), ]], size=12)
    D.text(s, xt + 2.1, 1.95, 1.0, 0.35, "Municipios", size=12, color=GRAY, bold=True, align=PP_ALIGN.RIGHT)
    D.text(s, xt + 3.1, 1.95, 1.3, 0.35, "Electores", size=12, color=GRAY, bold=True, align=PP_ALIGN.RIGHT)
    rangos = {"Rojo": "58% o más", "Naranja": "50 a 58%", "Amarillo": "40 a 50%", "Verde": "menos de 40%"}
    y = 2.45
    for k in ["Rojo", "Naranja", "Amarillo", "Verde"]:
        D.box(s, xt, y + 0.08, 0.28, 0.28, fill=SEM[k], shape=MSO_SHAPE.OVAL)
        D.text(s, xt + 0.42, y, 1.7, 0.45, [[(k, {"bold": True}), (f"\n{rangos[k]}", {"size": 11, "color": GRAY})]], size=14)
        D.text(s, xt + 2.1, y, 1.0, 0.45, f"{int(res.loc['E0', f'Mun_{k}']):,}", size=16, bold=True, align=PP_ALIGN.RIGHT)
        D.text(s, xt + 3.1, y, 1.3, 0.45, f"{res.loc['E0', f'LN_{k}_mill']:.1f} M", size=16, bold=True, align=PP_ALIGN.RIGHT)
        y += 0.85
    D.text(s, xt, 5.95, 4.4, 0.8, f"Abstención nacional proyectada: {c['abst27']:.1f}%. Umbrales fijos: una intervención sí puede bajar de color a un municipio.",
           size=12, color=GRAY)
    s.notes_slide.notes_text_frame.text = (
        "Este es el semáforo 2027 sin intervención. Rojo es 58 por ciento o más de abstención proyectada: 238 municipios, "
        "13.6 millones de electores. Se ve la frontera norte, el Bajío, Quintana Roo. Los umbrales son fijos, "
        "así que una intervención efectiva sí puede bajar a un municipio de color.")

    # 5. Por qué
    s = D.slide()
    D.chrome(s, "Por qué",
             f"El riesgo tiene dos perfiles: el {c['urb_share']:.0f}% de los electores en rojo vive en ciudades que reciben población de otros estados",
             FUENTE_CCPC + "; INEGI, Censo de Población y Vivienda 2020 (ITER)")
    cards = [
        ("Urbano de alta movilidad", f"{c['urb_n']} municipios · {c['urb_ln']:.1f} M de electores",
         [(f"{c['nacoe_u']:.0f}%", f"nació en otra entidad (nacional: {c['nacoe_n']:.0f}%)"),
          (f"+{c['crec_u']:.0f}%", f"creció su lista nominal 2012–2024 (nacional: +{c['crec_n']:.0f}%)")],
         "Tijuana, Juárez, Mexicali, Benito Juárez (Cancún), Tlaquepaque, Chimalhuacán"),
        ("Municipios indígenas de Oaxaca", f"{c['peq_oax']} municipios · {c['peq_ln']:.0f} mil electores",
         [(f"{c['hli_p']:.0f}%", f"habla una lengua indígena (nacional: {c['hli_n']:.0f}%)"),
          ("Alto", "rezago social; mayoría elige autoridades por sistemas normativos indígenas")],
         "Municipios de menos de 5 mil electores"),
    ]
    for k, (tit, sub, stats, ej) in enumerate(cards):
        x = X0 + k * 6.2
        D.box(s, x, 1.95, 5.9, 4.75)
        D.text(s, x + 0.35, 2.15, 5.2, 0.45, tit, size=20, color=NAVY, bold=True)
        D.text(s, x + 0.35, 2.62, 5.2, 0.35, sub, size=14, color=GRAY)
        yy = 3.2
        for big, lab in stats:
            D.text(s, x + 0.35, yy, 1.9, 0.8, big, size=36, color=NAVY if k == 0 else BLUE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
            D.text(s, x + 2.3, yy, 3.3, 0.8, lab, size=14, anchor=MSO_ANCHOR.MIDDLE)
            yy += 1.05
        D.text(s, x + 0.35, 5.6, 5.2, 0.8, ej, size=12, color=GRAY)
    s.notes_slide.notes_text_frame.text = (
        "El rojo no es un solo problema. 95 por ciento de esos electores vive en ciudades que reciben gente de otros estados: "
        "26 por ciento nació en otra entidad y su lista nominal creció 46 por ciento en doce años. Es gente que probablemente "
        "vota lejos de donde vive. El otro perfil son municipios pequeños de Oaxaca, casi la mitad hablante de lengua indígena. "
        "Dos problemas distintos, dos soluciones distintas. Y ojo: el rezago social casi no explica la abstención.")

    # 6. Confiabilidad
    s = D.slide()
    D.chrome(s, "Qué tan confiable",
             f"Probado hacia atrás: con datos hasta 2018, el semáforo habría anticipado {retro.loc[2021, 'Decil_real_en_rojo_o_naranja_%'] / 10:.0f} de cada 10 municipios de mayor abstención en 2021",
             FUENTE_CCPC + ". Backtest temporal: entrenar hasta T-3 y predecir T, sin información posterior")
    trio = [(f"{retro.loc[2021, 'Decil_real_en_rojo_o_naranja_%']:.0f}% · {retro.loc[2024, 'Decil_real_en_rojo_o_naranja_%']:.0f}%",
             "de los municipios con mayor abstención real (decil superior) estaban en rojo o naranja · 2021 y 2024"),
            (f"{retro.loc[2021, 'Rojos_que_quedaron_en_cuartil_real_%']:.0f}% · {retro.loc[2024, 'Rojos_que_quedaron_en_cuartil_real_%']:.0f}%",
             "de los marcados en rojo terminaron en el cuartil de mayor abstención · 2021 y 2024"),
            ("< 2%", "de los municipios en verde terminó entre los de mayor abstención")]
    for k, (big, lab) in enumerate(trio):
        x = X0 + k * 4.1
        D.stat(s, x, 2.05, 3.8, big, lab, big_size=40, label_size=14)
    D.rule(s, X0, 4.05, TW)
    D.text(s, X0, 4.3, TW, 0.4, "Cómo se construyó", size=16, color=NAVY, bold=True)
    pasos = [
        ("Modelo híbrido", "Ridge + Gradient Boosting combinados con la persistencia histórica de cada municipio."),
        ("Sin información del futuro", "Cada elección se predice solo con datos publicados antes de ella."),
        (f"Error de {c['mae21']:.1f} y {c['mae24']:.1f} pp", f"en 2021 y 2024 (ponderado por electores); ubica al {c['prec_ln']:.0f}% de las personas del quintil de mayor riesgo."),
    ]
    for k, (t1, t2) in enumerate(pasos):
        x = X0 + k * 4.1
        D.text(s, x, 4.8, 3.8, 1.6, [[(t1, {"bold": True, "color": INK})], [(t2, {"color": GRAY})]], size=14, spacing=1.15)
    s.notes_slide.notes_text_frame.text = (
        "¿Por qué creerle? Hicimos lo que el INE habría hecho: con datos hasta 2018 construimos el semáforo de 2021. "
        "Siete de cada diez municipios con mayor abstención ya estaban en rojo o naranja, y ocho de cada diez rojos terminaron "
        "efectivamente entre los de mayor abstención. En 2024 fue todavía mejor. El modelo nunca ve información del futuro.")

    # 7. Cuánto rinde
    s = D.slide()
    D.chrome(s, "Cuánto rinde",
             f"Con el mismo presupuesto, priorizar con el semáforo reduce {c['red1'] / c['red2']:.1f} veces más la abstención de la población en riesgo",
             "Simulación Data Insert sobre la proyección 2027. Efecto supuesto: +5 pp en la participación de 18–29 años donde se interviene")
    D.image(s, FIG / "deck_presupuesto.png", X0, 1.95, w=7.4)
    xs = X0 + 7.9
    D.stat(s, xs, 1.95, 4.2, f"{c['red1']:.2f} vs {c['red2']:.2f} pp", "reducción de abstención en municipios rojos y naranjas: priorizado vs uniforme", big_size=34)
    D.stat(s, xs, 3.55, 4.2, f"{res.loc['E1', 'Votos_recuperados'] / 1e3:,.0f} mil", "votos recuperados en ambos casos: lo que cambia es dónde", big_size=34, color=BLUE)
    D.stat(s, xs, 5.15, 4.2, f"{c['pres_rojo']:.0f}%", "de los jóvenes del país basta para cubrir todos los municipios rojos", big_size=34)
    s.notes_slide.notes_text_frame.text = (
        "Simulamos una intervención con el mismo presupuesto de dos formas. Ambas recuperan los mismos 586 mil votos, "
        "pero priorizada reduce la abstención de la población en riesgo 2.2 veces más, y es la única que reduce la desigualdad "
        "territorial. Para cubrir todos los municipios rojos basta llegar al 15 por ciento de los jóvenes del país. "
        "El efecto de 5 puntos es un supuesto; la ventaja se mantiene de 2 a 10 puntos.")

    # 8. Qué hacer
    s = D.slide()
    D.chrome(s, "Qué hacer",
             "El INE ya tiene las herramientas: el semáforo indica cuál usar en cada territorio",
             "Matriz de acción Data Insert para los municipios rojos y naranjas; INEGI, Censo 2020")
    filas = [
        ("Alta movilidad", "Nacida en otra entidad sobre el promedio, o ≥4% llegó desde 2015",
         "Módulos de Atención Ciudadana itinerantes para actualizar domicilio; casillas especiales donde hay población flotante",
         "Actualización de domicilio y campaña digital"),
        ("Brecha juvenil alta", "Jóvenes 20–29 votan muy por debajo del municipio",
         "Educación cívica en universidades, centros de trabajo y canales digitales de las secciones prioritarias",
         "Retención del voto juvenil (20-29)"),
        ("Lengua indígena", "≥40% de la población habla una lengua indígena",
         "Enfoque intercultural con autoridades comunitarias y el organismo electoral local; materiales en lenguas indígenas",
         "Enfoque intercultural"),
        ("Riesgo general", "Resto de municipios rojos y naranjas",
         "Campaña conjunta con el OPL, aprovechando las elecciones locales concurrentes",
         "Movilización general con el OPL"),
    ]
    cols = [(X0, 2.6, "Perfil"), (X0 + 2.75, 5.95, "Herramienta del INE"), (X0 + 8.9, 1.45, "Municipios"), (X0 + 10.45, 1.65, "Electores")]
    for x, w, lab in cols:
        D.text(s, x, 1.95, w, 0.35, lab, size=12, color=GRAY, bold=True,
               align=PP_ALIGN.RIGHT if lab in ("Municipios", "Electores") else PP_ALIGN.LEFT)
    y = 2.4
    for k, (perfil, crit, palanca, clave) in enumerate(filas):
        if k % 2 == 0:
            D.box(s, X0 - 0.1, y - 0.08, TW + 0.2, 1.04)
        D.text(s, X0, y, 2.6, 0.9, [[(perfil, {"bold": True, "color": NAVY, "size": 15})], [(crit, {"size": 11, "color": GRAY})]], size=14)
        D.text(s, X0 + 2.75, y, 5.95, 0.9, palanca, size=14, anchor=MSO_ANCHOR.MIDDLE)
        D.text(s, X0 + 8.9, y, 1.45, 0.9, f"{int(mat.loc[clave, 'Municipios'])}", size=18, bold=True, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        D.text(s, X0 + 10.45, y, 1.65, 0.9, f"{mat.loc[clave, 'Electores_mill']:.1f} M", size=18, bold=True, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        y += 1.08
    D.text(s, X0, 6.5, TW, 0.35, "Todas arrancan como piloto evaluable: grupos de comparación medidos con los Conteos Censales de 2027.",
           size=13, color=NAVY, bold=True)
    s.notes_slide.notes_text_frame.text = (
        "No proponemos inventar programas. El INE ya tiene módulos de atención ciudadana, casillas especiales, educación cívica "
        "y coordinación con los OPL. El semáforo dice cuál usar dónde: en ciudades de alta movilidad, módulos itinerantes para "
        "actualizar el domicilio, que es la causa que detectamos; donde la brecha juvenil es alta, educación cívica; en "
        "municipios indígenas, enfoque intercultural. Todo como piloto que se pueda medir.")

    # 9. Cómo operarlo
    s = D.slide()
    dt = c["dtop"]
    D.chrome(s, "Cómo operarlo",
             f"En cada distrito, una de cada cinco secciones concentra la mitad de los jóvenes que se abstendrían",
             FUENTE_CCPC + "; proyección por sección y distrito federal (marco distrital 2023, vigente en 2027)")
    D.image(s, FIG / "deck_tablero_distrito.png", X0, 1.95, w=8.1)
    xs = X0 + 8.5
    D.stat(s, xs, 1.95, 3.6, f"{c['mitad']:.0f} de {c['secc']:.0f}", "secciones reúnen la mitad de los jóvenes que se abstendrían, en el distrito típico", big_size=34)
    D.stat(s, xs, 3.55, 3.6, f"{c['dist_n'].get('Rojo', 0)} + {c['dist_n'].get('Naranja', 0)}", "distritos federales en rojo y naranja de 300", big_size=34, color=BLUE)
    D.text(s, X0, 5.35, 8.1, 1.4,
           [[("Tablero entregado: ", {"bold": True, "color": NAVY}),
             ("simulador con efecto y presupuesto ajustables, mapas sincronizados sin y con intervención, ficha por municipio con su "
              "porqué, y la lista de secciones prioritarias de cada Junta Distrital. Funciona sin conexión.", {})]], size=14, spacing=1.15)
    D.text(s, xs, 5.15, 3.6, 1.4, f"Ejemplo: distrito {int(dt.DEF):02d} de Baja California, {int(dt.SECC_MITAD_JOV_ABST)} de {int(dt.SECCIONES)} secciones concentran la mitad de {dt.JOV_ABST_ESP / 1e3:,.0f} mil jóvenes.",
           size=13, color=GRAY)
    s.notes_slide.notes_text_frame.text = (
        "El INE opera por Juntas Distritales y secciones, así que bajamos el semáforo a las 70 mil secciones y 300 distritos. "
        "En el distrito típico, 48 de 218 secciones concentran la mitad de los jóvenes que se abstendrían: una brigada sabe "
        "exactamente a dónde ir. Todo está en un tablero que funciona sin internet.")

    # 10. Próximos pasos
    s = D.slide(dark=True)
    D.text(s, X0, 0.38, 8, 0.3, "PRÓXIMOS PASOS", size=11, color="AFC3E0", bold=True)
    D.text(s, X0, 0.68, TW, 1.05, "Proponemos arrancar con un piloto evaluable antes de la jornada electoral de junio de 2027",
           size=24, color="FFFFFF", bold=True, spacing=1.0)
    pasos = [
        ("Nov – dic 2026", "Validar", "Revisar el semáforo y las listas seccionales con Juntas Locales y Distritales."),
        ("Ene – mar 2027", "Actualizar", "Módulos itinerantes en secciones de alta movilidad, antes del cierre de la lista nominal."),
        ("Abr – jun 2027", "Movilizar", "Educación cívica, enfoque intercultural y campañas con OPL, con grupos de comparación."),
        ("Después de la jornada", "Medir", "Estimar el efecto real con los Conteos Censales 2027 y recalibrar el semáforo para 2030."),
    ]
    for k, (cuando, verbo, txt) in enumerate(pasos):
        x = X0 + k * 3.08
        D.box(s, x, 2.2, 2.85, 3.3, fill="15335A")
        D.text(s, x + 0.25, 2.4, 2.4, 0.35, cuando, size=12, color="AFC3E0", bold=True)
        D.text(s, x + 0.25, 2.8, 2.4, 0.55, f"{k + 1}. {verbo}", size=22, color="FFFFFF", bold=True)
        D.text(s, x + 0.25, 3.5, 2.4, 1.9, txt, size=14, color="D6E0EE", spacing=1.15)
    D.text(s, X0, 5.95, TW, 0.8,
           [[("Código abierto y reproducible: ", {"bold": True, "color": "FFFFFF"}),
             ("el semáforo se actualiza en menos de dos minutos con cada corte de la lista nominal · github.com/PBJulian/semaforo-abstencion-2027", {"color": "D6E0EE"})]],
           size=14, spacing=1.15)
    D.text(s, W - X0 - 0.6, 6.95, 0.6, 0.3, str(D.n), size=10, color="AFC3E0", align=PP_ALIGN.RIGHT)
    s.notes_slide.notes_text_frame.text = (
        "Proponemos cuatro pasos: validar con las Juntas en noviembre y diciembre, actualizar domicilios antes del cierre de la "
        "lista nominal, movilizar en primavera con grupos de comparación, y medir después de la jornada con los conteos censales. "
        "Así el INE no solo actúa: aprende qué funciona. Todo el código es abierto y se actualiza en dos minutos. Gracias.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    D.p.save(OUT)
    print("Presentación:", OUT, D.n, "láminas")


if __name__ == "__main__":
    main()
