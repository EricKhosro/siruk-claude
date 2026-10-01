#!/usr/bin/env python3
"""Give every variant of a multi-variant product the axis its siblings use
(CLAUDE.md rule 9a).

The storefront builds the variant selector from the product type's OPTION-role
attributes plus the pack size (catalog model 2026-09-29): a variant that lacks
the option value its siblings carry is unreachable (product 874 hid half its
stock that way). A product that gains a variant through add-variant.sh or a
merge can end up like this when its original single variant was imported
without the axis ("Plastic Bowl 0.25 l/ø 10 cm" carried no `size`; "I.D. Tag"
carried no colour).

The axes of a product are read from its live product type
(`siruk_payload.product_type()`): every attribute with role "option" that at
least one sibling carries, plus the size — `measure_type`/`content` on the
variant columns, which is not an attribute (the old `product-weight` attribute
is retired). A variant without an axis gets it read off its own label
(`XS–S, 22–35 cm/10 mm, black` → size XS–S, colour Black; `0.25 l/ø 10 cm` →
size; `1–4 kg` → pet-weight-range; `28 cm` → toy-size; `85 g` → measure_type
mass, content 85 — never from a dose band, rule 8a). Option values are written
only when the label is in the closed menu; anything else is listed as
"wanted". It also lists variants that still share one option + size
combination after the fill (a colour the coarse family cannot separate).

The product list comes from .siruk-cache/catalogue-snapshot.json (products with
two or more variants); each candidate is then read LIVE, since the attribute
values are keyed by attribute id now and the snapshot does not carry them.

    scripts/backfill-variant-axes.py            # dry run: prints the plan
    scripts/backfill-variant-axes.py --apply    # set-variant.sh per fix
    scripts/backfill-variant-axes.py --ids 813 844 848 --apply
"""
import argparse, collections, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from siruk_payload import PayloadError, api, attributes, product_type  # noqa: E402

SNAP = os.path.join(ROOT, ".siruk-cache/catalogue-snapshot.json")
MENU = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
VAL = {code: {k.lower(): v for k, v in d["values"].items()} for code, d in MENU.items()}
LABEL = {code: {k.lower(): k for k in d["values"]} for code, d in MENU.items()}
UNIT = {"g": ("mass", 1), "kg": ("mass", 1000), "ml": ("volume", 1), "l": ("volume", 1000)}

LETTER = r"(?:XXS|XS|S|M|L|XL|XXL)"
LETTER_RUN_RE = re.compile(rf"^({LETTER}(?:\s*[–-]\s*{LETTER})?(?:,\s*{LETTER}(?:\s*[–-]\s*{LETTER})?)*)\s*(?:[,:]|$)")
CAPACITY_RE = re.compile(r"^(\d+(?:[.,]\d+)?\s*(?:l|ml)\s*/\s*ø\s*\d+(?:[.,]\d+)?\s*cm)", re.I)
WEIGHT_RE = re.compile(r"(?<![×x]\s)\b(\d+(?:[.,]\d+)?\s*(?:kg|g|ml|l))\s*$", re.I)
PETKG_RE = re.compile(r"^((?:up to|over)\s*\d+(?:[.,]\d+)?\s*kg|\d+(?:[.,]\d+)?\s*[–-]\s*\d+(?:[.,]\d+)?\s*kg)", re.I)
TOYCM_RE = re.compile(r"(?:^|ø\s*)(\d+(?:[.,]\d+)?)\s*cm$", re.I)
COLOUR = {"black": "Black", "royal blue": "Blue", "blue": "Blue", "dark blue": "Dark Blue", "neon blue": "Blue",
          "indigo": "Blue", "aqua": "Aqua", "ocean": "Blue", "petrol": "Teal", "red": "Red", "coral": "Red",
          "fuchsia": "Pink", "pink": "Pink", "neon pink": "Pink", "blush": "Blush", "antique pink": "Pink",
          "orchid": "Purple", "light lilac": "Purple", "purple": "Purple", "sangria": "Purple", "olive green": "Green",
          "green": "Green", "sage": "Sage", "mint": "Green", "mint green": "Green", "apple": "Green", "khaki": "Green",
          "grey": "Grey", "dark grey": "Grey", "light grey": "Grey", "graphite": "Grey", "silver grey": "Silver",
          "silver": "Silver", "chrome": "Silver", "gold": "Gold", "white": "White", "cream": "Ivory",
          "dark brown": "Brown", "brown": "Brown", "rust": "Brown", "orange": "Orange", "papaya": "Orange",
          "sand": "Beige", "beige": "Beige", "curry": "Yellow", "yellow": "Yellow", "neon yellow": "Yellow",
          "sorted": "Color Varies", "various": "Color Varies", "assorted": "Color Varies", "multi coloured": "Multi",
          "anthracite": "Grey", "natural": "Beige", "nature": "Beige"}


