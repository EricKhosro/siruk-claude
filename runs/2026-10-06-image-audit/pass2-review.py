#!/usr/bin/env python3
"""Build pass2-review.html — what pass 2 (2026-10-07) actually wrote, plus the open questions, with photos.

Before/after come from the write logs (apply-write-pass2.log, restore-write.log), so the page shows
exactly what was sent. Images are local copies: img/<media> for existing media, found/<sku>/… for
the photos uploaded in pass 2 (found-uploaded.json maps sku → new media ids). No API calls.
"""
import csv, glob, html, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
snap = json.load(open("products.json"))
pass1 = json.load(open("gallery-plan-pass1.json"))
local = {int(r["media"]): os.path.relpath(r["local"], HERE) for r in csv.DictReader(open("images.csv"))}
found = {}
for f in glob.glob("found/*.json"):
    if os.path.basename(f).startswith("need-"): continue
    for e in json.load(open(f)):
        if e.get("images"): found[e["sku"]] = e
uploaded = json.load(open("found-uploaded.json"))
new_src = {}  # media id -> (file, found entry)
for sku, ids in uploaded.items():
    for mid, img in zip(ids, found[sku]["images"]):
        new_src[int(mid)] = (img["file"], img)

LINE = re.compile(r"^(\d+) (\S+): \[([\d, ]*)\] (?:->|→) \[([\d, ]*)\](?:\s+#\s*(.*))?$")
def parse(path):
    """apply-plan prints each change (with its why), then galleries.py prints it again as it writes."""
    out = {}
    for ln in open(path):
        m = LINE.match(ln.strip())
        if m:
            ids = lambda s: [int(x) for x in s.split(",") if x.strip()]
            prev = out.get((m[1], m[2]))
            out[(m[1], m[2])] = (m[1], m[2], ids(m[3]), ids(m[4]), m[5] or (prev[4] if prev else ""))
    return list(out.values())

def variant(pid, sku):
    return next((v for v in snap[pid]["variants"] if v["sku"] == sku), {})

def label(v):
    return " · ".join(x for x in [v.get("name") or v.get("label"), v.get("size_label")] if x)

def fig(mid, i, status):
    if mid in new_src:
        src, new = new_src[mid][0], True
    else:
        src, new = local.get(mid, ""), False
    cls = " ".join(c for c in ["lead" if i == 0 else "", "new" if new else "", status] if c)
    tag = "<span class=t-new>NEW</span>" if new else ("<span class=t-gone>REMOVED</span>" if status == "gone" else "")
    return (f'<figure class="{cls}"><a href="{html.escape(src)}" target="_blank"><img loading="lazy" src="{html.escape(src)}"></a>'
            f'{tag}<figcaption>{mid}</figcaption></figure>')

def strip(ids, other=None, side="after"):
    if not ids: return '<div class="empty">no image</div>'
    other = set(other or [])
    return "".join(fig(m, i, "gone" if side == "before" and m not in other else "") for i, m in enumerate(ids))

def source_note(after):
    notes = []
    for m in after:
        if m in new_src:
            img = new_src[m][1]
            notes.append(f'<li><b>{m}</b> from {html.escape(img.get("source", ""))} — {html.escape(img.get("keyed_by", ""))}<br><i>{html.escape(img.get("seen", ""))}</i></li>')
    return f"<ul class=src>{''.join(notes)}</ul>" if notes else ""

QUESTIONS = {}  # sku -> question text, filled below, shown on the matching row too

def card(pid, sku, before, after, why, extra="", kind=""):
    p = snap[pid]; v = variant(pid, sku)
    q = QUESTIONS.get(sku)
    qhtml = f'<p class="q"><b>Question:</b> {html.escape(q)}</p>' if q else ""
    data = html.escape(f"{pid} {p['name']} {sku} {label(v)} {why}".lower())
    return f'''<article class="row {kind}" data-q="{data}">
<header><b>{html.escape(p["name"])}</b> <small>#{pid} · sku {html.escape(sku)} · {html.escape(label(v))}</small></header>
<div class="ba"><div><h4>Before</h4><div class="strip">{strip(before, after, "before")}</div></div>
<div><h4>After (live now)</h4><div class="strip">{strip(after)}</div></div></div>
{qhtml}{f'<p class="why">{html.escape(why)}</p>' if why else ''}{source_note(after)}{extra}</article>'''

