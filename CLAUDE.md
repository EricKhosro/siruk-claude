# Siruk PetShop — product import automation

Turn a supplier CSV into products in the Siruk admin. Per row: identify the
product (hafo.am, by article code) → get its **sale price from hafo** → get
name / images / description from the **brand's official site** → write it via
the admin JSON API. Read this file fully; open a `reference/` doc only when the
step you are on needs it.

## Hard rules — read before every run

1. **The CSV price is our COST, never the sale price.** Whatever price column
   the CSV carries (`Buy Price`, `Unit H/S Cost`, `R/Price`, a bare `Price`)
   goes to `cost_price`. The **sale price comes from hafo.am** for that exact
   article code — and, only where hafo has none, from the two named fallbacks
   in rules 2b and 2a. Nowhere else, and never from arithmetic.
2. **Never invent, derive or estimate a sale price.** No markup formula, no
   rounding of cost, no "similar product" price, no price from a brand site,
   no vendor `R/Price`. A row hafo cannot price is **not imported**: it goes to
   `runs/<date>/no-hafo-price.csv` with `Sale Price (AMD)` empty for the user.
   Three exceptions only: a price the user fills in there, a **confirmed
   zoovet.am price** (rule 2b) and the **sibling-price fallback** (rule 2a).
2a. **Sibling-price fallback** (user rule 2026-09-10). When hafo has no price
   for a code (not listed, or listed without our row) **and** the row is a
   variant of a product that already has a hafo-priced variant (from an
   earlier run or this one) **and** both rows have the **same CSV buy price**,
   the unpriced variant takes that sibling's hafo sale price. "Same product"
   = the shelf test passes (only flavour, texture or pack differ); pack weight
   need not match — equal cost is the test. If same-cost siblings carry
   **different** hafo prices, do not apply: the row goes to
   `no-hafo-price.csv` with `Why no price` = `sibling prices differ`, naming
   the candidates. Log every fallback in `runs/<date>/sibling-priced.csv`
   and in the report (`reference/pricing.md` has the columns).
2b. **zoovet.am is the second price source** (user rule 2026-09-11). When hafo
   has no price for the code, a zoovet.am price may be used — but only for a
   row whose identity there is **confirmed by hand** (zoovet has no article
   code; its `ME-…` number collides with brand article numbers), and only if it
   beats our cost. Order: hafo row → confirmed zoovet → sibling fallback →
   `no-hafo-price.csv`. Log each one in `runs/<date>/zoovet-priced.csv`. Where
   hafo does price the row hafo wins, and a large zoovet gap is a line in the
   report, not a change. `reference/zoovet.md` has the confirmation tests.
3. **Each variant gets its own hafo price.** A hafo listing spans every size of
   a product; the row for *our* article code is in
   `product_additional_information[]`, and the top-level `price` is only the
   cheapest row. `scripts/hafo-lookup.py` returns `price_source: "variant"` or
   `"UNRESOLVED"` (no price). Only `"variant"` may be written. Create only the
   priced variants; the unpriced ones go to the CSV individually.
4. **Re-check prices against hafo** with `scripts/check-hafo-prices.py`
   after any import and whenever asked; `--apply` only fixes unflagged rows.
5. **Sale price must beat cost.** hafo's per-row `wholesale_price` should equal
   our cost; a sale price at or below cost means the wrong hafo row — stop and
   check by hand. `create-product.sh` / `add-variant.sh` refuse such a variant.
6. **Identity only from the article code.** A hafo name-search hit is a
   candidate (`confirmed: false`), never a match. The CSV `Brand` column is
   derived and can be wrong for rows with no code suffix — membership in the
   brand's own catalogue decides. Unresolvable rows → `runs/<date>/not-found.csv`.