def colour_of(label):
    parts = [x.strip().lower() for x in (label or "").split(",")]
    txt = parts[-1] if len(parts) > 1 else (parts[0] if parts and parts[0] in COLOUR else "")
    if not txt:
        return None
    first = re.split(r"\s*/\s*", txt)[0].strip()
    for k in sorted(COLOUR, key=len, reverse=True):
        if first == k or first.endswith(" " + k) or first.startswith(k + " "):
            return COLOUR[k]
    return None


def derive(code, label):
    lab = (label or "").strip()
    if code == "size":
        m = LETTER_RUN_RE.match(lab)
        if m: return m.group(1).strip()
        m = CAPACITY_RE.match(lab)
        if m: return m.group(1).replace(",", ".").strip()
        return None
    if code == "color-family":
        return colour_of(lab)
    if code == "pet-weight-range":
        m = PETKG_RE.match(lab)
        return m.group(1) if m else None
    if code == "toy-size":
        m = TOYCM_RE.search(lab.split(",")[0].strip())
        return f"{m.group(1).replace(',', '.')} cm" if m else None
    return None


def derive_size(label):
    """`85 g` / `1.5 kg` / `500 ml` → (measure_type, content in g/ml), else None."""
    full = (label or "").strip()
    lab = full.split(",")[0]
    if PETKG_RE.match(lab) or re.search(r"up to|over|[–-]\s*\d", lab):
        return None                # a dose band is the pet's weight, not the pack's (rule 8a)
    # "85 g, red" carries it in front; "Veal, Liver & Vegetables 1250 g" at the end
    m = WEIGHT_RE.search(lab) or WEIGHT_RE.search(full)
    if not m:
        return None
    num, unit = re.match(r"(\d+(?:[.,]\d+)?)\s*(\w+)", m.group(1)).groups()
    mt, mult = UNIT[unit.lower()]
    c = round(float(num.replace(",", ".")) * mult, 3)
    return mt, int(c) if c == int(c) else c


