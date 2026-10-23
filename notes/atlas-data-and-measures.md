# Datos y medidas del atlas

Actualizado el 23/10/2026, pasada CDI + Wikidata y Peladómetro. Corte de los cargos: **14/10/2026**. La investigación complementaria no extiende ese corte.

## Procedencia y auditoría

Proyecto de investigación y visualización histórica. El constructor lee los CSV originales y los JSON editables de `data/curated/`. Genera tablas en `data/processed/atlas/` y el HTML autónomo en `output/argentina-ministers-atlas.html`, con D3 7.9.0 incluido. Los CSV, HTML de captura y resultados Plotly originales se conservan.

La auditoría identifica 67 registros presidenciales tras excluir tres duplicados exactos de 70 filas originales. Incluyen seis interinatos: la vista inicial muestra 61 registros. Se mantienen las 126 gestiones ministeriales. Cortínez termina al inicio de la cobertura presidencial y no aporta intersecciones positivas. La comparación inicial incluye 125 gestiones y 94 nombres; el directorio incluye los 95 nombres de toda la base. Wikidata vincula los 95 nombres a 94 entidades: José / José María Dagnino Pastore comparten QID. El inventario y los rankings previos siguen conservando los nombres originales; el Peladómetro ya agrupa por identidad para evitar duplicarlos.

Se generan 149 intersecciones ministro–presidencia y 99 hallazgos automáticos: tres duplicados, 13 nombres depurados, dos fechas finales recuperadas, 34 diferencias con vínculos heredados, una designación fuera de cobertura, siete pares presidenciales superpuestos, tres pares ministeriales y 36 registros con días sin ministro registrado. Las fechas recuperadas son Emilio Hansen (12/10/1892) y Marco Aurelio Avellaneda (12/10/1904). Los 34 cambios de vínculo no son 34 correcciones históricas independientes. Los solapamientos ministeriales de 1906, 1915 y 1962 requieren investigación; no se desplazan fechas para borrarlos.

`source_hashes.json` registra los CSV/HTML originales y los JSON curados. Las fotos se guardan en `data/external/portraits/`, con URL, procedencia y SHA-256 en su manifiesto. **El atlas no incrusta fotos ni las solicita al cargar.** `code/06_fetch_portraits.py` descarga el catálogo `portrait-sources.json` y reutiliza archivos existentes.

## Intervalos y filtros

- Todos los intervalos son `[inicio, fin)`: inicio incluido, fin excluido. No se añade un día al corte.
- El servicio en una presidencia es la intersección positiva de ambas fechas.
- Personas: nombres exactos distintos de las gestiones que atraviesan la presidencia, incluidos heredados.
- Designaciones: gestiones que comienzan en esa presidencia, excluidos heredados.
- Designaciones por año = designaciones / (días presidenciales / 365,25). Las presidencias muy cortas pueden producir tasas extremas. Un registro de un mismo día no tiene duración positiva medible.
- Permanencia promedio: media de días de cada gestión dentro de la presidencia. No es media por persona ni duración completa de las gestiones. Meses = días × 12 / 365,25.
- Las fechas seleccionan presidencias superpuestas al rango. La tabla y los rankings conservan las duraciones completas registradas. La línea se recorta visualmente.
- La búsqueda general selecciona presidencias por presidente o ministro y conserva los demás ministros de esas presidencias.
- Solo finalizadas excluye gestiones abiertas de conteos y promedios; conserva el denominador presidencial. No es un estimador corregido por censura.
- Las estadísticas globales deduplican gestiones entre presidencias. Sumar filas puede duplicar gestiones compartidas.
- Los vacíos se calculan mediante la unión de servicios de toda la base, antes del filtro de finalizadas; no se imputan.

## Tres categorías y 17 episodios

La nueva instrucción del usuario sustituye las nueve categorías visibles. Se preservan los 17 episodios, dimensiones, justificaciones y fuentes en `regime-periods.json`.

| Categoría anterior | Categoría actual |
|---|---|
| Orden electoral restringido | Democracia cerrada |
| Gobiernos electos por varones | Democracia cerrada |
| Gobiernos de origen electoral fraudulento | Democracia cerrada |
| Gobiernos electos con proscripciones | Democracia cerrada |
| Gobiernos electos con sufragio ampliado | Democracia abierta |
| Democracia desde 1983 | Democracia abierta |
| Dictaduras militares | Gobierno de facto / dictatorial |
| Gobierno civil bajo tutela militar | Gobierno de facto / dictatorial |
| Transición con autoridad disputada | Gobierno de facto / dictatorial |

