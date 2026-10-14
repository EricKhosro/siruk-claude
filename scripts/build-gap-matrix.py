#!/usr/bin/env python3
"""The catalogue gap matrix: per live variant, which fields are filled, empty, wrong or don't apply.

    uv run --with openpyxl python scripts/build-gap-matrix.py --out final/catalogue-gaps-<date>.xlsx

Read-only. Inputs: the en / ru / hy dumps (scripts/dump-products.py [--lang ru|hy]),
reference/product-types.json, reference/attribute-values.json, .siruk-cache/hafo-audit.json
and the media caches hafo-audit.py uses (media-cache / media-filenames / media-urls.json) to mark
hafo's watermarked placeholder photos with hafo-audit.py's own rules.

Statuses per cell:
  ok        filled and plausible
  EMPTY     applies to this product and is empty → to fill
  WRONG     filled but wrong: English field in Cyrillic/Armenian script, ru/hy identical to the
            English (a fallback, not a translation), only a hafo placeholder photo
  n/a       does not apply (a toy has no feeding guide; cat food has no breed size)

Applicability (the type skills + what the catalogue already does):
  about_this_item          every variant
  ingredient_information   food, treats, supplements, litter; grooming/accessories only for liquids,
                           sprays, powders and the like (by name / measure_type volume)
  feeding_instructions     same set ("how to use" for the non-food ones)
  net content              sized product types (measure_type set on the type)
  attributes               the type's FILTERABLE attributes, minus the not-applicable cases below
Sheets: Summary (counts per field and per brand) · Variants (the worklist) · Quality issues.
"""
import json, os, re, sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, ".siruk-cache", "live")
CONSUMABLE = {"Dry Food", "Wet Food", "Treats", "Supplements", "Litter"}
LIQUIDISH = re.compile(r"shampoo|conditioner|spray|lotion|drops|gel|wipes|cleaner|remover|balm|cream|"
                       r"powder|oil|foam|solution|serum|mousse|paste|liquid|repellent|deodor|odou?r|"
                       r"toothpaste|ear care|tearstain|stain", re.I)
CYR = re.compile(r"[А-Яа-яЁё]")
ARM = re.compile(r"[Ա-֏]")
TEXTS = ("about_this_item", "ingredient_information", "feeding_instructions")


def plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def load_dump(lang):
    d = os.path.join(LIVE, "products" if lang == "en" else f"products-{lang}")
    if not os.path.isdir(d):
        return {}
    return {int(f[:-5]): json.load(open(os.path.join(d, f))) for f in os.listdir(d) if f[:-5].isdigit()}


def tree():
    cats, root = {}, {}

    def walk(n, r, trail):
        cats[n["id"]] = " > ".join(trail + [n["name"]])
        root[n["id"]] = r
        for c in n.get("children") or []:
            walk(c, r, trail + [n["name"]])
    path = os.path.join(LIVE, "categories-after.json")
    data = json.load(open(path if os.path.exists(path) else os.path.join(LIVE, "categories.json")))
    for n in data.get("data", data) if isinstance(data, dict) else data:
        walk(n, n["name"], [])
    return cats, root


