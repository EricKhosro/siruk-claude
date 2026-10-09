#!/usr/bin/env python3
"""Build preview.html — before/after of every gallery change, from local files only (no API).

Pass 1 = already written to production on 2026-10-06 (gallery-plan.json from that run + the 3 pilots).
Pass 2 = NOT written: sourced photos (found/*.json, status found) put first, then the plan gallery.
Images are the local copies: img/<media>.<ext> for existing media, found/<sku>/... for new files.

    preview.py   →  preview.html (open it from this folder; paths are relative)
"""
import csv, glob, html, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
snap = json.load(open("products.json"))
local = {}
for r in csv.DictReader(open("images.csv")):
    local[int(r["media"])] = os.path.relpath(r["local"], HERE)
plan = {}
for f in sorted(glob.glob("plan-out/*.json")):
    plan.update(json.load(open(f)))
pass1 = json.load(open("gallery-plan-pass1.json"))  # pass 1 as written 2026-10-06 (apply-plan.py overwrites gallery-plan.json)
# The 3 pilots were written before the batch run; their target is the plan gallery.
for pid in ("353", "1125", "1126"):
    for sku, d in (plan.get(pid) or {}).items():
        before = next((v["images"] for v in snap[pid]["variants"] if v["sku"] == sku), None)
        if d.get("gallery") and [int(m) for m in d["gallery"]] != [int(m) for m in before or []]:
            pass1.setdefault(pid, {})[sku] = [int(m) for m in d["gallery"]]

found = {}
for f in sorted(glob.glob("found/*.json")):
    if os.path.basename(f).startswith("need-"): continue
    for e in json.load(open(f)):
        if e.get("status") == "found" and e.get("images"):
            found[e["sku"]] = e

def variant(pid, sku):
    return next((v for v in snap[pid]["variants"] if v["sku"] == sku), {})

def label(v):
    return " · ".join(x for x in [v.get("name") or v.get("label"), v.get("size_label")] if x)

def thumb(src, cls=""):
    return f'<a href="{html.escape(src)}" target="_blank"><img loading="lazy" class="{cls}" src="{html.escape(src)}"></a>'

def strip(items):
    if not items: return '<div class="empty">no image</div>'
    out = []
    for i, (src, new) in enumerate(items):
        cls = ("lead " if i == 0 else "") + ("new" if new else "")
        out.append(f'<figure class="{cls}">{thumb(src)}{"<span>NEW</span>" if new else ""}</figure>')
    return "".join(out)

def media_items(ids):
    return [(local.get(int(m), ""), False) for m in ids]

def row(pid, sku, before, after, note, kind):
    p = snap[pid]; v = variant(pid, sku)
    search = html.escape(f"{pid} {p['name']} {sku} {label(v)}".lower())
    return f'''<article class="row {kind}" data-q="{search}">
  <header><b>{html.escape(p["name"])}</b> <small>#{pid} · sku {html.escape(sku)} · {html.escape(label(v))}</small></header>
  <div class="ba"><div><h4>Before</h4><div class="strip">{strip(before)}</div></div>
  <div><h4>After</h4><div class="strip">{strip(after)}</div></div></div>
  {f'<p class="note">{note}</p>' if note else ''}
</article>'''

# ---- pass 2 (pending) -------------------------------------------------------
p2, p2_missing = [], []
for pid, by in plan.items():
    for sku, d in by.items():
        base = sku[:-3] if sku.endswith("-KG") else sku
        src = by.get(base, d)
        v = variant(pid, sku)
        if not v: continue
        cur = pass1.get(pid, {}).get(sku) or v.get("images") or []
        gal = [int(m) for m in src.get("gallery") or []]
        notes = []
        if src.get("question"): notes.append("<b>Question:</b> " + html.escape(src["question"]))
        if base in found:
            e = found[base]
            new = [(i["file"], True) for i in e["images"]]
            after = new + media_items(gal)
            for i in e["images"][:1]:
                notes.append(f'<b>New lead from</b> {html.escape(i.get("source",""))} — keyed by {html.escape(i.get("keyed_by",""))}. Seen: {html.escape(i.get("seen",""))}')
            if e.get("caveat"): notes.append("<b>Caveat:</b> " + html.escape(e["caveat"]))
            if src.get("hold"):
                p2_missing.append(row(pid, sku, media_items(cur), media_items(cur), "<b>Held:</b> " + html.escape(src["hold"]), "hold")); continue
            p2.append(row(pid, sku, media_items(cur), after, "<br>".join(notes), "pending"))
        elif src.get("need") and not gal:
            notes.insert(0, "<b>Still needs a photo:</b> " + html.escape(src["need"]))
            p2_missing.append(row(pid, sku, media_items(cur), media_items(cur), "<br>".join(notes), "missing"))

