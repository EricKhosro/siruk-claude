#!/usr/bin/env python3
"""Blog posts → ru / hy. The script half of the /translate-blog skill.

  scripts/blog-translate.py status                 which posts still lack ru / hy
  scripts/blog-translate.py export <id>            save en/ru/hy JSON + the English text to read
  scripts/blog-translate.py check  <id>            purity / banned words / structure / links
  scripts/blog-translate.py apply  <id> [--apply]  PUT ru + hy (dry run without --apply), read back

Files live in runs/<today>/blog/ (BLOG_DIR= overrides):
  p<id>-en.json, p<id>-ru.json, p<id>-hy.json   the posts as they were (backup)
  p<id>-en.txt                                  the English title, summary, meta, blocks to translate
  tr/p<id>-<lang>.json                          {"title", "featured_description", "meta"?: {title, description}}
  tr/p<id>-<lang>-b<blockId>.html               one file per TEXT block, same HTML tags as en

How the API works (siruk-web PostController, 2026-11-12):
- PUT /posts/<id> with "locale" (+ Content-Language) writes that locale only; en is untouched.
- The request is a full sync for content_blocks and author_ids: every block goes back with its id
  (image blocks with their image ids, related_products with product_ids), author_ids are resent.
- vet_reviews.review_text is a pivot column, single-language: resent exactly as en has it.
- published_at, is_published, is_featured and the image keys are left out, so they stay as they are.
- meta is sent only when the post has meta in en, always with meta_image (else the SEO image drops).
Pacing: one call at a time, >= 1.6 s apart (CLAUDE.md "Slow requests, everywhere").
"""
import datetime, json, os, re, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
API = os.path.join(ROOT, "scripts/api.sh")
DIR = os.environ.get("BLOG_DIR") or os.path.join(ROOT, "runs", datetime.date.today().isoformat(), "blog")
TR = os.path.join(DIR, "tr")
LANGS = ("ru", "hy")

# Words that must never appear. Armenian: insults that dictionaries give for "puppy" etc.
BANNED = {
    "hy": ["լակոտ", "շան ձագ", "շնաձագ", "անասուն ", "անասունն", "անասունի", "քաք", "էշ "],
    "ru": ["сука", "суки", "сучк", "кобел", "понос", "жрат", "жрёт", "морда", "пукать", "дерьм",
           "какашк", "сдох", "подыха", "загнулся"],
}
# Proper names allowed in Latin script inside ru/hy text. Extend when a post cites a new source.
LATIN_OK = {"Siruk", "PetMD", "Pet", "Poison", "Helpline", "Merck", "FEDIAF", "Schesir", "In", "Jelly",
            "WSAVA", "Purina", "Institute", "International", "Cat", "Care", "A", "B", "C", "D", "E",
            "Royal", "Canin", "Pro", "Plan", "Acana", "Orijen", "Brit", "Monge", "Trixie", "Hill", "Hill's"}


def api(method, path, body=None, lang=None):
    env = dict(os.environ)
    if lang:
        env["SIRUK_LANG"] = lang
    args = [API, method, path]
    if body is not None:
        os.makedirs(DIR, exist_ok=True)
        p = os.path.join(DIR, f"_body-{lang or 'x'}.json")
        with open(p, "w") as f:
            json.dump(body, f, ensure_ascii=False)
        args.append(p)
    out = subprocess.run(args, env=env, capture_output=True, text=True, cwd=ROOT)
    time.sleep(1.6)
    if out.returncode:
        sys.exit(f"{method} {path} failed: {out.stderr[-800:]}")
    return json.loads(out.stdout)


def load(path):
    with open(path) as f:
        return json.load(f)


def plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ")).strip()


def status():
    posts = api("GET", "/posts?perPage=200")["data"]
    for p in posts:
        en = p["title"]
        miss = [l for l in LANGS if api("GET", f"/posts/{p['id']}", lang=l)["data"]["title"] == en]
        print(f"{p['id']:>4}  {'MISSING ' + '+'.join(miss) if miss else 'ok      '}  {p.get('slug')}  {en[:60]}")


