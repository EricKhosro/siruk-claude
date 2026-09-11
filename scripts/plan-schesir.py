#!/usr/bin/env python3
"""Group the Schesir vendor rows into products + variants and match each to the
cached schesir.com catalogue.

Grouping follows the shelf test in reference/product-rules.md: a product is one
(species, line, sub-range, container); **pack weight, flavor and texture are
variant axes**, so every pack size / flavor / texture of one range collapses
into a single product and is told apart by its variant label.

    scripts/plan-schesir.py            # print the plan
    scripts/plan-schesir.py -o p.json  # also write it

Reads .siruk-cache/vendor-rows.json and .siruk-cache/sources/schesir.jsonl.
"""
import argparse
import json
import re
from collections import defaultdict

ROWS = '.siruk-cache/vendor-rows.json'
CAT = '.siruk-cache/sources/schesir.jsonl'

# Line / sub-brand, longest first so "AFTER DARK" wins over "AD".
LINES = [
    ('AFTER DARK', 'After Dark'), ('TASTE THE WORLD', 'Taste the World'),
    ('BABY THRIVE', 'Baby Thrive'), ('DRY BC', 'Born Carnivore'),
    ('FUNCTIONS', 'Functions'), ('SPECIAL', 'Special'), ('SILVER', 'Silver'),
    ('BABY', 'Baby'), ('GRILL', 'Grill'), ('STIX', 'Stix'), ('SNACK', 'Snack'),
    ('SOUP', 'Soup'), ('BIO', 'Bio'), ('C&B', ''), ('AD ', 'After Dark'),
]

# Texture / preparation. Vendor word -> our word.
TEXTURES = [
    ('VELVET MOUSSE', 'Mousse'), ('MOUSSE AND SHREDS', 'Mousse & Shreds'),
    ('WHOLEFOOD', 'Broth'), ('BRODO', 'Broth'), ('IN BROTH', 'Broth'),
    ('PATE', 'Paté'), ('MOUSSE', 'Mousse'), ('JELLY', 'Jelly'), ('JEL', 'Jelly'),
    ('NAT. BRINE', 'Natural'), ('NAT.BRINE', 'Natural'), ('NAT. STYLE', 'Natural'),
    ('NAT.STYLE', 'Natural'), ('SOUP', 'Soup'), ('BROTH', 'Broth'),
]

CONTAINERS = [
    ('MULTIPACK', 'Multipack'), ('MPK', 'Multipack'), ('POUCH', 'Pouch'),
    ('ALUTRAY', 'Alutray'), ('CAN', 'Can'), ('BAG', 'Bag'),
]

# Flavor words (English + the Italian the sheet mixes in).
FLAVOR_MAP = {
    'POLLO': 'Chicken', 'MANZO': 'Beef', 'VITELLO': 'Veal', 'VITEL': 'Veal',
    'VIT': 'Veal', 'PROSCIUTTO': 'Ham', 'PROSC': 'Ham', 'PROS': 'Ham',
    'PESCE': 'Fish', 'PESC': 'Fish', 'TONNO': 'Tuna', 'SALMONE': 'Salmon',
    'SALM': 'Salmon', 'AGNELLO': 'Lamb', 'ANATRA': 'Duck', 'CONIGLIO': 'Rabbit',
    'CONIG': 'Rabbit', 'TACCHINO': 'Turkey', 'TACC': 'Turkey', 'TAC': 'Turkey',
    'MAIALE': 'Pork', 'CINGHIALE': 'Boar', 'CNGL': 'Boar', 'TROTA': 'Trout',
    'TRIPPA': 'Tripe', 'ZUCCA': 'Pumpkin', 'CAROTE': 'Carrots',
    'PISELLI': 'Peas', 'MELA': 'Apple', 'ANANAS': 'Pineapple',
    'PAPAYA': 'Papaya', 'ALICETTE': 'Anchovies', 'GAMBERETTI': 'Prawns',
    'CALAMARI': 'Squid', 'SGOMBRO': 'Mackerel', 'SGOMB': 'Mackerel',
    'SGOM': 'Mackerel', 'SARDINE': 'Sardine', 'SARD': 'Sardine',
    'SPIGOLA': 'Seabass', 'SURIMI': 'Surimi', 'UOVO': 'Egg', 'UOVA': 'Egg',
    'ARINGA': 'Herring', 'NASEL': 'Hake', 'CHICKEN': 'Chicken', 'TUNA': 'Tuna',
    'SALMON': 'Salmon', 'BEEF': 'Beef', 'LAMB': 'Lamb', 'HAM': 'Ham',
    'DUCK': 'Duck', 'TURKEY': 'Turkey', 'LIVER': 'Liver', 'EGGS': 'Egg',
    'EGG': 'Egg', 'FISH': 'Fish', 'PORK': 'Pork', 'RABBIT': 'Rabbit',
    'BACON': 'Bacon', 'VEAL': 'Veal', 'TROUT': 'Trout',
}

