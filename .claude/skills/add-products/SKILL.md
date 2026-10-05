---
name: add-products
description: Import products from a CSV into the Siruk admin panel, sourcing data from each product's brand official website and filling variant attributes from the page text. Use when the user provides a CSV of product names to add, or asks to add/import products to the site. Drives chrome-devtools MCP for the brand sites; creates products via the admin JSON API.
argument-hint: [path to CSV file]
---

Import the products listed in the CSV into the Siruk admin panel in three
phases: **A** gather every row's data (no admin writes), **B** make sure every
row has a product type that allows what it will carry, **C** write the rows
one at a time.
CSV path (or inline product names):

$ARGUMENTS

Read `CLAUDE.md` first (hard rules, pipeline, environments), then the
reference doc for the step you are on: `reference/pricing.md` (price),
`reference/hafo.md` (identity lookup), `reference/brand-sites.md` (sources,
country TLDs), `reference/zoovet.md` (zoovet.am and nemo.am, the other two
Armenian shops), `reference/image-sources.md` (every image source, in order),
`reference/admin-api.md` (payloads, ids), `reference/product-rules.md`
(grouping, naming, categories). Key constraints:

- **The CSV price is our cost. The sale price is hafo.am per article code,
  per variant. Never invent, derive or estimate a sale price.** When hafo
  does not price the row: a
  **confirmed** zoovet.am or nemo.am price (rule 2b), then the sibling
  fallback (rule 2a); a row none of those can price goes to
  `runs/<date>/no-hafo-price.csv` and is NOT imported (`reference/pricing.md`).
  A register price that is blank, at or below cost (rule 5) or a typo-level
  jump is not a price — but the row is **not** parked for that: it falls back
  to hafo's variant price, then a confirmed zoovet.am / nemo.am price, then
  the sibling fallback (user, 2026-10-02; `prepare-run.py` does it and notes
  the overridden register price). Only a row none of them can price above
  cost is held and listed.
- **Exception — the user names a sale-price column up front** ("column X is
  our selling price"): that column is `price` for the run and the whole
  price-lookup chain (register, hafo, zoovet/nemo, sibling) is **skipped** for
  those rows. hafo is still used for identity. Rule 5 still applies — a
  value at or below cost stops the row. Only when the user said it for *this*
  run; a filled sale-price column the user did not name is not that
  (`reference/pricing.md`).
- **No product without an image, none without a product type.** Both
  write scripts refuse an image-less product (`ALLOW_NO_IMAGE=1` only on the
  user's say-so) and a missing `attribute_family_id` (the API's name for the
  product type). Types are created/extended in phase B, never mid-write
  (CLAUDE.md rule 8b).
- **Size is the variant's net content, stock is a ledger** (CLAUDE.md 8a,
  10a): `measure_type` + `content` + `pack_count`, `price` = the pack price,
  `initial_stock` on new variants only — **10 on every variant, whatever the
  CSV Qty** (user 2026-10-01). A per-kg price on the row → **every bag gets a
  "1 kg" pack variant** (`<bag sku>-KG`, price = per-kg price, CLAUDE.md 8a);
  never `sale_mode: "weight"` (paused by the PM 2026-10-01). **No pack
  size in the product Name** (CLAUDE.md 12). Each pack size shows its own
  photo (rule 7). Suppliers are out of scope.

- Source data from the **brand's official website** (per the brand map in
  CLAUDE.md), NOT Chewy. Sites are **read-only** (no cart, no account, no forms).
- Never `take_snapshot` on source product pages — extract with `evaluate_script`.
- In phase C, one product fully finished (written + verified) before starting the next.
- **Never create a product that already exists** — search first; if it's there,
  the row goes on as a new variant (step 8/9).
- **`category_ids` is a list — give a product every leaf it belongs to.** A
  pack that says "for dogs and cats" gets the **mirror leaf in both species'
  trees**; a dewormer gets Heartworm & Dewormers + Pharmacy & Prescriptions; a
  veterinary diet gets its food leaf + Health Condition 5. Never add a parent
  (parents roll their children up on their own) and never add a species the
  brand does not claim. Full table in `reference/product-rules.md`.
- Do not invent categories/attribute values that don't exist in the admin; flag
  in the report instead. A **missing brand** is the one exception: run the
  `/create-brand` skill for it (official logo → media library → brand) and use
  the id it returns.
- **Never put the brand in the product Name** — the storefront prints the brand
  before the name. Strip the CSV's brand/`RC ` prefix ("RC Mini Adult 8kg" →
  Name "Mini", label "Adult 8 kg"). The slug keeps the brand.