def export(pid):
    os.makedirs(TR, exist_ok=True)
    data = {}
    for l in ("en",) + LANGS:
        data[l] = api("GET", f"/posts/{pid}", lang=l)["data"]
        with open(os.path.join(DIR, f"p{pid}-{l}.json"), "w") as f:
            json.dump({"data": data[l]}, f, ensure_ascii=False, indent=1)
    en = data["en"]
    lines = [f"POST {pid}  slug={en['slug']}  published={en['is_published']} {en['published_at']}  "
             f"authors={en['author_ids']}  vets={len(en['vet_reviews'] or [])}",
             f"TITLE: {en['title']}", f"FEATURED: {en['featured_description']}",
             f"META: {json.dumps(en.get('meta'), ensure_ascii=False)}  meta_image={en.get('meta_image')}"]
    if en.get("content"):
        lines.append("WARNING: legacy `content` field is not empty — not handled by apply, ask the user.")
    for b in en["content_blocks"]:
        lines.append(f"\n===== block {b['id']} ({b['type']})")
        if b["type"] == "text":
            lines.append(b.get("text") or "")
            lines.append(f"-> write tr/p{pid}-<ru|hy>-b{b['id']}.html")
        else:
            lines.append("(not translated — passed through as is)")
    for l in LANGS:
        done = data[l]["title"] != en["title"]
        lines.append(f"\n{l}: {'HAS its own text already — compare before overwriting' if done else 'not translated yet'}")
    txt = os.path.join(DIR, f"p{pid}-en.txt")
    with open(txt, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"saved {DIR}/p{pid}-{{en,ru,hy}}.json and {txt}")
    print(f"text blocks: {[b['id'] for b in en['content_blocks'] if b['type'] == 'text']}  "
          f"other blocks: {[(b['id'], b['type']) for b in en['content_blocks'] if b['type'] != 'text']}  "
          f"meta: {bool((en.get('meta') or {}).get('title'))}")


def tag_counts(html):
    return {t: len(re.findall(rf"<{t}[\s>]", html)) for t in ("p", "li", "a", "strong", "h5", "h6", "table", "td")}


def check(pid, quiet=False):
    en = load(os.path.join(DIR, f"p{pid}-en.json"))["data"]
    problems = []
    for l in LANGS:
        jp = os.path.join(TR, f"p{pid}-{l}.json")
        if not os.path.exists(jp):
            problems.append(f"{l}: missing {jp}")
            continue
        tr = load(jp)
        texts = [tr.get("title", ""), tr.get("featured_description", "")]
        if not tr.get("title"):
            problems.append(f"{l}: empty title")
        if (en.get("meta") or {}).get("title"):
            m = tr.get("meta") or {}
            if not m.get("title") or not m.get("description"):
                problems.append(f"{l}: en has SEO meta, translation has none")
            else:
                texts += [m["title"], m["description"]]
                if len(m["title"]) > 60 or len(m["description"]) > 160:
                    problems.append(f"{l}: meta too long ({len(m['title'])}/60, {len(m['description'])}/160)")
        for b in en["content_blocks"]:
            if b["type"] != "text":
                continue
            hp = os.path.join(TR, f"p{pid}-{l}-b{b['id']}.html")
            if not os.path.exists(hp):
                problems.append(f"{l}: missing {hp}")
                continue
            html = open(hp).read()
            texts.append(plain(html))
            a, e = tag_counts(html), tag_counts(b.get("text") or "")
            diff = {t: (e[t], a[t]) for t in a if a[t] != e[t] and t not in ("p", "strong")}
            if diff:
                problems.append(f"{l} block {b['id']}: tag counts differ from en (en, {l}) {diff}")
            if abs(a["p"] - e["p"]) > 3:
                problems.append(f"{l} block {b['id']}: <p> count {a['p']} vs en {e['p']}")
            en_links = re.findall(r'href="([^"]+)"', b.get("text") or "")
            tr_links = re.findall(r'href="([^"]+)"', html)
            for u in tr_links:
                if "siruk.am/" in u and f"siruk.am/{l}/" not in u:
                    problems.append(f"{l} block {b['id']}: siruk.am link not localised: {u}")
            if len(en_links) != len(tr_links):
                problems.append(f"{l} block {b['id']}: {len(tr_links)} links vs en {len(en_links)}")
        text = " ".join(texts)
        latin = sorted(set(re.findall(r"[A-Za-z][A-Za-z']*", text)) - LATIN_OK)
        other = re.findall(r"[А-Яа-яЁё]+" if l == "hy" else r"[Ա-և]+", text)
        hits = [w for w in BANNED[l] if w in text.lower()]
        if latin:
            problems.append(f"{l}: Latin words (allowed only for proper names; add real names to LATIN_OK): {latin}")
        if other:
            problems.append(f"{l}: {'Cyrillic' if l == 'hy' else 'Armenian'} letters: {other[:10]}")
        if hits:
            problems.append(f"{l}: BANNED words: {hits}")
        bangs, dashes = text.count("!"), text.count("—") + text.count(" – ")
        if bangs:
            problems.append(f"{l}: {bangs} exclamation mark(s)")
        if dashes > (3 if l == "ru" else 0):
            problems.append(f"{l}: {dashes} dash(es) — use commas/colons unless grammar needs one")
        if l == "hy" and text.count(":") > 0:
            problems.append(f"{l}: Latin ':' — Armenian full stop is '։', colon is '.' / '․'")
    if not quiet:
        print("\n".join(problems) if problems else f"post {pid}: all checks pass")
    return problems


