#!/usr/bin/env python3
"""Give products their SEO meta title (≤ 60 chars) + description (≤ 160) in en, ru and hy, from the templates.

    uv run --no-sync python scripts/set-seo-meta.py <id> [<id> …] [--dry-run]
    uv run --no-sync python scripts/set-seo-meta.py --all [--limit N] [--dry-run]
    uv run --no-sync python scripts/set-seo-meta.py --scan          # read-only: names + existing meta

{Brand} is the brand's name as stored (en, Latin — the same in every locale); {Name} is the
product's name in that locale (names never carry the brand). A locale whose name is missing
(empty, or the same as en — the API falls back to en) uses the en name, and is listed.

Per product: GET en/ru/hy (the "before"), then write en → ru → hy through
siruk.translations.set_meta (the full body is rebuilt by siruk/payload.py from the GET,
rule 10; meta is a top-level request key the server's HasSeo hook stores in the request's
locale). Existing meta is overwritten whatever it holds (user, 2026-10-27); a locale is
skipped only when its stored meta is already exactly the target. Each write is read back in
its locale; at the end the three locales are read again and diffed against "before" with meta
and timestamps ignored — any other change (name, slug, categories, variants, prices, cost,
codes, stock, attributes, images, texts) is a failure.

Note: a ru/hy GET shows en's meta when the locale has none (spatie fallback), so a locale
that only "has" en's text is rewritten — as it should be.

Log: .siruk-cache/seo-meta/log.jsonl (one line per product; --all resumes past ids logged
"ok"; --redo ignores the log). Before/after GETs: .siruk-cache/seo-meta/<id>-<lang>-{before,after}.json (live runs
only; the first "before" is kept, never overwritten).
Pacing: siruk.client (config.json) per call, plus `product.pause_seconds` between products.
"""
import argparse, datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from siruk import client as _client  # noqa: E402
from siruk import config, refdata, seo, translations  # noqa: E402
from siruk import export as _export  # noqa: E402
from siruk.config import ROOT  # noqa: E402
from siruk.payload import PayloadError  # noqa: E402

LANGS = ("en", "ru", "hy")
TITLE_MAX, DESC_MAX = seo.TITLE_MAX, seo.DESC_MAX   # the templates and limits live in siruk/seo.py
OUT = os.path.join(ROOT, ".siruk-cache", "seo-meta")
LOG = os.path.join(OUT, "log.jsonl")
# fields that legitimately change on a meta write (meta_image: null appears once the seo row exists)
IGNORE = {"meta", "meta_image", "updatedAt", "updated_at"}
MISSING = object()


def target(lang, brand, name):
    return seo.meta(lang, brand, name)


def names(recs):
    """{lang: name to use}, [langs that fell back to en]."""
    en = (recs["en"].get("name") or "").strip()
    out, fell = {"en": en}, []
    for l in ("ru", "hy"):
        n = (recs[l].get("name") or "").strip()
        if not n or n == en:
            fell.append(l)
            n = en
        out[l] = n
    return out, fell


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in IGNORE}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def diff(a, b, path=""):
    a, b = strip(a), strip(b)
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            out += diff(a.get(k, MISSING), b.get(k, MISSING), f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}[{i}]")
    elif a is MISSING or b is MISSING or a != b:
        show = lambda x: "<absent>" if x is MISSING else json.dumps(x, ensure_ascii=False)[:120]
        out.append(f"{path or '.'}: {show(a)} → {show(b)}")
    return out


def get(pid, lang):
    return (_client.default().get(f"/products/{int(pid)}", lang=lang) or {}).get("data") or {}


