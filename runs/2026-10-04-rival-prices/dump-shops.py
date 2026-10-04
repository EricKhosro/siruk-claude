#!/usr/bin/env python3
"""Read-only: fresh brand catalogues from zoovet.am and nemo.am for every brand we sell -> shops.json.
Uses the parsers in scripts/zoovet-lookup.py and scripts/nemo-lookup.py; pages until no new card."""
import importlib.util, json, os, sys, time, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
def load(name, fn):
    s = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "scripts", fn))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
zv, nm = load("zv", "zoovet-lookup.py"), load("nm", "nemo-lookup.py")

ZOOVET = ["8in1", "acana", "beaphar", "club4paws", "gemon", "lechat", "monge", "orijen", "royal-canin",
          "simba", "trixie", "iv-san-bernard", "pchelodar", "dogman", "mr-fresh", "flexi", "schesir",
          "versele-laga", "eco-premium", "inspector"]
ZOOVET_RU = ["Гав!", "Деревенские лакомства", "Каскад", "Мнямс", "Мяу", "Гельминтал", "Секс Контроль",
             "КонтрСекс", "Барс", "Хочу еще!"]
NEMO = ["royal-canin", "monge-2", "gemon", "trixie", "orijen", "club4-paws", "beaphar-2", "special-dog",
        "bwild-2", "мяу-2", "деревенские-лакомства", "8in1", "мнямс", "lechat-2", "kormell-2", "acana",
        "iv-san-bernard", "pchelodar", "eco-premium", "versele-laga", "simba-կենդանիների-կերեր-և-պարագաներ"]

def fetch(f, url):
    for i in range(4):
        try: return f(url)
        except Exception as e:
            print("retry", url, e, file=sys.stderr); time.sleep(3 * (i + 1))
    return ""

out = {"zoovet": {}, "nemo": {}}
zb = zv.brands()
for name in ZOOVET_RU:
    if name in zb: ZOOVET.append(zb[name].rsplit("/", 1)[1])
    else: print("zoovet brand missing", name, file=sys.stderr)
for slug in ZOOVET:
    rows, page = [], 1
    while page <= 60:
        html = fetch(zv.fetch, "%s/%s?limit=100&page=%d" % (zv.SITE, slug, page))
        new = [r for r in zv.parse_list(html) if r["url"] not in {o["url"] for o in rows}]
        if not new: break
        rows += new; page += 1; time.sleep(0.5)
    out["zoovet"][urllib.parse.unquote(slug)] = rows
    print("zoovet", urllib.parse.unquote(slug), len(rows), file=sys.stderr, flush=True)
for slug in NEMO:
    rows, page = [], 1
    while page <= 80:
        u = nm.SITE + "/" + urllib.parse.quote(slug) + "?pagesize=100" + (("&pagenumber=%d" % page) if page > 1 else "")
        new = [r for r in nm.parse_list(fetch(nm.fetch, u)) if r["url"] not in {o["url"] for o in rows}]
        if not new: break
        rows += new; page += 1; time.sleep(0.5)
    out["nemo"][slug] = rows
    print("nemo", slug, len(rows), file=sys.stderr, flush=True)
json.dump(out, open(os.path.join(HERE, "shops.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print({k: sum(len(v) for v in d.values()) for k, d in out.items()})
