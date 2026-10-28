#!/usr/bin/env python3
"""Give every image in the media library a real `alt` and `caption` (SEO, user 2026-10-27).

    scripts/set-media-alt.py --dry-run                 # plan the whole library, write the plan CSV, no writes
    scripts/set-media-alt.py --ids 16954 10222 …       # write just these images (plan computed first)
    scripts/set-media-alt.py --all                     # write every planned image (resumable)
    … --plan runs/<date>/media-alt-plan.csv            # where the plan goes (default runs/<today>/)
    … --refresh                                        # re-fetch the sources even if cached today

Every image gets alt = caption = one English text (the fields are single-language, ≤ 255 chars),
overwriting what is there (today: the filename slug). Text by where the image is used, first match wins:
  product   in a live product's gallery (catalogue export `image_ids`) → "{Brand} {Product name}"
            (product names never carry the brand). One image in several products: the product whose
            not discontinued, then whose brand slug matches the image's products/<brand-slug>/ folder,
            then the lowest product id;
            the others are listed as conflicts.
  logo      a brand's logo (GET /brands `image`)                       → "{Brand} logo"
  category  a category's image / featured_image / meta_image          → "{Pet} {Category}" for a
            non-root category ("Cat Dry Food"), the bare name for a root ("Dog")
  banner    the home page banners, promotions' home-hero files, blog-category / campaign banners →
            the banner's readable file name without device/language tokens + " banner"
  page      a titled item on a page (home loyalty tiles, about-us features, blog categories …)
            → that item's title / name; the home page's SEO image → the home meta title
  filename  anything else (unused images included): the file name made readable — extension and
            trailing codes/ids dropped, hyphens/underscores → spaces, title case, brand names spelled
            as in the live brand list
  unresolved  even the file name gives nothing readable (Trixie "PHO_PRO_CLIP_34843-5…", UUIDs,
            bare article numbers) → not written, listed in the plan.

A write is skipped when alt and caption already equal the target. PUT /medias/<id> {alt, caption}
changes only those two fields (MediaController::update checks has()); each write is read back and
alt, caption, filename, directory and originalUrl are compared. Pacing: the siruk client
(config.json `request`). Resumable: a write run re-fetches the library first, so an interrupted
--all just runs again and skips what already matches. Every write (old values, new value, read-back
result) is appended to .siruk-cache/media-alt/log.jsonl.
"""
import argparse, csv, datetime, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from siruk import client as _client  # noqa: E402
from siruk import export as _export  # noqa: E402

CACHE = os.path.join(ROOT, ".siruk-cache", "media-alt")
LOG = os.path.join(CACHE, "log.jsonl")
TYPES = "image/jpeg,image/png,image/webp,image/svg%2Bxml,image/gif"
MAX = 255

NOISE = {"jpg", "jpeg", "png", "webp", "gif", "svg", "avif", "downloadasjpg", "copy", "final", "img",
         "image", "photo", "pic", "main", "views", "view", "sall", "awk", "pho", "pro", "pac", "det",
         "clip", "set", "gra", "ge", "catalog", "product", "upload", "working", "file", "wm", "st",
         "desktop", "mobile", "en", "gb", "ru", "hy", "am", "es", "fr", "nl", "pt", "it", "de", "mv",
         "x", "y", "e", "enhance", "the", "quality", "davinci", "ita", "ger", "all", "eng", "fra", "spa",
         "por", "group", "cv", "cig", "tsig", "eretailkit", "page", "norm", "pt"}
BANNER_DROP = {"desktop", "mobile", "hy", "ru", "en", "am", "banner", "banners"}
ALIASES = {"rc": "Royal Canin"}   # brand short forms seen in file names
SMALL = {"and", "or", "of", "on", "a", "an", "the", "with", "for", "in", "to", "at", "by", "con", "e"}


def log(msg):
    print(msg, file=sys.stderr)


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")


