# 2026-09-10 — CLAUDE.md restructure, pricing policy, Chewy-style toys, Grooming tree

## Docs
- `CLAUDE.md` 728 → ~125 lines. Detail moved to `reference/{pricing,hafo,brand-sites,admin-api,product-rules,csv-formats}.md`. Old file backed up at `.siruk-cache/CLAUDE.md.pre-2026-09-10.bak`.
- Pricing policy (`reference/pricing.md`): CSV price = cost; sale price = hafo row for the exact article code, per variant; never invented; unpriced rows → `no-hafo-price.csv` (reasons: `not on hafo` / `on hafo, size missing` / `wrong row`); only priced variants are created; a user-filled `Sale Price (AMD)` is honoured on re-import; vendor `R/Price` never used without asking.
- `scripts/lib.sh price_guard` — `create-product.sh` / `add-variant.sh` refuse a variant priced at or below cost (`ALLOW_BELOW_COST=1` only on explicit approval). Tested.
- One spec skill per product type: `toys` (complete, Chewy layout), `dry-food`, `wet-food`, `treats`, `supplements`, `grooming`, `accessories` (templates for the user to fill). `/add-products` step 6 reads the row's type skill.

## Admin changes (demo)
| What | Result |
|---|---|
| Product 201 "Per Pack" (test SKU, no cost) | deleted (204) |
| Attribute 10 `7015`/"test" | deleted (204) |
| Attribute 14 `toy-size` (42 values, on 133 variants) | removed from family 5, deleted (204) — user decision, Chewy layout |
| Attribute 15 `color-family` | created, 12 values (ids 264–275: Multi, Brown, Blue, Green, Red, Yellow, Orange, Pink, White, Black, Grey, Purple), added to family 5 |
| Family 5 Toys | now `[toy-type, material, toy-feature, color-family, lifestage, breed-size]` |
| Categories 27–33 | Dog → Grooming → Brushes & Combs, Shampoos & Conditioners, Grooming Tools, Paw & Nail Care, Ear Care, Skin Care |
| Categories 34–40 | same six under Cat → Grooming |
| `reference/attribute-values.json` | refreshed |

## Verified facts
- `attribute_value_ids.<code>` must be an integer; an array → 422 "must be an integer". Multi-value filters (Chewy's Toy Feature) are not possible on this backend. User: stay single for now.
- `DELETE /attributes/<id>` → 204; variants referencing it lose the key silently.
- Live price sweep (122 products / 136 variants before the deletion): no variant at or below cost; no multi-variant product with all variants at one price. Thin margin: 199 Silicate Litter 8 l (6000 vs 5780 cost, hafo figure).

## Consequence to resolve: 12 toy products lost their only variant axis
After `toy-size` went, these multi-variant toys have identical attribute combinations on every variant, so the storefront renders no selector and every `/dp/<id>` shows the default variant:
204 Playing Rope (3) · 207 Playing Rope · 212 Denta Fun Ball · 220 Flashing Ball · 221 Hedgehog Ball · 222 Stick · 223 Ball · 234 Sport Ball Dog Toy · 239 Chicken Toy for Dogs · 267 Vulture Gustav Dog Toy · 269 Hedgehog Dog Toy · 289 Aqua Toy Tugger.
New size-only toy ranges also cannot be created as multi-variant products (the API rejects a second variant with the same combination). Options are in the `toys` skill ("Variant axes"); needs the user's call.

## Waiting on the user
- Full Chewy value lists for Toy Feature (+23 unseen) and, if wanted, Material — to replace/extend attributes 13 and 12.
- The per-type skill contents for dry food, wet food, treats, supplements, grooming, accessories.
- Grooming attribute family (none exists) before the 86 Trixie grooming rows can be imported.

---

## Later the same day — Chewy vocabulary, toy-size back, translations

### Attribute vocabulary now replicates Chewy (`reference/chewy-attributes.json`, `scripts/sync-attributes.py`)
396 values created, 11 of ours renamed to Chewy's wording (With Squeaker→Squeaky, Glows in the Dark→Glowing & Light-Up, With Catnip→Catnip, Thermoplastic Rubber (TPR)→Thermoplastic Rubber, Vinyl→Vinyl / PVC, Fabric (Polyester)→Synthetic Fabric, Natural Rubber→Rubber, Plush (Polyester)→Plush, Dry→Dry Food, Wet→Wet Food, Food Topper→Food Topping). New attributes: 16 `toy-size` (hidden from filters, per the user's reversal), 17 `ingredient`, 18 `product-form`, 19 `active-ingredient`. Families extended (Dry +packaging +ingredient; Wet +ingredient; Treats +breed-size +packaging +ingredient; Supplements +product-form +active-ingredient +special-diet +flavor +breed-size +material; Toys +toy-size). Skipped on purpose: Collection, Made In, Deals & Savings.
**Kept, not in Chewy (your call to delete):** toy-feature: Massages Gums, Mint Flavour, Shock Absorber, With Bell, With Rope · material: Cotton/Polyester, Paper Cord, Plush · special-diet: Hypoallergenic, Monoprotein, Sterilised · flavor: Anchovies, Chicken and Eggs, Chicken and Herring, Egg, Fish, Ham, Herring, Herring and Salmon, Papaya, Peas, Pineapple, Prawns, Seabass, Squid, Surimi · food-form: Paste, Powder, Tablets.
**Single-value caveat stands:** Ingredient / Active Ingredient / Special Diet / Health Feature hold one value per variant here; Chewy's are multi-tag.

