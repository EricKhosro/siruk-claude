#!/usr/bin/env python3
"""Import the planned Schesir products into the Siruk admin.

    scripts/import-schesir.py --dry-run          # show payloads, touch nothing
    scripts/import-schesir.py --limit 5          # do the first 5 products
    scripts/import-schesir.py                    # do all of them

Content comes from the cached schesir.com catalogue plus the product page's
accordion blocks (Composition / Nutritional additives / Description / Feeding
recommendation / Storage). Images are uploaded through scripts/upload-media.sh
so they are alpha-flattened, sanitized and verified readable.

A product whose rows already exist in the catalogue (matched on SKU) is UPDATED:
its variant list is rebuilt from a fresh GET so nothing is silently dropped.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import urllib.request

PLAN = '.siruk-cache/schesir-plan.json'
CAT = '.siruk-cache/sources/schesir.jsonl'
MENU = 'reference/attribute-values.json'
PAGE_CACHE = '.siruk-cache/schesir-pages'
MEDIA_CACHE = '.siruk-cache/schesir-media.json'
BRAND_ID = 10                     # Schesir
FAMILY = {'wet': 2, 'dry': 1, 'treat': 3, 'supplement': 4}
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126 Safari/537.36')

FLAV_ALIAS = {'Carrots': 'Carrot'}
TEX_MAP = {'Paté': 'Pate', 'Jelly': 'Chunks in Jelly', 'Mousse': 'Mousse',
           'Broth': 'Broth', 'Mousse & Shreds': 'Mousse & Shreds'}
CONT_MAP = {'Can': 'Can', 'Pouch': 'Pouch', 'Bag': 'Bag', 'Alutray': 'Tray'}

missing_vocab = {}


def sh(cmd, inp=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, input=inp)
    return r.returncode, r.stdout, r.stderr


def api(method, path, payload=None):
    if payload is None:
        code, out, err = sh(f'./scripts/api.sh {method} {path}')
    else:
        code, out, err = sh(f'./scripts/api.sh {method} {path} -',
                            inp=json.dumps(payload))
    body = '\n'.join(l for l in out.splitlines() if not l.startswith('HTTP'))
    # api.sh reports the status line on stderr
    status = next((l for l in (err + '\n' + out).splitlines()
                   if l.startswith('HTTP')), '')
    try:
        return status, json.loads(body)
    except Exception:
        return status, {'raw': body, 'err': err}


# ------------------------------------------------------------------ content

def strip_tags(s):
    s = re.sub(r'(?is)<(script|style|svg)[^>]*>.*?</\1>', '', s)
    s = re.sub(r'(?s)<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def fetch_page(handle):
    os.makedirs(PAGE_CACHE, exist_ok=True)
    p = os.path.join(PAGE_CACHE, handle + '.html')
    if not os.path.exists(p):
        url = f'https://www.schesir.com/en/products/{handle}'
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                open(p, 'wb').write(r.read())
        except Exception as e:
            print(f'    ! page fetch failed {handle}: {e}')
            return {}
    h = open(p, encoding='utf-8', errors='ignore').read()
    out = {}
    for blk in re.findall(
            r'(?is)<details[^>]*class="[^"]*cc-accordion-item[^"]*"[^>]*>(.*?)</details>', h):
        m = re.search(r'(?is)<summary[^>]*>(.*?)</summary>', blk)
        if not m:
            continue
        out[strip_tags(m.group(1))] = strip_tags(blk[m.end():])
    return out


def para(text):
    return ''.join(f'<p>{html.escape(x.strip())}</p>'
                   for x in re.split(r'(?<=[.;])\s+(?=[A-Z])', text) if x.strip())


def build_content(site, sections):
    about = ''
    desc = sections.get('Description') or strip_tags(site.get('body_html') or '')
    if desc:
        about = para(desc)
    bullets = [t for t in site.get('tags', [])
               if t not in ('Gatto', 'Cane', 'Umido', 'Secco')]
    if bullets:
        about += '<ul>' + ''.join(f'<li>{html.escape(b)}</li>' for b in bullets) + '</ul>'
    ing = ''
    if sections.get('Composition'):
        ing += '<p><strong>Composition:</strong></p>' + para(sections['Composition'])
    for k in ('Analytical constituents', 'Nutritional additives/kg'):
        if sections.get(k):
            ing += f'<p><strong>{k}:</strong></p>' + para(sections[k])
    feed = ''
    if sections.get('Feeding recommendation'):
        feed += '<p><strong>Feeding recommendation:</strong></p>' + \
                para(sections['Feeding recommendation'])
    if sections.get('Storage'):
        feed += '<p><strong>Storage:</strong></p>' + para(sections['Storage'])
    return about, ing, feed


# ------------------------------------------------------------------ media

def load_media_cache():
    return json.load(open(MEDIA_CACHE)) if os.path.exists(MEDIA_CACHE) else {}


def save_media_cache(c):
    json.dump(c, open(MEDIA_CACHE, 'w'), indent=1)


def upload_images(urls, cache, dry):
    ids = []
    for u in urls:
        base = u.split('?')[0]
        if base in cache:
            ids.append(cache[base])
            continue
        if dry:
            ids.append(f'<upload {os.path.basename(base)}>')
            continue
        code, out, err = sh(f"./scripts/upload-media.sh '{base}' schesir")
        m = re.search(r'\b(\d{2,6})\s*$', out.strip())
        if code == 0 and m:
            cache[base] = int(m.group(1))
            ids.append(int(m.group(1)))
            save_media_cache(cache)
        else:
            print(f'    ! image failed {base}\n      {(err or out).strip()[:200]}')
    return ids


# ------------------------------------------------------------------ mapping

def vocab(menu, key, label):
    if label is None:
        return None
    v = menu[key]['values'].get(label)
    if v is None:
        missing_vocab.setdefault(key, set()).add(label)
    return v


def weight_label(g):
    if g is None:
        return None
    if g >= 1000 and g % 1000 == 0:
        return f'{int(g // 1000)} kg'
    if g >= 1000:
        return f'{g / 1000:g} kg'
    return f'{int(g)} g'


def kind_of(p):
    raw = ' '.join(v['raw'] for v in p['variants']).upper()
    if 'FISH OIL' in raw or 'OMEGA' in raw:
        return 'supplement'
    if p['line'] in ('Stix', 'Snack', 'Snax') or 'SNACK' in raw or 'STIX' in raw:
        return 'treat'
    return p['form'] or 'wet'


def category_of(p, kind):
    sp = p['species']
    if kind == 'supplement':
        return [12], None
    if kind == 'treat':
        if sp == 'dog':
            return [6], None
        return [8], 'cat treats have no Treat category (tree has Dog>Treat only)'
    if kind == 'dry':
        return ([3], None) if sp == 'dog' else ([10], None)
    return ([4], None) if sp == 'dog' else ([11], None)


def attrs_for(p, v, menu, kind):
    a = {}
    if kind != 'dry':                       # per_kg derives weight from pack weight
        w = vocab(menu, 'product-weight', weight_label(v['unit_g']))
        if w:
            a['product-weight'] = w
    ff = {'dry': 'Dry', 'wet': 'Wet', 'treat': 'Wet', 'supplement': 'Liquid'}[kind]
    if kind == 'treat':
        ff = 'Dry'
    a['food-form'] = vocab(menu, 'food-form', ff)
    life = {'Puppy/Kitten': 'Kitten' if p['species'] == 'cat' else 'Puppy',
            'Senior': 'Senior'}.get(p['lifestage'], 'Adult')
    a['lifestage'] = vocab(menu, 'lifestage', life)
    # Schesir names read "<base> with <qualifier>" — the qualifier is what makes
    # this variant different from its siblings, so it is the flavor we store.
    # (A single id per variant; multi-value attributes are an open dev question.)
    flavs = [FLAV_ALIAS.get(f.strip(), f.strip())
             for f in v['flavor'].split('&') if f.strip() != '(plain)']
    for f in reversed(flavs):
        fid = vocab(menu, 'flavor', f)
        if fid:
            a['flavor'] = fid
            break
    # texture is a variant axis, so read it off the variant; p['texture'] is
    # only set when every sibling shares it
    t = TEX_MAP.get(v.get('texture') or p['texture'])
    if t:
        tid = vocab(menu, 'texture', t)
        if tid:
            a['texture'] = tid
    c = CONT_MAP.get(p['container'])
    if c:
        cid = vocab(menu, 'packaging', c)
        if cid:
            a['packaging'] = cid
    return {k: v2 for k, v2 in a.items() if v2}


def slugify(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--only', help='substring of the product name')
    args = ap.parse_args()

    plan = json.load(open(PLAN))
    menu = json.load(open(MENU))
    cat = {}
    for ln in open(CAT, encoding='utf-8'):
        p = json.loads(ln)
        cat[p['handle']] = p
    media_cache = load_media_cache()

    # existing catalogue: sku -> (product_id, variant_id)
    _, existing = api('GET', '/products?per_page=300')
    sku_index, pid_name = {}, {}
    for page in range(1, 6):
        _, d = api('GET', f'/products?page={page}')
        for prod in d.get('data', []):
            if prod.get('brand') != 'Schesir':
                continue
            _, full = api('GET', f'/products/{prod["id"]}')
            fd = full.get('data', {})
            pid_name[prod['id']] = fd.get('name')
            for var in fd.get('variants', []):
                sku_index[str(var.get('sku'))] = (prod['id'], var.get('id'))

    todo = [p for p in plan if p['matched'] > 0]
    if args.only:
        todo = [p for p in todo if args.only.lower() in p['name'].lower()]
    if args.limit:
        todo = todo[:args.limit]

    created = updated = failed = skipped = 0
    report = []
    for p in todo:
        kind = kind_of(p)
        cats, catflag = category_of(p, kind)
        name = p['name']
        slug = slugify('schesir ' + name)
        target_pid = next((sku_index[v['sku']][0] for v in p['variants']
                           if v['sku'] in sku_index), None)

        variants = []
        for v in p['variants']:
            site = cat.get(v['handle'] or '')
            if not site:
                continue
            sections = fetch_page(site['handle'])
            about, ing, feed = build_content(site, sections)
            imgs = [i['src'] for i in site.get('images', [])[:3]]
            media = upload_images(imgs, media_cache, args.dry_run)
            g = v['unit_g'] or 0
            var = dict(
                name=v.get('label') or (v['flavor'] if v['flavor'] != '(plain)'
                                        else weight_label(g)),
                about_this_item=about, ingredient_information=ing,
                feeding_instructions=feed,
                sku=str(v['sku']), cost_price=v['cost'] or 0,
                compare_at_price=None, min_allowed_price=0,
                weight=round(g / 1000, 3), is_default=not variants,
                stock=10, vendor_stock=False, sort_order=len(variants),
                images=media, attribute_value_ids=attrs_for(p, v, menu, kind))
            if kind == 'dry' and g:
                var['pricing_type'] = 'per_kg'
                var['price_per_kg'] = round(v['price'] / (g / 1000), 2)
                var['price'] = 0
            else:
                var['pricing_type'] = 'fixed'
                var['price'] = v['price']
            variants.append(var)

        if not variants:
            skipped += 1
            continue

        # guard: the API rejects duplicate attribute combinations
        combos = {}
        for var in variants:
            key = tuple(sorted(var['attribute_value_ids'].items()))
            combos.setdefault(key, []).append(var['sku'])
        dupes = {k: v for k, v in combos.items() if len(v) > 1}

        body = dict(name=name, slug=slug, category_ids=cats, brand_id=BRAND_ID,
                    attribute_family_id=FAMILY.get(kind), is_best_seller=False,
                    is_on_sale=False, variants=variants)

        line = dict(name=name, kind=kind, species=p['species'],
                    variants=len(variants), skus=[v['sku'] for v in p['variants']],
                    dupes=list(dupes.values()), cat_flag=catflag)

        if args.dry_run:
            print(f"\n=== {name}  [{p['species']}/{kind}] cats={cats} "
                  f"{'UPDATE ' + str(target_pid) if target_pid else 'CREATE'}")
            for var in variants:
                print(f"   {var['sku']:10s} {var['name']:26s} "
                      f"{var['pricing_type']:7s} price={var.get('price')} "
                      f"ppk={var.get('price_per_kg','-')} w={var['weight']} "
                      f"imgs={len(var['images'])} attrs={var['attribute_value_ids']}")
            if dupes:
                print(f"   !! duplicate attribute combos: {list(dupes.values())}")
            if catflag:
                print(f"   !! {catflag}")
            report.append(line)
            continue

        if dupes:
            print(f'SKIP {name}: duplicate attribute combos {list(dupes.values())}')
            line['status'] = 'skipped-duplicate-attrs'
            report.append(line)
            skipped += 1
            continue

        if target_pid:
            st, cur = api('GET', f'/products/{target_pid}')
            cd = cur.get('data', {})
            by_sku = {str(x.get('sku')): x.get('id') for x in cd.get('variants', [])}
            for var in variants:
                if var['sku'] in by_sku:
                    var['id'] = by_sku[var['sku']]
            body['name'] = name
            body['slug'] = cd.get('slug') or slug
            st, res = api('PUT', f'/products/{target_pid}', body)
            good = 'HTTP 200' in st
            print(f"{'OK  ' if good else 'FAIL'} update {target_pid} {name} "
                  f"({len(variants)}v)")
            if not good:
                print('     ', json.dumps(res)[:300])
            line['status'] = 'updated' if good else 'failed'
            line['id'] = target_pid
            updated += good
            failed += not good
        else:
            st, res = api('POST', '/products', body)
            good = 'HTTP 201' in st or 'HTTP 200' in st
            pid = res.get('data', {}).get('id')
            print(f"{'OK  ' if good else 'FAIL'} create {pid} {name} ({len(variants)}v)")
            if not good:
                print('     ', json.dumps(res)[:300])
            line['status'] = 'created' if good else 'failed'
            line['id'] = pid
            created += good
            failed += not good
        report.append(line)

    json.dump(report, open('.siruk-cache/schesir-import-report.json', 'w'),
              ensure_ascii=False, indent=1)
    print(f'\ncreated={created} updated={updated} failed={failed} skipped={skipped}')
    if missing_vocab:
        print('\nwanted but missing vocabulary:')
        for k, v in missing_vocab.items():
            print(f'  {k}: {sorted(v)}')


if __name__ == '__main__':
    main()
