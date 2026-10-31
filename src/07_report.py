"""
07_report.py
Genera el Reporte metodológico y preventivo (DOCX) a partir de los resultados del pipeline,
para que todas las cifras del texto coincidan con la base de datos y el mapa.

Formato: carta, Calibri 11, interlineado 1.5.
Salida: entregables/Reporte_metodologico_preventivo_DataInsert.docx
"""
from pathlib import Path

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUTS = ROOT / "outputs"
FIG = OUTS / "figures"
OUT = ROOT / "entregables" / "Reporte_metodologico_preventivo_DataInsert.docx"

EQUIPO = "Data Insert"
INTEGRANTES = ["Aldo Sebastian Altamirano Vázquez", "Carlo Kiliano Ferrera Guadarrama",
               "Isaac Pancardo Botello", "José Julián Pérez Bustamante"]
SEMAFORO_HEX = {"Verde": "0CA30C", "Amarillo": "FAB219", "Naranja": "EC835A", "Rojo": "D03B3B"}
ESTADOS = {1: "Aguascalientes", 2: "Baja California", 3: "Baja California Sur", 4: "Campeche",
           5: "Coahuila", 6: "Colima", 7: "Chiapas", 8: "Chihuahua", 9: "Ciudad de México",
           10: "Durango", 11: "Guanajuato", 12: "Guerrero", 13: "Hidalgo", 14: "Jalisco",
           15: "México", 16: "Michoacán", 17: "Morelos", 18: "Nayarit", 19: "Nuevo León",
           20: "Oaxaca", 21: "Puebla", 22: "Querétaro", 23: "Quintana Roo", 24: "San Luis Potosí",
           25: "Sinaloa", 26: "Sonora", 27: "Tabasco", 28: "Tamaulipas", 29: "Tlaxcala",
           30: "Veracruz", 31: "Yucatán", 32: "Zacatecas"}
ESTADOS_ABR = {1: "Ags.", 2: "B.C.", 3: "B.C.S.", 4: "Camp.", 5: "Coah.", 6: "Col.", 7: "Chis.", 8: "Chih.",
               9: "CDMX", 10: "Dgo.", 11: "Gto.", 12: "Gro.", 13: "Hgo.", 14: "Jal.", 15: "Méx.", 16: "Mich.",
               17: "Mor.", 18: "Nay.", 19: "N.L.", 20: "Oax.", 21: "Pue.", 22: "Qro.", 23: "Q. Roo", 24: "S.L.P.",
               25: "Sin.", 26: "Son.", 27: "Tab.", 28: "Tamps.", 29: "Tlax.", 30: "Ver.", 31: "Yuc.", 32: "Zac."}
INK = RGBColor(0x0B, 0x0B, 0x0B)
ACCENT = RGBColor(0x1C, 0x5C, 0xAB)


def lista(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1]


# ------------------------------------------------------------------ cifras
def cifras():
    d = pd.read_parquet(PROC / "escenarios_2027.parquet")
    panel = pd.read_parquet(PROC / "panel_municipal_dev.parquet")
    cat = pd.read_parquet(PROC / "municipios_2024.parquet")
    sec = pd.read_parquet(PROC / "ccpc_seccion.parquet", columns=["AELEC", "EDOCVE", "SECCION", "GEDAD", "SEXO", "LN", "SV", "NV"])
    c = {"d": d,
         "nat": pd.read_csv(OUTS / "abstencion_nacional.csv").set_index("AELEC"),
         "met": pd.read_csv(OUTS / "metricas_backtest.csv"),
         "res": pd.read_csv(OUTS / "resumen_escenarios.csv").set_index("Escenario"),
         "sens": pd.read_csv(OUTS / "sensibilidad_efecto.csv"),
         "umb": pd.read_csv(OUTS / "umbrales_semaforo.csv"),
         "curva": pd.read_csv(OUTS / "curva_presupuesto.csv"),
         "conf": pd.read_csv(OUTS / "conformal.csv"),
         "confval": pd.read_csv(OUTS / "conformal_validacion.csv").set_index("Calibracion"),
         "rob": pd.read_csv(OUTS / "robustez_modelo.csv")}

    c["n_mun"] = len(d)
    c["n_sec_2024"] = sec[sec.AELEC == 2024][["EDOCVE", "SECCION"]].drop_duplicates().shape[0]
    c["ln_2024"] = sec[sec.AELEC == 2024].LN.sum()
    t = sec.groupby("AELEC")[["SV", "NV"]].sum()
    c["part_nac"] = 100 * t.SV / (t.SV + t.NV)
    g = sec.groupby(["AELEC", "GEDAD"], observed=True)[["SV", "NV"]].sum()
    c["abst_edad"] = (100 * g.NV / (g.SV + g.NV)).unstack("AELEC")
    s = sec[sec.SEXO < 2].groupby(["AELEC", "SEXO"])[["SV", "NV"]].sum()
    ps = (100 * s.SV / (s.SV + s.NV)).unstack("SEXO")
    c["brecha_sexo"] = ps[1] - ps[0]
    c["part_sexo"] = ps
    w = panel.pivot_table(index=["EDOCVE", "MPIO24"], columns="AELEC", values="DEV")
    c["corr_dev"] = w.corr()
    x = panel[panel.AELEC == 2021].merge(cat, on=["EDOCVE", "MPIO24"])
    c["corr_irs"] = x[["DEV", "IRS"]].corr().iloc[0, 1]
    c["corr_urb"] = x[["DEV", "SH_URB"]].corr().iloc[0, 1]

    met = c["met"]
    c["hib"] = met[met.Modelo == "Hibrido"].set_index("Evaluacion")
    c["t3"] = met[met.Modelo == "Ingenuo_T-3"].set_index("Evaluacion")
    c["t6"] = met[met.Modelo == "Ingenuo_T-6"].set_index("Evaluacion")
    c["mae_prom"] = met.pivot(index="Modelo", columns="Evaluacion", values="MAE_pond_LN_pp").mean(axis=1)

    c["abst27"] = 100 * np.average(d.ABST_E0, weights=d.LN_27)
    c["abst27_jov"] = 100 * np.average(d.ABST_JOV_E0, weights=d.LN_JOV_27)
    c["ln_jov_foco"] = (d.LN_JOV_27 * d.INTERVENIDO_E1).sum()
    c["ln_jov_tot"] = d.LN_JOV_27.sum()
    c["pres_rojo"] = d.LN_JOV_27[d.NIVEL_E0 == 3].sum() / c["ln_jov_tot"]
    c["n_foco"] = int(d.INTERVENIDO_E1.sum())
    c["cambio5"] = int((d.CAMBIO_VS_2021 >= 0.05).sum())

    rojo = d[d.SEMAFORO_E0 == "Rojo"].sort_values("LN_27", ascending=False)
    c["rojo"] = rojo
    urb = rojo[rojo.LN_27 >= 20000]
    peq = rojo[rojo.LN_27 < 5000]
    c["rojo_urb_n"], c["rojo_urb_share"] = len(urb), urb.LN_27.sum() / rojo.LN_27.sum()
    c["rojo_peq_n"], c["rojo_peq_oax"] = len(peq), int((peq.EDOCVE == 20).sum())
    c["rojo_peq_ln"] = peq.LN_27.sum()
    ln = panel.pivot_table(index=["EDOCVE", "MPIO24"], columns="AELEC", values="LN")
    u = ln.loc[urb.set_index(["EDOCVE", "MPIO24"]).index]
    c["crec_urb"] = 100 * (u[2024].sum() / u[2012].sum() - 1)
    c["crec_nac"] = 100 * (ln[2024].sum() / ln[2012].sum() - 1)
    rn = d[d.NIVEL_E0 >= 2].sort_values("LN_27", ascending=False)
    c["rn_100_share"] = rn.head(100).LN_27.sum() / rn.LN_27.sum()
    c["rn_ln"] = rn.LN_27.sum()

    perfil = d.groupby("SEMAFORO_E0", observed=True).agg(
        Municipios=("NOM24", "size"), LN=("LN_27", "sum"), Abst=("ABST_E0", "median"),
        Urbana=("SH_URB1", "median"), IRS=("IRS", "median"), Brecha=("BRECHA_JOV_27", "median"),
        Prob=("PROB_ROJO", "median"), Tam=("LN_27", "median"))
    c["perfil"] = perfil.reindex(["Verde", "Amarillo", "Naranja", "Rojo"])

    est = d.groupby("EDOCVE").apply(lambda t: t.LN_27[t.NIVEL_E0 >= 2].sum() / t.LN_27.sum())
    c["est_rn"] = est.sort_values(ascending=False)
    c["est_alto_txt"] = lista(ESTADOS[e] for e in c["est_rn"][c["est_rn"] > 0.85].index)

    # Regla de "deterioro" descartada: ¿los aumentos vs 2021 reflejan la anomalía de 2021 (regresión a la media)?
    otros = w[[2009, 2012, 2015, 2018, 2024]].mean(axis=1)
    anom = (w[2021] - otros).rename("ANOM21")
    x = d.set_index(["EDOCVE", "MPIO24"]).join(anom)
    c["corr_anom"] = x[["CAMBIO_VS_2021", "ANOM21"]].corr().iloc[0, 1]
    c["retro"] = pd.read_csv(OUTS / "retro_semaforo.csv").query("Semaforo == 'Modelo híbrido'").set_index("Eleccion")
    vs = pd.read_csv(OUTS / "validacion_secciones.csv")
    c["vsec_base"] = vs.MAE_pond_pp.iloc[0]
    c["vsec"] = vs.iloc[1:].sort_values("MAE_pond_pp").iloc[0]
    dist = pd.read_parquet(PROC / "distritos_2027.parquet")
    c["dist_n"] = dist.SEMAFORO_2027.value_counts()
    c["dist_mitad"], c["dist_secc"] = dist.SECC_MITAD_JOV_ABST.median(), dist.SECCIONES.median()
    c["dist_top"] = dist.sort_values("JOV_ABST_ESP", ascending=False).iloc[0]
    c["matriz"] = pd.read_csv(OUTS / "matriz_accion.csv").set_index("ACCION")
    censo = pd.read_parquet(PROC / "censo2020_mun.parquet")
    dc = d.merge(censo, on="CVEGEO", how="inner")
    wavg = lambda m, v: 100 * np.average(dc.loc[m, v], weights=dc.loc[m, "POBTOT"])
    urb_m = (dc.NIVEL_E0 == 3) & (dc.LN_27 >= 20000)
    peq_m = (dc.NIVEL_E0 == 3) & (dc.LN_27 < 5000)
    todo = dc.LN_27 > 0
    c["censo"] = {"nacoe_urb": wavg(urb_m, "PCT_NACOE"), "nacoe_nal": wavg(todo, "PCT_NACOE"),
                  "resoe_urb": wavg(urb_m, "PCT_RESOE15"), "resoe_nal": wavg(todo, "PCT_RESOE15"),
                  "hli_peq": wavg(peq_m, "PCT_HLI"), "hli_nal": wavg(todo, "PCT_HLI")}
    cv = c["curva"].pivot(index="Presupuesto_%jov", columns="Estrategia", values="Reduccion_abst_zona_riesgo_pp")
    c["cv"] = cv
    return c


