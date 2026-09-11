#!/usr/bin/env python3
"""Store ru + hy for every product using reference/translations.json.

For each product: name from "names"; each <li>/<p> of a variant's texts from
"strings" (exact, whitespace-normalised) or "paragraphs" (by opening phrase).
HTML structure is kept, only the text nodes change. A string with no entry
stays English and is listed at the end — nothing is invented.
Writes through scripts/set-translation.py (one PUT per locale, verified).

    scripts/backfill-translations.py [--only id,id] [--dry-run]
"""
import html, importlib.util, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
T = json.load(open(os.path.join(ROOT, "reference/translations.json")))
LANG = {"ru": 0, "hy": 1}
_spec = importlib.util.spec_from_file_location("tc", os.path.join(ROOT, "scripts/translate-composition.py"))
tc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(tc)
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def api_get(pid):
    env = dict(os.environ, SIRUK_NO_PACE="1", SIRUK_LANG="en")
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", f"/products/{pid}"],
                       capture_output=True, text=True, cwd=ROOT, env=env, timeout=120)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:])["data"]


def ws(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()


def tr_text(text, lang, missing):
    key = ws(text)
    if not key:
        return text
    if key in T["strings"]:
        return T["strings"][key][LANG[lang]]
    for opener, v in T["paragraphs"].items():
        if key.startswith(ws(opener)):
            return v[LANG[lang]]
    # composition / analytical / additive lines: rule-based, term by term
    if key.startswith("<strong>"):
        unk = set()
        out = tc.tr(key, lang, unk)
        if not unk:
            return out
        for u in unk:
            missing.add("TERM: " + u)
        return out
    # a paragraph of several sentences: sentence by sentence through the dictionary
    sents = SENT.split(key)
    if len(sents) > 1:
        outs, ok = [], True
        for sn in sents:
            k2 = ws(sn)
            if k2 in T["strings"]:
                outs.append(T["strings"][k2][LANG[lang]])
            else:
                ok = False; missing.add(k2); outs.append(sn)
        return " ".join(outs) if ok else text
    missing.add(key)
    return text


def tr_html(h, lang, missing):
    if not h:
        return h
    return re.sub(r"(<(li|p)>)(.*?)(</\2>)",
                  lambda m: m.group(1) + tr_text(m.group(3), lang, missing) + m.group(4), h, flags=re.S)


def main():
    only = None
    if "--only" in sys.argv:
        only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
    dry = "--dry-run" in sys.argv
    ids = []
    if only:
        ids = sorted(only)
    else:
        for line in open(os.path.join(CACHE, "products-dump.jsonl")):
            ids.append(json.loads(line)["id"])
    missing, failed, done = set(), [], 0
    for pid in sorted(ids):
        if only and pid not in only:
            continue
        p = api_get(pid)
        for lang in ("ru", "hy"):
            name = T["names"].get(p["name"])
            tr = {"name": name[LANG[lang]] if name else p["name"], "variants": {}}
            if not name:
                missing.add("NAME: " + p["name"])
            for v in p["variants"]:
                tr["variants"][v["sku"]] = {f: tr_html(v.get(f) or "", lang, missing)
                                            for f in ("about_this_item", "ingredient_information", "feeding_instructions")}
            path = os.path.join(CACHE, f"tr-{pid}-{lang}.json")
            json.dump(tr, open(path, "w"), ensure_ascii=False, indent=1)
            if dry:
                continue
            r = subprocess.run([os.path.join(ROOT, "scripts/set-translation.py"), str(pid), lang, path],
                               capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, SIRUK_NO_PACE="1"), timeout=300)
            line = (r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]
            print(line)
            if r.returncode != 0:
                failed.append((pid, lang, line))
        done += 1
    print(f"\nproducts processed: {done}")
    if missing:
        print("strings left in English (no dictionary entry):")
        for m in sorted(missing):
            print("  ", m)
    if failed:
        print("FAILED:", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
