"""Yandex Eda on/off from ArmSoft stock — the same rule and the same moments as Glovo (user 2026-11-19).

Yandex keeps no quantities, only `is_available` per card in our store (place 3315164). After every posted
warehouse receipt, write-off, count or till-sales check, the cards follow ArmSoft exactly as Glovo does
(`glovo-portal.py stock`): a bag needs a sealed bag, its -KG / -100G card needs 1 kg / 100 g loose,
everything else needs 1 in stock. Sold out → off. Back in stock → on only for the goods a receipt just
restocked (`--on-codes`), or everything with `--on`; a card someone switched off by hand stays off.

The cabinet's API only answers from the built-in browser (the Yango sign-in's cookies), so this script
plans and the browser applies:

  python scripts/yandex-availability.py plan Scale/armsoft-turnover-<date>.xlsx Scale/armsoft-export-<date>.xml \
      [--on-codes 0430 0431 …] [--on] [--out final/yandex/yandex-availability-<date>.xlsx]
      → .siruk-cache/yandex/availability.js (the cards that should be off / may go on) + the dry-run list
  in the cabinet tab (pickerapp.eats.yango.com), mcp__Claude_Browser__javascript_tool:
      window.__yav_apply = false; <availability.js>   → starts a dry run in the page; poll JSON.stringify(window.__yav),
      save it to .siruk-cache/yandex/availability-result.json, `show` it
      window.__yav_apply = true;  <availability.js>   → applies (on the user's yes); poll until phase "done"
  python scripts/yandex-availability.py record .siruk-cache/yandex/availability-result.json
      → state/yandex-products.json `available`, runs/<date>/yandex-availability.csv

Only the differences against the live store are written (one set-availability call ~1.1 s apart). The page
refuses to switch off more than 25 % of the cards that are on (a broken export, not a sell-out).
"""
import argparse, csv, datetime, importlib.util, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, 'state', 'yandex-products.json')
CACHE = os.path.join(ROOT, '.siruk-cache', 'yandex')
PLACE = 3315164


def glovo_portal():
    spec = importlib.util.spec_from_file_location('gp', os.path.join(ROOT, 'scripts', 'glovo-portal.py'))
    gp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gp)
    return gp


JS = r"""(() => {
  if (window.__yav && window.__yav.phase !== 'done' && window.__yav.phase !== 'error') return 'already running: ' + window.__yav.phase;
  const OFF = new Set(__OFF__), ON = new Set(__ON__), APPLY = !!window.__yav_apply, PLACE = __PLACE__;
  const S = window.__yav = {phase: 'listing', apply: APPLY, listed: 0, on_now: 0, to_off: [], to_on: [], done_off: [], done_on: [], failed: []};
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const post = async (path, body) => { const sk = (await (await fetch('/v1/pickerapp/csrf-token-generator')).json()).sk;
    const r = await fetch(path, {method: 'POST', headers: {'X-CSRF-Token': sk, 'Content-Type': 'application/json'}, body: JSON.stringify(body ?? {})});
    const t = await r.text(); if (!r.ok) throw new Error(r.status + ' ' + t.slice(0, 200)); return t ? JSON.parse(t) : null; };
  (async () => {
    try {
      const live = [];
      for (let off = 0; ; off += 100) {
        const j = await post(`/admin/v2/menu-catalog/place/products/list?place_id=${PLACE}&limit=100&offset=${off}&locale=en`, {});
        live.push(...j.products); S.listed = live.length; await sleep(1100);
        if (j.products.length < 100) break;
      }
      S.on_now = live.filter(p => p.is_available).length;
      for (const p of live) {
        if (OFF.has(p.id) && p.is_available) S.to_off.push(p.id);
        if (ON.has(p.id) && !p.is_available) S.to_on.push(p.id);
      }
      if (S.to_off.length > 0.25 * Math.max(S.on_now, 1)) { S.phase = 'error'; S.error = `refused: ${S.to_off.length} of ${S.on_now} cards would go off`; return; }
      if (!APPLY) { S.phase = 'done'; return; }
      S.phase = 'applying';
      for (const [id, want] of [...S.to_off.map(i => [i, false]), ...S.to_on.map(i => [i, true])]) {
        try { await post(`/admin/v1/menu-catalog/place/product/set-availability?place_id=${PLACE}`, {product_id: id, is_available: want});
              (want ? S.done_on : S.done_off).push(id); }
        catch (e) { S.failed.push([id, String(e).slice(0, 150)]); }
        await sleep(1100);
      }
      S.phase = 'done';
    } catch (e) { S.phase = 'error'; S.error = String(e).slice(0, 300); }
  })();
  return 'started ' + (APPLY ? 'APPLY' : 'dry run');
})()"""


