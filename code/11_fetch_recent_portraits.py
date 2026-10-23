"""Scoped recent ministers portrait evidence. Photos remain research references.

Fetch cached exact P18 through Commons imageinfo/extmetadata and CDI candidates;
make small contact sheets for manual inspection, then assemble observations.json.
Only this script, recent-pass/, and recent-portrait-review.json are owned outputs.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import unicodedata
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data/external/portraits/recent-pass'
REVIEW = ROOT / 'data/processed/biographies/recent-portrait-review.json'
TARGETS = ['Jorge Salimei', 'José Dagnino Pastore', 'Carlos Moyano Llerena',
    'Aldo Ferrer', 'Juan A. Quilici', 'Cayetano Antonio Licciardo',
    'Alfredo Gómez Morales', 'Celestino Rodrigo', 'Ernesto Corvalán Nanclares',
    'Antonio Cafiero', 'Emilio Mondelli', 'Joaquín de las Heras', 'Jesús Rodríguez',
    'Miguel Roig', 'Néstor Mario Rapanelli', 'Antonio Erman González',
    'José Luis Machinea', 'Ricardo López Murphy', 'Nicolas Gallo', 'Jorge Capitanich',
    'Rodolfo Frigeri', 'Jorge Remes Lenicov', 'Miguel Gustavo Peirano',
    'Carlos Rafael Fernández', 'Amado Boudou', 'Hernán Lorenzino',
    'Alfonso Prat-Gay', 'Nicolás Dujovne', 'Hernán Lacunza', 'Jorge Wehbe',
    'Juan Carlos Pugliese', 'Pedro José Bonanni']
AGENT = 'ArgentinaMinistersResearch/1.0 (local reference visual review)'
DISCOVERED_FILES = {'Juan A. Quilici': ['Juan Alberto Quilici.jpg', 'Jura Quilici como ministro.jpg']}

def now():
    return datetime.now(timezone.utc).isoformat()

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def slug(name):
    return re.sub('[^a-z0-9]+', '-', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()).strip('-')

def retrieve(url, target, image=False):
    receipt_path = target.with_name(target.name + '.http.json')
    if target.exists() and receipt_path.exists():
        receipt = read(receipt_path)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == receipt['sha256']
        return receipt
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': AGENT}), timeout=30) as response:
                payload = response.read(30_000_001)
                receipt = dict(request_url=url, final_url=response.url, status=response.status,
                    headers=dict(response.headers), retrieved_at=now(), content_type=response.headers.get_content_type())
            break
        except HTTPError as exc:
            write(target.with_name(target.name + f'.error-{attempt}.json'), dict(url=url,
                status=exc.code, headers=dict(exc.headers), body=exc.read(6000).decode('utf-8', 'replace'), retrieved_at=now()))
            if exc.code != 429 or attempt == 2:
                raise
            delay = exc.headers.get('Retry-After', '')
            if delay.isdigit() and int(delay) > 30:
                raise
            time.sleep(int(delay) if delay.isdigit() else 4 * (attempt + 1))
    if len(payload) > 30_000_000:
        raise ValueError('Image exceeds 30 MB')
    if image and not receipt['content_type'].startswith('image/'):
        raise ValueError('Nonimage response')
    target.write_bytes(payload)
    receipt.update(sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), local_path=target.relative_to(ROOT).as_posix())
    write(receipt_path, receipt)
    return receipt

def fetch_person(name, identity, entity, candidates):
    rows = []
    p18 = [c['mainsnak']['datavalue']['value'] for c in entity.get('claims', {}).get('P18', [])
        if c.get('rank') != 'deprecated' and 'datavalue' in c.get('mainsnak', {})]
    cached_p18 = set(p18)
    p18.extend(f for f in DISCOVERED_FILES.get(name, []) if f not in p18)
    for i, filename in enumerate(p18):
        row = dict(name=name, qid=identity['qid'], provider='Wikidata / Commons', exact_cached_p18=filename,
            source_url='https://commons.wikimedia.org/wiki/File:' + quote(filename.replace(' ', '_')))
        if filename not in cached_p18:
            row.pop('exact_cached_p18')
            row.update(discovered_commons_file=filename, discovery_source_url='https://es.hispanopedia.com/wiki/Juan_Alberto_Quilici',
                discovery_note='Bounded web search; not a P18 claim in cached entity')
        try:
            url = 'https://commons.wikimedia.org/w/api.php?' + urlencode(dict(action='query', format='json',
                titles='File:' + filename, prop='imageinfo', iiprop='url|size|extmetadata|timestamp|sha1', iiurlwidth=1000, redirects=1))
            path = DEST / f'{slug(name)}-commons-{i}.imageinfo.json'
            receipt = retrieve(url, path)
            info = next(page['imageinfo'][0] for page in read(path)['query']['pages'].values() if page.get('imageinfo'))
            row.update(metadata_api_url=url, raw_metadata_path=receipt['local_path'], extmetadata=info.get('extmetadata', {}),
                upload_timestamp=info.get('timestamp'), original_image_url=info['url'], original_width=info.get('width'), original_height=info.get('height'))
            # Preserve raw API metadata; omit analytics parameters on download URLs.
            row['image_url'] = info.get('thumburl', info['url']).split('?', 1)[0]
            row['image_url'] = row['image_url'].replace('/1000px-', '/960px-')
            # Use an advertised standard thumbnail size even for small originals.
            if '/thumb/' not in row['image_url'] and info.get('width', 0) > 250:
                original = info['url'].split('?', 1)[0]
                width = 960 if info['width'] > 960 else 250
                row['image_url'] = original.replace('/commons/', '/commons/thumb/') + f'/{width}px-' + original.rsplit('/', 1)[1]
            suffix = Path(urlsplit(info['url']).path).suffix.lower()
            if suffix not in {'.jpg', '.jpeg', '.png', '.webp'}:
                suffix = '.jpg'
            target = DEST / f'{slug(name)}-commons-{i}{suffix}'
            try:
                row.update(retrieve(row['image_url'], target, image=True))
            except HTTPError:
                row['image_url'] = info['url'].split('?', 1)[0]
                row.update(retrieve(row['image_url'], target, image=True))
            # A cached image may predate a thumbnail policy change; cite its actual request.
            row['image_url'] = row['request_url']
            row['status'] = 'downloaded'
        except Exception as exc:
            row.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        rows.append(row)
        print(name, 'Commons', row['status'], row.get('error', ''), flush=True)
    for candidate in candidates:
        if candidate['name'] != name or candidate['provider'] != 'CDI':
            continue
        row = dict(candidate)
        row.update(capture_date=None, capture_date_precision='unknown', license='Not specified by cached CDI source; research reference only')
        try:
            target = DEST / (slug(name) + '-cdi' + Path(candidate['image_url']).suffix)
            row.update(retrieve(candidate['image_url'], target, image=True), status='downloaded')
        except Exception as exc:
            row.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        rows.append(row)
        print(name, 'CDI', row['status'], row.get('error', ''), flush=True)
    return rows

def fetch(names):
    DEST.mkdir(parents=True, exist_ok=True)
    evidence = read(ROOT / 'data/processed/biographies/evidence.json')
    identities = {r['name']: r for r in evidence['identity_mapping']}
    with (ROOT / 'data/processed/biographies/portrait-candidates.csv').open(encoding='utf-8-sig', newline='') as stream:
        candidates = list(csv.DictReader(stream))
    assert all(n in identities for n in names)
    manifest_path = DEST / 'manifest.json'
    rows = [r for r in read(manifest_path)['images'] if r['name'] not in names] if manifest_path.exists() else []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(fetch_person, n, identities[n], evidence['entities'][identities[n]['qid']], candidates) for n in names]
        for future in futures:
            rows.extend(future.result())
            write(manifest_path, dict(retrieved_at=now(), purpose='Research references only; no atlas images', images=rows))

def sheets():
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    rows = [r for r in read(DEST / 'manifest.json')['images'] if r['status'] == 'downloaded']
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
    except OSError:
        font = ImageFont.load_default()
    index = []
    for offset in range(0, len(rows), 8):
        canvas = Image.new('RGB', (1400, 900), '#eeeeee')
        draw = ImageDraw.Draw(canvas)
        for j, row in enumerate(rows[offset:offset+8]):
            x, y = (j % 4) * 350, (j // 4) * 450
            with Image.open(ROOT / row['local_path']) as original:
                thumb = ImageOps.contain(ImageOps.exif_transpose(original).convert('RGB'), (340, 385))
            canvas.paste(thumb, (x + (350-thumb.width)//2, y+55))
            draw.text((x+7, y+3), f'{offset+j+1}. {row["name"]}', fill='black', font=font)
            draw.text((x+7, y+26), row['provider'], fill='black', font=font)
            index.append(dict(index=offset+j+1, sheet=f'contact-{offset//8+1:02d}.jpg', **{k:row[k] for k in ('name','provider','local_path')}))
        canvas.save(DEST / f'contact-{offset//8+1:02d}.jpg', quality=93)
    write(DEST / 'contact-index.json', index)
    print(f'{len(rows)} images in {(len(rows)+7)//8} inspection sheets')

def court_reference():
    """Extract unretouched embedded portrait from the official CSJN biography."""
    from pypdf import PdfReader
    url = 'https://www.csjn.gov.ar/boletin/detalle/10539'
    pdf_path = DEST / 'corvalan-nanclares-csjn-boletin-2023-98.pdf'
    pdf_receipt = retrieve(url, pdf_path)
    page = PdfReader(pdf_path).pages[6]
    write(DEST / 'corvalan-nanclares-csjn-page7-text.json', dict(source_url=url, page=7, text=page.extract_text()))
    manifest_path = DEST / 'manifest.json'
    manifest = read(manifest_path)
    manifest['images'] = [r for r in manifest['images'] if r.get('provider') != 'CSJN biography']
    identity = next(r for r in read(ROOT / 'data/processed/biographies/evidence.json')['identity_mapping'] if r['name']=='Ernesto Corvalán Nanclares')
    for i, embedded in enumerate(page.images):
        path = DEST / f'ernesto-corvalan-nanclares-csjn-{i}{Path(embedded.name).suffix}'
        path.write_bytes(embedded.data)
        row = dict(name=identity['name'], qid=identity['qid'], provider='CSJN biography', status='downloaded',
            source_url=url, image_url=url, local_path=path.relative_to(ROOT).as_posix(),
            sha256=hashlib.sha256(embedded.data).hexdigest(), bytes=len(embedded.data), retrieved_at=now(),
            source_pdf_path=pdf_receipt['local_path'], source_pdf_sha256=pdf_receipt['sha256'], source_page=7,
            extraction='Unretouched embedded PDF image; pypdf page.images', publication_date='2023-11',
            capture_date=None, capture_date_precision='unknown')
        manifest['images'].append(row)
        print(row['local_path'], embedded.image.size, flush=True)
    write(manifest_path, manifest)

def record_review():
    """Transcribe completed human-readable visual observations (not image inference).

    Reviewed with view_image: contact-01..05.jpg (37 references) and the individual
    Ernesto PNG (38th); Licciardo, Roig and Wehbe also opened individually.
    Re-running records the transcription time, not a new automatic image review.
    """
    timestamp = now()
    observer = 'Codex visual inspection via view_image; recent-pass reviewer'
    # filename suffix, coarse score, confidence, Spanish observation, view limitation
    judgments = [
      ('Jorge Salimei', 'commons-0.jpg', 0, 'alta',
       'Cobertura frontal y superior compacta; no se observa pérdida visible en esta vista.', 'Retrato pequeño; coronilla no visible.'),
      ('José Dagnino Pastore', 'cdi.jpg', 75, 'alta',
       'Frente ampliamente descubierta y cobertura superior muy escasa, con cabello conservado en laterales y parte posterior visible.', 'Vista frontal ligeramente elevada; no muestra toda la coronilla.'),
      ('Carlos Moyano Llerena', 'commons-0.jpg', 75, 'alta',
       'Retroceso frontal amplio; mechones muy finos y dispersos sobre la parte superior dejan ver extensamente el cuero cabelludo.', 'Vista frontal; región posterior fuera de campo.'),
      ('Aldo Ferrer', 'cdi.jpg', 25, 'media',
       'Entradas leves y línea frontal algo retirada; cabello peinado sobre la parte superior con cobertura conservada. Se elige este retrato frente al Commons de edad más avanzada.', 'Perfil de tres cuartos y contraste limitado; no se ve la coronilla.'),
      ('Cayetano Antonio Licciardo', 'cdi.jpg', 0, 'media',
       'Cabello blanco peinado hacia atrás con cobertura continua en frente y parte superior visible; el color blanco no se interpreta como menor densidad.', 'Perfil lateral e iluminación fuerte; no permite valorar la coronilla.'),
      ('Alfredo Gómez Morales', 'cdi.jpg', 25, 'alta',
       'Entradas frontotemporales leves con mechón central y cobertura superior abundante.', 'Retrato frontal de tres cuartos; coronilla oculta.'),
      ('Celestino Rodrigo', 'cdi.jpg', 100, 'alta',
       'Parte superior visible descubierta, con cabello concentrado en los laterales.', 'Fotografía en blanco y negro; se puntúa únicamente la zona superior visible.'),
      ('Ernesto Corvalán Nanclares', 'commons-0.png', 50, 'baja',
       'Se aprecia retroceso frontal y menor cobertura en la franja anterior superior, con cabello conservado detrás y a los lados. Propuesta aproximada por el desenfoque; conviene una segunda revisión antes de curar.', 'Imagen borrosa de 250 × 302 px; el límite entre sombra y cabello es impreciso. Rango razonable 25–50.'),
      ('Antonio Cafiero', 'cdi.jpg', 0, 'media',
       'Cabello canoso peinado hacia atrás con cobertura frontal y superior continua, sin claros visibles en esta toma.', 'Luz cálida y pelo claro; parte posterior no visible.'),
      ('Emilio Mondelli', 'cdi.jpg', 100, 'alta',
       'Amplia superficie frontal y superior descubierta; el cabello visible se concentra en laterales y contorno posterior.', 'Grano fotográfico; no permite descartar pelos finos aislados.'),
      ('Jesús Rodríguez', 'commons-0.jpg', 100, 'alta',
       'Frente y parte superior visibles ampliamente descubiertas, con cabello conservado en los lados y detrás.', 'Vista oblicua; no muestra toda la parte posterior.'),
      ('Miguel Roig', 'cdi.jpg', 50, 'media',
       'Retroceso frontal y cobertura rala en la franja superior anterior; aún hay cabello sobre la parte superior y en los laterales.', 'Retrato pequeño y desenfocado; coronilla no visible.'),
      ('Néstor Mario Rapanelli', 'commons-0.jpg', 100, 'media',
       'Zona frontal y parte superior visible descubiertas, con cabello en el contorno lateral. El retrato CDI coincide en el patrón general.', 'Foto de grupo granulada; se identifica al hombre central, no a los acompañantes.'),
      ('Antonio Erman González', 'cdi.jpg', 0, 'alta',
       'Cabello canoso abundante peinado hacia atrás; cobertura continua sin claros superiores visibles.', 'Vista frontal de tres cuartos; coronilla oculta.'),
      ('José Luis Machinea', 'commons-0.jpg', 50, 'media',
       'Entradas marcadas y menor densidad en la franja frontal superior; persiste cobertura en el centro y hacia atrás.', 'La cabeza inclinada ayuda a ver el frente; no muestra la coronilla completa.'),
      ('Ricardo López Murphy', 'commons-0.jpg', 0, 'alta',
       'Cabello compacto y línea frontal continua sin pérdida visible en esta toma.', 'Vista frontal con parte posterior oculta.'),
      ('Nicolas Gallo', 'commons-0.jpg', 0, 'alta',
       'Cabello rizado denso y cobertura frontal y superior continua, sin claros visibles.', 'Vista frontal; coronilla no visible.'),
      ('Jorge Capitanich', 'cdi.jpg', 0, 'alta',
       'Cobertura abundante en frente, sienes y parte superior visible, sin pérdida apreciable.', 'Fotografía frontal de tres cuartos; parte posterior oculta.'),
      ('Rodolfo Frigeri', 'cdi.jpg', 25, 'media',
       'Retroceso leve en las sienes y línea frontal algo alta; la parte superior mantiene cobertura.', 'Imagen en blanco y negro con peinado lateral; coronilla oculta.'),
      ('Jorge Remes Lenicov', 'cdi.jpg', 100, 'alta',
       'Frente y parte superior visibles descubiertas, con cabello claro conservado a los lados.', 'Vista frontal; pueden existir pelos finos aislados que esta resolución no permite distinguir.'),
      ('Miguel Gustavo Peirano', 'cdi.jpg', 25, 'alta',
       'Entradas leves en ambos lados de la frente, con cobertura central y superior conservada.', 'Retrato frontal; coronilla no visible.'),
      ('Carlos Rafael Fernández', 'cdi.jpg', 25, 'media',
       'Línea frontal algo retirada en las sienes; cabello peinado sobre la parte superior con cobertura conservada.', 'Peinado lateral limita la lectura del frente; no se ve la coronilla.'),
      ('Amado Boudou', 'cdi.jpg', 0, 'alta',
       'Cabello abundante con cobertura continua de frente y parte superior; sin claros visibles.', 'Peinado voluminoso y frontal; coronilla oculta.'),
      ('Hernán Lorenzino', 'cdi.jpg', 25, 'media',
       'Entradas leves y frente alta, con cobertura superior conservada bajo el peinado lateral.', 'El peinado cubre parte de la línea frontal; coronilla oculta.'),
      ('Alfonso Prat-Gay', 'cdi.jpg', 0, 'alta',
       'Cabello denso con cobertura continua en la zona frontal y superior visible.', 'Retrato de busto de resolución moderada; no muestra la coronilla.'),
      ('Nicolás Dujovne', 'cdi.jpg', 0, 'alta',
       'Cobertura frontal y superior abundante sin claros visibles; las canas no se usan como señal de menor densidad.', 'Vista frontal de tres cuartos; coronilla oculta.'),
      ('Hernán Lacunza', 'cdi.jpg', 0, 'alta',
       'Cabello abundante y continuo en la parte superior y frontal visible, sin pérdida apreciable.', 'Flequillo y peinado ondulado cubren parcialmente la línea frontal; coronilla oculta.'),
      ('Jorge Wehbe', 'cdi.jpg', 75, 'media',
       'Frente ampliamente descubierta y retroceso que alcanza gran parte de la zona superior anterior, con cabello conservado detrás y a los lados.', 'Imagen pequeña y borrosa; no permite delimitar toda la coronilla.'),
      ('Juan Carlos Pugliese', 'cdi.jpg', 25, 'media',
       'Entradas leves a moderadas y línea frontal retirada; cobertura superior todavía continua.', 'Vista frontal con peinado hacia atrás; parte posterior oculta. Identidad: Pugliese padre.'),
      ('Pedro José Bonanni', 'cdi.jpg', 100, 'media',
       'La parte frontal y superior visible aparece descubierta, con cabello limitado al contorno lateral y posterior.', 'Reproducción antigua de baja resolución; puede conservar pelos finos que no se distinguen.'),
    ]
    manifest = read(DEST / 'manifest.json')
    images = [r for r in manifest['images'] if r['status']=='downloaded']
    people = []
    image_reviews = []
    by_name = {j[0]: j for j in judgments}
    extra_visual = {
      'aldo-ferrer-commons-0.jpg': (75, 'Retrato de edad más avanzada que CDI; frente amplia y cobertura superior muy escasa. Se conserva como alternativa, no se usa para el puntaje seleccionado.'),
      'jesus-rodriguez-cdi.jpg': (100, 'Retrato posterior de la misma identidad atribuida; parte superior visible descubierta, cabello lateral. Se prefiere Commons con fecha declarada.'),
      'jose-luis-machinea-cdi.jpg': (50, 'Frente retirada con menor cobertura anterior y cabello superior conservado. Se prefiere Commons con fecha declarada.'),
      'ricardo-lopez-murphy-cdi.jpg': (25, 'Retrato con canas y entradas leves; cobertura superior continua. Se selecciona Commons fechado más próximo a su etapa ministerial.'),
      'nestor-mario-rapanelli-cdi.jpg': (100, 'Parte superior visible descubierta; referencia desenfocada compatible con el hombre central de la foto de Commons.'),
    }
    for image in images:
        j = by_name[image['name']]
        filename = Path(image['local_path']).name
        alternative = extra_visual.get(filename)
        metadata_date = image.get('extmetadata', {}).get('DateTimeOriginal', {}).get('value')
        image_reviews.append(dict(name=image['name'], local_path=image['local_path'],
            observer=observer, reviewed_at=timestamp, inspection_method='view_image of local contact sheet and/or individual local image',
            identity_status='confirmed', identity_basis='Atribución nominal en la fuente CDI o archivo Commons enlazado por P18 de la identidad en caché; inspección visual del sujeto indicado. No identificación biométrica independiente.',
            visible_score=alternative[0] if alternative else j[2],
            note=alternative[1] if alternative else j[4],
            capture_date_status='Fecha declarada por Commons; no verificada independientemente' if metadata_date else 'Fecha de toma no documentada',
            reported_capture_date=metadata_date, view_limitations=j[5]))
    undated_context = 'Fecha de toma no documentada; retrato público del CDI del Ministerio de Economía'
    for name, suffix, score, confidence, note, limitation in judgments:
        path = (DEST / (slug(name) + '-' + suffix)).relative_to(ROOT).as_posix()
        image = next(r for r in images if r['local_path']==path and r['name']==name)
        raw_date = image.get('extmetadata', {}).get('DateTimeOriginal', {}).get('value')
        precision = 'unknown'
        date = None
        if raw_date and re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw_date):
            precision, date = 'day', raw_date
        elif raw_date and re.fullmatch(r'\d{4}', raw_date):
            precision, date = 'year', raw_date
        if date:
            period = f'{date} (fecha declarada por Commons; no verificada independientemente)'
            temporal_note = 'La fecha procede de los metadatos del archivo, no del mandato; no se presupone coincidencia con la asunción.'
        else:
            period = undated_context
            temporal_note = 'La asociación con una etapa ministerial es probable, no verificada; la toma puede ser anterior o posterior al mandato.'
        hair = dict(score=score, period=period, note=note+' '+temporal_note, confidence=confidence,
            local_path=path, observer=observer, reviewed_at=timestamp,
            capture_date=date, capture_date_precision=precision,
            capture_date_basis='Commons DateTimeOriginal, declarada por el aportante' if date else 'No documentada por CDI; no se infiere del mandato',
            view_limitations=limitation, identity_status='confirmed', ministerial_period_link='not independently verified')
        if name=='Ernesto Corvalán Nanclares':
            hair.update(needs_second_review=True, plausible_score_range=[25,50])
        person = dict(name=name, hair=hair)
        if name=='José Dagnino Pastore':
            person['aliases']=['José María Dagnino Pastore']
            person['alias_note']='Una sola propuesta para los nombres que comparten QID en identity_mapping.'
        people.append(person)
    exclusions = [
      dict(name='Juan A. Quilici', score=None, reason='No se obtuvo imagen descargable utilizable con identidad confirmada en la búsqueda acotada. CDI no tiene foto y la entidad en caché no tiene P18. Dos archivos históricos encontrados por búsqueda devuelven ausencia de imageinfo en Commons.',
        attempted_files=['Juan Alberto Quilici.jpg','Jura Quilici como ministro.jpg'],
        search_queries=['"Juan A. Quilici" ministro foto','"Juan Alberto Quilici" fotografía retrato','"Jura Quilici como ministro"'],
        reference_urls=['https://es.wikipedia.org/wiki/Juan_Alberto_Quilici','https://picryl.com/media/jura-quilici-como-ministro-cf13a9'],
        metadata_paths=['data/external/portraits/recent-pass/juan-a-quilici-commons-0.imageinfo.json','data/external/portraits/recent-pass/juan-a-quilici-commons-1.imageinfo.json'],
        observer=observer, reviewed_at=timestamp),
      dict(name='Joaquín de las Heras', score=None, reason='Sin foto en CDI ni P18 en la caché. La búsqueda acotada no produjo un retrato atribuible de manera fiable al delegado militar de Economía de 1976; se descartaron resultados del prócer Juan Gregorio de Las Heras y otros homónimos.',
        search_queries=['"Joaquín de las Heras" ministro foto','"Joaquín de las Heras" general','"Joaquín de las Heras" "foto" 1976'],
        reference_urls=['https://es.wikipedia.org/wiki/Joaqu%C3%ADn_de_las_Heras'], observer=observer, reviewed_at=timestamp),
    ]
    methodology = dict(scale={'0':'sin pérdida visible en la vista disponible','25':'entradas o menor densidad leves',
        '50':'retroceso o menor cobertura moderados','75':'pérdida extensa o cobertura superior muy escasa','100':'parte superior visible descubierta'},
        scope='Propuestas visuales de cobertura capilar en fotografías públicas; no diagnósticos ni predicciones. Las canas por sí solas no aumentan el puntaje.',
        temporal_policy='La fecha de toma es ideal, no requisito. Fotografías sin fecha se puntúan cuando identidad y visibilidad son suficientes; no se asigna fecha por mandato.',
        reference_policy='Archivos de investigación exclusivamente; no incorporar fotografías al atlas.',
        confidence_values=['alta','media','baja'], identity_method='Atribución nominal de fuentes e identidad QID en caché, más inspección visual de la fotografía; no verificación biométrica independiente.',
        inspection_evidence=['contact-01.jpg','contact-02.jpg','contact-03.jpg','contact-04.jpg','contact-05.jpg','ernesto-corvalan-nanclares-commons-0.png'],
        bonanni_context='El inventario incluye Economía 1975-07-22–1975-08-11, además de 1952. Ningún mandato se usa como fecha del retrato.',
        second_review='Corvalán Nanclares: propuesta de baja confianza, 50 con rango plausible 25–50 por desenfoque.')
    write(DEST / 'observations.json', dict(recorded_at=timestamp, observer=observer, methodology=methodology,
        people=people, image_reviews=image_reviews, exclusions=exclusions))
    print(f'Recorded {len(people)} proposals and {len(image_reviews)} inspected references', flush=True)

def assemble():
    manifest = read(DEST / 'manifest.json')
    observations = read(DEST / 'observations.json')
    images = [r for r in manifest['images'] if r['status'] == 'downloaded']
    reviews = {r['local_path']: r for r in observations['image_reviews']}
    assert set(reviews) == {r['local_path'] for r in images}, 'Every downloaded image requires visual inspection'
    by_path = {r['local_path']: r for r in images}
    selected = {p['hair']['local_path'] for p in observations['people']}
    proposed_names = {p['name'] for p in observations['people']}
    excluded_names = {p['name'] for p in observations['exclusions']}
    assert proposed_names.isdisjoint(excluded_names)
    assert proposed_names | excluded_names == set(TARGETS), 'Account for all 32 identities'
    assert len(selected) == len(observations['people']), 'One selected reference per proposal'
    qids = set()
    for image in images:
        assert hashlib.sha256((ROOT / image['local_path']).read_bytes()).hexdigest() == image['sha256']
        image.update(visual_review=reviews[image['local_path']], selected_for_proposal=image['local_path'] in selected)
        image.pop('evaluation', None)
        image.pop('identity_warning', None)
    for person in observations['people']:
        hair = person['hair']
        reference = by_path[hair['local_path']]
        assert person['name'] in TARGETS and reference['name'] == person['name']
        assert reference['qid'] not in qids, 'One proposal per identity, including aliases'
        qids.add(reference['qid'])
        assert hair['score'] in (0,25,50,75,100) and hair['observer'] and hair['reviewed_at']
        assert hair['confidence'] in ('alta', 'media', 'baja')
        assert hair['capture_date_precision'] != 'unknown' or hair['capture_date'] is None
        assert reviews[hair['local_path']]['identity_status'] == 'confirmed'
        hair.update(source_url=reference['source_url'], image_url=reference['image_url'], sha256=reference['sha256'])
        person['qid'] = reference['qid']
    write(REVIEW, dict(version='recent-portrait-review-v1', reviewed_at=now(), status='Proposals only; parent merges curated profiles',
        methodology=observations['methodology'], people=observations['people'], images=images,
        fetch_failures=[r for r in manifest['images'] if r['status'] != 'downloaded'], exclusions=observations['exclusions']))
    print(f'Validated {len(observations["people"])} proposals, {len(images)} visually reviewed images, {len(observations["exclusions"])} exclusions')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names', nargs='+', choices=TARGETS)
    parser.add_argument('--sheets', action='store_true')
    parser.add_argument('--assemble', action='store_true')
    parser.add_argument('--court-reference', action='store_true')
    parser.add_argument('--record-review', action='store_true')
    args = parser.parse_args()
    if args.record_review:
        record_review()
    elif args.court_reference:
        court_reference()
    elif args.assemble:
        assemble()
    elif args.sheets:
        sheets()
    else:
        fetch(args.names or TARGETS)
