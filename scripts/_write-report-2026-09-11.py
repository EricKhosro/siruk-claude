#!/usr/bin/env python3
"""Assemble runs/2026-09-11/report.md from the three plans, their import state files,
the run CSVs and the post-import check outputs (whatever of those exists yet)."""
import collections, csv, glob, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
RUN = os.path.join(ROOT, "runs", sys.argv[1] if len(sys.argv) > 1 else "2026-09-11")
PLANS = [("Trixie", "trixie-plan.json"), ("Monge group", "monge-plan.json"), ("Small brands", "small-plan.json")]

cats = {int(k): v for k, v in json.load(open(os.path.join(CACHE, "categories-flat.json"))).items()}
AV = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
label_of = {}
for code, a in AV.items():
    for lab, vid in a["values"].items():
        label_of[(code, vid)] = lab
todo = {r["Article Code"]: r for r in json.load(open(os.path.join(CACHE, "todo-rows.json")))}
brands = dict(l.split("\t", 1) for l in """1\tAcana
2\tBelcando
3\tBrit
4\tCanvit
5\tMonge
6\tOrijen
7\tRoyal Canin
8\tTrixie
9\tFarmina
10\tSchesir
11\tLeonardo
12\tStuzzy
13\tBewi Dog
14\tBewi Cat
15\tDogland
16\tOk-Lock
17\tClub 4 Paws
18\tGemon
19\tSimba
20\tLechat
21\tSpecial Dog
22\tRolf Club
23\tInspector
24\tGelmintal
25\tInsectal
26\tCliny
27\tMr. Fresh
28\tComfy
29\tIv San Bernard
30\tBeaphar""".splitlines())
brands = {int(k): v for k, v in brands.items()}


def esc(s):
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ")


def ev_text(v, p):
    """Attribute → label (evidence). Planners that hand-map a page record no quote; say where the value came from."""
    out = []
    ev = v.get("_ev") or {}
    for code, vid in (v.get("attribute_value_ids") or {}).items():
        lab = label_of.get((code, vid), f"#{vid}")
        q = ev.get(code)
        if not q:
            if code in ("product-weight", "toy-size", "color-family"):
                q = f"label '{v['name']}'" if v.get("name") else f"name '{p['name']}'"
            elif code in ("flavor",):
                q = f"name '{p['name']}' / label '{v.get('name', '')}'"
            elif code == "ingredient":
                q = "composition on the brand page (first named meat)"
            else:
                q = "brand product page (hand-mapped)"
        out.append(f"{code}={lab} ({q})")
    return "; ".join(out) if out else "—"


def load(name):
    try:
        return json.load(open(os.path.join(CACHE, name)))
    except FileNotFoundError:
        return {}


def read_csv(name):
    p = os.path.join(RUN, name)
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


def read_txt(name):
    p = os.path.join(RUN, name)
    return open(p).read().strip() if os.path.exists(p) else ""


L = []
w = L.append
w(f"# 2026-09-11 — full import of `csv/products.csv` (everything not yet live)\n")
w("Request: *import every product from csv/products.csv if it's not already added*.\n")

# ------------------------------------------------------------------ summary
tot_rows = 1096; todo_n = len(todo)
plan_stats = []
all_ids = []
per_plan_rows = {}
for title, fn in PLANS:
    plan = load(fn); state = load(fn.replace(".json", ".state.json"))
    done = state.get("done", {}); failed = state.get("failed", {})
    prods = plan.get("products", [])
    n_var = sum(len(p["variants"]) for p in prods)
    n_done = sum(1 for p in prods if p["slug"] in done)
    n_fail = sum(1 for p in prods if p["slug"] in failed)
    ids = [done[p["slug"]]["id"] for p in prods if p["slug"] in done]
    all_ids += ids
    no_img = [(p["name"], v["sku"]) for p in prods for v in p["variants"] if not v.get("images")]
    plan_stats.append((title, len(prods), n_var, n_done, n_fail, len(prods) - n_done - n_fail, len(plan.get("unpriced", [])), len(plan.get("notfound", [])),
                       len(plan.get("blocked_no_category", [])) + len(plan.get("blocked_rows", [])), len(no_img)))
    per_plan_rows[title] = (plan, done, failed, no_img)