# ------------------------------------------------------------------ utilidades de formato
def set_cell_bg(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_row_flag(row, tag):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement(tag)
    el.set(qn("w:val"), "true")
    trPr.append(el)


def add_page_number(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for kind, text in [("begin", None), (None, "PAGE"), ("end", None)]:
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)
    run.font.size = Pt(9)


class Reporte:
    def __init__(self):
        self.doc = Document()
        self.fig_n = 0
        self.tab_n = 0
        sec = self.doc.sections[0]
        sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
        for side in ["left_margin", "right_margin", "top_margin", "bottom_margin"]:
            setattr(sec, side, Cm(2.5))
        st = self.doc.styles["Normal"]
        st.font.name = "Calibri"
        st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        st.font.size = Pt(11)
        st.paragraph_format.line_spacing = 1.5
        st.paragraph_format.space_after = Pt(6)
        for lvl, size in [(1, 14), (2, 12)]:
            h = self.doc.styles[f"Heading {lvl}"]
            h.font.name = "Calibri"
            rf = h.element.rPr.rFonts
            for a in ["w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"]:
                rf.set(qn(a), "Calibri")
            for a in ["w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"]:
                if rf.get(qn(a)) is not None:
                    del rf.attrib[qn(a)]
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.color.rgb = ACCENT if lvl == 1 else INK
            h.paragraph_format.space_before = Pt(12 if lvl == 1 else 8)
            h.paragraph_format.space_after = Pt(4)
            h.paragraph_format.line_spacing = 1.15
            h.paragraph_format.keep_with_next = True
        cap = self.doc.styles["Caption"]
        cap.font.name = "Calibri"
        cap.font.size = Pt(9)
        cap.font.italic = False
        cap.font.color.rgb = RGBColor(0x52, 0x51, 0x4E)
        cap.paragraph_format.line_spacing = 1.0
        add_page_number(sec)

    def h1(self, t):
        self.doc.add_heading(t, level=1)

    def h2(self, t):
        self.doc.add_heading(t, level=2)

    def p(self, text, bold_lead=None, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        par = self.doc.add_paragraph()
        par.alignment = align
        if bold_lead:
            par.add_run(bold_lead).bold = True
        par.add_run(text)
        return par

    def bullets(self, items):
        for it in items:
            par = self.doc.add_paragraph(style="List Bullet")
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            par.paragraph_format.space_after = Pt(2)
            if isinstance(it, tuple):
                par.add_run(it[0]).bold = True
                par.add_run(it[1])
            else:
                par.add_run(it)

    def numbered(self, items):
        # Numeración manual: cada lista reinicia en 1
        for n, it in enumerate(items, 1):
            par = self.doc.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            par.paragraph_format.left_indent = Cm(0.75)
            par.paragraph_format.first_line_indent = Cm(-0.75)
            par.paragraph_format.space_after = Pt(3)
            par.add_run(f"{n}.\t{it[0]}").bold = True
            par.add_run(it[1])

    def figura(self, file, caption, width=12.0):
        self.fig_n += 1
        par = self.doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = True
        par.paragraph_format.line_spacing = 1.0
        par.add_run().add_picture(str(FIG / file), width=Cm(width))
        cap = self.doc.add_paragraph(f"Figura {self.fig_n}. {caption}", style="Caption")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def tabla(self, df, caption, widths=None, fills=None, font=9):
        self.tab_n += 1
        cap = self.doc.add_paragraph(f"Tabla {self.tab_n}. {caption}", style="Caption")
        cap.paragraph_format.keep_with_next = True
        t = self.doc.add_table(rows=1, cols=len(df.columns))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        set_row_flag(t.rows[0], "w:tblHeader")
        for i, col in enumerate(df.columns):
            cell = t.rows[0].cells[i]
            cell.text = ""
            r = cell.paragraphs[0].add_run(str(col))
            r.bold = True
            r.font.size = Pt(font)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            set_cell_bg(cell, "1C5CAB")
        for ri, row in enumerate(df.itertuples(index=False)):
            new = t.add_row()
            set_row_flag(new, "w:cantSplit")
            for i, v in enumerate(row):
                cell = new.cells[i]
                cell.text = ""
                r = cell.paragraphs[0].add_run(str(v))
                r.font.size = Pt(font)
                if fills and (ri, i) in fills:
                    set_cell_bg(cell, fills[(ri, i)])
                    r.font.color.rgb = INK if fills[(ri, i)] == SEMAFORO_HEX["Amarillo"] else RGBColor(0xFF, 0xFF, 0xFF)
                    r.bold = True
        for ri, row in enumerate(t.rows):
            for i, cell in enumerate(row.cells):
                for par in cell.paragraphs:
                    par.paragraph_format.line_spacing = 1.0
                    par.paragraph_format.space_after = Pt(0)
                    # Mantener juntas las filas (salvo la última) para que la tabla no se parta entre páginas
                    par.paragraph_format.keep_with_next = ri < len(t.rows) - 1
                if widths:
                    cell.width = Cm(widths[i])
        if widths:
            for i, col in enumerate(t.columns):
                col.width = Cm(widths[i])
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)

    def salto(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ------------------------------------------------------------------ contenido
def portada(R):
    doc = R.doc
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Hackea la participación: Datos que construyen democracia")
    r.font.size = Pt(12)
    r.font.color.rgb = RGBColor(0x52, 0x51, 0x4E)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.1
    r = p.add_run("Semáforo de Riesgo de Abstención 2027")
    r.bold = True
    r.font.size = Pt(26)
    r.font.color.rgb = ACCENT
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Modelo predictivo municipal, escenarios de intervención y recomendaciones preventivas")
    r.font.size = Pt(14)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Reporte metodológico y preventivo · Reto 2: Predicción y escenarios de riesgo de abstención")
    r.font.size = Pt(11)
    r.italic = True
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"Equipo: {EQUIPO}")
    r.bold = True
    r.font.size = Pt(13)
    for n in INTEGRANTES:
        p = doc.add_paragraph(n)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph("Fuentes: INE, Conteos Censales de Participación Ciudadana 2009–2024; CONEVAL, Índice de "
                          "Rezago Social 2010, 2015 y 2020; INEGI, Marco Geoestadístico")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].font.size = Pt(9)
    p = doc.add_paragraph("31 de octubre de 2026")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_break(WD_BREAK.PAGE)       # el salto va en el último párrafo para no generar una hoja en blanco