7. **Media, English name and description come from the brand's official site**
   (`reference/brand-sites.md`) — **including its other country domains**: a
   national site is the same official source and keeps its own copies, so an
   article the main site dropped is often still there (Trixie: `trixie.es`,
   `scripts/trixie-es.py`, wired into `scripts/trixie-image.sh`). hafo is
   Armenian-only and for identity + price.
   **Upload the whole gallery, not one picture** — every image the product page
   shows for that article, each verified readable, all of them in
   `variant.images`, ordered packshot, pack, lifestyle, group shot, drawing.
   **The first image is the feature image and must be a clean product shot**:
   the product alone (or in its own pack) on a plain background — no animal,
   no hand, no scene, no group of sibling products. Look at it before writing.
   If the source leads with a lifestyle or group shot, move the packshot
   first; a lifestyle/group shot may lead **only when the product has no
   clean shot at all** (typically a single-image product) — then log the
   variant in `runs/<date>/needs-packshot.csv`. Never crop or edit an image to
   make one. `scripts/feature-image.py` audits the whole catalogue
   (`--apply` reorders, `--sheet` renders the feature images for a visual
   check). Never attach an image from a fuzzy name match — only sources keyed
   to the article number, or a filename naming the same line, flavour and pack.
7a. **A hafo.am image is a placeholder, never a finished one.** Every photo
   hafo serves is stamped with a repeating "Hafo" watermark, so it must not
   survive to production. It is still attached when the brand site has no
   picture for the article, because the PM uses it to recognise the product and
   replace it by hand (PM decision, 2026-09-11, reversing the "drop them"
   instruction earlier that day). Rules for a hafo picture: it goes **last** in
   the gallery, so a brand shot always leads; every variant that carries one is
   listed in `runs/<date>/needs-image.csv` as the replacement worklist; and the
   run report says plainly that those galleries are watermarked placeholders.
   Only take a hafo file whose name carries **our** article (a listing spans
   sizes), or the listing photo when the listing has a single row.
7b. **zoovet.am comes before a hafo placeholder** (user rule 2026-09-11).
   zoovet.am serves the brands' own packshots **unwatermarked** (the original
   behind the thumbnail: drop `cache/` and the `-800x800` suffix), so a
   confirmed zoovet photo is a finished image — it leads the gallery like any
   brand shot and the variant does **not** go on `needs-image.csv`. But zoovet
   carries no article code and its internal `ME-…` number collides with brand
   articles, so every hit is a candidate until confirmed by hand: the article
   read off the pack in the full-size photo, or brand + line + flavour + pack
   all matching with the artwork matching the brand site. Image order:
   brand site (incl. country TLDs) → confirmed zoovet → hafo placeholder.
   `scripts/zoovet-lookup.py`, `reference/zoovet.md`.
7c. **Two approved fallbacks sit between the brand site and hafo** (PM, 2026-09-11;
   the chain lives in `config.json` → `images.sources`, the evaluation of all 21
   candidates in `runs/2026-09-11/image-source-candidates.md`). For Trixie:
   **trixie.shop**, Trixie's own Shopify store, which keeps Trixie's file names
   (`scripts/trixie-shop-index.py`); then **trixiecz.cz**, the official Czech
   distributor, which still lists discontinued articles and prints `Kód` + EAN on
   every page (`scripts/trixiecz-index.py --sweep`; its sitemap omits the
   clearance stock, the id sweep is what reaches it). Both are keyed to the
   article, never to a name. trixiecz photos are 570 px, so they never outrank a
   brand-CDN shot. Anything the chain still misses: a Trixie EAN is computable
   (`4011905` + article padded to 5 + check digit) — search it and accept only a
   page that prints the same EAN back.
8. **Never fabricate specs.** Empty field beats a guess. Attribute values only
   from the closed menu `reference/attribute-values.json`, with an evidence
   quote. Don't create attributes, values or categories without an explicit
   ask. One value per attribute per variant (the API rejects arrays). The
   product-type skill says which attributes a row gets — toy `material` is the
   one value set you may extend, deduplicating synonyms.
9. **Search before create.** `scripts/find-product.sh` first; an existing
   product gets the row as a variant (`scripts/add-variant.sh`), never a second
   product. Variant axes: pack weight, flavour, texture. Anything else splits
   products (`reference/product-rules.md`).
10. **Write only through `scripts/`.** Never hand-write a `PUT /products` body
   (PUT replaces the whole variants array). Never trust a media id you have not
   verified readable.
11. **Brand sites are read-only.** No cart, no accounts, no forms. Don't
    `take_snapshot` product pages; extract with `evaluate_script`.