def clip(text):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= MAX:
        return text
    cut = text[:MAX + 1].rsplit(" ", 1)[0]
    return cut[:MAX].rstrip(" ,;-")


# ------------------------------------------------------------------ sources ----
def _cached(name, fetch, refresh):
    path = os.path.join(CACHE, name)
    today = datetime.date.today().isoformat()
    if not refresh and os.path.exists(path) and \
            datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat() == today:
        return json.load(open(path, encoding="utf-8"))
    data = fetch()
    os.makedirs(CACHE, exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return data


def load_sources(refresh):
    c = _client.default()

    def opt(path):
        def f():
            try:
                return c.get(path)
            except _client.ApiError as e:
                log(f"⚠ {path}: {e}")
                return None
        return f
    src = {
        "medias": _cached("medias.json", lambda: c.get(f"/medias?acceptTypes={TYPES}", timeout=300)["data"],
                          refresh),
        "export": _cached("export-en.json", lambda: _export.records("en"), refresh),
        "brands": _cached("brands-all.json", lambda: c.get("/brands")["data"], refresh),
        "categories": _cached("categories.json", lambda: c.get("/categories?search=&sortBy=id")["data"],
                              refresh),
    }
    for name, path in [("home", "/pages/home"), ("about-us", "/pages/about-us"),
                       ("promotions", "/promotions"), ("post-categories", "/post-categories"),
                       ("campaigns", "/campaigns")]:
        src[name] = _cached(f"src-{name}.json", opt(path), refresh)
    return src


# ----------------------------------------------------------------- filename ----
def brand_index(brands):
    """slug token tuple → brand name, longest first ("royal-canin" → "Royal Canin")."""
    idx = {}
    for b in brands:
        toks = tuple(slugify(b["name"]).split("-"))
        if toks and toks[0]:
            idx[toks] = b["name"]
    for alias, name in ALIASES.items():
        if name in {b["name"] for b in brands}:
            idx.setdefault((alias,), name)
    return sorted(idx.items(), key=lambda kv: -len(kv[0]))


def _strip_ext(name):
    name = name or ""
    while True:  # "x.jpg.jpg", "x.jpg-3", "x.png-1"
        new = re.sub(r"\.(jpe?g|png|webp|gif|svg|avif)(-\d+)?$", "", name, flags=re.I)
        if new == name:
            return name
        name = new


def readable(filename, brands, drop=NOISE):
    """File name → readable words, or '' when nothing readable is left."""
    name = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", " ", _strip_ext(filename),
                  flags=re.I)                                    # UUIDs ("…_DownloadAsJpg")
    raw = [t for t in re.split(r"[^A-Za-z0-9']+", name) if t]
    low = [t.lower() for t in raw]
    out, i = [], 0
    while i < len(low):
        for toks, name in brands:
            if tuple(low[i:i + len(toks)]) == toks:
                out.append(("brand", name))
                i += len(toks)
                break
        else:
            out.append(("word", low[i]))
            i += 1
    words = []
    for kind, w in out:
        if kind == "brand":
            words.append(w)
            continue
        if re.search(r"\d", w) or w in drop or len(w) < 2 and w not in SMALL:
            continue
        if len(w) >= 8 and not re.search(r"[aeiouy]", w):   # hashes
            continue
        words.append(w)
    while words and words[-1].lower() in SMALL:
        words.pop()
    while words and words[0].lower() in SMALL:
        words.pop(0)
    letters = sum(len(w) for w in words if not w[:1].isupper() or w.lower() not in SMALL)
    brand_names = {n for _, n in brands}
    if not words or letters < 4 or len(words) == 1 and words[0] not in brand_names:
        return ""                                    # one generic word ("Group", "Slide") says nothing
    text = []
    for n, w in enumerate(words):
        if w in brand_names:
            text.append(w)
        elif n and w in SMALL:
            text.append(w)
        else:
            text.append(w[:1].upper() + w[1:])
    return " ".join(text)