def resumen(R, c):
    res, hib = c["res"], c["hib"]
    z0, z1, z2 = (res.loc[k, "Abst_zona_riesgo_%"] for k in ["E0", "E1", "E2"])
    R.h1("Resumen ejecutivo")
    R.p(f"Este reporte presenta un modelo para anticipar dónde podría concentrarse la abstención en la elección federal "
        f"intermedia de 2027 y cómo reducirla con una intervención focalizada. Se construyó un panel de {c['n_mun']:,} "
        f"municipios con los Conteos Censales de Participación Ciudadana (CCPC) del INE de 2009 a 2024 (sección electoral, "
        f"sexo y edad simple), complementado con indicadores de rezago social del CONEVAL. No se utilizó ningún dato "
        f"personal: toda la información es agregada.")
    R.bullets([
        ("Patrón histórico. ", "La abstención nacional sube en las elecciones intermedias (55.9% en 2009, 52.9% en 2015 y "
                               "48.2% en 2021) frente a las presidenciales (37.9%, 37.6% y 40.3%). Las personas de 20 a 29 años "
                               "se abstienen entre 8 y 12 puntos más que el promedio."),
        ("Modelo validado. ", f"Un modelo híbrido (Ridge y Gradient Boosting combinados con persistencia histórica, con "
                              f"información espacial de municipios vecinos) se validó con un backtest temporal sin fuga de "
                              f"información. Su error medio ponderado por lista nominal es de {hib.loc[2021, 'MAE_pond_LN_pp']:.1f} pp "
                              f"(2021) y {hib.loc[2024, 'MAE_pond_LN_pp']:.1f} pp (2024), y localiza al "
                              f"{100 * hib.Precision_top20_LN.min():.0f}% de las personas que viven en el quintil de "
                              f"municipios de mayor riesgo."),
        ("Semáforo 2027. ", f"Sin intervención, se proyecta una abstención nacional de {c['abst27']:.1f}%. "
                            f"{int(res.loc['E0', 'Mun_Rojo'])} municipios quedan en rojo y {int(res.loc['E0', 'Mun_Naranja'])} "
                            f"en naranja, con {c['rn_ln'] / 1e6:.1f} millones de personas en la lista nominal."),
        ("Escenarios. ", f"Con el mismo presupuesto, una campaña juvenil focalizada con el semáforo reduce la abstención de "
                         f"la población en riesgo {(z0 - z1) / (z0 - z2):.1f} veces más que repartir el esfuerzo de manera "
                         f"uniforme ({z0 - z1:.2f} frente a {z0 - z2:.2f} pp), y es la única opción que reduce la desigualdad "
                         f"territorial."),
        ("Dos perfiles de riesgo. ", f"El {100 * c['rojo_urb_share']:.0f}% de las personas en zona roja vive en municipios "
                                     f"urbanos de alta movilidad: la frontera norte, las periferias metropolitanas, el Bajío y "
                                     f"los polos turísticos. Un segundo grupo, pequeño en población, son {c['rojo_peq_oax']} "
                                     f"municipios de Oaxaca con menos de 5 mil electores. Cada perfil requiere una estrategia "
                                     f"distinta."),
    ])


def introduccion(R):
    R.h1("1. Introducción y planteamiento del problema")
    R.p("La participación no se distribuye de manera homogénea en el territorio. Para el INE, anticipar dónde podría caer "
        "permite dirigir con anticipación los recursos de promoción del voto, educación cívica y actualización del padrón "
        "hacia donde más se necesitan, en lugar de distribuirlos de forma uniforme o reactiva.")
    R.p("La pregunta que guía este trabajo es: ¿qué zonas podrían presentar mayor abstención en la elección federal de 2027 "
        "si no se interviene y cuánto podría reducirse ese riesgo con una intervención focalizada? Siguiendo lo que pide el "
        "Reto 2, el trabajo tiene cuatro componentes: un modelo predictivo de abstención municipal basado en tendencias "
        "históricas y variables sociodemográficas agregadas (secciones 2 a 4); un semáforo de riesgo territorial (sección 5); "
        "un escenario inercial y dos con intervención que usan el mismo presupuesto (sección 6); y recomendaciones preventivas "
        "y de priorización de recursos (sección 7).")
    R.p("El horizonte es la elección intermedia de 2027, la próxima elección federal. Las intermedias tienen históricamente "
        "la menor participación, así que es el momento en que una estrategia preventiva tiene más margen de impacto.")


