#!/usr/bin/env python3
"""Apply a reviewed corrections plan (renames, labels, attributes, sizes, text replacements) via PUT /products/bulk.

    scripts/apply-corrections.py runs/<date>/corrections/plan.json [--dry-run] [--only 327,331]

plan.json:
  {"renames":  [{"product_id": 327, "name": {"en": "…", "ru": "…", "hy": "…"}, "why": "evidence"}],
   "variants": [{"product_id": 679, "variant_id": 821, "why": "evidence",
                 "label": "Beef & Liver 415 g",                     # the variant name (single-language)
                 "attributes": {"flavor": "Beef"},                  # code → value label; replaces that attribute (null removes it)
                 "size": {"measure_type": "count", "content": 1, "pack_count": 1},
                 "texts": {"ingredient_information": {"en": "…", "ru": "…", "hy": "…"}}}]}
These are data fixes the user delegated to us (2026-10-12). Every change carries its evidence in "why".
Per product: backup en/ru/hy (<plan dir>/backup/), fresh GET → siruk_payload.put_body → the listed changes
only → one bulk PUT per chunk → re-read and check each change landed → <plan dir>/applied.csv.
"""
import csv, json, os, re, subprocess, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import PayloadError, api, attributes, put_body  # noqa: E402

MENU = json.load(open(os.path.join(ROOT, "reference", "attribute-values.json")))


def get(pid, lang):
    env = dict(os.environ)
    if lang != "en":
        env["SIRUK_LANG"] = lang
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", f"/products/{pid}"],
                       capture_output=True, text=True, cwd=ROOT, env=env)
    return json.loads(r.stdout[r.stdout.find("{"):])


def plain(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")).strip()


def main(argv):
    plan_path = argv[0]
    d = json.load(open(plan_path))
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
    dry = "--dry-run" in argv
    base = os.path.dirname(plan_path)
    bdir = os.path.join(base, "backup")
    os.makedirs(bdir, exist_ok=True)
    amap = attributes()
    by = defaultdict(lambda: {"rename": None, "variants": []})
    for r in d.get("renames", []):
        by[str(r["product_id"])]["rename"] = r
    for v in d.get("variants", []):
        by[str(v["product_id"])]["variants"].append(v)
    pids = [p for p in by if not only or p in only]
    out = csv.writer(open(os.path.join(base, "applied.csv"), "a", newline="", encoding="utf-8"))
    items, checks = [], {}
    for pid in pids:
        for lang in ("en", "ru", "hy"):
            path = os.path.join(bdir, f"{pid}-{lang}.json")
            if not os.path.exists(path):
                json.dump(get(pid, lang), open(path, "w"), ensure_ascii=False)
        live = get(pid, "en")["data"]
        try:
            body = put_body(live)
        except PayloadError as e:
            print(f"FAIL {pid} body: {e}")
            continue
        want = []
        job = by[pid]
        if job["rename"]:
            body["name"] = job["rename"]["name"]
            want.append(("name", None, job["rename"]["name"]))
        vmap = {bv.get("id"): bv for bv in body["variants"]}
        bad = False
        for v in job["variants"]:
            bv = vmap.get(v["variant_id"])
            if bv is None:
                print(f"FAIL {pid}: variant {v['variant_id']} not on the product")
                bad = True
                break
            if "label" in v:
                bv["name"] = v["label"]
                want.append(("label", v["variant_id"], v["label"]))
            for code, label in (v.get("attributes") or {}).items():
                if label is None:                      # remove an unsupported value
                    (bv.get("attribute_values") or {}).pop(str(amap[code]["id"]), None)
                    want.append(("attr-removed", v["variant_id"], code))
                    continue
                vid = (MENU.get(code) or {}).get("values", {}).get(label)
                if vid is None:
                    print(f"FAIL {pid}: '{label}' is not a value of {code}")
                    bad = True
                    break
                bv.setdefault("attribute_values", {})[str(amap[code]["id"])] = [vid]
                want.append(("attr", v["variant_id"], (code, label)))
            for k, val in (v.get("size") or {}).items():
                bv[k] = val
            if v.get("size"):
                want.append(("size", v["variant_id"], v["size"]))
            for k, m in (v.get("texts") or {}).items():
                bv[k] = m
                want.append(("text", v["variant_id"], (k, m)))
        if bad:
            continue
        if dry:
            print(f"PLAN {pid}: " + "; ".join(f"{w[0]}{'/' + str(w[1]) if w[1] else ''}" for w in want))
            continue
        items.append({"id": int(pid), **body})
        checks[pid] = (want, job)
    for i in range(0, len(items), 25):
        part = items[i:i + 25]
        res = api("PUT", "/products/bulk", {"products": part})
        print(f"chunk {i // 25 + 1}: {res.get('summary')}")
        for r in res.get("data") or []:
            pid = str(part[r["index"]]["id"])
            if r.get("status") != "updated":
                print(f"FAIL {pid}: {json.dumps(r.get('errors'), ensure_ascii=False)[:300]}")
                continue
            want, job = checks[pid]
            now = {lang: get(pid, lang)["data"] for lang in ("en", "ru", "hy")}
            problems = []
            for kind, vid, val in want:
                vs = {lang: {x["id"]: x for x in now[lang]["variants"]} for lang in now}
                if kind == "name":
                    problems += [f"name {l}" for l in ("en", "ru", "hy") if now[l]["name"] != val[l]]
                elif kind == "label" and vs["en"][vid].get("name") != val:
                    problems.append(f"label {vid}")
                elif kind == "attr":
                    labs = {(x["attributeName"], x["label"]) for x in vs["en"][vid].get("attribute_value_labels") or []}
                    if val[1] not in {lbl for _, lbl in labs}:
                        problems.append(f"attr {vid} {val}")
                elif kind == "attr-removed":
                    names = {x["attributeName"].lower().replace(" ", "-") for x in vs["en"][vid].get("attribute_value_labels") or []}
                    if val in names:
                        problems.append(f"attr {vid} {val} still set")
                elif kind == "size" and float(vs["en"][vid].get("content") or 0) != float(val["content"]):
                    problems.append(f"size {vid}")
                elif kind == "text":
                    k, m = val
                    problems += [f"text {vid} {k} {l}" for l in ("en", "ru", "hy") if plain(vs[l][vid].get(k)) != plain(m[l])]
            whys = [job["rename"]["why"]] if job["rename"] else []
            whys += [v["why"] for v in job["variants"]]
            out.writerow([pid, "; ".join(f"{w[0]}" for w in want), " | ".join(dict.fromkeys(whys)),
                          "ok" if not problems else "PROBLEM: " + ", ".join(problems)])
            print(f"{'ok' if not problems else 'PROBLEM'} {pid}" + (f": {problems}" if problems else ""))
        subprocess.run([os.path.join(ROOT, "scripts/pace.sh"), "product"], cwd=ROOT)


if __name__ == "__main__":
    main(sys.argv[1:])
