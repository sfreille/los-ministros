"""Regression checks for historical boundary cases and derived measures."""
from pathlib import Path
from datetime import date
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'data/processed/atlas/atlas.json').read_text(encoding='utf-8'))
ps, ms, links = data['presidents'], data['ministers'], data['links']
def find(rows, name, start):
    return next(r for r in rows if r['name'] == name and r['start'] == start)
def duration(a, b):
    return (date.fromisoformat(b)-date.fromisoformat(a)).days
assert find(ms, 'Emilio Hansen', '1891-10-22')['end'] == '1892-10-12'
assert find(ms, 'Marco Aurelio Avellaneda', '1901-07-11')['end'] == '1904-10-12'
romero = find(ms, 'Juan José Romero', '1892-10-12')
saenz = find(ps, 'Luis Sáenz Peña', '1892-10-12')
assert any(l['minister_id']==romero['id'] and l['president_id']==saenz['id'] and l['initiated'] for l in links)
pellegrini = find(ps, 'Carlos Pellegrini', '1890-08-06')
assert not any(l['minister_id']==romero['id'] and l['president_id']==pellegrini['id'] for l in links)
cortinez = find(ms, 'Santiago Cortínez', '1880-05-07')
assert not any(l['minister_id']==cortinez['id'] for l in links)
assert len([p for p in ps if p['name']=='Julio Argentino Roca']) == 2
assert len([p for p in ps if p['name']=='Pedro Pablo Ramírez']) == 1
pinedo = next(p for p in ps if p['name']=='Federico Pinedo')
assert pinedo['days']==0 and pinedo['appointments_per_year'] is None
caputo = find(ms, 'Luis Caputo', '2023-12-10')
assert caputo['ongoing'] and caputo['end']==data['cutoff']
for l in links:
    p=next(p for p in ps if p['id']==l['president_id'])
    m=next(m for m in ms if m['id']==l['minister_id'])
    assert l['start']==max(p['start'],m['start'])
    assert l['end']==min(p['end'],m['end'])
    assert 0<l['days']==duration(l['start'],l['end'])<=min(p['days'],m['days'])
for p in ps:
    ls=[l for l in links if l['president_id']==p['id']]
    assert p['spells_serving']==len(ls)
    assert p['appointments']<=p['spells_serving']
    assert 0<=p['uncovered_days']<=p['days']
for name, digest in json.loads((ROOT / 'data/processed/atlas/source_hashes.json').read_text()).items():
    assert hashlib.sha256((ROOT/'data'/name).read_bytes()).hexdigest()==digest
regimes = data['classification']['periods']
assert len(regimes) == 17
for a, b in zip(regimes, regimes[1:]):
    assert a['end'] == b['start']
for m in ms:
    fragments = [r for r in data['regime_service'] if r['minister_id'] == m['id']]
    expected = max(0, duration(max(m['start'], regimes[0]['start']), min(m['end'], data['cutoff'])))
    assert sum(r['days'] for r in fragments) == expected, m['name']
    assert len({r['period_id'] for r in fragments}) == len(fragments)
    for r in fragments:
        period = next(p for p in regimes if p['id'] == r['period_id'])
        assert r['start'] == max(m['start'], period['start'])
        assert r['end'] == min(m['end'], period['end'])
        assert r['days'] == duration(r['start'], r['end']) > 0
assert find(ps, 'Agustín Pedro Justo', '1932-02-20')['regime_categories'] == ['closed']
assert find(ps, 'José María Guido', '1962-03-29')['regime_categories'] == ['de_facto']
assert find(ps, 'Arturo Rawson', '1943-06-04')['regime_categories'] == ['de_facto']
assert find(ps, 'Héctor José Cámpora', '1973-05-25')['regime_categories'] == ['closed']
assert find(ps, 'Juan Perón', '1952-06-04')['regime_categories'] == ['open', 'de_facto']
assert find(ps, 'Ramón Castillo', '1940-07-03')['authority_role'] == 'interino'
assert find(ps, 'Eduardo Lonardi', '1955-09-16')['authority_role'] == 'autoridad disputada'
print('PASS: historical boundaries, date repairs, repeated terms, source preservation, all presidential and regime intersections, conservation of service days, and explicit disputed/acting authority.')

assert len(data["classification"]["categories"]) == 3
assert len(data["classification"]["crosswalk"]) == 9
assert next(m for m in ms if m["name"] == "Domingo Cavallo" and m["start"].startswith("1991"))["age_at_start"] == 44
assert set(p["name"] for p in data["profiles"]["people"]) == set(m["name"] for m in ms)
profiles = {p['name']:p for p in data['profiles']['people']}
for m in ms:
    profile = profiles[m['name']]
    if profile['birth_date']:
        birth, start = date.fromisoformat(profile['birth_date']), date.fromisoformat(m['start'])
        assert m['age_at_start'] == start.year-birth.year-((start.month,start.day)<(birth.month,birth.day))
        assert profile['bio_sources']
    else:
        assert m['age_at_start'] is None
    if profile.get('birth_lower'):
        earliest=date.fromisoformat(profile['birth_lower'])
        latest=date.fromisoformat(profile['birth_upper'])
        start=date.fromisoformat(m['start'])
        age=lambda born:start.year-born.year-((start.month,start.day)<(born.month,born.day))
        assert m['age_at_start_min']==age(latest)
        assert m['age_at_start_max']==age(earliest)
        if not profile['birth_date']:
            assert profile['birth_precision'] in ('month','year')
            assert 0<=m['age_at_start_max']-m['age_at_start_min']<=1
    else:
        assert m['age_at_start_min'] is None and m['age_at_start_max'] is None
for profile in profiles.values():
    hair = profile['hair']
    if hair:
        assert hair['score'] in (0,25,50,75,100)
        assert hair['period'] and hair['note'] and hair['source_url']
        assert (ROOT/hair['local_path']).is_file()
        if hair.get('sha256'):
            assert hashlib.sha256((ROOT/hair['local_path']).read_bytes()).hexdigest()==hair['sha256']
manifest = json.loads((ROOT/'data/external/portraits/manifest.json').read_text(encoding='utf-8'))
for item in manifest['images']:
    assert item['status']=='downloaded'
    assert hashlib.sha256((ROOT/item['local_path']).read_bytes()).hexdigest()==item['sha256']
assert profiles['Pedro Groppo']['birth_date'] is None
assert profiles['Norberto Piñero']['birth_date'] is None
assert profiles['Juan A. Quilici']['birth_date'] is None
assert profiles['José Dagnino Pastore']['wikidata_id']==profiles['José María Dagnino Pastore']['wikidata_id']
assert profiles['Carlos Rafael Fernández']['birth_date'] is None
assert profiles['Carlos Rafael Fernández']['birth_lower']=='1954-01-01'
assert profiles['Carlos Rafael Fernández']['birth_upper']=='1954-12-31'
biography_root=ROOT/'data/external/biographies'
for filename,digest in json.loads((ROOT/'data/processed/biographies/source_hashes.json').read_text()).items():
    assert hashlib.sha256((biography_root/filename).read_bytes()).hexdigest()==digest
for review_name in data['profiles'].get('portrait_review',{}).get('review_files',[]):
    review=json.loads((ROOT/'data/processed/biographies'/review_name).read_text(encoding='utf-8'))
    for item in review.get('images',[]):
        if item.get('local_path') and item.get('sha256'):
            assert hashlib.sha256((ROOT/item['local_path']).read_bytes()).hexdigest()==item['sha256']
print('PASS: exact and partial biographical ages, quarantined conflicting/impossible dates, shared identity, cached CDI/Wikidata evidence and inspected image references.')
