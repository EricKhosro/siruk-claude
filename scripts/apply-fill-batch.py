#!/usr/bin/env python3
"""Apply a batch of gap cards or translation files the safe way: backup → check → write → verify.

    scripts/apply-fill-batch.py cards --run runs/<date>/fill [--only 1,2,3] [--dry-run]
    scripts/apply-fill-batch.py translations --run runs/<date>/fill [--only …] [--dry-run]

cards:        products that have cards in <run>/gapcards/ and no HOLD in a fill-gaps.py dry run.
              Each is backed up (en/ru/hy → <run>/backup/), written with fill-gaps.py --apply, then
              checked with verify-fill.py. A product whose verify fails is listed loudly.
translations: <run>/translations/<pid>-<ru|hy>.json files (set-translation.py's shape). Each product is
              backed up, set-translation.py is run per locale, and the result is re-read: every
              translated field must now differ from the English (else it is reported).
Writes <run>/apply-log.csv (product, step, result) and prints a summary.
"""
import csv, json, os, re, subprocess, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT, **kw)


def get(pid, lang):
    env = dict(os.environ)
    if lang != "en":
        env["SIRUK_LANG"] = lang
    r = sh([os.path.join(ROOT, "scripts/api.sh"), "GET", f"/products/{pid}"], env=env)
    return json.loads(r.stdout[r.stdout.find("{"):])


def backup(run, pid):
    d = os.path.join(run, "backup")
    os.makedirs(d, exist_ok=True)
    for lang in ("en", "ru", "hy"):
        path = os.path.join(d, f"{pid}-{lang}.json")
        if not os.path.exists(path):          # keep the FIRST backup: the true "before"
            json.dump(get(pid, lang), open(path, "w"), ensure_ascii=False)
    return d


def plain(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")).strip()


def main(argv):
    mode = argv[0]
    run = os.path.join(ROOT, argv[argv.index("--run") + 1])
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
    dry = "--dry-run" in argv
    log = csv.writer(open(os.path.join(run, "apply-log.csv"), "a", newline="", encoding="utf-8"))
    results = defaultdict(list)
    if mode == "cards":
        cards = [json.load(open(os.path.join(run, "gapcards", f))) for f in os.listdir(os.path.join(run, "gapcards"))
                 if f.endswith(".json")]
        pids = sorted({str(c["product_id"]) for c in cards if not only or str(c["product_id"]) in only}, key=int)
        check = sh([sys.executable, "scripts/fill-gaps.py", "--run", run, "--only", ",".join(pids)])
        held = {m.group(1) for m in re.finditer(r"^HOLD (\d+)/", check.stdout, re.M)}
        ready = [p for p in pids if p not in held]
        print(f"{len(pids)} products with cards, {len(held)} with a held card (skipped whole), {len(ready)} ready")
        for line in check.stdout.splitlines():
            if line.startswith("HOLD"):
                print("  " + line)
        if dry:
            return
        for pid in ready:
            bdir = backup(run, pid)
            r = sh([sys.executable, "scripts/fill-gaps.py", "--run", run, "--only", pid, "--apply"])
            failed = "FAIL" in r.stdout
            v = sh([sys.executable, "scripts/verify-fill.py", "--backup", bdir, pid])
            ok = not failed and v.returncode == 0
            results["ok" if ok else "PROBLEM"].append(pid)
            log.writerow([pid, "cards", "ok" if ok else "PROBLEM: " + (r.stdout + v.stdout)[-300:]])
            if not ok:
                print(f"PROBLEM {pid}\n{r.stdout[-500:]}\n{v.stdout[-800:]}")
    elif mode == "translations":
        tdir = os.path.join(run, "translations")
        files = defaultdict(dict)
        for f in os.listdir(tdir):
            m = re.fullmatch(r"(\d+)-(ru|hy)\.json", f)
            if m and (not only or m.group(1) in only):
                files[m.group(1)][m.group(2)] = os.path.join(tdir, f)
        print(f"{len(files)} products with translation files")
        if dry:
            return
        for pid, locs in sorted(files.items(), key=lambda x: int(x[0])):
            backup(run, pid)
            en = get(pid, "en")["data"]
            ens = {str(v["sku"]): v for v in en["variants"]}
            problems = []
            for lang, path in locs.items():
                r = sh([sys.executable, "scripts/set-translation.py", pid, lang, path])
                if r.returncode:
                    problems.append(f"{lang}: {r.stderr.strip()[-200:]}")
                    continue
                want = json.load(open(path))
                now = get(pid, lang)["data"]
                nows = {str(v["sku"]): v for v in now["variants"]}
                if want.get("name") and now["name"] != want["name"]:
                    problems.append(f"{lang} name not stored")
                for sku, fields in (want.get("variants") or {}).items():
                    for k in fields:
                        if plain((nows.get(sku) or {}).get(k)) in ("", plain((ens.get(sku) or {}).get(k))):
                            problems.append(f"{lang} {sku} {k} still English/empty")
            results["ok" if not problems else "PROBLEM"].append(pid)
            log.writerow([pid, "translations", "ok" if not problems else "PROBLEM: " + "; ".join(problems)[:300]])
            if problems:
                print(f"PROBLEM {pid}: " + "; ".join(problems))
    print(f"\nok {len(results['ok'])}, problems {len(results['PROBLEM'])} {results['PROBLEM']}")


if __name__ == "__main__":
    main(sys.argv[1:])
