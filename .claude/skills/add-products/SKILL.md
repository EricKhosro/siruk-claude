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
- One product fully finished (created + verified) before starting the next.
- Do not invent brands/categories/attribute values that don't exist in the
  admin; flag in the report instead.
- Create via the **admin JSON API** (payloads in CLAUDE.md), not the UI form.
  The browser is only for brand sites and for reading the token once.

## Steps per run

1. **Auth** — get the Bearer token: navigate to the admin, run
   `JSON.parse(localStorage.access_token).token` via `evaluate_script`
   (log in first with CLAUDE.md credentials if needed). Save it to the session
   scratchpad. Verify with `GET /api/admin/account` via curl.
   Note: always send a real `User-Agent` (curl default is fine; the WAF 403s
   `Python-urllib`).
2. **Load the attribute menu** — `reference/attribute-values.json`
   (attribute code → label → value id). If the user edited attributes in the
   admin since it was written, refresh it first (command in CLAUDE.md →
   "Refreshing the attribute menu"). This menu is the ONLY source of pickable
   attribute values.
3. **Read the CSV** with the Read tool. For each row, do steps 4–9.
4. **Find on the brand's official site** — resolve the site from the row's
   `Brand / Vendor` using the brand→site map in CLAUDE.md. Use the site's own
   search or product-finder (or a scoped web search
   `site:<brand-domain> <product name>`) to reach the product page. Confirm the
   match: same brand, line, and pack size as the CSV name. If the exact size
   isn't on the site, use the closest product page for copy/images and keep the
   CSV size in the admin Name/Label. If the brand site is unreachable or has no
   product page, use the CLAUDE.md fallback (distributor catalog / general web
   search) and mark the row's source as "fallback".
5. **Extract** with a single `evaluate_script` returning JSON only:
   title, brand, size/pack, gallery image URLs (highest resolution),
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
   - **CSV wins** over the brand site on any conflict (e.g. size).
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
     before building the payload. Per-variant facts (size, packaging) may
     differ per variant; product-wide facts (lifestage, breed, diet) are set
     identically on every variant of the product.
7. **Images** — download each image URL to the scratchpad with `curl` (browser
   User-Agent), then upload via `POST /api/admin/medias` (multipart shape in
   CLAUDE.md). Collect the returned media ids.
8. **Create via API** — `POST /api/admin/products` with the payload shape in
   CLAUDE.md: name, slug, `category_ids` (from the CSV category map in
   CLAUDE.md), `brand_id`, variants with sku/price/cost_price/stock/images and
   `attribute_value_ids` from step 6. Multiple CSV rows for the same product in
   different sizes → one product, one variant per size (first = default).
9. **Verify** — `GET /api/admin/products/<id>`: confirm name, categories,
   variant price/stock, images, and that `attribute_value_ids` are set as
   intended. Record status.

Fallback: if the API create fails validation in a way that can't be fixed from
the error message, fall back to the UI form for that product (`fill_form` per
the CLAUDE.md field map) and note it in the report.

## Report

Write `runs/<date>-report.md` and summarize it in the reply. Per product:

- CSV name → source page (brand-site url, or "fallback") → created (admin id) /
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
- Brands/categories missing in admin (do not create them).