w("## Summary\n")
w("| | Rows |\n|---|---|")
w(f"| CSV rows | {tot_rows} |")
w(f"| Already live before this run (SKU match in the demo) | {tot_rows - todo_n} |")
w(f"| Rows to import | {todo_n} |")
w("")
w("| Plan | Products planned | Variants | Products created | Failed | Pending | Rows without hafo price | Rows not found | Rows blocked (no category) | Variants without image |")
w("|---|---|---|---|---|---|---|---|---|---|")
for s in plan_stats:
    w("| " + " | ".join(str(x) for x in s) + " |")
w(f"| **Total** | {sum(s[1] for s in plan_stats)} | {sum(s[2] for s in plan_stats)} | {sum(s[3] for s in plan_stats)} | {sum(s[4] for s in plan_stats)} | {sum(s[5] for s in plan_stats)} | {sum(s[6] for s in plan_stats)} | {sum(s[7] for s in plan_stats)} | {sum(s[8] for s in plan_stats)} | {sum(s[9] for s in plan_stats)} |")
w("")
w("Every created variant carries **cost = CSV buy price** and **sale price = the hafo.am row for its own article code** "
  "(`price_source: variant`, `wholesale_price == cost`); the one sibling-priced row is in `sibling-priced.csv`. "
  "Stock: the CSV quantity, 10 where the invoice says 1 (placeholder rule). Everything else that could not be settled "
  "by the rules is in the CSVs below — nothing was invented.\n")
w("One row was skipped on purpose: 40261Tx (Trixie granulate litter 5 l) is already live as SKU 4026.\n")

# ------------------------------------------------------------------ per product
w("## Products created (one line per variant: CSV → hafo → source → admin)\n")
w("Columns: admin id · product (slug) · variant label [article code] · invoice name · cost → sale (AMD) · category · source page · attributes (evidence).\n")
for title, fn in PLANS:
    plan, done, failed, no_img = per_plan_rows[title]
    w(f"### {title}\n")
    w("| id | Product | Variant [code] | Invoice name | Cost → Sale | Category | Source | Attributes (evidence) |")
    w("|---|---|---|---|---|---|---|---|")
    for p in sorted(plan.get("products", []), key=lambda p: (done.get(p["slug"], {}).get("id") or 10**6, p["name"])):
        st = done.get(p["slug"])
        pid = st["id"] if st else ("FAILED" if p["slug"] in failed else "pending")
        catn = ", ".join(cats.get(c, str(c)) for c in p["category_ids"])
        src = p.get("source", "")
        src_md = f"[page]({src})" if src.startswith("http") else esc(src)
        for v in p["variants"]:
            code = v.get("_code", v["sku"])
            price = v.get("price") if v.get("pricing_type", "fixed") == "fixed" else f"{v.get('price_per_kg')}/kg × {v.get('weight')}"
            sib = f" (sibling {v['_sibling']})" if v.get("_sibling") else ""
            noimg = " **no image**" if not v.get("images") else ""
            w(f"| {pid} | {esc(p['name'])} (`{p['slug']}`) | {esc(v['name'])} [{code}]{noimg} | {esc(v.get('_inv') or todo.get(code, {}).get('Product Name (as printed)', ''))} | {v.get('cost_price')} → {price}{sib} | {esc(catn)} | {src_md} | {esc(ev_text(v, p))} |")
    w("")

# ------------------------------------------------------------------ failed
fails = [(t, s, per_plan_rows[t][2][s]) for t, _ in PLANS for s in per_plan_rows[t][2]]
if fails:
    w("### Failed creations (left in the state files; re-running the plan retries them)\n")
    for t, s, e in fails:
        w(f"- {t}: `{s}` — {esc(json.dumps(e)[:300])}")
    w("")

