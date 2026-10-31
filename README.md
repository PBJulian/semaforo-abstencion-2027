# Semáforo de Riesgo de Abstención 2027

**Equipo Data Insert** · Hackathon INE *Hackea la participación: Datos que construyen democracia* · Reto 2: Predicción y escenarios de riesgo de abstención

Integrantes: Aldo Sebastian Altamirano Vázquez, Carlo Kiliano Ferrera Guadarrama, Isaac Pancardo Botello y José Julián Pérez Bustamante.

Este proyecto proyecta la abstención municipal para la elección federal intermedia de 2027 a partir de los Conteos Censales de Participación Ciudadana (CCPC) 2009–2024 del INE. Con esa proyección clasifica a los 2,477 municipios en un semáforo de riesgo y simula escenarios con y sin una intervención de promoción del voto juvenil.

## Resultados principales

- **Modelo híbrido validado con backtest temporal:** combina Ridge y Gradient Boosting con persistencia histórica. Su error medio, ponderado por lista nominal, es de 3.0 pp en 2021 y 2.3 pp en 2024. Localiza al 82 % de las personas que viven en el quintil de municipios de mayor riesgo.
- **Semáforo 2027 sin intervención:** 238 municipios en rojo (13.6 M de electores) y 376 en naranja.
- **Escenarios:** con el mismo presupuesto, priorizar la campaña con el semáforo reduce la abstención de la población en riesgo 2.2 veces más que repartirla de forma uniforme.
- **Validación retrospectiva:** con datos hasta 2018, el semáforo habría marcado en rojo o naranja al 70 % de los municipios del decil de mayor abstención de 2021 (88 % en 2024).
- **Operación:** proyección para las 70,751 secciones y los 300 distritos federales. En el distrito típico, 48 de 218 secciones concentran la mitad de los jóvenes que se abstendrían.
- **Por qué y qué hacer:** explicación por municipio de los factores de riesgo y una matriz de acción (enfoque intercultural, actualización de domicilio, retención juvenil o movilización general), sustentada con el Censo 2020.

## Estructura

```
data/raw/ccpc/      CCPC 2009-2024 (DatosAbiertos_DECEyEC_ConteosCensales{año}/), descarga del INE
data/raw/coneval/   IRS_entidades_mpios_{2010,2015,2020}.xlsx, descarga de CONEVAL
data/raw/geo/       mun.shp (Marco Geoestadístico INEGI, división municipal)
data/raw/inegi/     iter2020/ (Censo 2020, Principales resultados por localidad, CSV nacional)
data/processed/     intermedios generados por el pipeline
src/                código (ver abajo)
outputs/            métricas, tablas y figuras
entregables/        reporte (DOCX/PDF), mapa de escenarios (HTML), capas GeoJSON/GPKG y base de datos (CSV/XLSX)
```

| Script | Qué hace |
|---|---|
| `src/01_ingest.py` | Lee los 192 archivos CCPC (sección × sexo × edad simple) y los agrega por sección, sexo y grupo de edad. |
| `src/02_panel.py` | Proyecta cada sección histórica al marco municipal 2024 (las claves municipales del INE cambian entre años), cruza el CONEVAL 2010, 2015 y 2020 y construye la matriz de vecindad municipal. |
| `src/02b_censo.py` | Indicadores municipales del Censo 2020: migración interna, lengua indígena y escolaridad (solo para diagnóstico y matriz de acción, no en el modelo, para evitar fuga). |
| `src/03_model.py` | Variables sin fuga temporal, backtest (2021 y 2024), modelo híbrido, intervalos conformales calibrados con la intermedia 2021 e importancia por permutación fuera de muestra. |
| `src/03b_robustez.py` | Compara variantes del modelo (CONEVAL fijo o por edición, sin CONEVAL, rezago espacial, ponderación). |
| `src/04_scenarios.py` | Proyección 2027, semáforo, escenarios (inercial, focalizado, uniforme), sensibilidad al efecto y curva de presupuesto. |
| `src/04b_retro.py` | Retro-semáforo: qué habría anticipado el procedimiento antes de 2021 y de 2024. |
| `src/04c_operativo.py` | Proyección por sección y por distrito federal (marco 2023), secciones prioritarias por distrito y matriz de acción. |
| `src/05_export_figures.py` | Base de datos anonimizada (CSV, y XLSX con diccionario de variables) y figuras del reporte. |
| `src/06_maps.py` | Tablero de escenarios (HTML autocontenido, a partir de `src/tablero_template.html` con Leaflet 1.9.4 incrustado desde `src/vendor/`) y capas GeoJSON/GeoPackage. Verifica que la simulación del tablero reproduzca las cifras del pipeline. |
| `src/08_presentacion.py` | Presentación ejecutiva (10 láminas, PPTX y PDF) con guion del pitch en las notas. |
| `src/07_report.py` | Genera el reporte metodológico (DOCX) a partir de los resultados, para que sus cifras coincidan con la base y el mapa. |

## Cómo reproducir

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run_all.sh          # ~2 minutos; el PDF del reporte requiere LibreOffice
```

El pipeline es determinista: dos corridas producen resultados idénticos.

## Decisiones metodológicas clave

1. **Unidad municipal en el marco 2024.** Las secciones históricas se asignan al municipio al que pertenecen en 2024, porque el INE reasigna claves municipales entre elecciones. Con esto se cubre más del 99.9 % de la lista nominal de cada año.
2. **Desviación intra-estatal.** El modelo predice la abstención de cada municipio *relativa a su entidad*. El nivel estatal de 2027 es un supuesto explícito: el de 2021, última intermedia, que también fue concurrente en las 32 entidades.
3. **Sin fuga de información.** Cada elección se modela solo con datos publicados antes de ella: rezagos electorales, la edición vigente del CONEVAL y la abstención de los municipios vecinos en elecciones previas.
4. **Semáforo por nivel absoluto.** Los umbrales son 40 %, 50 % y 58 %. Se descartó una regla de "deterioro" porque reflejaba regresión a la media y no un empeoramiento real.
5. **Métrica de escenarios.** Con un efecto lineal, las estrategias focalizada y uniforme recuperan los mismos votos. Por eso se comparan por la reducción de abstención en la población en riesgo y por la dispersión territorial.

## Datos y privacidad

Solo se usan datos públicos y agregados (INE, CONEVAL, INEGI). Las bases entregadas son municipales y no contienen información de personas identificables.