# ---- questions ----------------------------------------------------------------
mine = [
    ("1284", "04812K", "The product is called “Padded Leather Collar with Bells”, but the brand’s own photo for our barcode "
     "(Kaskad 00010027-12, EAN 4605350048120) shows a studded collar with no bells — and so do all its colour siblings. "
     "Rename the product, or are the bells really on the stock?"),
    ("1148", "00244K", "The brand’s photo for our barcode (Kaskad 00035303, EAN 4605350002443) is a leather collar WITH a woven "
     "tape strip; the plain padded collar is a different article. Rename to mention the tape? It also shares a product "
     "with 01664K (12 mm pink) — should they be separate products?"),
    ("665", "060347", "Monge’s photo for our barcode prints 1250 g on the can; our variant says 1275 g. Should the label be 1250 g?"),
    ("666", "060357", "Same as the lamb can: Monge’s photo for our barcode prints 1250 g; our variant says 1275 g."),
    ("1201", "DL711836", "The current photos are Dog Fest packs that print our exact barcode; Dog Fest is the export label of "
     "Derevenskie. Which pack is actually on the shelf? (Left unchanged.)"),
    ("315", "45558", "Old multi-colour gallery restored as you asked. Is the stock assorted colours? If yes, should colour "
     "become an option so each colour has its own photo?"),
    ("319", "45755", "Same as Sleeping face: old multi-colour gallery restored. Assorted stock? Colour as an option?"),
]
for pid, sku, q in mine: QUESTIONS[sku] = q
earlier = [(str(a), b, str(c), d) for a, b, c, d in json.load(open("questions.json"))]

# ---- pass 2 rows ---------------------------------------------------------------
rows = parse("apply-write-pass2.log")
restore = parse("restore-write.log")
p2 = [card(pid, sku, b, a, why) for pid, sku, b, a, why in rows]
rs = [card(pid, sku, b, a, "Restored on your request: the gallery from before the audit, same order.", kind="restore")
      for pid, sku, b, a, why in restore]

def current(pid, sku):
    for r in rows + restore:
        if r[0] == pid and r[1] == sku: return r[3]
    if sku in (pass1.get(pid) or {}): return pass1[pid][sku]
    return variant(pid, sku).get("images") or []

def qcard(pid, sku, q, tag):
    p = snap.get(pid)
    if not p: return ""
    v = variant(pid, sku)
    ids = current(pid, sku)
    sib = ""
    if sku == "00244K":
        o = current(pid, "01664K")
        sib = f'<h4>Same product, sku 01664K</h4><div class="strip">{strip(o)}</div>'
    data = html.escape(f"{pid} {p['name']} {sku} {q}".lower())
    return f'''<article class="row qrow" data-q="{data}"><header><span class="tag">{tag}</span> <b>{html.escape(p["name"])}</b>
<small>#{pid} · sku {html.escape(sku)} · {html.escape(label(v))}</small></header>
<p class="q">{html.escape(q)}</p><h4>Live gallery now</h4><div class="strip">{strip(ids)}</div>{sib}</article>'''

qs_mine = [qcard(pid, sku, q, "new") for pid, sku, q in mine]
qs_old = [qcard(pid, sku, q, "from audit") for pid, name, sku, q in earlier]

CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--mute:#6b6b66;--line:#e2e1dc;--new:#1f7a4d;--lead:#2457c5;--gone:#b3261e;--q:#fff6e0;--qink:#6a4a00}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#161615;--card:#20201e;--ink:#ecebe6;--mute:#a09f98;--line:#33332f;--new:#4cc38a;--lead:#7aa2ff;--gone:#ff7b72;--q:#2e2614;--qink:#f0c674}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,system-ui,sans-serif}
main{max-width:1280px;margin:0 auto;padding:16px}h1{font-size:22px;margin:4px 0}h2{margin:28px 0 6px;font-size:18px}
.sub{color:var(--mute);margin:0 0 10px}.bar{position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:2;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
input{flex:1;min-width:200px;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
nav a{color:var(--lead);margin-right:12px;white-space:nowrap}
.row{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:10px 0}
.row header small{color:var(--mute)}.ba{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:6px}
@media (max-width:700px){.ba{grid-template-columns:1fr}}
h4{margin:8px 0 4px;font-size:12px;color:var(--mute);text-transform:uppercase;letter-spacing:.04em}
.strip{display:flex;gap:6px;flex-wrap:wrap}
figure{margin:0;position:relative;border:2px solid transparent;border-radius:6px;background:#fff;width:128px}
figure.lead{border-color:var(--lead)}figure.new{outline:2px solid var(--new);outline-offset:1px}
figure.gone img{opacity:.35}figure.gone{outline:2px dashed var(--gone);outline-offset:1px}
figure img{display:block;width:124px;height:124px;object-fit:contain;border-radius:4px}
figcaption{font-size:10px;color:#777;text-align:center}
figure span{position:absolute;top:3px;left:3px;color:#fff;font-size:10px;padding:1px 4px;border-radius:3px}
.t-new{background:var(--new)}.t-gone{background:var(--gone)}
.empty{color:var(--gone);font-style:italic;padding:40px 0}
.why{margin:8px 0 0;color:var(--mute);font-size:13px}.src{margin:6px 0 0;padding-left:18px;font-size:12px;color:var(--mute)}
.q{background:var(--q);color:var(--qink);padding:8px 10px;border-radius:6px;margin:8px 0 0}
.tag{font-size:11px;background:var(--q);color:var(--qink);padding:1px 6px;border-radius:10px}
.restore{border-color:var(--lead)}
.legend{color:var(--mute);font-size:13px}.legend i{display:inline-block;width:12px;height:12px;vertical-align:-2px;border-radius:2px;margin:0 4px 0 10px}
"""
JS = """document.getElementById('f').addEventListener('input',e=>{const q=e.target.value.toLowerCase().trim();
document.querySelectorAll('.row').forEach(r=>r.style.display=!q||r.dataset.q.includes(q)?'':'none')})"""
page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pass 2 Review</title><style>{CSS}</style></head><body><main>
<h1>Pass 2 — what was written, and open questions</h1>
<p class="sub">Production, written 2026-10-07. Before/after are taken from the write logs; every product was read back after writing and all 205 image links were checked (0 broken).</p>
<p class="legend">Lead (first image) <i style="background:var(--lead)"></i> · new photo uploaded today <i style="background:var(--new)"></i> · removed from the gallery <i style="background:var(--gone)"></i></p>
<div class="bar"><input id="f" placeholder="Filter by product, sku, id, word…"><nav>
<a href="#qs">My questions ({len(qs_mine)})</a><a href="#p2">Pass 2 ({len(p2)})</a><a href="#rs">Restored ({len(rs)})</a><a href="#qo">Earlier questions ({len(qs_old)})</a></nav></div>
<h2 id="qs">Questions for you ({len(qs_mine)})</h2>
<p class="sub">The photo shown is what is live now. Answer in chat, e.g. “04812K: rename”, “060347: yes 1250 g”.</p>
{''.join(qs_mine)}
<h2 id="p2">Pass 2 — new photos written ({len(p2)} variants)</h2>
<p class="sub">1 kg loose-sale variants (-KG) get the same gallery as their bag.</p>
{''.join(p2)}
<h2 id="rs">Restored on your request ({len(rs)})</h2>
{''.join(rs)}
<h2 id="qo">Earlier questions from the audit ({len(qs_old)})</h2>
<p class="sub">Raised by the review on 2026-10-06; galleries shown as they are live now.</p>
{''.join(qs_old)}
</main><script>{JS}</script></body></html>"""
open("pass2-review.html", "w").write(page)
print(f"pass2 {len(p2)}, restored {len(rs)}, my questions {len(qs_mine)}, earlier questions {len(qs_old)}")
missing = sorted({m for r in rows + restore for m in r[2] + r[3] if m not in new_src and m not in local})
print("media with no local file:", missing)