def datos(R, c):
    pn = c["part_nac"]
    R.h1("2. Datos, unidad de análisis y variables")
    R.h2("2.1 Fuentes y validación")
    R.p(f"La fuente principal son los Conteos Censales de Participación Ciudadana (CCPC) 2009–2024 del INE. Para cada una de "
        f"las seis elecciones federales reportan, por sección electoral, sexo y edad simple, la lista nominal (LN) y los "
        f"registros con marca de voto (SV), sin marca (NV) y no especificados (NS). Se procesaron 192 archivos (6 elecciones × "
        f"32 entidades); en 2024 cubren {c['n_sec_2024']:,} secciones y {c['ln_2024'] / 1e6:.1f} millones de registros. Como "
        f"fuentes complementarias se usaron el Índice de Rezago Social del CONEVAL (ediciones 2010, 2015 y 2020) y el Marco "
        f"Geoestadístico del INEGI, para la cartografía y la vecindad entre municipios.")
    R.p(f"Las tasas nacionales de participación que calcula nuestro procesamiento ({lista(f'{v:.1f}%' for v in pn.values)} "
        f"para 2009–2024) coinciden con las que publica la plataforma de los CCPC del INE. Esto confirma que la lectura y "
        f"agregación de los datos es correcta.", "Validación. ")
    R.p("La abstención se define como NV / (SV + NV). Se excluyen los registros no especificados, que corresponden a "
        "cuadernillos no disponibles o sin marcas (de 0.2% a 6.8% de la LN según el año), para no confundir la falta de "
        "información con la abstención.", "Indicador. ")

    R.h2("2.2 Unidad de análisis y armonización territorial")
    R.p("La unidad de análisis es el municipio. Es lo bastante desagregado para orientar la operación de las Juntas "
        "Distritales, permite cruzar información sociodemográfica oficial y es estable en el tiempo, a diferencia de los "
        "distritos federales, que se redibujaron en 2017 y 2023.")
    R.p(f"Durante la preparación de los datos se detectó que las claves municipales del INE no son estables: se crearon "
        f"municipios nuevos y algunas claves se reasignaron (por ejemplo, en Chiapas). Para no comparar municipios distintos "
        f"con la misma clave, cada sección histórica se asignó al municipio al que pertenece en el marco geográfico de 2024. "
        f"Con esto se asigna más del 99.9% de la LN de cada año y se obtiene un panel balanceado de {c['n_mun']:,} "
        f"municipios × 6 elecciones.")
    R.p("Las claves del CONEVAL y del INEGI son distintas de las del INE. El cruce se hizo por nombre normalizado dentro de "
        "cada entidad, revisando uno por uno los casos no exactos y los municipios homónimos (por ejemplo, los dos San Juan "
        "Mixtepec de Oaxaca). Las ediciones 2010 y 2015 se unieron por la clave del INEGI, que no se reasigna entre ediciones. "
        "Los municipios creados después de cada edición reciben la mediana estatal y una variable indicadora.")

    R.h2("2.3 Variables del modelo")
    vars_ = pd.DataFrame([
        ("Historial electoral", "Abstención relativa a la entidad en la elección previa (T-3), en la previa del mismo tipo (T-6), promedio histórico y cambio reciente", "CCPC"),
        ("Juventud", "Abstención relativa de 18 a 29 años (T-3 y T-6) y brecha de participación juvenil", "CCPC"),
        ("Demografía electoral", "% de LN de 18–29 y de 60 o más años; tamaño (log) y crecimiento de la LN", "CCPC"),
        ("Género", "Brecha de participación mujeres – hombres", "CCPC"),
        ("Territorio", "% de LN en secciones urbanas y rurales; entidad federativa", "CCPC"),
        ("Contexto espacial", "Abstención relativa de los municipios vecinos (T-3 y T-6), ponderada por LN", "CCPC + INEGI"),
        ("Rezago social", "Índice de rezago social, analfabetismo, educación básica incompleta, sin salud, carencias de vivienda (edición vigente en cada elección)", "CONEVAL"),
        ("Calidad y contexto", "% de registros no especificados; tipo de elección e interacciones", "CCPC"),
    ], columns=["Dimensión", "Variables", "Fuente"])
    R.tabla(vars_, "Variables utilizadas en el modelo de riesgo", widths=[3.2, 10.4, 2.4])
    R.p("Las bases que se entregan son agregadas a nivel municipal y no contienen información de personas identificables, "
        "como pide el reto.", "Protección de datos. ")


def diagnostico(R, c):
    ae, bs, cd = c["abst_edad"], c["brecha_sexo"], c["corr_dev"]
    R.h1("3. Diagnóstico: patrones históricos de abstención")
    R.p("La Figura 1 muestra el rasgo más marcado de la serie: la abstención sube en las elecciones intermedias y baja en "
        "las presidenciales. La abstención juvenil sigue el mismo ciclo, pero siempre entre 8 y 11 puntos por encima del "
        "total. La intermedia de 2021, con 48.2%, fue la de menor abstención entre las intermedias de la serie, lo que "
        "coincide con que hubo elecciones locales concurrentes en las 32 entidades.")
    R.figura("f1_abstencion_nacional.png", "Abstención nacional total y juvenil (18–29 años), 2009–2024. Fuente: elaboración propia con CCPC-INE.")
    R.p(f"Por edad (Figura 2), las personas de 18 y 19 años participan más que las de 20 a 29: en 2024, su abstención fue "
        f"de {ae.loc['18-19', 2024]:.1f}%, frente a {ae.loc['25-29', 2024]:.1f}% en el grupo de 25 a 29 años. Esto sugiere un "
        f"efecto de «primer voto» que se pierde en los años siguientes. Por sexo, las mujeres participan sistemáticamente más "
        f"que los hombres, con una brecha de entre {bs.min():.0f} y {bs.max():.0f} puntos en todas las elecciones.")
    R.figura("f2_abstencion_edad.png", "Abstención por grupo de edad, elecciones 2021 y 2024. Fuente: elaboración propia con CCPC-INE.")
    R.p(f"La posición de cada municipio respecto a su entidad es muy persistente. La correlación de la abstención relativa "
        f"municipal entre 2018 y 2021 es de {cd.loc[2018, 2021]:.2f}, y entre 2021 y 2024, de {cd.loc[2021, 2024]:.2f}. El "
        f"patrón territorial de la abstención es estructural y, por lo tanto, predecible.", "Persistencia territorial. ")
    R.p(f"Contra lo que podría esperarse, la abstención relativa casi no se relaciona con el rezago social (correlación de "
        f"{c['corr_irs']:.2f} en 2021) y aumenta ligeramente con la proporción de lista nominal urbana ({c['corr_urb']:.2f}). "
        f"Como se verá en la sección 5, la mayor parte de la población en riesgo vive en municipios urbanos de alta movilidad.",
        "Abstención y rezago social. ")


