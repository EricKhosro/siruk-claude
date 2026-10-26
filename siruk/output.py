"""Plain-text tables for the CLI (pipe-friendly); --json prints the data instead."""
import json, sys, unicodedata


def _w(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def table(rows, cols, out=None):
    """rows: list of dicts; cols: [(key, header)]. Values are str()-ed, None → '-'."""
    out = out or sys.stdout
    cells = [[("-" if r.get(k) is None else str(r.get(k))) for k, _ in cols] for r in rows]
    widths = [max([_w(h)] + [_w(c[i]) for c in cells]) for i, (_, h) in enumerate(cols)]
    pad = lambda s, w: s + " " * (w - _w(s))
    print("  ".join(pad(h, widths[i]) for i, (_, h) in enumerate(cols)).rstrip(), file=out)
    print("  ".join("─" * w for w in widths), file=out)
    for c in cells:
        print("  ".join(pad(v, widths[i]) for i, v in enumerate(c)).rstrip(), file=out)


def dump(data, out=None):
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str), file=out or sys.stdout)


def money(x):
    return "-" if x in (None, "") else f"{int(float(x)):,}".replace(",", " ")


def product(s, out=None):
    out = out or sys.stdout
    print(f"product {s['id']}  {s['name']}   [type {s['product_type']}  brand {s['brand_id']}  "
          f"categories {s['category_ids']}]", file=out)
    rows = []
    for v in s["variants"]:
        rows.append({**v, "price": money(v["price"]), "cost": money(v["cost"]),
                     "margin": "-" if v["margin_pct"] is None else f"{v['margin_pct']}%"
                               + (" ✗ BELOW COST" if v["below_cost"] else ""),
                     "default": "★" if v["default"] else "",
                     "attrs": ", ".join(f"{k}: {x}" for k, x in (v.get("options") or {}).items())})
    table(rows, [("id", "variant"), ("default", ""), ("sku", "sku"), ("label", "label"), ("size", "size"),
                 ("price", "price"), ("cost", "cost"), ("margin", "margin"), ("stock", "stock"),
                 ("barcode", "barcode"), ("accounting_code", "acct"), ("images", "img"), ("attrs", "options")],
          out)


def diff(rows, out=None):
    out = out or sys.stdout
    if not rows:
        print("no changes", file=out)
        return
    for d in rows:
        tag = d["sku"] or "product"
        old, new = d["old"], d["new"]
        if isinstance(old, str) and len(old) > 70:
            old = old[:67] + "…"
        if isinstance(new, str) and len(new) > 70:
            new = new[:67] + "…"
        print(f"  {tag:<24} {d['field']:<24} {json.dumps(old, ensure_ascii=False)} → "
              f"{json.dumps(new, ensure_ascii=False)}", file=out)
