"""
10_paquete.py
Arma el paquete de entrega: LEEME (PDF) con el mapa de archivos frente a los requisitos de la
convocatoria (Base Sexta) y el zip con carpetas numeradas.

Las cartas firmadas se colocan en entregables/cartas/ (PDF). Si faltan, el script lo advierte.

Salidas:
  entregables/LEEME_DataInsert.pdf
  Data_Insert_Reto2_Prediccion_riesgo_abstencion.zip (en la raíz del proyecto)
"""
import shutil
import subprocess
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
ENT = ROOT / "entregables"
SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
ZIP = ROOT / "Data_Insert_Reto2_Prediccion_riesgo_abstencion.zip"
REPO = "https://github.com/PBJulian/semaforo-abstencion-2027"
NAVY = RGBColor(0x0B, 0x25, 0x45)

# carpeta del zip -> archivos (rutas relativas al proyecto)
ESTRUCTURA = {
    "01_Reporte_metodologico_y_preventivo": ["entregables/Reporte_metodologico_preventivo_DataInsert.pdf"],
    "02_Mapa_de_escenarios": ["entregables/mapa_escenarios_2027.html", "entregables/geo"],
    "03_Base_de_datos_anonimizada": ["entregables/base_datos"],
    "04_Presentacion_ejecutiva": ["entregables/Presentacion_ejecutiva_DataInsert.pdf",
                                  "entregables/Presentacion_ejecutiva_DataInsert.pptx"],
    "05_Codigo_fuente": ["src", "README.md", "requirements.txt", "run_all.sh"],
    "06_Cartas_firmadas": ["entregables/cartas"],
}

REQUISITOS = [
    ("Reporte metodológico y preventivo (10 a 15 cuartillas, PDF)", "01_Reporte_metodologico_y_preventivo",
     "15 páginas con portada y referencias. Variables: sección 2. Semáforo de riesgo territorial: sección 5. "
     "Recomendaciones preventivas y de priorización de recursos: sección 7."),
    ("Mapa de escenarios con y sin intervención (archivo ejecutable y SHP/GeoJSON/GPKG)", "02_Mapa_de_escenarios",
     "mapa_escenarios_2027.html: tablero interactivo; se abre con doble clic en Chrome, Edge o Firefox y funciona sin "
     "internet (solo el mapa base de fondo requiere conexión). geo/: capas GeoJSON y GeoPackage."),
    ("Base de datos anonimizada (CSV / XLSX)", "03_Base_de_datos_anonimizada",
     "XLSX con diccionario de variables y 13 hojas; CSV municipal (2,477 municipios), por distrito (300) y por sección "
     "(70,751), y panel histórico 2009–2024. Solo datos públicos agregados, sin información personal."),
    ("Presentación ejecutiva (máximo 10 diapositivas)", "04_Presentacion_ejecutiva",
     "10 diapositivas en PDF y PPTX editable."),
    ("Código o enlace a un repositorio", "05_Codigo_fuente",
     f"Código en Python reproducible con run_all.sh (ver README.md). Repositorio: {REPO}"),
    ("Carta de cesión de derechos y carta declaratoria de decir verdad", "06_Cartas_firmadas",
     "Firmadas por las cuatro personas integrantes."),
]


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def leeme():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
    for side in ["left_margin", "right_margin", "top_margin", "bottom_margin"]:
        setattr(sec, side, Cm(2.0))
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)

    def par(text, size=10.5, bold=False, color=None, after=4):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.font.size, r.bold = Pt(size), bold
        if color:
            r.font.color.rgb = color
        p.paragraph_format.space_after = Pt(after)
        return p

    par("LÉEME · Equipo Data Insert", 16, True, NAVY, 2)
    par("Hackea la participación · Eje: Predicción y escenarios de riesgo de abstención (Reto 2)", 11, False, None, 2)
    par("Semáforo de Riesgo de Abstención 2027", 11, True, None, 8)
    par("Integrantes: Aldo Sebastian Altamirano Vázquez, Carlo Kiliano Ferrera Guadarrama, Isaac Pancardo Botello "
        "y José Julián Pérez Bustamante.", after=10)
    par("Contenido del paquete y requisitos de la convocatoria (Base Sexta)", 12, True, NAVY, 4)

    t = doc.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    t.autofit = False
    widths = [4.4, 5.6, 7.6]
    for i, h in enumerate(["Requisito", "Carpeta", "Contenido"]):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold, r.font.size = True, Pt(10)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade(c, "0B2545")
    for req, carpeta, nota in REQUISITOS:
        cells = t.add_row().cells
        for i, v in enumerate([req, carpeta, nota]):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(v)
            r.font.size = Pt(9.5)
            r.bold = i == 0
    for row in t.rows:
        for i, c in enumerate(row.cells):
            c.width = Cm(widths[i])
    for i, col in enumerate(t.columns):
        col.width = Cm(widths[i])

    par("", after=4)
    par("Cómo revisarlo en cinco minutos", 12, True, NAVY, 4)
    for txt in [
        "1. Abrir 04_Presentacion_ejecutiva: la historia completa en 10 diapositivas.",
        "2. Abrir 02_Mapa_de_escenarios/mapa_escenarios_2027.html: mover los controles de escenario, efecto y presupuesto; "
        "hacer clic en un municipio para ver su ficha; elegir un distrito federal para ver sus secciones prioritarias.",
        "3. Consultar el detalle metodológico en el reporte y los datos en 03_Base_de_datos_anonimizada.",
    ]:
        par(txt, after=3)
    par("", after=2)
    par("Fuentes: INE, Conteos Censales de Participación Ciudadana 2009–2024; CONEVAL, Índice de Rezago Social 2010, "
        "2015 y 2020; INEGI, Marco Geoestadístico y Censo de Población y Vivienda 2020. Todas las cifras del reporte, la "
        "presentación, el tablero y la base de datos provienen del mismo flujo de código y coinciden entre sí.", 9.5)
    out = ENT / "LEEME_DataInsert.docx"
    doc.save(out)
    subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(ENT), str(out)],
                   capture_output=True, check=True)
    out.unlink()
    print("LEEME:", ENT / "LEEME_DataInsert.pdf")


def empaquetar():
    cartas = [f for f in (ENT / "cartas").glob("*") if f.suffix.lower() in (".pdf", ".jpg", ".jpeg", ".png")]
    if len(cartas) < 2:
        print(f"ADVERTENCIA: entregables/cartas/ tiene {len(cartas)} archivo(s); faltan las cartas firmadas.")
    base = ZIP.stem
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(ENT / "LEEME_DataInsert.pdf", f"{base}/00_LEEME_DataInsert.pdf")
        for carpeta, items in ESTRUCTURA.items():
            for it in items:
                src = ROOT / it
                files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
                for f in files:
                    if f.name == ".DS_Store" or "__pycache__" in f.parts:
                        continue
                    rel = f.name if src.is_file() else f.relative_to(src.parent)
                    z.write(f, f"{base}/{carpeta}/{rel}")
    print(f"Zip: {ZIP} ({ZIP.stat().st_size / 1e6:.1f} MB)")
    with zipfile.ZipFile(ZIP) as z:
        for carpeta in sorted({n.split("/")[1] for n in z.namelist()}):
            n = sum(1 for x in z.namelist() if x.split("/")[1] == carpeta)
            print(f"  {carpeta}: {n} archivo(s)")


if __name__ == "__main__":
    leeme()
    empaquetar()
