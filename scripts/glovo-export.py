#!/usr/bin/env python3
"""Fill Glovo's "Pelican Partners" product template from the live Siruk catalogue.

One row per VARIANT (a product with 3 variants = 3 rows), in the columns the
Glovo onboarding video shows (reference/glovo/README.md):

  A sku          <- variant sku
  B BARCODE      <- variant barcode, only an 8/13/14-digit EAN/GTIN (a 5-digit PLU is left out)
  C Title        <- Armenian: "<kind> «Brand» <hy name>, <hy options>, <size>"
  D Image link   <- the variant's first image, made a white-padded 500×500 square and
                    uploaded to ImgBB (the video uses postimages.org, which refuses
                    scripts): its direct link https://i.ibb.co/<id>/siruk-m<media id>.jpg
  E Description  <- the variant's hy "about this item", plain text, short
  F Price        <- variant price (AMD), dot decimals
  G Availability <- 1 in stock and purchasable, else 0
  H/I/J Section  <- the product's category leaves in Armenian ("Չոր կեր շների համար")

Input: the product dumps from scripts/dump-products.py (en + `--lang hy`).

    scripts/dump-products.py --refresh --fast
    scripts/dump-products.py --lang hy --refresh --fast
    .venv-img/bin/python scripts/glovo-export.py                 # images: Siruk direct links
    .venv-img/bin/python scripts/glovo-export.py --upload        # images: 500×500 on ImgBB
    … --out final/glovo/siruk-glovo.xlsx  --limit 5  --ids 1000 1257

--upload makes each image a white-padded 500×500 square, uploads it once through
ImgBB's official API (key in .imgbb-key, gitignored; no expiry) and keeps
media id -> direct link in .siruk-cache/glovo/imgbb.json, so a re-run only
uploads new images. Without --upload, column D gets the image's original
api.siruk.am url (not square) and the row is listed in the problems CSV.

Read-only towards Siruk: GET /medias/<id> only.
"""
import argparse, glob, html, io, json, os, re, subprocess, sys, time, urllib.error, urllib.request

import openpyxl
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, 'reference/glovo/Pelican-Partners-Template.xlsx')
CACHE = os.path.join(ROOT, '.siruk-cache/glovo')
MEDIA_CACHE = os.path.join(CACHE, 'media.json')       # media id -> {url, dimensions}
IMGBB_CACHE = os.path.join(CACHE, 'imgbb.json')       # media id -> i.ibb.co 500×500 direct link
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'

PET = {1: 'շների', 8: 'կատուների', 95: 'թռչունների', 98: 'կրծողների'}

# What the item is, for the title, when the hy product name starts with a Latin
# line name ("Instinctive 7+") and so does not say it. Keyed by leaf, then group.
KIND_LEAF = {3: 'Չոր կեր', 10: 'Չոր կեր', 4: 'Թաց կեր', 11: 'Թաց կեր', 5: 'Բուժական կեր',
             96: 'Կեր', 99: 'Կեր', 100: 'Խոտ', 93: 'Կատվախոտ', 94: 'Խոտ',
             42: 'Միջոց լվերի և տզերի դեմ', 51: 'Միջոց լվերի և տզերի դեմ',
             43: 'Վիտամիններ', 52: 'Վիտամիններ', 44: 'Պրոբիոտիկ', 53: 'Պրոբիոտիկ',
             46: 'Հակաճիճվային միջոց', 48: 'Հանգստացնող միջոց', 56: 'Հանգստացնող միջոց',
             60: 'Լցանյութ', 61: 'Լցանյութ', 62: 'Լցանյութ', 63: 'Լցանյութ', 64: 'Լցանյութ', 65: 'Լցանյութ',
             103: 'Թեփ', 102: 'Հավելում'}