- Write via the **admin JSON API using `scripts/`** (see `scripts/README.md`),
  not the UI form and not hand-typed curl. The browser is only for brand sites
  and for reading the token once.

## Steps per run

**Phase A — gather (steps 1–6, every row, no admin writes).** Do 1–2 once,
then 3a–6 for every row and keep the result per row (a card,
`reference/card-schema.md`, when the run was prepared with
`scripts/prepare-run.py`; otherwise a JSON per row in `runs/<date>/rows/`):
identity, price, name/label, size (`measure_type`/`content`/`pack_count`),
categories, the product type you'd give it, attribute picks with quotes,
**wanted-but-missing** values/attributes, image URLs, texts, `existing_id`.

**Phase B — product types (once per run, before any write).**
1. `python3 scripts/product-types.py --dump` (live roles and flags).
2. Spawn the `attribute-manager` agent in pre-import mode and feed it the
   batch: per row the code, name, intended type, category leaves, size
   (measure + content), attribute picks and the wanted-but-missing list. It
   maps every row to a product type, creates or extends types (and the values
   the rows need) with logical roles/flags, and returns a row → type id map.
   The user delegated these decisions to us; the PM edits later. Put the
   agent's created/flagged lists in the report.
3. Save the agent's map as `runs/<date>/product-types-map.json`
   (`{code: type id}`), refresh the menu (`scripts/refresh-attributes.sh`,
   `scripts/live-ids.py`), build every payload — for a prepared run
   `scripts/card-import.py --run runs/<date> <code> --payload` per card — and
   run `python3 scripts/product-types.py --check <payloads…>`. Every payload
   must pass before phase C; a failing row is fixed or held, never written.

For a prepared run, phase C goes one of two ways:

