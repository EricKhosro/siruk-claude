# Siruk data tables — our site's definitions

Lookup tables that define **how Siruk understands** attribute concepts, for use
when reading brand sites. Brand sites use their own age bands and wording; these
tables are authoritative for our catalog. When a brand's definition disagrees
with ours, **ours wins** — translate, don't copy.

Values picked from these tables must still exist in the attribute menu
(`reference/attribute-values.json`) — see the closed-menu rule in the
`add-products` skill.

Tables in this file:
1. [Lifestage](#1-lifestage)
2. [Product vs variant](#2-product-vs-variant)
3. [Our attribute names vs brand wording](#3-our-attribute-names-vs-brand-wording)
4. [Pricing type — sold by weight vs sold by count](#4-pricing-type--sold-by-weight-vs-sold-by-count)

---

## 1. Lifestage

Attribute `lifestage` — menu values: `Puppy · Kitten · Adult · Senior ·
All Lifestages` (see `reference/attribute-redesign.md`).

### Cats

| Stage | Age |
|---|---|
| Kitten | 0 – 1 year |
| Adult | 1 – 10 years |
| Senior | 10+ years |

### Dogs

| Stage | Age |
|---|---|
| Puppy | 0 – 1 year |
| Adult | 1 – 8 years |
| Senior | 8+ years |

Note the species difference: **senior starts at 10 for cats but 8 for dogs.**

### How to map a brand page to these stages

1. **A stated age range beats brand wording.** If the page gives an age
   ("for cats 7+ years", "12 months to 6 years"), place that range on our bands
   above and use the stage it falls in — even if the brand calls it something
   else. So a cat food labelled "Senior 7+" is **Adult** for us (our cat senior
   starts at 10); a dog food labelled "Mature 7+" is likewise **Adult**.
2. **Range straddles a boundary** → take the stage covering most of the range
   ("6 months – 2 years" → mostly under 1 → Puppy/Kitten). If it's roughly even,
   leave `null` and flag it as a candidate with the quote.
3. **No age given** → map the brand's word:
   | Brand wording | Our stage |
   |---|---|
   | Puppy, Junior, Growth, Starter, Mother & Babycat, weaning, pregnant/nursing | Puppy (dog) / Kitten (cat) |
   | Adult, Maintenance | Adult |
   | Senior, Mature, Ageing, Aging, Older | **Check the age first** — only Senior if the page states 8+ (dog) / 10+ (cat), otherwise Adult; no age at all → Senior |
   | All life stages, Complete for all ages, Family | All Lifestages |
4. **Range spanning our whole scale** ("from 2 months to old age") → All
   Lifestages.
5. **Two stages named, no single value** (e.g. "adult and senior dogs") → this
   attribute holds one value per variant; pick the one the product is primarily
   marketed for, otherwise `null` + flag. Do **not** use All Lifestages as a
   catch-all for "more than one stage" — it means the brand markets it for every
   age.
6. **Veterinary / therapeutic diets** often state no lifestage — leave `null`,
   don't infer one from the condition.
7. Confidence gate, evidence quotes, and "wanted but missing" reporting work
   exactly as in the `add-products` skill; a mapping done via this table counts
   as direct evidence (quote the age or wording you mapped from).

---

## 2. Product vs variant

**One product = one recipe sold under one name. Variants = the buying choices
inside that product** (the options a shopper picks between on one page).

### The test — does it look like the same bag on the shelf?

**The shelf test (the rule that decides everything below):** variants are the
options a shopper picks between *for the same pack of food* — the packaging
artwork is the same design and colour, only the size differs. **If the packaging
art changes, it is a different product.** Chewy works exactly this way: "Royal
Canin Size Health Nutrition Small Puppy" and "… Small Adult" are two products,
not two variants of one.

So in practice the variant axes are **pack size, flavor and texture** — the
options printed on a band of an otherwise identical pack. Everything that
redesigns the pack (lifestage, breed size, food form, diet, health claim) splits
products.

⚠️ **Every variant needs a *different* attribute combination.** The API rejects
two variants whose `attribute_value_ids` are identical ("This attribute
combination is already used in variant N"), so a flavor or texture variant only
works if `flavor`/`texture` is actually set on it. If the distinguishing value is
missing from the menu, either map the brand's wording onto an existing value
(our definitions win — e.g. Royal Canin "thin slices in gravy" → **Chunks in
Gravy**) or keep them as separate products and report the missing value.

Variants of the same product must be **identical on every product-wide fact**.
If any of these differ, it is a **separate product**:

| Must match across variants | Why |
|---|---|
| Brand | different brand = different product, always |
| Categories | drives navigation |
| `lifestage` | **never a variant axis** — the pack art and colour change with the animal on the bag (user rule, 2026-08-12). Puppy + Adult of the same line = two products |
| `breed-size` | a line is sold *for a breed size*; different breed size = different product (user rule, 2026-08-12) |
| Named breed (German Shepherd, Persian, …) | a breed-specific line is its own product; the breed goes in the Name, not in an attribute |
| `food-form` (Dry / Wet / Tablets / …) | a dry and a wet product are not one product |
| `special-diet`, `health-feature` | different formulation claims |

May differ per variant — this is what variants are *for*:

| Free to differ | Notes |
|---|---|
| `product-weight` (pack weight) | **variant axis**: same recipe, same art, different bag — 4 kg / 10 kg / 15 kg |
| `flavor` | **variant axis** (user rule, 2026-08-12): Tuna / Chicken / Beef of one line is one product, one variant each |
| `texture` | **variant axis** (user rule, 2026-08-12): gravy / jelly / loaf / mousse of the same recipe — same bag design, option named on a band |
| Pack count of the same unit | 1 × 85 g vs 12 × 85 g of the same recipe |
| Price, cost price, SKU, stock | per variant by design |
| Images | variant carries its own gallery |
| `about_this_item`, `ingredient_information`, `feeding_instructions` | per-variant fields in the API |

### The cases that come up

**Different lifestage → separate products.** The brand sells them as separate
pages with different pack art ("Mini Puppy" has a puppy on a differently coloured
bag than "Mini Adult"), so they are separate products here, each with the
lifestage in its Name and in `lifestage` on its variant.

| Brand sells | Our shape |
|---|---|
| RC Mini Adult 8 kg + Mini Puppy 8 kg | **2 products** — "Mini Adult 8kg", "Mini Puppy 8kg" |
| RC Sterilised 37 in 4 kg + 10 kg | **1 product** "Sterilised 37", variants "4 kg" / "10 kg" |
| RC Mini Adult, Medium Adult, Maxi Adult | **3 products** — breed size is not a variant axis |
| RC Maine Coon Adult + Maine Coon Kitten | **2 products** — same breed, but lifestage splits them |
| RC German Shepherd Adult + Labrador Adult | **2 products** — different breed |

A named breed no longer *groups* anything on its own: it just means the breed
belongs in the Name (and the lifestage still splits the line).

**Different flavor → one product, one variant per flavor** (user rule,
2026-08-12), regardless of how the brand pages them: Schesir "Cat Adult" in Tuna
and Chicken is one product with two variants, and so is a brand that gives each
flavour its own page. Set `flavor` on each variant; the flavour goes in the
variant label, not the Name. A **variety/multipack** ("6 × mixed flavors") is one
variant with `flavor` = Flavor Variety, because it is one physical pack.

**Different texture → one product, one variant per texture** (user rule,
2026-08-12): "Sterilised in gravy" + "Sterilised in jelly" is one product with
Gravy and Jelly variants, even though Royal Canin sells them as separate pages
with their own article codes. Same for loaf / mousse / thin slices of one recipe.

### Consequences of the choice

- **Never put the brand in the Name** (user rule, 2026-08-12). The storefront
  prints the brand before the product name, so a brand in the Name renders twice
  ("Royal Canin Royal Canin Mini"). Strip it from the CSV name too — the CSV's
  "RC Mini Adult 8kg" becomes Name "Mini Adult 8kg". The brand lives in
  `brand_id` only.
- **The Name carries everything that identifies the product** — line, breed size,
  lifestage, and (while there is only one) the pack weight, flavor and texture:
  "Mini Adult 8kg", "Maine Coon Kitten 2kg", "Sterilised 37". A varying axis moves
  out of the Name into the variant labels as soon as there are two of them
  ("Sterilised 12x85g" with Gravy + Jelly variants).
- **The slug keeps the brand** (`royal-canin-mini-adult-8kg`): slugs are global
  and a bare "mini-adult" would collide across brands. Name ≠ slug is intended.
- **Variant label = the varying axes**, in this order: flavor, texture, pack
  size — "8 kg", "Gravy 12 x 85 g", "Tuna 85 g", "10+2 kg". Never a lifestage or
  breed size in a label; those identify their own product.
- **Single-variant products keep the varying axis in the Name.** When a second
  pack size / flavor / texture arrives, strip it from the Name and let the labels
  carry it (see "Adding a variant" below).
- **First variant** listed gets `is_default: true` — with several pack sizes,
  default to the one the CSV prioritises (or the mid size).
- **SKU:** brand article code per variant when shown; else `BRAND-SLUG-WEIGHT`.

### Adding a variant to a product that already exists

**Never create a second product for something that is a variant of one already
in the admin.** Before every create, search the catalog; if the product identity
already exists (same brand + line + **lifestage** + breed size + food form +
diet/health feature, differing only in pack weight, flavor or texture), the row
is a **new variant of that product** — edit it instead:

1. `GET /api/admin/products?search=<line name>` → find the id (the search
   matches product names; other query params are silently ignored).
2. `GET /api/admin/products/<id>` → returns the exact re-postable shape, with
   each existing variant carrying its `id`.
3. `PUT /api/admin/products/<id>` with **the full variants array**: every
   existing variant object unchanged (keep its `id`) **plus** the new one (no
   `id`). Keep the existing default's `is_default: true`; the new variant gets
   `false`.
4. `GET` again to confirm both the old and new variants are present.

⚠️ **PUT replaces the whole variants array** (verified 2026-08-12): a variant
left out of the payload is deleted — silently (200) for a non-default one, or
422 if the omitted one was the default. Always build the PUT body from a fresh
GET, never from scratch.

If it's genuinely a different product (different lifestage, breed size, food
form, diet or recipe line), create a new product as usual. Only a second **pack
size, flavor or texture** of an otherwise identical product becomes a variant —
and remember to strip that axis out of the product Name when it starts varying.

### With the import CSV

The CSV decides what exists; this table decides how the rows are grouped:

1. Group CSV rows by product identity: same brand + same line name once the
   **pack weight** is stripped + same lifestage, breed size, flavor, food form,
   category, special diet and health feature.
2. Rows that differ **only by pack weight, flavor or texture** → one product,
   one variant each. Those are the only merges.
3. Rows that differ by **lifestage** → separate products (different pack art).
4. Rows that differ by **breed size** → separate products, even when the CSV
   names look near-identical.
5. A mixed variety pack is one variant with `flavor` = Flavor Variety.
6. So "Puppy 3 kg + Puppy 12 kg + Adult 12 kg" = **two** products: Puppy with
   two variants (3 kg, 12 kg) and Adult with one (12 kg).
7. Never add pack weights the brand lists but the CSV doesn't — no AMD price
   for them.
8. Groups can also span *runs*: if an earlier import already created the
   product, the row is added as a variant to it (see the section above), not as
   a new product.

**When genuinely unclear, create separate products** and flag it in the run
report. Two products can be merged later; splitting one that already has a live
url is worse.

> **Open dev question (much less urgent since 2026-08-12):** does storefront
> filtering/faceting read *all* variants or only the default variant? Now that
> only pack size varies, every variant of a product shares its lifestage, breed
> size, diet and health claims — so a facet reading only the default variant
> still returns the right products. It would only mis-answer a
> **Product Weight** filter. Still worth confirming, together with the
> multi-value question on `special-diet` / `health-feature` in CLAUDE.md.

---

## 3. Our attribute names vs brand wording

**Rule: never name a Siruk attribute after a brand's word for it.** The
authoritative attribute names/codes are the 9 in
`reference/attribute-redesign.md`; brand wording gets *translated* into them.
Brands reuse the same words for different concepts (Royal Canin's "Size" means
dog body size, not pack weight), so copying their label straight into the admin
produces exactly the wrong facet — this table exists because that happened once.

| Brand / source wording | What it actually means | Our attribute |
|---|---|---|
| Royal Canin "Size", "Size Health Nutrition", Mini / Medium / Maxi / Giant; Brit "Large Breed"; Farmina "Mini/Medium/Maxi" | the **dog's** body size | `breed-size` — Extra Small / Small / Medium / Large / Giant Breeds |
| Royal Canin "Breed", "Breed Health Nutrition" (German Shepherd, Labrador, Persian) | a specific breed | **no attribute** — it goes in the product Name and makes its own product |
| Bag / pack weight: "8 kg", "400 g", "Format", "Pack size", "Available sizes", a brand's own "Weight" | how much food is in the pack | `product-weight` — label **Product Weight**, code `product-weight` (renamed from `size` on 2026-08-12; the word "Size" is banned here because RC uses it for breed size) |
| Chewy "Product Weight" filter bands ("5–10 lbs") | computed weight ranges | **no attribute** — storefront computes them from the variant `weight` field |
| "Adult", "Junior", "Senior 7+" | age band | `lifestage` — via table 1 (our bands win) |
| "Croquettes", "Pouch", "Chunks in jelly" | three different things | `food-form` (Dry) / `packaging` (Pouch) / `texture` (Chunks in Jelly) — don't collapse them |

**Weights are always metric, kilogram-based — never lbs/oz** (user rule,
2026-08-12). A source in pounds gets converted before it reaches any field:
`product-weight` label, the product Name, the variant label, and the numeric
variant `weight` (which is in kg). Conversion: `lb x 0.4536 = kg`,
`oz x 28.35 = g`. Prefer the brand's own metric pack size over an arithmetic
conversion when both exist (US "5 lb" = the same bag the EU page sells as
"2 kg"). Flag any row where only a US pack size exists, so nobody mistakes a
converted `2.27 kg` for a real SKU.

If a brand concept has no attribute here, do **not** invent one: leave the field
blank and report it under "wanted but missing" so the user decides (attribute
vocabulary is curated by hand — see CLAUDE.md).

---

## 4. Pricing type — sold by weight vs sold by count

Two kinds of product, two pricing shapes (user rule, 2026-08-12). Decide from
**how the shop sells it**, which in practice follows `food-form`:

| Kind | Admin form | API | Our products |
|---|---|---|---|
| **Sold by weight** — loose food in a bag, price per kilo is the meaningful number | Pricing type = **priced by weight**, then **Rate per Kg** + **Pack weight** | `pricing_type: "per_kg"`, `price_per_kg`, `weight` (kg) | dry kibble (`food-form: Dry`) |
| **Sold by count** — you buy the unit, not the weight | Pricing type = fixed, **Price** | `pricing_type: "fixed"`, `price` (int AMD) | wet pouches/cans/trays and multipacks (`Wet`), supplements, tablets, powders/tins |

### Filling the weight-priced shape

- **Rate per Kg = pack price ÷ pack weight**, from the CSV price. A 1.5 kg bag at
  7,000 AMD → `price_per_kg = 4666.67`, `weight = 1.5`.
- **`price` is ignored by the API on a `per_kg` variant** (it stores 0), so the
  rate *is* the price — get it right or the shopper sees the wrong number.
- Only **2 decimals** are kept, so the recomputed pack price can differ by a few
  hundredths of an AMD (15 kg × 3033.33 = 44,999.95). That rounds back to the CSV
  price; anything worse means the weight or price is wrong.
- **Cost price stays per pack** (the CSV's buy price), not per kilo.
- **Do not set the `product-weight` attribute** — the admin generates the weight
  from Pack weight, so tagging it duplicates the same fact.

### ⚠️ The one conflict, and the dev question behind it

The API requires every variant of a product to have a **unique attribute
combination**. A product whose variants differ *only* by pack size therefore
breaks when `product-weight` is dropped: both variants end up with identical
attributes and the second is refused with *"This attribute combination is already
used in variant N."*

Live example: **Sterilised 37** (15 kg + 2 kg) keeps `product-weight` on both
variants for exactly this reason.

→ **Ask the dev team:** for `per_kg` variants, should the uniqueness check include
`weight` (or the generated weight value) instead of hand-tagged attributes only?
If yes, `product-weight` can come off every weight-priced variant with no
exception. Same bucket of backend questions as the multi-value
`special-diet`/`health-feature` one in CLAUDE.md.
