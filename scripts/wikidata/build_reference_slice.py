#!/usr/bin/env python3
"""Build a tiny reproducible Wikidata reference slice (network; never imported by tests).

Endpoints: WDQS (targeted VALUES queries, used for selection and light descriptions) and
Special:EntityData JSON (full statements with ranks and qualifiers for a few entities and
properties). No Action API (rate-limited here), no HTML. Every request is logged in the manifest
with URL, UTC time, HTTP status, size and sha256; SPARQL query texts are stored verbatim.

Outputs:
  data/wikidata_slice/raw/<ID>.json.gz      raw Special:EntityData responses (gitignored)
  data/wikidata_slice/raw/wdqs_<n>.json.gz  raw WDQS responses (gitignored)
  data/wikidata_slice/kgview.json           normalised kgview/v1 (gitignored)
  manifests/wikidata_reference_slice.json   metadata only (committed)

Constraints are stored as found (type, status, separators, exceptions, other qualifiers). They
are guidance with exceptions, never axioms. Mutability is not taken from Wikidata (left null).
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from kgrerank.manifest import git_state, sha256_bytes, sha256_file, utc_now, write_manifest  # noqa: E402

WDQS = "https://query.wikidata.org/sparql"
ENTITY_DATA = "https://www.wikidata.org/wiki/Special:EntityData/{id}.json"
STATUS = {"Q21502408": "mandatory", "Q62026391": "suggestion"}
MAX_EXCEPTIONS_STORED = 200


class StopBuild(RuntimeError):
    """Stop without bypassing: rate limit, size cap or ID budget reached."""


class Fetcher:
    def __init__(
        self, ua: str, sleep_s: float, max_bytes: int, raw_dir: Path, previous: list[dict] | None
    ):
        self.ua, self.sleep_s, self.max_bytes, self.raw_dir = ua, sleep_s, max_bytes, raw_dir
        self.log: list[dict[str, Any]] = []
        self.stored_bytes = 0
        self._first = True
        # Successful requests of a previous run whose raw response is still on disk are reused
        # (no re-download); the original request record is copied into the new log.
        self._previous = {r["url"]: r for r in (previous or []) if r.get("status") == 200}

    def cached(self, name: str, url: str) -> bytes | None:
        path = self.raw_dir / f"{name}.json.gz"
        prev = self._previous.get(url)
        if prev is None or not path.exists():
            return None
        body = gzip.decompress(path.read_bytes())
        if sha256_bytes(body) != prev.get("sha256"):
            return None
        self.log.append({**prev, "reused_from_previous_run": True})
        self.stored_bytes += path.stat().st_size
        return body

    def _get(self, url: str, accept: str) -> tuple[int, bytes, str]:
        if not self._first:
            time.sleep(self.sleep_s)
        self._first = False
        req = urllib.request.Request(url, headers={"User-Agent": self.ua, "Accept": accept})
        ts = utc_now()
        with urllib.request.urlopen(req, timeout=90) as resp:  # fixed Wikimedia endpoints
            body = resp.read(self.max_bytes + 1)
            if len(body) > self.max_bytes:
                raise StopBuild(f"response larger than {self.max_bytes} bytes: {url}")
            return resp.status, body, ts

    def get(self, url: str, accept: str = "application/json", **extra: Any) -> bytes:
        for attempt in (1, 2):
            try:
                status, body, ts = self._get(url, accept)
            except urllib.error.HTTPError as err:
                retry_after = err.headers.get("Retry-After") if err.headers else None
                self.log.append(
                    {
                        "url": url,
                        "utc": utc_now(),
                        "status": err.code,
                        "retry_after": retry_after,
                        **extra,
                    }
                )
                if err.code == 429 and attempt == 1:
                    wait = min(float(err.headers.get("Retry-After") or 10), 30.0)
                    time.sleep(wait)  # one polite retry, then stop
                    continue
                raise StopBuild(f"HTTP {err.code} for {url}") from err
            self.log.append(
                {
                    "url": url,
                    "utc": ts,
                    "status": status,
                    "bytes": len(body),
                    "sha256": sha256_bytes(body),
                    **extra,
                }
            )
            return body
        raise StopBuild(f"rate limited twice: {url}")

    def store(self, name: str, body: bytes) -> None:
        path = self.raw_dir / f"{name}.json.gz"
        data = gzip.compress(body, mtime=0)
        path.write_bytes(data)
        self.stored_bytes += len(data)

    def sparql(self, query: str, name: str) -> dict[str, Any]:
        url = f"{WDQS}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}"
        body = self.cached(name, url)
        if body is None:
            body = self.get(url, "application/sparql-results+json", query=query)
            self.store(name, body)
        return json.loads(body)

    def entity(self, eid: str) -> bytes:
        url = ENTITY_DATA.format(id=eid)
        body = self.cached(eid, url)
        if body is None:
            body = self.get(url, id=eid)
            self.store(eid, body)
        return body


# ---------------------------------------------------------------------------- parsing
def snak_value(snak: dict[str, Any]) -> dict[str, Any]:
    st = snak.get("snaktype")
    if st != "value":
        return {"kind": st or "unknown", "value": ""}
    dv = snak["datavalue"]
    t, v = dv.get("type"), dv.get("value")
    if t == "wikibase-entityid":
        return {"kind": "item", "value": v.get("id") or f"Q{v.get('numeric-id')}"}
    if t == "string":
        return {"kind": "string", "value": v}
    if t == "monolingualtext":
        return {"kind": "text", "value": v["text"], "lang": v.get("language")}
    if t == "time":
        # Calendar model (Julian/Gregorian) is not converted; documented limitation.
        return {"kind": "time", "value": v["time"], "precision": v.get("precision")}
    if t == "quantity":
        return {"kind": "quantity", "value": v.get("amount")}
    if t == "globecoordinate":
        return {"kind": "coordinate", "value": f"{v.get('latitude')},{v.get('longitude')}"}
    return {"kind": t or "unknown", "value": json.dumps(v, sort_keys=True)}


def statement_record(eid: str, pid: str, st: dict[str, Any]) -> dict[str, Any]:
    quals = {
        qpid: [snak_value(s) for s in snaks]
        for qpid, snaks in sorted((st.get("qualifiers") or {}).items())
    }
    return {
        "sid": st.get("id", f"{eid}-{pid}"),
        "s": eid,
        "p": pid,
        "v": snak_value(st["mainsnak"]),
        "rank": st.get("rank", "normal"),
        "q": quals,
        "n_refs": len(st.get("references") or []),
    }


def only_entity(doc: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    ents = doc.get("entities") or {}
    if len(ents) != 1:
        raise StopBuild(f"expected one entity, got {list(ents)}")
    return next(iter(ents.items()))


def lang_text(d: dict[str, Any], lang: str) -> str:
    return (d.get(lang) or {}).get("value", "")


def constraint_record(st: dict[str, Any]) -> dict[str, Any]:
    ctype = snak_value(st["mainsnak"]).get("value")
    quals = st.get("qualifiers") or {}

    def items(pid: str) -> list[str]:
        return [
            snak_value(s).get("value", "")
            for s in quals.get(pid, [])
            if s.get("snaktype") == "value"
        ]

    status_items = items("P2316")
    exceptions = items("P2303")
    params = {
        pid: [snak_value(s).get("value", "") for s in snaks]
        for pid, snaks in sorted(quals.items())
        if pid not in ("P2316", "P2303", "P4155")
    }
    return {
        "type": ctype,
        "status": STATUS.get(status_items[0], status_items[0]) if status_items else None,
        "separators": items("P4155"),
        "exceptions": exceptions,
        "exceptions_count": len(exceptions),
        "params": params,
        "statement_rank": st.get("rank", "normal"),
    }


# ---------------------------------------------------------------------------- build
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    cfg = yaml.safe_load(Path(ap.parse_args().config).read_text(encoding="utf-8"))
    out_dir = ROOT / cfg["out_dir"]
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    prev_path = ROOT / cfg["manifest"]
    previous = (
        json.loads(prev_path.read_text("utf-8")).get("requests") if prev_path.exists() else None
    )
    f = Fetcher(
        cfg["user_agent"], float(cfg["sleep_s"]), int(cfg["max_response_bytes"]), raw_dir, previous
    )
    langs, max_ids = cfg["languages"], int(cfg["max_ids"])
    props_wanted = list(dict.fromkeys(cfg["properties"]))
    entities: dict[str, dict[str, Any]] = {}
    statements: list[dict[str, Any]] = []
    properties: dict[str, dict[str, Any]] = {}
    revisions: dict[str, Any] = {}
    notes: list[str] = []
    seeds: dict[str, str] = {}
    status = "complete"
    try:
        # 1) selection: enwiki titles -> QIDs (WDQS sitelinks)
        titles = " ".join(
            json.dumps(t, ensure_ascii=False) + "@en" for t in cfg["seed_enwiki_titles"]
        )
        q = (
            "SELECT ?title ?item WHERE { VALUES ?title { " + titles + " } "
            "?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; "
            "schema:name ?title . }"
        )
        res = f.sparql(q, "wdqs_1_titles")
        seeds = {
            b["title"]["value"]: b["item"]["value"].rsplit("/", 1)[-1]
            for b in res["results"]["bindings"]
        }
        missing = [t for t in cfg["seed_enwiki_titles"] if t not in seeds]
        if missing:
            notes.append(f"titles not resolved: {missing}")
        if len(props_wanted) + len(seeds) > max_ids:
            raise StopBuild("ID budget exceeded by properties + seeds")

        # 2) seeds: full statements via Special:EntityData
        keep = set(cfg["keep_properties"])
        for title, qid in sorted(seeds.items(), key=lambda kv: kv[1]):
            body = f.entity(qid)
            eid, ent = only_entity(json.loads(body))
            revisions[eid] = {
                "lastrevid": ent.get("lastrevid"),
                "modified": ent.get("modified"),
                "pinned_url": f"{ENTITY_DATA.format(id=eid)}?revision={ent.get('lastrevid')}",
            }
            entities[eid] = {
                "label": lang_text(ent.get("labels", {}), "en"),
                "aliases": [a["value"] for a in (ent.get("aliases") or {}).get("en", [])],
                "description": lang_text(ent.get("descriptions", {}), "en"),
                "labels_other": {
                    lg: lang_text(ent.get("labels", {}), lg) for lg in langs if lg != "en"
                },
                "lastrevid": ent.get("lastrevid"),
                "enwiki_title": title,
                "detail": "full",
            }
            for pid in sorted(keep):
                for st in (ent.get("claims") or {}).get(pid, []):
                    statements.append(statement_record(eid, pid, st))

        # 3) properties: metadata and constraint statements via Special:EntityData
        view_ids = set(entities)  # seeds; exceptions outside the view are counted only
        for pid in props_wanted:
            body = f.entity(pid)
            _, ent = only_entity(json.loads(body))
            revisions[pid] = {
                "lastrevid": ent.get("lastrevid"),
                "modified": ent.get("modified"),
                "pinned_url": f"{ENTITY_DATA.format(id=pid)}?revision={ent.get('lastrevid')}",
            }
            claims = ent.get("claims") or {}
            cons = []
            for st in claims.get("P2302", []):
                c = constraint_record(st)
                if len(c["exceptions"]) > MAX_EXCEPTIONS_STORED:
                    c["exceptions"] = sorted(set(c["exceptions"]) & view_ids)
                    c["exceptions_truncated_to_view"] = True
                cons.append(c)
            properties[pid] = {
                "label": lang_text(ent.get("labels", {}), "en"),
                "datatype": ent.get("datatype", ""),
                "constraints": cons,
                "inverse": [snak_value(s["mainsnak"])["value"] for s in claims.get("P1696", [])],
                "subproperty_of": [
                    snak_value(s["mainsnak"])["value"] for s in claims.get("P1647", [])
                ],
                "mutability": None,
                "lastrevid": ent.get("lastrevid"),
            }
            if f.stored_bytes > int(cfg["max_stored_bytes"]):
                raise StopBuild(f"stored bytes exceed {cfg['max_stored_bytes']}")

        # 4) optional: light descriptions of referenced items (WDQS; skipped on rate limit)
        try:
            budget = max_ids - len(props_wanted) - len(entities)
            frontier = sorted(
                {
                    v["value"]
                    for st in statements
                    for v in [st["v"], *(x for vs in st["q"].values() for x in vs)]
                    if v["kind"] == "item" and v["value"] not in entities
                },
                key=lambda x: (len(x), x),
            )
            for depth in range(1, int(cfg["describe_depth"]) + 1):
                todo = [x for x in frontier if x not in entities]
                if len(todo) > budget:
                    notes.append(
                        f"depth {depth}: {len(todo) - budget} referenced items dropped (ID budget)"
                    )
                    todo = todo[:budget]
                if not todo:
                    break
                values = " ".join(f"wd:{x}" for x in todo)
                q = (
                    "SELECT ?e ?label ?desc ?type ?parent ?rev WHERE { VALUES ?e { "
                    + values
                    + " } "
                    'OPTIONAL { ?e rdfs:label ?label FILTER(lang(?label) = "en") } '
                    'OPTIONAL { ?e schema:description ?desc FILTER(lang(?desc) = "en") } '
                    "OPTIONAL { ?e wdt:P31 ?type } OPTIONAL { ?e wdt:P131 ?parent } "
                    "OPTIONAL { ?e schema:version ?rev } }"
                )
                res = f.sparql(q, f"wdqs_{depth + 1}_describe")
                new_parents: set[str] = set()
                seen_truthy: set[tuple[str, str, str]] = set()
                for b in res["results"]["bindings"]:
                    e = b["e"]["value"].rsplit("/", 1)[-1]
                    rec = entities.setdefault(
                        e, {"label": "", "aliases": [], "description": "", "detail": "wdqs_light"}
                    )
                    rec["label"] = rec["label"] or b.get("label", {}).get("value", "")
                    rec["description"] = rec["description"] or b.get("desc", {}).get("value", "")
                    if "rev" in b:
                        rec["wdqs_revision"] = int(b["rev"]["value"])
                    for key, pid in (("type", "P31"), ("parent", "P131")):
                        if key in b:
                            val = b[key]["value"].rsplit("/", 1)[-1]
                            if (e, pid, val) not in seen_truthy:
                                seen_truthy.add((e, pid, val))
                                statements.append(
                                    {
                                        "sid": f"wdqs-truthy:{e}:{pid}:{val}",
                                        "s": e,
                                        "p": pid,
                                        "v": {"kind": "item", "value": val},
                                        "rank": "normal",
                                        "q": {},
                                        "n_refs": 0,
                                    }
                                )
                                if pid == "P131":
                                    new_parents.add(val)
                budget = max_ids - len(props_wanted) - len(entities)
                frontier = sorted(new_parents - set(entities), key=lambda x: (len(x), x))

        except StopBuild as err:
            notes.append(f"optional WDQS describe step skipped: {err}")
        # 5) reproducibility check: refetch the first seed pinned to its revision
        first = sorted(seeds.values())[0]
        pinned = revisions[first]["pinned_url"]
        body = f.get(pinned, id=first, purpose="revision-pinned refetch")
        orig = json.loads(gzip.decompress((raw_dir / f"{first}.json.gz").read_bytes()))
        _, a = only_entity(orig)
        _, b = only_entity(json.loads(body))
        revisions["_reproducibility_check"] = {
            "id": first,
            "url": pinned,
            "same_bytes": sha256_bytes(body)
            == sha256_bytes(gzip.decompress((raw_dir / f"{first}.json.gz").read_bytes())),
            "same_claims": a.get("claims") == b.get("claims"),
            "same_lastrevid": a.get("lastrevid") == b.get("lastrevid"),
        }
    except StopBuild as err:
        status = f"stopped: {err}"
        notes.append(status)

    kgview = {
        "format": "kgview/v1",
        "provenance": {
            "source": "wikidata",
            "built_utc": utc_now(),
            "licence": "CC0 (Wikidata)",
            "note": "seed entities: full statements (kept properties); other items: WDQS "
            "light records with truthy P31/P131 (sid prefix wdqs-truthy:)",
        },
        "entities": entities,
        "statements": statements,
        "properties": properties,
    }
    view_path = out_dir / "kgview.json"
    view_path.write_text(
        json.dumps(kgview, ensure_ascii=False, sort_keys=True, indent=1) + "\n", "utf-8"
    )
    ids_total = len(entities) + len(properties)
    summary = {
        pid: sorted(
            {(c["type"], c["status"] or "-", c["exceptions_count"]) for c in p["constraints"]}
        )
        for pid, p in properties.items()
    }
    manifest = {
        "name": "wikidata_reference_slice",
        "status": status,
        "created_utc": utc_now(),
        "script": "scripts/wikidata/build_reference_slice.py",
        "script_sha256": sha256_file(Path(__file__)),
        "repo_git": git_state(ROOT),
        "config": cfg,
        "requests": f.log,
        "counts": {
            "entities": len(entities),
            "seed_entities": len(seeds),
            "properties": len(properties),
            "ids_total": ids_total,
            "statements": len(statements),
        },
        "limits": {
            "max_ids": max_ids,
            "ids_ok": ids_total <= max_ids,
            "stored_bytes": f.stored_bytes,
            "max_stored_bytes": cfg["max_stored_bytes"],
        },
        "revisions": revisions,
        "constraint_summary": {pid: [list(t) for t in v] for pid, v in summary.items()},
        "kgview_path": str(view_path.relative_to(ROOT)),
        "kgview_sha256": sha256_file(view_path),
        "notes": notes,
        "committed": "manifest only; raw responses and kgview stay in data/ (gitignored)",
    }
    write_manifest(ROOT / cfg["manifest"], manifest)
    print(json.dumps({"status": status, **manifest["counts"], **manifest["limits"]}, indent=1))
    return 0 if status == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