12. **Weights are metric (kg/g), never lbs.** Name never contains the brand;
    slug does. Don't turn a volume (litres) into a weight.
13. **Everything that can be translated is written in three languages** —
    products, categories, brands, attributes. The API takes one locale per
    request, so: create in `en`, then `ru` and `hy` (`scripts/set-translation.py`
    for products, `translate-categories.py`, `translate-brands.py`,
    `translate-attributes.py` for attribute names, value labels and family
    names from `reference/translations-attributes.json`;
    `verify-translations.py` audits the whole server). Attributes, values
    and families are per-locale since the 2026-09-10 backend change; a new
    value needs its ru/hy pair added to that JSON, then re-run the script.
    Variant labels are still single-language — keep them English, never
    "translate" them in place (a `ru` write REPLACES the English).
    **Report translation status only from `scripts/verify-translations.py`
    / `translate-attributes.py --verify-only` output, never from what was
    sent** — and say plainly which resources the backend cannot store per
    locale, so nobody expects a Russian tab to differ where it cannot.

## Environments
- Admin (demo): `https://demo-api.siruk.am/admin/login` —
  `dev@conceptstudio.club` / `C6iA7HLmHU00v/0`. Production needs a dedicated
  catalog-only service account (not yet requested).
- API: `https://demo-api.siruk.am/api/admin/*`, `Authorization: Bearer <JWT>`
  (cookies alone fail). Token in `.siruk-token` (gitignored, ~1 year). Check
  with `scripts/api.sh GET /account`; re-capture per `scripts/README.md` on 401.
- Pacing / retries / image verification: `config.json` (read on every call).
- Working files: `.siruk-cache/` (gitignored). Run outputs: `runs/<date>/`.

## The pipeline (one row at a time, verified before the next)

1. `scripts/api.sh GET /account` → 200. `scripts/ids.sh` for live ids.
2. Load `reference/attribute-values.json` (refresh with
   `scripts/refresh-attributes.sh` if the user edited attributes).
3. **hafo** — `scripts/hafo-lookup.py --code <code> --name "<name>"`
   (`reference/hafo.md`). Need `confirmed: true` **and** `price_source:
   "variant"`. Confirmed but no price → try zoovet (rule 2b,
   `scripts/zoovet-lookup.py`), then the sibling fallback, then
   `no-hafo-price.csv`. Not confirmed → `not-found.csv`.
4. **Brand site** — resolve from the brand hafo returned
   (`reference/brand-sites.md`), find the product page, extract title, images,
   description, composition, feeding guide, spec text. Nothing there? the
   brand's other country domains, then zoovet (`reference/zoovet.md`). New
   brand → research the official site, add it to the table, `/create-brand`.
5. **Attributes** — closed menu, evidence quote per pick, our definitions
   (`reference/data-tables.md`) beat the brand's wording.
6. **Group / exists?** — `reference/product-rules.md` for product-vs-variant,
   Name/slug/label, categories. `scripts/find-product.sh` before writing.
7. **Write** — `scripts/upload-media.sh` per image (all gallery images;
   Trixie: `scripts/trixie-image.sh <art>` lists them all, .de plus the .es
   shop), then
   `scripts/create-product.sh` or `scripts/add-variant.sh`. Payload shapes and
   pricing type in `reference/admin-api.md` (`fixed` = per unit with `price`;
   `per_kg` = dry kibble by weight with `price_per_kg` + `weight`, rate =
   hafo price ÷ pack weight).
8. **Translate** — write `.siruk-cache/tr-<id>-ru.json` and `-hy.json`
   (name + per-SKU texts; the hafo Armenian `title` is a good source for
   the `hy` name) and run `scripts/set-translation.py` for each.
9. **Verify** — `scripts/show-product.sh <id>`; `scripts/verify-media.sh` at
   the end of the run. `scripts/pace.sh product` between rows.
10. **Report** — `runs/<date>/report.md` + the two CSVs (`reference/pricing.md`
   has their columns). List "wanted but missing" vocabulary as questions.

## Reference docs

