#!/usr/bin/env python3
"""Write ru + hy for every brand (verified per-locale on 2026-09-10).

Policy: the brand NAME stays Latin in every locale — brands are proper nouns
and the Armenian market (hafo.am, the brands' own packs) prints them Latin —
but it is written explicitly per locale so nothing falls back. The SEO meta
description is translated. Slug is owned by `en` and sent unchanged.

    scripts/translate-brands.py [--dry-run]
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
META = {"ru": ("{n}", "Корма и товары для животных {n}"),
        "hy": ("{n}", "{n} ընտանի կենդանիների կեր և պարագաներ")}


def api(method, path, payload=None, lang=None):
    env = dict(os.environ, SIRUK_NO_PACE="1")
    if lang:
        env["SIRUK_LANG"] = lang
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_trbrand.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=120, env=env)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr}


def main():
    dry = "--dry-run" in sys.argv
    bad = []
    for b in api("GET", "/brands?forProducts=true").get("data", []):
        en = api("GET", f"/brands/{b['id']}", lang="en").get("data") or {}
        name = en["name"]
        for lang, (t, d) in META.items():
            body = {"name": name, "slug": en["slug"], "locale": lang,
                    "meta": {"title": t.format(n=name), "description": d.format(n=name)}}
            if en.get("image"):
                body["image"] = en["image"] if isinstance(en["image"], int) else (en["image"].get("id") if isinstance(en["image"], dict) else None)
                if body["image"] is None:
                    body.pop("image")
            if dry:
                print(f"{b['id']:>3} {name:<14} {lang}: {body['meta']['description']}"); continue
            api("PUT", f"/brands/{b['id']}", body)
            got = api("GET", f"/brands/{b['id']}", lang=lang).get("data") or {}
            if got.get("name") != name or (got.get("meta") or {}).get("description") != body["meta"]["description"]:
                bad.append((b["id"], lang, got.get("name"), (got.get("meta") or {}).get("description")))
        en2 = api("GET", f"/brands/{b['id']}", lang="en").get("data") or {}
        if not dry and (en2.get("name") != name or en2.get("image") != en.get("image")):
            bad.append((b["id"], "en-changed!", en2.get("name"), en2.get("image")))
        if not dry:
            print(f"{b['id']:>3} {name:<14} ru/hy ok")
    print("problems:", bad if bad else "none")


if __name__ == "__main__":
    main()
