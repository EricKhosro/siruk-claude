#!/usr/bin/env python3
"""Fill the ArmSoft goods export (Scale/all-xml.xml) for the shop's scale.

Per <Goods>:
  * BarCode     -> the product's EAN (existing value, PM register, run data)
  * Image       -> left empty by default. The ArmSoft importer wants base64
                   image bytes in <Image> and rejects a URL ("not a valid
                   Base-64 string", 2026-10-02). The first gallery image URL
                   goes to the report CSV; --image-urls writes it anyway.
  * sold per kg -> a bag with a "1 kg" twin on siruk (SKU <bag sku>-KG) becomes
                   a weight good laid out like 0002: Unit 303 (kg) default,
                   AltUnit 003 (bag, Coef = bag kg), BarCode = a unique 5-digit
                   scale code (00001, 00002, ... — the next free number,
                   user 2026-10-04), MTBarCode 003 = EAN, MTBarCode 303 =
                   scale code, PLUCode nil.

Scale codes are kept in state/scale-codes.json (good -> code) so a rebuild
keeps them. Read-only against the API: it reads a product dump made earlier.

  scripts/scale-export.py --catalogue <dir of /products/<id> JSON> \
      --media <medias.json {id: {url}}> [--in Scale/all-xml.xml] \
      [--out Scale/all-xml-scale.xml] [--report Scale/scale-export-report.csv]
"""
import argparse, collections, csv, glob, json, os, re, sys, zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = {'a': 'http://www.armsoft.am/Accountant/6.0'}
X = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def p(*a):
    return os.path.join(ROOT, *a)


def nz(s):
    return ' '.join((s or '').split()).lower()


def ncode(s):
    return re.sub(r'\s+', '', (s or '')).upper()


def read_xlsx(path):
    z = zipfile.ZipFile(path)
    ss = [''.join(t.text or '' for t in si.iter(X + 't'))
          for si in ET.fromstring(z.read('xl/sharedStrings.xml')).iter(X + 'si')] \
        if 'xl/sharedStrings.xml' in z.namelist() else []
    rows = []
    for r in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).iter(X + 'row'):
        row = {}
        for c in r.iter(X + 'c'):
            col = re.match(r'[A-Z]+', c.get('r')).group()
            v = c.find(X + 'v')
            if c.get('t') == 'inlineStr':
                row[col] = ''.join(x.text or '' for x in c.iter(X + 't'))
            elif v is not None:
                row[col] = ss[int(v.text)] if c.get('t') == 's' else v.text
        rows.append(row)
    return rows


# ---- barcodes -------------------------------------------------------------

def check_ok(d):
    """GS1 check digit (EAN-8/UPC-A/EAN-13/GTIN-14)."""
    body, chk = d[:-1], int(d[-1])
    s = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(body)))
    return (10 - s % 10) % 10 == chk


def valid_ean(b):
    """'' if usable, else the reason it is not."""
    b = (b or '').strip()
    if not b.isdigit():
        return 'not digits'
    if len(b) not in (8, 12, 13, 14):
        return f'{len(b)} digits'
    if b.startswith('2001002'):
        return 'hafo shop-internal code'
    if len(b) == 12 and b.startswith('00649925'):
        return 'hafo truncated Acana/Orijen code'
    if not check_ok(b):
        return 'bad check digit'
    return ''


def harvest_by_code():
    """article code -> [(ean, source)] from the run data, best source first."""
    out = collections.defaultdict(list)

    def add(code, ean, src):
        code, ean = ncode(code), (ean or '').strip()
        if code and ean and (ean, src) not in out[code]:
            out[code].append((ean, src))

    for f in ['runs/2026-10-02-found/barcode-sourced.csv',
              'runs/2026-09-28/barcode-sourced.csv',
              'runs/2026-09-25/import/barcode-sourced.csv']:
        if os.path.exists(p(f)):
            for r in csv.DictReader(open(p(f), encoding='utf-8-sig')):
                add(r.get('Article Code'), r.get('EAN'), f)
    f = 'runs/2026-09-25/barcode-web-2026-09-28.json'
    if os.path.exists(p(f)):
        for code, (ean, _) in json.load(open(p(f)))['confirmed'].items():
            add(code, ean, f + ' (confirmed)')
    f = 'runs/2026-09-30-rc/barcodes.csv'
    if os.path.exists(p(f)):
        for r in csv.DictReader(open(p(f), encoding='utf-8-sig')):
            add(r['sku'], r['barcode_ean'], f)
    f = '.siruk-cache/trixie-gtin-index.json'
    if os.path.exists(p(f)):
        for art, eans in json.load(open(p(f))).items():
            if len(eans) == 1:
                add(art + 'TX', eans[0], 'trixie.de GTIN')
    for f in sorted(glob.glob(p('runs/*/hafo.json')), reverse=True):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        src = os.path.relpath(f, ROOT)
        for code, v in d.items():
            if not isinstance(v, dict):
                continue
            arts, bcs = v.get('articles') or [], v.get('barcodes') or []
            if len(arts) == len(bcs):
                for a, b in zip(arts, bcs):
                    if ncode(a) == ncode(code):
                        add(code, b, src)
    return out