# Noise: pack/marketing tokens that are neither line, texture nor flavor.
NOISE = {
    'SCH', 'SCHESIR', 'NE', 'IE', 'EX', 'EM', 'W', 'WITH', 'AND', 'THE',
    'GR', 'G', 'KG', 'X', 'VARIETY', 'PACK', 'IN', 'STYLE', 'FILLETS',
    'FILLET', 'FIL', 'DRY', 'WET', 'CAT', 'DOG', 'M&S', 'BC', 'TREATS',
    'TOPPER', 'OF', 'A', 'CIL', 'INT', 'EU',
}


def norm(s):
    return re.sub(r'\s+', ' ', s.upper().replace('.', ' ').replace('/', ' ')).strip()


def take(text, table):
    """Find the first table entry present in text; return (our_word, text_without)."""
    for needle, ours in table:
        if needle in text:
            return ours, text.replace(needle, ' ', 1)
    return None, text


def parse_vendor(raw):
    # strip every pack spec first: 12X80G, 8X6X50GR, 6X1,5KG, 40X150, 250ML
    t = norm(raw)
    t = re.sub(r'\b\d+(?:[.,]\d+)?\s*[X*]\s*', ' ', t)      # leading multipliers
    t = re.sub(r'\b\d+(?:[.,]\d+)?\s*(KG|GR|G|ML|L)\b', ' ', t)
    t = re.sub(r'\b\d+(?:[.,]\d+)?\b', ' ', t)              # bare numbers
    line, t = take(t, [(k, v) for k, v in LINES])
    texture, t = take(t, TEXTURES)
    container, t = take(t, CONTAINERS)
    flavors, extra = [], []

    def add(f):
        if f not in flavors:
            flavors.append(f)

    for tok in t.split():
        tok = tok.strip('-&,')
        if not tok or tok in NOISE or any(c.isdigit() for c in tok):
            continue
        if tok in FLAVOR_MAP:
            add(FLAVOR_MAP[tok])
            continue
        # The sheet joins a compound flavor with "&" and no spaces
        # ("POLLO&UOVO", "ANATRA&MELA"). norm() splits on "/" already but not
        # on "&", so the whole token misses FLAVOR_MAP and used to land in
        # `extra` — where it acted as a product discriminator and split one
        # range into a product per flavor. Only accept the split when *every*
        # part is a flavor, so "M&S" stays one token and is filtered as noise.
        parts = [x for x in tok.split('&') if x]
        mapped = [FLAVOR_MAP.get(x) for x in parts]
        if len(parts) > 1 and all(mapped):
            for f in mapped:
                add(f)
        else:
            extra.append(tok.title())
    return dict(line=line, texture=texture, container=container,
                flavors=flavors, extra=extra)


def load_catalogue():
    """full article code -> product. Codes that several products claim are
    dropped: an ambiguous code is worse than no match."""
    by_code, by_handle = defaultdict(set), {}
    prods = {}
    for ln in open(CAT, encoding='utf-8'):
        p = json.loads(ln)
        by_handle[p['handle']] = p
        prods[p['handle']] = p
        for im in p.get('images', []):
            for m in re.finditer(r'[A-Z]{2,4}_(\d{7,9})_', im['src']):
                by_code[m.group(1)].add(p['handle'])
    clean = {c: prods[next(iter(hs))] for c, hs in by_code.items() if len(hs) == 1}
    return clean, by_handle


# Tags that name a Schesir range. Order = preference when several apply.
LINE_TAGS = ['After Dark', 'Baby Thrive', 'Baby', 'Silver', 'Bio', 'Stix',
             'Snax', 'Soup', 'Taste the World', 'Born Carnivore',
             'Monoprotein Nutrition', 'Monoprotein', 'Petit Cuisine',
             'Functions Nutrition', 'Veterinary solutions', 'Classic']
LIFESTAGE_TAGS = {'Cucciolo': 'Puppy/Kitten', 'Anziano': 'Senior',
                  'Adulto': None}          # Adult is the default, not in the name


