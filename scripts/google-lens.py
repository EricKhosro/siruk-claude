#!/usr/bin/env python3
"""Google search, Google Images and Google Lens in a HEADED real Chrome, through
Scrapling (https://github.com/d4vinci/Scrapling) — image-sources.md rung 9c.

Why Scrapling: plain automation (chrome-devtools MCP's fresh profile) gets
Google's /sorry reCAPTCHA on the first query. Scrapling's StealthySession drives
the installed Google Chrome (real_chrome) with a normal fingerprint and a
PERSISTENT profile (.siruk-cache/google-profile), so Google sees one ordinary
returning browser and the cookie from a CAPTCHA the user cleared once is kept.

A CAPTCHA is never solved by us (CLAUDE.md rule 7): when Google shows one the
script prints `CAPTCHA: waiting for the user …` on stderr and holds the visible
window open (up to --captcha-wait seconds) until the user has cleared it, then
carries on. Run it in the background and tell the user when that line appears.
`solve_cloudflare` is never turned on.

    .venv-scrapling/bin/python scripts/google-lens.py --search '"8009470418874"'
    .venv-scrapling/bin/python scripts/google-lens.py --images '"041887" monge'
    .venv-scrapling/bin/python scripts/google-lens.py --lens <image url>
    .venv-scrapling/bin/python scripts/google-lens.py --page <url> --keys 8009470418874,041887
    .venv-scrapling/bin/python scripts/google-lens.py --jobs jobs.json --out results.json

jobs.json: [{"id": "041887", "kind": "search|images|lens|page", "q": "<query, image url or page url>",
             "keys": ["<ean>", "<article>"]}, …]          (keys: page jobs only, optional)
Output (stdout, or --out): {"<id>/<kind>": {"url", "captcha", "results": [...]}}
  search  → [{title, href, page, cite, snippet}]   (page = where Google's link lands)
  images  → [{img, page, title}]      (the full-size url when Google exposes it)
  lens    → results = "Exact matches" tab [{title, meta, href, page}], visual = the "All" tab
            (non-Google pages only). q = an image url or a local file: Lens is fed by
            uploading the file through the camera icon (uploadbyurl gets a 403).
  page    → results = [{title, h1, lang, meta_description, jsonld: [Product…], text, keys_found}]
            q = a result page (description fallback, image-sources.md → "Texts when the
            brand has no page"). Opened in the same headed Chrome; `keys_found` lists
            which of the job's keys (EAN / article) the page prints. A bot wall or
            CAPTCHA on a shop page is never cleared: the job ends with error "blocked".

Nothing here accepts a result: every hit still needs our EAN/article on the
page or in the file name, or the same photograph beside hafo's on a contact
sheet (reference/image-sources.md → "Google and Google Lens before hafo").
Setup once: python3 -m venv .venv-scrapling && .venv-scrapling/bin/pip install "scrapling[fetchers]"
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE = os.path.join(ROOT, ".siruk-cache", "google-profile")
DEBUG_DIR = None
RESOLVE = 15

# Google wraps every result in /goto?url=<opaque> (2026-10-02): the extractors keep the
# wrapped href, the title, the "1,150x1,508" size/price line and the site name;
# resolve() then follows the first --resolve of them, as a click would.
EXTRACT = {
    "search": r"""() => {
      const out = [];
      document.querySelectorAll('#search a h3').forEach(h => {
        const a = h.closest('a'); if (!a) return;
        const box = a.closest('[data-hveid]') || a.parentElement.parentElement;
        out.push({title: h.innerText, href: a.href,
                  cite: (box.querySelector('cite') || {}).innerText || '',
                  snippet: (box.innerText || '').replace(h.innerText, '').slice(0, 300)});
      });
      return out;
    }""",
    "images": r"""() => {
      const out = [], seen = new Set();
      document.querySelectorAll('a[href*="imgurl="]').forEach(a => {
        const u = new URL(a.href, location.href);
        const img = u.searchParams.get('imgurl'), page = u.searchParams.get('imgrefurl');
        if (img && !seen.has(img)) { seen.add(img); out.push({img, page, title: a.innerText.slice(0, 120)}); }
      });
      if (!out.length) document.querySelectorAll('div[data-lpage]').forEach(d => {
        const im = d.querySelector('img');
        out.push({img: im ? (im.getAttribute('data-src') || im.src) : null, page: d.getAttribute('data-lpage'),
                  title: (d.innerText || '').slice(0, 120)});
      });
      return out;
    }""",
    "lens": r"""() => {
      const out = [], seen = new Set();
      document.querySelectorAll('a[href*="/goto?url="], a[href^="http"]').forEach(a => {
        const h = a.href;
        if (!/\/goto\?url=/.test(h) && /(^https?:\/\/([a-z]+\.)?google\.|gstatic\.com|googleusercontent\.com)/.test(h)) return;
        if (seen.has(h)) return; seen.add(h);
        const t = a.querySelector('.ZhosBf, [style*="line-clamp"]');
        const lines = (a.innerText || '').split('\n').map(x => x.trim()).filter(Boolean);
        out.push({title: t ? t.innerText : (lines[0] || ''), meta: lines.slice(1).join(' | '), href: h});
      });
      return out;
    }""",
    "page": r"""() => {
      const clean = t => (t || '').replace(/[ \t]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();
      const ld = [];
      document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
        try {
          const walk = o => { if (!o) return; if (Array.isArray(o)) return o.forEach(walk);
            if (o['@graph']) walk(o['@graph']);
            const t = [].concat(o['@type'] || []);
            if (t.includes('Product')) ld.push({name: o.name, description: o.description, sku: o.sku,
              gtin: o.gtin13 || o.gtin || o.gtin12 || o.ean || null, brand: (o.brand || {}).name || o.brand,
              image: o.image}); };
          walk(JSON.parse(s.textContent));
        } catch (e) {}
      });
      const main = document.querySelector('main, [itemtype*="Product"], #content, article') || document.body;
      const meta = n => (document.querySelector(`meta[name="${n}"], meta[property="${n}"]`) || {}).content || '';
      return [{title: document.title, h1: clean((document.querySelector('h1') || {}).innerText),
               lang: document.documentElement.lang, meta_description: meta('description') || meta('og:description'),
               jsonld: ld, text: clean(main.innerText).slice(0, 20000), html: document.documentElement.outerHTML}];
    }""",
}

# A shop's own anti-bot page: we stop there, never work around it (image-sources.md rule 5).
BLOCKED = re.compile(r"(cf-challenge|challenges\.cloudflare\.com|captcha|ddos-guard|access denied|"
                     r"attention required|are you a robot|verify you are human)", re.I)


def resolve(page, rows, limit):
    """Follow a result's /goto link in a throw-away tab and record where it lands."""
    for r in rows[:limit]:
        h = r.get("href") or ""
        if "/goto?url=" not in h:
            r["page"] = h
            continue
        tab = page.context.new_page()
        try:
            tab.goto(h, wait_until="commit", timeout=30000)
            for _ in range(20):
                if "google." not in urllib.parse.urlparse(tab.url).netloc:
                    break
                tab.wait_for_timeout(500)
            r["page"] = tab.url
        except Exception as e:
            r["page"] = tab.url if "google." not in tab.url else None
            r["resolve_error"] = type(e).__name__
        finally:
            tab.close()


