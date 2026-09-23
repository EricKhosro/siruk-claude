#!/usr/bin/env python3
"""Recompute Schesir product names and rename where they improve.

The first import derived names from the site titles, which left artefacts:
names beginning "in ", bare ingredient words ("Peas 85g"), a duplicated
lifestage ("Medium Puppy Puppy/Kitten 12kg"), stray single letters and one
product with no name at all.

Rules (reference/product-rules.md "Product vs variant"):
  * the Name never contains the brand — the storefront prints it separately
  * a single-variant product MAY carry its flavor; a multi-variant one must not,
    because flavor is the variant axis
  * shape: [Line] [Flavor|Descriptor] [Lifestage] [in Texture] [Multipack]
           <size> [Pouch|Tray]

    scripts/fix-schesir-names.py            # show proposed renames
    scripts/fix-schesir-names.py --apply    # PUT them
"""
import argparse
import json
import re
import subprocess

PLAN = '.siruk-cache/schesir-plan.json'

# Words that are ingredients/flavors rather than a range identity. When a base
# reduces to only these, the product is named from its flavor instead.
INGREDIENTY = {
    'PEAS', 'CARROTS', 'CARROT', 'SPINACH', 'PUMPKIN', 'POTATOES', 'ROSMARY',
    'ROSEMARY', 'APPLE', 'ALOE', 'HERRING', 'SEABASS', 'COUS', 'PAPAYA',
    'PINEAPPLE', 'SURIMI', 'ANCHOVIES', 'PRAWNS', 'SQUID', 'EGG', 'HAM',
    'RICE', 'WHEAT', 'GRASS', 'PUREE', 'BREAK', 'MELA',
}
JUNK = {'E', 'G', 'M', 'S', 'W', 'C', 'D', 'N', 'POLLO', 'UOVO', 'MANZO',
        'TONNO', 'SALMONE', 'PESCE', 'AGNELLO', 'CONIGLIO', 'ANATRA'}
ITAL = {'Pollo': 'Chicken', 'Uovo': 'Egg', 'Manzo': 'Beef', 'Tonno': 'Tuna',
        'Salmone': 'Salmon', 'Pesce': 'Fish', 'Agnello': 'Lamb',
        'Coniglio': 'Rabbit', 'Anatra': 'Duck', 'Cous Cous': 'Couscous'}


def sh(cmd, inp=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, input=inp)
    return r.returncode, r.stdout, r.stderr


def api(method, path, payload=None):
    if payload is None:
        _, out, err = sh(f'./scripts/api.sh {method} {path}')
    else:
        _, out, err = sh(f'./scripts/api.sh {method} {path} -', inp=json.dumps(payload))
    body = '\n'.join(l for l in out.splitlines() if not l.startswith('HTTP'))
    status = next((l for l in (err + '\n' + out).splitlines()
                   if l.startswith('HTTP')), '')
    try:
        return status, json.loads(body)
    except Exception:
        return status, {'raw': body, 'err': err}


def size_label(g):
    if g is None:
        return None
    if g >= 1000 and g % 1000 == 0:
        return f'{int(g // 1000)}kg'
    if g >= 1000:
        return f'{g / 1000:g}kg'
    return f'{int(g)}g'


def clean_base(name, line, texture, size, container, lifestage):
    """Strip everything the new name rebuilds, leaving the descriptor."""
    t = name
    for junk in (line or '', f'in {texture}' if texture else '', size or '',
                 'Multipack', 'Pouch', 'Tray', 'Puppy/Kitten', 'Senior',
                 container or ''):
        if junk:
            t = t.replace(junk, ' ')
    toks = [w for w in re.split(r'[\s&]+', t) if w]
    toks = [w for w in toks if w.upper() not in JUNK and not w.isdigit()]
    if not toks or all(w.upper() in INGREDIENTY for w in toks):
        return None
    return ' '.join(ITAL.get(w, w) for w in toks)


