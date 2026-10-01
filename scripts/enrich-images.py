#!/usr/bin/env python3
"""Give every variant of this run's products as many verified images as the
sources honestly offer, and never leave one with none.

Sources, in the order they are ranked into the gallery (CLAUDE.md rule 7: the
first image is the feature image and must be a clean product shot):

  1 brand packshot   Trixie PHO_PRO_CLIP  ·  monge.it / monge.shop pack photo
  2 brand pack shot  Trixie PHO_PAC_CLIP
  3 detail / set     Trixie PHO_PRO_DET_CLIP, PHO_PRO_SET_CLIP, extra shop shots
  4 distributor      trixiecz.cz's leading photo (570px packshot, keyed by the
                     `Kód` printed on the page) — only reached when the brand
                     site has no packshot of its own
  5 in use           Trixie PHO_PRO_USE(_CLIP)  ·  further trixiecz.cz photos
  6 lifestyle        Trixie PHO_PRO_DOG / PHO_PRO_CAT (animal in shot)
  7 group / drawing  Trixie PHO_PRO_GROUP_CLIP, GRA_PRO

Ranks 1-3 and 5-8 are also filled from **trixie.shop**, Trixie's own Shopify
store, which keeps Trixie's file names and so proves the article the same way
the CDN does; it carries the family files the CDN probe cannot guess.
The chain and what each source may be used for live in `config.json`
→ `images.sources`; the evaluation that picked them is in
`reference/image-sources.md`.
  9 hafo.am          the distributor's own photo for the SAME article code —
                     the documented fallback, used only when the brand site
                     gives the variant fewer than two pictures, and only when
                     the hafo file name carries our article (never a sibling's)

Every URL is keyed to the article number (or the EAN that hafo stores for it),
so nothing here rests on a name match.

    scripts/enrich-images.py --build          # collect URLs  -> image-plan.json
    scripts/enrich-images.py --apply [--only id,id] [--limit N] [--dry-run]
"""
import json, os, re, subprocess, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
PLAN = os.path.join(CACHE, "image-plan.json")
STATE = os.path.join(CACHE, "enrich-images.state.json")
HAFO_PAGES = os.path.join(CACHE, "hafo-page-images.json")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Every PUT body is rebuilt by the one payload builder (catalog model 2026-09-29),
# which also checks the variants against the product type before anything is written.
from siruk_payload import PayloadError, put_body  # noqa: E402
TRIXIE_RANK = {"PHO_PRO_CLIP": 1, "PHO_PAC_CLIP": 2, "PHO_PRO_DET_CLIP": 3, "PHO_PRO_SET_CLIP": 4, "PHO_PRO": 3,
               "PHO_PRO_USE_CLIP": 5, "PHO_PRO_USE": 5, "PHO_PRO_DOG_CLIP": 6, "PHO_PRO_CAT_CLIP": 6,
               "PHO_PRO_DOG": 6, "PHO_PRO_CAT": 6, "PHO_PRO_GROUP_CLIP": 7, "PHO_PRO_GROUP": 7,
               "GRA_PRO": 8, "GRA_INFO": 8}


# Hand-verified, where the article has no hafo listing to carry an EAN. Gemon's
# pack files are keyed by the EAN whose item number is the article without its
# trailing supplier digit (300607 -> …300605, 300617 -> …300612: EAN-13 check
# digits make the run look irregular), and the file also names the line, the
# flavour and the pack, which is what rule 7 asks for.
# Hand-verified images for articles the brand's own sites do not picture, found by
# EAN (hafo row barcode) on catalogues that name the file after the EAN, and looked
# at one by one before writing (rule 7, fallback level 2). Kept as data so a rebuild
# never drops them: reference/recovered-images.json.
def _recovered():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference", "recovered-images.json")
    return json.load(open(p)) if os.path.exists(p) else {}


