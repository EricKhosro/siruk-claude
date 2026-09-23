#!/usr/bin/env python3
"""Render a contact sheet of candidate images so they can be LOOKED AT (rule 7).

Thumbnails are inlined as data: URIs — headless Chrome will not load file://
images from a file:// page, so a sheet that references them never shows anything.

    scripts/contact-sheet.py out.html found.json [found2.json ...]
    scripts/contact-sheet.py out.html --dir some/folder
"""
import base64, html, json, os, subprocess, sys, tempfile

def thumb(path, px=260):
    d = tempfile.mkdtemp()
    out = os.path.join(d, "t.jpg")
    r = subprocess.run(["sips", "-s", "format", "jpeg", "-Z", str(px), path, "--out", out],
                       capture_output=True)
    p = out if os.path.exists(out) else path
    return base64.b64encode(open(p, "rb").read()).decode()


def main():
    out = sys.argv[1]
    rows = []
    args = sys.argv[2:]
    if "--dir" in args:
        d = args[args.index("--dir") + 1]
        for f in sorted(os.listdir(d)):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                rows.append({"article": f, "name": "", "product_id": "",
                             "images": [{"file": os.path.join(d, f), "w": 0, "h": 0,
                                         "source": "", "why": ""}]})
    else:
        for f in args:
            rows += json.load(open(f))
    cells = []
    for r in rows:
        for i, k in enumerate(r.get("images") or []):
            if not os.path.exists(k["file"]):
                continue
            cells.append(
                f'<figure class="{"lead" if i == 0 else ""}">'
                f'<img src="data:image/jpeg;base64,{thumb(k["file"])}">'
                f'<figcaption><b>{r["article"]}</b> p{r.get("product_id","")} '
                f'{html.escape(str(r.get("name","")))[:40]}<br>{k.get("w")}×{k.get("h")} · '
                f'{html.escape(str(k.get("source","")))}<br>'
                f'<span>{html.escape(str(k.get("why","")))[:70]}</span></figcaption></figure>')
    open(out, "w").write(
        "<!doctype html><meta charset=utf-8><style>body{font:12px -apple-system;background:#fff;margin:8px;"
        "display:flex;flex-wrap:wrap;gap:6px}figure{margin:0;width:200px}"
        "figure.lead img{border:3px solid #1a7}img{width:200px;height:200px;object-fit:contain;"
        "background:#f7f7f7;border:1px solid #ddd}figcaption{font-size:9px;line-height:1.2}"
        "span{color:#888}</style>" + "".join(cells))
    print(f"{len(cells)} images -> {out}")


if __name__ == "__main__":
    main()
