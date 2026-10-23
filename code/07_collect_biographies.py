"""Collect CDI and Wikidata evidence without modifying curated biographies.

Uses the inventory's own Wikipedia links to resolve identities, not name search.
Responses are cached under data/external/biographies for offline reproduction.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlencode, unquote, urlsplit
from datetime import datetime, timezone
import hashlib
import json
import time
import unicodedata
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT/'data/external/biographies'
OUT = ROOT/'data/processed/biographies'
AGENT = 'ArgentinaMinistersAtlas/1.0 (historical biographical research)'

def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.casefold()) if not unicodedata.combining(c)).strip()

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.current=None
    def handle_starttag(self, tag, attrs):
        if tag=='a': self.current=[dict(attrs),'']
    def handle_data(self, value):
        if self.current is not None: self.current[1]+=value
    def handle_endtag(self, tag):
        if tag=='a' and self.current is not None:
            self.rows.append(self.current); self.current=None

def fetch(url, filename):
    target=EXTERNAL/filename
    if target.exists(): return target.read_bytes()
    request=urllib.request.Request(url,headers={'User-Agent':AGENT,'Accept':'application/json,text/html,text/csv;q=0.9,*/*;q=0.8'})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request,timeout=30) as response: payload=response.read()
            target.write_bytes(payload)
            print('Fetched',filename,len(payload),flush=True)
            return payload
        except Exception:
            if attempt: raise
            time.sleep(1)

def main():
    EXTERNAL.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    profiles=json.loads((ROOT/'data/curated/minister-profiles.json').read_text(encoding='utf-8'))['people']
    links=[]
    for filename in ['economia.html','hacienda.html']:
        parser=Links();parser.feed((ROOT/'data'/filename).read_text(encoding='utf-8'));links+=parser.rows
    mapping=[]
    for person in profiles:
        matches=sorted({attrs['href'] for attrs,text in links if norm(text)==norm(person['name']) and '/wiki/' in attrs.get('href','')})
        assert len(matches)==1,person['name']
        mapping.append(dict(name=person['name'],wikipedia_url=matches[0],title=unquote(urlsplit(matches[0]).path.split('/wiki/')[1]).replace('_',' ')))
    fetch('https://cdi.mecon.gob.ar/ministros-de-economia','cdi-ministers.html')
    fetch('https://cdi.mecon.gob.ar/vertical-timeline/js/ministros.csv','cdi-ministers.csv')
    title_map={};errors=[]
    for i in range(0,len(mapping),25):
        batch=mapping[i:i+25]
        params=dict(action='query',format='json',formatversion=2,prop='pageprops',ppprop='wikibase_item',redirects=1,titles='|'.join(r['title'] for r in batch))
        try:
            result=json.loads(fetch('https://es.wikipedia.org/w/api.php?'+urlencode(params),f'wiki-pages-{i//25+1}.json'))
            query=result['query']
            redirects={r['from']:r['to'] for r in query.get('normalized',[])+query.get('redirects',[])}
            pages={p['title']:p for p in query.get('pages',[])}
            for row in batch:
                title=row['title'];seen=set()
                while title in redirects and title not in seen:
                    seen.add(title);title=redirects[title]
                page=pages.get(title,{})
                title_map[row['title']]=dict(resolved_title=title,qid=page.get('pageprops',{}).get('wikibase_item'))
        except Exception as exc:
            errors.append(dict(stage='wiki-pages',batch=i//25+1,error=str(exc)))
            print('Wikipedia batch failed:',str(exc),flush=True)
    for row in mapping: row.update(title_map.get(row['title'],{}))
    qids=sorted({row['qid'] for row in mapping if row.get('qid')})
    entities={}
    for i in range(0,len(qids),40):
        params=dict(action='wbgetentities',format='json',ids='|'.join(qids[i:i+40]),props='claims|labels|descriptions|aliases|sitelinks',languages='es|en',sitefilter='eswiki')
        try:
            result=json.loads(fetch('https://www.wikidata.org/w/api.php?'+urlencode(params),f'wikidata-entities-{i//40+1}.json'))
            entities.update(result['entities'])
        except Exception as exc:
            errors.append(dict(stage='wikidata',batch=i//40+1,error=str(exc)))
            print('Wikidata batch failed:',str(exc),flush=True)
    evidence=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),identity_mapping=mapping,entities=entities,errors=errors)
    (OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in EXTERNAL.iterdir() if p.is_file()}
    (OUT/'source_hashes.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(inventory_names=len(mapping),mapped_names=sum(bool(r.get('qid')) for r in mapping),entities=len(entities),errors=errors)),flush=True)

if __name__=='__main__': main()