KIND_GROUP = {6: 'Հյուրասիրություն', 14: 'Հյուրասիրություն', 97: 'Հյուրասիրություն', 101: 'Հյուրասիրություն',
              15: 'Խաղալիք', 16: 'Խաղալիք', 27: 'Խնամքի միջոց', 34: 'Խնամքի միջոց', 104: 'Խնամքի միջոց',
              106: 'Խնամքի միջոց', 41: 'Միջոց', 50: 'Միջոց', 59: 'Լցանյութ'}
UNITS = [(r'\bkg\b', 'կգ'), (r'\bg\b', 'գ'), (r'\bml\b', 'մլ'), (r'\bl\b', 'լ'), (r'\bcm\b', 'սմ'),
         (r'\bmm\b', 'մմ'), (r'\bm\b', 'մ'), (r'\bpcs\.?', 'հատ'), (r'\bpc\.?', 'հատ')]


def hy_units(s):
    for a, b in UNITS:
        s = re.sub(a, b, s)
    return s


def num(x):
    return f'{x:g}' if isinstance(x, float) else str(x)


def size_text(v):
    """Pack size in Armenian: '1.5 կգ', '12 × 85 գ', '30 հատ'."""
    m = re.search(r'(\d+)\s*[×x]\s*([\d.,]+)\s*(kg|g|ml|l)\b', v.get('name') or '')
    if m:
        return f'{m.group(1)} × {m.group(2).replace(",", ".")} {hy_units(m.group(3))}'
    if v.get('size_label'):
        return hy_units(v['size_label'])
    c, mt = v.get('content'), v.get('measure_type')
    if c and mt:
        c = float(c)
        if mt == 'mass':
            s = f'{num(c / 1000)} կգ' if c >= 1000 else f'{num(c)} գ'
        elif mt == 'volume':
            s = f'{num(c / 1000)} լ' if c >= 1000 else f'{num(c)} մլ'
        else:
            s = f'{num(c)} հատ'
        n = v.get('pack_count') or 1
        return f'{n} × {s}' if n > 1 else s
    return ''


