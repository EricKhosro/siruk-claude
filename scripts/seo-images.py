#!/usr/bin/env python3
"""Give products a padded 1200×630 SEO / share image (og:image) — never cropped (user, 2026-11-17).

    uv run --no-sync python scripts/seo-images.py <id> [<id> …]            # dry run: renders, writes nothing
    uv run --no-sync python scripts/seo-images.py <id> [<id> …] --apply    # upload to media folder seo/ + set meta_image
    uv run --no-sync python scripts/seo-images.py --sheet <id> …          # also a contact sheet (before | after) to review
    uv run --no-sync python scripts/seo-images.py --categories [<cat id> …] [--apply]   # categories: their own image, padded

Why: a product with no SEO image of its own falls back to the variant's first gallery photo,
mostly tall (688×1200 …), so 1.91:1 share previews (Facebook, Telegram, WhatsApp) cut off the
top and bottom of the pack. This is a stop-gap until the server makes an 'og' variant itself
(developer brief, 2026-11-17).

Per product: the DEFAULT variant's first gallery image (original file, not the webp) →
flatten transparency on white → trim the near-white border already in the photo → scale to fit
529×529, the centre 630×630 square minus an 8% margin (the "safe" layout, user 2026-11-17: Google's
square search thumbnail is cut from the middle, so a wide product must not reach past it) →
centre on white 1200×630 → JPEG q85, progressive. One image works for 1.91:1 share previews and
the square thumbnail; wide products just look smaller in share previews. Uploaded to the media-library folder `seo` with alt = caption = "{Brand} {Name}",
then set as the product's meta_image through a full PUT built by siruk/payload.py (rule 10;
no `meta` is sent, so the meta texts stay as they are). Read back: meta_image must be the new
id and nothing else in the product may change.

The padding takes the photo's own backdrop colour when its four corners agree (category images sit
on a light grey card), else white.

A category's SEO image is its own `image`, padded the same way; a category whose meta_image is
already something else is skipped unless --force.

A product that already has a meta_image is skipped (someone chose it), unless --force.
One SEO image per product: every size's page shares it (the server has one meta_image per product).

Log: .siruk-cache/seo-images/log.jsonl. Rendered files: .siruk-cache/seo-images/<id>.jpg.
Pacing: siruk.client (config.json) per call, the photo download included, plus
product.pause_seconds between products — one call at a time, never parallel.
"""
import argparse, datetime, io, json, os, sys, urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from siruk import client as _client  # noqa: E402
from siruk import config, media, seo  # noqa: E402
from siruk import payload as P  # noqa: E402
from siruk import products  # noqa: E402
from siruk.config import ROOT  # noqa: E402
from siruk.payload import PayloadError  # noqa: E402

from PIL import Image, ImageChops, ImageDraw  # noqa: E402

W, H, MARGIN, QUALITY, TRIM_TOL = 1200, 630, 0.08, 85, 12
FOLDER = "seo"
OUT = os.path.join(ROOT, ".siruk-cache", "seo-images")
LOG = os.path.join(OUT, "log.jsonl")
IGNORE = {"meta_image", "updatedAt", "updated_at"}


# ------------------------------------------------------------------ render ----
def flatten(im):
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return im.convert("RGB")


