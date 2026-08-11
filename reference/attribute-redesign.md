# Attribute system redesign (clean slate)

Decided in the 2026-08-11 meeting: delete all existing attributes, values, and
families; recreate with correct naming. This is the target list, modeled on
Chewy's verified facet system, sized for the current catalog (dog/cat food,
treats, supplements, accessories — EU brands).

## Naming conventions (apply everywhere)

- **Codes:** kebab-case, singular, no units baked in (`breed-size`, not
  `size-kg`).
- **Labels (values):** Title Case, one consistent form per concept — never two
  spellings of the same thing ("Grain-Free" only, never also "Grain Free").
- **Weights:** one format, always: `400 g`, `1.5 kg` (dot decimal, space before
  unit, lowercase unit). The old data had "0,4", "400 g", and duplicates —
  that's what we're cleaning.
- Value lists sorted logically (lifestage by age, size by weight), not
  alphabetically — `sort_order` supports this.

## The attributes (9)

### 1. `size` — Size
Variant pack size. Values created as needed per product, following the weight
format above. Starter set from the CSV:
`85 g · 100 g · 150 g · 195 g · 400 g · 800 g · 1 kg · 1.5 kg · 2 kg · 3 kg ·
4 kg · 8 kg · 10 kg · 12 kg · 15 kg · 17 kg`

### 2. `food-form` — Food Form  *(new — Chewy: FoodForm)*
What the product physically is. Replaces guessing from category.
`Dry · Wet · Freeze-Dried · Food Topper · Tablets · Powder · Liquid · Paste`
(Last four are the supplement forms — Canvit is tablets/gels.)

### 3. `lifestage` — Lifestage  *(Chewy: Lifestage)*
`Puppy · Kitten · Adult · Senior · All Lifestages`

### 4. `breed-size` — Breed Size  *(Chewy: BreedSize; dogs only)*
Chewy's exact labels:
`Extra Small Breeds · Small Breeds · Medium Breeds · Large Breeds ·
Giant Breeds · All Breeds`
(Fixes the old "Extra Small Breads" typo.)

### 5. `flavor` — Flavor  *(Chewy: FoodFlavor)*
Primary protein/flavor as marketed. Starter set for these brands:
`Chicken · Turkey · Duck · Beef · Veal · Lamb · Pork · Venison · Rabbit ·
Salmon · Trout · Tuna · Cod · Whitefish · Fish · Poultry · Liver`
Combo recipes ("Lamb & Apple"): tag the primary protein (Lamb); the full combo
name stays in the product/variant name. Add combo values only if customers
actually filter by them.

### 6. `special-diet` — Special Diet  *(Chewy: SpecialDiet, 26 values → our 14)*
Diet claims stated by the manufacturer:
`Grain-Free · With Grain · Gluten-Free · Veterinary Diet · Hypoallergenic ·
Monoprotein · Limited Ingredient · Hydrolyzed Protein · High Protein · Low Fat ·
Weight Control · Sterilised · Indoor · Natural`
(EU-specific keepers: Monoprotein, Sterilised, Hypoallergenic — Chewy's US list
words these differently, our brands use these terms. Gluten-Free added: common
EU-brand claim. Skipped US-marketing values: Human-Grade, Non-GMO, Pea-Free,
Chicken-Free, Flax-Free, Low Glycemic, Starch Free, Plant Based, Raw — add only
if a product in the catalog actually claims them.)

### 7. `health-feature` — Health Feature  *(Chewy: HealthFeature, 29 → our 12)*
What the product claims to help with:
`Digestive Health · Skin & Coat · Hip & Joint · Urinary Care · Kidney Care ·
Dental Care · Weight Management · Hairball Control · Diabetic Support ·
Calming · Immune Support · Mobility`