OVERRIDE = {
            # ok-lock.pet (the brand's own site) shows both packs, and each file is
            # the pack whose size is printed on it — looked at 2026-09-11
            "1101413": ["https://static.tildacdn.com/tild3462-3366-4231-b862-666639323432/_5_4.png"],
            "1101213": ["https://static.tildacdn.com/tild3861-6562-4237-a265-313833303830/_11_4.png"],
            # monge.it names the line, the form, the lifestage and the flavour in the
            # file: gift / soft-sticks / adult skin-support / merluzzo (cod) with red
            # clover — exactly the invoiced article, which comes in one pack size
            "08527MG": ["https://www.monge.it/wp-content/uploads/2023/05/18_monge-gift_soft-sticks_adult-·-skin-support-ricco-in-merluzzo-fresco-con-trifoglio-rosso-319x500-1.jpg"],
            "300617": ["https://www.monge.it/wp-content/uploads/2023/11/ALL-BREEDS-ADULT_Salmone_100g_8009470300612.jpg"],
            # hafo's photo for this article is a Leo's "selvaggina" (game) can, but the
            # article, the invoice and hafo's own row all say poultry — use Monge's
            # own picture of the adult dog chunks with chicken instead (2026-09-11)
            "390807": ["https://www.monge.it/wp-content/uploads/2020/06/monge_cane_umido_leos_bocconi_con_pollo_adult.jpg"]}
DENY = {"390807"}
_RECOVERED = _recovered()


def load(p, d=None):
    return json.load(open(p)) if os.path.exists(p) else d


def sh(args, timeout=600):
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=timeout, env=dict(os.environ))
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_enrich.json"); json.dump(payload, open(p, "w"), ensure_ascii=False); args.append(p)
    rc, out, err = sh(args)
    i = out.find("{")
    return json.loads(out[i:]) if i >= 0 else {"_err": err[-300:]}


def trixie_rank(url):
    f = url.rsplit("/", 1)[-1]
    m = re.match(r"^([A-Z_]+?)_[0-9]", f)
    n = re.search(r"-(\d+)_%23", f)
    return (TRIXIE_RANK.get(m.group(1) if m else "", 6), int(n.group(1)) if n else 99, f)


# trixie.shop keeps Trixie's file names but a family file can start with the line
# name rather than the article (PHO_PRO_CLIP_SilverReflect-12222-1), so match the
# longest known prefix instead of "prefix then digit".
SHOP_PREFIXES = sorted(TRIXIE_RANK, key=len, reverse=True)


def shop_rank(url):
    f = url.rsplit("/", 1)[-1]
    p = next((x for x in SHOP_PREFIXES if f.startswith(x + "_")), "")
    n = re.search(r"-(\d+)_", f[len(p):]) if p else None
    return (TRIXIE_RANK.get(p, 6), int(n.group(1)) if n else 99, f)


def image_sources():
    """The approved fallback chain from config.json (see CLAUDE.md rule 7 / 7a).
    Missing config = every source on, which is the behaviour before 2026-09-11."""
    cfg = load(os.path.join(ROOT, "config.json"), {}) or {}
    src = {s["id"]: s for s in (cfg.get("images") or {}).get("sources", [])}
    return src, lambda i: (src.get(i, {}).get("enabled", True))


# ---------------------------------------------------------------- hafo gallery
def hafo_page_images(code, rec, cache):
    """The hafo listing's own photos, but only files whose name carries OUR
    article number (a listing spans sizes: 40181's page also shows 40182)."""
    if code in cache:
        return cache[code]
    urls, slug = [], (rec or {}).get("slug")
    if slug:
        try:
            req = urllib.request.Request(f"https://hafo.am/products/{slug}", headers={"User-Agent": UA})
            h = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "ignore")
            art = re.sub(r"[^0-9]", "", code)
            for u in sorted(set(re.findall(r"https://d1b3l6j8a0ngef\.cloudfront\.net/uploads/[^\"'\\\s>]+?\.(?:jpg|jpeg|png|webp)", h))):
                if "/thumb/" in u:
                    continue
                f = u.rsplit("/", 1)[-1]
                if re.search(r"[-_]" + art + r"(_\d+)?\.", f):
                    urls.append(u)
        except Exception:
            pass
        time.sleep(0.4)
    cache[code] = urls
    json.dump(cache, open(HAFO_PAGES, "w"), indent=0)
    return urls