# ---- goods blocks ---------------------------------------------------------

GOODS_RE = re.compile(r'(  <Goods xmlns:i="[^"]+">.*?</Goods>)', re.S)


def parse_block(block):
    root = ET.fromstring(
        '<Exchange xmlns="http://www.armsoft.am/Accountant/6.0">' + block + '</Exchange>')
    return root.find('a:Goods', NS)


def txt(g, k):
    e = g.find('a:' + k, NS)
    return (e.text or '') if e is not None else ''


def set_simple(block, tag, value, nil=False):
    """Replace the first top-level (4-space indented) <tag> in a block."""
    new = f'<{tag} i:nil="true" />' if nil else f'<{tag}>{escape(value)}</{tag}>'
    pat = re.compile(r'(\r?\n    )<' + tag + r'(?: [^>]*)?(?:/>|>[^<]*</' + tag + '>)')
    block, n = pat.subn(lambda m: m.group(1) + new, block, count=1)
    if n != 1:
        raise SystemExit(f'no <{tag}> in block')
    return block


def set_section(block, tag, inner_lines, nl):
    pat = re.compile(r'    <' + tag + r'(?: */>|>.*?</' + tag + '>)', re.S)
    body = (f'    <{tag}>' + nl + nl.join(inner_lines) + nl + f'    </{tag}>') if inner_lines \
        else f'    <{tag} />'
    block, n = pat.subn(lambda m: body, block, count=1)
    if n != 1:
        raise SystemExit(f'no <{tag}> section in block')
    return block


def mt(code, unit, bc):
    return ['      <MTBarCode>', f'        <GoodsCode>{code}</GoodsCode>',
            f'        <Unit>{unit}</Unit>', f'        <BarCode>{bc}</BarCode>',
            '      </MTBarCode>']