def metodologia(R, c):
    met, hib, t3, mp, rob = c["met"], c["hib"], c["t3"], c["mae_prom"], c["rob"]
    cf, cfv = c["conf"], c["confval"]
    R.h1("4. Metodología del modelo de riesgo")
    R.h2("4.1 Descomposición del problema y supuesto para 2027")
    R.p("La abstención de un municipio combina dos componentes. El primero es un choque común a los municipios de una "
        "entidad: la concurrencia con elecciones locales, la competencia por la gubernatura y el contexto político. El "
        "segundo es la posición estructural del municipio dentro de su entidad. El primero depende del contexto de cada "
        "elección y no puede inferirse de manera confiable con datos territoriales. En una primera versión, que predecía la "
        "abstención contra el promedio nacional, el modelo no superaba a la regla simple de persistencia, justamente porque "
        "los choques estatales de 2015 no se repitieron en 2021.")
    R.p("Por eso, el modelo predice la desviación de cada municipio respecto a la abstención de su entidad (DEV), y el nivel "
        "estatal de 2027 se fija como supuesto explícito: el de la intermedia de 2021. El supuesto es razonable porque 2027 "
        "tendrá una concurrencia similar a la de 2021, que fue concurrente en las 32 entidades con 15 gubernaturas: se "
        "renovarán la Cámara de Diputados, 17 gubernaturas, congresos locales y ayuntamientos (El Congresista, 2026). La "
        "elección judicial, que inicialmente iba a coincidir, se pospuso a 2028 (La Jornada, 2026).")
    par = R.p("Abstención 2027 (municipio m) = Abstención 2021 (entidad de m) + DEV proyectada 2027 (m)", align=WD_ALIGN_PARAGRAPH.CENTER)
    par.runs[0].italic = True
    R.p("Esta separación es transparente: el INE puede sustituir el supuesto estatal por otro sin reentrenar el modelo.")

    R.h2("4.2 Modelos y validación temporal")
    R.p("Se compararon tres reglas simples de referencia (persistencia de la elección anterior, T-3; persistencia de la "
        "anterior del mismo tipo, T-6; y promedio histórico) con dos modelos de aprendizaje automático: una regresión Ridge, "
        "lineal e interpretable (Hoerl y Kennard, 1970), y un Gradient Boosting de árboles (Friedman, 2001), ambos en "
        "scikit-learn (Pedregosa et al., 2011). Los modelos se ponderan por la raíz de la lista nominal, para dar más peso a "
        "los municipios donde vive más gente sin ignorar a los pequeños.")
    R.p("La validación fue temporal, nunca aleatoria: se entrenó con 2012–2018 para predecir 2021 y con 2012–2021 para "
        "predecir 2024. Cada variable usa solo información disponible antes de la elección que se predice. Por ejemplo, para "
        "2018 y 2021 se usa la edición 2015 del CONEVAL, no la de 2020.")
    R.p(f"Ninguna regla simple funcionó bien en ambas evaluaciones: T-3 explica bien 2021 (R² de {t3.loc[2021, 'R2']:.2f}) "
        f"pero no 2024 ({t3.loc[2024, 'R2']:.2f}), y con T-6 ocurre lo contrario ({c['t6'].loc[2021, 'R2']:.2f} y "
        f"{c['t6'].loc[2024, 'R2']:.2f}). Como no es posible saber de antemano cuál funcionará en 2027, se adoptó un modelo híbrido que "
        f"combina pronósticos (Bates y Granger, 1969): la mitad es el promedio de Ridge y Gradient Boosting, y la otra mitad, "
        f"el promedio de las dos persistencias. El híbrido tiene el menor error promedio de todas las alternativas "
        f"({mp['Hibrido']:.2f} pp, contra {mp['Ingenuo_T-3']:.2f} pp de T-3 y {mp['Ingenuo_T-6']:.2f} pp de T-6) y es el más "
        f"estable entre evaluaciones (Figura 3 y Tabla 2).")
    R.figura("f3_backtest.png", "Error absoluto medio ponderado por lista nominal (pp), por modelo y año de evaluación.")
    nombres = {"Ingenuo_T-3": "Persistencia T-3", "Ingenuo_T-6": "Persistencia T-6", "Ingenuo_promedio": "Promedio histórico",
               "Ridge": "Ridge", "GBM": "Gradient Boosting", "Ensamble": "Ensamble ML", "Hibrido": "Híbrido (final)"}
    t = met.assign(Modelo=met.Modelo.map(nombres)).pivot(
        index="Modelo", columns="Evaluacion", values=["MAE_pond_LN_pp", "R2", "Precision_top20", "Precision_top20_LN"])
    t = t.loc[list(nombres.values())]
    tab = pd.DataFrame({
        "Modelo": t.index,
        "MAE pond. 2021": t[("MAE_pond_LN_pp", 2021)].map("{:.2f}".format).values,
        "MAE pond. 2024": t[("MAE_pond_LN_pp", 2024)].map("{:.2f}".format).values,
        "R² 2021 / 2024": [f"{a:.2f} / {b:.2f}" for a, b in zip(t[("R2", 2021)], t[("R2", 2024)])],
        "Top 20% municipios 2021 / 2024": [f"{a:.0%} / {b:.0%}" for a, b in zip(t[("Precision_top20", 2021)], t[("Precision_top20", 2024)])],
        "Top 20% personas 2021 / 2024": [f"{a:.0%} / {b:.0%}" for a, b in zip(t[("Precision_top20_LN", 2021)], t[("Precision_top20_LN", 2024)])],
    })
    R.tabla(tab, "Métricas del backtest temporal. «Top 20%»: proporción del quintil de mayor abstención real que el modelo "
                 "identifica, contada en municipios y en personas (lista nominal)",
            widths=[3.4, 2.1, 2.1, 2.5, 3.0, 3.0], font=8.5)
    R.p(f"En número de municipios, la persistencia T-3 identificó mejor el quintil de mayor riesgo de 2021 "
        f"({100 * t3.loc[2021, 'Precision_top20']:.0f}% contra {100 * hib.loc[2021, 'Precision_top20']:.0f}% del híbrido). Medido "
        f"en personas, que es lo relevante para asignar recursos, la relación se invierte: el híbrido localiza al "
        f"{100 * hib.loc[2021, 'Precision_top20_LN']:.0f}% de la población del quintil de mayor riesgo, contra "
        f"{100 * t3.loc[2021, 'Precision_top20_LN']:.0f}% de T-3. La persistencia acierta en municipios pequeños, pero falla en "
        f"los grandes.", "Una precisión que depende de cómo se cuente. ")

    R.h2("4.3 Robustez")
    r = rob[rob.Modelo == "Hibrido"].pivot(index="Variante", columns="Evaluacion", values=["MAE_pond_LN_pp", "Precision_top20_LN"])
    tr = pd.DataFrame({
        "Variante": r.index,
        "MAE pond. 2021": r[("MAE_pond_LN_pp", 2021)].map("{:.2f}".format).values,
        "MAE pond. 2024": r[("MAE_pond_LN_pp", 2024)].map("{:.2f}".format).values,
        "Promedio": r["MAE_pond_LN_pp"].mean(axis=1).map("{:.2f}".format).values,
        "Top 20% personas (prom.)": r["Precision_top20_LN"].mean(axis=1).map("{:.0%}".format).values,
    })
    R.p("La Tabla 3 compara variantes del modelo híbrido con el mismo backtest. Usar el CONEVAL 2020 para todas las "
        "elecciones (variante A) implicaba usar información posterior a 2012–2018. Al usar la edición vigente en cada elección "
        "(C), el error prácticamente no cambia, así que esa fuga no inflaba los resultados. Quitar el CONEVAL (B) casi no "
        "empeora el modelo, lo que confirma el diagnóstico de la sección 3. El contexto espacial (D) no cambia el error, pero "
        "mejora ligeramente la identificación del quintil de riesgo. La ponderación por tamaño (E) mejora ambos años y es el "
        "cambio de mayor impacto.")
    R.tabla(tr, "Análisis de robustez del modelo híbrido (MAE ponderado por lista nominal, en pp)", widths=[5.4, 2.4, 2.4, 2.2, 3.4])

    R.h2("4.4 Incertidumbre e importancia de variables")
    q = cf.set_index("TAM").Q90_pp
    R.p(f"Para cuantificar la incertidumbre se calcularon intervalos de predicción conformales (Vovk, Gammerman y Shafer, "
        f"2005), por terciles de tamaño de la lista nominal. Al validarlos fuera de muestra se encontró que los errores "
        f"dependen del tipo de elección: calibrados con 2021, cubren el {cfv.loc[2021, 'Cobertura_%']:.0f}% de los casos de "
        f"2024, pero calibrados con 2024 cubren solo el {cfv.loc[2024, 'Cobertura_%']:.0f}% de 2021. Las intermedias son más "
        f"difíciles de predecir. Por eso, para 2027 los intervalos se calibran con los errores de la intermedia de 2021. La "
        f"semiamplitud del intervalo al 90% es de ±{q[2]:.1f} pp en municipios con más de 17.5 mil electores, ±{q[1]:.1f} pp "
        f"entre 5 mil y 17.5 mil, y ±{q[0]:.1f} pp en los más pequeños. Con los mismos errores se estima la probabilidad de "
        f"que cada municipio quede en rojo.")
    R.p("La importancia de las variables se midió por permutación fuera de muestra (Breiman, 2001): se entrenó hasta 2021 y "
        "se midió cuánto aumenta el error en 2024 al desordenar cada variable. Dominan las variables de historial electoral, "
        "en especial la abstención juvenil relativa; el rezago social aporta poco. Que el historial juvenil sea tan "
        "informativo justifica que la intervención simulada se dirija a jóvenes. Para cada municipio, además, se descompone "
        "la proyección en la contribución de cada familia de variables (sección 5.4).")


