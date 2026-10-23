# Los ministros

## Atlas de ministros de economía — versión en español argentino

**[Abrir la versión lista para Pages](docs/index.html)** — el enlace público se añadirá al vincular el repositorio con GitHub. — línea de tiempo, rankings de mayor y menor duración, tabla presidencial, distribuciones por régimen y fichas individuales con Peladómetro interactivo. Se recorre por siete bloques o con scroll continuo. Incluye búsqueda, filtros, fuentes y cuatro descargas CSV. Datos observados hasta el **14/10/2026**.

Los datos originales y las salidas Plotly están preservados. La clasificación editable en `data/curated/regime-periods.json` distingue tres categorías —democracia abierta, democracia cerrada y gobierno de facto/dictatorial— y conserva 17 episodios con sus matices y la correspondencia con las categorías anteriores. Es una clasificación electoral analítica, no un índice general de calidad democrática. Para retomar el trabajo, ver **[la cuarta iteración del 23/10/2026](notes/session-2026-10-23-v4.md)** y la [tercera iteración](notes/session-2026-10-23-v3.md) y [la metodología actual](notes/atlas-data-and-measures.md). Incluyen estado, decisiones, pruebas, pendientes y comandos de reconstrucción.

**Primera pasada CDI + Wikidata:** 95 fichas por nombre, vinculadas a 94 entidades; 78 nacimientos completos, 11 parciales y 95 valores de sexo/género con fuente. Se conservan 14 medidas y seis frases documentadas. Las edades parciales se muestran como rangos y las fechas dudosas quedan pendientes. El Peladómetro usa un velocímetro semicircular de 0–100 %, con umbral ajustable, 50 personas evaluadas y cobertura de 47 de las 49 que tuvieron servicio desde 1966. Incluye poca densidad y muestra los faltantes; las fotos no se incrustan en la visualización. Ver [el balance de investigación](notes/research-cdi-wikidata-2026-10-23.md).

The material below documents the **legacy Plotly dashboard**; its headline estimates have not been adopted as atlas measures.

An interactive data visualization exploring the relationship between political regime instability and economic management turnover in Argentina.

**[View the legacy interactive visualization →](output/argentina_ministers_timeline.html)**

---

## What this shows

### Top panel: Timeline (1880–2026)
- **Thick colored bands** = presidential terms
  - **Blue** = Constitutional (de iure)
  - **Orange** = Fraudulent elections (Infamous Decade)
  - **Red** = Military coups & juntas (de facto)
- **Green vertical ticks** = each time a new economy/finance minister took office
- **Dotted lines** = major crises (1890, 1930, 1955, 1966, 1976, 1989, 2001, 2023)

### Bottom-left: Ministers per President
Horizontal bars sorted by how many economy ministers each president had.

### Bottom-center: Tenure Distribution
Histogram of how long ministers stayed in office. The red dashed line marks the **median (~0.8 years / ~9 months)**.

### Bottom-right: Key Numbers
Big, scannable stats: total ministers, average tenure, de facto presidents, total presidents.

---

## Key findings

| Metric | Value |
|--------|-------|
| Total ministers (1880–present) | **126** |
| Average tenure | **~1.1 years** (~13 months) |
| Median tenure | **~0.8 years** (~9 months) |
| De facto presidents | **~19** |
| Constitutional presidents | **~51** |

## Data sources

Compiled from:

1. **Wikipedia – *Anexo:Ministros de Economía de Argentina***  
   <https://es.wikipedia.org/wiki/Anexo:Ministros_de_Econom%C3%ADa_de_Argentina>

2. **Wikipedia – *List of heads of state of Argentina***  
   <https://en.wikipedia.org/wiki/List_of_heads_of_state_of_Argentina>

> **Academic note:** Wikipedia served as the structured compilation layer. The underlying facts (names, dates, terms) can be cross-referenced with the *Diario de Sesiones* archives, BCRA historical records, and standard academic histories such as Romero's *A History of Argentina in the Twentieth Century* (UC Press) and Gerchunoff & Llach's *El ciclo de la ilusión y el desencanto* (Ariel).

## How to publish on GitHub

1. Push this folder to a repository.
2. Go to **Settings → Pages → Deploy from a branch** → select `main` and `/ (root)`.
3. Visit `https://yourusername.github.io/repo-name/`.

The file `index.html` is a self-contained copy of the visualization ready for GitHub Pages.

## Files

```
argentina-ministers-viz/
  code/
    01_scrape_wikipedia.R      # Data acquisition
    02_clean_data.R            # Parsing & classification
    03_build_visualization.R   # Plotly dashboard generation
  data/
    ministers_clean.csv
    presidents_clean.csv
    ministers_per_president.csv
  output/
    argentina_ministers_timeline.html  # Interactive viz
    index.html                         # GitHub Pages ready
  README.md
```

## Rebuilding

Requires R with `tidyverse`, `plotly`, `rvest`, `lubridate`:

```r
source("code/01_scrape_wikipedia.R")
source("code/02_clean_data.R")
source("code/03_build_visualization.R")
```

---

Built with [Plotly for R](https://plotly.com/r/). Data compiled October 2026.