def dump(pid, lang, tag, data):
    path = os.path.join(OUT, f"{pid}-{lang}-{tag}.json")
    if tag == "before" and os.path.exists(path):
        return                  # keep the first live "before" — a re-run must not erase it
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def log(entry):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def done_ids():
    if not os.path.exists(LOG):
        return set()
    out = set()
    for line in open(LOG, encoding="utf-8"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("status") == "ok" and not e.get("dry_run"):
            out.add(e["id"])
    return out


def run_one(pid, brands, dry):
    before = {l: get(pid, l) for l in LANGS}
    if not before["en"]:
        raise PayloadError(f"product {pid} not found")
    brand = brands.get(before["en"].get("brand_id"))
    if not brand:
        raise PayloadError(f"product {pid}: brand {before['en'].get('brand_id')} not found")
    if not dry:
        for l in LANGS:
            dump(pid, l, "before", before[l])
    nm, fell = names(before)
    entry = {"id": pid, "brand": brand, "fallback_en_name": fell, "dry_run": dry,
             "had_meta": bool(before["en"].get("meta")), "old_meta": {l: before[l].get("meta") for l in LANGS},
             "written": [], "skipped": [], "meta": {}}
    en = before["en"]
    for l in LANGS:
        want = target(l, brand, nm[l])
        entry["meta"][l] = want
        if (before[l].get("meta") or {}) == want:
            entry["skipped"].append(l)
            continue
        res = translations.set_meta(pid, l, want, dry_run=dry, en=en,
                                    cur=None if l == "en" else before[l])
        entry["written"].append(l)
        if not dry and l == "en":
            en = res.after          # ru/hy rebuild from the fresh en record
    if dry:
        entry["status"] = "dry-run"
        return entry
    after = {l: get(pid, l) for l in LANGS}
    problems = []
    for l in LANGS:
        dump(pid, l, "after", after[l])
        if (after[l].get("meta") or {}) != entry["meta"][l]:
            problems.append(f"{l} meta reads back as {after[l].get('meta')!r}")
        problems += [f"{l} {d}" for d in diff(before[l], after[l])]
    entry["status"] = "ok" if not problems else "problems"
    entry["problems"] = problems
    return entry


def scan():
    """Read-only: names per locale from the export; meta presence needs a GET per product."""
    recs = {l: _export.records(lang=l) for l in LANGS}
    by = {l: {} for l in LANGS}
    for l in LANGS:
        for r in recs[l]:
            by[l].setdefault(r["product_id"], r)
    miss = {"ru": [], "hy": []}
    for pid, r in by["en"].items():
        for l in ("ru", "hy"):
            n = ((by[l].get(pid) or {}).get("product_name") or "").strip()
            if not n or n == (r.get("product_name") or "").strip():
                miss[l].append((pid, r.get("product_name")))
    print(f"products: {len(by['en'])}")
    for l in ("ru", "hy"):
        print(f"{l} name missing / same as en: {len(miss[l])}")
        for pid, n in miss[l]:
            print(f"   {pid}\t{n}")
    return by["en"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ids", nargs="*", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--scan", action="store_true", help="read-only: missing ru/hy names")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--redo", action="store_true", help="ignore the log's finished ids")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.scan:
        scan()
        return 0
    if a.all:
        ids = sorted({r["product_id"] for r in _export.records(lang="en")})
    else:
        ids = a.ids
    if not ids:
        ap.error("give product ids or --all")
    if not a.redo and not a.dry_run:
        skip = done_ids()
        ids = [i for i in ids if i not in skip]
    if a.limit:
        ids = ids[:a.limit]
    brands = {b["id"]: b["name"] for b in refdata.ids("brands")}
    pause = float(config.load()["product"]["pause_seconds"])
    bad = 0
    for n, pid in enumerate(ids, 1):
        if n > 1 and pause and not a.dry_run:
            _client.default().pacer.pace("product", _client.stderr_log)
        t0 = datetime.datetime.now()
        try:
            e = run_one(pid, brands, a.dry_run)
        except Exception as ex:  # log and go on; the log makes the run resumable
            e = {"id": pid, "status": "error", "error": str(ex), "dry_run": a.dry_run}
        e["at"] = t0.isoformat(timespec="seconds")
        e["seconds"] = round((datetime.datetime.now() - t0).total_seconds(), 1)
        log(e)
        bad += e["status"] not in ("ok", "dry-run")
        line = (f"[{n}/{len(ids)}] {pid} {e['status']}  written={e.get('written')} skipped={e.get('skipped')}"
                f"  fallback={e.get('fallback_en_name')}  {e['seconds']}s")
        print(line, flush=True)
        for p in e.get("problems") or []:
            print(f"     ! {p}")
        if e.get("error"):
            print(f"     ! {e['error']}")
        if a.dry_run:
            for l in LANGS:
                if l in (e.get("meta") or {}):
                    print(f"     {l}: {e['meta'][l]['title']}\n         {e['meta'][l]['description']}")
    print(f"done: {len(ids) - bad} ok, {bad} failed — log {LOG}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