def semaforo(R, c):
    d, umb, res, perf = c["d"], c["umb"], c["res"], c["perfil"]
    R.h1("5. Semáforo de riesgo territorial")
    R.h2("5.1 Definición")
    R.p("El semáforo clasifica a cada municipio según su abstención proyectada para 2027 en el escenario inercial. Los cortes "
        "son umbrales absolutos, fijados en los percentiles 50, 75 y 90 de esa distribución y redondeados a puntos enteros. "
        "Que sean absolutos es clave: con colores asignados por ranking siempre habría el mismo número de municipios en rojo; "
        "con umbrales fijos, una intervención efectiva sí puede bajar de color a un municipio.")
    nivel = pd.DataFrame({
        "Nivel": ["Verde", "Amarillo", "Naranja", "Rojo"],
        "Abstención proyectada 2027": [f"Menos de {umb['Hasta_%'][0]:.0f}%", f"{umb['Desde_%'][1]:.0f}% a {umb['Hasta_%'][1]:.0f}%",
                                       f"{umb['Desde_%'][2]:.0f}% a {umb['Hasta_%'][2]:.0f}%", f"{umb['Desde_%'][3]:.0f}% o más"],
        "Municipios": [f"{int(res.loc['E0', f'Mun_{k}']):,}" for k in ["Verde", "Amarillo", "Naranja", "Rojo"]],
        "Lista nominal (mill.)": [f"{res.loc['E0', f'LN_{k}_mill']:.1f}" for k in ["Verde", "Amarillo", "Naranja", "Rojo"]],
        "Acción sugerida": ["Monitoreo ordinario", "Vigilancia y acciones de bajo costo", "Intervención focalizada",
                            "Intervención prioritaria e intensiva"],
    })
    R.tabla(nivel, "Semáforo de riesgo de abstención 2027: umbrales y resultados del escenario inercial",
            widths=[2.0, 3.6, 2.2, 2.6, 5.6], fills={(i, 0): SEMAFORO_HEX[k] for i, k in enumerate(nivel.Nivel)})
    R.p(f"Se evaluó una regla adicional que subía un nivel a los municipios cuya abstención proyectada empeoraba 5 puntos o "
        f"más respecto a 2021 ({c['cambio5']} municipios). Se descartó porque esos aumentos tenían una correlación de {c['corr_anom']:.2f} "
        f"con la anomalía del propio municipio en 2021: eran sobre todo municipios pequeños con una abstención atípicamente "
        f"baja ese año, que regresan a su nivel habitual. Era regresión a la media, no deterioro. El cambio respecto a 2021 se "
        f"reporta en la base de datos como indicador informativo.", "Regla descartada. ")
    rt = c["retro"]
    R.p(f"Se repitió el procedimiento completo como si el INE lo hubiera aplicado antes de cada elección, con datos "
        f"anteriores a ella. Con información hasta 2018, el semáforo de 2021 habría marcado en rojo o naranja al "
        f"{rt.loc[2021, 'Decil_real_en_rojo_o_naranja_%']:.0f}% de los municipios que terminaron en el decil de mayor abstención, "
        f"y el {rt.loc[2021, 'Rojos_que_quedaron_en_cuartil_real_%']:.0f}% de los que marcó en rojo quedó efectivamente en el "
        f"cuartil de mayor abstención. Para 2024 esas cifras fueron {rt.loc[2024, 'Decil_real_en_rojo_o_naranja_%']:.0f}% y "
        f"{rt.loc[2024, 'Rojos_que_quedaron_en_cuartil_real_%']:.0f}%. Menos del 2% de los municipios en verde terminó en el decil "
        f"de mayor abstención.", "Validación retrospectiva. ")

    R.h2("5.2 Resultados: dos perfiles de riesgo")
    rojo = c["rojo"]
    top = ", ".join(f"{r.NOM24} ({ESTADOS_ABR[r.EDOCVE]})" for r in rojo.head(8).itertuples())
    R.p(f"En el escenario inercial, la abstención nacional proyectada para 2027 es de {c['abst27']:.1f}%, y de {c['abst27_jov']:.1f}% "
        f"entre jóvenes de 18 a 29 años. {int(res.loc['E0', 'Mun_Rojo'])} municipios quedan en rojo, con "
        f"{res.loc['E0', 'LN_Rojo_mill']:.1f} millones de personas. Dentro de ellos se distinguen dos perfiles:")
    R.bullets([
        ("Urbano de alta movilidad. ", f"{c['rojo_urb_n']} municipios con más de 20 mil electores concentran el "
                                       f"{100 * c['rojo_urb_share']:.0f}% de la población en rojo. Los más grandes son {top}. "
                                       f"Son ciudades fronterizas, periferias metropolitanas, el corredor industrial del Bajío "
                                       f"y polos turísticos. Su lista nominal creció {c['crec_urb']:.0f}% entre 2012 y 2024, contra "
                                       f"{c['crec_nac']:.0f}% a nivel nacional. El Censo 2020 lo confirma: el {c['censo']['nacoe_urb']:.0f}% de "
                                       f"su población nació en otra entidad ({c['censo']['nacoe_nal']:.0f}% nacional) y el "
                                       f"{c['censo']['resoe_urb']:.1f}% vivía en otra entidad en 2015 ({c['censo']['resoe_nal']:.1f}% nacional)."),
        ("Municipios pequeños de Oaxaca. ", f"{c['rojo_peq_n']} municipios con menos de 5 mil electores, de los cuales "
                                       f"{c['rojo_peq_oax']} están en Oaxaca, entidad donde la mayoría de los municipios eligen "
                                       f"a sus autoridades por sistemas normativos indígenas. Suman apenas "
                                       f"{c['rojo_peq_ln'] / 1e3:,.0f} mil electores; el {c['censo']['hli_peq']:.0f}% de su población "
                                       f"habla una lengua indígena ({c['censo']['hli_nal']:.0f}% nacional) y su rezago social es "
                                       f"alto. Requieren un enfoque intercultural."),
    ])
    pf = pd.DataFrame({
        "Nivel": perf.index,
        "Municipios": perf.Municipios.map("{:,.0f}".format).values,
        "Abst. 2027 (mediana)": (100 * perf.Abst).map("{:.1f}%".format).values,
        "Tamaño LN (mediana)": perf.Tam.map("{:,.0f}".format).values,
        "% LN urbana": (100 * perf.Urbana).map("{:.0f}%".format).values,
        "Brecha juvenil (pp)": (100 * perf.Brecha).map("{:.1f}".format).values,
        "Índice rezago social": perf.IRS.map("{:.2f}".format).values,
        "Prob. rojo (mediana)": (100 * perf.Prob).map("{:.0f}%".format).values,
    })
    R.tabla(pf, "Perfil mediano de los municipios por nivel del semáforo (escenario inercial)",
            widths=[1.9, 1.9, 2.1, 2.1, 1.9, 2.1, 2.1, 2.0], fills={(i, 0): SEMAFORO_HEX[k] for i, k in enumerate(pf.Nivel)}, font=8.5)
    R.p(f"Las medianas de la Tabla 5 reflejan la mezcla: el municipio rojo típico es pequeño y con rezago alto, por el grupo "
        f"oaxaqueño, aunque la mayoría de la población en rojo es urbana. La brecha juvenil crece de forma sostenida con el "
        f"nivel de riesgo. A nivel estatal, {c['est_alto_txt']} tienen más del 85% de su lista nominal en "
        f"municipios rojos o naranjas. Esto se debe sobre todo a un nivel estatal de abstención históricamente alto, por lo "
        f"que ahí conviene una estrategia de alcance estatal.")

    R.h2("5.3 Del semáforo a la operación: distritos y secciones")
    dn, dt, vb = c["dist_n"], c["dist_top"], c["vsec"]
    R.p(f"El INE opera a través de sus 300 Juntas Distritales y planea en secciones. Por eso la proyección municipal se "
        f"desagrega por sección electoral: cada sección hereda la proyección de su municipio más su desviación persistente "
        f"dentro de él (promedio de 2021 y 2024, contraída en secciones pequeñas). Esa desviación es estable: predecir la de "
        f"2024 con la de 2018 y 2021 tiene una correlación de {vb.Correlacion:.2f} y reduce el error de {c['vsec_base']:.1f} a "
        f"{vb.MAE_pond_pp:.1f} pp frente a suponer secciones homogéneas. Al agregar por distrito federal (marco 2023, vigente "
        f"en 2027), {dn.get('Rojo', 0)} distritos quedan en rojo y {dn.get('Naranja', 0)} en naranja.")
    R.p(f"Para cada distrito se ordenan las secciones por el número de jóvenes que se abstendrían (electores de 18 a 29 años "
        f"× abstención juvenil proyectada). La concentración es alta: en el distrito típico, {c['dist_mitad']:.0f} de "
        f"{c['dist_secc']:.0f} secciones reúnen la mitad de esas personas. Por ejemplo, en el distrito {int(dt.DEF):02d} de "
        f"{ESTADOS[int(dt.EDOCVE)]}, el de mayor volumen, {int(dt.SECC_MITAD_JOV_ABST)} de {int(dt.SECCIONES)} secciones "
        f"concentran la mitad de {dt.JOV_ABST_ESP / 1e3:,.0f} mil jóvenes que se abstendrían. La lista completa se entrega "
        f"en la base de datos y se consulta por distrito en el tablero.")

    R.h2("5.4 Por qué y qué hacer: explicación municipal y matriz de acción")
    R.p("Para cada municipio, la proyección se descompone en la contribución de cada familia de variables (historial, "
        "abstención juvenil, municipios vecinos, rezago social, estructura de la lista nominal), con el componente lineal del "
        "modelo. Así el tablero responde por qué un municipio está en riesgo, y no solo dónde. Con esa información y el Censo "
        "2020 se asigna a cada municipio rojo o naranja una acción sugerida, con reglas transparentes y en este orden: enfoque "
        "intercultural si al menos 40% de la población habla una lengua indígena; actualización de domicilio y campaña digital "
        "si tiene alta movilidad (población nacida en otra entidad por encima del promedio nacional, o al menos 4% llegada "
        "desde 2015); retención del voto juvenil si su brecha juvenil está por encima de la mediana; y movilización general con "
        "el organismo electoral local en el resto (Tabla 6).")
    m = c["matriz"].reindex(["Actualización de domicilio y campaña digital", "Retención del voto juvenil (20-29)",
                             "Enfoque intercultural", "Movilización general con el OPL"])
    R.tabla(pd.DataFrame({"Acción sugerida": m.index, "Municipios": m.Municipios.astype(int).values,
                          "De ellos en rojo": m.Rojos.astype(int).values,
                          "Electores (mill.)": m.Electores_mill.map("{:.1f}".format).values}),
            "Matriz de acción para los municipios rojos y naranjas del escenario inercial", widths=[7.4, 2.6, 2.8, 3.0])