# ------------------------------------------------------------------ pricing outputs
unp = read_csv("no-hafo-price.csv"); nf = read_csv("not-found.csv"); sib = read_csv("sibling-priced.csv")
blocked = read_csv("blocked-no-category.csv"); packshot = read_csv("needs-packshot.csv")
w("## Rows not imported\n")
w(f"### No hafo sale price — `runs/2026-09-11/no-hafo-price.csv` ({len(unp)} rows)\n")
w("Fill `Sale Price (AMD)` and re-import; the row keeps its cost. Reasons:\n")
c = collections.Counter((r["Brand"], re.sub(r"\(.*", "", r["Why no price"]).strip()) for r in unp)
w("| Brand | Why no price | Rows |\n|---|---|---|")
for (b, why), n in sorted(c.items(), key=lambda x: (-x[1], x[0])):
    w(f"| {esc(b)} | {esc(why)} | {n} |")
w("\n**The CSV's `Product Name (as printed)` column is offset for part of the 427xx cat-treat block.** For nine of those "
  "articles the printed name describes a different treat than the article does — e.g. 42746 is printed as *salmon & menthol 50 g* "
  "while both trixie.de and hafo's own row for 42746 say *Premio Strips with Tuna & Whitefish, 20 g*. Identity came from the "
  "article code, as the rules require, so the products are right and only that column is unreliable.\n")
w("\n`wrong row` = hafo lists the code but its row's wholesale price is not our cost (hafo's listing is for another size/lot); "
  "`not on hafo` = no listing for the code; `on hafo, size missing` = the listing exists but has no row for our code. "
  "Trixie's `not on hafo` rows are articles hafo does not list at all (many are also the pageless ones); the proposed names are the invoice names where no trixie.de page exists.\n")
w(f"### Not identified — `runs/2026-09-11/not-found.csv` ({len(nf)} rows)\n")
w("| Brand | Rows | Why |\n|---|---|---|")
byb = collections.defaultdict(list)
for r in nf:
    byb[r["Brand"]].append(r)
for b, rs in sorted(byb.items(), key=lambda x: -len(x[1])):
    notes = collections.Counter(re.sub(r"\s+", " ", r["Note"])[:160] for r in rs)
    w(f"| {esc(b) or '(none)'} | {len(rs)} | {esc('; '.join(f'{k} ×{n}' if n > 1 else k for k, n in notes.most_common(3)))} |")
w("\nThese brands have no official site or product page I could reach (Мяу, Kormell, Moor, Justin, Интеко, Dogman, Pchelodar/Api-San, the Iv San Bernard DIY perfumes, "
  "and the Trixie-tagged codes that are not Trixie articles). Identity was not confirmable from the article code, so nothing was created.\n")
w(f"### Blocked: no product category — `runs/2026-09-11/blocked-no-category.csv` ({len(blocked)} rows)\n")
w("Category 13 *Accessories* is not a product category on this backend (it is absent from `/categories?forProducts=true`; a POST with it returns 422). "
  "These rows are fully prepared (identity, hafo price, name, images) and import in minutes once a leaf exists. Categories are created only on your explicit ask. Proposed tree (Chewy's *Supplies* menu, species-specific):\n")
w("- Dog → Supplies: Bowls & Feeders · Collars, Leads & Harnesses · Beds & Mats · Crates, Carriers & Travel · Clothing · Training & Behaviour · Cleaning & Odour Control · Hygiene (diapers, pads)")
w("- Cat → Supplies (66, exists): Litter Boxes & Accessories (67, exists) · Bowls & Feeders · Collars & Harnesses · Beds & Furniture · Carriers & Travel · Scratchers · Cleaning & Odour Control\n")
c = collections.Counter()
for r in blocked:
    m = re.search(r"productworld/(dog|cat|small-animal|bird)/([^/]+)/([^/]+)/", r.get("Source", ""))
    if r["Brand"] == "Mr. Fresh":
        kind = "cleaning / behaviour sprays"
    elif m:
        kind = f"{m.group(1)}: {m.group(2).replace('-', ' ')} › {m.group(3).replace('-', ' ')}"
    else:
        kind = "(no trixie.de page) " + (todo.get(r["Article Code"], {}).get("Category") or "").lower()
    c[(r["Brand"], kind)] += 1
