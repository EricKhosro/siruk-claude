#!/usr/bin/env python3
"""report.md for the 2026-10-01 production fixes, from the run's state files and the
final snapshot (verify.py). Every list carries siruk.am links."""
import csv, json, os

H = os.path.dirname(os.path.abspath(__file__))
P = {}
for f in os.listdir(os.path.join(H, "snapshot")):
    d = json.load(open(os.path.join(H, "snapshot", f)))
    P[d["id"]] = d
V = {v["id"]: (p, v) for p in P.values() for v in p["variants"]}
SKU = {(p["id"], v["sku"]): v for p in P.values() for v in p["variants"]}
link = lambda p, v: f"https://siruk.am/product/{p['slug']}/dp/{v['id']}/"
plink = lambda p: link(p, next((v for v in p["variants"] if v["is_default"]), p["variants"][0]))
J = lambda f: json.load(open(os.path.join(H, f)))
verify = J("verify.json")
weight, stock, names = J("weight-state.json")["done"], J("stock-state.json")["done"], J("names-state.json")["done"]
L, links = [], []


def row(*c):
    L.append("| " + " | ".join(str(x) for x in c) + " |")


L += ["# Production fixes — 2026-10-01", "",
      "Production (`api.siruk.am`), written through `runs/2026-10-01-fix/*.py` (dry run first, every write read back). "
      f"Final check (`verify.py`, a fresh read of all {verify['products']} products): "
      f"**{len(verify['problems'])} problem(s)** — " + ("; ".join(map(str, verify["problems"])) or "none") + ".", ""]

# 1 weight
n_tw = sum(len(x["added"]) for x in weight.values())
L += ["## 1. Sold by weight", "",
      f"Every bag of a loose-sold product (the register's `Kg` column, `AllAngineProduct-FINAL-2026-09-28.xlsx`) now has its own "
      f"by-weight twin: **{n_tw} twins on {len(weight)} products** — price = the Kg column per kg, 1 kg minimum and step, "
      "10 kg stock, cost = bag cost ÷ bag kg, same texts (en/ru/hy), attributes and photos as the bag. The yesterday's import had "
      "**none** (only the old 1 kg *pack* twins). Royal Canin (`Price Royal Canin Nor _ SIRUK.xlsx`): all 23 dry products already "
      "had a correct by-weight variant — no change.", "",
      "The 61 old 1 kg pack twins can't be deleted or converted (the backend locks any variant with stock history): sku renamed "
      "`<bag>-1KG`, label \"1 kg\", **stock 0** so they can't be bought. They still show as an out-of-stock \"1 kg\" option — "
      "**ask the developers to allow deleting a variant whose only history is its initial stock**.", "",
      "Not done: All Breeds Puppy & Junior **800 g Lamb** (011257) — no Kg price in the sheet (never derived). "
      "Mini Adult 800 g Chicken shares its flavour with the 15 kg Chicken bag; the backend allows one weight variant per "
      "flavour, so the 15 kg twin serves it.", "",
      "| Product | Bag | By-weight variant | Price / kg | Link |", "|---|---|---|---|---|"]
for pid, x in sorted(weight.items(), key=lambda t: int(t[0])):
    p = P[int(pid)]
    for sku in x["added"]:
        v = SKU[(p["id"], sku)]
        row(p["name"], sku[:-3], v["name"], f"{v['price']:,}", link(p, v)); links.append(link(p, v))

# 2 stock
L += ["", "## 2. Stock", "", f"**{len(stock)} variants** set through `/stock/variants` (reason *correction*, note says why): "
      "every pack variant 10, every by-weight variant 10 kg, the retired 1 kg twins 0. 123 of them were at 1, "
      "64 held real counts above 10 (lowered on your instruction), 7 toys were at 0. Plan with before/after: `stock-plan.json`.", ""]

# 3 names
L += ["## 3. Product names without the pack size", "",
      f"**{len(names)} products** renamed in en, ru and hy; slugs (URLs) unchanged. Stripping the size made three Acana pairs "
      "and the Trixie dental sets identical — they are **cat vs dog** products, not mis-split sizes, so the species went into "
      "the name instead (\"… Cat\" / \"… Dog\", \"for Cats\" / \"for Dogs\"). Accessory dimensions (cm, l/ø) and dose bands stay.", "",
      "| id | Before (en) | After (en) | Link |", "|---|---|---|---|"]
for pid, r in sorted(names.items(), key=lambda t: int(t[0])):
    p = P[int(pid)]
    row(pid, r["en"][0], r["en"][1], plink(p)); links.append(plink(p))

# 4 merge
p = P[1102]
L += ["", "## 4. Merge", "", "Gemon *Adult Dog Paté* 400 g cans (product 678) folded into the 150 g trays (1102) — one product, "
      "5 variants (tray / can × flavour); 678 is discontinued (hidden) with stock 0, its skus suffixed `-OLD`. "
      f"{plink(p)}", ""]