def url_for(kind, q):
    if kind == "search":
        return "https://www.google.com/search?hl=en&q=" + urllib.parse.quote(q)
    if kind == "images":
        return "https://www.google.com/search?hl=en&udm=2&q=" + urllib.parse.quote(q)
    if kind == "page":
        return q
    if kind == "lens":
        # lens.google.com/uploadbyurl redirects to a /search url Google answers 403 for
        # (tested 2026-10-02); the camera icon + a file upload works, so Lens starts here.
        return "https://www.google.com/?hl=en"
    raise SystemExit(f"unknown kind {kind}")


def local_image(q):
    """Lens takes a file: download an image url once into .siruk-cache/lens/."""
    if os.path.exists(q):
        return os.path.abspath(q)
    d = os.path.join(ROOT, ".siruk-cache", "lens"); os.makedirs(d, exist_ok=True)
    f = os.path.join(d, re.sub(r"[^A-Za-z0-9._-]", "_", q.split("?")[0].rsplit("/", 1)[-1]) or "img.jpg")
    if not os.path.exists(f):
        req = urllib.request.Request(q, headers={"User-Agent": "Mozilla/5.0"})
        open(f, "wb").write(urllib.request.urlopen(req, timeout=60).read())
    return f


def lens_upload(page, path):
    page.locator('[aria-label="Search by image"]').first.click()
    page.wait_for_timeout(1200)
    with page.expect_file_chooser() as fc:
        page.get_by_text("upload a file").first.click()
    fc.value.set_files(path)
    page.wait_for_url("**/search?**", timeout=60000)
    page.wait_for_load_state("networkidle")


def is_captcha(page):
    if "/sorry/" in page.url:
        return True
    try:
        return page.locator('iframe[src*="recaptcha"]').count() > 0
    except Exception:
        return False