# ---- pass 1 (live) ----------------------------------------------------------
p1 = []
for pid, by in pass1.items():
    for sku, gal in by.items():
        v = variant(pid, sku)
        d = (plan.get(pid) or {}).get(sku) or (plan.get(pid) or {}).get(sku[:-3]) or {}
        note = html.escape(d.get("why") or "")
        if d.get("question"): note += "<br><b>Question:</b> " + html.escape(d["question"])
        p1.append(row(pid, sku, media_items(v.get("images") or []), media_items(gal), note, "done"))

CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--mute:#6b6b66;--line:#e2e1dc;--new:#1f7a4d;--lead:#2457c5;--warn:#9a5b00}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#161615;--card:#20201e;--ink:#ecebe6;--mute:#a09f98;--line:#33332f;--new:#4cc38a;--lead:#7aa2ff;--warn:#e0a24a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,system-ui,sans-serif}
main{max-width:1280px;margin:0 auto;padding:16px}h1{font-size:22px;margin:4px 0}h2{margin:28px 0 8px;font-size:18px}
.sub{color:var(--mute);margin:0 0 12px}.bar{position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:2;display:flex;gap:8px;flex-wrap:wrap}
input{flex:1;min-width:200px;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
nav a{color:var(--lead);margin-right:12px}
.row{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:10px 0}
.row header small{color:var(--mute)}.ba{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:6px}
@media (max-width:700px){.ba{grid-template-columns:1fr}}
h4{margin:0 0 4px;font-size:12px;color:var(--mute);text-transform:uppercase;letter-spacing:.04em}
.strip{display:flex;gap:6px;flex-wrap:wrap}figure{margin:0;position:relative;border:2px solid transparent;border-radius:6px;background:#fff}
figure.lead{border-color:var(--lead)}figure.new{outline:2px solid var(--new);outline-offset:1px}
figure img{display:block;width:120px;height:120px;object-fit:contain;border-radius:4px}
figure span{position:absolute;top:3px;left:3px;background:var(--new);color:#fff;font-size:10px;padding:1px 4px;border-radius:3px}
.empty{color:var(--warn);font-style:italic;padding:40px 0}.note{margin:8px 0 0;color:var(--mute);font-size:13px}.note b{color:var(--ink)}
.legend{color:var(--mute);font-size:13px}.legend i{display:inline-block;width:12px;height:12px;vertical-align:-2px;border-radius:2px;margin:0 4px 0 10px}
"""
JS = """document.getElementById('q').addEventListener('input',e=>{const q=e.target.value.toLowerCase().trim();
document.querySelectorAll('.row').forEach(r=>r.style.display=!q||r.dataset.q.includes(q)?'':'none')})"""
page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gallery Fix Preview</title><style>{CSS}</style></head><body><main>
<h1>Product photo fix — before / after</h1>
<p class="sub">Production catalogue, image audit 2026-10-06. Built from local copies only — nothing on this page has been sent to the site.</p>
<p class="legend">Lead image (first in gallery) <i style="background:var(--lead)"></i> · new photo, not uploaded yet <i style="background:var(--new)"></i></p>
<div class="bar"><input id="q" placeholder="Filter by product, sku, id…"><nav><a href="#p2">Pass 2 · pending ({len(p2)})</a><a href="#miss">Still missing ({len(p2_missing)})</a><a href="#p1">Pass 1 · live ({len(p1)})</a></nav></div>
<h2 id="p2">Pass 2 — new photos, waiting for your OK ({len(p2)} variants)</h2>
<p class="sub">Each new photo was opened and checked against the variant (brand, recipe, colour, printed size).</p>
{''.join(p2)}
<h2 id="miss">Still missing a correct photo ({len(p2_missing)} variants) — left unchanged</h2>
{''.join(p2_missing)}
<h2 id="p1">Pass 1 — already live since 2026-10-06 ({len(p1)} variants)</h2>
<p class="sub">Wrong images removed and leads reordered, using only images that were already on the site.</p>
{''.join(p1)}
</main><script>{JS}</script></body></html>"""
open("preview.html", "w").write(page)
print(f"pass2 pending {len(p2)}, still missing {len(p2_missing)}, pass1 live {len(p1)}")
missing_files = [m for by in pass1.values() for g in by.values() for m in g if int(m) not in local]
print("media without local file:", missing_files[:10])
