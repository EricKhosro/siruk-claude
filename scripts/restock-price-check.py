#!/usr/bin/env python3
"""Before a hafo restock goes in the basket: has our buying price moved, do the rivals sell it
for something else, and is our Glovo price still under Zoovet's? (user 2026-11-16)

    uv run --no-sync --with openpyxl python scripts/restock-price-check.py \
        --lines runs/<today>/restock-lines.json [--xlsx final/hafo/hafo-restock-<today>.xlsx] \
        [--out runs/<today>/restock-prices.json] [--offline]

--lines comes from scripts/hafo-restock.py --lines (the A and B lines only: what we may order).
Adds a "Prices" sheet to the restock Excel and prints one line per thing to change.
NOTHING is written to Siruk, Glovo or ArmSoft: every row is a proposal for the user.

Per line:
  Cost     hafo `wholesale_price` (= Pet House's invoice price, knowledge/costs-and-rivals.md) from
           the hafo-watch snapshot vs Siruk cost_price. A by-weight hafo listing quotes per kg:
           when the pack figure only fits as per-kg × bag kg, it is scaled and marked "per kg".
  Rivals   hafo retail (snapshot, exact row by EAN/article) — always.
           zoovet / nemo — only CONFIRMED pages: the variant's price_source_url, a row of
           state/rival-urls.csv (hand-checked; "none" = that shop doesn't sell it; shared with
           `siruk restock-check`), or for zoovet the Glovo match's ME code
           (state/glovo-zoovet-matches.csv), searched and kept only when the page's code is that
           code. Anything else is a name search → "candidates" to confirm by hand, never a price.
           Rule price = the highest confirmed rival price (reference/pricing.md); a suggestion
           at or below the new cost is never made (rule 5) — the line is flagged instead.
  Glovo    our price (final/glovo/siruk-glovo-products.xlsx col F) vs Zoovet's Glovo price
           (.siruk-cache/glovo/zoovet-glovo-open.json via the matches CSV; refresh with
           glovo-prices-into-sheet.py harvest). Lines with no match get Zoovet-Glovo name
           candidates (brand + size in the name) to confirm and add to the matches CSV.

Outside sites: one request at a time, ≥ 1.5 s apart (CLAUDE.md "Slow requests").
"""
import argparse, csv, datetime as dt, importlib.util, json, os, re, sys, time, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIVAL_URLS = os.path.join(ROOT, 'state', 'rival-urls.csv')
GLOVO_MATCHES = os.path.join(ROOT, 'state', 'glovo-zoovet-matches.csv')
ZOOVET_GLOVO = os.path.join(ROOT, '.siruk-cache', 'glovo', 'zoovet-glovo-open.json')
GLOVO_SHEET = os.path.join(ROOT, 'final', 'glovo', 'siruk-glovo-products.xlsx')
PACE = 1.6
DISCOUNT = 0.97   # some goods' cost is hafo wholesale × 0.97 to the dram (Trixie 19510 1,212.46 vs 1,250)
CONF = {}
SIRUK = os.path.join(ROOT, '.siruk-cache', 'glovo', 'siruk-export.json')
_last = [0.0]


