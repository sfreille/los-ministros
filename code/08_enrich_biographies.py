"""Apply a conservative, auditable first pass from the cached CDI/Wikidata data.

Never overwrite existing birth data or office dates. Preserve the source's date
precision, statement IDs, reference counts and unresolved identity/date issues.
"""
from pathlib import Path
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, quote
from collections import Counter
import calendar
import csv
import html
import json
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed/biographies'
CURATED=ROOT/'data/curated/minister-profiles.json'
CDI_URL='https://cdi.mecon.gob.ar/ministros-de-economia'

def tokens(value):
    value=''.join(c for c in unicodedata.normalize('NFD',value.casefold()) if not unicodedata.combining(c))
    return frozenset(x for x in re.findall(r'[a-z]+',value) if len(x)>1 and x not in ['de','del','la','los','el','padre','hijo','politico','argentina'])

class Plain(HTMLParser):
    def __init__(self):super().__init__();self.text=[]
    def handle_data(self,value):self.text.append(value)

def plain(value):
    parser=Plain();parser.feed(value);return ' '.join(' '.join(parser.text).split())

def cdi_cards():
    document=(ROOT/'data/external/biographies/cdi-ministers.html').read_text(encoding='utf-8')
    cards=[]
    for block in document.split('<div class="cd-timeline-block">')[1:]:
        name=re.search(r'<h2[^>]*>(.*?)</h2>',block,re.S)
        if not name:continue
        role=re.search(r'<h3[^>]*>(.*?)</h3>',block,re.S)
        image=re.search(r'<img\b([^>]+)>',block,re.S)
        attrs=dict(re.findall(r'(\w+)=["\'](.*?)["\']',image[1])) if image else {}
        image_url=urljoin(CDI_URL,html.unescape(attrs.get('src',''))) if attrs.get('src') else None
        if image_url and 'placehold' in image_url:image_url=None
        period=re.search(r'<span class="cd-date">(.*?)</span>',block,re.S)
        dates=re.findall(r'(\d{2}/\d{2}/\d{4})',plain(period[1])) if period else []
        links=[dict(url=urljoin(CDI_URL,html.unescape(u)),text=plain(t)) for u,t in re.findall(r'<a\b[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a>',block,re.S)]
        cards.append(dict(name=plain(name[1]),role=plain(role[1]) if role else '',dates=dates,image_url=image_url,image_alt=html.unescape(attrs.get('alt','')),links=links))
    return cards

def claims(entity,prop):
    values=[c for c in entity.get('claims',{}).get(prop,[]) if c.get('rank')!='deprecated' and c['mainsnak'].get('snaktype')=='value']
    return [c for c in values if c.get('rank')=='preferred'] or values

def value(claim):return claim['mainsnak']['datavalue']['value']

def birth_bounds(raw):
    if raw.get('calendarmodel','').split('/')[-1]!='Q1985727':raise ValueError('non-Gregorian birth date')
    year,month,day=map(int,raw['time'].split('T')[0].lstrip('+').split('-'))
    precision=raw['precision']
    if precision>=11:return date(year,month,day),date(year,month,day),'day'
    if precision==10:return date(year,month,1),date(year,month,calendar.monthrange(year,month)[1]),'month'
    if precision==9:return date(year,1,1),date(year,12,31),'year'
    raise ValueError('birth date less precise than a year')

def age(born,start):return start.year-born.year-((start.month,start.day)<(born.month,born.day))

