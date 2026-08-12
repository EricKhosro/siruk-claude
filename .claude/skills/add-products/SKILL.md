---
name: add-products
description: Import products from a CSV into the Siruk admin panel, sourcing data from each product's brand official website and filling variant attributes from the page text. Use when the user provides a CSV of product names to add, or asks to add/import products to the site. Drives chrome-devtools MCP for the brand sites; creates products via the admin JSON API.
argument-hint: [path to CSV file]
---

Import the products listed in the CSV into the Siruk admin panel, one at a time.
CSV path (or inline product names):

$ARGUMENTS

Read `CLAUDE.md` first — it has credentials, the brand→official-site map, the
API payload shapes, reference data ids, and token-efficiency rules. Key
constraints:

- Source data from the **brand's official website** (per the brand map in
  CLAUDE.md), NOT Chewy. Sites are **read-only** (no cart, no account, no forms).
- Never `take_snapshot` on source product pages — extract with `evaluate_script`.
- One product fully finished (written + verified) before starting the next.
- **Never create a product that already exists** — search first; if it's there,
  the row goes on as a new variant (step 8/9).
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
3. **Read the CSV** with the Read tool. For each row, do steps 4–10. If the
   row's brand isn't in the admin brand list, run the `/create-brand` skill for
   it first and use the brand id it returns (creating one brand once, not per
   row); note the creation in the report.
4. **Find on the brand's official site** — resolve the site from the row's
   `Brand / Vendor` using the brand→site map in CLAUDE.md. Use the site's own
   search or product-finder (or a scoped web search
   `site:<brand-domain> <product name>`) to reach the product page. Confirm the
   match: same brand, line, and pack weight as the CSV name. If the exact weight
   isn't on the site, use the closest product page for copy/images and keep the
   CSV pack weight in the admin Name/Label. If the brand site is unreachable or has no
   product page, use the CLAUDE.md fallback (distributor catalog / general web
   search) and mark the row's source as "fallback".
5. **Extract** with a single `evaluate_script` returning JSON only:
   title, brand, pack weight/format, gallery image URLs (highest resolution),
   description/benefits, composition/ingredients, feeding guide, and the raw
   text of any spec/attribute sections. Ignore any price on the site (price
   comes from the CSV). Missing sections → `null`, don't fail. Brand sites vary
   a lot in structure — target the specific DOM of that page rather than
   assuming a fixed layout.
6. **Fill attributes** from the extracted text — for each attribute in the
   menu, pick a value under these hard rules:
   - **Closed menu:** only labels present in `reference/attribute-values.json`,
     or `null`. Never invent a value, never submit a label not in the menu.
   - **Evidence required:** every non-null pick needs a supporting quote from
     the CSV row or the page text. No quote → `null`.
   - **CSV wins** over the brand site on any conflict (e.g. pack weight).
   - **Weights are metric, kilogram-based — never lbs/oz.** Convert a US source
     (`lb x 0.4536 = kg`), preferring the brand's own metric pack size.
   - **Skip `product-weight` on weight-priced (`per_kg`) variants** — the admin
     derives it from Pack weight (table 4 of `reference/data-tables.md`). Keep it
     only if the product's variants would otherwise have identical attributes.
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
     before building the payload. Per-variant facts (**lifestage**, `product-weight`,
     flavor, packaging) are set per variant and sourced from that variant's own
     brand page; product-wide facts (breed size, food form, diet, health
     feature) are identical on every variant — if they aren't, it's a separate
     product (see `reference/data-tables.md`).
7. **Images** — `scripts/upload-media.sh <image-url>` per image (it downloads
   with a browser User-Agent and prints the media id). Collect the ids for the
   variant's `images` array.
8. **Does it already exist?** — before writing anything:
   `scripts/find-product.sh "<product line name>"` (try the line name without
   lifestage/weight/flavor, then the brand name if that misses), and
   `scripts/show-product.sh <id>` on any hit. A hit is the **same product** only
   if brand, line, lifestage, breed size, food form, diet and health claims all
   match and it differs only in **pack weight, flavor or texture** — then this row
   is a new variant of it. Anything else is a new product.
9. **Write via API** — one of two paths, both scripted (write the JSON to
   `.siruk-cache/` and pass the path):
   - **New product** → `scripts/create-product.sh <payload.json>`. Payload shape
     in CLAUDE.md / the script header: name, slug, `category_ids` (from the CSV
     category map in CLAUDE.md), `brand_id`, `attribute_family_id`, variants with
     sku/cost_price/stock/images, the right **pricing shape** (table 4 of
     `reference/data-tables.md`: dry kibble → `pricing_type:"per_kg"` with
     `price_per_kg` = CSV price ÷ pack weight and `weight`; units → `"fixed"`
     with `price`) and `attribute_value_ids` from step 6. It
     validates the required fields, refuses if a similar product already exists
     (`FORCE=1` overrides), then POSTs and reads back.
   - **Existing product** → `scripts/add-variant.sh <id> <variant.json>` with
     ONE variant object (no `id`; it sets `is_default: false`, `sort_order`, and
     `pricing_type` for you). It rebuilds the PUT body from a fresh GET and
     refuses to write if any existing variant would be lost.
     ⚠️ Never hand-write a `PUT /products/<id>` body: PUT replaces the entire
     variants array, so an omitted variant is deleted (silently, 200; 422 if it
     was the default). If the product Name still carries a pack weight from when
     it was single-variant (e.g. "… 8kg"), fix Name/slug in a separate
     `scripts/api.sh PUT` built from `show-product.sh <id> --json`, and move the
     weight into the variant labels.

   Group rows into products using "Product vs variant" in
   `reference/data-tables.md` — **the shelf test**: variants are the same pack
   with a different option on it, so rows differing only by **pack weight,
   flavor or texture** merge into one product (one variant each). Rows differing
   by **lifestage, breed size, food form, diet or health claim → separate
   products** (a redesigned pack = a different product, as Chewy lists them).
   Each variant must carry a **unique attribute combination** — set
   `flavor`/`texture` on flavor/texture variants or the API rejects the second
   one. Unclear → separate products + flag.
10. **Verify** — `scripts/show-product.sh <id>` (both write scripts already
   print this): confirm name, categories, that **every** variant (pre-existing +
   new) is present with the right price/stock/images, and that
   `attribute_value_ids` are set as intended.
   Record status, and say in the report whether the row was created as a new
   product or added as a variant to an existing one.

Fallback: if the API create fails validation in a way that can't be fixed from
the error message (`.siruk-cache/` keeps the exact payload sent — diff it), fall
back to the UI form for that product (`fill_form` per the CLAUDE.md field map)
and note it in the report.

## Report

Write `runs/<date>-report.md` and summarize it in the reply. Per product:

- CSV name → source page (brand-site url, or "fallback") → **created** (admin
  id) / **variant added** to existing product (admin id + variant label) /
  skipped (reason)
- attributes set (label + evidence quote), fields left empty with reason
  (not stated / not applicable / flagged candidate below threshold)
- rich-text fields populated (about / ingredients / feeding)

End with the aggregated lists:

- **Flagged candidates** — picks that need a human yes/no (with evidence).
- **Wanted but missing** — attribute values (or whole attributes) the text
  asked for that aren't in the menu, grouped and counted across products, with
  evidence quotes — phrased as questions for the user ("add value X to
  attribute Y?").
- Brands created during the run (name → id, logo source) and categories missing
  in admin (do not create categories).