Abierta sigue el criterio electoral pedido: sufragio amplio, ausencia de proscripción partidaria y de grandes fraudes o supresión del voto documentados en esta codificación. Cerrada reúne elecciones con aquellas restricciones. De facto comprende acceso o ejercicio del poder impuesto por la fuerza. Las sucesiones constitucionales no cambian de categoría por carecer de una nueva elección.

1916–1930 y el mandato 1946–1952 son cerrados por la exclusión de las mujeres. Las fronteras siguen la asunción del mandato resultante, no la sanción de las leyes. Guido se agrupa en de facto por golpe, anulación electoral, clausura del Congreso y subordinación militar, conservando su singularidad de autoridad civil con vía sucesoria. La semana del golpe de 1955 también queda en de facto, sin borrar las disputas de titularidad.

1952–1955 y octubre de 1973–1976 se asignan abierta por el criterio electoral adoptado, con reservas explícitas sobre represión, violencia y libertades. No se certifica calidad democrática plena. Es una clasificación analítica revisable si nueva evidencia documenta supresión electoral que satisfaga el criterio.

Las distribuciones usan 127 fragmentos gestión–episodio y conservan exactamente los días dentro de la cobertura. Los interinatos no duplican fragmentos. En este gráfico las fechas sí recortan los fragmentos: acortar el rango puede reducir mecánicamente la permanencia. La búsqueda determina las gestiones elegibles; la selección presidencial solo resalta puntos. Caja = 50 % central, raya = mediana, hueco = gestión abierta. Los fragmentos no son gestiones completas ni observaciones independientes. Las diferencias son descriptivas, sin interpretación causal.

## Rankings y navegación

Las burbujas fueron retiradas. Dos listas muestran cinco gestiones de mayor y menor duración, con días, fechas y barras. Se alterna entre gestiones separadas y acumulado por nombre: este último usa la unión de intervalos elegibles sin duplicar días superpuestos. No añade automáticamente cargos fuera de la selección. El extremo inicio–fin puede contener períodos sin servicio entre gestiones.

Se excluyen por defecto abiertas y duraciones cero. La opción propia incluye abiertas como duraciones mínimas observadas, salvo que el filtro general ya las excluya. Empates: inicio y nombre; cinco posiciones, no todos los empatados. El ranking corresponde al inventario disponible, con sus diferencias de cartera y posibles interinatos ministeriales.

El título visible y del navegador es Los ministros. La ayuda Cómo leer este atlas queda desplegable dentro de Fuentes, sin un bloque permanente en la portada. Hay siete bloques: Historia, Rankings, Presidencias, Regímenes, Ministros, Peladómetro y Fuentes. Navegación fija, anterior/siguiente, fragmento URL y opción Ver todo seguido. Los filtros desplegables conservan su estado entre bloques; se ocultan en Ministros, Peladómetro y Fuentes porque no afectan esas secciones. El recorrido completo los conserva en la parte superior.

## Biografías y frases

`minister-profiles.json` tiene 95 fichas y campos nulos explícitos. La pasada CDI + Wikidata amplió la cobertura a **78 nacimientos completos y 11 parciales; los 95 nombres tienen sexo/género según la fuente**. Las 14 medidas y seis frases se conservan. La cobertura de evaluaciones visuales se calcula desde las fichas; localizar una imagen candidata no equivale a inspeccionarla. El [balance de investigación](research-cdi-wikidata-2026-10-23.md) documenta las incorporaciones y los casos pendientes.

La edad se calcula en años cumplidos al comenzar cada gestión. Si solo hay mes/año o año de nacimiento, se calculan los extremos compatibles y se muestra un rango de edad; no se inventa un cumpleaños. Los datos de Wikidata se identifican como primera pasada y conservan precisión, declaraciones y referencias. Se retienen para revisión las fechas conflictivas, incompatibles o dudosas. No se sustituyen fechas de cargos por las que mencione otra fuente. P21 se registra como sexo o género según Wikidata, sin inferencia por nombre o foto y sin equipararlo a sexo registral certificado.

La medida emblemática es una selección editorial de un hito documentado, con año y fuente. No mide objetivamente notoriedad ni adjudica autoría exclusiva de decisiones colectivas. Puede corresponder a una de varias gestiones de la persona.

Las frases distinguen discurso reproducido, registro audiovisual, atribución secundaria y versión popular, con contexto. Un nombre de plan no cuenta como cita personal. Sigaut conserva el año y la versión popular porque las fuentes difieren sobre fecha y formulación. Pugliese conserva la advertencia de atribución secundaria. Pendiente no significa que no exista una frase.

