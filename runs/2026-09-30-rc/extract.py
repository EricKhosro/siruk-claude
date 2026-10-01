#!/usr/bin/env python3
"""Per selected row: the RC page's name, our pack's EAN, images, texts -> extracted.json + barcodes.csv."""
import csv, json, os, re
R = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(f"{R}/rows.json"))
def g(size):
    """'15 kg' -> (15000,1); '12x85 g' -> (85,12); '85 g' -> (85,1)."""
    s = (size or "").lower().replace(",", ".").replace("×", "x")
    m = re.match(r"\s*(?:(\d+)\s*x\s*)?(\d+(?:\.\d+)?)\s*(kg|g)\b", s)
    if not m: return None
    v = float(m.group(2)) * (1000 if m.group(3) == "kg" else 1)
    return (round(v, 1), int(m.group(1) or 1))
out, bc = [], []
for r in rows:
    key = str(r["row"]); page = f"{R}/pages/{key}.json"
    rec = {"row": r["row"], "name_file": r["name_file"]}
    if not os.path.exists(page):
        rec["status"] = "no page"; out.append(rec); continue
    d = json.load(open(page))
    want = (r["pack"]["content"], r["pack"]["pack_count"]) if r.get("pack") else None
    packs = [(p.get("size"), p.get("ean"), g(p.get("size"))) for p in d.get("packs") or []]
    hit = [p for p in packs if p[2] == want]
    alt = f"{R}/pages/{key}mt.json"      # same RC product id on the Malta site (other country domain)
    if not hit and os.path.exists(alt):
        a = json.load(open(alt))
        hit = [(p.get("size"), p.get("ean"), g(p.get("size"))) for p in a.get("packs") or [] if g(p.get("size")) == want]
        if hit:
            d.setdefault("_ean_url", a["_url"])
    # a 12-pack sold as one pack: the page may list only the single 85 g pouch
    single = [p for p in packs if want and p[2] == (want[0], 1)]
    rec.update(title=d.get("title"), url=d["_url"], species=d.get("species"), category=d.get("categoryLabel"),
               sub=(d.get("digitalSubCategory") or {}).get("label"), vet=d.get("isVetProduct"),
               packs=[(a, b) for a, b, _ in packs],
               ean=hit[0][1] if hit else None, ean_url=d.get("_ean_url") or d["_url"],
               ean_note=None if hit else (f"size not on the UK page; single {single[0][0]} EAN {single[0][1]}" if single else "size not on the UK page"),
               images=[i.get("url") for i in d.get("images") or []],
               description=d.get("description"), details=(d.get("details") or {}).get("description"),
               benefits=[(b.get("label"), b.get("description")) for b in d.get("benefits") or []],
               nutrition={(n.get("title") or "").split(".")[-1]: n.get("description") for n in d.get("nutritionalInfo") or []},
               lifestages=d.get("lifestages"), sizes=d.get("petSizeLabels"), needs=d.get("specificNeeds"))
    rec["status"] = "ok" if hit else "check-size"
    out.append(rec)
    bc.append([r["row"], r["name_file"], rec["title"], r["pack"] and f"{r['pack']['pack_count']}x{r['pack']['content']:g} g", rec["ean"] or "", rec["ean_note"] or "", rec["ean_url"] if rec["ean"] else rec["url"]])
json.dump(out, open(f"{R}/extracted.json", "w"), ensure_ascii=False, indent=1)
with open(f"{R}/barcodes.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["file_row", "name_in_file", "rc_title", "pack", "ean", "note", "source_url"]); w.writerows(bc)
for x in out:
    print(x["row"], x["status"], "|", x["name_file"], "->", x.get("title"), "|", x.get("ean") or x.get("ean_note"), "|", x.get("packs"))
