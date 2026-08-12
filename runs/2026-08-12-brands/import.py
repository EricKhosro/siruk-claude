#!/usr/bin/env python3
"""Generic importer: plan.json + extract.json -> Siruk admin API.

    ./import.py <plan.json> <extract.json> <brand_id> [product_key ...]

Resumable and idempotent: it records product_key -> admin id in
.siruk-cache/<plan-stem>-created.json and skips keys already created.
Images are uploaded through scripts/upload-media.sh (which caches url -> media
id), so re-running never re-uploads.

Rich text is built from the extraction: `about_this_item` from the page
description + bullet/benefit lists, `ingredient_information` from the
Composition / Analytical / Nutritional sections, `feeding_instructions` from a
Feeding guide / Feeding table section when the page has one.
"""
import json, os, re, subprocess, sys, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(ROOT) if os.path.basename(ROOT) == 'runs' else ROOT
CACHE = os.path.join(ROOT, '.siruk-cache')
SCRIPTS = os.path.join(ROOT, 'scripts')


def sh(args, inp=None):
    r = subprocess.run(args, capture_output=True, text=True, input=inp, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed:\n{r.stderr[-2000:]}")
    return r.stdout.strip()


def esc(t):
    return html.escape(t, quote=False)


def para(text):
    """Plain text with newlines -> <p> blocks."""
    if not text:
        return ''
    return ''.join(f'<p>{esc(l.strip())}</p>' for l in text.split('\n') if l.strip())


def bullets(items):
    items = [i.strip() for i in items or [] if i and i.strip()]
    if not items:
        return ''
    return '<ul>' + ''.join(f'<li>{esc(i)}</li>' for i in items) + '</ul>'


def about(e):
    out = para(e.get('description') or '')
    b = list(e.get('bullets') or [])
    # some pages put the bullet list inside one <li> separated by newlines
    b = [x for i in b for x in i.split('\n')]
    out += bullets(b)
    ben = e.get('benefits') or []
    if ben:
        out += bullets(ben)
    return out or None


ING_KEYS = [  # brit
            'Composition', 'Analytical ingredients', 'Nutritional composition',
            'Additives', 'Zootechnical additives', 'Technological additives',
            'Sensory additives', 'Contains EU approved antioxidants',
            'Contains natural antioxidants', 'Metabolizable energy',
            # bewital (belcando / leonardo)
            "That's in it", 'Made without',
            # canvit
            'COMPOSITION', 'NUTRITIONAL ADDITIVES PER KG', 'ANALYTICAL CONSTITUENTS',
            'ADDITIVES PER KG', 'ZOOTECHNICAL ADDITIVES', 'TECHNOLOGICAL ADDITIVES',
            # schesir
            'Analytical Constituents', 'Analytical constituents', 'Nutritional additives/kg']
FEED_KEYS = ['Feeding guide', 'Feeding table', 'Dosage', 'Recommended daily dose',
             'Instructions for use', 'Usage', 'Feeding recommendation',
             'Feeding recommendations', 'Instructions', 'Storage']

# sub-headings brand pages run inline with their body text; break them onto
# their own line so the rendered block keeps its structure
INLINE_HEADS = ['Composition', 'Analytical constituents', 'Additives per kg',
                'Nutritional additives', 'Technological additives',
                'Sensory additives', 'Zootechnical additives']
_INLINE_RE = re.compile(r'(?<!\n)\b(' + '|'.join(INLINE_HEADS) + r') (?=[A-Z0-9])')


def sections_html(e, keys):
    sec = e.get('sections') or {}
    parts = []
    for k in keys:
        if sec.get(k):
            body = _INLINE_RE.sub(lambda m: '\n' + m.group(1) + ': ', sec[k])
            parts.append(f'<p><strong>{esc(k)}:</strong></p>' + para(body))
    return ''.join(parts) or None


def main():
    plan_path, extract_path, brand_id = sys.argv[1], sys.argv[2], int(sys.argv[3])
    only = set(sys.argv[4:])
    plan = json.load(open(plan_path))
    extracts = {}
    for e in json.load(open(extract_path)):
        extracts[e['url'].rstrip('/').split('/')[-1]] = e
        if e.get('handle'):
            extracts[e['handle']] = e

    stem = os.path.splitext(os.path.basename(plan_path))[0]
    created_path = os.path.join(CACHE, f'{stem}-created.json')
    created = json.load(open(created_path)) if os.path.exists(created_path) else {}
    os.makedirs(CACHE, exist_ok=True)

    for p in plan:
        key = p['key']
        if only and key not in only:
            continue
        if key in created:
            print(f'-- {key}: already created as product {created[key]}, skipping')
            continue

        variants = []
        for i, v in enumerate(p['variants']):
            e = extracts.get(v['src'], {})
            # prefer the page's full gallery when it has one, else the single
            # main image; cap at 3 as the Royal Canin run did
            urls = (e.get('images') or ([e['image']] if e.get('image') else []))[:3]
            imgs = []
            for url in urls + (v.get('extra_images') or []):
                try:
                    imgs.append(int(sh([os.path.join(SCRIPTS, 'upload-media.sh'), url])))
                except Exception as ex:
                    print(f'   ! image failed ({url}): {ex}', file=sys.stderr)
            vo = {
                'name': v['label'], 'sku': v['sku'],
                'pricing_type': v['pricing'],
                'cost_price': v['cost'], 'stock': v['stock'],
                'min_allowed_price': 0, 'compare_at_price': None,
                'weight': v['weight'],
                'is_default': i == 0, 'vendor_stock': False, 'sort_order': i,
                'images': imgs,
                'about_this_item': about(e),
                'ingredient_information': sections_html(e, ING_KEYS),
                'feeding_instructions': sections_html(e, FEED_KEYS),
            }
            if v['pricing'] == 'per_kg':
                vo['price_per_kg'] = round(v['price'] / v['weight'], 2)
                vo['price'] = 0
            else:
                vo['price'] = v['price']
            if v.get('attrs'):
                vo['attribute_value_ids'] = v['attrs']
            variants.append(vo)

        payload = {
            'name': p['name'], 'slug': p['slug'],
            'category_ids': p['category_ids'], 'brand_id': brand_id,
            'attribute_family_id': p.get('family'),
            'is_best_seller': False, 'is_on_sale': False,
            'variants': variants,
        }
        path = os.path.join(CACHE, f'payload-{key}.json')
        json.dump(payload, open(path, 'w'), ensure_ascii=False, indent=1)

        env = dict(os.environ, FORCE='1')
        r = subprocess.run([os.path.join(SCRIPTS, 'create-product.sh'), path],
                           capture_output=True, text=True, cwd=ROOT, env=env)
        m = re.search(r'created product (\d+)', r.stderr + r.stdout)
        if not m:
            print(f'!! {key}: FAILED\n{r.stderr[-1500:]}', file=sys.stderr)
            continue
        pid = int(m.group(1))
        created[key] = pid
        json.dump(created, open(created_path, 'w'), indent=1)
        print(f'== {key}: product {pid}  ({len(variants)} variant(s))')


if __name__ == '__main__':
    main()