def escenarios(R, c):
    res, sens, cv = c["res"], c["sens"], c["cv"]
    R.h1("6. Simulación de escenarios")
    R.h2("6.1 Diseño")
    R.p("La intervención hipotética es una campaña de promoción del voto juvenil (18 a 29 años) que eleva la participación de "
        "ese grupo en los municipios donde se aplica. El efecto base es de +5 puntos porcentuales, coherente con la evidencia "
        "experimental sobre campañas de movilización, que reporta efectos de pocos puntos porcentuales, mayores en el "
        "contacto directo que en los medios impersonales (Green y Gerber, 2019). El efecto sobre la abstención total de cada "
        "municipio es proporcional al peso de los jóvenes en su lista nominal.")
    R.bullets([
        ("E0 · Inercial. ", "Sin intervención: la proyección del modelo."),
        ("E1 · Focalizado. ", f"La campaña se aplica en los {c['n_foco']} municipios rojos y naranjas. Alcanza a "
                              f"{c['ln_jov_foco'] / 1e6:.1f} millones de jóvenes, el {100 * c['ln_jov_foco'] / c['ln_jov_tot']:.0f}% "
                              f"del total nacional."),
        ("E2 · Uniforme. ", f"El mismo presupuesto (el mismo número de jóvenes alcanzados) repartido en todo el país: cada "
                            f"municipio recibe una cobertura del {100 * c['ln_jov_foco'] / c['ln_jov_tot']:.0f}% de sus jóvenes."),
    ])
    R.p("Con un efecto lineal, E1 y E2 recuperan exactamente los mismos votos, porque alcanzan al mismo número de jóvenes. La "
        "comparación relevante no es cuántos votos se recuperan, sino dónde. La métrica principal es, por lo tanto, la "
        "reducción de la abstención en la población que el semáforo identifica en riesgo (municipios rojos y naranjas del "
        "escenario inercial).", "Qué se compara. ")

    R.h2("6.2 Resultados")
    rows = [("Abstención nacional", "Abst_nacional_%", "{:.2f}%"), ("Votos recuperados", "Votos_recuperados", "{:,.0f}"),
            ("Abstención en zona de riesgo (rojo y naranja)", "Abst_zona_riesgo_%", "{:.2f}%"),
            ("Abstención en el resto del país", "Abst_resto_%", "{:.2f}%"),
            ("Desviación estándar territorial (pp)", "Desv_est_abst_pp", "{:.2f}"),
            ("Municipios en rojo", "Mun_Rojo", "{:.0f}"), ("Lista nominal en rojo (mill.)", "LN_Rojo_mill", "{:.1f}")]
    t = pd.DataFrame({"Indicador": [r[0] for r in rows],
                      **{lab: [("—" if (k == "E0" and col == "Votos_recuperados") else f.format(res.loc[k, col])) for _, col, f in rows]
                         for k, lab in [("E0", "E0 Inercial"), ("E1", "E1 Focalizado"), ("E2", "E2 Uniforme")]}})
    R.tabla(t, "Comparación de escenarios con efecto base de +5 pp en la participación juvenil", widths=[6.6, 3.0, 3.0, 3.0])
    z0, z1, z2 = (res.loc[k, "Abst_zona_riesgo_%"] for k in ["E0", "E1", "E2"])
    R.p(f"Ambas intervenciones recuperan unos {res.loc['E1', 'Votos_recuperados'] / 1e3:,.0f} mil votos. Pero en la "
        f"población en riesgo, la estrategia focalizada reduce la abstención {z0 - z1:.2f} puntos, contra {z0 - z2:.2f} de la "
        f"uniforme ({(z0 - z1) / (z0 - z2):.1f} veces más). La uniforme gasta más de la mitad de su efecto en municipios de menor riesgo. "
        f"Además, solo la focalizada reduce la dispersión territorial de la abstención (de {res.loc['E0', 'Desv_est_abst_pp']:.2f} "
        f"a {res.loc['E1', 'Desv_est_abst_pp']:.2f} pp). Las personas en zona roja bajan de {res.loc['E0', 'LN_Rojo_mill']:.1f} a "
        f"{res.loc['E1', 'LN_Rojo_mill']:.1f} millones con E1, y a {res.loc['E2', 'LN_Rojo_mill']:.1f} con E2. Este último indicador "
        f"se presenta con cautela, porque depende de cuántos municipios quedan cerca del umbral.")
    R.figura("f5_semaforo_escenarios.png", "Distribución del semáforo por escenario, en número de municipios y en lista nominal.", width=11)
    R.p(f"La Figura 5 repite la comparación para distintos tamaños de presupuesto. En la estrategia priorizada, la campaña se "
        f"asigna primero a los municipios con mayor abstención proyectada. Con presupuestos de hasta la mitad de los jóvenes "
        f"del país, priorizar logra al menos el doble de reducción en la población en riesgo: con 20% de los jóvenes alcanzados, "
        f"{cv.loc[20, 'Priorizado']:.2f} pp frente a {cv.loc[20, 'Uniforme']:.2f} pp. Cubrir a todos los jóvenes de los "
        f"municipios rojos requiere alcanzar solo al {100 * c['pres_rojo']:.0f}% de los jóvenes del país.", "Presupuesto. ")
    R.figura("f6_presupuesto.png", "Reducción de la abstención en la población de municipios rojo y naranja, según el presupuesto y la estrategia.")
    s = sens.set_index(["Escenario", "Efecto_pp"])["Abst_zona_riesgo_%"]
    R.p(f"Como el efecto se modela de forma lineal, todos los resultados escalan en proporción al efecto supuesto, y la "
        f"ventaja de priorizar no depende de su valor exacto. Con un efecto conservador de +2 pp, la reducción en la población "
        f"en riesgo sería de {s['E0', 2.0] - s['E1', 2.0]:.2f} pp (focalizado) contra {s['E0', 2.0] - s['E2', 2.0]:.2f} pp "
        f"(uniforme); con +10 pp, de {s['E0', 10.0] - s['E1', 10.0]:.2f} contra {s['E0', 10.0] - s['E2', 10.0]:.2f} pp.",
        "Sensibilidad al efecto. ")
    R.p("El tablero interactivo (mapa_escenarios_2027.html) compara en dos mapas sincronizados la situación sin y con "
        "intervención, y funciona como simulador: permite ajustar el efecto supuesto y el presupuesto, elegir la estrategia, "
        "filtrar por entidad y consultar la ficha de cada municipio (historial, proyección, intervalo y probabilidad de quedar "
        "en rojo). Las capas también se entregan en GeoJSON y GeoPackage.", "Mapa de escenarios. ", align=WD_ALIGN_PARAGRAPH.LEFT)


