#!/usr/bin/env python3
"""Create many NEW products in one call: POST /api/admin/products/bulk.

    scripts/bulk-create.py <payload.json>… [--dry-run] [--en-only] [--out results.json]

The logic lives in siruk/bulk.py since 2026-10-26 (also: `siruk bulk-create`, and
the MCP tool bulk_create_products); its docstring has what the endpoint does.

Payload files are create-product.sh payloads (shape: siruk/payload.py). The
translations go either inline (name / variant texts as {en, ru, hy}) or as a
"translations" block in set-translation.py's file shape:
  "translations": {"ru": {"name": "…", "variants": {"<sku>": {"about_this_item": "…"}}},
                   "hy": {…}}
A product missing its ru or hy name is refused unless --en-only (then translate after
with set-translation.py). Guards: ALLOW_BELOW_COST=1, ALLOW_NO_IMAGE=1, FORCE=1 (skip the
similar-name check), as before. Created products are read back, then the translation
audit runs on them (CLAUDE.md 13 — report from that, not from what was sent).
Results (file → status, id, slug, errors) go to --out, default .siruk-cache/bulk-<time>.json.
Exit 1 if any item failed or was refused.
"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from siruk import bulk, verify  # noqa: E402
from siruk.config import CACHE  # noqa: E402


def main(argv):
    out = argv[argv.index("--out") + 1] if "--out" in argv else \
        os.path.join(CACHE, time.strftime("bulk-%Y%m%d-%H%M%S.json"))
    files = [a for a in argv if not a.startswith("--") and a != out]
    dry, en_only = "--dry-run" in argv, "--en-only" in argv
    if not files:
        sys.exit(__doc__)
    items = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                items.append((f, json.load(fh)))
        except (OSError, ValueError) as e:
            items.append((f, {"_unreadable": str(e)}))
    log = lambda m: print(m, file=sys.stderr if m.startswith(("✗", "⚠")) else sys.stdout)
    results = bulk.create(items, dry_run=dry, en_only=en_only, log=log)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if dry:
        ready = {f: r["body"] for f, r in results.items() if r["status"] == "ready"}
        refused = len(results) - len(ready)
        print(f"\ndry run: {len(ready)} ready, {refused} refused — nothing sent")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(ready, fh, ensure_ascii=False, indent=1)
        print(f"bodies → {out}")
        sys.exit(1 if refused else 0)
    for r in results.values():
        r.pop("body", None)
        if r["status"] == "created":
            print(f"  product {r['id']}  {r['slug']}  " + ("read-back ok" if r["read_back"] == "ok"
                                                           else "⚠ " + "; ".join(r["read_back"])))
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    print(f"results → {out}")
    ids = [r["id"] for r in results.values() if r["status"] == "created"]
    if ids:
        print("\n# translations (CLAUDE.md 13 — report from this, not from what was sent):")
        os.environ["SIRUK_NO_PACE"] = "1"
        verify.print_report(verify.translations(only=ids))
    sys.exit(0 if bulk.ok(results) else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
