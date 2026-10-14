#!/usr/bin/env python3
"""Fill the EMPTY fields of live variants from reviewed gap cards. Never overwrites a filled field.

    scripts/fill-gaps.py --run runs/<date> [--only 1200,1201]            # validate + plan (no writes)
    scripts/fill-gaps.py --run runs/<date> --apply [--only …]            # write en, then ru/hy

One card per variant, <run>/gapcards/<variant_id>.json, written by whoever read the source page:

  {"product_id": 1200, "variant_id": 1758, "sku": "12207S",
   "source": {"kind": "brand-site", "url": "https://…"},          # rule 7 ladder: brand-site, country-site,
                                                                  # barcode, 4lapy, zoovet, petshop, web, hafo
   "evidence_file": "evidence/1758.txt",                          # the raw page text, relative to the run
   "texts": {"about_this_item": "<p>…</p>", "ingredient_information": "<p>…</p>",
             "feeding_instructions": "<p>…</p>"},                 # English HTML; omit what the page lacks
   "attributes": {"lifestage": {"value": "Adult", "quote": "for adult dogs"}},
   "images": [{"url": "https://…", "source": "brand-site", "why": "page of art. 12207"}],   # full gallery, packshot first
   "replace_wrong": ["ingredient_information"],          # only replaces an en field that is in Cyrillic/Armenian live
   "replace_gallery": true, "drop_existing": [12062],     # only after looking: a better official photo replaces a weaker copy
   "size": {"measure_type": "count", "content": 1, "pack_count": 1},                        # only if the variant has none
   "translations": {"ru": {"about_this_item": "…", …}, "hy": {…}}}                          # machine translation is fine (user, 2026-10-12)

Checks before anything is written (a failing card is skipped, the rest go ahead):
  * texts are English (no Cyrillic / Armenian in the en fields) and non-trivial;
  * each attribute: a label of reference/attribute-values.json, part of the product's type, its quote
    found verbatim in the evidence file or the card's own texts (CLAUDE.md 8);
  * a field is only planned when it is EMPTY live — a filled one is reported as "kept" instead;
  * translations exist for every text the card writes (ru and hy), else the card holds.
Writing: images through apply-gap-images.py with MEDIA_DIR=products/<brand-slug>/<type> (verified
upload, new photos first, earlier non-hafo photos kept after them, hafo placeholder dropped); texts,
attributes and size in ONE PUT per product via siruk_payload.put_body; then set-translation.py per
locale with only the new texts (other variants' translations are kept by that script). Every
written field is logged to <run>/fill-log.csv with its source url.
"""
import csv, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import PayloadError, api, attributes, product_type, put_body  # noqa: E402

TEXTS = ("about_this_item", "ingredient_information", "feeding_instructions")
# media folder per product type (rule 7: products/<brand-slug>/<type>, as card-import.py does)
TYPE_DIR = {"Dry Food": "dry-food", "Wet Food": "wet-food", "Treats": "treats", "Supplements": "supplements",
            "Toys": "toys", "Grooming": "grooming", "Accessories": "accessories", "Litter": "litter"}
_brands = None


def media_dir(live):
    global _brands
    if _brands is None:
        # same derivation as card-import.py, so a brand's photos stay in one folder
        _brands = {b["id"]: re.sub(r"[^a-z0-9]+", "-", str(b.get("name", "")).lower()).strip("-")
                   for b in api("GET", "/brands?forProducts=true").get("data", [])}
    bslug = _brands.get(live.get("brand_id")) or "unbranded"
    return f"products/{bslug}/{TYPE_DIR.get(live.get('attribute_family_name'), 'accessories')}"
NON_LATIN = re.compile(r"[А-Яа-яЁёԱ-֏]")
MENU = json.load(open(os.path.join(ROOT, "reference", "attribute-values.json")))


