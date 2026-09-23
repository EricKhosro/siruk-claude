#!/usr/bin/env python3
"""Give every variant of a multi-variant product the attribute axis its
siblings use (CLAUDE.md rule 9a).

The storefront builds the variant selector from ATTRIBUTES, never from the
label: a variant that lacks the value its siblings carry on `size`,
`color-family`, `flavor`, `product-weight`, `pet-weight-range` or `toy-size`
is unreachable (product 874 hid half its stock that way). A product that gains
a variant through add-variant.sh or a merge can end up like this when its
original single variant was imported without the axis ("Plastic Bowl
0.25 l/ø 10 cm" carried no `size`; "I.D. Tag" carried no colour).

For each live product with two or more variants, for each axis that at least
one sibling carries, a variant without it gets the value read off its own
label (`XS–S, 22–35 cm/10 mm, black` → size XS–S, colour Black; `0.25 l/ø 10 cm`
→ size; `85 g` → product-weight; `1–4 kg` → pet-weight-range; `28 cm` →
toy-size). Only labels in the closed menu are written; anything else is
listed as "wanted". It also lists variants that still share one attribute
combination after the fill (a colour the coarse family cannot separate).

    scripts/backfill-variant-axes.py            # dry run: prints the plan
    scripts/backfill-variant-axes.py --apply    # set-variant.sh per fix
    scripts/backfill-variant-axes.py --ids 813 844 848 --apply
"""
import argparse, collections, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, ".siruk-cache/catalogue-snapshot.json")
MENU = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
VAL = {code: {k.lower(): v for k, v in d["values"].items()} for code, d in MENU.items()}
LABEL = {code: {k.lower(): k for k in d["values"]} for code, d in MENU.items()}
AXES = ("size", "color-family", "flavor", "product-weight", "pet-weight-range", "toy-size")

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
    if code == "product-weight":
        if PETKG_RE.match(lab) or re.search(r"up to|over|[–-]\s*\d", lab.split(",")[0]):
            return None            # a dose band is the pet's weight, not the pack's (rule 8a)
        m = WEIGHT_RE.search(lab.split(",")[0])
        return m.group(1).replace(",", ".") if m else None
    if code == "pet-weight-range":
        m = PETKG_RE.match(lab)
        return m.group(1) if m else None
    if code == "toy-size":
        m = TOYCM_RE.search(lab.split(",")[0].strip())
        return f"{m.group(1).replace(',', '.')} cm" if m else None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--ids", nargs="*", default=None)
    a = ap.parse_args()
    snap = json.load(open(SNAP))
    only = {int(x) for x in a.ids} if a.ids else None

    fixes, wanted, collisions = [], collections.Counter(), []
    for pid, p in snap.items():
        if only and int(pid) not in only: continue
        vs = p["variants"]
        if len(vs) < 2: continue
        axes = [c for c in AXES if any(c in (v.get("attrs") or {}) for v in vs)]
        after = []
        for v in vs:
            attrs = dict(v.get("attrs") or {})
            for c in axes:
                if c in attrs: continue
                lab = derive(c, v.get("label"))
                if not lab: continue
                canon = LABEL.get(c, {}).get(lab.lower())
                if canon:
                    attrs[c] = canon
                    fixes.append((int(pid), p["name"], v["sku"], v.get("label"), c, canon, VAL[c][lab.lower()]))
                else:
                    wanted[(c, lab)] += 1
            after.append((v["sku"], tuple(sorted(attrs.items()))))
        combos = collections.Counter(x[1] for x in after)
        for combo, n in combos.items():
            if n > 1:
                collisions.append((int(pid), p["name"], [s for s, c in after if c == combo], dict(combo)))

    print(f"{len(fixes)} attribute value(s) to set on {len({f[0] for f in fixes})} product(s)", file=sys.stderr)
    for f in fixes:
        print(f"  {f[0]:>4} {f[1][:40]:<40} {f[2]:<10} {str(f[3])[:34]:<34} {f[4]} = {f[5]} ({f[6]})", file=sys.stderr)
    if wanted:
        print("wanted (not in the menu):", file=sys.stderr)
        for (c, lab), n in wanted.most_common():
            print(f"  {c}: {lab!r} ×{n}", file=sys.stderr)
    if collisions:
        print("still colliding after the fill (selector cannot tell these apart):", file=sys.stderr)
        for pid, name, skus, combo in collisions:
            print(f"  {pid} {name[:40]}: {skus} share {combo}", file=sys.stderr)
    if not a.apply:
        return
    ok = bad = 0
    by_var = collections.defaultdict(dict)
    for pid, name, sku, lab, c, canon, vid in fixes:
        by_var[(pid, sku)][c] = vid
    for (pid, sku), av in by_var.items():
        r = subprocess.run([os.path.join(ROOT, "scripts/set-variant.sh"), str(pid), sku,
                            json.dumps({"attribute_value_ids": av})], capture_output=True, text=True, cwd=ROOT, timeout=300)
        good = r.returncode == 0
        ok += good; bad += not good
        print(f"  {'ok ' if good else 'BAD'} {pid}/{sku} {av}" + ("" if good else f" {(r.stderr or r.stdout)[-160:]}"), file=sys.stderr)
    print(f"written {ok}, failed {bad}", file=sys.stderr)


if __name__ == "__main__":
    main()