- **New products: bulk** (`POST /products/bulk`, 2026-10-01). Write each card's
  ru/hy first (step 9b's content) as `runs/<date>/tr/<code>-ru.json` and
  `-hy.json`, in set-translation.py's shape and keyed by sku, the `-KG` twin included.
  Then run `scripts/card-import.py --run runs/<date> <code> --queue` per card, which
  uploads the gallery and writes `runs/<date>/bulk/<code>.json`. Finish with
  `scripts/bulk-create.py runs/<date>/bulk/*.json --out runs/<date>/bulk-results.json`.
  That one call creates en/ru/hy together, refuses an item without ru/hy, fails a bad
  item alone, reads every product back and runs verify-translations.py. Then fix any
  failed items and re-run with just those files, and do step 10 per id from the results.
- **Existing products** (`existing_id`): one at a time with
  `scripts/card-import.py --run runs/<date> <code> --write` (uploads the gallery, then
  add-variant.sh, register loose twin included), then steps 9b–11.

**Phase C — write (steps 7–11, one row at a time).**

1. **Auth** — check `scripts/api.sh GET /account` first; if it returns 200 the
   token in `.siruk-token` is still good (they last ~1 year — do NOT re-capture
   per session). On 401: navigate to the admin, run
   `JSON.parse(localStorage.access_token).token` via `evaluate_script` (log in
   with CLAUDE.md credentials if needed), write it to `.siruk-token`, re-verify.
   Then confirm the reference ids with `scripts/ids.sh` — the wipe renumbered
   brands/categories once already, so never trust ids from an old report.
2. **Load the attribute menu** — `reference/attribute-values.json`
   (attribute code → label → value id). If the user edited attributes in the
   admin since it was written, refresh it first: `scripts/refresh-attributes.sh`.
   This menu is the ONLY source of pickable attribute values.
3. **Read the CSV** with the Read tool. For each row, do steps 3a–10. If the
   row's brand isn't in the admin brand list, run the `/create-brand` skill for
   it first and use the brand id it returns (creating one brand once, not per
   row); note the creation in the report.
3a. **hafo first** — `scripts/hafo-lookup.py --code <article code> --name
   "<name>"` (`reference/hafo.md`). **A row with no article code** (the PM's
   register) is identified by name first — `scripts/identify-by-name.py`:
   hafo by Armenian name, then nemo.am / zoovet.am by name (the script adds
   their hits as `shop_candidates` when hafo is weak), then a web search —
   and only a hit where brand, line, lifestage/function, flavour, pack (and
   size/colour for accessories) ALL match is taken; its code goes into
   `state/register/match-overrides.json` and the row is logged in
   `state/register/identified-by-name.csv` (CLAUDE.md rule 6). A hit that matches
   only part of that → `not-found.csv`, candidate named. The row continues only with
   `confirmed: true` **and** `price_source: "variant"`; that variant row's
   `price` is the sale price (hafo's `wholesale_price` is only a tie-break
   between several candidate rows, never a gate). Confirmed but unpriced → `runs/<date>/no-hafo-price.csv`; not
   confirmed → `runs/<date>/not-found.csv`. Either way stop the row here. Each
   variant of a multi-variant product gets its own lookup and its own price.
   **One fallback** (CLAUDE.md rule 2a, `reference/pricing.md`): an unpriced
   row that is a variant of a product with a hafo-priced variant **and has the
   same CSV buy price** as that sibling takes the sibling's hafo sale price —
   unless same-cost siblings disagree on price (then the CSV, `Why no price`
   = `sibling prices differ`). Log it in `runs/<date>/sibling-priced.csv` and
   the report. Identity, images and texts still come from the brand site.
   **Before that fallback, try zoovet.am and nemo.am** (CLAUDE.md rule 2b,
   `reference/zoovet.md`; neither outranks the other), both **by product
   name** — neither carries our article code:
   `scripts/zoovet-lookup.py --search "<russian/latin words>" [--brand <slug>]`,
   `scripts/nemo-lookup.py --search "<armenian/latin words>" [--brand <slug>]`.
   Their hits are always `confirmed: false` — usable only once you confirm the
   identity (the article read off the pack in the full-size photo, or brand +
   line + flavour + pack all matching) and the price beats cost. Log it in
   `runs/<date>/zoovet-priced.csv` / `nemo-priced.csv` (same columns). An
   unconfirmed candidate is not a price: put it in the CSV's `Why no price`
   text instead.
4. **Find on the brand's official site** — resolve the site from the row's
   `Brand / Vendor` using the brand→site map in CLAUDE.md. A brand has more
   than one official domain: when the main site has no page for the article,
   try its **country sites** before any fallback (Trixie: `trixie.es` via
   `scripts/trixie-es.py --article <art>`, which also confirms the article
   through the page's `Ref.`). Use the site's own
   search or product-finder (or a scoped web search
   `site:<brand-domain> <product name>`) to reach the product page. Confirm the
   match: same brand, line, and pack weight as the CSV name. If the exact weight
   isn't on the site, use the closest product page for copy/images and keep the
   CSV pack weight in the admin Name/Label. If the brand site is unreachable or has no
   product page, use the fallback sites in order — country TLD, then the
   **barcode lookup** (`scripts/barcode-lookup.py --code <art> --name "<name>"`,
   then WebSearch the EAN in quotes): it tells you what the product is and
   which pages print our barcode. Identity needs two independent EAN pages
   that agree with hafo's name; name, texts and photos come only from pages
   that print our exact EAN; log the row in `runs/<date>/barcode-sourced.csv`
   (`reference/image-sources.md` → "Barcode lookup"). Also run it whenever the
   identity is in doubt (flavour, recipe, size) — don't park such a row
   before its barcode has been searched. Then
   **4lapy.ru by EAN** (`scripts/4lapy-lookup.py --search "<brand line words>"
   --ean <ean>`: photos + texts, confirmed by the barcode), then zoovet.am
   (confirmed by hand), then **petshop.ru for texts only** (confirmed by hand,
   never its photos), then a general web search, then **Google search +
   Google Lens in a headed Chrome — the `/google-lens` skill**
   (`scripts/google-lens.py`, Scrapling; batch every row still without a photo
   into one jobs file and run it in the background; a CAPTCHA goes to the user),
   and only then a hafo placeholder —
   and mark the row's source as "fallback", naming which one.
   **Texts** (name, description, composition, feeding) follow the same
   ladder, and when every site above has nothing: **Google search in the same
   headed browser** — `search` jobs for the EAN, `"<article>" <brand>` and the
   brand + line + flavour + pack in Latin and Cyrillic, then `page` jobs on the
   best result pages (`scripts/google-lens.py`, `"kind": "page"`, with the EAN
   and article as `keys`). A page is accepted when it prints our EAN/article,
   or when two independent pages match every axis by name. Nothing acceptable
   → **hafo's own text** last: its Armenian `content_html` (price table and
   maker line stripped) becomes `hy` and is translated to `en`/`ru`; the row
   goes on `runs/<date>/needs-text.csv`. Log every try in
   `runs/<date>/text-sources.csv` (`reference/image-sources.md` → "Texts when
   the brand has no page"). Their texts are
   Russian: evidence and the `ru` translation; translated into English only
   when no English source exists. petfood.ru and zoozavr.ru are not usable
   (`reference/image-sources.md` → "Fallback sites").
5. **Extract** with a single `evaluate_script` returning JSON only:
   title, brand, pack weight/format, **every** gallery image URL (highest
   resolution; upload them all, a product with one picture is a defect —
   and then order them so a **clean product shot leads**: the product alone on
   a plain background, no animal / hand / scene / group; the page's own order
   often leads with a lifestyle photo, so look at the first image before you
   write, see CLAUDE.md rule 7),
   description/benefits, composition/ingredients, feeding guide, and the raw
   text of any spec/attribute sections. Ignore any price on the site (sale
   price comes from hafo, cost from the CSV). Missing sections → `null`, don't fail. Brand sites vary
   a lot in structure — target the specific DOM of that page rather than
   assuming a fixed layout.
6. **Fill attributes** — first decide the row's **product type** (dry food,
   wet food, treats, toys, supplements, grooming, accessories, litter — or a
   new kind the phase-B agent will create) and read that type's skill
   (`.claude/skills/<type>/SKILL.md`): leaf categories, how to pick values,
   how to encode its size. Which attributes the type carries and their roles
   are the live product type's (`reference/product-types.json`). Then, for
   each attribute, pick a value under these hard rules:
   - **Closed menu:** only labels present in `reference/attribute-values.json`,
     or `null`. Never invent a value, never submit a label not in the menu.
   - **Evidence required:** every non-null pick needs a supporting quote from
     the CSV row or the page text. No quote → `null`.
   - **CSV wins** over the brand site on any conflict (e.g. pack weight).
   - **Weights are metric, kilogram-based — never lbs/oz.** Convert a US source
     (`lb x 0.4536 = kg`), preferring the brand's own metric pack size.
   - **The pack size is the variant's net content, not an attribute**
     (CLAUDE.md 8a): `measure_type` `mass` + `content` in g (2 kg → 2000),
     `volume` in ml (0.4 ml pipette → 0.4), `count` in pieces (10 tablets →
     10); a multipack is `pack_count` × one item (12 × 85 g → 12, 85; a
     2-pipette pack of 0.5 ml → 2, 0.5). Supplements choose per variant:
     tablets/pipettes/collars `count`, liquids/pastes ml/g. What is *not* net
     content: a dose band (`1–4 kg` → `pet-weight-range` 27), a length or a
     bowl capacity (`75 cm`, `0.4 l/ø 17 cm` → the `size` option 28). A pack
     with no printed content (a chew in cm, a toy) has none —
     `ALLOW_NO_SIZE=1` for a sized type.
   - **Our definitions win** over the brand's: `reference/data-tables.md` defines
     how Siruk understands attribute concepts (Lifestage age bands, etc.) and
     how to translate brand wording into them. Read it before picking any
     attribute it covers — e.g. a cat food the brand labels "Senior 7+" is
     **Adult** for us. A mapping made via that file counts as direct evidence.
   - **Confidence gate:** if the pick is an inference rather than a direct
     statement (e.g. "maintains healthy weight" → Weight Management on a
     regular adult food; packaging visible only in photos), treat it as
     below-threshold: leave `null` and record it in the report as a flagged
     candidate with the evidence. Direct statements ("for adult dogs",
     "grain-free recipe", "salmon 25%") are above threshold.
   - **Not-applicable is silent:** e.g. Food Texture on dry food → `null`, no
     flag.
   - **Misses:** when the text clearly states a fact that has NO matching value
     in the menu (e.g. texture "in jelly" absent), leave `null` and record
     `{attribute, wanted_label, evidence, row}` for the report. Same if a whole
     attribute is missing for a new product domain.
   - Resolve picked labels → ids via the menu; double-check every id exists
     before building the payload. Per-variant facts (**lifestage**, size,
     flavor, packaging) are set per variant and sourced from that variant's own
     brand page; product-wide facts (breed size, food form, diet, health
     feature) are identical on every variant — if they aren't, it's a separate
     product (see `reference/data-tables.md`).
7. **Images** — `scripts/upload-media.sh <image-url> products/<brand-slug>/<type>`
   per image (it downloads with a browser User-Agent and prints the media id).
   The folder is required by rule 7 — never the media root; `<type>` is the
   type skill's name (`dry-food`, `toys`, …). `MEDIA_DIR=…` in the environment
   does the same for scripts that call it without the argument. Collect the ids for the
   variant's `images` array. The script sanitizes the filename and confirms the
   uploaded file is really readable before printing an id — the api otherwise
   hands back ids whose files 404 (see CLAUDE.md). If it dies with "never became
   readable", **do not fall back to an unverified id**: flag the row in the
   report and move on. Before writing, **look at the image you put first**
   (download it and view it): it must be a clean packshot — product alone,
   plain background, no animal, no hand, no scene, no group of siblings. If it
   isn't, move the packshot to the front (Trixie: `PHO_PRO_CLIP`, then
   `PHO_PAC_CLIP`; other brands: by eye). A lifestyle/group shot may lead only
   when the product has no clean image at all — then add the variant to
   `runs/<date>/needs-packshot.csv`.
   Source order for the gallery: brand site **including its country domains**
   (`scripts/trixie-image.sh` already merges trixie.es) → photos from pages
   the **barcode lookup** found that print our exact EAN (looked at, clean,
   unwatermarked) → a **confirmed**
   zoovet.am original, which is unwatermarked and therefore a finished image
   (it leads the gallery and the variant does NOT go on `needs-image.csv`) →
   the **`/google-lens` skill** (Google search + Images + Lens on hafo's photo,
   `scripts/google-lens.py`, headed Chrome via Scrapling — never skipped) →
   a hafo photo, which is a watermarked placeholder: last in the gallery and
   on `runs/<date>/needs-image.csv` (CLAUDE.md rules 7, 7a, 7b).
