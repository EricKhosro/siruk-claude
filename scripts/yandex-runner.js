// Yandex upload runner (2026-11-18). Served from localhost; survives a page reload: re-run it.
(async () => {
  if (window.__ybusy) return 'already running';
  window.__ybusy = true;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const unz = async b64 => { const bin = Uint8Array.from(atob(b64.trim()), c => c.charCodeAt(0));
    return JSON.parse(await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'))).text()); };
  const csrf = async () => (await (await fetch('/v1/pickerapp/csrf-token-generator')).json()).sk;
  const post = async (path, body) => { const sk = await csrf();
    const r = await fetch(path, {method: 'POST', headers: {'X-CSRF-Token': sk, 'Content-Type': 'application/json'}, body: JSON.stringify(body ?? {})});
    const t = await r.text(); if (!r.ok) throw new Error(r.status + ' ' + t.slice(0, 200)); return t ? JSON.parse(t) : null; };
  const key = (n, m) => n.trim() + '|' + Number(m?.value);
  const listAll = async () => { const out = []; for (let off = 0; ; off += 100) {
      const j = await post(`/admin/v2/menu-catalog/place/products/list?place_id=3315164&limit=100&offset=${off}&locale=en`, {});
      out.push(...j.products); await sleep(1100); if (j.products.length < 100) return out; } };
  const S = window.__ys = {phase: 'loading', created: 0, existing: 0, off: 0, errors: {}, res: {}};
  try {
    let cards = [];
    for (const n of (window.__ychunks || ['01','02','03','04','05','06','07','08','09','10']))
      cards.push(...await unz(await (await fetch('http://localhost:8765/chunk-' + n + '.b64')).text()));
    S.total = cards.length;
    for (let pass = 1; pass <= 3; pass++) {
      S.phase = 'listing ' + pass;
      const store = new Map(); for (const p of await listAll()) store.set(key(p.name, p.measure), p);
      S.store_count = store.size;
      const todo = [];
      for (const c of cards) {
        const p = store.get(key(c.body.name, c.body.measure));
        if (p) { S.res[c.sku] = {product_id: p.id, image_url: p.images?.[0]?.url, available: p.is_available};
                 if (c.off && p.is_available) todo.push(c); }
        else todo.push(c);
      }
      S.existing = Object.keys(S.res).length; S.todo = todo.length;
      if (!todo.length) break;
      S.phase = 'uploading ' + pass;
      for (const c of todo) {
        const R = S.res[c.sku] = S.res[c.sku] || {};
        try {
          if (!R.product_id) {
            if (!R.image_url) {
              const blob = await (await fetch(c.wsrv)).blob();
              if (!blob.type.startsWith('image/') || blob.size < 5000) throw new Error('bad image ' + blob.type + ' ' + blob.size);
              const fd = new FormData(); fd.append('image', blob, c.sku + '.jpg');
              const up = await fetch('/admin/v1/menu-catalog/image/upload?network_id=13258', {method: 'POST', headers: {'X-CSRF-Token': await csrf()}, body: fd});
              if (!up.ok) throw new Error('upload ' + up.status + ' ' + (await up.text()).slice(0, 200));
              R.image_url = (await up.json()).image_url; await sleep(1300);
            }
            c.body.images = [{url: R.image_url}];
            R.product_id = (await post('/admin/v2/menu-catalog/product/create?brand_slug=siruk_pet_shop_shop', c.body)).product_id;
            S.created++; await sleep(1300);
          }
          if (c.off) { await post('/admin/v1/menu-catalog/place/product/set-availability?place_id=3315164', {product_id: R.product_id, is_available: false});
                       R.available = false; S.off++; await sleep(1100); }
          delete S.errors[c.sku];
        } catch (e) { S.errors[c.sku] = String(e); await sleep(3000); }
      }
    }
    S.phase = 'done';
  } catch (e) { S.phase = 'failed: ' + e; } finally { window.__ybusy = false; }
})(); 'started'