def recomendaciones(R, c):
    R.h1("7. Recomendaciones preventivas y de priorización de recursos")
    R.numbered([
        ("Adoptar el semáforo para asignar recursos. ",
         f"Distribuir los recursos de promoción del voto según el semáforo y no de forma uniforme: con el mismo presupuesto, "
         f"el efecto en la población en riesgo es más del doble. Los {c['n_foco']} municipios rojos y naranjas concentran "
         f"{c['rn_ln'] / 1e6:.1f} millones de electores, y los 100 más grandes reúnen el {100 * c['rn_100_share']:.0f}%. Cada Junta "
         f"Distrital puede empezar por sus secciones prioritarias, donde se concentran los jóvenes que se abstendrían."),
        ("Retener el voto juvenil con educación cívica en las secciones prioritarias. ",
         "Las personas de 18 y 19 años participan más que las de 20 a 29. Se sugieren acciones en universidades, centros de "
         "trabajo y plataformas digitales, dirigidas a personas de 20 a 29 años en las secciones que concentran a los "
         "jóvenes que se abstendrían."),
        ("Llevar Módulos de Atención Ciudadana itinerantes a las zonas de alta movilidad. ",
         "En las ciudades fronterizas, turísticas y periferias metropolitanas, parte de la abstención registrada puede deberse "
         "a personas que ya no viven en la sección de su credencial. Módulos itinerantes en sus secciones prioritarias, antes "
         "del cierre de la lista nominal, atacan esa causa y mejoran el padrón; donde hay población flotante, conviene "
         "reforzar las casillas especiales."),
        ("Diseñar un enfoque intercultural para los municipios pequeños de Oaxaca. ",
         "En los municipios que se rigen por sistemas normativos indígenas, la promoción del voto federal debe coordinarse con "
         "las autoridades comunitarias y con el organismo electoral local, con materiales en lenguas indígenas y respeto a "
         "sus formas propias de organización."),
        ("Atender la brecha de los hombres jóvenes. ",
         f"Las mujeres participan entre {c['brecha_sexo'].min():.0f} y {c['brecha_sexo'].max():.0f} puntos más que los hombres "
         f"en todas las elecciones. Los mensajes y canales dirigidos a hombres jóvenes (espacios deportivos, laborales y "
         f"digitales) deben ser un componente explícito de la estrategia."),
        ("Coordinar estrategias estatales donde el riesgo es generalizado. ",
         f"En {c['est_alto_txt']}, más del 85% de la lista nominal está en municipios rojos o naranjas. Ahí conviene una "
         f"campaña estatal con el Organismo Público Local, complementaria a la focalización municipal."),
        ("Medir el efecto real con un piloto evaluable. ",
         "El efecto de +5 pp es un supuesto. Se recomienda implementar la intervención de forma escalonada en municipios "
         "comparables de la zona roja, para estimar su efecto real con los Conteos Censales de 2027 y recalibrar el semáforo "
         "para 2030."),
        ("Actualizar el semáforo y revisar los datos incompletos. ",
         "El código es reproducible y corre en minutos; puede actualizarse con cada corte de la lista nominal. Conviene revisar "
         "con las Juntas Locales los 12 municipios sin registros de votación capturados en 2024 y los que tienen muchos "
         "registros no especificados."),
    ])


def limitaciones(R):
    R.h1("8. Limitaciones")
    R.bullets([
        ("Nivel estatal supuesto. ", "La abstención de cada entidad en 2027 se fijó en su nivel de 2021. Un contexto distinto "
                                     "movería todos los municipios de la entidad, aunque no su orden relativo. Los intervalos de "
                                     "predicción cubren el componente municipal, no este supuesto."),
        ("Efecto de la intervención. ", "Es hipotético y lineal. Por eso se presenta un análisis de sensibilidad y se "
                                        "recomienda un piloto evaluable."),
        ("Una sola intermedia para calibrar. ", "Los intervalos de 2027 se calibran con los errores de 2021, la única intermedia "
                                                "evaluable fuera de muestra."),
        ("Cobertura de los CCPC. ", "No incluyen el voto en casillas especiales ni desde el extranjero, por lo que en zonas "
                                    "turísticas o de tránsito la abstención puede estar sobreestimada."),
    ])
    R.p("Todo el flujo, de los archivos públicos del INE, el CONEVAL y el INEGI hasta el mapa y este reporte, se reproduce "
        "con el script run_all.sh en menos de dos minutos (Python: pandas, scikit-learn, geopandas; tablero en Leaflet). Como el reporte "
        "se genera a partir de los resultados, sus cifras coinciden con la base de datos y el mapa.", "Reproducibilidad. ")


def referencias(R):
    R.h1("Referencias")
    refs = [
        "Bates, J. M. y Granger, C. W. J. (1969). The combination of forecasts. Operational Research Quarterly, 20(4), 451–468.",
        "Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5–32.",
        "CONEVAL (2021). Índice de Rezago Social 2020 (y ediciones 2010 y 2015) a nivel municipal. Consejo Nacional de Evaluación de la Política de Desarrollo Social.",
        "El Congresista (2026). INE arranca proceso electoral 2027 que incluye 17 gubernaturas y 31 congresos locales. elcongresista.mx.",
        "Friedman, J. H. (2001). Greedy function approximation: A gradient boosting machine. The Annals of Statistics, 29(5), 1189–1232.",
        "Green, D. P. y Gerber, A. S. (2019). Get Out the Vote: How to Increase Voter Turnout (4.ª ed.). Brookings Institution Press.",
        "Hoerl, A. E. y Kennard, R. W. (1970). Ridge regression: Biased estimation for nonorthogonal problems. Technometrics, 12(1), 55–67.",
        "INEGI (2020). Marco Geoestadístico, división municipal; Censo de Población y Vivienda 2020, Principales resultados por localidad (ITER).",
        "Instituto Nacional Electoral (2024). Conteos Censales de Participación Ciudadana 2009–2024. Datos abiertos, DECEyEC.",
        "La Jornada (1 de junio de 2026). Congreso declara constitucional la reforma que pospone elección del Poder Judicial al 2028.",
        "Pedregosa, F. et al. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825–2830.",
        "Vovk, V., Gammerman, A. y Shafer, G. (2005). Algorithmic Learning in a Random World. Springer.",
    ]
    for r in refs:
        par = R.doc.add_paragraph(r)
        par.paragraph_format.left_indent = Cm(1)
        par.paragraph_format.first_line_indent = Cm(-1)
        par.paragraph_format.line_spacing = 1.0
        par.paragraph_format.space_after = Pt(2)
        par.runs[0].font.size = Pt(10)


def main():
    c = cifras()
    R = Reporte()
    portada(R)
    resumen(R, c)
    introduccion(R)
    datos(R, c)
    diagnostico(R, c)
    metodologia(R, c)
    semaforo(R, c)
    escenarios(R, c)
    recomendaciones(R, c)
    limitaciones(R)
    referencias(R)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    R.doc.save(OUT)
    print("Reporte:", OUT)


if __name__ == "__main__":
    main()