w("| Brand | Kind (trixie.de section, or the CSV category for pageless rows) | Rows |\n|---|---|---|")
for (b, k), n in c.most_common(40):
    w(f"| {esc(b)} | {esc(k)} | {n} |")
w("")
w(f"### Sibling-priced — `runs/2026-09-11/sibling-priced.csv` ({len(sib)} row)\n")
for r in sib:
    w(f"- {r['Article Code']} {r['Brand']} *{r['Product (admin id)']} / {r['Variant']}*: cost {r['Buy Price (AMD)']}, sale {r['Sale Price (AMD)']} taken from sibling {r['Priced from (sibling code)']} ({r['Why hafo had no price']}).")
w("")

# ------------------------------------------------------------------ media
w("## Media\n")
img = load("image-plan.json") or {}
if img:
    import collections as _c
    per = _c.Counter(len(x["urls"]) for x in img.values())
    bysrc = _c.Counter()
    for x in img.values():
        for u in x["urls"]:
            bysrc[x["sources"][u]] += 1
    w("### Where the pictures come from\n")
    w("The first pass took only what the product page listed, which left 57 variants with no image and 138 with one. "
      "Two sweeps and three hand checks raised that to 481 variants with a picture and 335 with two or more — every URL "
      "keyed to the article number or to the EAN of our own hafo row, so nothing rests on a name match:\n")
    w("- **The TRIXIE CDN was probed directly** (`scripts/trixie-cdn-sweep.py`). A product page is written for a whole "
      "family, so a single-article variant usually keeps one photo; the CDN serves each shot under "
      "`<PREFIX>_<article>-<n>`, and sweeping 12 prefixes × n = 1..26 found 424 more pictures.")
    w("- **monge.it was crawled in full** (`scripts/monge-it-crawl.py`, 2,078 pages) and indexed by the EAN printed in "
      "each image file name, which the hafo row carries for our exact article.")
    w("- **ok-lock.pet and monge.it filled three more** by hand, from files that name the pack (`_5_4.png`, `_11_4.png`) "
      "or the line, form, lifestage and flavour — these replaced hafo placeholders with the brand's own photo.\n")
    w("**The hafo.am pictures are watermarked placeholders, not finished images.** Every photo hafo serves carries a "
      "repeating \"Hafo\" mark across the frame, so none of them may reach production. They are attached anyway where the "
      "brand site has nothing, so the PM can recognise the product and replace the photo by hand (PM decision, "
      "2026-09-11). Each one sits **last** in its gallery, so a brand shot always leads, and every variant carrying one "
      "is in `needs-image.csv` — that file is the replacement worklist.\n")
    w("| Images on a variant | Variants |\n|---|---|")
    for k in sorted(per):
        w(f"| {k} | {per[k]} |")
    w(f"| **total** | **{sum(per.values())}** |")
    w("")
    w("| Source | Images |\n|---|---|")
    for k, n in bysrc.most_common():
        w(f"| {k} | {n} |")
    w("")
    holder = [x for x in img.values() if x["urls"] and all("hafo.am" in x["sources"][u] for u in x["urls"])]
    w(f"### Watermarked placeholder only — `runs/2026-09-11/needs-image.csv` ({len(holder)})\n")
    w("These carry a hafo photo and nothing else, so the whole gallery needs replacing. 38 are Trixie articles that have "
      "left the catalogue: no product page, nothing on the CDN (12 file prefixes × 26 indices × 10 name suffixes probed), "
      "and no sibling page carries them. Four are Gran Bontà cans in a pack size monge.it does not picture (it publishes "
      "150 g, 300 g and 1230 g only). Price, text and attributes are complete; only the picture is a stand-in.\n")
    w("| Code | Product | admin id |\n|---|---|---|")
    for x in sorted(holder, key=lambda x: x["code"]):
        w(f"| {x['code']} | {esc(x['name'])} | {x['product_id']} |")
    w("")
    singles = [x for x in img.values() if len(x["urls"]) == 1]
    w(f"### Still on a single picture ({len(singles)})\n")
    w("For these the brand publishes exactly one photo of the article. Nothing was invented to pad them.\n")
    w("| Code | Product | The one image comes from |\n|---|---|---|")
    for x in sorted(singles, key=lambda x: x["code"]):
        w(f"| {x['code']} | {esc(x['name'])} | {esc(list(x['sources'].values())[0])} |")
    w("")
    w("### Identity errors the image work uncovered\n")
    w("- **004097 is the 800 g Mini Adult, not 3 kg.** The invoice, the hafo row and monge.shop's EAN 8009470004091 "
      "all say 800 g; the product had been created as 3 kg with the 3 kg bag photo. Renamed (product 636), pack "
      "weight set to 800 g, the per-kg rate corrected to 4,812.50 AMD/kg, and the wrong photo dropped.")
    w("- **Three Gran Bontà cans are 1230 g, not 1250 g** (products 661, 662, 664). The invoice says 1.230 g and the "
      "brand's own file is named `GRAN-BONTA-CANE-MANZO-1230_…`. Renamed; the Gemon 1250 g cans are genuinely 1250 g.")
    w("- The cause in both cases was joining on hafo's `barcodes`, which lists **every size in the listing**. The join "
      "now uses the barcode of our own row (`.siruk-cache/hafo-variant-barcode.json`), and an image whose file names a "
      "different pack is refused.\n")