# ---------------------------------------------------------------- build
def build():
    hafo = load(os.path.join(CACHE, "hafo-all.json"), {})
    cdn = load(os.path.join(CACHE, "trixie-cdn-gallery.json"), {})
    srccfg, on = image_sources()
    shop_img = load(os.path.join(CACHE, "trixie-shop-art-images.json"), {}) if on("trixie-shop") else {}
    czidx = load(os.path.join(CACHE, "trixiecz-index.json"), {}) if on("trixiecz") else {}
    cz1 = (srccfg.get("trixiecz") or {}).get("rank_first_image", 4)
    czn = (srccfg.get("trixiecz") or {}).get("rank_other_images", 5)
    ean2mit = load(os.path.join(CACHE, "ean2mit.json"), {})
    shop = load(os.path.join(CACHE, "mongeshop-pages.json"), {})
    shop_by_ean = {}
    for v in shop.values():
        if v.get("reference"):
            shop_by_ean.setdefault(str(v["reference"]).strip(), v)
    hcache = load(HAFO_PAGES, {})
    dropped = {}
    rowbar = load(os.path.join(CACHE, "hafo-variant-barcode.json"), {})   # the barcode of OUR hafo row, not the listing's
    shop_by_img = {}
    for v in shop.values():
        for u in v.get("images") or []:
            shop_by_img[u] = str(v.get("reference") or "")
    EAN = re.compile(r"(80094\d{8})")

    def wrong_ean(url, mine):
        """A monge-group picture that belongs to another pack of the same line.
        monge.it pages carry every size of the family plus site banners, and a
        hafo listing lists the barcodes of all its sizes, so the only safe key is
        the barcode of our own row (found 2026-09-11: article 004097 is the 800 g
        Mini Adult but had been given the 3 kg pack shot)."""
        if not mine:
            return False
        if "monge.it" in url:
            f = url.rsplit("/", 1)[-1]
            found = EAN.findall(f)
            if found:                       # the file names a pack: it must be ours
                return mine not in found
            return False                    # names only the line and flavour: the bag artwork is shared
        if url in shop_by_img:
            return shop_by_img[url] != mine
        return False

    out = {}
    for fn in ("trixie-plan.json", "monge-plan.json", "small-plan.json"):
        plan = load(os.path.join(CACHE, fn), {})
        state = load(os.path.join(CACHE, fn.replace(".json", ".state.json")), {"done": {}})
        for p in plan.get("products", []):
            done = state["done"].get(p["slug"])
            if not done:
                continue
            for v in p["variants"]:
                code = v.get("_code") or v["sku"]
                art = re.sub(r"[^0-9]", "", code)
                ranked, src = [], {}

                def add(url, rank, where):
                    if url and url not in src:
                        ranked.append((rank, len(ranked), url)); src[url] = where

                mine = (rowbar.get(code) or {}).get("barcode", "")
                for u in OVERRIDE.get(code, []) + _RECOVERED.get(code, []):
                    add(u, 1, "monge.it (line/flavour/pack in the file name)")
                for i, u in enumerate(v.get("images") or []):        # what the planner already found
                    if wrong_ean(u, mine):
                        dropped.setdefault(code, []).append(u); continue
                    add(u, trixie_rank(u)[0] if "cdn.trixie.de" in u else (1 if i == 0 else 3), "brand page")
                for u in cdn.get(art, []):                            # trixie CDN sweep
                    add(u, trixie_rank(u)[0], "trixie CDN")
                # trixie.shop — Trixie's own Shopify store, same file names, so the
                # article is still proved by the file itself. Reaches the family
                # files the CDN probe cannot guess (PHO_PRO_CLIP_SilverReflect-…).
                for u in shop_img.get(art) or shop_img.get(art.lstrip("0")) or []:
                    add(u, shop_rank(u)[0], "trixie.shop (article in file name)")
                # trixiecz.cz — the official CZ distributor, the only reliable route
                # to discontinued articles. Its files have no naming convention, so
                # the page's own `Kód` is the key and the first picture (the one the
                # shop leads with, a 570px packshot) ranks below every brand shot.
                cz = czidx.get(art) or czidx.get(art.lstrip("0")) or {}
                for i, u in enumerate(cz.get("images") or []):
                    add(u, cz1 if i == 0 else czn, "trixiecz.cz (Kód + EAN on the page)")
                rec = hafo.get(code) or {}
                for b in ([mine] if mine else (rec.get("barcodes") or [])):   # monge group, by OUR row's EAN
                    d = ean2mit.get(str(b))
                    if d:
                        for u in d["images"]:
                            if str(b) in u:                     # only the file that names this exact pack
                                add(u, 1, "monge.it (EAN)")
                    sp = shop_by_ean.get(str(b))
                    if sp:
                        for i, u in enumerate(sp.get("images") or []):
                            add(u, 1 if i == 0 else 3, "monge.shop (EAN)")
                # hafo pictures are watermarked, so they are a PLACEHOLDER only
                # (CLAUDE.md rule 7a): attached when the brand site has nothing, so
                # the PM can recognise the product and replace the photo by hand.
                # Rank 9 keeps them last, behind every brand shot, and every variant
                # carrying one is listed in needs-image.csv as the worklist.
                if len(ranked) < 2 and code not in DENY:
                    for u in hafo_page_images(code, rec, hcache):
                        add(u, 9, "hafo.am (watermarked placeholder — replace by hand)")
                    # the listing's own photo: safe when the listing holds a single row
                    # (then it can only show our article), and the last resort when the
                    # brand site gave us nothing at all
                    if rec.get("image") and (not ranked or len(rec.get("skus") or []) <= 1):
                        add(rec["image"], 9, "hafo.am (watermarked placeholder — replace by hand)")
                urls = [u for _, _, u in sorted(ranked)]
                out[str(done["id"]) + "/" + str(v["sku"])] = {
                    "product_id": done["id"], "sku": v["sku"], "code": code, "name": p["name"],
                    "urls": urls, "sources": {u: src[u] for u in urls}}
    json.dump(out, open(PLAN, "w"), ensure_ascii=False, indent=0)
    import collections
    c = collections.Counter(len(x["urls"]) for x in out.values())
    print(f"{len(out)} variants; images per variant:", dict(sorted(c.items())))
    empty = [x for x in out.values() if not x["urls"]]
    holder = [x for x in out.values() if x["urls"] and all("hafo.am" in x["sources"][u] for u in x["urls"])]
    print(f"no picture at all: {len(empty)} variant(s); watermarked hafo placeholder only: {len(holder)} -> needs-image.csv")
    if dropped:
        print(f"dropped {sum(len(v) for v in dropped.values())} image(s) whose pack EAN is not the variant's:",
              {k: [u.rsplit('/', 1)[-1] for u in v] for k, v in dropped.items()})


