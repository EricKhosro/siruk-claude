#!/usr/bin/env python3
"""Make sure a media-library folder chain exists, the way the admin UI does it.

    scripts/media-folder.py products/trixie/toys   # prints: products/trixie/toys
    scripts/media-folder.py logos
    scripts/media-folder.py --list             # every folder path with its id

Layout (CLAUDE.md rule 7, set by the user 2026-09-23):
    products/<brand-slug>/<type>   product images   ("Products / Trixie / Toys")
    logos                          brand logos
    categories                     category tiles
    banners                        page-top banners (free shipping, landing, blog)

Folders are records of their own (`POST /media-folders {name, parentId}` — the
server derives `path` from the name). Uploading or moving into a directory that
has no folder record works, but the admin media library never shows it, so an
upload must go through here first. Each segment is created with a human name:
a brand slug gets the brand's name ("royal-canin" → "Royal Canin"), a type slug
the family's name ("dry-food" → "Dry Food"), the top level "Products", "Logos",
"Categories", "Banners". If the path the server derives differs from the slug
asked for, this stops rather than leaving a folder the upload scripts can't find.

A folder is re-parented with `PUT /media-folders/<id> {name, parentId}` (the
admin's Edit Folder dialog) and its files move with it — that is how the brand
folders went under Products/ on 2026-09-23 in 32 calls instead of 3,000 moves.

Mirrors the siruk-web admin backend (routes/admin.php `media-folders`,
MediaFolderController). Note for the listing endpoint: `acceptTypes` is ONE comma-joined
string (MediaController::index does explode(',', acceptTypes));
`acceptTypes[]=…` hands the backend an array and it answers 500. The listing
filters by the stored mime type, so a file stored as text/html (an uploaded 404
page) never shows in it — look such a file up by id.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(ROOT, "scripts/api.sh")

ACCEPT_IMAGES = "image%2Fjpeg%2Cimage%2Fpng%2Cimage%2Fwebp%2Cimage%2Favif%2Cimage%2Fgif%2Cimage%2Fsvg%2Bxml"


def api(method, path, body=None):
    r = subprocess.run([API, method, path] + (["-"] if body is not None else []),
                       input=json.dumps(body) if body is not None else None,
                       capture_output=True, text=True, cwd=ROOT, timeout=300)
    out = r.stdout
    i = min([x for x in (out.find("{"), out.find("[")) if x >= 0], default=-1)
    if r.returncode != 0 or i < 0:
        raise RuntimeError(f"{method} {path} failed: {(r.stderr or out).strip()[-400:]}")
    return json.loads(out[i:])


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def folder_index():
    """{path: folder} for the whole tree."""
    idx = {}

    def walk(nodes):
        for n in nodes or []:
            idx[n["path"]] = n
            walk(n.get("children"))
    tree = api("GET", "/media-folders")
    walk(tree if isinstance(tree, list) else tree.get("data"))
    return idx


_names = None


def segment_name(slug):
    global _names
    if _names is None:
        _names = {"products": "Products", "logos": "Logos", "categories": "Categories", "banners": "Banners"}
        for b in api("GET", "/brands?forProducts=true").get("data", []):
            _names.setdefault(slugify(b["name"]), b["name"])
        for f in api("GET", "/attribute-families?forProducts=true").get("data", []):
            _names.setdefault(f.get("code") or slugify(f["name"]), f["name"])
    return _names.get(slug) or slug.replace("-", " ").title()


def ensure(path, idx=None):
    """Create any missing folder along `path`; returns the index (updated)."""
    path = path.strip("/")
    idx = folder_index() if idx is None else idx
    parent, built = None, ""
    for seg in path.split("/"):
        built = f"{built}/{seg}" if built else seg
        if built not in idx:
            made = api("POST", "/media-folders", {"name": segment_name(seg), "parentId": parent})
            made = made.get("data", made)
            if made.get("path") != built:
                raise RuntimeError(f"folder {built!r}: server made path {made.get('path')!r} — stopping")
            print(f"  + folder {built}  ({made.get('name')}, id {made['id']})", file=sys.stderr)
            idx[built] = made
        parent = idx[built]["id"]
    return idx


def list_dir(directory):
    """Media records directly inside `directory` ('' = the root)."""
    return api("GET", f"/medias?directory={directory}&acceptTypes={ACCEPT_IMAGES}").get("data", [])


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip()); sys.exit(0)
    if args[0] == "--list":
        for p, f in sorted(folder_index().items()):
            print(f"{f['id']}\t{p}\t{f.get('name')}")
        sys.exit(0)
    ensure(args[0])
    print(args[0].strip("/"))