def qu(unit, coef, default):
    return ['      <QuantityUnitPart>', '        <GoodsCode></GoodsCode>',
            f'        <Unit>{unit}</Unit>', f'        <Coef>{coef:.10f}</Coef>',
            f'        <IsDefault>{"true" if default else "false"}</IsDefault>',
            '        <Image></Image>', '        <IsAltUnit i:nil="true" />',
            '      </QuantityUnitPart>']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', default=p('Scale/all-xml.xml'))
    ap.add_argument('--out', default=p('Scale/all-xml-scale.xml'))
    ap.add_argument('--report', default=p('Scale/scale-export-report.csv'))
    ap.add_argument('--catalogue', required=True)
    ap.add_argument('--media', required=True)
    ap.add_argument('--register', default=p('csv/AllAngineProduct-FINAL-2026-09-28.xlsx'))
    ap.add_argument('--codes', default=p('state/scale-codes.json'))
    ap.add_argument('--image-urls', action='store_true',
                    help='write the siruk image URL into <Image>. Off by default: the ArmSoft '
                         'importer expects base64 image bytes there and rejects a URL '
                         '("not a valid Base-64 string", 2026-10-02). The URL is always in the report CSV.')
    a = ap.parse_args()

    raw = open(a.inp, encoding='utf-8-sig', newline='').read()
    nl = '\r\n' if '\r\n' in raw else '\n'

    # register rows (PM) and their siruk mapping
    fin = [r for r in read_xlsx(a.register)[3:] if r.get('A') and r.get('B')]
    fin_by_name = collections.defaultdict(list)
    for r in fin:
        fin_by_name[nz(r['B'])].append(r)
    status = {r['reg_no']: r for r in json.load(open(p('state/register/register-status.json')))}
    status_by_name = collections.defaultdict(list)
    for r in status.values():
        status_by_name[nz(r['name_hy'])].append(r)
    found = {}
    f = p('runs/2026-10-01-register/found.csv')
    if os.path.exists(f):
        for r in csv.DictReader(open(f, encoding='utf-8-sig')):
            if r.get('Barcode (EAN)'):
                found[r['Կոդ']] = r['Barcode (EAN)']
    by_code = harvest_by_code()

    # live catalogue
    products, variants, by_sku = {}, {}, {}
    for f in glob.glob(os.path.join(a.catalogue, '*.json')):
        d = json.load(open(f))
        products[d['id']] = d
        for v in d.get('variants') or []:
            variants[v['id']] = (d, v)
            by_sku[ncode(v.get('sku'))] = (d, v)
    media = {int(k): v for k, v in json.load(open(a.media)).items()}

    codes = json.load(open(a.codes)) if os.path.exists(a.codes) else {}
    taken = set(codes.values())
    taken |= set(re.findall(r'<BarCode>(\d+)</BarCode>', raw))
    next_code = max((int(c) for c in codes.values()), default=0) + 1

    used_reg, rows, eans_seen = set(), [], collections.defaultdict(list)
    blocked = {}
    RANK = {'XML': 0, 'PM register': 1, 'runs/2026-10-01-register/found.csv': 2}

    def convert(m):
        nonlocal next_code
        block = m.group(1)
        g = parse_block(block)
        code, name, long_name = txt(g, 'Code'), txt(g, 'Name'), txt(g, 'LongName')
        notes = []

        # 1. register row: exact Armenian name (+ LongName), first unused on duplicates
        cands = [r for r in fin_by_name.get(nz(name), []) if r['A'] not in used_reg]
        cands = [r for r in cands if nz(r.get('L')) == nz(long_name)] or cands
        reg = cands[0] if cands else None
        if reg:
            used_reg.add(reg['A'])
            st = status.get(reg['A'])
            if st and nz(st['name_hy']) != nz(name):
                st = None
        else:
            st = next(iter(status_by_name.get(nz(name), [])), None)
            notes.append('not in the PM register by name' + ('; found in register state' if st else ''))
        reg_no = reg['A'] if reg else (st or {}).get('reg_no', '')

        # 2. siruk variant
        prod = var = None
        if st and st.get('variant_id') in variants:
            prod, var = variants[st['variant_id']]
        elif st and st.get('code') and ncode(st['code']) in by_sku:
            prod, var = by_sku[ncode(st['code'])]
            notes.append('variant found by SKU')
        elif reg_no and ncode('REG' + reg_no) in by_sku:
            prod, var = by_sku[ncode('REG' + reg_no)]
            notes.append('variant found by SKU REG' + reg_no)
        if not var:
            notes.append('not on siruk')

        # 3. EAN
        cand = []
        cur = txt(g, 'BarCode')
        cand.append((cur, 'XML'))
        if reg:
            cand.append((reg.get('N') or '', 'PM register'))
        cand.append((found.get(reg_no, ''), 'runs/2026-10-01-register/found.csv'))
        if st:
            cand.append(((st.get('hafo') or {}).get('barcode') or '', 'hafo (register state)'))
            cand += by_code.get(ncode(st.get('code')), [])
        if var:
            cand += by_code.get(ncode(var.get('sku')), [])
            if len(var.get('sku') or '') == 13:
                cand.append((var['sku'], 'siruk SKU'))
        good = [(e, s) for e, s in cand if e and not valid_ean(e)]
        if code in blocked:
            dropped = [e for e, _ in good if e in blocked[code]]
            good = [(e, s) for e, s in good if e not in blocked[code]]
            for e in sorted(set(dropped)):
                notes.append(f'{e} not used: {blocked[code][e]}')
        rejected = sorted({f'{e} ({valid_ean(e)}, {s})' for e, s in cand
                           if e and valid_ean(e) and not (s == 'XML' and len(e) == 5)})
        ean, ean_src = good[0] if good else ('', '')
        others = sorted({e for e, _ in good} - {ean})
        if others:
            notes.append('other EANs seen: ' + ', '.join(others))
        if rejected and not ean:
            notes.append('unusable codes: ' + '; '.join(rejected))
        if ean:
            eans_seen[ean].append((code, RANK.get(ean_src, 4)))

        # 4. image
        img = ''
        if var:
            ids = var.get('images') or []
            if ids:
                img = (media.get(ids[0]) or {}).get('url') or ''
                if not img:
                    notes.append(f'media {ids[0]} not in the media listing')
            else:
                notes.append('variant has no image')

        # 5. sold per kg on siruk?
        kg_twin = None
        if var and prod:
            twin_sku = ncode(var.get('sku')) + '-KG'
            kg_twin = next((v for v in prod['variants'] if ncode(v.get('sku')) == twin_sku), None)
        was_weight = txt(g, 'IsWeight') == 'true'
        bag_kg = None
        if kg_twin:
            if var.get('measure_type') == 'mass' and var.get('content'):
                bag_kg = float(var['content']) / 1000
            else:
                notes.append('has a 1 kg twin but the bag has no mass content')
        weight = bool(kg_twin and bag_kg)
        if was_weight and not weight:
            notes.append('XML had it as a weight good, siruk has no 1 kg twin: left as it was')

        scale = ''
        if weight:
            scale = codes.get(code)
            if not scale:
                while f'{next_code:05d}' in taken:
                    next_code += 1
                scale = f'{next_code:05d}'
                codes[code] = scale
                taken.add(scale)
            block = set_simple(block, 'Unit', '303')
            block = set_simple(block, 'AltUnit', '003')
            block = set_simple(block, 'IsWeight', 'true')
            block = set_simple(block, 'PLUCode', '', nil=True)
            block = set_simple(block, 'BarCode', scale)
            block = set_section(block, 'GoodQuantityUnits',
                                qu('003', bag_kg, False) + qu('303', 1, True), nl)
            block = set_section(block, 'GoodBarCodes',
                                (mt(code, '003', ean) if ean else []) + mt(code, '303', scale), nl)
            if not ean:
                notes.append('weight good with no EAN for the bag')
        elif not was_weight:
            unit = txt(g, 'Unit')
            block = set_simple(block, 'BarCode', ean)
            # keep any other unit's barcodes, replace this unit's
            others = []
            for m2 in g.findall('a:GoodBarCodes/a:MTBarCode', NS):
                u, b = txt(m2, 'Unit'), txt(m2, 'BarCode')
                if u != unit and b:
                    others += mt(code, u, b)
            block = set_section(block, 'GoodBarCodes',
                                (mt(code, unit, ean) if ean else []) + others, nl)
        elif ean and not txt(g, 'BarCode'):
            notes.append('EAN found but not written (weight good left as it was)')
        if img and a.image_urls:
            block = set_simple(block, 'Image', img)

        rows.append({'code': code, 'reg_no': reg_no, 'name': name, 'long_name': long_name,
                     'siruk_product': prod['id'] if prod else '', 'siruk_variant': var['id'] if var else '',
                     'siruk_sku': var.get('sku') if var else '', 'ean': ean,
                     'ean_source': ean_src, 'ean_was_in_xml': 'yes' if cur and cur == ean else '',
                     'image': img, 'sold_per_kg': 'yes' if weight else '',
                     'bag_kg': bag_kg or '', 'scale_code': scale, 'notes': ' | '.join(notes)})
        return block.replace('\n', nl) if nl == '\r\n' and '\r\n' not in block else block

    # pass 1 finds EANs that would land on two goods: the strongest source keeps
    # it, the others fall back to their next EAN (or none) in pass 2
    blocked = collections.defaultdict(dict)
    for _ in range(5):
        rows.clear(); used_reg.clear(); eans_seen.clear()
        out = GOODS_RE.sub(convert, raw)
        clash = {e: cs for e, cs in eans_seen.items() if len(cs) > 1}
        if not clash:
            break
        for e, cs in clash.items():
            cs = sorted(cs, key=lambda c: (c[1], c[0]))
            for c, _ in cs[1:]:
                blocked[c][e] = f'already the barcode of good {cs[0][0]}'
    else:
        raise SystemExit('EAN clashes did not settle')
    ET.fromstring(out.encode('utf-8'))  # still well-formed
    open(a.out, 'w', encoding='utf-8-sig', newline='').write(out)
    json.dump(dict(sorted(codes.items())), open(a.codes, 'w'), indent=1)
    with open(a.report, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    c = collections.Counter()
    for r in rows:
        c['goods'] += 1
        c['on siruk'] += bool(r['siruk_variant'])
        c['with EAN'] += bool(r['ean'])
        c['EAN newly filled'] += bool(r['ean'] and not r['ean_was_in_xml'])
        c['with image'] += bool(r['image'])
        c['sold per kg'] += bool(r['sold_per_kg'])
    print(json.dumps(c, indent=1))
    print('wrote', os.path.relpath(a.out, ROOT), os.path.relpath(a.report, ROOT))


if __name__ == '__main__':
    sys.exit(main())