def plain(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")).strip()


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def check(card, run, live):
    """Returns (plan, kept, errors). plan = {field: value} limited to fields EMPTY live."""
    errs, kept, plan = [], [], {}
    v = next((x for x in live["variants"] if x["id"] == card["variant_id"]), None)
    if v is None:
        return {}, [], [f"variant {card['variant_id']} is not on product {card['product_id']}"]
    if str(v["sku"]) != str(card.get("sku")):
        errs.append(f"sku mismatch: live {v['sku']} vs card {card.get('sku')}")
    if not (card.get("source") or {}).get("url"):
        errs.append("no source url")
    evidence = ""
    if card.get("evidence_file"):
        path = os.path.join(run, card["evidence_file"])
        evidence = open(path).read() if os.path.exists(path) else ""
        if not evidence:
            errs.append(f"evidence file missing: {card['evidence_file']}")
    texts = card.get("texts") or {}
    for k in TEXTS:
        t = texts.get(k)
        if not t:
            continue
        if NON_LATIN.search(plain(t)):
            errs.append(f"{k}: not English")
        elif len(plain(t)) < 20:
            errs.append(f"{k}: too short to be real")
        elif plain(v.get(k)):
            # the one exception to "never overwrite": an English field that is provably not English
            if k in (card.get("replace_wrong") or []) and NON_LATIN.search(plain(v.get(k))):
                plan[k] = t
            else:
                kept.append(k)
        else:
            plan[k] = t
    ptype = product_type(live["attribute_family_id"])
    in_type = {a["code"]: a for a in ptype.get("attributes") or []}
    amap = attributes()
    hay = norm(evidence + " " + " ".join(plain(x) for x in texts.values() if x))
    for code, pick in (card.get("attributes") or {}).items():
        a = in_type.get(code)
        labels = (MENU.get(code) or {}).get("values") or {}
        if a is None:
            errs.append(f"attribute {code} is not part of product type {ptype.get('name')}")
            continue
        if pick.get("value") not in labels:
            errs.append(f"{code}: '{pick.get('value')}' is not in the closed menu")
            continue
        if pick.get("basis") != "photo" and norm(pick.get("quote")) not in hay:
            errs.append(f"{code}: quote not found in the evidence: {pick.get('quote')!r}")
            continue
        aid = str(amap[code]["id"])
        if (v.get("attribute_values") or {}).get(aid):
            kept.append(f"attr {code}")
        else:
            plan.setdefault("attribute_values", {})[aid] = [labels[pick["value"]]]
    if card.get("size"):
        if v.get("content") is not None:
            kept.append("size")
        else:
            plan.update({k: card["size"][k] for k in ("measure_type", "content", "pack_count") if k in card["size"]})
    if card.get("images"):
        # apply-gap-images replaces the gallery; only do that where the live gallery is empty, a lone
        # hafo placeholder, or smaller than the reviewed one (a fuller official gallery)
        if len(v.get("images") or []) >= len(card["images"]) and not card.get("replace_gallery"):
            kept.append("images")
        else:
            plan["_images"] = card["images"]
            if card.get("drop_existing"):        # reviewed duplicates / weaker copies the new photos replace
                plan["_drop"] = [int(x) for x in card["drop_existing"]]
    for lang in ("ru", "hy"):
        tr = (card.get("translations") or {}).get(lang) or {}
        for k in TEXTS:
            if k in plan and not tr.get(k):
                errs.append(f"{k}: no {lang} translation in the card")
            elif k in plan and lang == "hy" and not re.search(r"[Ա-֏]", plain(tr[k])):
                errs.append(f"{k}: hy translation is not in Armenian")
            elif k in plan and lang == "ru" and not re.search(r"[А-Яа-яЁё]", plain(tr[k])):
                errs.append(f"{k}: ru translation is not in Russian")
    return plan, kept, errs


def main(argv):
    if "--run" not in argv:
        sys.exit(__doc__)
    run = os.path.join(ROOT, argv[argv.index("--run") + 1])
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
    folder = os.path.join(run, "gapcards")
    cards = [json.load(open(os.path.join(folder, f))) for f in sorted(os.listdir(folder)) if f.endswith(".json")]
    if only:
        cards = [c for c in cards if str(c["product_id"]) in only]
    by_product = {}
    for c in cards:
        by_product.setdefault(c["product_id"], []).append(c)
    apply = "--apply" in argv
    log_path = os.path.join(run, "fill-log.csv")
    new_log = not os.path.exists(log_path)
    log = csv.writer(open(log_path, "a", newline="", encoding="utf-8"))
    if new_log:
        log.writerow(["product_id", "variant_id", "sku", "field", "source_kind", "source_url", "status"])
    totals = {"planned": 0, "kept": 0, "held": 0, "written": 0}
    for pid, pcards in by_product.items():
        live = api("GET", f"/products/{pid}")["data"]
        plans = {}
        for c in pcards:
            plan, kept, errs = check(c, run, live)
            totals["kept"] += len(kept)
            if errs:
                totals["held"] += 1
                print(f"HOLD {pid}/{c['variant_id']} {c.get('sku')}: " + "; ".join(errs))
                continue
            if plan:
                plans[c["variant_id"]] = (c, plan)
                totals["planned"] += len([k for k in plan if k != "attribute_values"]) + len(plan.get("attribute_values", {}))
                print(f"PLAN {pid}/{c['variant_id']} {c.get('sku')}: {', '.join(k for k in plan)}"
                      + (f"  (kept: {', '.join(kept)})" if kept else ""))
        if not apply or not plans:
            continue
        # 1. images: the reviewed apply-gap-images path (verified uploads, hafo placeholder dropped)
        found = [{"product_id": pid, "sku": c["sku"], "article": c["sku"], "images": p["_images"]}
                 for c, p in plans.values() if p.get("_images")]
        if found:
            tmp = os.path.join(run, f".found-{pid}.json")
            json.dump(found, open(tmp, "w"))
            r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/apply-gap-images.py"), tmp],
                               capture_output=True, text=True, cwd=ROOT,
                               env=dict(os.environ, MEDIA_DIR=media_dir(live)))
            if r.returncode:
                print(f"FAIL {pid} images: {r.stderr.strip()[-300:]}")
                continue
            live = api("GET", f"/products/{pid}")["data"]
        # 2. texts / attributes / size in one PUT
        try:
            body = put_body(live)
            for bv in body["variants"]:
                c_p = plans.get(bv.get("id"))
                if not c_p:
                    continue
                for k, val in c_p[1].items():
                    if k == "_drop":
                        bv["images"] = [i for i in bv.get("images") or [] if i not in val]
                        continue
                    if k == "_images":
                        continue
                    if k == "attribute_values":
                        bv["attribute_values"] = {**(bv.get("attribute_values") or {}), **val}
                    else:
                        bv[k] = val
            api("PUT", f"/products/{pid}", body)
        except (PayloadError, Exception) as e:
            print(f"FAIL {pid}: {e}")
            continue
        back = {v["id"]: v for v in api("GET", f"/products/{pid}")["data"]["variants"]}
        # 3. translations, only the new texts
        for lang in ("ru", "hy"):
            tr = {"variants": {}}
            for vid, (c, p) in plans.items():
                t = {k: c["translations"][lang][k] for k in TEXTS if k in p}
                if t:
                    tr["variants"][str(c["sku"])] = t
            if tr["variants"]:
                tmp = os.path.join(run, f".tr-{pid}-{lang}.json")
                json.dump(tr, open(tmp, "w"), ensure_ascii=False)
                r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/set-translation.py"), str(pid), lang, tmp],
                                   capture_output=True, text=True, cwd=ROOT)
                if r.returncode:
                    print(f"FAIL {pid} {lang}: {r.stderr.strip()[-300:]}")
        for vid, (c, p) in plans.items():
            for k in p:
                ok = k in ("_images", "_drop", "attribute_values") or plain(str(back.get(vid, {}).get(k))) != ""
                log.writerow([pid, vid, c["sku"], k, c["source"].get("kind"), c["source"].get("url"),
                              "written" if ok else "NOT READ BACK"])
                totals["written"] += ok
        print(f"DONE {pid}")
        subprocess.run([os.path.join(ROOT, "scripts/pace.sh"), "product"], cwd=ROOT)
    print(f"\nplanned {totals['planned']} fields, kept {totals['kept']} filled ones, held {totals['held']} cards"
          + (f", wrote {totals['written']}" if apply else " — dry run, nothing written (--apply)"))


if __name__ == "__main__":
    main(sys.argv[1:])