def tidy_title(title, p, size):
    """Turn a schesir.com title into a storefront product name."""
    t = re.sub(r'\s+', ' ', title).strip()
    t = re.sub(r'(?i)\bin (can|pouch|bag|alutray)\b', '', t)      # container word
    t = re.sub(r'(?i)\brich in\b', '', t)
    t = re.sub(r'(?i)\bcon\b', 'with', t)
    t = re.sub(r'\s*,\s*', ', ', t)
    for it, en in ITAL.items():
        t = re.sub(rf'(?i)\b{it}\b', en, t)
    # pack specs: "6x50g", "3x55 g" as well as a plain "85g" — size is re-added below
    t = re.sub(r'(?i)\b\d+\s*x\s*\d+(?:[.,]\d+)?\s*(kg|gr|g|ml)?\b', '', t)
    t = re.sub(r'(?i)\b\d+(?:[.,]\d+)?\s*(kg|gr|g|ml)\b', '', t)
    t = re.sub(r'(?i)(?<=\s)e(?=\s)', 'and', t)                  # Italian "e"
    t = re.sub(r'\s{2,}', ' ', t).strip(' -,')
    small = {'with', 'in', 'and', 'of', 'the', 'for', 'on'}
    words = []
    for i, w in enumerate(t.split()):
        lw = w.lower()
        if i and lw in small:
            words.append(lw)
        elif w.isupper() and len(w) > 1:
            words.append(w)
        else:
            words.append(w[:1].upper() + w[1:])
    t = ' '.join(words)
    bits = [b for b in (t, size) if b]
    if p['container'] == 'Pouch':
        bits.append('Pouch')
    elif p['container'] == 'Alutray':
        bits.append('Tray')
    return re.sub(r'\s+', ' ', ' '.join(bits)).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    plan = {p['name']: p for p in json.load(open(PLAN))}
    titles = {}
    for ln in open('.siruk-cache/sources/schesir.jsonl', encoding='utf-8'):
        d = json.loads(ln)
        titles[d['handle']] = d['title']

    prods = []
    for page in range(1, 10):
        _, d = api('GET', f'/products?page={page}')
        for pr in d.get('data', []):
            if pr.get('brand') == 'Schesir':
                prods.append(pr)
        if not d.get('data'):
            break

    renames = []
    for pr in prods:
        _, full = api('GET', f'/products/{pr["id"]}')
        fd = full.get('data', {})
        variants = fd.get('variants', [])
        p = plan.get(pr['name'])
        if not p:
            continue
        size = size_label(p['unit_g'])
        life = {'Puppy/Kitten': 'Kitten' if p['species'] == 'cat' else 'Puppy',
                'Senior': 'Senior'}.get(p['lifestage'])
        base = clean_base(pr['name'], p['line'], p['texture'], size,
                          p['container'], p['lifestage'])

        # A single-variant product IS the site product — use its own title, which
        # is a real product name. Reconstructing one from parts produced
        # nonsense like "Classic Chicken with Small Puppy 2kg".
        if len(variants) == 1 and p['variants'][0].get('handle'):
            title = titles.get(p['variants'][0]['handle'])
            if title:
                new = tidy_title(title, p, size)
                if new and new != pr['name']:
                    renames.append((pr['id'], pr['name'], new, 1))
                continue

        parts = []
        if p['line']:
            parts.append(p['line'])
        if base:
            parts.append(base)
        if life and life.lower() not in ' '.join(parts).lower():
            parts.append(life)
        if p['texture']:
            parts.append(f'in {p["texture"]}')
        if p['multipack']:
            parts.append('Multipack')
        if size:
            parts.append(size)
        if p['container'] in ('Pouch', 'Alutray'):
            parts.append('Pouch' if p['container'] == 'Pouch' else 'Tray')

        new = re.sub(r'\s+', ' ', ' '.join(parts)).strip()
        if not new or new == size:
            new = f'{p["texture"] or "Selection"} {size}'.strip()
        if new != pr['name']:
            renames.append((pr['id'], pr['name'], new, len(variants)))

    print(f'{len(prods)} Schesir products, {len(renames)} renames\n')
    for pid, old, new, nv in renames:
        print(f'  {pid:4d} ({nv}v)  {old!r}\n            -> {new!r}')

    if args.apply:
        ok = bad = 0
        for pid, old, new, _ in renames:
            _, full = api('GET', f'/products/{pid}')
            fd = full.get('data', {})
            body = {k: v for k, v in fd.items()
                    if k not in ('createdAt', 'updatedAt', 'attribute_family_name', 'id')}
            body['variants'] = [{k: v for k, v in var.items()
                                 if k not in ('attribute_values', 'attributes')}
                                for var in fd.get('variants', [])]
            body['name'] = new
            st, res = api('PUT', f'/products/{pid}', body)
            good = 'HTTP 200' in st
            ok += good
            bad += not good
            if not good:
                print(f'  FAIL {pid}: {json.dumps(res)[:200]}')
        print(f'\nrenamed={ok} failed={bad}')


if __name__ == '__main__':
    main()