8. **Does it already exist?** — before writing anything:
   `scripts/find-product.sh "<product line name>"` (try the line name without
   lifestage/weight/flavor, then the brand name if that misses), and
   `scripts/show-product.sh <id>` on any hit. A hit is the **same product** only
   if brand, line, lifestage, breed size, food form, diet and health claims all
   match and it differs only in **pack weight, flavor or texture** (food) or
   **size, colour, dose band** (accessories, grooming, antiparasitics) — then
   this row is a new variant of it. Anything else is a new product.
   **Search for the LINE, not the row's name**: "Barbecue Ribs", not "Barbecue
   Ribs with Duck". A live single-variant product whose Name still carries the
   axis ("Barbecue Ribs with Chicken", "Flash USB Light Collar, nylon, M–L …,
   red") IS the line product: add the row to it and rename it to the line name
   with `scripts/rename-product.sh` (label + attributes carry the axis from
   then on). For Trixie the strongest key is the **page**: a live product whose
   variant sits on the same trixie.de page takes the row (`plan-trixie.py`
   does this with `existing_id`). 55 duplicates made by ignoring this were
   folded away on 2026-09-16.
9. **Write via API** — one of two paths, both scripted (write the JSON to
   `.siruk-cache/` and pass the path):
   - **New product** → `scripts/create-product.sh <payload.json>`. Payload shape
     in CLAUDE.md / the script header: name, slug, `category_ids` (**every**
     leaf that fits — the category map and the multi-category table in
     `reference/product-rules.md`), `brand_id`, `attribute_family_id` (the
     phase-B product type), variants with sku / `price` (the sale **pack**
     price) / `cost_price` (CSV) / `measure_type` + `content` + `pack_count` /
     `initial_stock` (10) / images, and `attribute_values` from step 6
     (attribute code or id → [value ids]). Shape: `scripts/siruk_payload.py`.
     Both write scripts refuse a variant priced at or below cost and anything
     the product type refuses. It refuses if a similar product already exists
     (`FORCE=1` overrides), then POSTs and reads back.
   - **Existing product** → `scripts/add-variant.sh <id> <variant.json>` with
     ONE variant object (no `id`; it sets `is_default`, `sort_order` and the
     sale mode for you). It rebuilds the PUT body from a fresh GET and
     refuses to write if any existing variant would be lost, or if the new
     variant lacks an option the others have or duplicates one's options + size.
     ⚠️ Never hand-write a `PUT /products/<id>` body: PUT replaces the entire
     variants array, so an omitted variant is deleted (silently, 200; 422 if it
     was the default). If the product Name still carries a pack weight from when
     it was single-variant (e.g. "… 8kg"), fix Name/slug with
     `scripts/rename-product.sh`, and move the weight into the variant labels.

   Group rows into products using "Product vs variant" in
   `reference/data-tables.md` — **the shelf test**: variants are the same pack
   with a different option on it, so rows differing only by **pack weight,
   flavor or texture** merge into one product (one variant each). Rows differing
   by **lifestage, breed size, food form, diet or health claim → separate
   products** (a redesigned pack = a different product, as Chewy lists them).
   Each variant must differ in its **options + size** — set the type's option
   attributes (flavor, texture, colour…) on every variant, or the second one is
   unreachable on the storefront. Unclear → separate products + flag.
9b. **Translate** — every product gets Russian and Armenian (user rule
   2026-09-10). Write `.siruk-cache/tr-<id>-ru.json` and `-hy.json` in the
   shape `scripts/set-translation.py` documents: `name` (brand-less, like the
   English) and per-SKU `about_this_item` /
   `ingredient_information` / `feeding_instructions` — a faithful translation
   of the English you just wrote, no new claims. Keep the variant labels,
   units and numbers as in English ("12 x 85 g" stays). For the `hy` name
   prefer the wording hafo's Armenian `title` uses when the row was
   hafo-confirmed. Run `scripts/set-translation.py <id> ru <file>` then `hy`;
   both must print OK. A product added as a variant to an existing product
   needs the new variant's texts translated too (same script, same product id).
10. **Verify** — `scripts/show-product.sh <id>` (both write scripts already
   print this): confirm name, categories (**all** of them — a dual-species item
   must show both trees' leaves), that **every** variant (pre-existing +
   new) is present with the right price, size label, available stock and
   images, and that `attribute_values` are set as intended. For a
   multi-variant product also read what the shop builds:
   `curl -s https://demo-api.siruk.am/api/products/<id> | jq '.data.optionGroups'`
   — every variant reachable, no two "Size" rows.
   Record status, and say in the report whether the row was created as a new
   product or added as a variant to an existing one.
11. **Breathe, then next row** — `scripts/pace.sh product` between rows (the
   pause comes from `config.json → product.pause_seconds`; API calls and uploads
   are paced and retried by the scripts themselves — don't add your own sleeps,
   change `config.json` instead).

At the **end of the run**, sweep the images once: `scripts/verify-media.sh
<id> <id> …` for the products you touched (`--fix` to re-upload and relink
anything dead) and put the result in the report.

**Then run the sibling check over everything you created** (user rule
2026-09-16): `scripts/catalogue-snapshot.py --ids <created ids>`, then
`scripts/find-duplicate-products.py --refresh` → `plan-product-merge.py` for
Trixie accessories/toys, and a hand-written `runs/<date>/variant-groups.json`
→ `scripts/plan-variant-merge.py --run runs/<date>` for any food, treat or
pharmacy product whose Name carries a flavour, pack, dose band or colour that a
live sibling shares. Merge with `scripts/merge-products.py --run runs/<date>`:
it moves EVERY variant of the wrongly created product onto the right one
before deleting it. Finish with `scripts/backfill-variant-axes.py --apply`
(rule 9a) and `scripts/register-price-sync.py --run state/register` (rule 2c).

Fallback: if the API create fails validation in a way that can't be fixed from
the error message (`.siruk-cache/` keeps the exact payload sent — diff it), fall
back to the UI form for that product (`fill_form` per the CLAUDE.md field map)
and note it in the report.

## Report

Write `runs/<date>-report.md` and summarize it in the reply. Per product:

- CSV name → hafo match (code, price) → source page (brand-site url, or
  "fallback") → **created** (admin id) / **variant added** to existing product
  (admin id + variant label) / skipped (reason)
- price per variant: hafo price, CSV cost, and the wholesale==cost check — and
  where the price came from a fallback (confirmed zoovet match, with the url
  and how identity was confirmed; or the sibling rule)
- attributes set (label + evidence quote), fields left empty with reason
  (not stated / not applicable / flagged candidate below threshold)
- rich-text fields populated (about / ingredients / feeding)
- translations: ru / hy stored (OK from `set-translation.py`) or why not

End with the aggregated lists, and write the CSVs into `runs/<date>/`
(columns in `reference/pricing.md`): `no-hafo-price.csv`, `not-found.csv`, plus
`sibling-priced.csv` / `zoovet-priced.csv` for rows a fallback priced and
`needs-image.csv` / `needs-packshot.csv` for the picture worklists:

- **Flagged candidates** — picks that need a human yes/no (with evidence).
- **Wanted but missing** — attribute values (or whole attributes) the text
  asked for that aren't in the menu, grouped and counted across products, with
  evidence quotes — phrased as questions for the user ("add value X to
  attribute Y?").
- Brands created during the run (name → id, logo source) and categories missing
  in admin (do not create categories).
