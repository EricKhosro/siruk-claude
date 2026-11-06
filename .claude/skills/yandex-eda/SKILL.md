---
name: yandex-eda
description: List and maintain Siruk's products on Yandex Eda through the retailer cabinet (ЛК Ритейлера, pickerapp.eda.yandex.ru) — one Yandex card per Siruk variant, Armenian name in Yandex's order, white 1000×1000 photo, EAN, price per store, category tree. Drives the cabinet's own JSON API from the Claude desktop app's built-in browser, where the user's Yandex sign-in lives. Use when the user asks to add / update / remove products on Yandex, Yandex Eda, the picker app, or ЛК Ритейлера, or to check their moderation status.
---

# Yandex Eda catalogue

Read `reference/yandex/README.md` first: the account ids, every endpoint,
the product body and Yandex's name / photo / delivery rules. This skill is
the procedure.

## 0. Session

1. Open the cabinet in the **built-in browser** (never Claude in Chrome,
   never chrome-devtools: the sign-in lives in the built-in browser's
   profile): `mcp__Claude_Browser__preview_start` with
   `url: https://pickerapp.eda.yandex.ru/pa/catalog/edit?id=siruk_pet_shop_shop`.
2. `get_page_text`. A `passport.yandex.ru` login page means the session
   expired. Call `tabs_context`. If the pane is hidden, ask the user to
   press Cmd+Shift+B, then ask them to sign in there. **Never type the
   password.**
3. Every call below is a `fetch` in `mcp__Claude_Browser__javascript_tool`
   on that tab. httpOnly cookies ride along. Start each batch with:

```js
const sk = (await (await fetch('/v1/pickerapp/csrf-token-generator')).json()).sk;
const H = {'X-CSRF-Token': sk, 'Content-Type': 'application/json'};
const api = async (path, body) => { const r = await fetch(path, {method: 'POST', headers: H, body: JSON.stringify(body ?? {})});
  const t = await r.text(); if (!r.ok) throw new Error(r.status + ' ' + path + ' ' + t.slice(0, 300)); return t ? JSON.parse(t) : null; };
```

Reads are free. **Writes (create / update / delete, category changes) need
the user's go-ahead for the batch.** Show them the planned cards first.

## 1. Build the cards (Siruk → Yandex), one per variant

**Language:** names follow Zoovet (Latin brand/line + Russian, see `name`); descriptions
and category names stay **Armenian** (Zoovet's own categories are Armenian too). Sources: the
live catalogue export in `hy` (descriptions) and `ru` (name words), one row per variant.
Skip a variant whose `content` is empty unless its label is a plain size («250 ml»); a toy,
bowl or leash has no mass/volume for `measure`, so ask the user.

| Yandex field | From Siruk |
|---|---|
| `name` | **Zoovet's pattern** (user, 2026-11-02): **brand + line in Latin**, then a **Russian** description (product type, flavour, who it is for), then the **pack size** in Russian units. «Trixie Junior Soft Snack Dots лакомство для щенков, 140 г», «Club 4 Paws Premium Sterilised Cat влажный корм с кроликом в желе для стерилизованных кошек, 80 г», «Ferma Kota Fedora лакомые палочки с уткой для кошек и котят, 3 шт × 5 г». Russian words from the Siruk `ru` export. Unlike Siruk, the size **is** in the name. No CAPS, quotes, ad words or Zoovet-style «#code». |
| `description` | hy description, HTML stripped, ≤ 2400 chars, no links |
| `vendor_name` | brand name |
| `barcodes` | `[{"value": barcode}]` only for a real 8/13-digit EAN. Never a 5-digit PLU. |
| `measure` | mass → `GRM` (< 1000 g) / `KGRM`; volume → `MLT` / `LT`; value = content × pack_count. `count` items have no unit: use the pack's mass if known, else ask the user. |
| `package_quantity` | `pack_count` when > 1 |
| `places_prices` | `[{"place_id": 3315164, "price": {"value": "<price>"}}]`. **The Siruk price** for now (PM, 2026-11-02); the suggested prices in `final/yandex/` are not used yet. |
| `place_ids` / `place_ids_to_add` | `[3315164]` |
| `category_id` | the Yandex category made from the Siruk leaf (step 2) |
| `images` | `[{"url": image_url}]` from step 3 |

**Skip, and list for the user:** 1 kg / 100 g loose variants (`-KG`,
`-100G` SKUs), out-of-stock or discontinued variants, vet medicines (Yandex
bans vet pharmacy without a licence; supplements need a per-item call),
items bigger than 40×25×40 cm, and variants with no usable photo.

## 2. Categories

`categories/list` first. Mirror Siruk's tree (user, 2026-11-02): pet →
group → leaf, with Siruk's Armenian category names. Delete the empty
placeholder «Կեր» once the tree exists. Create only the missing
ones (`category/create`, `parent_id` for children). Keep a map
`state/yandex-categories.json` (`siruk leaf id → yandex uuid`).

## 3. Photos

Yandex wants JPEG/PNG ≥ 800×600, ≤ 25 MB, white background, whole product
centred, no hands / animals / other brands' watermarks. Take the variant's
**first Siruk image** (rule 7 makes it a clean packshot). Never a hafo
placeholder (watermarked).

- Pad it onto a **white 1000×1000** square: `square_jpeg(raw, side=1000)`
  from `scripts/glovo-export.py`. The Glovo squares in
  `.siruk-cache/glovo/squares/` are 500×500, **too small** to reuse. Write
  them to `.siruk-cache/yandex/squares/m<media id>.jpg`.
- An original with a long side < 800 px gets upscaled: check it by eye,
  and list it if it looks soft.
- Upload from the page. The cabinet tab can't fetch `api.siruk.am/storage` (no CORS) or localhost, so the square comes from
  **wsrv.nl** (public image proxy, CORS `*`), which also does the padding: `https://wsrv.nl/?url=<encoded Siruk image url>&w=1000&h=1000&fit=contain&cbg=white&output=jpg&q=90`
  (verified 2026-11-02). Fetch → Blob → `FormData` field `image` → `POST
  /admin/v1/menu-catalog/image/upload?network_id=13258` (send only the CSRF header). Look at the squares first
  (download the same wsrv URLs with Python into a contact sheet). Keep `{media id: image_url}` in
  `state/yandex-images.json` so a re-run never uploads twice.

## 4. Write

Search before create: `products/list` with `name_part`, or the saved map
`state/yandex-products.json` (`siruk sku → yandex product uuid`). An existing
card is updated (`product/update`), never duplicated. Create with
`product/create?brand_slug=siruk_pet_shop_shop`. Pace ~1 call / second, in
batches of ≤ 25, and save the map after each card.

## 5. Verify and report

- `product/detail-info` per new card: name, price, measure, image present.
- `moderation_info.status` starts `required`. Re-check later.
  `/admin/v1/brand/products/moderation` lists the rejections and their
  reasons, and `support/retail/ru/catalog/moderation-errors` explains them.
- Report: created / updated / skipped (with the reason) in
  `runs/<date>/yandex-report.md`, and anything still open in
  `state/open-items.csv`.

## Keeping it in sync

Price change in Siruk → `product/update` (or store-level
`place/products/update-or-create`). Out of stock → `place/product/set-availability`
`is_available: false`. A deleted Siruk variant → `products/delete`.
