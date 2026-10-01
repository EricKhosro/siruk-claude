#!/usr/bin/env python3
"""Apply reference/translations-attributes.json (ru/hy for attribute names,
value labels and family names). The backend stores them per locale since
2026-09-10; the probe below still guards against a regression.

On 2026-09-10 the admin API kept a single label for attributes, values and
families: a PUT with "locale":"ru" rewrote the English text for every locale.
So this script first PROBES on a throwaway attribute/value (PUT ru, read en);
if English changed, it deletes the throwaway and exits without touching any
real record. Re-run it after the backend team ships per-locale attribute labels.

    scripts/translate-attributes.py [--dry-run] [--probe-only] [--verify-only]
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
T = json.load(open(os.path.join(ROOT, "reference/translations-attributes.json")))


def api(method, path, payload=None, lang=None):
    env = dict(os.environ, SIRUK_NO_PACE="1")
    if lang:
        env["SIRUK_LANG"] = lang
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_trattr.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=120, env=env)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr[-200:]}


def probe():
    a = api("POST", "/attributes", {"code": "zz-locale-probe", "name": "ZZ Probe EN"}).get("data") or {}
    v = api("POST", "/attribute-values", {"attribute_id": a["id"], "value": "zz-probe", "label": "ZZ Probe Value EN"}).get("data") or {}
    api("PUT", f"/attribute-values/{v['id']}", {"attribute_id": a["id"], "value": "zz-probe", "label": "ZZ Probe Value RU", "locale": "ru"})
    api("PUT", f"/attributes/{a['id']}", {"code": "zz-locale-probe", "name": "ZZ Probe RU", "locale": "ru"})
    en_v = (api("GET", f"/attribute-values/{v['id']}", lang="en").get("data") or {}).get("label")
    en_a = (api("GET", f"/attributes/{a['id']}", lang="en").get("data") or {}).get("name")
    api("DELETE", f"/attribute-values/{v['id']}"); api("DELETE", f"/attributes/{a['id']}")
    ok = en_v == "ZZ Probe Value EN" and en_a == "ZZ Probe EN"
    print(f"probe: value en={en_v!r} attribute en={en_a!r} → per-locale {'SUPPORTED' if ok else 'NOT supported (English was overwritten)'}")
    return ok


def main():
    dry = "--dry-run" in sys.argv
    if "--verify-only" in sys.argv:
        verify({x["code"]: x for x in api("GET", "/attributes?forProducts=true").get("data", [])}); return
    if not probe():
        print("refusing to write — the backend would overwrite the English labels. Nothing changed.")
        sys.exit(2)
    if "--probe-only" in sys.argv:
        return
    live = {x["code"]: x for x in api("GET", "/attributes?forProducts=true").get("data", [])}
    bad = []
    for code, att in live.items():
        full = api("GET", f"/attributes/{att['id']}", lang="en").get("data") or {}
        names = T["attributes"].get(code)
        for i, lang in enumerate(("ru", "hy")):
            if names:
                # same body the admin UI sends (snake_case flags)
                body = {"locale": lang, "name": names[i], "code": code, "is_variant": full.get("isVariant", True), "is_filterable": full.get("isFilterable", True)}
                if not dry:
                    api("PUT", f"/attributes/{att['id']}", body)
        for v in full.get("values") or []:
            tr = T["values"].get(code, {}).get(v["label"])
            if not tr:
                bad.append((code, v["label"], "no translation")); continue
            for i, lang in enumerate(("ru", "hy")):
                if dry:
                    continue
                api("PUT", f"/attribute-values/{v['id']}", {"locale": lang, "attribute_id": att["id"], "value": v["value"], "label": tr[i], "color_hex": v.get("color_hex"), "sort_order": v.get("sort_order", 0), "image": (v.get("image") or {}).get("id") if isinstance(v.get("image"), dict) else v.get("image")})
        print(f"{code}: {len(full.get('values') or [])} values {'(dry)' if dry else 'written'}")
    for f in api("GET", "/attribute-families").get("data", []):
        tr = T.get("families", {}).get(f["code"])
        if not tr:
            bad.append(("family", f["code"], "no translation")); continue
        for i, lang in enumerate(("ru", "hy")):
            if not dry:
                api("PUT", f"/attribute-families/{f['id']}", {"locale": lang, "name": tr[i], "code": f["code"]})  # no `attributes` key: the type's rows stay as they are
        print(f"family {f['code']}: {'(dry)' if dry else 'written'}")
    print("problems:", bad if bad else "none")
    if not dry:
        verify(live)


def verify(live):
    """Read every attribute back in en/ru/hy; report anything not matching the table."""
    miss = []
    en_attrs = {}
    for lang in ("en", "ru", "hy"):
        for code, att in live.items():
            full = api("GET", f"/attributes/{att['id']}", lang=lang).get("data") or {}
            if lang == "en":
                en_attrs[code] = full
                continue
            i = 0 if lang == "ru" else 1
            names = T["attributes"].get(code)
            if names and full.get("name") != names[i]:
                miss.append((lang, code, "name", full.get("name")))
            en_labels = {v["id"]: v["label"] for v in en_attrs[code].get("values") or []}
            for v in full.get("values") or []:
                tr = T["values"].get(code, {}).get(en_labels.get(v["id"]))
                if tr and v["label"] != tr[i]:
                    miss.append((lang, code, v["id"], v["label"]))
    # English must be untouched
    for code, full in en_attrs.items():
        if full.get("name") != live[code]["name"]:
            miss.append(("en", code, "name CHANGED", full.get("name")))
    for lang in ("en", "ru", "hy"):
        for f in api("GET", "/attribute-families", lang=lang).get("data", []):
            tr = T.get("families", {}).get(f["code"])
            if lang == "en":
                if tr and f["name"] in tr:
                    miss.append(("en", f["code"], "family name CHANGED", f["name"]))
            elif tr and f["name"] != tr[0 if lang == "ru" else 1]:
                miss.append((lang, f["code"], "family", f["name"]))
    n = sum(len(a.get("values") or []) for a in en_attrs.values())
    print(f"verify: {len(en_attrs)} attributes, {n} values read back in en/ru/hy → {len(miss)} mismatches")
    for m in miss[:40]:
        print("  ", m)


if __name__ == "__main__":
    main()
