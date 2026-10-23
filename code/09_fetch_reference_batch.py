"""Fetch a scoped portrait research batch, preserving evidence and manual review.

Uses exact P18 values in the cached Wikidata entities. Commons imageinfo metadata
is saved verbatim before downloading images; CDI references provide comparisons
and fallbacks, with no capture date inferred from a minister's term. No files
outside pass1 and portrait-review-batch.json are written. Run --assemble after
visually inspecting references and writing pass1/observations.json.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import unicodedata
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/external/portraits/pass1"
REVIEW = ROOT / "data/processed/biographies/portrait-review-batch.json"
TARGETS = [
    "Domingo Salaberry", "Ramón Antonio Cereijo", "Álvaro Alsogaray",
    "Roberto Alemann", "Adalbert Krieger Vasena", "José Ber Gelbard",
    "José Alfredo Martínez de Hoz", "Lorenzo Sigaut", "Bernardo Grinspun",
    "Roberto Lavagna", "Felisa Miceli", "Axel Kicillof", "Martín Guzmán",
    "Sergio Massa", "Roque Fernández",
]
AGENT = "ArgentinaMinistersAtlas/1.0 (reference research; local visual review)"
MAX_BYTES = 25_000_000


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()).strip("-")


def now():
    return datetime.now(timezone.utc).isoformat()


def retrieve(url, target, image=False):
    """Keep exact payload, response headers, resolved URL, and SHA256."""
    receipt = target.with_name(target.name + ".http.json")
    if target.exists() and receipt.exists():
        metadata = read_json(receipt)
        if hashlib.sha256(target.read_bytes()).hexdigest() != metadata["sha256"]:
            raise ValueError(f"Cached hash mismatch: {target}")
        return metadata
    request = Request(url, headers={"User-Agent": AGENT})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=35) as response:
                payload = response.read(MAX_BYTES + 1)
                content_type = response.headers.get_content_type()
                metadata = dict(request_url=url, final_url=response.url,
                                status=response.status, headers=dict(response.headers),
                                content_type=content_type, retrieved_at=now())
            break
        except HTTPError as exc:
            failure = target.with_name(target.name + f".error-{attempt}.json")
            write_json(failure, dict(request_url=url, status=exc.code, headers=dict(exc.headers),
                                     body=exc.read(10000).decode("utf-8", "replace"), retrieved_at=now()))
            if exc.code != 429 or attempt == 2:
                raise
            delay = exc.headers.get("Retry-After", "")
            # A longer server-requested cooldown is left for a later manual rerun.
            if delay.isdigit() and int(delay) > 45:
                raise
            time.sleep(int(delay) if delay.isdigit() else (4 * (attempt + 1)))
    if len(payload) > MAX_BYTES:
        raise ValueError("Response exceeds 25 MB")
    if image and not content_type.startswith("image/"):
        raise ValueError(f"Expected image; got {content_type}")
    target.write_bytes(payload)
    metadata.update(sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload),
                    local_path=target.relative_to(ROOT).as_posix())
    write_json(receipt, metadata)
    return metadata


def fetch(names):
    DEST.mkdir(parents=True, exist_ok=True)
    evidence = read_json(ROOT / "data/processed/biographies/evidence.json")
    identities = {item["name"]: item for item in evidence["identity_mapping"]}
    with (ROOT / "data/processed/biographies/portrait-candidates.csv").open(encoding="utf-8-sig", newline="") as stream:
        candidates = list(csv.DictReader(stream))
    results = []
    old_manifest = DEST / "manifest.json"
    if old_manifest.exists():
        results = [row for row in read_json(old_manifest)["images"] if row["name"] not in names]
    for name in names:
        identity = identities[name]
        entity = evidence["entities"][identity["qid"]]
        p18 = [claim["mainsnak"]["datavalue"]["value"]
               for claim in entity.get("claims", {}).get("P18", [])
               if "datavalue" in claim.get("mainsnak", {}) and claim.get("rank") != "deprecated"]
        for index, filename in enumerate(p18):
            row = dict(name=name, qid=identity["qid"], provider="Wikidata / Commons",
                       exact_cached_p18=filename, source_url="https://commons.wikimedia.org/wiki/File:" + quote(filename.replace(" ", "_")),
                       identity_status="pending visual inspection", capture_date_status="pending metadata inspection")
            try:
                api_url = "https://commons.wikimedia.org/w/api.php?" + urlencode(dict(
                    action="query", format="json", titles="File:" + filename, prop="imageinfo",
                    iiprop="url|size|extmetadata|timestamp|sha1", iiurlwidth=1000, redirects=1))
                metadata_target = DEST / (slug(name) + f"-commons-{index}.imageinfo.json")
                api_receipt = retrieve(api_url, metadata_target)
                raw = read_json(metadata_target)
                info = next(page["imageinfo"][0] for page in raw["query"]["pages"].values() if page.get("imageinfo"))
                row.update(metadata_api_url=api_url, raw_metadata_path=api_receipt["local_path"],
                           extmetadata=info.get("extmetadata", {}), upload_timestamp=info.get("timestamp"),
                           original_image_url=info["url"], original_width=info.get("width"), original_height=info.get("height"))
                row["image_url"] = info.get("thumburl", info["url"])
                suffix = Path(info["url"]).suffix.lower()
                if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
                    suffix = ".jpg"
                target = DEST / (slug(name) + "-commons" + (f"-{index}" if index else "") + suffix)
                try:
                    row.update(retrieve(row["image_url"], target, image=True), status="downloaded")
                except HTTPError as exc:
                    if row["image_url"] == info["url"]:
                        raise
                    row["thumbnail_error"] = str(exc)
                    row["image_url"] = info["url"]
                    row.update(retrieve(row["image_url"], target, image=True), status="downloaded")
                # A cached original may be reused after a previous thumbnail failure.
                row["image_url"] = row["request_url"]
            except Exception as exc:
                row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            results.append(row)
            print(name, "Commons", row["status"], row.get("error", row.get("bytes")), flush=True)
            time.sleep(0.3)
        for candidate in candidates:
            if candidate["name"] != name or candidate["provider"] != "CDI":
                continue
            row = dict(candidate, identity_status="pending visual inspection",
                       capture_date=None, capture_date_precision="unknown",
                       license="Not specified on cached CDI page; reference research only")
            try:
                target = DEST / (slug(name) + "-cdi" + Path(candidate["image_url"]).suffix)
                row.update(retrieve(candidate["image_url"], target, image=True), status="downloaded")
            except Exception as exc:
                row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            results.append(row)
            print(name, "CDI", row["status"], row.get("error", row.get("bytes")), flush=True)
        write_json(old_manifest, dict(retrieved_at=now(), purpose="Research references only; no atlas images", images=results))


def assemble():
    manifest = read_json(DEST / "manifest.json")
    observations = read_json(DEST / "observations.json")
    by_path = {row.get("local_path"): row for row in manifest["images"] if row["status"] == "downloaded"}
    image_reviews = {row["local_path"]: row for row in observations["image_reviews"]}
    assert set(by_path) == set(image_reviews), "Every downloaded image must have a manual visual review"
    selected = {row["hair"]["local_path"] for row in observations["people"]}
    for path, item in by_path.items():
        item["visual_review"] = image_reviews[path]
        item["identity_status"] = image_reviews[path]["identity_status"]
        item["selected_for_proposal"] = path in selected
        item["eligible_for_scoring"] = not any(
            excluded.get("local_path") == path and excluded.get("scope") == "image excluded from scoring"
            for excluded in observations.get("exclusions", [])
        )
        item["capture_date_status"] = image_reviews[path]["capture_date_status"]
        item.pop("evaluation", None)
    for person in observations["people"]:
        hair = person["hair"]
        assert hair["score"] in (0, 25, 50, 75, 100)
        image = by_path[hair["local_path"]]
        assert image["name"] == person["name"]
        assert hashlib.sha256((ROOT / hair["local_path"]).read_bytes()).hexdigest() == image["sha256"]
        assert hair["observer"] and hair["note"] and hair["view_limitations"]
        assert hair["capture_date_precision"] in {"unknown", "day", "year", "approximate-year"}
        assert hair["capture_date_precision"] != "unknown" or hair["capture_date"] is None
        hair.update(source_url=image["source_url"], image_url=image["image_url"], sha256=image["sha256"])
        if image["provider"] == "Wikidata / Commons":
            hair["source_declared_date_raw"] = image.get("extmetadata", {}).get("DateTimeOriginal", {}).get("value")
            hair["capture_date_status"] = "unknown" if hair["capture_date"] is None else "source-declared; precision retained, not independently authenticated"
            if person["name"] in {"José Alfredo Martínez de Hoz", "Martín Guzmán"}:
                hair["capture_date_status"] = "source-declared; exact capture versus publication date uncorroborated"
                hair["capture_date_confidence"] = "baja"
        else:
            hair["capture_date_status"] = "unknown"
    write_json(REVIEW, dict(
        version="portrait-review-batch-pass1", reviewed_at=now(),
        status="Proposals only; not merged into curated profiles",
        methodology=observations["methodology"] + " La fecha de toma es ideal, pero no obligatoria para puntuar: la inclusión depende de identidad y visibilidad suficientes. Los retratos sin fecha conservan capture_date=null; el vínculo con un período ministerial se señala como probable y no verificado cuando corresponde. No se exige coincidencia con el año de asunción.", people=observations["people"],
        images=manifest["images"], exclusions=observations.get("exclusions", [])))
    print(f"Assembled {len(observations['people'])} proposals; {len(manifest['images'])} fetch records", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assemble", action="store_true")
    parser.add_argument("--names", nargs="+", choices=TARGETS)
    args = parser.parse_args()
    if args.assemble:
        assemble()
    else:
        fetch(args.names or TARGETS)