# ---------------------------------------------------------------- apply
HAFO_HOST = "d1b3l6j8a0ngef.cloudfront.net"


def hafo_media_ids(state):
    """Media ids that came from hafo — every upload these scripts ever made is in
    media-cache.json, so the ids are known exactly (same trick as --purge-hafo)."""
    mc = load(os.path.join(CACHE, "media-cache.json"), {})
    return {mid for u, mid in list(state.get("media", {}).items()) + list(mc.items())
            if HAFO_HOST in u and isinstance(mid, int) and mid}


def low_res_trixiecz(state):
    """The first trixiecz uploads took the 570x570 square (`_3`); the indexer now
    takes the original the lightbox links to (`_0`, 1000-1920 px). Where a variant
    gets the original, the square is a duplicate — drop it."""
    mc = load(os.path.join(CACHE, "media-cache.json"), {})
    return {mid for u, mid in list(state.get("media", {}).items()) + list(mc.items())
            if "trixiecz.cz/data/tmp/3/" in u and isinstance(mid, int) and mid}


def apply_():
    plan = load(PLAN, {})
    state = load(STATE, {"done": [], "problems": [], "media": {}})
    placeholder = hafo_media_ids(state)
    squares = low_res_trixiecz(state)
    displaced = []
    dry = "--dry-run" in sys.argv
    only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")} if "--only" in sys.argv else None
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    by_product = {}
    for x in plan.values():
        by_product.setdefault(x["product_id"], {})[str(x["sku"])] = x["urls"]
    n = 0
    for pid in sorted(by_product):
        if only and pid not in only:
            continue
        if pid in state["done"] and not dry:
            continue
        p = api("GET", f"/products/{pid}").get("data") or {}
        if not p:
            state["problems"].append((pid, "GET failed")); continue
        try:
            body = put_body(p)
        except PayloadError as e:
            state["problems"].append((pid, "payload", str(e)))
            print(f"{pid:>4} {p.get('name','')[:38]:<38} REFUSED before writing: {e}", flush=True)
            continue
        variants, changed, rep = [], False, []
        for v, nv in zip(p.get("variants", []), body["variants"]):
            nv["images"] = list(nv.get("images") or [])
            want = by_product.get(pid, {}).get(str(v["sku"]), [])
            # A hafo picture is a placeholder (rule 7a): it is only ever attached
            # when nothing else has one. So if this variant already carries a real
            # photo — or the plan now offers one, e.g. from trixie.shop or
            # trixiecz.cz — drop the placeholders instead of keeping them around.
            live_real = [i for i in (nv.get("images") or []) if i not in placeholder]
            want_real = [u for u in want if HAFO_HOST not in u]
            if live_real or want_real:
                want = want_real
            if dry:
                # project the outcome instead of the plan size: images already
                # uploaded are known by url, the rest would be new uploads
                known = [state["media"].get(u) for u in want]
                have_ids = [i for i in known if i]
                proj = list(dict.fromkeys(have_ids + [i for i in nv["images"] if i not in have_ids]))
                if [i for i in proj if i not in placeholder]:
                    proj = [i for i in proj if i not in placeholder]
                new = sum(1 for i in known if not i)
                rep.append(f"{v['sku']}: {len(nv['images'])}→{len(proj) + new}" + (f" ({new} new)" if new else ""))
                variants.append(nv); continue
            ids = []
            for u in want:
                mid = state["media"].get(u)
                if mid is None:
                    rc, out, err = sh([os.path.join(ROOT, "scripts/upload-media.sh"), u], timeout=900)
                    last = out.splitlines()[-1] if out else ""
                    mid = int(last) if re.fullmatch(r"\d+", last) else 0
                    state["media"][u] = mid
                    json.dump(state, open(STATE, "w"), indent=0)
                    if not mid:
                        state["problems"].append((pid, v["sku"], u, (err or out)[-150:]))
                if mid and mid not in ids:
                    ids.append(mid)
            ordered = ids + [i for i in nv["images"] if i not in ids]
            if any("trixiecz.cz/data/tmp/0/" in u for u in want):
                ordered = [i for i in ordered if i not in squares]   # original replaces the square
            real = [i for i in ordered if i not in placeholder]
            if real and len(real) != len(ordered):
                displaced.append((pid, v["sku"], len(ordered) - len(real)))
                ordered = real                      # a real photo displaces the placeholder
            if ordered != nv["images"]:
                nv["images"] = ordered; changed = True
            rep.append(f"{v['sku']}: {len(v.get('images') or [])}→{len(ordered)}")
            variants.append(nv)
        if changed and not dry:
            body["variants"] = variants
            r = api("PUT", f"/products/{pid}", body)
            back = api("GET", f"/products/{pid}").get("data") or {}
            got = {str(x["sku"]): len(x.get("images") or []) for x in back.get("variants", [])}
            if any(got.get(str(x["sku"]), -1) != len(x["images"]) for x in variants):
                state["problems"].append((pid, "verify", got, str(r)[:200]))
        if not dry:
            state["done"].append(pid)
            json.dump(state, open(STATE, "w"), indent=0)
        print(f"{pid:>4} {p.get('name','')[:38]:<38} {'; '.join(rep)}", flush=True)
        n += 1
        if limit and n >= limit:
            break
    if displaced:
        print(f"watermarked placeholders dropped for a real photo: {len(displaced)} variant(s), "
              f"{sum(d for _, _, d in displaced)} image(s)")
    print("problems:", len(state["problems"]))
    for x in state["problems"][:20]:
        print("  ", x)


