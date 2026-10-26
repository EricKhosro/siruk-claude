"""Media upload — the port of scripts/upload-media.sh + media-folder.py, and the
first version that flattens and downscales on Windows (the bash one needs
macOS `sips`; here Pillow does it, and its absence is reported, not hidden).

Rule 7: every upload goes in a folder — products/<brand-slug>/<type>, logos,
categories or banners. A 201 is not proof: the record must exist AND its file
must answer 200 (media 621, 2026-08-13), else the dud is deleted and re-uploaded.
"""
import io, json, mimetypes, os, re, time, urllib.parse, urllib.request

from siruk import client as _client
from siruk import config
from siruk.payload import PayloadError

FOLDER_RE = re.compile(r"^(products/[^/]+/[^/]+|logos|categories|banners(/.*)?)$")
TOP_NAMES = {"products": "Products", "logos": "Logos", "categories": "Categories", "banners": "Banners"}
CACHE_FILE = os.path.join(config.CACHE, "media-cache.json")
EXT_BY_TYPE = {"png": "png", "jpeg": "jpg", "jpg": "jpg", "webp": "webp", "avif": "avif", "gif": "gif"}


def _c():
    return _client.default()


# ----------------------------------------------------------------- folders ----
def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def folder_index():
    idx = {}

    def walk(nodes):
        for n in nodes or []:
            idx[n["path"]] = n
            walk(n.get("children"))
    tree = _c().get("/media-folders")
    walk(tree if isinstance(tree, list) else (tree or {}).get("data"))
    return idx


def _segment_names():
    names = dict(TOP_NAMES)
    for b in (_c().get("/brands?forProducts=true") or {}).get("data") or []:
        names.setdefault(slugify(b["name"]), b["name"])
    for f in (_c().get("/attribute-families?forProducts=true") or {}).get("data") or []:
        names.setdefault(f.get("code") or slugify(f["name"]), f["name"])
    return names


def ensure_folder(path, log=lambda m: None):
    path = path.strip("/")
    idx, names, parent, built = folder_index(), None, None, ""
    for seg in path.split("/"):
        built = f"{built}/{seg}" if built else seg
        if built not in idx:
            names = names or _segment_names()
            made = _c().post("/media-folders", {"name": names.get(seg) or seg.replace("-", " ").title(),
                                                "parentId": parent}) or {}
            made = made.get("data", made)
            if made.get("path") != built:
                raise PayloadError(f"folder {built!r}: server made path {made.get('path')!r} — stopping")
            log(f"  + folder {built} ({made.get('name')}, id {made['id']})")
            idx[built] = made
        parent = idx[built]["id"]
    return parent


# ------------------------------------------------------------------ checks ----
def media_ok(media_id, log=lambda m: None):
    cfg = config.load()["media"]["verify"]
    tries, wait = max(1, int(cfg["attempts"])), float(cfg["wait_seconds"])
    status = "no media record"
    for t in range(1, tries + 1):
        try:
            url = ((_c().get(f"/medias/{int(media_id)}") or {}).get("data") or {}).get("url")
        except _client.ApiError:
            url = None
        if url:
            status = _c().url_status(url)
            if status == 200:
                return True
        if t < tries:
            log(f"media {media_id} not readable yet ({status}) — re-checking in {wait:g}s")
            time.sleep(wait)
    log(f"⚠ media {media_id} is broken: {status}")
    return False


