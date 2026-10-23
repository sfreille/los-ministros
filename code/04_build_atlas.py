"""Build the offline atlas and auditable derived data; Python standard library only."""
from pathlib import Path
from datetime import date
import csv
import hashlib
import json
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = '2026-10-14'
OUT = ROOT / 'data/processed/atlas'
OUT.mkdir(parents=True, exist_ok=True)
audit = []

def read(name):
    with (ROOT / 'data' / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days

def issue(kind, record, detail):
    audit.append(dict(kind=kind, record=record, detail=detail))

def write_csv(name, rows):
    if not rows:
        return
    with (OUT / name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows({k: '|'.join(v) if isinstance(v, list) else v for k, v in r.items()} for r in rows)

def clean_name(s):
    return re.sub(r'First.*|Second.*|Third.*', '', re.sub(r'\([^)]*\)', '', s)).strip()

months = {m: i + 1 for i, m in enumerate('enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split())}
def spanish_dates(s):
    return [date(int(y), months[m], int(d)).isoformat() for d, m, y in
            re.findall(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', s.lower()) if m in months]

def build():
    audit.clear()
    classification = json.loads((ROOT / 'data/curated/regime-periods.json').read_text(encoding='utf-8'))
    regimes = classification['periods']
    categories = {c['id']: c for c in classification['categories']}
    assert regimes[0]['start'] == '1880-10-12' and regimes[-1]['end'] == CUTOFF
    for i, r in enumerate(regimes):
        assert r['start'] < r['end'] and r['category'] in categories
        assert all(s in classification['sources'] for s in r['sources'])
        if i:
            assert regimes[i-1]['end'] == r['start'], 'Regime intervals must form a disjoint partition'
    presidents = []
    seen = {}
    for rownum, r in enumerate(read('presidents_clean.csv'), 2):
        name = clean_name(r['name_raw'])
        start, end = r['start_date'], min(r['end_date'], CUTOFF)
        key = (name, start, end)
        if key in seen:
            issue('duplicate_president', f'presidents_clean.csv:{rownum}', f'Identical name and dates to {seen[key]}; removed from derived table.')
            continue
        pid = f'p{rownum:03}'
        seen[key] = pid
        flags = []
        if 'Acting president' in r['notes']:
            flags.append('acting')
        if days(start, end) == 0:
            flags.append('same-day: duration unavailable')
        if name != r['name']:
            issue('display_name', pid, f"{r['name']} -> {name}; parsed from name_raw")
        presidents.append(dict(id=pid, name=name, start=start, end=end,
            days=days(start, end), ongoing=r['end'].lower() == 'incumbent',
            regime=r['regime_detail'], source_regime=r['regime_detail'], notes=r['notes'], source_row=rownum, flags=flags))
    for p in presidents:
        p['regime_periods'] = [r['id'] for r in regimes if max(p['start'], r['start']) < min(p['end'], r['end'])
                               or p['days'] == 0 and r['start'] <= p['start'] < r['end']]
        p['regime_categories'] = list(dict.fromkeys(r['category'] for r in regimes if r['id'] in p['regime_periods']))
        p['regime'] = ' / '.join(categories[c]['label'] for c in p['regime_categories'])
        p['authority_role'] = 'interino' if 'acting' in p['flags'] else 'titular'
        if 'Self-appointed' in p['notes']:
            p['authority_role'] = 'autoridad disputada'
    for i, p in enumerate(presidents):
        for q in presidents[i+1:]:
            a, b = max(p['start'], q['start']), min(p['end'], q['end'])
            if a < b:
                p['flags'].append('overlap: ' + q['id'])
                q['flags'].append('overlap: ' + p['id'])
                issue('presidential_overlap', p['id'] + '/' + q['id'], f'{a} to {b}; retained, not resolved by nearest-date matching.')
    ministers = []
    seen = set()
    for rownum, r in enumerate(read('ministers_clean.csv'), 2):
        mid = f'm{rownum:03}'
        parsed = spanish_dates(r['periodo'])
        start, end = r['start_date'], r['end_date']
        flags = []
        ongoing = bool(re.search(r'desde|en el cargo', r['periodo'], re.I))
        if end in ('', 'NA') and len(parsed) >= 2:
            end = parsed[1]
            flags.append('end date repaired from source period')
            issue('date_repair', mid, f"{r['ministro']}: missing end -> {end}; period: {r['periodo']}")
        if ongoing:
            end = CUTOFF
            flags.append('observed to cutoff; not a completed tenure')
        if start in ('', 'NA') or end in ('', 'NA') or end < start:
            issue('invalid_minister_interval', mid, f'{start} / {end}; excluded from metrics')
            continue
        end = min(end, CUTOFF)
        key = (r['ministro'], start, end, r['ministerio'])
        if key in seen:
            issue('duplicate_minister', mid, str(key))
            continue
        seen.add(key)
        matches = [p for p in presidents if p['start'] <= start < p['end'] and 'acting' not in p['flags']]
        if len(matches) != 1:
            flags.append('appointment president unresolved')
            issue('appointment_link', mid, f"{r['ministro']}: {len(matches)} non-acting matches at {start}")
        elif clean_name(r['president_name']) != matches[0]['name']:
            issue('legacy_link_changed', mid, f"{r['ministro']}: {r['president_name']} -> {matches[0]['name']}")
        ministers.append(dict(id=mid, name=r['ministro'], office=r['ministerio'], start=start, end=end,
            days=days(start, end), ongoing=ongoing, source_president=r['presidente'],
            source_period=r['periodo'], source_row=rownum, flags=flags))
    for i, m in enumerate(ministers):
        for n in ministers[i+1:]:
            a, b = max(m['start'], n['start']), min(m['end'], n['end'])
            if a < b:
                m['flags'].append('minister overlap: ' + n['id'])
                n['flags'].append('minister overlap: ' + m['id'])
                issue('minister_overlap', m['id'] + '/' + n['id'], f'{a} to {b}; offices {m["office"]} / {n["office"]}')
    links = []
    for p in presidents:
        for m in ministers:
            a, b = max(p['start'], m['start']), min(p['end'], m['end'])
            if a < b:
                links.append(dict(president_id=p['id'], minister_id=m['id'], start=a, end=b,
                    days=days(a, b), initiated=p['start'] <= m['start'] < p['end'], ongoing=m['ongoing']))
        ls = [l for l in links if l['president_id'] == p['id']]
        p['spells_serving'] = len(ls)
        p['people_serving'] = len({m['name'] for m in ministers if any(l['minister_id'] == m['id'] for l in ls)})
        p['appointments'] = sum(l['initiated'] for l in ls)
        p['appointments_per_year'] = p['appointments'] * 365.25 / p['days'] if p['days'] else None
        p['mean_service_days'] = statistics.mean(l['days'] for l in ls) if ls else None
        # Union of intervals distinguishes coverage gaps from concurrent offices.
        cursor, covered = p['start'], 0
        for l in sorted(ls, key=lambda x: x['start']):
            if l['end'] > cursor:
                covered += days(max(cursor, l['start']), l['end'])
                cursor = l['end']
        p['uncovered_days'] = p['days'] - covered
        if p['uncovered_days']:
            p['flags'].append(f'{p["uncovered_days"]} days without a recorded minister')
            issue('coverage_gap', p['id'], f'{p["uncovered_days"]} of {p["days"]} days lack minister coverage; not imputed.')
    regime_service = []
    for m in ministers:
        for r in regimes:
            a, b = max(m['start'], r['start']), min(m['end'], r['end'])
            if a < b:
                regime_service.append(dict(minister_id=m['id'], period_id=r['id'], category=r['category'],
                    start=a, end=b, days=days(a, b), ongoing=m['ongoing']))
    profiles = json.loads((ROOT / 'data/curated/minister-profiles.json').read_text(encoding='utf-8'))
    profile_map = {p['name']: p for p in profiles['people']}
    for m in ministers:
        profile = profile_map.get(m['name'], {})
        birth = profile.get('birth_date')
        m['age_at_start'] = None
        m['age_at_start_min'] = None
        m['age_at_start_max'] = None
        m['birth_precision'] = profile.get('birth_precision')
        if birth:
            born, start_date = date.fromisoformat(birth), date.fromisoformat(m['start'])
            m['age_at_start'] = start_date.year-born.year-((start_date.month,start_date.day)<(born.month,born.day))
            m['age_at_start_min'] = m['age_at_start_max'] = m['age_at_start']
            assert 15 <= m['age_at_start'] <= 100, m['name']
        elif profile.get('birth_lower') and profile.get('birth_upper'):
            earliest, latest, start_date = map(date.fromisoformat, [profile['birth_lower'],profile['birth_upper'],m['start']])
            age_at = lambda born: start_date.year-born.year-((start_date.month,start_date.day)<(born.month,born.day))
            m['age_at_start_min'], m['age_at_start_max'] = age_at(latest), age_at(earliest)
            assert 15 <= m['age_at_start_min'] <= m['age_at_start_max'] <= 100, m['name']
    data = dict(cutoff=CUTOFF, profiles=profiles, presidents=presidents, ministers=ministers, links=links, audit=audit,
                classification=classification, regime_service=regime_service)
    for name, rows in [('presidents.csv', presidents), ('ministers.csv', ministers), ('service_intersections.csv', links), ('audit.csv', audit)]:
        write_csv(name, rows)
    (OUT / 'atlas.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    write_csv('regime_service.csv', regime_service)
    write_csv('regime_periods.csv', regimes)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'data').iterdir() if p.suffix in ('.csv', '.html')}
    hashes.update({p.relative_to(ROOT/'data').as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/curated').glob('*.json')})
    (OUT / 'source_hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    template = (ROOT / 'code/d3/atlas.html').read_text(encoding='utf-8')
    license_text = (ROOT / 'code/d3/vendor/LICENSE-d3.txt').read_text(encoding='utf-8')
    html = template.replace('/*__D3__*/', '/*\n' + license_text + '\n*/\n' + (ROOT / 'code/d3/vendor/d3.v7.min.js').read_text(encoding='utf-8'))
    html = html.replace('/*__DATA__*/', json.dumps(data, ensure_ascii=False).replace('<', '\\u003c'))
    if '/*__PELADOMETRO__*/' in html:
        html = html.replace('/*__PELADOMETRO__*/', (ROOT/'code/d3/peladometro.js').read_text(encoding='utf-8'))
    html = html.replace('/*__APP__*/', (ROOT / 'code/d3/atlas.js').read_text(encoding='utf-8'))
    (ROOT / 'output/argentina-ministers-atlas.html').write_text(html, encoding='utf-8')
    print(json.dumps(dict(presidential_records=len(presidents), minister_spells=len(ministers), intersections=len(links), audit_findings=len(audit))))
    return data

if __name__ == '__main__':
    build()
