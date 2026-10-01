#!/usr/bin/env python3
"""Product types (the API's attribute-families) — live snapshot and pre-import check.

    scripts/product-types.py --dump                 # -> reference/product-types.json (+ a table on stdout)
    scripts/product-types.py --check payload.json…  # create-product payloads / new-variant files

--check runs every payload through scripts/siruk_payload.py without writing:
a product with no product type, an attribute outside its type, two values on
an option, a required attribute missing, a sized type with no content, or two
variants the storefront cannot tell apart are all reported. Run it on the whole
batch after the attribute-manager agent has created/extended the types and
before the first write; exit 1 if any payload fails.

The snapshot is for reading (skills, planners, the agent). Roles and flags are
decided in the admin / by the agent, never by editing the snapshot.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from siruk_payload import PayloadError, api, post_body  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "reference", "product-types.json")


def dump():
    types = api("GET", "/attribute-families").get("data") or []
    snap = [{k: t.get(k) for k in ("id", "name", "code", "defaultSaleMode", "measureType", "unitPriceBasis")}
            | {"attributes": [{k: a.get(k) for k in ("id", "code", "name", "inputType", "role", "isRequired",
                                                      "isFilterable", "showOnProductCard", "position")}
                              for a in sorted(t.get("attributes") or [], key=lambda a: a.get("position") or 0)]}
            for t in types]
    with open(OUT, "w") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    for t in snap:
        print(f"#{t['id']} {t['name']} ({t['code']})  measure={t['measureType']}  sale={t['defaultSaleMode']}")
        for a in t["attributes"]:
            flags = ("F" if a["isFilterable"] else "-") + ("C" if a["showOnProductCard"] else "-") + ("R" if a["isRequired"] else "-")
            print(f"   {a['role']:<9} {flags}  {a['id']:>3} {a['name']}")
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}  (F filterable, C on card, R required)")


def check(files):
    bad = 0
    for path in files:
        data = json.load(open(path))
        if "variants" not in data:
            print(f"- {path}: not a product payload (new-variant files are checked by add-variant.sh itself)")
            continue
        try:
            post_body(data)
            print(f"ok {path}")
        except PayloadError as e:
            bad += 1
            print(f"FAIL {path}: {e}")
    print(f"\n{len(files) - bad}/{len(files)} payloads pass")
    return 1 if bad else 0


def main(argv):
    if argv[:1] == ["--dump"]:
        dump()
    elif argv[:1] == ["--check"] and len(argv) > 1:
        sys.exit(check(argv[1:]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