w("### Feature-image audit\n")
w("`scripts/feature-image.py` re-checked all 524 variants and found **nothing to reorder** — the order written by the "
  "image pass already leads with the cleanest shot everywhere. It flags 249 feature images as *unknown*, which only "
  "means the file name is not one of Trixie's `PHO_*` patterns (monge.it, monge.shop, neoterica, comfypet and hafo "
  "files carry ordinary names), so the script cannot classify them by name alone. That flagged list is in "
  "`feature-audit.txt`; the rendered contact sheet is `feature-sheet.html`.\n")
w(f"### Feature image is not a clean packshot — `runs/2026-09-11/needs-packshot.csv` ({len(packshot)} rows)\n")
for r in packshot:
    w(f"- {r['Article Code']} {r['Brand']} *{r['Product']}*: {esc(r['Why'])}")
w("\n### Variants created without any image\n")
w("The brand site has no picture keyed to the article (rule: never attach an image from a fuzzy name match). They need a packshot from the distributor or a photo of the pack.\n")
for title, _ in PLANS:
    ni = per_plan_rows[title][3]
    if ni:
        w(f"- **{title}** ({len(ni)}): " + "; ".join(f"{n} [{s}]" for n, s in ni))
w("")

# ------------------------------------------------------------------ wanted values
w("## Vocabulary wanted but missing from the closed menu (questions)\n")
w("Not created (rule 8). Each would let the listed rows carry the attribute; today those variants simply lack it (or, for the toy sizes, the size is only in the label).\n")
want = collections.defaultdict(lambda: [0, ""])
for title, _ in PLANS:
    for x in per_plan_rows[title][0].get("wanted", []):
        k = (x["attribute"], x["label"]); want[k][0] += x.get("count", 1); want[k][1] = want[k][1] or x.get("evidence", "")
w("| Attribute | Value | Variants | Evidence (one) | Add it? |\n|---|---|---|---|---|")
for (a, l), (n, e) in sorted(want.items(), key=lambda x: (x[0][0], -x[1][0])):
    w(f"| {a} | {l} | {n} | {esc(e[:70])} | yes / no |")
w("")

# ------------------------------------------------------------------ flagged
w("## Flagged decisions (review)\n")
fl = collections.defaultdict(list)
for title, _ in PLANS:
    for f in per_plan_rows[title][0].get("flagged", []):
        fl[re.sub(r"'[^']*'", "'…'", f["what"])].append(f["code"])
for what, codes in sorted(fl.items(), key=lambda x: -len(x[1])):
    w(f"- **{esc(what)}** ({len(codes)}): {', '.join(codes[:25])}{' …' if len(codes) > 25 else ''}")
w("")
w("Name/description fallbacks: Trixie articles with no trixie.de page (pageless) got a hand-written English name from the invoice/hafo name and no description; "
  "their source column reads `fallback: hafo/invoice`. Monge-group pages: EAN-keyed match on monge.it / monge.shop, so names, images and compositions are the brand's own.\n")