El directorio tiene búsqueda propia por nombre, medida o frase y filtro de sexo, independiente de los filtros presidenciales. Las búsquedas externas se identifican como búsquedas, no como fuentes verificadas. La descarga incluye toda la base, una fila por gestión.

## Índice pelado

Valoración lúdica, subjetiva y experimental, en escalones: **0** sin pérdida visible; **25** entradas o menor densidad leves; **50** retroceso o menor densidad moderados; **75** pérdida extensa o pelo muy ralo arriba; **100** parte superior sin cabello visible. Considera también afinamiento aparente y cuero cabelludo visible entre el pelo. No predice caída futura. Describe zonas visibles de una foto inspeccionada; no diagnostica alopecia ni distingue afeitado. No se presume observado lo que oculta el peinado.

Cada valoración guarda archivo, fuente, época, nota, confianza y revisión. Por instrucción del usuario se pueden puntuar fotos sin fecha de toma si la identidad y el pelo son observables; la asociación probable con su etapa ministerial se conserva como contexto, sin presentarla como fecha confirmada. La fecha de publicación no equivale a fecha de toma. El puntaje no se traslada automáticamente a todas las asunciones. Un dato faltante no equivale a cero.

La primera tanda de cinco observaciones se conserva: Cavallo 100, Sourrouille 25, Lousteau 0, Batakis 0 y Caputo 0. Las ampliaciones desde CDI/Commons se documentan junto a cada imagen y ficha, con metadatos y hashes. Hay 50 personas evaluadas, reflejadas en 51 fichas por los alias de Dagnino Pastore. Se descargaron e inspeccionaron 73 archivos de imagen de referencia, incluidas las cinco imágenes iniciales. Para el grupo con servicio desde 1966 hay 47 evaluados de 49; quedan pendientes Quilici y Joaquín de las Heras. El HTML muestra únicamente puntajes, explicaciones y enlaces a las fuentes.

El **Peladómetro** muestra un velocímetro semicircular: 0 % a la izquierda, 50 % arriba y 100 % a la derecha. La aguja representa la proporción de evaluados que alcanza el umbral, no el puntaje visual promedio ni la probabilidad de llegar a ministro. Sin evaluaciones no hay aguja. Se retiraron las barras por pedido del usuario. Permite variar el umbral (25/50/75/100) y el grupo: todos, algún servicio desde el 01/01/1966, o primera asunción antes/después del 01/01/1983. Cuenta una observación por entidad de Wikidata, con nombre como alternativa si falta el QID. Un 0 es una observación válida; un faltante o un conflicto entre fichas no lo es. La proporción usa exclusivamente a los evaluados del grupo y muestra numerador, denominador y faltantes. Es una selección parcial no representativa. No estima la probabilidad de ser ministro siendo pelado: para eso falta un grupo de no ministros. El grupo desde 1966 considera cualquier servicio que se superponga a ese período, no solo la primera asunción. Los otros grupos sí usan la primera asunción. Ninguna agrupación fecha la foto. Sus filtros son propios e independientes de los del atlas.

## Reconstrucción y validación

```text
python code/04_build_atlas.py
python code/05_check_atlas.py
node --check code/d3/atlas.js
node code/d3/check-peladometro.cjs
node code/d3/check-browser.cjs
```

Usar el Python del runtime compartido cuando el del PATH sea el alias de Windows. Playwright requiere `NODE_PATH` del runtime compartido y Edge instalado; `ATLAS_BROWSER_CHANNEL=chrome` permite cambiarlo. `python code/06_fetch_portraits.py` descarga nuevas referencias del catálogo, pero no es necesario para reconstruir el HTML existente.

La adquisición de esta pasada está en code/07_collect_biographies.py; code/08_enrich_biographies.py aplica los controles sobre la caché, conserva los datos previos y genera el balance. Los CSV de cobertura, correspondencias, candidatos fotográficos y hallazgos están en data/processed/biographies/.

Las verificaciones cubren fronteras históricas, fechas, enlaces, conservación de días, hashes, edades exactas y por intervalo, fechas retenidas y fotos descargadas. El helper del Peladómetro tiene pruebas de ceros/faltantes, duplicados, conflictos, umbrales inclusivos y denominadores vacíos. El control del navegador comprueba carga sin red ni errores JS, filtros, selección, bloques, rankings, fichas, teclado, cuatro CSV y desborde móvil a 390 px. Incluye el velocímetro, sus controles y los extremos 0 %, 100 % y denominador vacío sin aguja. Es QA focalizada, no una auditoría histórica independiente ni certificación completa de accesibilidad.

El atlas actual está en `output/argentina-ministers-atlas.html`. `output/index.html` conserva el dashboard Plotly anterior.
