---
name: manage-attributes
description: Create or manage Siruk admin attributes, attribute values, and product types (the API's attribute families) via the admin JSON API. Use when the user asks to add/create attributes, values, or product types, rebuild the attribute system (e.g. from reference/attribute-redesign.md), or refresh the attribute menu file. Never deletes anything without an explicit ask.
argument-hint: [what to create: inline list, a file path, or "from redesign doc"]
---

Create/manage attributes, attribute values, and product types (the admin's
name; the API/DB still say `attribute-families` / `attribute_family_id`) in
the Siruk admin. Input (inline list, file path, or "from redesign doc" =
`reference/attribute-redesign.md`):

$ARGUMENTS

Read `CLAUDE.md` first (credentials; rules 8, 8a–8c), then
`reference/admin-api.md` — "Product types", "Variants and attributes",
"Brands / categories / attributes" — and the live types in
`reference/product-types.json` (`scripts/product-types.py --dump` refreshes
it). For large batches (>15 creations), and for the per-import product-type
design of rule 8b, delegate to the `attribute-manager` agent instead of doing
it inline — pass it the exact list (or the batch's gathered product data) and
these rules.

## API (all verified unless marked)

Base `https://demo-api.siruk.am/api/admin` · header
`Authorization: Bearer <JWT>` · always send a real User-Agent (WAF 403s
`Python-urllib`; curl default is fine).

**Use `scripts/api.sh METHOD PATH [payload.json|-]` for every call** (it handles
auth, status codes and error dumps) and `scripts/ids.sh` to see what exists —
see `scripts/README.md`. The paths below are what to pass it.

- Token: `.siruk-token` in the repo root (gitignored, survives reboots). Verify
  with `scripts/api.sh GET /account`; only if that 401s, re-capture from the
  logged-in SPA via chrome-devtools MCP
  (`JSON.parse(localStorage.access_token).token`) and rewrite that file.
- List: `GET /attributes?forProducts=true` → `{data:[{id,code,name,values:[{id,label,value}]}]}`
- List product types: `GET /attribute-families?forProducts=true` →
  `{data:[{id,name,code,defaultSaleMode,measureType,unitPriceBasis,attributes:[{id,code,role,isRequired,isFilterable,showOnProductCard,position}]}]}`
  (single `GET /attribute-families/<id>` adds `guards`)
- Create attribute: `POST /attributes` `{code, name, input_type
  (select|multiselect|boolean|number|text), unit?, is_filterable,
  show_on_product_card}` → `{data:{id,...}}`. The two flags are only the
  defaults for a new product-type row; the storefront reads the per-type flags.
  `is_variant` is gone — whether an attribute is a selector is the type's
  `role`.
- Create value: `POST /attribute-values` `{attribute_id, value, label,
  sort_order?}` → `{data:{id,...}}`. `value` is the **code**: a slug
  `^[a-z0-9]+(?:-[a-z0-9]+)*$`, unique within the attribute (a duplicate is a
  422 now, not a 500). `sort_order` sets the tile order.
- Rename attribute: `PUT /attributes/<id>` `{code, name}` (PATCH equivalent) →
  renames in place; value ids/labels and product-type membership survive, and each
  value's derived `name` re-derives from the new code. Verified 2026-08-12
  (history: that rename, `size` → `product-weight`, is moot — `product-weight`
  was retired on 2026-09-29).
- Create / edit a product type (catalog model, 2026-09-29): `POST` / `PUT
  /attribute-families[/<id>]` `{name, code, default_sale_mode (pack|weight),
  measure_type (mass|volume|count|null), unit_price_basis, low_stock_threshold,
  low_stock_grams, attributes:[{id, role: option|attribute, is_required,
  is_filterable, show_on_product_card}]}`. **`attributes` replaces the whole
  set** (array order = position) — GET first and re-send every row. The old
  `attribute_ids` key is **ignored** now (it was the only shape that worked
  before 2026-09-29; don't use it). The API refuses removing an attribute
  still in use, promoting to `option` while a variant holds two values,
  requiring an attribute some variant lacks, a demotion that makes variants
  identical, and a measure change while variants hold other-measure sizes —
  read `guards` first. Read back `attributes` to confirm, then
  `scripts/product-types.py --dump`.
- Delete (only on explicit user ask, see Safety): `DELETE /attributes/<id>`
  → 204 (verified 2026-09-10; variants referencing it silently lose that key,
  so check multi-variant products for now-identical combinations first). Try
  `DELETE /attribute-values/<id>` (refused while a variant uses the value),
  `DELETE /attribute-families/<id>` (other admin resources use this pattern;
  products verified → 204).

## Workflow

1. **Parse the request** into a plan: attributes to create (code, name,
   input_type), values per attribute (label), product types (name, code,
   measure_type, default_sale_mode, and per attribute in order: role,
   is_required, is_filterable, show_on_product_card).
2. **Fetch existing** attributes+values+product types FIRST. Dedupe
   case-insensitively (and ignoring `-`/space differences: "Grain Free" ==
   "Grain-Free"). Existing → skip, report as "already present". Near-match →
   do NOT create; flag for the user ("'Joint Care' vs existing 'Hip & Joint
   Support' — same thing?").
3. **Enforce naming conventions** (from `reference/attribute-redesign.md`):
   kebab-case singular codes; Title Case labels; one spelling per concept;
   measurements in labels as `400 g` / `1.5 kg` / `0.45 l/ø 19 cm` (dot
   decimal, space, lowercase unit).
   Auto-fix casing/format silently; flag anything ambiguous instead of
   guessing.
   **Never name an attribute after a brand's word for it** — brands reuse words
   for different concepts (Royal Canin "Size" = breed size, not pack weight).
   **Pack size is never an attribute** (CLAUDE.md 8a): it is the variant's
   `measure_type` + `content` + `pack_count`; `product-weight` was retired on
   2026-09-29 — do not (re)create it or anything like it. A **physical** size
   (bowl, collar, toy) is an option attribute (`size` 28, `toy-size` 16).
   Full brand-wording → our-name mapping: table 3 of
   `reference/data-tables.md`.
4. **Create** in order: attributes → values → product types (types reference
   attribute ids). Verify each response has an id. Roles: `option` for what
   the customer picks between variants of one product (flavour, colour, toy
   size, dose band), `attribute` for specs and filters; `is_filterable` on the
   type is what puts an attribute in the category sidebar.
5. **Refresh the snapshots**: `scripts/refresh-attributes.sh` (regenerates
   `reference/attribute-values.json` from a fresh
   `GET /attributes?forProducts=true`, atomic write) and, after any product-type
   change, `scripts/product-types.py --dump` (→ `reference/product-types.json`).
6. **Report**: table of created (name → id), skipped-as-duplicate,
   flagged near-matches/questions, and any endpoint discoveries appended to
   `reference/admin-api.md`.

## Translations

Attribute names, value labels and product-type names are **per-locale** since
the 2026-09-10 backend change (`reference/admin-api.md` → "Translations").
Create them in English, put the ru/hy wording for every new value into
`reference/translations-attributes.json`, then run
`scripts/translate-attribute-values.py <new ids>` (a few values) or
`scripts/translate-attributes.py` (everything; it probes a throwaway attribute
first and refuses on a regression). Report translation status only from
`translate-attributes.py --verify-only` output (CLAUDE.md 13).

## Safety

- **Never delete anything unless the user explicitly asked for deletion in
  this conversation.** Bulk wipes: list exactly what will be deleted and get a
  confirmation first. Check `GET /products` for variants referencing the
  value ids about to be deleted and warn if any.
- Never modify values the user created by hand (rename/merge) without asking.
- Demo junk values (`xlllllrr`, `flavor test`, …) are known — do not touch
  unless asked; never pick them for anything.
- This skill writes to the demo admin. If `SIRUK_API` points anywhere else,
  stop and confirm with the user first.
