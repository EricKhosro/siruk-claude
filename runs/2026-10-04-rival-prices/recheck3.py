#!/usr/bin/env python3
"""Read-only re-check of the zoovet / nemo prices the final CSV uses -> recheck3.json.
  every nemo price from agent-results.json, -2 and -3 (with nemo's struck-through old price), and every zoovet
  price from agent-results3.json (pass 1 and 2 zoovet prices were re-fetched live earlier on 2026-10-04).

  nemo    the page is re-fetched live (rival.py nemo-page); ok when our price is the page's price.
  zoovet  the page is re-fetched live (rival.py zoovet-page) when zoovet answers; ok when our price is the
          page price or one of its option prices. zoovet refused connections from this machine late on
          2026-10-04, so when the page can't be fetched the price is compared with today's saved zoovet
          list (shops.json, same URL): "saved-list" when it equals the listing price, "unconfirmed" when the
          listing price differs (e.g. a per-kg option, which the saved list does not carry).
Prints every mismatch."""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
def load(n):
    return {r["variant_id"]: r["final"] for r in json.load(open(os.path.join(HERE, n), encoding="utf-8"))}


A1, A2, A3 = load("agent-results.json"), load("agent-results2.json"), load("agent-results3.json")
SAVED = {}
for rows in json.load(open(os.path.join(HERE, "shops.json"), encoding="utf-8"))["zoovet"].values():
    for r in rows:
        SAVED[r["url"]] = r


def page(shop, url, tries):
    for i in range(tries):
        out = subprocess.run([sys.executable, "rival.py", f"{shop}-page", url], capture_output=True, text=True,
                             encoding="utf-8", cwd=HERE, timeout=120).stdout
        try:
            return json.loads(out)
        except Exception:
            time.sleep(2)
    return None


def zoovet_up():
    import urllib.request
    try:
        urllib.request.urlopen(urllib.request.Request("https://zoovet.am/", headers={"User-Agent": "Mozilla/5.0"}), timeout=15)
        return True
    except Exception:
        return False


ZOOVET_UP = zoovet_up()
print("zoovet reachable:", ZOOVET_UP)


def chk(job):
    vid, shop, s = job
    p = page(shop, s["url"], 3) if shop == "nemo" or ZOOVET_UP else None
    if p:
        prices = {p.get("price"), p.get("price_new")} | {o[1] for o in p.get("options", [])}
        return {"variant_id": vid, "shop": shop, "url": s["url"], "price": s["price"],
                "status": "live-ok" if s["price"] in prices else "live-MISMATCH",
                "page_prices": sorted(x for x in prices if x), "page_name": p.get("name"),
                "old_price": p.get("old_price"), "in_stock": (p.get("stock") or "").lower() == "in stock" if shop == "nemo" else None}
    if shop == "zoovet" and s["url"] in SAVED:
        lp = SAVED[s["url"]]["price"]
        return {"variant_id": vid, "shop": shop, "url": s["url"], "price": s["price"],
                "status": "saved-list" if lp == s["price"] else "unconfirmed", "page_prices": [lp],
                "page_name": SAVED[s["url"]]["name"]}
    return {"variant_id": vid, "shop": shop, "url": s["url"], "price": s["price"], "status": "unconfirmed",
            "page_prices": [], "page_name": None}


jobs = {}
for src, shops in ((A1, ("nemo",)), (A2, ("nemo",)), (A3, ("zoovet", "nemo"))):
    for vid, f in src.items():
        for s in shops:
            x = f.get(s) or {}
            if x.get("found") and x.get("url") and x.get("price") is not None:
                jobs[(vid, s)] = (vid, s, x)          # a later pass overrides an earlier one, as in build-final.py
jobs = list(jobs.values())
with ThreadPoolExecutor(3) as ex:
    res = list(ex.map(chk, jobs))
json.dump(res, open(os.path.join(HERE, "recheck3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print(len(res), "prices re-checked:", Counter((r["shop"], r["status"]) for r in res))
for r in res:
    if r["status"] not in ("live-ok", "saved-list"):
        print(r)