def plain(h, limit=300):
    h = re.sub(r'(?i)</(li|p|h\d)>|<br\s*/?>', ' ։ ', h or '')   # (Armenian full stop) list items / paragraphs end a sentence
    t = html.unescape(re.sub(r'<[^>]+>', ' ', h))
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'\s+(?=[.,;:!?։])', '', t)                          # "word ." -> "word."
    t = re.sub(r'([.,;:!?։])[.։]+', r'\1', t)                       # "։։" / ":։" / ".." -> one mark
    t = re.sub(r'^[\s.։]+', '', t).strip()
    t = re.sub(r'(^|[.!?։] )(\w)', lambda m: m.group(1) + m.group(2).upper(), t)   # each sentence starts upper-case
    if len(t) <= limit:
        return t
    cut = t[:limit]
    i = max(cut.rfind('։'), cut.rfind('. '), cut.rfind('! '))
    return (cut[:i + 1] if i > limit // 3 else cut.rsplit(' ', 1)[0] + '…').strip()


def load(dirname, ids):
    out = {}
    for f in glob.glob(os.path.join(ROOT, '.siruk-cache/live', dirname, '*.json')):
        b = os.path.basename(f)[:-5]
        if not b.isdigit() or (ids and int(b) not in ids):
            continue
        d = json.load(open(f))
        out[int(b)] = d.get('data', d)
    return out


def api_get(path):
    r = subprocess.run([os.path.join(ROOT, 'scripts/api.sh'), 'GET', path], capture_output=True,
                       text=True, cwd=ROOT, timeout=120, env=dict(os.environ, SIRUK_NO_PACE='1'))
    i = r.stdout.find('{')
    return json.loads(r.stdout[i:]) if i >= 0 else None


def jload(p):
    try:
        return json.load(open(p))
    except Exception:
        return {}


def jsave(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    json.dump(d, open(tmp, 'w'), ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def media(mid, cache):
    k = str(mid)
    if k not in cache:
        d = api_get(f'/medias/{mid}')
        d = (d or {}).get('data') or {}
        cache[k] = {'url': d.get('originalUrl') or d.get('url'), 'dimensions': d.get('dimensions'),
                    'filename': d.get('filename')}
        jsave(MEDIA_CACHE, cache)
    return cache[k]


def fetch(url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def square_jpeg(raw, side=500):
    """The photo, whole and centred on a white side×side square (Glovo asks for 500×500)."""
    im = Image.open(io.BytesIO(raw))
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        bg = Image.new('RGB', im.size, 'white')
        bg.paste(im, mask=im.split()[-1])
        im = bg
    im = im.convert('RGB')
    k = side / max(im.size)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    sq = Image.new('RGB', (side, side), 'white')
    sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    out = io.BytesIO()
    sq.save(out, 'JPEG', quality=90)
    return out.getvalue()


KEY_AT = [0]    # which line of .imgbb-key is in use; moves on when a key hits the cap


class RateLimited(Exception):
    """ImgBB's undocumented upload cap (hit after ~1,030 uploads on 2026-10-26)."""


def _imgbb_upload(jpeg, name):
    """Upload through ImgBB's official API (api.imgbb.com/1/upload, key in .imgbb-key);
    no expiration, so the link is permanent. Returns the direct link (data.url)."""
    keys = [k.strip() for k in open(os.path.join(ROOT, '.imgbb-key')) if k.strip()]
    if not keys[KEY_AT[0]:]:
        raise RateLimited('every key in .imgbb-key is rate limited')
    key = keys[KEY_AT[0]]
    boundary = '----siruk' + str(int(time.time() * 1000))
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="key"\r\n\r\n{key}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="name"\r\n\r\n{name}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}.jpg"\r\n'
            f'Content-Type: image/jpeg\r\n\r\n').encode() + jpeg + f'\r\n--{boundary}--\r\n'.encode()
    for attempt in range(4):
        try:
            r = json.loads(fetch('https://api.imgbb.com/1/upload', body,
                                 {'Content-Type': f'multipart/form-data; boundary={boundary}'}, timeout=120))
            if 'rate limit' in str(r).lower():
                raise RateLimited(str(r)[:200])
            url = (r.get('data') or {}).get('url')
            if r.get('success') and url:
                return url
            raise RuntimeError(f'imgbb answered {str(r)[:200]}')
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')
            if 'rate limit' in msg.lower():
                raise RateLimited(msg[:200])
            if attempt == 3:
                raise
            time.sleep(10 * (attempt + 1))
        except RateLimited:
            raise
        except Exception:
            if attempt == 3:
                raise
            time.sleep(10 * (attempt + 1))      # rate limit / transient error: back off


def imgbb_upload(jpeg, name):
    """_imgbb_upload, moving to the next key of .imgbb-key when one hits the cap
    (ImgBB okayed a second key by phone, user 2026-10-26)."""
    while True:
        try:
            return _imgbb_upload(jpeg, name)
        except RateLimited:
            n = len([k for k in open(os.path.join(ROOT, '.imgbb-key')) if k.strip()])
            if KEY_AT[0] + 1 >= n:
                raise
            KEY_AT[0] += 1
            print(f'ImgBB key {KEY_AT[0]} hit the cap, switching to key {KEY_AT[0] + 1}', file=sys.stderr)


def slug_file(s):
    return (re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-') or 'image')[:80] + '.jpg'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'final/glovo/siruk-glovo-products.xlsx'))
    ap.add_argument('--upload', action='store_true', help='make 500×500 squares and upload them to ImgBB (cached; the video used postimages.org)')
    ap.add_argument('--ids', type=int, nargs='*')
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()

    if a.upload and not os.path.exists(os.path.join(ROOT, '.imgbb-key')):
        sys.exit('no .imgbb-key: get a key at api.imgbb.com and save it there')
    ids = set(a.ids or [])
    en, hy = load('products', ids), load('products-hy', ids)
    cats = json.load(open(os.path.join(ROOT, '.siruk-cache/glovo-categories-hy.json')))['data']
    node, parent = {}, {}

    def walk(n, p=None):
        node[n['id']] = n['name']
        parent[n['id']] = p
        for c in n.get('children') or []:
            walk(c, n['id'])
    for n in cats:
        walk(n)

    def root(c):
        while parent.get(c):
            c = parent[c]
        return c

    def group(c):
        while parent.get(c) and parent.get(parent[c]):
            c = parent[c]
        return c

    brands = {b['id']: b['name'] for b in (api_get('/brands?per_page=500') or {}).get('data', [])}
    mcache, pcache = jload(MEDIA_CACHE), jload(IMGBB_CACHE)

    rows, problems = [], []
    limited = False
    for pid in sorted(en):
        p, ph = en[pid], hy.get(pid) or en[pid]
        if p.get('is_discontinued'):
            continue
        leaves = [c for c in p.get('category_ids') or [] if c in node]
        pets = []
        for c in leaves:
            r = PET.get(root(c))
            if r and r not in pets:
                pets.append(r)
        pet = ' և '.join(pets) + ' համար' if pets else ''
        sections = []
        for c in leaves:
            s = f'{node[c]} {PET[root(c)]} համար' if root(c) in PET else node[c]
            if s not in sections:
                sections.append(s)
        lead = leaves[0] if leaves else None
        kind = KIND_LEAF.get(lead) or KIND_GROUP.get(group(lead) if lead else None) or ''
        name_hy = (ph.get('name') or p['name']).strip()
        brand = brands.get(p.get('brand_id'), '')
        hy_vars = {v['id']: v for v in ph.get('variants') or []}
        seen = {}                     # option attribute -> labels across the variants
        for vv in hy_vars.values():
            for a_ in vv.get('attribute_value_labels') or []:
                if a_.get('role') == 'option':
                    seen.setdefault(a_['attributeId'], set()).add(a_.get('label'))
        varying = {k for k, labels in seen.items() if len(labels) > 1}   # only what tells variants apart
        for v in p.get('variants') or []:
            vh = hy_vars.get(v['id'], v)
            if not v.get('price'):
                problems.append((p['id'], v.get('sku'), 'no price — left out'))
                continue
            opts = [a_['label'] for a_ in vh.get('attribute_value_labels') or []
                    if a_.get('role') == 'option' and a_.get('label') and a_['attributeId'] in varying]
            size = size_text(vh)
            if size:
                opts = [o for o in opts if o not in size and size not in o]
            def known(x):     # already said by the name, the size or an option
                n = x.replace(',', '.').lower()
                return (n in name_hy.replace(',', '.').lower() or n == size.replace(',', '.').lower()
                        or any(n in o.lower() or o.lower() in n for o in opts))
            nh = name_hy.replace(',', '.').lower()
            opts = [o for o in opts if o.replace(',', '.').lower() not in nh]
            if not size and not opts and len(p.get('variants') or []) > 1 and not known(hy_units(v.get('name') or '')):
                opts = [hy_units(v.get('name') or '')]
            for part in (v.get('name') or '').split(', '):   # a collar's "35–41 cm/15 mm" is not an option
                part = hy_units(part.strip())
                if size and part.replace(',', '.') == size:            # "1 × 5 g" is the size itself
                    continue
                if size:
                    part = re.sub(r'\s*[\d.,]+\s*(գ|կգ|մլ|լ|հատ)$', '', part)    # "Tuna 415 g" -> "Tuna"
                if (re.search(r'\d', part) and not known(part)
                        and not (size and re.fullmatch(r'[\d.,]+\s*(գ|կգ|մլ|լ|հատ)', part))):   # "1,800 g" = the size
                    opts.append(part)
            head = descr = ''
            rest = name_hy
            m = re.search(r',\s*([^,]*\bհամար)\s*$', name_hy)
            if m and re.match(r'[A-Za-z0-9]', name_hy):     # "Classics Red Meat, չոր կեր շների համար"
                descr, rest = m.group(1).strip(), name_hy[:m.start()].strip()
            elif (re.match(r'[A-Za-z0-9]', name_hy) and kind      # "Instinctive 7+" says nothing of what it is
                  and kind.split()[0].lower() not in name_hy.lower()):
                descr = kind if 'համար' in name_hy else f'{kind} {pet}'.strip()
            elif (kind and lead and (group(lead) in (6, 14, 15, 16, 97, 101) or lead in KIND_LEAF)
                  and kind.split()[0].lower() not in name_hy.lower()):   # "Նապաստակ" -> a toy, for dogs
                descr = kind if 'համար' in name_hy else f'{kind} {pet}'.strip()
            if descr:
                descr = descr[0].upper() + descr[1:]
                head = f'{descr} «{brand}» {rest}' if brand else f'{descr} {rest}'
            else:
                head = f'{name_hy} «{brand}»' if brand else name_hy
            title = ', '.join([head] + opts + ([size] if size else []))
            bc = (v.get('barcode') or '').strip()
            if re.fullmatch(r'\d{12}', bc):        # UPC-A (Acana) -> its EAN-13 form; Glovo takes 8/13/14 only
                bc = '0' + bc                      # (Glovo file only: Siruk keeps the code as scanned)
            elif re.fullmatch(r'\d{5}', bc):       # scale PLU of a loose 1 kg / 100 g variant -> 8 digits
                bc = bc.zfill(8)                   # (user 2026-10-26: "do the 0 padding"; Glovo file only)
            bc = bc if re.fullmatch(r'\d{8}|\d{13}|\d{14}', bc) else ''
            desc = plain(vh.get('about_this_item')) or plain(v.get('about_this_item'))
            img = ''
            imgs = v.get('images') or []
            if not imgs:
                problems.append((p['id'], v['sku'], 'no image'))
            else:
                m = media(imgs[0], mcache)
                img = m.get('url') or ''
                if a.upload and not limited:
                    k = str(imgs[0])
                    if k not in pcache:
                        try:
                            jpeg = square_jpeg(fetch(img))
                            pcache[k] = imgbb_upload(jpeg, f'siruk-m{k}')
                            jsave(IMGBB_CACHE, pcache)
                            time.sleep(1)
                        except RateLimited as e:
                            limited = True
                            print(f'ImgBB rate limit — uploads stopped, re-run --upload later: {e}', file=sys.stderr)
                        except Exception as e:
                            problems.append((p['id'], v['sku'], f'upload failed: {e}'))
                img = pcache.get(str(imgs[0]), img)          # an earlier upload counts without --upload too
                if 'i.ibb.co' not in img:
                    problems.append((p['id'], v['sku'], 'no 500×500 ImgBB link (Siruk original url used)'))
            avail = 1 if v.get('stock_status') == 'in_stock' and v.get('is_purchasable', True) else 0
            price = v['price']
            price = int(price) if float(price).is_integer() else round(float(price), 2)
            rows.append([v.get('sku') or f'siruk-{v["id"]}', bc, title, img, desc, price, avail,
                         *(sections + ['', '', ''])[:3]])
            if a.limit and len(rows) >= a.limit:
                break
        if a.limit and len(rows) >= a.limit:
            break

    wb = openpyxl.load_workbook(TEMPLATE)
    ws = wb.active
    for i, r in enumerate(rows, start=3):
        for j, val in enumerate(r, start=1):
            ws.cell(row=i, column=j, value=val if val != '' else None)
        ws.cell(row=i, column=1).number_format = '@'
        ws.cell(row=i, column=2).number_format = '@'
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    wb.save(a.out)
    rep = os.path.splitext(a.out)[0] + '-problems.csv'
    with open(rep, 'w') as f:
        f.write('product_id,sku,problem\n')
        for pr in problems:
            f.write(','.join('"%s"' % str(x).replace('"', "'") for x in pr) + '\n')
    print(f'{len(rows)} variant rows -> {a.out}')
    print(f'{len(problems)} problems -> {rep}')
    if limited:
        sys.exit(3)


if __name__ == '__main__':
    main()