# ---------------------------------------------------------------- purge
def purge_hafo(whole_catalogue=False):
    """Unlink every hafo.am picture from the catalogue (rule 7a).

    hafo files are served from its CloudFront bucket, and both `state["media"]`
    (this run) and `.siruk-cache/media-cache.json` (every upload these scripts ever
    made) record which media id each url became, so the ids are known exactly.
    `--all` walks the whole catalogue, not just this run's products — earlier
    sessions attached hafo pictures too."""
    state = load(STATE, {"done": [], "problems": [], "media": {}})
    mc = load(os.path.join(CACHE, "media-cache.json"), {})
    bad = {mid for u, mid in list(state["media"].items()) + list(mc.items())
           if "d1b3l6j8a0ngef.cloudfront.net" in u and isinstance(mid, int) and mid}
    print(f"{len(bad)} media id(s) uploaded from hafo")
    if whole_catalogue:
        pids, page = [], 1
        while True:
            d = api("GET", f"/products?page={page}")
            pids += [p["id"] for p in d.get("data", [])]
            if page >= (d.get("meta") or {}).get("last_page", 1):
                break
            page += 1
        pids = sorted(set(pids))
        print(f"scanning the whole catalogue: {len(pids)} products")
    else:
        plan = load(PLAN, {})
        pids = sorted({x["product_id"] for x in plan.values()})
    emptied, touched = [], 0
    for pid in pids:
        p = api("GET", f"/products/{pid}").get("data") or {}
        if not p:
            continue
        try:
            body = put_body(p)
        except PayloadError as e:
            print(f"{pid:>4} {p.get('name','')[:38]:<38} REFUSED before writing: {e}", flush=True)
            continue
        variants, changed = [], False
        for v, nv in zip(p.get("variants", []), body["variants"]):
            keep = [i for i in (nv.get("images") or []) if i not in bad]
            if keep != (nv.get("images") or []):
                changed = True
                if not keep:
                    emptied.append((pid, v["sku"], p.get("name", "")))
            nv["images"] = keep
            variants.append(nv)
        if changed:
            body["variants"] = variants
            api("PUT", f"/products/{pid}", body)
            back = api("GET", f"/products/{pid}").get("data") or {}
            left = [i for x in back.get("variants", []) for i in (x.get("images") or []) if i in bad]
            print(f"{pid:>4} {p.get('name','')[:38]:<38} hafo images removed" + ("  !! STILL PRESENT" if left else ""), flush=True)
            touched += 1
    print(f"products changed: {touched}; variants left with an empty gallery: {len(emptied)}")
    for e in emptied:
        print("   empty now:", e)
    json.dump(emptied, open(os.path.join(CACHE, "hafo-purged-empty.json"), "w"), ensure_ascii=False, indent=0)


if __name__ == "__main__":
    if "--purge-hafo" in sys.argv:
        purge_hafo("--all" in sys.argv)
    elif "--build" in sys.argv:
        build()
    elif "--apply" in sys.argv:
        apply_()
    else:
        print(__doc__)