### toy-size restored
`scripts/restore-toy-size.py` put the size back on all 120 toy products (133 variants) from the variant labels; product 204's three rope sizes are distinct again. No label lacked a "<n> cm".

### Translations (ru / hy) — mechanism verified against the demo API
Read with `Content-Language`, write with `"locale"` in the body, one write per locale. **Per-locale:** product name, meta, variant about/ingredients/feeding; category name. **Single-language (last write wins for every locale):** variant labels, slugs, attribute names and value labels — a Russian PUT on value 275 overwrote the English "Purple" (restored) — brands untested. Tooling: `scripts/set-translation.py` (product; refuses to touch single-language fields; verifies `en` unchanged), `scripts/translate-categories.py`. Done: all 40 categories in ru+hy; product 321 (Snack Roll) in ru+hy as the first real product. Rule 12 added to `CLAUDE.md`; `/add-products` step 9b.
**Not done:** the other 121 existing products are English-only — backfill is a separate decision (see reply).

### Health & Pharmacy sub-tree — proposal, not created
Chewy's dog list, mapped onto our tree (mirror under Cat with the cat-relevant subset):
Dog → Health & Pharmacy → Heartworm Prevention & Dewormers · Dental Care · Over-the-Counter Medicine · Health & DNA Test Kits · Itch Relief · Ear Care · Puppy Milk Replacers · Eye Care · Calming Aids · Medicated Shampoos & Topicals · First Aid · Pill Dispensers · Skin & Coat Care · Hip & Joint Care · Digestive Care · Nail & Paw Care.
Open: keep the flat 12 Vitamins & Supplements, or replace it with Dog/Cat → Health & Pharmacy and re-file its products.

---

## Evening — Health & Pharmacy tree, Cat Litter, translation backfill

### Categories (all with ru/hy names)
- **Health & Pharmacy** from Chewy's *menu* (species-specific, 8 leaves each) rather than the 16-item listing pasted earlier: Dog 41 → 42–49, Cat 50 → 51–58 (dog has Heartworm & Dewormers, cat has Urinary Tract & Kidneys).
- **Cat → Litter 59** → 60 Clumping, 61 Scented, 62 Unscented, 63 Natural, 64 Lightweight, 65 Crystal. Product 199 (Trixie silicate litter) moved from Accessories to 65 Crystal.
- **Cat → Supplies 66 → 67 Litter Boxes & Accessories** — the one Supplies leaf needed for litter trays; the rest of Chewy's Supplies tree was not created.
- **12 Vitamins & Supplements deleted** (it had no products; supplements now go in 43 / 52). 13 Accessories is empty and kept.
- Product 278 (Junior Dog, plush puppy toy) was sitting on the Toys parent → 17 Plush.

### Data fixes
Three broken English names from an old scrape renamed: 247 → "Fox Latex Toy", 230 → "Cow Plush Toy", 285 → "Silent Ball Dog Toy".

### Translation backfill
`reference/translations.json` — en → ru/hy dictionary: 109 product names, 69 recurring Trixie bullet phrases, 4 long paragraphs. `scripts/backfill-translations.py` applies it through `set-translation.py` (HTML structure kept, only text nodes translated; every string resolved — nothing left in English). Result in `.siruk-cache/backfill.log`. Reuse the dictionary on future Trixie imports — the bullets repeat.
Note: the catalogue today is 120 toys + 1 litter (the food imports from August are no longer on the demo), which is why the backfill is toy vocabulary.

---

## Night — how hafo prices variants, and a full price check

Learned in the chrome-devtools browser on `https://hafo.am/products/hangucavor-paran-voskoranman` (knotted rope, 8 sizes): the size selector is `<select name=product_data_id>` over the listing's `product_additional_information[].id` rows; changing it fires `POST /product/change` (`color-id`, `image-color`, `product_id`, CSRF header) which returns `{sku, price, wholesale_price, in_stock, …}` and the page shows that `price`. It equals the row price in `/products/filter` — the API rows are the storefront price. The description's typed price table is stale (3275Tx: 3100 vs real 2750). Details in `reference/hafo.md`.