def cmd_plan(a):
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    gp = glovo_portal()
    stock = gp.armsoft_stock(a.turnover, a.goods)
    gp.siruk_names()                                       # refreshes the Siruk export if older than a day
    ours = {str(r['sku']): r for r in json.load(open(gp.SIRUK_EXPORT, encoding='utf-8'))}
    cards = json.load(open(STATE, encoding='utf-8'))
    off, on, rows = [], [], []
    for sku, c in sorted(cards.items(), key=lambda kv: kv[1].get('name', '')):
        v = ours.get(sku)
        code = ((v or {}).get('accounting_code') or '').strip()
        if not v or not code:
            rows.append([sku, c.get('name'), code, '', '', 'no Siruk variant' if not v else 'no ArmSoft code', '', '?', ''])
            continue
        st = stock.get(code)
        if st is None:
            st = {'kg': v.get('measure_type') == 'mass' and sku.endswith(('-KG', '-100G')), 'stock': 0, 'bag': 0}
        need, why = gp.variant_need(v, st)
        have = None if need is None else st['stock'] >= need - 1e-6
        plan = ''
        if have is False:
            off.append(c['product_id']); plan = 'off'
        elif have is True and (a.on or code in a.on_codes):
            on.append(c['product_id']); plan = 'on'
        rows.append([sku, c.get('name'), code, st['stock'], 'kg' if st['kg'] else 'pcs', why, need,
                     {True: 'yes', False: 'NO', None: '?'}[have], plan])
    js = JS.replace('__OFF__', json.dumps(off)).replace('__ON__', json.dumps(on)).replace('__PLACE__', str(PLACE))
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, 'availability.js')
    open(p, 'w', encoding='utf-8').write(js)
    json.dump({'off': off, 'on': on, 'planned': datetime.datetime.now().isoformat(timespec='seconds'),
               'on_codes': a.on_codes, 'turnover': a.turnover},
              open(os.path.join(CACHE, 'availability-plan.json'), 'w', encoding='utf-8'))
    print(f'{len(cards)} Yandex cards: {len(off)} should be off (sold out), {len(on)} may go on'
          + (' (--on: everything in stock)' if a.on else f' (restocked: {" ".join(a.on_codes) or "none"})'))
    print(f'unknown (left alone): {sum(1 for r in rows if r[7] == "?")}')
    print(f'→ {p} ({len(js)} chars): the page compares with the live store and touches only the differences')
    if a.out:
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Yandex availability'
        ws.append(['Siruk SKU', 'Yandex name', 'ArmSoft code', 'Stock', 'Unit', 'Rule', 'Needs', 'We have', 'Plan'])
        for cell in ws[1]:
            cell.font = Font(bold=True, color='FFFFFF'); cell.fill = PatternFill('solid', fgColor='1F4E78')
        for r in sorted(rows, key=lambda r: ({'off': 0, 'on': 1}.get(r[8], 2), r[1] or '')):
            ws.append(r)
        for j, w in enumerate([12, 70, 9, 8, 5, 34, 6, 8, 6], start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(j)].width = w
        ws.freeze_panes = 'C2'; ws.auto_filter.ref = ws.dimensions
        wb.save(a.out)
        print('→', a.out)


def cmd_show(a):
    """Names for a page result (JSON.stringify(window.__yav) saved to a file): what would go off / on."""
    res = json.load(open(a.result, encoding='utf-8'))
    names = {c['product_id']: c.get('name', '') for c in json.load(open(STATE, encoding='utf-8')).values()}
    print(f"phase {res.get('phase')}, apply {res.get('apply')}, listed {res.get('listed')}, on now {res.get('on_now')}"
          + (f", error {res['error']}" if res.get('error') else ''))
    for key, label in (('to_off', 'OFF'), ('to_on', 'ON ')):
        print(f'{label}: {len(res.get(key, []))}')
        for i in res.get(key, []):
            print(f'  {label} {names.get(i, i)[:90]}')


def cmd_record(a):
    """Write the page's result (JSON.stringify(window.__yav), saved to a file) into the state map and the run log."""
    res = json.load(open(a.result, encoding='utf-8'))
    if not res.get('apply') or res.get('phase') != 'done':
        sys.exit(f'not an applied, finished run (apply={res.get("apply")}, phase={res.get("phase")})')
    cards = json.load(open(STATE, encoding='utf-8'))
    by_id = {c['product_id']: sku for sku, c in cards.items()}
    now = datetime.datetime.now().isoformat(timespec='seconds')
    log = []
    for ids, want in ((res['done_off'], False), (res['done_on'], True)):
        for i in ids:
            sku = by_id.get(i)
            if sku:
                cards[sku]['available'] = want
            log.append([now, sku or '', i, (cards.get(sku) or {}).get('name', ''), want,
                        a.note or ('ArmSoft stock: ' + ('back in stock' if want else 'none left'))])
    json.dump(cards, open(STATE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    d = os.path.join(ROOT, 'runs', datetime.date.today().isoformat())
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, 'yandex-availability.csv')
    new = not os.path.exists(p)
    with open(p, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['time', 'sku', 'yandex id', 'name', 'available', 'note'])
        w.writerows(log)
    print(f'recorded off {len(res["done_off"])}, on {len(res["done_on"])}, failed {len(res.get("failed", []))} → {p}')
    for f in res.get('failed', []):
        print('  FAIL', *f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan', help='which cards should be off / may go on, from an ArmSoft turnover export')
    p.add_argument('turnover'); p.add_argument('goods')
    p.add_argument('--on-codes', nargs='+', default=[], metavar='CODE', help="a posted receipt's ArmSoft codes")
    p.add_argument('--on', action='store_true', help='switch on every card in stock (not only a receipt\'s goods)')
    p.add_argument('--out')
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser('show', help="list a page result's off / on cards by name")
    p.add_argument('result')
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser('record', help="write an applied run's result into state/yandex-products.json")
    p.add_argument('result'); p.add_argument('--note')
    p.set_defaults(fn=cmd_record)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