def run(jobs, captcha_wait, pause):
    from scrapling.fetchers import StealthySession
    import fcntl
    os.makedirs(PROFILE, exist_ok=True)
    # one Chrome per profile: a second run waits instead of failing on the profile lock
    lock = open(os.path.join(os.path.dirname(PROFILE), "google-profile.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another google-lens.py run holds the Chrome profile — waiting for it", file=sys.stderr, flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
    results = {}
    with StealthySession(headless=False, real_chrome=True, user_data_dir=PROFILE,
                         locale="en-US", network_idle=True, timeout=60000,
                         solve_cloudflare=False) as s:
        for i, job in enumerate(jobs):
            kind, q = job["kind"], job["q"]
            key = f'{job.get("id", i)}/{kind}'
            box = {"url": url_for(kind, q), "captcha": False, "results": []}

            def action(page, kind=kind, box=box, q=q, key=key, keys=job.get("keys") or []):
                if kind == "page":
                    page.wait_for_timeout(1500)
                    r = page.evaluate(EXTRACT["page"])[0]
                    html = r.pop("html")
                    box["final_url"] = page.url
                    if BLOCKED.search(r["title"] + " " + r["text"][:2000]) and len(r["text"]) < 3000:
                        box["error"] = "blocked"   # a bot wall stays closed — skip the page
                        return page
                    digits = re.sub(r"\D", "", html)
                    r["keys_found"] = [k for k in keys if k and (k in html or (k.isdigit() and len(k) >= 12 and k in digits))]
                    box["results"] = [r]
                    if DEBUG_DIR:
                        os.makedirs(DEBUG_DIR, exist_ok=True)
                        page.screenshot(path=os.path.join(DEBUG_DIR, key.replace("/", "-") + ".png"), full_page=True)
                    return page
                if is_captcha(page):
                    box["captcha"] = True
                    print(f"CAPTCHA: waiting for the user to clear it in the Chrome window ({key})",
                          file=sys.stderr, flush=True)
                    end = time.time() + captcha_wait
                    while is_captcha(page) and time.time() < end:
                        page.wait_for_timeout(3000)
                    if is_captcha(page):
                        box["error"] = "captcha not cleared"
                        return page
                    print("CAPTCHA cleared, continuing", file=sys.stderr, flush=True)
                    page.wait_for_load_state("networkidle")
                if kind == "lens":
                    lens_upload(page, local_image(q))
                    page.wait_for_timeout(3000)
                    box["visual"] = page.evaluate(EXTRACT["lens"])
                    tab = page.get_by_role("link", name="Exact matches")
                    if tab.count():
                        tab.first.click(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(3000)
                box["final_url"] = page.url
                box["results"] = page.evaluate(EXTRACT[kind])
                if kind in ("search", "lens"):
                    resolve(page, box["results"], RESOLVE)
                if DEBUG_DIR:
                    os.makedirs(DEBUG_DIR, exist_ok=True)
                    stem = os.path.join(DEBUG_DIR, key.replace("/", "-"))
                    page.screenshot(path=stem + ".png", full_page=True)
                    open(stem + ".html", "w").write(page.content())
                return page

            try:
                s.fetch(box["url"], page_action=action)
            except Exception as e:  # one failed job never stops the batch
                box["error"] = f"{type(e).__name__}: {e}"[:300]
            results[key] = box
            print(f"{key}: {len(box['results'])} results"
                  + (" (captcha)" if box["captcha"] else "")
                  + (f" ERROR {box.get('error')}" if box.get("error") else ""), file=sys.stderr, flush=True)
            if i < len(jobs) - 1:
                time.sleep(pause)        # a human pace keeps Google calm
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--search"); ap.add_argument("--images"); ap.add_argument("--lens")
    ap.add_argument("--page", help="open a result page and extract its texts (description fallback)")
    ap.add_argument("--keys", help="comma-separated EAN/article the --page should print")
    ap.add_argument("--jobs", help="JSON list of {id, kind, q}")
    ap.add_argument("--out")
    ap.add_argument("--captcha-wait", type=int, default=600, help="seconds to wait for the user (default 600)")
    ap.add_argument("--pause", type=float, default=6.0, help="seconds between queries (default 6)")
    ap.add_argument("--resolve", type=int, default=15, help="follow the first N result links (default 15)")
    ap.add_argument("--debug", help="folder for a screenshot + html of every result page")
    a = ap.parse_args()
    global DEBUG_DIR, RESOLVE
    DEBUG_DIR, RESOLVE = a.debug, a.resolve
    jobs = json.load(open(a.jobs)) if a.jobs else []
    for k in ("search", "images", "lens", "page"):
        if getattr(a, k):
            jobs.append({"id": "q", "kind": k, "q": getattr(a, k),
                         "keys": a.keys.split(",") if k == "page" and a.keys else []})
    if not jobs:
        ap.error("give --search / --images / --lens / --page or --jobs")
    res = run(jobs, a.captcha_wait, a.pause)
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        open(a.out, "w").write(txt)
        print(f"wrote {a.out}", file=sys.stderr)
    else:
        print(txt)


if __name__ == "__main__":
    main()