`scripts/check-hafo-prices.py` — every Siruk variant vs its hafo row, cross-checked through `/product/change`. **135 variants: 133 match, 1 mismatch fixed, 1 tie broken.**
- Fixed: 199 Simple'n'Clean Silicate Litter 8 l (sku 4020) **6000 → 9250** (hafo wholesale 5780 = our cost; `/product/change` confirms 9250). Note this variant was 9250 in yesterday's report, so something set it to 6000 in between.
- Tie: 304 Set Rainbow balls (4097) matched both Trixie `TX 040971` and a Monge kibble row `004097` (maker field empty on hafo); wholesale 965 = cost picked the balls, price 1550 already matched.
Full table: `runs/2026-09-10/price-check.csv`.

---

## Night 2 — translations everywhere the backend allows

**Can a create carry translations?** No. Checked in `cs-dev-hub` (`_dataStore.js`, `Form/Container/index.js`): the SPA sends one flat `locale` key with the body and re-fetches per locale; the switcher is disabled on create. Confirmed on the API: `POST /products` with `"locale":"ru"` created a product whose `en`/`hy` names were empty; a nested `{"name":{"en","ru","hy"}}` 422s; a `translations[]` array is ignored. So every record is created in `en` and then written once per extra locale — which is what all our scripts now do in one flow.

**What stores per locale:** product name + variant texts, category name, brand name + meta. **What does not** (verified with `locale`, nested, `translations[]` and `label_ru` shapes on a throwaway attribute, value and family — every shape rewrote the single English label): attribute `name`, attribute-value `label`, attribute-family `name`, variant `name`. That is a backend gap — the storefront filter and variant selector print exactly those strings. Dev question logged in `reference/admin-api.md`.

**Done on the server**
- Brands: all 19 written in `ru` and `hy` (`scripts/translate-brands.py`; Latin name in every locale, meta translated).
- Products (121) and categories (66) were already trilingual; `scripts/verify-translations.py` now audits all three resource types and passes (identity translations such as "TPE", "Turbinio", "MOT®-Fun" are recognised via the dictionary).
- Attributes: the complete ru/hy vocabulary is prepared — 17 attribute names and all 629 value labels in `reference/translations-attributes.json`. `scripts/translate-attributes.py` applies it, but probes first and refused today (probe output: English overwritten). Run it again once the backend stores attribute labels per locale.

**Rules updated:** `CLAUDE.md` rule 13 (everything that can be translated is: products, categories, brands; one locale per request), `/create-brand` step 6b, `/manage-attributes` "Translations".

---

## Night 3 — every gallery image, and the attribute-translation question settled

### Images
Cause: `scripts/trixie-image.sh` returned the first CDN probe hit, so every imported toy had one picture. Rewritten to read the product page's gallery (via the cached catalogue) and return **every** 1600mx1200m image keyed to the article — `PHO_PRO_CLIP` packshot first, then `PHO_PAC_CLIP`, lifestyle `PHO_PRO_DOG/CAT`, group shots, `GRA_PRO` drawings — with a CDN probe (all hits) as fallback for articles without a page. `scripts/add-all-images.py` backfilled the catalogue: **134 variants, 131 → 275 images, 73 variants gained pictures** (1 image: 63 variants — Trixie lists one shot per size for many ropes/balls; 2: 30; 3: 22; 4: 12; 5: 4; 6: 3). Existing thumbnail kept first. Rule added to `CLAUDE.md` (7), `/add-products` step 5 and the `toys` skill; `reference/brand-sites.md` documents the prefixes.

### "Plush shows the same in every language"
Not a translation I wrote — the backend keeps one label per attribute value and the admin UI shows a Ru/Hy switcher on that form only because the framework enables it for every form (`defaultFormConfig.trans:!0`; the attribute/value forms do not override it — checked in the deployed bundle). Re-verified today on a throwaway value with `locale`, nested `{en,ru,hy}`, `translations[]` and `label_ru` shapes: each rewrote the English. `scripts/translate-attributes.py` probes and refuses. The ru/hy vocabulary (17 attributes, 629 values — Plush = Плюш / Պլյուշ) is ready in `reference/translations-attributes.json`. `CLAUDE.md` rule 13 now forbids reporting translation status from anything but `verify-translations.py` and requires naming what the backend cannot store per locale.


## Simba import (later today)

See `runs/2026-09-10/simba-report.md` — products 324, 325, 326; 15/15 rows (one via the new sibling-price fallback, CLAUDE.md rule 2a); 7 attribute values added.