def apply(pid, write):
    en = load(os.path.join(DIR, f"p{pid}-en.json"))["data"]
    if en.get("content"):
        sys.exit("legacy `content` field is set on this post — not handled; ask the user")
    if write and check(pid, quiet=True):
        sys.exit(f"check {pid} has problems — fix them (or run check to see them) before --apply")
    for l in LANGS:
        tr = load(os.path.join(TR, f"p{pid}-{l}.json"))
        blocks = []
        for b in en["content_blocks"]:
            if b["type"] == "text":
                html = open(os.path.join(TR, f"p{pid}-{l}-b{b['id']}.html")).read().strip()
                blocks.append({"id": b["id"], "type": "text", "text": html})
            elif b["type"] == "image":
                blocks.append({"id": b["id"], "type": "image", "image": b.get("image") or []})
            elif b["type"] == "related_products":
                blocks.append({"id": b["id"], "type": "related_products", "product_ids": b.get("product_ids") or []})
            else:
                sys.exit(f"unknown block type {b['type']} (block {b['id']})")
        body = {"locale": l, "post_category_id": en["post_category_id"], "author_ids": en["author_ids"],
                "vet_reviews": en["vet_reviews"] or [], "title": tr["title"], "slug": en["slug"],
                "featured_description": tr.get("featured_description") or en["featured_description"],
                "content_blocks": blocks}
        if (en.get("meta") or {}).get("title") and tr.get("meta"):
            body["meta"] = tr["meta"]
            body["meta_image"] = en.get("meta_image")
        print(f"post {pid} {l}: {tr['title'][:60]!r} blocks={[(b['id'], b['type']) for b in blocks]} meta={'meta' in body}")
        if not write:
            continue
        api("PUT", f"/posts/{pid}", body, lang=l)
        got = api("GET", f"/posts/{pid}", lang=l)["data"]
        ok = got["title"] == tr["title"] and all(
            g.get("text") == b["text"] for g, b in zip(got["content_blocks"], blocks) if b["type"] == "text")
        ids = [g["id"] for g in got["content_blocks"]] == [b["id"] for b in en["content_blocks"]]
        print(f"   read back: text ok={ok} block ids kept={ids} authors={got['author_ids']} "
              f"published_at={got['published_at']} image={got['image']} meta={bool((got.get('meta') or {}).get('title'))}")
    if write:
        now = api("GET", f"/posts/{pid}", lang="en")["data"]
        keys = ("title", "featured_description", "published_at", "is_published", "is_featured", "image",
                "author_ids", "meta", "meta_image")
        diff = [k for k in keys if now.get(k) != en.get(k)]
        same = [b.get("text") for b in now["content_blocks"]] == [b.get("text") for b in en["content_blocks"]]
        print(f"post {pid} en unchanged: {not diff and same} {diff or ''}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("status", "export", "check", "apply") or (a[0] != "status" and len(a) < 2):
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "status":
        status()
    elif cmd == "export":
        export(int(a[1]))
    elif cmd == "check":
        sys.exit(1 if check(int(a[1])) else 0)
    else:
        apply(int(a[1]), "--apply" in a)