def _mod(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), os.path.join(ROOT, 'scripts', name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def paced(fn, *a):
    wait = PACE - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    try:
        return fn(*a)
    except Exception as e:
        return {'_err': str(e)}
    finally:
        _last[0] = time.time()


def num(x):
    try:
        return float(x) if x not in (None, '') else None
    except (TypeError, ValueError):
        return None


def hafo_pack(l):
    """hafo row → (pack wholesale, pack retail, hafo per-kg retail, note).
    A by-weight listing (Trixie loose treats) has price == kg_price, and both price and wholesale
    are per kg: × bag kg. On a bag listing (Monge 15 kg: 39,000, kg_price 2,700) kg_price is
    hafo's loose per-kg price for that bag (checked 2026-11-16)."""
    ws, pr, kgp = num(l.get('hafo_wholesale')), num(l.get('hafo_price')), num(l.get('hafo_kg_price'))
    kg = (l.get('content') or 0) / 1000 if l.get('measure_type') == 'mass' else 0
    if kgp and pr == kgp and kg:
        return (round(ws * kg, 2) if ws is not None else None), round(pr * kg, 2), kgp, f'hafo per-kg listing × {kg:g} kg'
    return ws, pr, kgp, ''


def site_of(url):
    u = (url or '').lower()
    return 'zoovet' if 'zoovet.am' in u else 'nemo' if 'nemo.am' in u else 'hafo' if 'hafo.am' in u else ''


def load_rival_urls():
    """state/rival-urls.csv (shared with `siruk restock-check`): sku,zoovet_url,nemo_url,checked,note.
    A url = the confirmed page; "none" = confirmed that shop doesn't sell it."""
    out = {}
    if os.path.exists(RIVAL_URLS):
        for r in csv.DictReader(open(RIVAL_URLS, encoding='utf-8-sig')):
            sku = (r.get('sku') or '').strip()
            if sku:
                out[sku] = {s: (r.get(f'{s}_url') or '').strip() for s in ('zoovet', 'nemo') if (r.get(f'{s}_url') or '').strip()}
    return out


def load_glovo():
    """(sku → our Glovo price, sku → [zoovet codes], code → zoovet glovo item, harvest date)"""
    ours, codes, zg, when = {}, {}, {}, ''
    try:
        import openpyxl
        ws = openpyxl.load_workbook(GLOVO_SHEET, read_only=True, data_only=True).worksheets[0]
        for r in ws.iter_rows(min_row=3, values_only=True):
            if r and r[0] and num(r[5]) is not None:
                ours[str(r[0]).strip()] = num(r[5])
    except Exception as e:
        print(f'  (Glovo sheet not read: {e})')
    if os.path.exists(GLOVO_MATCHES):
        for r in csv.DictReader(open(GLOVO_MATCHES, encoding='utf-8')):
            codes.setdefault(r['sku'].strip(), []).append(r['zoovet_code'].strip())
            CONF[(r['sku'].strip(), r['zoovet_code'].strip())] = (r.get('confidence') or '').strip()
    if os.path.exists(ZOOVET_GLOVO):
        zg = json.load(open(ZOOVET_GLOVO, encoding='utf-8'))
        when = dt.datetime.fromtimestamp(os.path.getmtime(ZOOVET_GLOVO)).strftime('%Y-%m-%d %H:%M')
    return ours, codes, zg, when


def size_tokens(line):
    c, m = line.get('content') or 0, line.get('measure_type')
    if not c:
        return []
    if m == 'mass':
        return [f'{c / 1000:g}կգ', f'{c / 1000:g} կգ'] if c >= 1000 else [f'{c:g}գ', f'{c:g} գ']
    if m == 'volume':
        return [f'{c / 1000:g}լ', f'{c / 1000:g} լ'] if c >= 1000 else [f'{c:g}մլ', f'{c:g} մլ']
    return []


def glovo_candidates(line, zg, matched):
    """Zoovet Glovo items with our brand, our size and a word of our product name — leads, not matches."""
    brand = (line.get('brand') or '').lower()
    toks = [t.replace(' ', '') for t in size_tokens(line)]
    words = {w for w in re.findall(r'[a-z]{4,}', (line.get('product') or '').lower())} - {
        'adult', 'with', 'dogs', 'cats', 'food', 'for', 'and'}
    if not brand or not toks or not words:
        return []
    out = []
    for code, it in zg.items():
        n = (it.get('name') or '').lower()
        flat = n.replace(' ', '')
        if code in matched or brand not in n:
            continue
        if not any(re.search(r'(?<![\d.,])' + re.escape(t), flat) for t in toks):
            continue
        hit = sum(1 for w in words if w in n)
        if hit:
            out.append((-hit, f"{code} {it.get('name')} — {num(it.get('price')) or 0:,.0f}"))
    return [c for _, c in sorted(out)[:3]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lines', required=True)
    ap.add_argument('--xlsx', help='restock Excel to add the Prices sheet to (default: the one --lines names)')
    ap.add_argument('--out', help='write the result rows as JSON here')
    ap.add_argument('--siruk', default=SIRUK, help='Siruk export (json), for the -KG / -100G loose twins')
    ap.add_argument('--offline', action='store_true', help='no zoovet / nemo requests (hafo + Glovo cache only)')
    a = ap.parse_args()

    data = json.load(open(a.lines, encoding='utf-8'))
    lines, fetched = data['lines'], data.get('fetched', '?')
    zv = None if a.offline else _mod('zoovet-lookup')
    nm = None if a.offline else _mod('nemo-lookup')
    rival_urls = load_rival_urls()
    g_ours, g_codes, zg, zg_when = load_glovo()
    g_conf = CONF
    twins = {}
    if os.path.exists(a.siruk):
        for v in json.load(open(a.siruk, encoding='utf-8')):
            m = re.match(r'(.+)-(KG|100G)$', str(v.get('sku') or ''))
            if m:
                twins.setdefault(m.group(1), []).append(v)
    # stale or missing inputs must not read as "all fine"
    warn = []
    age = lambda iso: (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(iso)).total_seconds() / 3600
    try:
        if age(fetched) > 24:
            warn.append(f'hafo snapshot is {age(fetched) / 24:.0f} days old: run hafo-watch.py crawl first')
    except Exception:
        warn.append('hafo snapshot date unknown')
    if lines and not any(l.get('hafo_wholesale') is not None for l in lines):
        warn.append('NO line has a hafo wholesale: the snapshot predates 2026-11-16, re-crawl; costs not checked')
    if not zg_when:
        warn.append('no Zoovet Glovo harvest: Glovo not checked')
    elif (time.time() - os.path.getmtime(ZOOVET_GLOVO)) > 3 * 86400:
        warn.append(f'Zoovet Glovo prices are from {zg_when}: run glovo-prices-into-sheet.py harvest')
    if os.path.exists(a.siruk) and (time.time() - os.path.getmtime(a.siruk)) > 86400:
        warn.append('Siruk export is over a day old: our prices/costs may be stale (siruk export)')
    for w in warn:
        print('WARNING:', w)

    rows = []
    for i, l in enumerate(lines, 1):
        sku, price, cost = str(l.get('sku') or ''), num(l.get('siruk_price')), num(l.get('siruk_cost'))
        notes, actions, cands = [], [], []
        # --- cost
        ws, hp, kgp, how = hafo_pack(l)
        cost_flag = ''
        if how:
            notes.append(how)
        if ws is None:
            cost_flag = 'no hafo wholesale'
            actions.append('cost NOT checked (no hafo wholesale)')
        elif cost and abs(ws * DISCOUNT - cost) <= max(1, ws * 0.002):
            cost_flag = '= wholesale − 3% (invoice discount)'   # ~50 goods, 2026-11-16: same, not a change
            ws = cost
        elif cost and abs(ws - cost) >= 1:
            cost_flag = f'{"UP" if ws > cost else "down"} {ws - cost:+,.0f} ({(ws - cost) / cost:+.0%})'
            actions.append(f'cost {cost:,.0f} → {ws:,.0f}')
        elif not cost:
            cost_flag = 'Siruk has no cost'
            actions.append(f'cost → {ws:,.0f}')
        new_cost = ws if ws is not None else cost
        # --- rivals
        rival = {'hafo': (hp, l.get('url') or '')} if hp else {}
        known = dict(rival_urls.get(sku, {}))
        src = site_of(l.get('price_source_url'))
        if src in ('zoovet', 'nemo'):
            known.setdefault(src, l['price_source_url'])
        if not a.offline:
            for site, mod in (('zoovet', zv), ('nemo', nm)):
                url = known.get(site)
                if url == 'none':
                    continue                                 # confirmed: this shop doesn't sell it
                if not url and site == 'zoovet':
                    for code in g_codes.get(sku, []):        # the Glovo match's code is zoovet.am's own code
                        res = paced(zv.fetch, zv.SEARCH.format(q=urllib.parse.quote(code)))
                        hits = zv.parse_list(res) if isinstance(res, str) else []
                        for h in hits[:3]:
                            pg = paced(zv.product, h['url'])
                            if isinstance(pg, dict) and (pg.get('zoovet_code') or '').strip() == code:
                                url = h['url']
                                notes.append(f'zoovet page from Glovo match {code}')
                                break
                        if url:
                            break
                if url:
                    pg = paced(mod.product, url)
                    p = pg.get('price') if isinstance(pg, dict) else None
                    if p and price and float(p) < 0.4 * price:   # per-kg / per-piece page (as glovo-prices-into-sheet)
                        notes.append(f'{site} {p:,} is a per-kg/per-piece price, not compared')
                    elif p:
                        rival[site] = (float(p), url)
                    else:
                        notes.append(f'{site} page gave no price ({(pg or {}).get("_err", "")[:60]})')
                else:
                    q = f"{l.get('brand', '')} {l.get('product', '')}".strip()
                    if site == 'zoovet':
                        res = paced(zv.fetch, zv.SEARCH.format(q=urllib.parse.quote(q)))
                        hits = zv.parse_list(res) if isinstance(res, str) else []
                    else:
                        res = paced(nm.fetch, nm.SEARCH.format(q=urllib.parse.quote(q), n=12))
                        hits = nm.parse_list(res) if isinstance(res, str) else []
                    cands += [f"{site}: {h.get('name')} — {h.get('price')} {h.get('url')}" for h in hits[:3]]
        src_unread = src in ('zoovet', 'nemo') and src not in rival
        if src_unread:
            notes.append(f'our price came from {src}, not re-read — no price proposal')
        best_site, best = (max(rival.items(), key=lambda kv: kv[1][0]) if rival else (None, (None, '')))
        best_price, best_url = best
        rule = ''
        if best_price is not None and price is not None and abs(best_price - price) >= 1 and not src_unread:
            if new_cost and best_price <= new_cost:
                rule = f'highest rival {best_price:,.0f} ({best_site}) is at/below cost {new_cost:,.0f}: CHECK BY HAND'
            else:
                rule = f'{price:,.0f} → {best_price:,.0f} ({best_site})'
                unread = [x for x in ('zoovet', 'nemo') if x not in rival]
                if best_price < price and unread:
                    rule += f' — DOWN on {"/".join(sorted(rival))} only; {"/".join(unread)} not confirmed, check first'
                actions.append(f'price {rule}')
        if new_cost and price and price <= new_cost:
            actions.append(f'LOSS: our price {price:,.0f} ≤ new cost {new_cost:,.0f}')
        # --- Glovo
        gp = g_ours.get(sku)
        zgp = [num(zg[c].get('price')) for c in g_codes.get(sku, []) if c in zg and not zg[c].get('out_of_stock')]
        zgp = [x for x in zgp if x]
        g_flag = ''
        if any(g_conf.get((sku, c)) == 'medium' for c in g_codes.get(sku, [])):
            notes.append('Glovo match is medium confidence')
        if zgp:
            z = min(zgp)
            if gp is None:
                g_flag = f'Zoovet Glovo {z:,.0f}; we are not on Glovo'
            elif gp >= z and z >= 0.4 * gp:
                g_flag = f'ours {gp:,.0f} ≥ Zoovet {z:,.0f}'
                actions.append('Glovo: re-run glovo-prices-into-sheet fill')
            else:
                g_flag = f'ours {gp:,.0f} < Zoovet {z:,.0f}'
        elif zg:
            gc = glovo_candidates(l, zg, set(g_codes.get(sku, [])))
            if gc:   # a lead only (the 2026-11-06 review may have turned it down): no TO DO
                g_flag = 'Zoovet Glovo lead, not matched — check: ' + ' | '.join(gc)
        if price and new_cost and gp and gp * 0.8 <= new_cost:
            actions.append(f'Glovo price {gp:,.0f} leaves nothing after commission at cost {new_cost:,.0f}')
        r = {'group': l['group'], 'code': l.get('code'), 'sku': sku, 'product_id': l.get('product_id'),
             'brand': l.get('brand'), 'product': l.get('product'), 'size': l.get('size'), 'order': l.get('bags', l.get('order')),   # bags: wholesale is per pack
             'siruk_cost': cost, 'hafo_wholesale': ws, 'cost_change': cost_flag,
             'siruk_price': price, 'hafo': rival.get('hafo', (None,))[0], 'zoovet': rival.get('zoovet', (None,))[0],
             'nemo': rival.get('nemo', (None,))[0], 'highest_rival': best_price, 'highest_url': best_url,
             'price_change': rule, 'glovo_ours': gp, 'glovo': g_flag,
             'action': '; '.join(actions), 'candidates': ' | '.join(cands), 'notes': '; '.join(notes)}
        rows.append(r)
        # loose twins share the bag's cost (rule 8a): bag cost ÷ kg, or ÷ (g / 100)
        bag_g = l.get('content') or 0
        for t in twins.get(sku, []):
            per = bag_g / 1000 if str(t['sku']).endswith('-KG') else bag_g / 100
            if not per or new_cost is None:
                continue
            tc, tnew = num(t.get('cost_price')), round(new_cost / per, 2)
            ta = []
            if tc is None or abs(tnew - tc) >= 0.5:
                ta.append(f'cost {tc or 0:,.2f} → {tnew:,.2f} (bag ÷ {per:g})')
            if t.get('price') and num(t['price']) <= tnew:
                ta.append(f'LOSS: price {num(t["price"]):,.0f} ≤ cost {tnew:,.2f}')
            hint = ''
            if kgp:
                hint = f'hafo loose {kgp:,.0f}/kg' + (f' = {kgp / 10:,.0f}/100 g' if t['sku'].endswith('-100G') else '')
            rows.append({'group': l['group'], 'code': l.get('code'), 'sku': t['sku'], 'product_id': t.get('product_id'),
                         'brand': l.get('brand'), 'product': l.get('product'), 'size': t.get('size') or t.get('variant_name'),
                         'order': '', 'siruk_cost': tc, 'hafo_wholesale': tnew,
                         'cost_change': '' if not ta else 'follows the bag', 'siruk_price': num(t.get('price')),
                         'hafo': None, 'zoovet': None, 'nemo': None, 'highest_rival': None, 'highest_url': '',
                         'price_change': '', 'glovo_ours': g_ours.get(t['sku']), 'glovo': '',
                         'action': '; '.join(ta), 'candidates': '',
                         'notes': '; '.join(x for x in ('loose twin of ' + sku, hint, 'loose price: user decides, never derived') if x)})
        print(f'[{i}/{len(lines)}] {sku} {(l.get("product") or "")[:40]}: {r["action"] or "ok"}', flush=True)

    ws_total = sum((r['hafo_wholesale'] or 0) * (r['order'] or 0) for r in rows if r['group'] == 'A')
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump({'hafo_snapshot': fetched, 'zoovet_glovo_harvest': zg_when, 'a_total_wholesale': ws_total,
                   'rows': rows}, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    xlsx = a.xlsx or data.get('xlsx')
    if xlsx and os.path.exists(xlsx):
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
        wb = openpyxl.load_workbook(xlsx)
        if 'Prices' in wb.sheetnames:
            del wb['Prices']
        sh = wb.create_sheet('Prices', 1)
        for w in warn:
            sh.append(['WARNING: ' + w])
        sh.append([f'Price check {dt.date.today()}: hafo snapshot {fetched}, Zoovet Glovo harvest {zg_when or "none"}. '
                   f'Proposals only — nothing written. Group A at hafo wholesale: {ws_total:,.0f} AMD'])
        cols = [('Group', 'group', 6), ('ArmSoft', 'code', 8), ('SKU', 'sku', 12), ('Brand', 'brand', 12),
                ('Product', 'product', 38), ('Size', 'size', 9), ('Order', 'order', 6),
                ('Our cost', 'siruk_cost', 9), ('hafo wholesale', 'hafo_wholesale', 10), ('Cost change', 'cost_change', 16),
                ('Our price', 'siruk_price', 9), ('hafo', 'hafo', 8), ('zoovet', 'zoovet', 8), ('nemo', 'nemo', 8),
                ('Price change', 'price_change', 26), ('Our Glovo', 'glovo_ours', 9), ('Glovo vs Zoovet', 'glovo', 30),
                ('TO DO (on your yes)', 'action', 40), ('Rival candidates to confirm', 'candidates', 50),
                ('Notes', 'notes', 24), ('Rival link', 'highest_url', 30)]
        sh.append([c[0] for c in cols])
        for c in sh[sh.max_row]:
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor='1F4E78')
            c.alignment = Alignment(wrap_text=True)
        bags = {}
        for n, r in enumerate(rows):
            bags.setdefault(r['notes'].split('loose twin of ')[-1].split(';')[0] if 'loose twin of' in r['notes'] else r['sku'], []).append(r)
        order = sorted(bags.values(), key=lambda g: (not any(x['action'] for x in g), g[0]['group']))
        for r in [x for g in order for x in g]:
            sh.append([r[k] for _, k, _ in cols])
            if 'LOSS' in r['action'] or 'UP' in r['cost_change']:
                sh.cell(sh.max_row, 18).fill = PatternFill('solid', fgColor='F8CBAD')
            elif r['action']:
                sh.cell(sh.max_row, 18).fill = PatternFill('solid', fgColor='FFF2CC')
        for j, (_, _, w) in enumerate(cols, 1):
            sh.column_dimensions[get_column_letter(j)].width = w
        sh.freeze_panes = f'F{sh.max_row - len(rows) + 1}'
        wb.save(xlsx)
        print('→ Prices sheet in', xlsx)
    todo = [r for r in rows if r['action']]
    for w in warn:
        print('WARNING:', w)
    print(f'\n{len(rows)} lines checked, {len(todo)} with something to change; '
          f'group A at hafo wholesale {ws_total:,.0f} AMD (Zoovet Glovo prices from {zg_when or "—"})')
    for r in todo:
        print(f'  {r["sku"]:>12} {(r["product"] or "")[:36]:36} {r["action"]}')


if __name__ == '__main__':
    main()
