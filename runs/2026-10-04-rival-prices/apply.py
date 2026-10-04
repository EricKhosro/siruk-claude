#!/usr/bin/env python3
"""Set the planned prices on PRODUCTION (plan.json, built from siruk-vs-rivals-final.csv).
User instruction 2026-10-04 evening: every variant whose price differs from the highest rival (hafo / zoovet / nemo)
gets that price, 543 variants; Bony Mix 1.8 kg (variant 454) held back for the user.

    apply.py              # dry run: GET + checks + backup, builds every body, writes nothing
    apply.py --write      # PUT each product once, then read it back
    apply.py --write --only 1229,1230

Per product: fresh GET (backup/<pid>.json) -> every planned variant must still be at the price read on
2026-10-04 (else skipped: someone changed it) -> new price > cost_price and a multiple of 10 ->
body from scripts/siruk_payload.py put_body (product type checked) with only `price` changed ->
PUT -> GET again: planned variants at the new price, every other variant's price unchanged.
Resumable: apply-state.json records finished products. Uses .siruk-token-prod.
"""
import json, os, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.update(SIRUK_API="https://api.siruk.am/api/admin",
                  SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import siruk_payload  # noqa: E402
from siruk_payload import PayloadError, put_body  # noqa: E402
import urllib.error, urllib.request  # noqa: E402

TOKEN = open(os.environ["SIRUK_TOKEN_FILE"], encoding="utf-8").read().strip()


def api(method, path, payload=None, lang=None):
    """scripts/api.sh's request (same headers) in Python: this shell has no jq, which api.sh needs."""
    h = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json", "User-Agent": "curl/8.5.0"}
    data = None
    if payload is not None:
        h["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if lang:
        h["Content-Language"] = lang
    for attempt in range(4):
        try:
            req = urllib.request.Request(os.environ["SIRUK_API"] + path, data=data, headers=h, method=method)
            return json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in (429, 502, 503, 504) and attempt < 3:
                time.sleep(3 * (attempt + 1)); continue
            raise PayloadError(f"api {method} {path} -> HTTP {e.code}: {body[:300]}")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 3:
                time.sleep(3 * (attempt + 1)); continue
            raise PayloadError(f"api {method} {path} failed: {e}")


siruk_payload.api = api          # put_body's product-type lookups go through the same client

WRITE = "--write" in sys.argv
PRICE_ONLY = "--price-only" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
PLAN = sys.argv[sys.argv.index("--plan") + 1] if "--plan" in sys.argv else "plan.json"   # e.g. plan-bony.json
SF = os.path.join(HERE, PLAN.replace("plan", "apply-state", 1) if PLAN != "plan.json" else "apply-state.json")
state = json.load(open(SF, encoding="utf-8")) if os.path.exists(SF) else {"done": {}, "skipped": {}}
os.makedirs(os.path.join(HERE, "backup"), exist_ok=True)

plan = json.load(open(os.path.join(HERE, PLAN), encoding="utf-8"))
by_pid = defaultdict(list)
for r in plan:
    by_pid[str(r["product_id"])].append(r)


def save():
    json.dump(state, open(SF, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


ok = skipped = 0
for pid, changes in sorted(by_pid.items(), key=lambda t: int(t[0])):
    if (ONLY and pid not in ONLY) or pid in state["done"]:
        continue
    g = api("GET", f"/products/{pid}").get("data")
    if not g:
        state["skipped"][pid] = "GET failed"; skipped += 1; save(); continue
    json.dump(g, open(os.path.join(HERE, "backup", f"{pid}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    vs = {v["sku"]: v for v in g["variants"]}
    problems = []
    for c in changes:
        v = vs.get(c["sku"])
        new = int(c["new price"])
        if v is None:
            problems.append(f"{c['sku']}: variant gone")
        elif int(float(v["price"])) != int(c["current price"]):
            problems.append(f"{c['sku']}: price is now {v['price']}, planned from {c['current price']}")
        elif v.get("cost_price") is not None and new <= float(v["cost_price"]):
            problems.append(f"{c['sku']}: new {new} <= cost {v['cost_price']}")
        elif new % 10:
            problems.append(f"{c['sku']}: {new} not a multiple of 10")
    if problems:
        state["skipped"][pid] = problems; skipped += 1; save()
        print(f"{pid}: SKIPPED {problems}"); continue
    try:
        if PRICE_ONLY:
            # --price-only: nothing but `price` changes, so no variant counts as touched; gaps already in the
            # product (a sized type's variant with no content, an option missing on some variants) stay
            # warnings, not refusals. Every other check still runs, and the read-back below still verifies.
            body = put_body(g)
        else:
            body = put_body(g, patch_sku=changes[0]["sku"], patch={"price": int(changes[0]["new price"])})
    except PayloadError as e:
        state["skipped"][pid] = f"refused: {e}"; skipped += 1; save()
        print(f"{pid}: REFUSED {e}"); continue
    want = {c["sku"]: int(c["new price"]) for c in changes}
    for bv in body["variants"]:
        if bv["sku"] in want:
            bv["price"] = want[bv["sku"]]
    if len(body["variants"]) != len(g["variants"]):
        state["skipped"][pid] = "variant count changed in body"; skipped += 1; save(); continue
    desc = ", ".join(f"{c['sku']} {c['current price']}->{c['new price']}" for c in changes)
    if not WRITE:
        print(f"{pid}: dry-run ok  {desc}"); ok += 1; continue
    api("PUT", f"/products/{pid}", body)
    time.sleep(0.6)
    after = {v["sku"]: v for v in (api("GET", f"/products/{pid}").get("data") or {}).get("variants", [])}
    bad = [s for s, p in want.items() if s not in after or int(float(after[s]["price"])) != p]
    bad += [s for s, v in vs.items() if s not in want and (s not in after or float(after[s]["price"]) != float(v["price"]))]
    if bad:
        state["skipped"][pid] = f"READ-BACK MISMATCH {bad}"; skipped += 1; save()
        print(f"{pid}: READ-BACK MISMATCH {bad}"); continue
    state["done"][pid] = desc; ok += 1; save()
    print(f"{pid}: written + verified  {desc}")
    time.sleep(0.6)
print(f"{'written' if WRITE else 'dry-run ok'}: {ok} products; skipped: {skipped}; variants planned: {len(plan)}")