# ------------------------------------------------------------------- bytes ----
def _sniff(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[4:12] in (b"ftypavif", b"ftypavis"):
        return "image/avif"
    if data.lstrip()[:5] in (b"<?xml", b"<svg ") or b"<svg" in data[:300]:
        return "image/svg+xml"
    return None


def _download(url):
    req = urllib.request.Request(url, headers={"User-Agent": config.UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers.get("Content-Type", "")


def _prepare(data, name, keep_alpha, max_px, log):
    """Flatten transparency on white (unless keep_alpha) and downscale over max_px. → (bytes, name, dims)."""
    try:
        from PIL import Image
    except ImportError:
        log("⚠ Pillow not installed — uploading without flatten/downscale (`uv run siruk …` has it)")
        return data, name, ""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        return data, name, ""  # svg/avif without a plugin: send as is
    changed = False
    if not keep_alpha and (im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        im, changed = bg, True
        name = os.path.splitext(name)[0] + ".jpg"
        log(f"flattened transparency onto white → {name}")
    if max_px and max(im.size) > max_px:
        before = im.size
        im.thumbnail((max_px, max_px), Image.LANCZOS)
        changed = True
        log(f"downscaled {before[0]}x{before[1]} → {im.size[0]}x{im.size[1]}")
    if changed:
        buf = io.BytesIO()
        ext = os.path.splitext(name)[1].lower()
        if ext in (".jpg", ".jpeg") or im.mode == "RGB" and ext not in (".png", ".webp"):
            im.convert("RGB").save(buf, "JPEG", quality=92)
            name = os.path.splitext(name)[0] + ".jpg"
        else:
            im.save(buf, "PNG" if ext == ".png" else "WEBP")
        data = buf.getvalue()
    return data, name, f"{im.size[0]}x{im.size[1]}"


def safe_name(name):
    """A '%' or a space in the stored filename gives a url the server can't resolve (media 621)."""
    decoded = urllib.parse.unquote(name)
    safe = re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9._-]", "-", decoded)).lstrip("-.").rstrip("-")
    return safe or f"image-{os.getpid()}.jpg", decoded


def _cache():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _cache_put(url, mid):
    c = _cache()
    c[url] = mid
    os.makedirs(config.CACHE, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ upload ----
def upload(src, folder, keep_alpha=False, dry_run=False, log=lambda m: None):
    """→ {"id", "folder", "name", "cached"}. src is a local file or an http(s) url."""
    folder = (folder or "").strip("/")
    if not FOLDER_RE.match(folder):
        raise PayloadError(f"folder '{folder}' is outside the layout: products/<brand-slug>/<type>, "
                           "logos, categories or banners (rule 7)")
    cfg = config.load()["media"]
    is_url = src.startswith(("http://", "https://"))
    if is_url:
        cached = _cache().get(src)
        if cached and (not cfg["verify"]["enabled"] or media_ok(cached, log)):
            log(f"cache hit: {src} → media {cached}")
            return {"id": cached, "folder": folder, "name": None, "cached": True}
        data, ctype = _download(src)
        name = os.path.basename(urllib.parse.urlparse(src).path) or "image"
        if "." not in name:
            sub = ctype.split("/")[-1].split(";")[0].strip()
            name += "." + EXT_BY_TYPE.get(sub, "jpg")
        log(f"downloaded {name} ({len(data)} bytes, {ctype})")
    else:
        if not os.path.isfile(src):
            raise PayloadError(f"no such file: {src}")
        with open(src, "rb") as f:
            data = f.read()
        name = os.path.basename(src)
    mime = _sniff(data)
    if not mime:
        raise PayloadError(f"not an image: {src} — the source probably 404'd (an HTML page saved as .jpg)")
    data, name, dims = _prepare(data, name, keep_alpha, int(float(cfg["max_pixels"])), log)
    name, decoded = safe_name(name)
    if dry_run:
        return {"id": None, "folder": folder, "name": name, "bytes": len(data), "dims": dims, "dry_run": True}
    ensure_folder(folder, log)
    caption = os.path.splitext(decoded)[0]
    info = json.dumps({"filename": name, "caption": caption, "alt": caption, "dimensions": dims,
                       "directory": folder}, ensure_ascii=False)
    mime = mimetypes.guess_type(name)[0] or mime
    tries = max(1, int(cfg["verify"]["upload_attempts"])) if cfg["verify"]["retry_upload"] else 1
    for attempt in range(1, tries + 1):
        r = _c().upload("/medias", name, data, {"fileInfo": info}, mime=mime) or {}
        mid = (r.get("data") or {}).get("id")
        if not isinstance(mid, int):
            raise PayloadError(f"no media id in the response for {name}")
        if not cfg["verify"]["enabled"]:
            break
        time.sleep(float(cfg["verify"]["wait_seconds"]))
        if media_ok(mid, log):
            break
        if cfg["verify"]["delete_broken"]:
            try:
                _c().delete(f"/medias/{mid}")
                log(f"deleted broken media record {mid}")
            except _client.ApiError:
                log(f"could not delete broken media {mid}")
        if attempt == tries:
            raise PayloadError(f"media for {name} never became readable after {attempt} upload(s)")
        log(f"re-uploading {name} (attempt {attempt + 1}/{tries})")
    if is_url:
        _cache_put(src, mid)
    return {"id": mid, "folder": folder, "name": name, "dims": dims, "cached": False}