def _num(x):
    return None if x is None else round(float(x), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--ids", nargs="*", default=None)
    a = ap.parse_args()
    snap = json.load(open(SNAP))
    only = {int(x) for x in a.ids} if a.ids else None
    amap = attributes()

    # fixes: (pid, name, sku, label, axis, shown value, patch for set-variant.sh)
    fixes, wanted, collisions, untyped = [], collections.Counter(), [], []
    for pid, sp in snap.items():
        if only and int(pid) not in only: continue
        if len(sp["variants"]) < 2: continue
        p = api("GET", f"/products/{pid}").get("data") or {}
        vs = p.get("variants") or []
        if len(vs) < 2: continue
        try:
            ptype = product_type(p.get("attribute_family_id") or 0)
        except PayloadError as e:
            untyped.append((int(pid), p.get("name", ""), str(e))); continue
        options = [(str(x["id"]), x["code"]) for x in ptype.get("attributes") or [] if x["role"] == "option"]
        axes = [(aid, code) for aid, code in options
                if any((v.get("attribute_values") or {}).get(aid) for v in vs)]
        sized = any(v.get("content") is not None for v in vs)
        after = []
        for v in vs:
            av = {k: list(ids) for k, ids in (v.get("attribute_values") or {}).items()}
            size = (v.get("measure_type"), _num(v.get("content")), v.get("pack_count") or 1)
            for aid, code in axes:
                if av.get(aid): continue
                lab = derive(code, v.get("name"))
                if not lab: continue
                canon = LABEL.get(code, {}).get(lab.lower())
                vid = VAL.get(code, {}).get(lab.lower())
                if canon and vid in (amap.get(code) or {}).get("values", set()):
                    av[aid] = [vid]
                    fixes.append((int(pid), p["name"], v["sku"], v.get("name"), code, canon,
                                  {"attribute_values": {code: [vid]}}))
                else:
                    wanted[(code, lab)] += 1
            if sized and v.get("sale_mode") == "pack" and v.get("content") is None:
                got = derive_size(v.get("name"))
                if got:
                    size = (got[0], got[1], v.get("pack_count") or 1)
                    fixes.append((int(pid), p["name"], v["sku"], v.get("name"), "size", f"{got[1]} ({got[0]})",
                                  {"measure_type": got[0], "content": got[1]}))
                else:
                    wanted[("size", v.get("name"))] += 1
            opt = tuple(sorted((aid, tuple(sorted(av[aid]))) for aid, _ in options if av.get(aid)))
            after.append((v["sku"], (opt, size)))
        combos = collections.Counter(x[1] for x in after)
        for combo, n in combos.items():
            if n > 1:
                collisions.append((int(pid), p["name"], [s for s, c in after if c == combo], combo))

    print(f"{len(fixes)} axis value(s) to set on {len({f[0] for f in fixes})} product(s)", file=sys.stderr)
    for f in fixes:
        print(f"  {f[0]:>4} {f[1][:40]:<40} {f[2]:<10} {str(f[3])[:34]:<34} {f[4]} = {f[5]} {json.dumps(f[6])}", file=sys.stderr)
    if wanted:
        print("wanted (not in the menu):", file=sys.stderr)
        for (c, lab), n in wanted.most_common():
            print(f"  {c}: {lab!r} ×{n}", file=sys.stderr)
    if collisions:
        print("still colliding after the fill (selector cannot tell these apart):", file=sys.stderr)
        for pid, name, skus, combo in collisions:
            print(f"  {pid} {name[:40]}: {skus} share {combo}", file=sys.stderr)
    if untyped:
        print("no product type (every product needs one — set it first):", file=sys.stderr)
        for pid, name, err in untyped:
            print(f"  {pid} {name[:40]}: {err}", file=sys.stderr)
    if not a.apply:
        return
    ok = bad = 0
    by_var = collections.defaultdict(dict)
    for pid, name, sku, lab, c, canon, patch in fixes:
        cur = by_var[(pid, sku)]
        cur.setdefault("attribute_values", {}).update(patch.get("attribute_values") or {})
        cur.update({k: x for k, x in patch.items() if k != "attribute_values"})
    for (pid, sku), patch in by_var.items():
        if not patch.get("attribute_values"):
            patch.pop("attribute_values", None)
        # set-variant.sh rebuilds the body through siruk_payload and refuses a failing check
        r = subprocess.run([os.path.join(ROOT, "scripts/set-variant.sh"), str(pid), sku,
                            json.dumps(patch)], capture_output=True, text=True, cwd=ROOT, timeout=300)
        good = r.returncode == 0
        ok += good; bad += not good
        print(f"  {'ok ' if good else 'BAD'} {pid}/{sku} {patch}" + ("" if good else f" {(r.stderr or r.stdout)[-160:]}"), file=sys.stderr)
    print(f"written {ok}, failed {bad}", file=sys.stderr)


if __name__ == "__main__":
    main()