def background(im, spread=10):
    """The photo's own backdrop: the corners' colour when all four agree (a grey studio card on
    category images), else white. The padding uses it, so the photo has no visible box edge."""
    w, h, k = im.width, im.height, max(1, min(im.width, im.height) // 40)
    patches = [im.crop(b).resize((1, 1), Image.BOX).getpixel((0, 0))
               for b in ((0, 0, k, k), (w - k, 0, w, k), (0, h - k, k, h), (w - k, h - k, w, h))]
    if all(max(c[i] for c in patches) - min(c[i] for c in patches) <= spread for i in range(3)):
        return tuple(round(sum(c[i] for c in patches) / 4) for i in range(3))
    return (255, 255, 255)


def trim(im, bg=(255, 255, 255), tol=TRIM_TOL):
    """Crop away rows/columns that are entirely backdrop. Never touches the product itself."""
    diff = ImageChops.difference(im, Image.new("RGB", im.size, bg))
    box = diff.convert("L").point(lambda p: 255 if p > tol else 0).getbbox()
    return im.crop(box) if box else im


def render(data, w=W, h=H, margin=MARGIN):
    """bytes of any image → (JPEG bytes, info). The whole product fits; its backdrop colour fills the rest."""
    im = Image.open(io.BytesIO(data))
    im.load()
    src = im.size
    im = flatten(im)
    bg = background(im)
    im = trim(im, bg)
    box = min(w, h) * (1 - 2 * margin)          # safe layout: inside the centre h×h square
    s = min(box / im.width, box / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    out = Image.new("RGB", (w, h), bg)
    out.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return buf.getvalue(), {"src": f"{src[0]}x{src[1]}", "fit": f"{im.width}x{im.height}", "scale": round(s, 3),
                            "bg": "#%02x%02x%02x" % bg}


# ------------------------------------------------------------------ source ----
def source_image(p):
    """The default variant's first gallery image → (media id, original url)."""
    vs = p.get("variants") or []
    v = next((x for x in vs if x.get("is_default")), vs[0] if vs else None)
    for cand in ([v] if v else []) + vs:
        for m in cand.get("images_media") or []:
            url = m.get("originalUrl") or m.get("url")
            if url and (m.get("aggregate_type") in (None, "image")):
                return m.get("id"), url
    return None, None


def download(url):
    _client.default().pacer.pace("api")      # same delay as an API call — it is our server too
    req = urllib.request.Request(url, headers={"User-Agent": config.UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in IGNORE}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def log(rec):
    os.makedirs(OUT, exist_ok=True)
    rec["at"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------- write ----
def set_meta_image(pid, before, mid):
    """Full PUT (siruk/payload.py) with meta_image only — no `meta`, so the meta texts are untouched."""
    warns = []
    body = P.put_body(before, warnings=warns)
    body["meta_image"] = mid
    res = products._put(int(pid), before, body, "seo-image", False, warns)
    after = res.after or products.get(pid)
    if after.get("meta_image") != mid:
        raise PayloadError(f"product {pid}: meta_image reads back as {after.get('meta_image')!r}, wanted {mid}")
    if strip(before) != strip(after):
        raise PayloadError(f"product {pid}: meta_image written, but other fields read back different — compare "
                           f".siruk-cache/product-{pid}-before/after.json")
    return after


def run(pid, apply, force):
    p = products.get(pid)
    if not p:
        return {"id": pid, "status": "not found"}
    rec = {"id": pid, "name": p.get("name"), "old_meta_image": p.get("meta_image")}
    if p.get("meta_image") and not force:
        return {**rec, "status": "skipped: has its own SEO image (use --force)"}
    brand = seo.brand_name(p.get("brand_id")) or ""
    src_id, url = source_image(p)
    if not url:
        return {**rec, "status": "skipped: no gallery image"}
    data, info = render(download(url))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{pid}.jpg")
    with open(path, "wb") as f:
        f.write(data)
    rec.update(source_media=src_id, source_url=url, file=path, kb=len(data) // 1024, **info)
    if not apply:
        return {**rec, "status": "dry run"}
    products._snapshot(pid, "before", p)
    name = f"seo-{p.get('slug') or pid}.jpg"
    named = os.path.join(OUT, name)
    with open(named, "wb") as f:
        f.write(data)
    up = media.upload(named, FOLDER, alt=seo.alt(brand, p.get("name") or ""))
    rec["media_id"] = up["id"]
    set_meta_image(pid, p, up["id"])
    return {**rec, "status": "ok"}


# -------------------------------------------------------------- categories ----
CAT_KEEP = ("name", "slug", "parent_id", "image", "featured_image", "complement_category_ids", "list_as_products",
            "meta")


def run_category(c, apply, force):
    """A category's SEO image = its own `image`, padded the same way (user 2026-11-17)."""
    c_ = _client.default()
    cid, img = c["id"], c.get("image")
    rec = {"category": cid, "name": c.get("path"), "old_meta_image": c.get("meta_image")}
    if not img:
        return {**rec, "status": "skipped: no category image"}
    if c.get("meta_image") and c["meta_image"] != img and not force:
        return {**rec, "status": "skipped: has its own SEO image (use --force)"}
    m = (c_.get(f"/medias/{int(img)}") or {}).get("data") or {}
    url = m.get("originalUrl") or m.get("url")
    if not url:
        return {**rec, "status": f"skipped: media {img} has no url"}
    data, info = render(download(url))
    path = os.path.join(OUT, f"cat-{cid}.jpg")
    with open(path, "wb") as f:
        f.write(data)
    rec.update(source_media=img, source_url=url, file=path, kb=len(data) // 1024, **info)
    if not apply:
        return {**rec, "status": "dry run"}
    phrases = json.load(open(os.path.join(ROOT, "reference/category-seo-phrases.json"), encoding="utf-8"))
    alt = (phrases.get(str(cid)) or [c.get("name")])[0]
    named = os.path.join(OUT, f"seo-category-{c['path'].replace('/', '-')}.jpg")
    with open(named, "wb") as f:
        f.write(data)
    up = media.upload(named, FOLDER, alt=alt)
    rec["media_id"] = up["id"]
    cur = (c_.get(f"/categories/{cid}", lang="en") or {}).get("data") or {}
    body = {"name": cur["name"], "slug": cur["slug"], "parent_id": cur.get("parent_id"),
            "list_as_products": bool(cur.get("list_as_products")), "meta_image": up["id"]}
    if cur.get("meta"):
        body["meta"] = cur["meta"]                    # en's own texts, re-sent unchanged
    c_.put(f"/categories/{cid}", body, lang="en")
    back = (c_.get(f"/categories/{cid}", lang="en") or {}).get("data") or {}
    bad = [k for k in CAT_KEEP if back.get(k) != cur.get(k)]
    if back.get("meta_image") != up["id"]:
        bad.append("meta_image")
    if bad:
        raise PayloadError(f"category {cid}: read-back differs on {bad}")
    return {**rec, "status": "ok"}


def sheet(rows, path):
    """Before (the gallery image as is) | after (the SEO image), one row per product."""
    tw, th, pad = 360, 189, 10
    ok = [r for r in rows if r.get("file")]
    if not ok:
        return None
    im = Image.new("RGB", (pad * 3 + 200 + tw, pad + len(ok) * (th + pad)), (235, 235, 235))
    d = ImageDraw.Draw(im)
    for i, r in enumerate(ok):
        y = pad + i * (th + pad)
        try:
            before = flatten(Image.open(io.BytesIO(download(r["source_url"]))))
            before.thumbnail((200, th))
            im.paste(before, (pad, y))
        except Exception:
            d.text((pad, y), "source?", fill=(200, 0, 0))
        after = Image.open(r["file"]).resize((tw, th))
        im.paste(after, (pad * 2 + 200, y))
        d.text((pad * 2 + 204, y + 2), f"{r['id']}", fill=(150, 150, 150))
    im.save(path, "JPEG", quality=85)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", type=int, help="product ids (with --categories: category ids, none = all)")
    ap.add_argument("--categories", action="store_true", help="category SEO images instead of products")
    ap.add_argument("--apply", action="store_true", help="upload + set meta_image (default: dry run)")
    ap.add_argument("--force", action="store_true", help="replace an existing meta_image")
    ap.add_argument("--sheet", action="store_true", help="write a before|after contact sheet")
    a = ap.parse_args()
    rows = []
    if a.categories:
        cats = (_client.default().get("/categories?search=&sortBy=id", lang="en") or {}).get("data") or []
        for c in sorted(cats, key=lambda c: c["id"]):
            if a.ids and c["id"] not in a.ids:
                continue
            try:
                r = run_category(c, a.apply, a.force)
            except Exception as e:
                r = {"category": c["id"], "name": c.get("path"), "status": f"FAILED: {e}"}
            rows.append(r)
            if a.apply:
                log(dict(r))
            print(f"cat {c['id']:<4} {str(c.get('path'))[:40]:<40} {r.get('src', ''):>9} → {r.get('kb', '?')} KB "
                  f"{r.get('bg', '')}  {('media ' + str(r['media_id'])) if r.get('media_id') else ''}  {r['status']}",
                  flush=True)
        sys.exit(1 if any(str(r["status"]).startswith("FAILED") for r in rows) else 0)
    if not a.ids:
        ap.error("give product ids, or --categories")
    for n, pid in enumerate(a.ids):
        if a.apply and n:
            _client.default().pacer.pace("product")   # config.json product.pause_seconds between products
        try:
            r = run(pid, a.apply, a.force)
        except Exception as e:  # one bad product never stops the batch
            r = {"id": pid, "status": f"FAILED: {e}"}
        rows.append(r)
        if a.apply:
            log(dict(r))
        print(f"{pid:<5} {str(r.get('name') or '')[:42]:<42} {r.get('src', ''):>10} → {r.get('kb', '?')} KB  "
              f"{('media ' + str(r['media_id'])) if r.get('media_id') else ''}  {r['status']}", flush=True)
    if a.sheet:
        print("sheet:", sheet(rows, os.path.join(OUT, "sheet.jpg")))
    bad = [r for r in rows if str(r["status"]).startswith("FAILED")]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