def hafo_media(media_ids):
    """Media ids that are hafo's watermarked photos, by hafo-audit.py's own rules: uploaded from
    hafo's CDN (media-cache.json) or carrying a hafo file name (media-filenames / media-urls caches)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("hafo_audit", os.path.join(ROOT, "scripts", "hafo-audit.py"))
    ha = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ha)
    cache = lambda f: json.load(open(os.path.join(ROOT, ".siruk-cache", f))) if os.path.exists(
        os.path.join(ROOT, ".siruk-cache", f)) else {}
    mc, names, murl = cache("media-cache.json"), cache("media-filenames.json"), cache("media-urls.json")
    bad = {v for u, v in mc.items() if ha.HAFO_CDN in u and isinstance(v, int)}
    src = {v: u for u, v in mc.items() if isinstance(v, int)}
    unknown = set()
    for mid in media_ids:
        rec = names.get(str(mid))
        fn = rec.get("filename") if isinstance(rec, dict) else None
        if not fn and murl.get(str(mid)):
            fn = murl[str(mid)].rsplit("/", 1)[-1]
        if fn is None:
            unknown.add(mid)
        elif ha.looks_like_hafo(fn, src.get(mid)):
            bad.add(mid)
    return bad, unknown


def build():
    en, ru, hy = load_dump("en"), load_dump("ru"), load_dump("hy")
    types = {t["id"]: t for t in json.load(open(os.path.join(ROOT, "reference", "product-types.json")))}
    menu = json.load(open(os.path.join(ROOT, "reference", "attribute-values.json")))
    code_of = {str(a["attribute_id"]): c for c, a in menu.items() if isinstance(a, dict) and "attribute_id" in a}
    id_of = {c: i for i, c in code_of.items()}
    cats, root = tree()
    all_media = {int(i if not isinstance(i, dict) else i.get("id")) for p in en.values()
                 for v in p["variants"] for i in (v.get("images") or []) if i}
    hafo, unknown_media = hafo_media(all_media)
    if unknown_media:
        print(f"⚠ {len(unknown_media)} media ids with no cached file name — the placeholder check skips them "
              "(fill .siruk-cache/media-urls.json first)", file=sys.stderr)
    rows, issues = [], []
    for pid, p in sorted(en.items()):
        if p.get("is_discontinued"):
            continue
        t = types.get(p.get("attribute_family_id")) or {}
        tname = t.get("name", "?")
        roots = {root.get(c) for c in p.get("category_ids") or []}
        pr, ph = ru.get(pid) or {}, hy.get(pid) or {}
        filterable = [a for a in t.get("attributes") or [] if a.get("isFilterable") or a.get("is_filterable")]
        for v in p["variants"]:
            r = {"product_id": pid, "product": p["name"], "brand_id": p.get("brand_id"), "type": tname,
                 "categories": " | ".join(cats.get(c, str(c)) for c in p.get("category_ids") or []),
                 "variant_id": v["id"], "sku": v["sku"], "label": v.get("size_label") or v.get("name")}
            liquid = v.get("measure_type") == "volume" or bool(LIQUIDISH.search(p["name"]))
            for k in TEXTS:
                applies = k == "about_this_item" or tname in CONSUMABLE or (tname in ("Grooming", "Accessories") and liquid)
                val = plain(v.get(k))
                if not applies:
                    r[k] = "ok" if val else "n/a"
                elif not val:
                    r[k] = "EMPTY"
                elif CYR.search(val) or ARM.search(val):
                    r[k] = "WRONG"
                    issues.append((pid, v["id"], v["sku"], p["name"], f"{k} (en) is not in English", val[:120]))
                else:
                    r[k] = "ok"
                for lang, other in (("ru", pr), ("hy", ph)):
                    ov = next((plain(x.get(k)) for x in (other.get("variants") or []) if x.get("id") == v["id"]), "")
                    col = f"{k}_{lang}"
                    if not val:
                        r[col] = "n/a" if r[k] in ("n/a",) else "-"
                    elif not other:
                        r[col] = "?"
                    elif not ov or ov == val:
                        r[col] = "EMPTY"
                    else:
                        r[col] = "ok"
            for lang, other in (("ru", pr), ("hy", ph)):
                n = other.get("name")
                r[f"name_{lang}"] = "?" if not other else ("EMPTY" if not n or n == p["name"] else "ok")
            imgs = v.get("images") or []
            ids = [int(i if not isinstance(i, dict) else i.get("id")) for i in imgs if i]
            r["images"] = len(ids)
            r["photo"] = ("EMPTY" if not ids else "WRONG" if ids and all(i in hafo for i in ids)
                          else "placeholder last" if ids and ids[-1] in hafo else "ok")
            if t.get("measureType") and v.get("sale_mode") == "pack":
                r["size"] = "ok" if v.get("content") is not None else "EMPTY"
            else:
                r["size"] = "n/a"
            for k in ("barcode", "accounting_code", "price_source_url"):
                r[k] = "ok" if v.get(k) else "EMPTY"
            missing = []
            for a in filterable:
                code = a.get("code")
                if code == "breed-size" and roots and roots <= {"Cat", "Bird", "Small Animal"}:
                    continue
                if code == "texture" and tname != "Wet Food":
                    continue
                aid = str(a.get("id") or id_of.get(code))
                if not (v.get("attribute_values") or {}).get(aid):
                    missing.append(code)
            r["filter_attrs_missing"] = ", ".join(missing)
            rows.append(r)
    return rows, issues


def write(path, rows, issues):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    brands = {}
    bpath = os.path.join(LIVE, "brand-names.json")
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        from siruk_payload import api
        brands = {b["id"]: b["name"] for b in api("GET", "/brands?forProducts=true").get("data", [])}
    except Exception:
        if os.path.exists(bpath):
            brands = {int(k): v for k, v in json.load(open(bpath)).items()}
    status_cols = ["about_this_item", "ingredient_information", "feeding_instructions", "photo", "size",
                   "barcode", "accounting_code", "price_source_url", "name_ru", "name_hy",
                   "about_this_item_ru", "about_this_item_hy", "ingredient_information_ru",
                   "ingredient_information_hy", "feeding_instructions_ru", "feeding_instructions_hy"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Field", "To fill (EMPTY)", "Wrong (WRONG)", "OK", "Not applicable"])
    for c in status_cols + ["filter_attrs_missing"]:
        if c == "filter_attrs_missing":
            n = sum(1 for r in rows if r[c])
            ws.append([c, n, 0, len(rows) - n, 0])
            continue
        cnt = Counter(r[c] for r in rows)
        ws.append([c, cnt["EMPTY"], cnt["WRONG"], cnt["ok"] + cnt["placeholder last"], cnt["n/a"] + cnt["-"]])
    ws.append([])
    ws.append(["Brand", "Variants", "Missing about", "Missing ingredients", "Missing feeding", "Photo problem",
               "Filter attrs missing", "Not translated (any)"])
    by = defaultdict(Counter)
    for r in rows:
        b = by[brands.get(r["brand_id"], str(r["brand_id"]))]
        b["v"] += 1
        b["about"] += r["about_this_item"] == "EMPTY"
        b["ingr"] += r["ingredient_information"] == "EMPTY"
        b["feed"] += r["feeding_instructions"] == "EMPTY"
        b["photo"] += r["photo"] in ("EMPTY", "WRONG")
        b["attrs"] += bool(r["filter_attrs_missing"])
        b["tr"] += any(r[c] == "EMPTY" for c in status_cols if c.endswith(("_ru", "_hy")))
    for name, b in sorted(by.items(), key=lambda x: -x[1]["v"]):
        ws.append([name, b["v"], b["about"], b["ingr"], b["feed"], b["photo"], b["attrs"], b["tr"]])
    for c in ws[1] + ws[len(status_cols) + 4]:
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 30
    ws2 = wb.create_sheet("Variants")
    cols = ["product_id", "product", "brand", "type", "categories", "variant_id", "sku", "label", "images"] + \
        status_cols + ["filter_attrs_missing"]
    ws2.append(cols)
    red, amber = PatternFill("solid", fgColor="FBE3E1"), PatternFill("solid", fgColor="FFF1D6")
    for r in rows:
        ws2.append([brands.get(r["brand_id"], r["brand_id"]) if c == "brand" else r.get(c) for c in cols])
        for i, c in enumerate(cols, 1):
            val = ws2.cell(ws2.max_row, i).value
            if val == "EMPTY":
                ws2.cell(ws2.max_row, i).fill = red
            elif val == "WRONG":
                ws2.cell(ws2.max_row, i).fill = amber
    for c in ws2[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True)
    ws2.freeze_panes = "C2"
    ws2.auto_filter.ref = ws2.dimensions
    ws3 = wb.create_sheet("Quality issues")
    ws3.append(["product_id", "variant_id", "sku", "product", "issue", "text (start)"])
    for i in issues:
        ws3.append(list(i))
    for c in ws3[1]:
        c.font = Font(bold=True)
    wb.save(path)


def main(argv):
    out = argv[argv.index("--out") + 1] if "--out" in argv else "final/catalogue-gaps.xlsx"
    rows, issues = build()
    json.dump({"rows": rows, "issues": issues}, open(os.path.join(ROOT, ".siruk-cache", "gap-matrix.json"), "w"),
              ensure_ascii=False)
    write(os.path.join(ROOT, out), rows, issues)
    c = Counter()
    for r in rows:
        for k, v in r.items():
            if v == "EMPTY":
                c[k] += 1
            if v == "WRONG":
                c[k + " WRONG"] += 1
    print(f"{len(rows)} variants; " + ", ".join(f"{k} {n}" for k, n in c.most_common()))
    print(f"quality issues: {len(issues)}")


if __name__ == "__main__":
    main(sys.argv[1:])