def site_facts(p):
    """species / line / lifestage / dry-wet from a catalogue product's tags."""
    if not p:
        return {}
    tags = p.get('tags', [])
    species = 'cat' if 'Gatto' in tags else 'dog' if 'Cane' in tags else None
    line = next((t for t in LINE_TAGS if t in tags), None)
    life = next((v for k, v in LIFESTAGE_TAGS.items() if k in tags and v), None)
    form = 'dry' if 'Secco' in tags else 'wet' if 'Umido' in tags else None
    return dict(species=species, line=line, lifestage=life, form=form,
                complementary='Complementare' in tags)


# Words that carry no identity once flavor/size/texture are stripped out.
TITLE_NOISE = {'RICH', 'IN', 'WITH', 'AND', 'CON', 'THE', 'FILLETS', 'FILLET',
               'CAN', 'POUCH', 'BAG', 'ALUTRAY', 'JELLY', 'PATE', 'PATÉ',
               'MOUSSE', 'BROTH', 'SAUCE', 'CREAM', 'GRAVY', 'COOKING',
               'WATER', 'SHREDS', 'MIX', 'BOX', 'FILETS', 'A', 'OF', 'DRY'}


def site_base(items):
    """Longest identity prefix shared by the matched site titles."""
    bases = []
    for r in items:
        t = (r['site'].get('title') or '').upper()
        t = re.sub(r'\b\d+(?:[.,]\d+)?\s*(KG|GR|G|ML|L)\b', ' ', t)
        t = re.sub(r'\d+\s*[Xx]\s*', ' ', t)
        toks = []
        for tok in re.split(r'[^A-Z&À-ſ]+', t):
            if not tok or tok in TITLE_NOISE or tok in FLAVOR_MAP:
                continue
            toks.append(tok)
        # keep empty results too: a title that reduces to nothing means the range
        # has no shared identity beyond flavor, and must not inherit a stray token
        bases.append(toks)
    if not bases:
        return None
    common = []
    for i in range(min(len(b) for b in bases)):
        col = {b[i] for b in bases}
        if len(col) == 1:
            common.append(bases[0][i])
        else:
            break
    return ' '.join(w.title() for w in common) or None


def weight_label(g):
    """Same number as size_label, spaced — variant labels read "80 g", product
    names read "80g"."""
    s = size_label(g)
    return re.sub(r'(\d)(kg|g)$', r'\1 \2', s)