| Doc | When |
|---|---|
| `reference/pricing.md` | anything touching `price`, `cost_price`, `price_per_kg` — the full policy, cross-checks and the two output CSVs |
| `reference/hafo.md` | the hafo API, SKU formats per brand, what the lookup script returns |
| `reference/zoovet.md` | zoovet.am — unwatermarked photos, a second price, the `ME-…` code trap and how to confirm a candidate |
| `reference/brand-sites.md` | brand → official site, per-site extraction notes, image sourcing (Trixie CDN, Schesir JSON, Monge caveats) |
| `reference/admin-api.md` | endpoints, payload shapes, pricing types, media rules, known API quirks, **live ids** (brands, categories, families, attributes) |
| `reference/product-rules.md` | Name / slug / label rules, product vs variant, category map, admin form field map, storefront behaviour |
| `reference/csv-formats.md` | the input CSV shapes (starter list, vendor sheets, invoice extract) and how to decode vendor strings |
| `reference/data-tables.md` | our attribute definitions (lifestage etc.), brand wording → our values, pricing-type table |
| `reference/attribute-redesign.md` | the attribute/family spec |
| `reference/script-guide.md` | **which script, when** — by job: session start, per-row pipeline, end-of-run checks, translations, media, brands, prices, one-offs |
| `scripts/README.md` | every script, `config.json`, debugging |
| `PLAN.md`, `INVESTIGATION.md` | roadmap; why Chewy was dropped (Kasada anti-bot) |

## Skills

`/add-products <csv>` imports; `/create-brand <name>` adds a brand with a
verified official logo; `/manage-attributes` edits the vocabulary (never deletes
without an explicit ask). Big attribute batches → the `attribute-manager` agent.
**One spec skill per product type** — `toys`, `dry-food`, `wet-food`, `treats`,
`supplements`, `grooming`, `accessories` (`.claude/skills/<type>/SKILL.md`) —
says which categories, family, attributes, values and variant axes that type
gets. `/add-products` reads the row's type skill before filling attributes;
`/manage-attributes` builds vocabulary from it. `toys` is complete (Chewy
layout); the others are templates for the user to fill.

## Quick ids (demo, 2026-09-10 — `scripts/ids.sh` is the truth)

Categories: Dog 1 → Food 2 → {Dry 3, Wet 4, Health Condition 5}, Treat 6 →
{7}, Toys 15 → {17–22}, Grooming 27 → {28–33}, Health & Pharmacy 41 → {42–49},
**Supplies 68 → {69 Collars/Leashes/Harnesses, 70 Bowls & Feeders, 71 Beds,
72 Clothing & Accessories, 73 Carriers & Travel, 74 Training & Behavior},
Cleaning & Potty 75 → {76 Pee Pads & Diapers, 77 Poop Bags & Scoopers,
78 Cleaners & Stain Removers}** · Cat 8 → Food 9 → {Dry 10, Wet 11}, Treat 14,
Toys 16 → {23–26}, Grooming 34 → {35–40}, Health & Pharmacy 50 → {51–58},
Litter 59 → {60–65}, Supplies 66 → {67 Litter Boxes & Accessories,
**79 Collars/Leashes/Harnesses**}, **Trees, Condos & Scratchers 80 →
{81 Scratchers & Scratching Posts}** · Accessories 13 is **not** a product
category — never file a row there. Products go in a **leaf**, never a parent.
All categories carry ru/hy names (68–81 added 2026-09-11 from the Chewy menu,
`scripts/create-category.py`).
Full tree with names in `reference/admin-api.md`.
Brands: 1 Acana, 2 Belcando, 3 Brit, 4 Canvit, 5 Monge, 6 Orijen, 7 Royal
Canin, 8 Trixie, 9 Farmina, 10 Schesir, 11 Leonardo, 12 Stuzzy, 13 Bewi Dog,
14 Bewi Cat, 15 Dogland, 16 Ok-Lock, 17 Club 4 Paws, 18 Gemon, 19 Simba.
Families: 1 Dry Food, 2 Wet Food, 3 Treats, 4 Supplements, 5 Toys. The
attribute vocabulary replicates Chewy's filters (`reference/chewy-attributes.json`;
`toy-size` 16 is the hidden toy variant axis). Type skills say which apply.
Any id in a note written before 2026-08-12 predates the rebuild and is wrong.