### 8. `texture` — Food Texture  *(Chewy: FoodTexture; wet food only)*
`Pate · Chunks in Gravy · Chunks in Jelly · Fillets · Shredded · Minced ·
Mousse · Stew`
(Chunks in Jelly and Fillets added vs Chewy's list — Schesir/Stuzzy signatures.)

### 9. `packaging` — Packaging Type  *(Chewy: PackagingType)*
`Bag · Can · Pouch · Tray · Tub · Box · Bottle · Tube`

### Dropped from the old system
- `formula` (Original/Tundra/Six Fish) — recipe names belong in the product
  name, not an attribute. Delete.
- `package-count` — parked, not created for now. Multipacks barely exist in
  this CSV; add it back (values `4 · 6 · 12 · 24`) the first time a variety
  pack shows up. The run report will say so.
- All junk/test values die with the wipe.

## Appendix — full Chewy dry-food facet lists (user-captured 2026-08-11)

Merged from the live Dog Dry Food + Cat Dry Food filter sidebars. Values
marked (dog)/(cat) appear only on that species' list.

**Decision 2026-08-11: go FULL PARITY** — the storefront only shows filter
values that have matching products, so unused values cost nothing to shoppers.
Create everything in this appendix (union of dog+cat + our 3 EU additions),
with two exceptions: skip "Colic Relief" (horse condition leaked into Chewy's
cat data) and skip the entire Ingredient facet (see below). The core lists
above remain as the "most likely to be used" reference, but the create-list is
this appendix.

**Special Diet — 30 Chewy values (+ our 3 EU additions):**
Chicken-Free · Flax-Free · Gluten Free · Grain-Free · High Fiber ·
High-Protein · Human-Grade · Hydrolyzed Protein · Indoor (cat) ·
Limited Ingredient Diet · Low Calorie · Low Fat · Low Glycemic · Low-Protein ·
Molasses-Free (dog) · Natural · No Artificial Colorants ·
No Corn No Wheat No Soy · Non-GMO · Organic · Pea-Free · Plant Based · Raw ·
Soy Free (dog) · Starch Free (cat) · Vegan (dog) · Vegetarian (dog) ·
Veterinary Diet · Weight Control · With Grain
— EU additions: Hypoallergenic · Monoprotein · Sterilised

**Health Feature — 36 Chewy values:**
Allergy Relief · Appetite Stimulation · Brain Health · Calming ·
Circulatory Care · Colic Relief (cat) · Dander · Dental & Breath Care ·
Diabetic Support · Digestive Health · Ear Care · Eye Care ·
Hairball Control (cat) · Heart Care · High-Energy · Hip & Joint Support ·
Hormone Support (cat) · Immune Support · Itch & Redness Remedy · Kidney Care ·
Liver Care · Metabolic (cat) · Muscle Care · Oncology Care · Recovery ·
Reproduction & Nursing · Respiratory Care (dog) · Senior Care ·
Sensitive Digestion · Sensitive Skin · Shedding Control · Skin & Coat Health ·
Thyroid-Support (dog) · Urinary Tract Health · Vitamins & Minerals ·
Weight Management

**Flavor — 34 leaf values (parent groups: Poultry · Meat · Seafood & Fish ·
Fruits & Vegetables · Herbs & Spices; plus "Flavor Variety" = variety packs):**
Chicken · Beef · Salmon · Turkey · Lamb · Tuna · Duck · Flower Herbs ·
Sweet Potato · Peanut Butter (dog) · Liver · Pork · Bacon (dog) · Cheese ·
Pumpkin · Venison · Rabbit · Apple · Buffalo · Shrimp (cat) · Mackerel ·
Carrot · Boar · Quail · Bison (dog) · Kangaroo · Goat · Cod · Tripe (dog) ·
Catfish · Guinea Fowl · Alligator · Sardine · Pheasant (dog)

**Lifestage:** Puppy · Kitten · Adult · Senior · All Lifestages *(core list
already matches exactly)*

**Ingredient — 45 values (dog list only; facet our research had missed):**
Barley · Beef · Beef Liver · Beef Meal · Beta-Carotene · Biotin · Bison ·
Blueberries · Broccoli · Brown Rice · Canola Oil · Carrots · Chicken ·
Chicken Meal · Chickpeas · Coconut Oil · Cod · Cranberries · Duck · Egg ·
Fish Oil · Flaxseed · Flaxseed Oil · Glucosamine · Kale · Lamb · Lamb Meal ·
Lentils · Liver · Oatmeal · Peas · Pork · Potato · Pumpkin · Rice · Rosemary ·
Salmon · Salmon Meal · Salmon Oil · Sunflower Oil · Sweet Potato · Taurine ·
Turkey · Venison · Vitamin E
**Recommendation: do NOT create Ingredient as an attribute.** It duplicates
the composition text we already store per variant (`ingredient_information`),
it's ~45+ values to hand-tag per product, and it mostly matters for
ingredient-avoidance shoppers — which storefront text search over composition
serves. If ever wanted, it's the most automatable facet (parse the composition
list), but that's a later project. Flavor ≠ Ingredient: Flavor is how the
product is marketed (one value), Ingredient is what's in it (many).