def size_label(g):
    if g is None:
        return '?'
    if g >= 1000 and g % 1000 == 0:
        return f'{int(g // 1000)}kg'
    if g >= 1000:
        return f'{g / 1000:g}kg'
    return f'{int(g)}g'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--out')
    args = ap.parse_args()

    by_code, _ = load_catalogue()
    rows = [r for r in json.load(open(ROWS))
            if r['brand'] == 'Schesir' and not r['skip_reason']]

    groups = defaultdict(list)
    for r in rows:
        p = parse_vendor(r['name_clean'])
        r['parsed'] = p
        r['site'] = by_code.get(r['sku'] or '')
        f = site_facts(r['site'])
        r['facts'] = f
        # species splits products; fall back to the Armenian prefix
        species = f.get('species') or r.get('species_hint')
        line = p['line'] or f.get('line')
        # the site handle states the container reliably; vendor strings often omit it
        handle = (r['site'] or {}).get('handle', '')
        m = re.search(r'in-(can|pouch|bag|alutray)\b', handle)
        container = (m.group(1).title() if m else None) or p['container']
        r['container'] = container
        multipack = p['container'] == 'Multipack'
        # CLAUDE.md's shelf test: pack weight, flavor and texture are VARIANT
        # axes, so none of them may appear in the product key. Keeping pack
        # weight here split every range into a product per pack size (the
        # 113 g and 283 g training snacks became two products), and keeping
        # texture split the broth/paté/jelly formats of one range apart.
        # `extra` stays: it carries the sub-range ("Training", "Meatballs",
        # "Maintenance"), which really is a different product on the shelf.
        key = (species or '?', line or '', container or '',
               multipack, ' '.join(p['extra']))
        groups[key].append(r)

    # An UNKNOWN field must not act as a discriminator. Species and container
    # are only known when the row matched the site catalogue, and a few
    # products carry no article code in their image filenames at all
    # (`flavoured-with-chicken-6x113g`, the 113 g training snack) — that row
    # used to land in its own group purely because its container was null,
    # which is how the 113 g and 283 g training snacks became two products.
    # Fold such a group into the one group that agrees on every known field;
    # if several match, the row is genuinely ambiguous, so leave it alone.
    for key in [k for k in groups if k[0] == '?' or not k[2]]:
        cands = [o for o in groups
                 if o != key and o[1] == key[1] and o[3] == key[3]
                 and o[4] == key[4]
                 and (key[0] == '?' or o[0] == key[0])
                 and (not key[2] or o[2] == key[2])]
        if len(cands) == 1:
            groups[cands[0]].extend(groups.pop(key))

    plan = []
    for key, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        species, line, container, multipack, extra = key
        life = next((r['facts'].get('lifestage') for r in items
                     if r['facts'].get('lifestage')), None)
        # An axis only belongs in the product name while it does NOT vary;
        # as soon as it varies it is what the variant labels carry.
        sizes = {r['unit_g'] for r in items}
        textures = {r['parsed']['texture'] or '' for r in items}
        g = next(iter(sizes)) if len(sizes) == 1 else None
        texture = next(iter(textures)) if len(textures) == 1 else None
        # Prefer a base derived from the matched site titles: strip flavor, size,
        # texture and container words and keep what identifies the range
        # ("Medium Adult Rich In Chicken 12kg" -> "Medium Adult").
        base = site_base([r for r in items if r['site']])
        # A few ranges (the plain cat/dog cans) carry no line tag on the site
        # and used to borrow their only identity from the texture word
        # ("in Jelly 85g"). Now that texture varies across the variants that
        # word is gone, so fall back to the format rather than to a bare size.
        if not (base or line or extra):
            base = ' '.join(b for b in ((species or '').title(), container) if b)
        bits = [b for b in (base or line, None if base else extra, life,
                            texture and f'in {texture}',
                            'Multipack' if multipack else '',
                            size_label(g) if len(sizes) == 1 else '',
                            container if container in ('Pouch', 'Alutray') else '') if b]
        name = ' '.join(bits) or f'{texture or "Item"} {size_label(g)}'

        def label(r):
            """The varying axes only — that is what tells the siblings apart.

            A label that repeats what every sibling shares is noise, and one
            that omits a varying axis makes two variants indistinguishable
            (three Born Carnivore flavors all read "255 g"). With a single
            variant nothing varies, so fall back to flavor, then pack size.
            """
            flav = ' & '.join(r['parsed']['flavors'])
            if len(items) == 1:
                return flav or weight_label(r['unit_g'])
            parts = []
            if flav:
                parts.append(flav)
            if len(textures) > 1 and r['parsed']['texture']:
                parts.append(f"in {r['parsed']['texture']}")
            if len(sizes) > 1 and r['unit_g'] is not None:
                parts.append(weight_label(r['unit_g']))
            return ' '.join(parts) or weight_label(r['unit_g'])

        plan.append(dict(
            name=name, species=species, line=line, texture=texture,
            container=container,
            multipack=multipack, unit_g=g, extra=extra, lifestage=life,
            form=next((r['facts'].get('form') for r in items
                       if r['facts'].get('form')), None),
            matched=sum(1 for r in items if r['site']),
            variants=[dict(sku=r['sku'],
                           flavor=' & '.join(r['parsed']['flavors']) or '(plain)',
                           texture=r['parsed']['texture'],
                           label=label(r),
                           price=r['price'], cost=r['cost'], unit_g=r['unit_g'],
                           handle=(r['site'] or {}).get('handle'),
                           raw=r['raw_name'].strip()) for r in items]))

    print(f'schesir priced rows: {len(rows)}')
    print(f'proposed products:   {len(plan)}')
    print(f'rows matched to site: {sum(p["matched"] for p in plan)}\n')
    for p in plan:
        flag = '' if p['matched'] == len(p['variants']) else \
            f'  [{p["matched"]}/{len(p["variants"])} matched]'
        print(f'{len(p["variants"]):3d}v  [{p["species"]}/{p["form"] or "?"}] '
              f'{p["name"]}{flag}')
        for v in p['variants']:
            mark = ' ' if v['handle'] else '?'
            print(f'      {mark} {v["sku"] or "-":10s} {v["label"]:28s} '
                  f'{v["price"] or 0:6d}  {v["handle"] or "NO MATCH"}')
    if args.out:
        json.dump(plan, open(args.out, 'w'), ensure_ascii=False, indent=1)
        print(f'\nwrote {args.out}')


if __name__ == '__main__':
    main()