def write_csv(name,rows):
    if not rows:return
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def main():
    evidence=json.loads((OUT/'evidence.json').read_text(encoding='utf-8'))
    data=json.loads(CURATED.read_text(encoding='utf-8'))
    people={p['name']:p for p in data['people']}
    with (ROOT/'data/processed/atlas/ministers.csv').open(encoding='utf-8') as f:spells=list(csv.DictReader(f))
    cdi=cdi_cards();findings=[];coverage=[];portraits=[];crosswalk=[]
    baseline=data.setdefault('first_pass_baseline',{k:sum(bool(p.get(k)) for p in people.values()) for k in ['birth_date','sex','hair']})
    for row in evidence['identity_mapping']:
        p=people[row['name']];qid=row.get('qid');entity=evidence['entities'].get(qid,{})
        p['wikidata_id']=qid;p['wikidata_url']='https://www.wikidata.org/wiki/'+qid
        p['wikipedia_url']=row['wikipedia_url']
        aliases=[p['name'],row.get('resolved_title','')]+[v['value'] for v in entity.get('labels',{}).values()]+[v['value'] for vals in entity.get('aliases',{}).values() for v in vals]
        aliases=[tokens(v) for v in aliases if v]
        matches=[c for c in cdi if tokens(c['name']) in aliases]
        method='exact name/alias tokens'
        if not matches:
            candidates=[c for c in cdi if any(a and tokens(c['name']) and (tokens(c['name']).issubset(a) or a.issubset(tokens(c['name']))) for a in aliases)]
            groups={tokens(c['name']) for c in candidates}
            if len(groups)==1:matches=candidates;method='unique compatible name tokens; first pass'
        if len({tokens(c['name']) for c in matches})>1:
            findings.append(dict(name=p['name'],field='CDI identity',detail='Several CDI people match; not linked.'));matches=[]
        p['cdi_records']=matches
        p['cdi_source_url']=CDI_URL if matches else None
        for c in matches:crosswalk.append(dict(name=p['name'],qid=qid,cdi_name=c['name'],role=c['role'],period=' — '.join(c['dates']),match_method=method,image_url=c['image_url'] or ''))
        birth_claims=claims(entity,'P569');sex_claims=claims(entity,'P21');image_claims=claims(entity,'P18')
        p['wikidata_evidence']={prop:[dict(statement_id=c['id'],value=value(c),reference_count=len(c.get('references',[])),references=c.get('references',[])) for c in claims(entity,prop)] for prop in ['P569','P21','P18']}
        birth_status='existing curated value' if p['birth_date'] else 'missing in source'
        if not p['birth_date'] and birth_claims:
            try:
                bounds=[birth_bounds(value(c)) for c in birth_claims]
                # Compatible imprecise and precise statements can intersect;
                # conflicting years are never silently resolved by rank alone.
                lower=max(b[0] for b in bounds);upper=min(b[1] for b in bounds)
                if lower>upper:raise ValueError('conflicting birth statements')
                starts=[date.fromisoformat(m['start']) for m in spells if m['name']==p['name']]
                if any(age(upper,start)<18 or age(lower,start)>100 for start in starts):raise ValueError('birth incompatible with recorded ministerial service')
                if any(age(upper,start)<30 for start in starts):raise ValueError('age under 30 at recorded service: manual identity/date check required')
                if any(b[2]=='day' and b[0].month==1 and b[0].day==1 and not c.get('references') for b,c in zip(bounds,birth_claims)):raise ValueError('unreferenced 1 January birthday: possible date placeholder')
                p.update(birth_lower=lower.isoformat(),birth_upper=upper.isoformat(),birth_precision='day' if lower==upper else 'month' if lower.year==upper.year and lower.month==upper.month else 'year')
                if lower==upper:p['birth_date']=lower.isoformat()
                birth_status='Wikidata first pass; independent verification pending'
                source=dict(title='Wikidata: nacimiento · primera pasada',url=p['wikidata_url']+'#P569')
                if source not in p['bio_sources']:p['bio_sources'].append(source)
                p['birth_status']=birth_status
            except ValueError as exc:
                birth_status='requires review: '+str(exc)
                findings.append(dict(name=p['name'],field='birth',detail=birth_status))
        elif p['birth_date']:
            p.setdefault('birth_precision','day')
            p.setdefault('birth_lower',p['birth_date']);p.setdefault('birth_upper',p['birth_date'])
        if p.get('birth_status') and p.get('birth_lower'):birth_status=p['birth_status']
        p['birth_review_note']=birth_status
        sex_values={value(c).get('id') for c in sex_claims}
        if len(sex_values)==1:
            raw=next(iter(sex_values));mapped={'Q6581097':'Masculino','Q6581072':'Femenino'}.get(raw)
            p['sex_or_gender_source_value']=raw
            if not p['sex'] and mapped:
                p['sex']=mapped;p['sex_status']='Wikidata P21 (sexo o género), primera pasada'
            if mapped and p['sex']!=mapped:findings.append(dict(name=p['name'],field='sex_or_gender',detail='Existing biography differs from Wikidata P21; existing value retained.'))
            p['sex_source_url']=p['wikidata_url']+'#P21'
        else:
            findings.append(dict(name=p['name'],field='sex_or_gender',detail='Missing or multiple non-deprecated P21 values; not filled.'))
        urls=set()
        for c in matches:
            if c['image_url'] and c['image_url'] not in urls:
                urls.add(c['image_url']);alt_warning=bool(c['image_alt'] and tokens(c['image_alt'])!=tokens(c['name']))
                portraits.append(dict(name=p['name'],qid=qid,provider='CDI',source_url=CDI_URL,image_url=c['image_url'],commons_file='',date_status='date of photograph not documented by the ministerial period',identity_warning='image alt differs from CDI name' if alt_warning else 'requires visual identity check',evaluation='not inspected; no score assigned'))
        for claim in image_claims:
            filename=value(claim)
            portraits.append(dict(name=p['name'],qid=qid,provider='Wikidata / Commons',source_url='https://commons.wikimedia.org/wiki/File:'+quote(filename.replace(' ','_')),image_url='https://commons.wikimedia.org/wiki/Special:Redirect/file/'+quote(filename.replace(' ','_')),commons_file=filename,date_status='requires Commons metadata review',identity_warning='requires visual identity check',evaluation='not inspected; no score assigned'))
        p['research_status']='parcial'
        coverage.append(dict(name=p['name'],qid=qid,cdi_records=len(matches),birth_date=p['birth_date'] or '',birth_lower=p.get('birth_lower',''),birth_upper=p.get('birth_upper',''),birth_precision=p.get('birth_precision',''),birth_status=birth_status,sex_or_gender=p['sex'] or '',sex_source=p.get('sex_source_url',''),cdi_portrait=any(c['image_url'] for c in matches),wikidata_portraits=len(image_claims),hair_score='' if not p['hair'] else p['hair']['score']))
    data['first_pass']={'sources':['CDI','Wikidata'],'source_snapshot':evidence['retrieved_at'],'status':'Primera pasada con controles de coherencia; no equivale a contraste biográfico independiente de todos los campos.','baseline':baseline}
    write_csv('coverage.csv',coverage);write_csv('cdi-crosswalk.csv',crosswalk);write_csv('portrait-candidates.csv',portraits);write_csv('review-findings.csv',findings)
    (OUT/'cdi-records.json').write_text(json.dumps(cdi,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary=dict(names=len(people),wikidata_entities=len({p['wikidata_id'] for p in people.values()}),cdi_matched_names=sum(bool(p['cdi_records']) for p in people.values()),exact_birth=sum(bool(p['birth_date']) for p in people.values()),partial_birth=sum(bool(p.get('birth_lower')) and not p['birth_date'] for p in people.values()),sex_or_gender=sum(bool(p['sex']) for p in people.values()),portrait_candidate_names=len({p['name'] for p in portraits}),portrait_candidates=len(portraits),evaluated_hair=sum(bool(p['hair']) for p in people.values()),review_findings=len(findings),baseline=baseline)
    summary['evaluated_hair_identities']=len({p.get('wikidata_id') or p['name'] for p in people.values() if p['hair']})
    data['first_pass']['coverage']=summary
    CURATED.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    pending=[p['name'] for p in people.values() if not p['birth_date'] and not p.get('birth_lower')]
    report=f'''# Primera pasada CDI + Wikidata — 23/10/2026

## Resultado

La pasada se ejecutó sobre los {summary['names']} nombres del inventario, que apuntan a {summary['wikidata_entities']} entidades de Wikidata. Las variantes José / José María Dagnino Pastore comparten identificador. Se conservan los nombres del inventario y no se modifica ninguna fecha de cargo.

| Campo | Antes | Después |
|---|---:|---:|
| Nacimiento con día, mes y año | {baseline['birth_date']} | {summary['exact_birth']} |
| Nacimiento con mes/año o solo año | 0 | {summary['partial_birth']} |
| Sexo/género con fuente | {baseline['sex']} | {summary['sex_or_gender']} |
| Índices pelados con imagen inspeccionada (personas distintas) | {baseline['hair']} | {summary['evaluated_hair_identities']} |

CDI permitió vincular {summary['cdi_matched_names']} nombres. Se localizaron {summary['portrait_candidates']} referencias de imágenes, procedentes de CDI y Wikidata/Commons, para {summary['portrait_candidate_names']} nombres. Son referencias candidatas: ni su identificación ni su fecha de toma se presumen verificadas por encontrarlas.

Las evaluaciones visuales cubren {summary['evaluated_hair_identities']} personas distintas, reflejadas en {summary['evaluated_hair']} fichas por los alias del inventario. Las tandas descargadas y revisadas están documentadas en `portrait-review-batch.json` y `recent-portrait-review.json`; incluyen imágenes fechadas y retratos sin fecha, que pueden puntuarse si permiten identificar a la persona y apreciar el pelo.

## Criterio de incorporación

Se resolvieron los nombres desde los enlaces de Wikipedia ya incluidos en los insumos originales, siguiendo normalizaciones y redirecciones hasta su QID. No se aceptó la primera coincidencia de una búsqueda nominal. CDI se vinculó mediante nombres y alias compatibles, guardando la regla de correspondencia y sus registros completos.

Los valores existentes de nacimiento se conservaron. P569 de Wikidata se importó solo si sus declaraciones seleccionadas eran compatibles y pasaban controles de cronología. Se respetó la precisión del dato: los valores por año o mes producen intervalos de edad, nunca un cumpleaños inventado. Un 1 de enero almacenado con precisión de año no significa nacimiento el 1 de enero.

P21 se conserva como sexo o género según la fuente, no como una certificación de sexo registral. La ficha enlaza la propiedad y conserva el valor original. Las afirmaciones y referencias descargadas están guardadas por campo. Los datos nuevos se identifican como primera pasada: no se presentan como cotejados independientemente con documentos primarios.

## Pendientes y controles

Quedan sin fecha de nacimiento utilizable: {', '.join(pending)}.

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
'''
    (ROOT/'notes/research-cdi-wikidata-2026-10-23.md').write_text(report,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True))

if __name__=='__main__':main()