# --------------------------------------------------------------------- plan ----
def walk_titled(node, found, ids, where, top=True):
    """Media ids in titled list items (title/name) → found[id] = (text, where)."""
    if isinstance(node, list):
        for x in node:
            walk_titled(x, found, ids, where, top=False)
    elif isinstance(node, dict):
        text = None if top else (node.get("title") or node.get("name"))
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                walk_titled(v, found, ids, where, top=False)
            elif text and isinstance(v, int) and v in ids and re.search(r"image|icon|file|photo|avatar", k):
                found.setdefault(v, (str(text), f"{where} {k}"))


def plan(src):
    medias = src["medias"]
    ids = {m["id"] for m in medias}
    brands = brand_index(src["brands"])
    target, conflicts = {}, []

    # product
    users = {}
    for r in src["export"]:
        for mid in r.get("image_ids") or []:
            users.setdefault(mid, {}).setdefault(r["product_id"], r)
    by_id = {m["id"]: m for m in medias}
    for mid, prods in users.items():
        folder = (by_id.get(mid) or {}).get("directory") or ""
        pick = min(prods.values(), key=lambda p: (bool(p.get("is_discontinued")),
                                                   not folder.startswith(f"products/{slugify(p.get('brand'))}/"),
                                                   p["product_id"]))
        text = f"{pick.get('brand') or ''} {pick.get('product_name') or ''}"
        target[mid] = (clip(text), "product", str(pick["product_id"]))
        if len(prods) > 1:
            conflicts.append((mid, folder, pick, [prods[p] for p in sorted(prods) if p != pick["product_id"]]))

    # logo
    for b in src["brands"]:
        if b.get("image") and b["image"] not in target:
            target[b["image"]] = (clip(f"{b['name']} logo"), "logo", f"brand {b['id']}")

    # category
    cats = {c["id"]: c for c in src["categories"]}

    def root(c):
        while c.get("parent_id") and c["parent_id"] in cats:
            c = cats[c["parent_id"]]
        return c
    for c in src["categories"]:
        r = root(c)
        name = c["name"] if r["id"] == c["id"] or r["name"].lower() in c["name"].lower() \
            else f"{r['name']} {c['name']}"
        for k in ("image", "featured_image", "meta_image"):
            if c.get(k) and c[k] not in target:
                target[c[k]] = (clip(name), "category", f"category {c['id']} {k}")

    # banner
    banner_ids = {}
    home = (src.get("home") or {}).get("data") or {}
    for b in home.get("banners") or []:
        for k, v in b.items():
            if k.startswith("file_") and v:
                banner_ids.setdefault(v, f"home banner {b.get('id')} {k}")
    for p in (src.get("promotions") or {}).get("data") or []:
        for k, v in p.items():
            if k.startswith("home_hero_") and isinstance(v, int):
                banner_ids.setdefault(v, f"promotion {p['id']} {k}")
    for pc in (src.get("post-categories") or {}).get("data") or []:
        if pc.get("banner_image"):
            banner_ids.setdefault(pc["banner_image"], f"blog category {pc['id']} banner_image")
    for cp in (src.get("campaigns") or {}).get("data") or []:
        if isinstance(cp.get("banner"), int):
            banner_ids.setdefault(cp["banner"], f"campaign {cp['id']} banner")
    for mid, where in banner_ids.items():
        if mid in target or mid not in by_id:
            continue
        words = readable(by_id[mid]["filename"], brands, NOISE | BANNER_DROP)
        if words:
            target[mid] = (clip(f"{words} banner"), "banner", where)

    # page: titled items, home SEO image
    found = {}
    for name in ("home", "about-us", "post-categories"):
        walk_titled((src.get(name) or {}).get("data"), found, ids, name)
    if home.get("meta_image") and (home.get("meta") or {}).get("title"):
        found.setdefault(home["meta_image"], (home["meta"]["title"], "home meta_image"))
    for mid, (text, where) in found.items():
        if mid not in target:
            target[mid] = (clip(text), "page", where)

    rows = []
    for m in sorted(medias, key=lambda m: m["id"]):
        t = target.get(m["id"])
        if not t:
            words = readable(m["filename"], brands)
            t = (clip(words), "filename", "") if words else ("", "unresolved", "")
        new, source, ref = t
        rows.append({"id": m["id"], "folder": m.get("directory") or "", "filename": m["filename"],
                     "used": int(bool(m.get("isUsed"))), "old_alt": m.get("alt") or "",
                     "old_caption": m.get("caption") or "", "new_alt": new, "source": source, "ref": ref,
                     "action": "unresolved" if source == "unresolved" else
                     "same" if (m.get("alt") or "") == new and (m.get("caption") or "") == new else "write"})
    return rows, conflicts


