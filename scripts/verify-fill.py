#!/usr/bin/env python3
"""Compare a product before and after a fill: only the expected fields may have changed.

    scripts/verify-fill.py --backup runs/<date>/pilot/backup <product-id> [<product-id> …]

Reads <backup>/<id>-<lang>.json (taken before the write) for en/ru/hy, GETs the product now, and
prints per locale: the name change, every variant text that went from empty to filled (with its
start), attribute changes, and whether EVERYTHING ELSE is byte-identical (prices, images, stock,
slug, categories). Photo changes are listed separately. Exit 1 if anything outside texts / names / attributes moved.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS = ("about_this_item", "ingredient_information", "feeding_instructions")
VOLATILE = {"updatedAt", "stock_levels", "available_quantity"}
# a size the card set: these move together (the server derives item_content / net_content / size_label)
SIZE = ("measure_type", "content", "pack_count", "item_content", "net_content", "size_label", "unit_price",
        "formatted_unit_price")


def get(pid, lang):
    env = dict(os.environ)
    if lang != "en":
        env["SIRUK_LANG"] = lang
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", f"/products/{pid}"],
                       capture_output=True, text=True, cwd=ROOT, env=env)
    return json.loads(r.stdout[r.stdout.find("{"):])["data"]


def plain(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")).strip()


def strip(x, extra):
    if isinstance(x, dict):
        return {k: strip(v, extra) for k, v in x.items() if k not in VOLATILE | extra}
    if isinstance(x, list):
        return [strip(v, extra) for v in x]
    return x


def main(argv):
    backup = argv[argv.index("--backup") + 1]
    ids = [a for a in argv if a.isdigit()]
    bad = False
    for pid in ids:
        for lang in ("en", "ru", "hy"):
            path = os.path.join(backup, f"{pid}-{lang}.json")
            if not os.path.exists(path):
                print(f"{pid} [{lang}]: no backup")
                continue
            a = json.load(open(path))
            a = a.get("data", a)
            b = get(pid, lang)
            json.dump({"data": b}, open(os.path.join(backup, f"{pid}-{lang}-after.json"), "w"), ensure_ascii=False)
            changed = {"name", "attribute_values", "attribute_value_labels", "used_attribute_ids", "images", *TEXTS,
                       *SIZE}
            same = strip(a, changed) == strip(b, changed)
            bad |= not same
            print(f"{pid} [{lang}] name: {a['name']!r}" + (f" -> {b['name']!r}" if a["name"] != b["name"] else " (same)")
                  + f" | everything else identical: {same}")
            before = {v["id"]: v for v in a["variants"]}
            for v in b["variants"]:
                o = before.get(v["id"], {})
                for k in TEXTS:
                    if plain(o.get(k)) != plain(v.get(k)):
                        print(f"    {v['sku']} {k}: {plain(o.get(k))[:40]!r} -> {plain(v.get(k))[:70]!r}")
                if lang == "en" and (o.get("size_label"), o.get("content")) != (v.get("size_label"), v.get("content")):
                    print(f"    {v['sku']} size: {o.get('size_label')!r} -> {v.get('size_label')!r}")
                if lang == "en" and (o.get("images") or []) != (v.get("images") or []):
                    print(f"    {v['sku']} images: {o.get('images')} -> {v.get('images')}")
                if lang == "en":
                    la = sorted(l["attributeName"] + ":" + l["label"] for l in o.get("attribute_value_labels") or [])
                    lb = sorted(l["attributeName"] + ":" + l["label"] for l in v.get("attribute_value_labels") or [])
                    if la != lb:
                        print(f"    {v['sku']} attributes: +{sorted(set(lb) - set(la))} -{sorted(set(la) - set(lb))}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