## What NOT to copy from Chewy's filter sidebar

Chewy's listing-page filter list mixes real attributes with computed filters.
Only the real attributes get created in the admin:

- **Price / Deals & Savings** — computed from variant pricing, never an
  attribute. The storefront derives these.
- **Product Weight bands** ("Less than 5 lbs", "5–10 lbs") — computed from the
  variant's numeric `weight` field, not hand-tagged. We keep exact sizes in
  `size` + the variant `weight` field; if banded weight filtering is wanted,
  it's a storefront feature over `weight`, not an attribute to maintain.
- **Flavor parent groups** (Poultry / Meat / Seafood & Fish / Fruits &
  Vegetables) — Chewy's flavor facet is two-level; at our catalog size a flat
  flavor list filters fine. Revisit if the flavor list passes ~30 values.
- **"Flavor Variety"** — that's their variety-pack marker, tied to
  package-count, which we parked.
- **Exotic/US-specific values** (Kangaroo, Alligator, Guinea Fowl, Boar …) —
  add a flavor value the first time a product actually needs it, not before.
  Same for non-protein flavors (Pumpkin, Sweet Potato, Cheese): real on Chewy,
  rare in this catalog; the import's "wanted but missing" report will surface
  them when they appear.

## The families (4)

Order = dropdown order in the form.

| Family | Attributes (in order) |
|---|---|
| **Dry Food** | size, flavor, breed-size, lifestage, special-diet, health-feature |
| **Wet Food** | size, flavor, lifestage, texture, special-diet, health-feature, packaging |
| **Treats** | size, flavor, lifestage, special-diet, health-feature |
| **Supplements** | food-form, size, lifestage, health-feature, packaging |

Accessories: no family (no shared attributes yet). All old brand-named
families (Royal/Monge/Orijen Dry Food) die with the wipe.

## ⚠ Before deleting: two things

1. **Existing products reference the old value ids.** Several demo products
   (the Royal Canin/Monge ones from April–May) have `attribute_value_ids` set
   on their variants. Deleting values they point at either orphans or breaks
   those variants. Since it's demo data this is probably acceptable — but
   decide consciously: either clear/recreate those products after the wipe, or
   accept broken references on old demo products.
2. **One-value-per-attribute limit (real backend question).** The variant
   payload shape is `attribute_value_ids: {<code>: <valueId>}` — ONE value per
   attribute per variant. Chewy's whole Special Diet / Health Feature model is
   multi-value (a food is Grain-Free AND High Protein AND Hypoallergenic at
   once; helps Digestion AND Skin & Coat). With the current shape we can tag
   only ONE diet and ONE health feature per product.
   → Ask the dev team: can `special-diet` and `health-feature` accept multiple
   values per variant? If yes, we get real Chewy-style filtering. If no, the
   AI will tag the single most prominent claim and note the rest in the
   description — workable, but weaker filters. **This is the first genuine
   backend change worth requesting.**

## After the wipe + recreate

Refresh `reference/attribute-values.json` (command in CLAUDE.md) so the import
picks from the new menu. The import skill needs no changes — it reads whatever
the menu file contains.
