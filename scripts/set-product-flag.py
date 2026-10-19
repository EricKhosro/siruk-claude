#!/usr/bin/env python3
"""Set one product-level flag: show_unit_price, is_best_seller, is_on_sale or is_discontinued.

    scripts/set-product-flag.py <product-id> <flag> <true|false> [--dry-run]

e.g. `set-product-flag.py 1384 show_unit_price false` hides the per-100 g / per-kg rate on the
storefront (user 2026-10-19: a product selling one stick and a 10-stick pack). The PUT body is built
from a fresh GET by siruk_payload.put_body (every variant re-sent, nothing dropped, CLAUDE.md 10),
and the flag is read back.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from siruk_payload import PayloadError, api, put_body  # noqa: E402

FLAGS = ("show_unit_price", "is_best_seller", "is_on_sale", "is_discontinued")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 3 or args[1] not in FLAGS or args[2] not in ("true", "false"):
    sys.exit(__doc__)
pid, flag, value = args[0], args[1], args[2] == "true"

get = api("GET", f"/products/{pid}")
p = get.get("data", get)
before = p.get(flag)
try:
    body = put_body(p)
except PayloadError as e:
    sys.exit(f"error: {e}")
body[flag] = value
print(f"product {pid} {p.get('name')}: {flag} {before} -> {value}  ({len(body['variants'])} variants re-sent)")
if "--dry-run" in sys.argv:
    sys.exit()
api("PUT", f"/products/{pid}", body)
back = api("GET", f"/products/{pid}")
back = back.get("data", back)
ok = back.get(flag) == value and len(back["variants"]) == len(p["variants"])
print(f"read back: {flag}={back.get(flag)}  variants={len(back['variants'])}  {'OK' if ok else 'MISMATCH'}")
sys.exit(0 if ok else 1)
