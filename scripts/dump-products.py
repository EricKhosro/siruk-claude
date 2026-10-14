#!/usr/bin/env python3
"""Save every live product's full admin GET (en) — the raw input for read-only audits.

    scripts/dump-products.py              # -> .siruk-cache/live/products/<id>.json (+ index.json)
    scripts/dump-products.py --refresh    # re-read products already saved
    scripts/dump-products.py --ids 12 13  # re-read just these (a 404 removes the file)
    scripts/dump-products.py --lang ru    # the ru texts → .siruk-cache/live/products-ru/ (same for hy)
    … --fast                              # no pacing (sequential, one call at a time), as verify-translations.py does

Resumable: a product already on disk is skipped unless --refresh. Paced by api.sh
(config.json), so a full pass of ~950 products takes a while — run it in the
background. Read-only: GET only.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, ".siruk-cache", "live", "products")
ENV = dict(os.environ)


def get(path):
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path],
                       capture_output=True, text=True, cwd=ROOT, timeout=180, env=ENV)
    i = r.stdout.find("{")
    if i < 0:
        return None, r.stderr.strip()[-200:]
    return json.loads(r.stdout[i:]), r.stderr


def all_ids():
    ids, page = [], 1
    while True:
        d, _ = get(f"/products?page={page}")
        ids += [p["id"] for p in (d or {}).get("data") or []]
        if not d or page >= d["meta"]["last_page"]:
            return ids
        page += 1


def main(argv):
    global OUT
    if "--lang" in argv:
        lang = argv[argv.index("--lang") + 1]
        if lang != "en":
            ENV["SIRUK_LANG"] = lang
            OUT = OUT + "-" + lang
        argv = [a for i, a in enumerate(argv) if a != "--lang" and (i == 0 or argv[i - 1] != "--lang")]
    if "--fast" in argv:
        ENV["SIRUK_NO_PACE"] = "1"
    os.makedirs(OUT, exist_ok=True)
    refresh = "--refresh" in argv
    ids = [int(a) for a in argv[argv.index("--ids") + 1:]] if "--ids" in argv else all_ids()
    if "--ids" not in argv:
        json.dump(ids, open(os.path.join(OUT, "index.json"), "w"))
        for f in os.listdir(OUT):          # products deleted since the last pass
            if f[:-5].isdigit() and int(f[:-5]) not in set(ids):
                os.remove(os.path.join(OUT, f))
    todo = [i for i in ids if refresh or "--ids" in argv or not os.path.exists(os.path.join(OUT, f"{i}.json"))]
    print(f"{len(ids)} products, {len(todo)} to fetch", file=sys.stderr)
    for n, pid in enumerate(todo, 1):
        d, err = get(f"/products/{pid}")
        path = os.path.join(OUT, f"{pid}.json")
        if d and d.get("data"):
            json.dump(d["data"], open(path, "w"), ensure_ascii=False)
        elif "404" in (err or ""):
            if os.path.exists(path):
                os.remove(path)
        else:
            print(f"  {pid}: failed {err}", file=sys.stderr)
        if n % 50 == 0:
            print(f"  {n}/{len(todo)}", file=sys.stderr)
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
