#!/usr/bin/env python3
"""Add one or more leaf categories to a live product (never removes one).

    scripts/add-category.py <product-id> <leaf-id> [<leaf-id> …] [--dry-run]

e.g. `add-category.py 1365 107` files the Luna cave under Cat > Supplies > Beds as well as Dog > Beds
(2026-10-19, when the Cat Beds leaf was created). The PUT body is built from a fresh GET by
siruk_payload.put_body (every variant re-sent, CLAUDE.md 10); category_ids is always a superset of
the current list (CLAUDE.md 7: never drop a category an existing product already has), and it is read back.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from siruk_payload import PayloadError, api, put_body  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) < 2 or not all(a.isdigit() for a in args):
    sys.exit(__doc__)
pid, add = args[0], [int(a) for a in args[1:]]

get = api("GET", f"/products/{pid}")
p = get.get("data", get)
cur = [c["id"] if isinstance(c, dict) else int(c) for c in (p.get("categories") or p.get("category_ids") or [])]
new = cur + [c for c in add if c not in cur]
try:
    body = put_body(p)
except PayloadError as e:
    sys.exit(f"error: {e}")
body["category_ids"] = new
print(f"product {pid} {p.get('name')}: categories {cur} -> {new}")
if new == cur or "--dry-run" in sys.argv:
    sys.exit()
api("PUT", f"/products/{pid}", body)
back = api("GET", f"/products/{pid}")
back = back.get("data", back)
got = [c["id"] if isinstance(c, dict) else int(c) for c in (back.get("categories") or back.get("category_ids") or [])]
ok = set(new) <= set(got) and len(back["variants"]) == len(p["variants"])
print(f"read back: categories {got}  variants={len(back['variants'])}  {'OK' if ok else 'MISMATCH'}")
sys.exit(0 if ok else 1)