# -------------------------------------------------------------------- write ----
def write(row):
    c = _client.default()
    mid, new = row["id"], row["new_alt"]
    before = (c.get(f"/medias/{mid}") or {}).get("data") or {}
    if before.get("alt") == new and before.get("caption") == new:
        return "same", before
    c.put(f"/medias/{mid}", {"alt": new, "caption": new})
    back = (c.get(f"/medias/{mid}") or {}).get("data") or {}
    bad = [k for k in ("filename", "directory", "originalUrl", "extension", "mime_type", "size")
           if back.get(k) != before.get(k)]
    if back.get("alt") != new or back.get("caption") != new:
        bad.append("alt/caption not saved")
    os.makedirs(CACHE, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"id": mid, "alt": new, "old_alt": before.get("alt"),
                            "old_caption": before.get("caption"), "ok": not bad, "bad": bad,
                            "at": datetime.datetime.now().isoformat(timespec="seconds")},
                           ensure_ascii=False) + "\n")
    return ("ok" if not bad else "MISMATCH " + ", ".join(bad)), back


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--ids", nargs="+", type=int)
    g.add_argument("--all", action="store_true")
    ap.add_argument("--plan", default=os.path.join(ROOT, "runs", datetime.date.today().isoformat(),
                                                    "media-alt-plan.csv"))
    ap.add_argument("--refresh", action="store_true", help="re-fetch sources even if cached today")
    a = ap.parse_args(argv)

    rows, conflicts = plan(load_sources(a.refresh or not a.dry_run))
    os.makedirs(os.path.dirname(a.plan), exist_ok=True)
    with open(a.plan, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.splitext(a.plan)[0] + "-conflicts.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["media_id", "folder", "used_product_id", "used_product", "also_in"])
        for mid, folder, pick, others in conflicts:
            w.writerow([mid, folder, pick["product_id"], f"{pick.get('brand')} {pick.get('product_name')}",
                        " | ".join(f"{o['product_id']} {o.get('brand')} {o.get('product_name')}"
                                   + (" (discontinued)" if o.get("is_discontinued") else "") for o in others)])
    from collections import Counter
    cnt = Counter((r["source"], r["action"]) for r in rows)
    log(f"plan → {a.plan} ({len(rows)} images, {len(conflicts)} shared between products)")
    for k, v in sorted(cnt.items()):
        log(f"  {k[0]:<11} {k[1]:<10} {v}")
    if a.dry_run:
        return 0

    todo = [r for r in rows if r["action"] == "write"]
    if a.ids:
        want = set(a.ids)
        todo = [r for r in rows if r["id"] in want]
        missing = want - {r["id"] for r in todo}
        if missing:
            log(f"⚠ not in the library: {sorted(missing)}")
    fails = 0
    for n, r in enumerate(todo, 1):
        if r["action"] == "unresolved" or not r["new_alt"]:
            log(f"skip {r['id']}: unresolved ({r['filename']})")
            continue
        try:
            status, _ = write(r)
        except _client.ApiError as e:
            status = f"ERROR {e}"
        fails += not status.startswith(("ok", "same"))
        print(f"[{n}/{len(todo)}] {r['id']:>6} {r['source']:<9} {status:<6} {r['old_alt']!r} → {r['new_alt']!r}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
