#!/usr/bin/env python3
"""Add attribute values that the register needs and the menu does not have.

Rule 8 keeps the vocabulary closed, so this only ever runs on an explicit ask,
and it only ADDS — it never renames or deletes a value other products use.
Every label must already have its ru/hy pair in
`reference/translations-attributes.json`, so `translate-attributes.py` can
follow straight after (rule 13).

    scripts/add-attribute-values.py product-weight --dry-run
    scripts/add-attribute-values.py product-weight --apply
"""
import argparse, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
MENU = os.path.join(ROOT, "reference/attribute-values.json")
TRANS = os.path.join(ROOT, "reference/translations-attributes.json")


def api(method, path, payload=None):
    cmd = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "attr-value-post.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        cmd.append(p)
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    if i < 0:
        raise SystemExit(f"{method} {path} failed:\n{r.stdout[-400:]}\n{r.stderr[-400:]}")
    return json.loads(r.stdout[i:])


def slug(label):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", label.lower())).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("code", help="attribute code, e.g. product-weight")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    menu = json.load(open(MENU))
    if a.code not in menu:
        raise SystemExit(f"{a.code} is not in {MENU}")
    attr_id = menu[a.code]["attribute_id"]
    have = set(menu[a.code]["values"])
    want = json.load(open(TRANS))["values"].get(a.code, {})

    todo = [lab for lab in want if lab not in have]
    print(f"{a.code} (attribute {attr_id}): {len(have)} values live, "
          f"{len(todo)} to add", file=sys.stderr)
    for lab in todo:
        print(f"   + {lab:<10} {want[lab]}", file=sys.stderr)
    if not todo:
        return
    if not a.apply:
        print("\ndry run — re-run with --apply", file=sys.stderr)
        return

    created = {}
    for lab in todo:
        d = api("POST", "/attribute-values",
                {"attribute_id": attr_id, "value": slug(lab), "label": lab})["data"]
        if d.get("label") != lab:
            raise SystemExit(f"{lab}: came back as {d.get('label')!r} — STOPPING")
        created[lab] = d["id"]
        print(f"   created {d['id']:>4}  {lab}", file=sys.stderr)

    menu[a.code]["values"].update(created)
    json.dump(menu, open(MENU, "w"), ensure_ascii=False, indent=1)
    print(f"\n{len(created)} value(s) created; {MENU} refreshed.\n"
          f"Now run: scripts/translate-attributes.py", file=sys.stderr)


main()