links.append(plink(p))

# 5 images
L += ["## 5. Photos per pack size", "",
      "Every sized variant was looked at on contact sheets (all images of the 46 multi-size products, the first image of the "
      "481 other sized variants). Replacements are keyed to our EAN / article and were checked by eye before upload; the "
      "bag's by-weight twin got the same gallery.", "",
      "| Product | Variant | What was wrong | Now | Link |", "|---|---|---|---|---|"]
work = {x["variant"]: x for x in J("image-worklist.json")}
for g in ("B", "C", "A"):
    for it in J(f"upload-{g}.json"):
        pv = V.get(it["variant"])
        if not pv:
            continue
        p, v = pv
        why = "; ".join(i.split(":")[0] for i in work.get(it["variant"], {}).get("issues", [])) or "hafo / size"
        row(p["name"], v["size_label"] or v["name"], why, f"{len(v['images'])} image(s), first = new", link(p, v)); links.append(link(p, v))
for pid, by in J("plan-rc-reorder.json").items():
    p = P[int(pid)]
    for sku in by:
        v = SKU[(p["id"], sku)]
        row(p["name"], v["size_label"], "12-pack showed the single pouch", "the 12-pack box shot moved first", link(p, v)); links.append(link(p, v))

# 6 still on hafo
rows = list(csv.DictReader(open(os.path.join(H, "hafo-images.csv"))))
L += ["", "## 6. Still showing a hafo photo (after all of the above)", "",
      f"**{len(rows)} variants.** The Google / Google Lens step could not run in this session (the Claude Chrome extension "
      "was not connected and the devtools browser profile was held by another window) — it is the next thing to run on these.", "",
      "| Product | Variant | sku | hafo at | Only hafo? | Searched, nothing usable | Link |", "|---|---|---|---|---|---|---|"]
tried = {}
for g in "ABC":
    for r in J(f"cand/{g}/result.json"):
        if r.get("status") == "not_found":
            tried[r["variant"]] = (r.get("notes") or r.get("evidence") or "EAN web search")[:90]
held = {1685: "held: barcode page shows the retail bag, hafo the Breeders bag — PM to say which we sell",
        1689: "held: same as Kitten 10 kg"}
for r in rows:
    vid = int(r["variant_id"])
    note = held.get(vid) or tried.get(vid, "")
    if r["sku"].endswith("-KG"):
        note = "by-weight twin — follows its bag"
    row(r["product"], r["variant"], r["sku"], r["hafo_positions"], "yes" if r["only_hafo"] == "True" else "no",
        note, r["siruk_link"]); links.append(r["siruk_link"])

# 7 questions
L += ["", "## 7. For the PM", "",
      "- **Gemon names vs cans** (the photos match the barcodes, the names don't): 679 *Medium Adult Dog Chunks Veal & Liver* — "
      "the can is Beef & Liver (Manzo e Fegato); 683 *Medium Adult Dog Paté* 1.25 kg — the cans are chunks (Bocconi); 681 "
      "*Mini Adult Dog Chunks Chicken* — Monge's can says Adult Medium, shops list the barcode as Mini. Rename?",
      "- **Monge Best for Breeders 10 kg cat bags** (1685 Kitten, 1689 Adult): retail bag or Breeders bag — which do we sell?",
      "- **Litter Tray with Mesh 03623K**: its EAN prefix 4605350 is Kaskad's, not Inteko's — check the brand.",
      "- **Simba Chunks 1230 g**: the photos found are the right can size but the older label; Wild Game 1230 g still shows the 415 g can.",
      "- **Monge 800 g bags** (761 All Breeds Puppy Lamb, 763 Extra Small Adult Lamb): the photo shows a bigger bag; no 800 g photo found.",
      "- **Simba Adult Dog Kibbles 20 kg**: only the 4 kg bag photo exists anywhere we can reach.",
      "- **Royal Canin Mother & Babycat 12 × 195 g**: no 12-pack photo exists (the sku is the single-can EAN).",
      "- **Travel Bottle with Bowl, 500 ml** (852): capacity in the name of an accessory without a size label — keep?",
      "- Developers: allow deleting the 61 retired `-1KG` variants (stock history = initial stock only).", ""]

# 8 links
seen, uniq = set(), []
for u in links:
    if u not in seen:
        seen.add(u); uniq.append(u)
L += ["## 8. siruk.am links (every product/variant touched or still open, in report order)", ""] + [f"- {u}" for u in uniq]
open(os.path.join(H, "report.md"), "w").write("\n".join(L) + "\n")
print(len(L), "lines,", len(uniq), "links")
