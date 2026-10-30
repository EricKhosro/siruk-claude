#!/usr/bin/env python3
"""Write reviewed gap cards through PUT /products/bulk (siruk-web e67f9c19), en/ru/hy in one call.

    scripts/fill-gaps-bulk.py --run runs/<date>/fill --only 1,2,3 [--chunk 25] [--dry-run]

Same checks and the same "only EMPTY fields (or a provably non-English one in replace_wrong)" rule as
fill-gaps.py, whose check() it reuses. Per chunk of products:
  1. back up each product in en/ru/hy (<run>/backup/<id>-<lang>.json, the first backup is kept);
  2. check every card against the fresh en record (a held card skips its whole product);
  3. upload new photos (upload-media.sh, MEDIA_DIR=products/<brand-slug>/<type>), new first, earlier
     non-hafo photos kept after them, hafo placeholders and the card's drop_existing removed;
  4. build each body with siruk_payload.put_body (the full product, every variant with its id, since the
     bulk update replaces variants like a single PUT does) and set the new texts as {en, ru, hy}
     maps, so other locales of other fields are untouched;
  5. one PUT /products/bulk per chunk; per-item results are read (a failed item is reported, the
     rest stand);
  6. each updated product is verified with verify-fill.py against its backup.
Every written field goes to <run>/fill-log.csv with its source url.
"""
import csv, importlib.util, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import PayloadError, api, put_body  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(ROOT, "scripts", f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


fg = load("fill-gaps")
ag = load("apply-gap-images")
TEXTS = fg.TEXTS


def get(pid, lang):
    env = dict(os.environ)
    if lang != "en":
        env["SIRUK_LANG"] = lang
    r = subprocess.run(["bash", os.path.join(ROOT, "scripts/api.sh"), "GET", f"/products/{pid}"],
                       capture_output=True, text=True, cwd=ROOT, env=env)
    return json.loads(r.stdout[r.stdout.find("{"):])


def upload(url, media_dir):
    r = subprocess.run([os.path.join(ROOT, "scripts/upload-media.sh"), url], capture_output=True, text=True,
                       cwd=ROOT, env=dict(os.environ, MEDIA_DIR=media_dir), timeout=900)
    last = (r.stdout.strip().splitlines() or [""])[-1]
    return int(last) if re.fullmatch(r"\d+", last) else None


def main(argv):
    run = os.path.join(ROOT, argv[argv.index("--run") + 1])
    only = [p for p in argv[argv.index("--only") + 1].split(",") if p] if "--only" in argv else None
    chunk = int(argv[argv.index("--chunk") + 1]) if "--chunk" in argv else 25
    dry = "--dry-run" in argv
    cards = {}
    for f in os.listdir(os.path.join(run, "gapcards")):
        if f.endswith(".json"):
            c = json.load(open(os.path.join(run, "gapcards", f)))
            cards.setdefault(str(c["product_id"]), []).append(c)
    pids = [p for p in (only or sorted(cards, key=int)) if p in cards]
    bdir = os.path.join(run, "backup")
    os.makedirs(bdir, exist_ok=True)
    log_path = os.path.join(run, "fill-log.csv")
    new_log = not os.path.exists(log_path)
    logf = open(log_path, "a", newline="", encoding="utf-8")
    log = csv.writer(logf)
    if new_log:
        log.writerow(["product_id", "variant_id", "sku", "field", "source_kind", "source_url", "status"])
    hafo = ag.hafo_ids()
    totals = {"products": 0, "held": 0, "failed": 0, "verified": 0, "problems": []}
    for start in range(0, len(pids), chunk):
        part = pids[start:start + chunk]
        items, plans_by_pid = [], {}
        for pid in part:
            for lang in ("en", "ru", "hy"):
                path = os.path.join(bdir, f"{pid}-{lang}.json")
                if not os.path.exists(path):
                    json.dump(get(pid, lang), open(path, "w"), ensure_ascii=False)
            live = get(pid, "en")["data"]
            plans, held = {}, False
            for c in cards[pid]:
                plan, kept, errs = fg.check(c, run, live)
                if errs:
                    print(f"HOLD {pid}/{c['variant_id']}: " + "; ".join(errs))
                    held = True
                elif plan:
                    plans[c["variant_id"]] = (c, plan)
            if held:
                totals["held"] += 1
                continue
            if not plans:
                continue
            if dry:
                print(f"PLAN {pid}: " + "; ".join(f"{v}: {','.join(p)}" for v, (c, p) in plans.items()))
                continue
            try:
                body = put_body(live)
            except PayloadError as e:
                print(f"FAIL {pid} body: {e}")
                totals["failed"] += 1
                continue
            mdir = fg.media_dir(live)
            ok = True
            for bv in body["variants"]:
                cp = plans.get(bv.get("id"))
                if not cp:
                    continue
                c, plan = cp
                if plan.get("_images"):
                    new_ids = [upload(i["url"], mdir) for i in plan["_images"]]
                    if None in new_ids:
                        print(f"FAIL {pid}/{bv['id']}: a photo did not upload")
                        ok = False
                        break
                    drop = set(plan.get("_drop") or []) | hafo
                    bv["images"] = new_ids + [i for i in bv.get("images") or [] if i not in drop and i not in new_ids]
                for k in TEXTS:
                    if k in plan:
                        bv[k] = {"en": plan[k], "ru": c["translations"]["ru"][k], "hy": c["translations"]["hy"][k]}
                if plan.get("attribute_values"):
                    bv["attribute_values"] = {**(bv.get("attribute_values") or {}), **plan["attribute_values"]}
                for k in ("measure_type", "content", "pack_count"):
                    if k in plan:
                        bv[k] = plan[k]
            if not ok:
                totals["failed"] += 1
                continue
            items.append({"id": int(pid), **body})
            plans_by_pid[pid] = plans
        if dry or not items:
            continue
        res = api("PUT", "/products/bulk", {"products": items})
        print(f"chunk {start // chunk + 1}: {res.get('summary')}")
        for r in res.get("data") or []:
            pid = str(items[r["index"]]["id"])
            if r.get("status") != "updated":
                totals["failed"] += 1
                print(f"FAIL {pid}: {json.dumps(r.get('errors'), ensure_ascii=False)[:400]}")
                continue
            totals["products"] += 1
            v = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/verify-fill.py"), "--backup", bdir, pid],
                               capture_output=True, text=True, cwd=ROOT)
            if v.returncode == 0:
                totals["verified"] += 1
            else:
                totals["problems"].append(pid)
                print(f"VERIFY PROBLEM {pid}\n{v.stdout[-600:]}")
            for vid, (c, plan) in plans_by_pid[pid].items():
                for k in plan:
                    log.writerow([pid, vid, c["sku"], k, c["source"].get("kind"), c["source"].get("url"),
                                  "written" if v.returncode == 0 else "VERIFY PROBLEM"])
            logf.flush()
        subprocess.run([os.path.join(ROOT, "scripts/pace.sh"), "product"], cwd=ROOT)
    print(f"\nupdated {totals['products']}, verified {totals['verified']}, held {totals['held']}, "
          f"failed {totals['failed']}, verify problems {totals['problems']}")


if __name__ == "__main__":
    main(sys.argv[1:])