# ------------------------------------------------------------------ brands
w("## Brands created this batch (ids 20–30, ru/hy written, logos verified by eye)\n")
w("| id | Brand | Logo source |\n|---|---|---|")
for bid, src in ((20, "https://www.monge.it/wp-content/uploads/2023/05/Lechat_logo.png"), (21, "https://www.monge.it/wp-content/uploads/2023/05/Specialdog_logo.png"),
                 (22, "https://neoterica.ru/sitefiles/Brands/424c4yKAIqxeRTmevbw7oYYkVg7Hfd4e.png"), (23, "https://neoterica.ru/sitefiles/Brands/0cZiuRecdwWTEdSBW-D1a3l0zao7Dlf3.jpg"),
                 (24, "https://neoterica.ru/sitefiles/Brands/5PeprSbsUa2SDG_PuVCQS0e2H-1ldubH.png"), (25, "https://neoterica.ru/sitefiles/Brands/RLjhFq3Z9QuN3IAnWadYdkS4b-RAhMgI.png"),
                 (26, "https://neoterica.ru/sitefiles/Brands/IG1QUVl5nI4Rv9ItyZqM_TrWvPRgBGKv.png"), (27, "https://neoterica.ru/sitefiles/Brands/pr4cewHzXc8wqespPu2wErkCElQJXGA-.jpg"),
                 (28, "https://comfypet.pl (site logo, comfy-logo.png)"), (29, "https://ivsanbernardcanada.ca/cdn/shop/files/logo-gold-transbg.png (ivsanbernard.it is behind a CAPTCHA)"),
                 (30, "https://www.beaphar.com (site logo SVG, rasterised)")):
    w(f"| {bid} | {brands[bid]} | {src} |")
w("\nBrand names stay Latin in every locale by policy; the ru/hy meta descriptions are written (`scripts/translate-brands.py`, problems: none).\n")

# ------------------------------------------------------------------ translations & checks
w("## Translations (status from `scripts/verify-translations.py`, not from what was sent)\n")
vt = read_txt("verify-translations.txt")
w("```\n" + (vt[:6000] if vt else "not run yet — pending the end of the import") + "\n```")
w("Product names, variant about/ingredients/feeding, category names and brand meta are per-locale and were written in ru + hy "
  "(`reference/translations.json` dictionary + the rule-based composition translator). Attribute names, value labels, family names and "
  "variant labels are single-language on this backend and stay English.\n")
w("## Post-import checks\n")
for label, fn in (("hafo price re-check (`scripts/check-hafo-prices.py`)", "price-check.txt"), ("media integrity (`scripts/verify-media.sh`)", "verify-media.txt"),
                  ("feature-image audit (`scripts/feature-image.py`)", "feature-audit.txt"), ("translation backfill (`scripts/backfill-translations.py`)", "backfill.txt")):
    t = read_txt(fn)
    w(f"### {label}\n")
    w("```\n" + (t[-3000:] if t else "not run yet") + "\n```\n")

# ------------------------------------------------------------------ docs
w("## Docs and tooling touched\n")
w("- `reference/brand-sites.md`: rows for Neoterica (Rolf Club, Inspector, Gelmintal, Insectal, Cliny, Mr. Fresh, SexControl), Comfy, Iv San Bernard, Beaphar; monge.it EAN-in-filename convention.")
w("- `reference/translations.json` (names 780, strings 494, paragraphs 123) and `reference/translations-composition.json` (composition terms/sentences) — reusable on the next import.")
w("- `scripts/import-plan.py` (resumable plan importer), `scripts/plan-trixie.py`, `scripts/plan-monge.py`, `scripts/plan-small.py`, `scripts/translate-composition.py`, `scripts/_write-run-csvs.py`, this report script.")
w("- `.siruk-cache/trixie-names.json`: hand-written English names for the 149 pageless Trixie articles (with `force` overrides where trixie.de reuses a page for several articles).")
w("")
open(os.path.join(RUN, "report.md"), "w").write("\n".join(L))
print("report.md", len(L), "lines; ids:", len(all_ids))
