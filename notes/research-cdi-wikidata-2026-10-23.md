# Primera pasada CDI + Wikidata — 23/10/2026

## Resultado

La pasada se ejecutó sobre los 95 nombres del inventario, que apuntan a 94 entidades de Wikidata. Las variantes José / José María Dagnino Pastore comparten identificador. Se conservan los nombres del inventario y no se modifica ninguna fecha de cargo.

| Campo | Antes | Después |
|---|---:|---:|
| Nacimiento con día, mes y año | 24 | 78 |
| Nacimiento con mes/año o solo año | 0 | 11 |
| Sexo/género con fuente | 24 | 95 |
| Índices pelados con imagen inspeccionada (personas distintas) | 5 | 50 |

CDI permitió vincular 93 nombres. Se localizaron 182 referencias de imágenes, procedentes de CDI y Wikidata/Commons, para 93 nombres. Son referencias candidatas: ni su identificación ni su fecha de toma se presumen verificadas por encontrarlas.

Las evaluaciones visuales cubren 50 personas distintas, reflejadas en 51 fichas por los alias del inventario. Las tandas descargadas y revisadas están documentadas en `portrait-review-batch.json` y `recent-portrait-review.json`; incluyen imágenes fechadas y retratos sin fecha, que pueden puntuarse si permiten identificar a la persona y apreciar el pelo.

## Criterio de incorporación

Se resolvieron los nombres desde los enlaces de Wikipedia ya incluidos en los insumos originales, siguiendo normalizaciones y redirecciones hasta su QID. No se aceptó la primera coincidencia de una búsqueda nominal. CDI se vinculó mediante nombres y alias compatibles, guardando la regla de correspondencia y sus registros completos.

Los valores existentes de nacimiento se conservaron. P569 de Wikidata se importó solo si sus declaraciones seleccionadas eran compatibles y pasaban controles de cronología. Se respetó la precisión del dato: los valores por año o mes producen intervalos de edad, nunca un cumpleaños inventado. Un 1 de enero almacenado con precisión de año no significa nacimiento el 1 de enero.

P21 se conserva como sexo o género según la fuente, no como una certificación de sexo registral. La ficha enlaza la propiedad y conserva el valor original. Las afirmaciones y referencias descargadas están guardadas por campo. Los datos nuevos se identifican como primera pasada: no se presentan como cotejados independientemente con documentos primarios.

## Pendientes y controles

Quedan sin fecha de nacimiento utilizable: Juan Agustín García Seoane, Norberto Piñero, Lorenzo Anadón, Pedro Groppo, Roberto Verrier, Juan A. Quilici.

Se retuvieron para revisión: Juan Agustín García Seoane y Lorenzo Anadón por edades inferiores a 30 años en los cargos registrados; Norberto Piñero por años de nacimiento incompatibles entre declaraciones; Pedro Groppo por un nacimiento posterior a su servicio ministerial; Juan A. Quilici por un 1 de enero sin referencias que podría ser una fecha de relleno. El umbral de 30 es una señal de revisión de esta pasada, no una afirmación de imposibilidad histórica. Roberto Verrier carece de nacimiento en la respuesta consultada.

CDI contiene discrepancias y metadatos que requieren contraste: por ejemplo, la etiqueta alternativa de la imagen de Sigaut nombra a Alemann. Las fotografías se inspeccionan antes de asignar puntajes. Los períodos ministeriales de CDI no se convierten en fechas de captura. Las fechas de cargo permanecen en el inventario original para una auditoría posterior de decretos.

El índice visual también contempla menor densidad, afinamiento aparente y cuero cabelludo visible. No estima caída futura. El Peladómetro describe proporciones entre ministros con imágenes evaluadas; no estima la probabilidad de ser ministro siendo pelado, porque falta el denominador de no ministros.

## Fuentes y archivos reproducibles

- [CDI: listado, decretos y bibliografía](https://cdi.mecon.gob.ar/ministros-de-economia).
- [Wikidata: modelo biográfico y propiedades](https://www.wikidata.org/wiki/Wikidata:WikiProject_Biography/Model).
- `data/external/biographies/`: HTML/CSV de CDI, respuestas de Wikipedia y entidades de Wikidata.
- `data/processed/biographies/evidence.json`: resolución de identidades y evidencia completa.
- `coverage.csv`: estado por nombre, precisión y fuentes.
- `cdi-crosswalk.csv`: correspondencias, carteras, períodos y enlaces de imágenes.
- `portrait-candidates.csv`: referencias candidatas y advertencias de identificación/fecha.
- `review-findings.csv`: valores retenidos para revisión.
- `source_hashes.json`: hashes de las respuestas conservadas.
- `code/07_collect_biographies.py`: adquisición con caché; `code/08_enrich_biographies.py`: aplicación reproducible y este balance.
