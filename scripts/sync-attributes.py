#!/usr/bin/env python3
"""Sync the admin attribute vocabulary to a spec file (default: reference/chewy-attributes.json).

Idempotent — every run diffs against the LIVE admin, so it can be re-run after
an interruption. Per attribute in the spec:
  * create the attribute if its code does not exist
  * rename our existing values whose meaning equals a spec value (spec "renames")
  * create the spec values that do not exist (match is case/punctuation-insensitive)
  * set isFilterable from the spec ("filterable": false hides it from the storefront sidebar)
  * report live values that are NOT in the spec (never deleted — the user decides)
Then extends each family's attribute_ids (keeps existing order, appends the "add" list).

    scripts/sync-attributes.py [--spec file] [--dry-run] [--only code,code]
"""
import argparse, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_sync.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=180)
    body = r.stdout
    i = body.find("{")
    try:
        return json.loads(body[i:]) if i >= 0 else {}
    except ValueError:
        return {"_raw": body, "_err": r.stderr}


def norm(s):
    """Case/punctuation-insensitive key. Keeps a dot between digits so '3.5 cm'
    and '35 cm' stay different values."""
    s = (s or "").lower()
    s = re.sub(r"(?<=\d)\.(?=\d)", "\x00", s)
    return re.sub(r"[^a-z0-9\x00]", "", s).replace("\x00", ".")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=os.path.join(ROOT, "reference/chewy-attributes.json"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    only = set(filter(None, a.only.split(",")))
    dry = a.dry_run

    live = {x["code"]: x for x in api("GET", "/attributes?forProducts=true").get("data", [])}
    # /attribute-values is paginated (15/page) — read each attribute's own record instead,
    # which embeds every value.
    by_attr = {}
    for code, att in live.items():
        if only and code not in only:
            continue
        full = api("GET", f"/attributes/{att['id']}").get("data") or {}
        by_attr[code] = full.get("values") or []
        for k in ("isFilterable", "isVariant"):
            if k in full:
                att[k] = full[k]

    report = {"created_attributes": [], "created_values": {}, "renamed": {}, "extras": {}, "filterable": {}}
    for code, s in spec["attributes"].items():
        if only and code not in only:
            continue
        att = live.get(code)
        if not att:
            print(f"+ attribute {code} ({s['name']})")
            if not dry:
                att = api("POST", "/attributes", {"code": code, "name": s["name"]}).get("data")
                if not att:
                    print(f"  ! failed to create {code}"); continue
                live[code] = att
            report["created_attributes"].append(code)
        vals = by_attr.get(code, []) if att else []
        idx = {norm(v["label"]): v for v in vals}
        # renames first, so the renamed value counts as present
        for old, new in (s.get("renames") or {}).items():
            v = idx.get(norm(old))
            if v and norm(new) not in idx:
                print(f"  ~ {code}: '{old}' -> '{new}' (id {v['id']})")
                if not dry:
                    api("PUT", f"/attribute-values/{v['id']}", {"attribute_id": att["id"], "value": v["value"], "label": new})
                v["label"] = new; idx.pop(norm(old), None); idx[norm(new)] = v
                report["renamed"].setdefault(code, []).append([old, new])
        wanted = {norm(x): x for x in s["values"]}
        missing = [x for k, x in wanted.items() if k not in idx]
        for label in missing:
            value = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
            if dry:
                print(f"  + {code}: {label}")
            else:
                r = api("POST", "/attribute-values", {"attribute_id": att["id"], "value": value, "label": label})
                vid = (r.get("data") or {}).get("id")
                if not vid:  # value slug may collide (e.g. 'steel' in two attrs is fine; within one attr it is a dup)
                    r = api("POST", "/attribute-values", {"attribute_id": att["id"], "value": f"{value}-{att['id']}", "label": label})
                    vid = (r.get("data") or {}).get("id")
                print(f"  + {code}: {label} -> {vid}" if vid else f"  ! {code}: {label} FAILED {str(r)[:160]}")
            report["created_values"].setdefault(code, []).append(label)
        extras = [v["label"] for k, v in idx.items() if k not in wanted]
        if extras:
            report["extras"][code] = sorted(extras)
        want_f = s.get("filterable", True)
        if att and att.get("isFilterable") is not None and bool(att.get("isFilterable")) != want_f:
            print(f"  * {code}: isFilterable -> {want_f}")
            if not dry:
                api("PUT", f"/attributes/{att['id']}", {"code": code, "name": att["name"], "isFilterable": want_f, "isVariant": att.get("isVariant", True)})
            report["filterable"][code] = want_f
        elif att and s.get("filterable") is False and not dry:
            # freshly created attributes come back without the flag in the list view; set it explicitly
            api("PUT", f"/attributes/{att['id']}", {"code": code, "name": att["name"], "isFilterable": False, "isVariant": True})
            report["filterable"][code] = False

    live = {x["code"]: x for x in api("GET", "/attributes?forProducts=true").get("data", [])}
    for fid, f in (spec.get("families") or {}).items():
        cur = api("GET", f"/attribute-families/{fid}").get("data") or {}
        ids = [x["id"] for x in cur.get("attributes", [])]
        add = [live[c]["id"] for c in f["add"] if c in live and live[c]["id"] not in ids]
        if add:
            print(f"family {fid} {f['name']}: + {[c for c in f['add'] if c in live and live[c]['id'] in add]}")
            if not dry:
                api("PUT", f"/attribute-families/{fid}", {"name": f["name"], "code": f["code"], "sortOrder": cur.get("sortOrder", int(fid)), "attribute_ids": ids + add})
    json.dump(report, open(os.path.join(CACHE, "sync-attributes-report.json"), "w"), indent=1, ensure_ascii=False)
    print("\n== extras (live values not in the Chewy spec — kept, your call) ==")
    for code, ex in report["extras"].items():
        print(f"  {code}: {', '.join(ex)}")


if __name__ == "__main__":
    main()
