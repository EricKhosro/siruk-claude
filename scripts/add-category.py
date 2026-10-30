#!/usr/bin/env python3
"""Add one or more leaf categories to a live product; remove one only with --remove.

    scripts/add-category.py <product-id> <leaf-id> [<leaf-id> …] [--remove <leaf-id>] [--dry-run]

e.g. `add-category.py 1365 107` files the Luna cave under Cat > Supplies > Beds as well as Dog > Beds
(2026-10-19, when the Cat Beds leaf was created). The PUT body is built from a fresh GET by
siruk_payload.put_body (every variant re-sent, CLAUDE.md 10); without --remove category_ids is always a
superset of the current list (CLAUDE.md 7: never drop a category an existing product already has), and it
is read back.

--remove <leaf-id> drops a category that is wrong — only on the user's explicit say-so (2026-10-27: three
cat-only Trixie bowls filed under Dog > Bowls & Feeders, `add-category.py 798 <cat-bowls> --remove 70`).
The product must keep at least one category.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from siruk_payload import PayloadError, api, put_body  # noqa: E402

argv = sys.argv[1:]
remove = []
if "--remove" in argv:
    i = argv.index("--remove")
    if i + 1 >= len(argv) or not argv[i + 1].isdigit():
        sys.exit(__doc__)
    remove = [int(argv[i + 1])]
    del argv[i:i + 2]
args = [a for a in argv if not a.startswith("--")]
if len(args) < 2 or not all(a.isdigit() for a in args):
    sys.exit(__doc__)
pid, add = args[0], [int(a) for a in args[1:]]

get = api("GET", f"/products/{pid}")
p = get.get("data", get)
cur = [c["id"] if isinstance(c, dict) else int(c) for c in (p.get("categories") or p.get("category_ids") or [])]
new = [c for c in cur if c not in remove] + [c for c in add if c not in cur and c not in remove]
if not new:
    sys.exit(f"error: product {pid} would be left with no category")
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
ok = set(got) == set(new) and len(back["variants"]) == len(p["variants"])
print(f"read back: categories {got}  variants={len(back['variants'])}  {'OK' if ok else 'MISMATCH'}")
sys.exit(0 if ok else 1)
