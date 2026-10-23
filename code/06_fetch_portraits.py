"""Download the curated image references for visual coding, never into the site.

Files are research references; their original rights remain with their authors.
The manifest records retrieval, a hash and source page for reproducible inspection.
"""
from pathlib import Path
from datetime import datetime, timezone
import concurrent.futures
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data/external/portraits'
SOURCES = ROOT / 'data/curated/portrait-sources.json'

def download(item):
    result = dict(item)
    target = DEST / item['filename']
    try:
        if not target.exists():
            request = urllib.request.Request(item['image_url'], headers={'User-Agent': 'ArgentinaMinistersAtlas/1.0 (historical research)'})
            with urllib.request.urlopen(request, timeout=25) as response:
                payload = response.read(15_000_001)
                content_type = response.headers.get_content_type()
            if not content_type.startswith('image/') or len(payload) > 15_000_000:
                raise ValueError('Response is not a supported image or exceeds 15 MB')
            target.write_bytes(payload)
        payload = target.read_bytes()
        result.update(status='downloaded', bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                      local_path=target.relative_to(ROOT).as_posix())
    except Exception as exc:
        result.update(status='failed', error=str(exc))
    return result

if __name__ == '__main__':
    DEST.mkdir(parents=True, exist_ok=True)
    sources = json.loads(SOURCES.read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(download, sources))
    manifest = dict(retrieved_at=datetime.now(timezone.utc).isoformat(),
                    purpose='Referencias para codificación visual; no se incrustan ni publican en el atlas.', images=results)
    (DEST/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for row in results:
        print(row['name'], row['status'], row.get('bytes', row.get('error')))
    raise SystemExit(any(r['status']=='failed' for r in results))
