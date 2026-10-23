# Costs, and checking them against the rivals

Method: `.claude/skills/armsoft-sync/SKILL.md` → "Checking a cost or a price
against the rivals". Facts behind it:

- **hafo's `wholesale_price_amd` is our purchase price.** hafo's wholesale equals
  Pet House's invoice price (likely the same company, not confirmed); it matched our ArmSoft receipts to the dram
  on every case checked (2026-10-23). Rivals (zoovet, nemo) show only retail.
- **Per-kg listings.** hafo/nemo/zoovet sell some packs by weight; then hafo's
  price *and* wholesale are per kg (page text "Կայքում նշված է կգ-ի արժեքը";
  nemo may say "500 գ-ի արժեքը"; zoovet adds "на развес 1 кг"). Pack cost =
  wholesale × pack kg. `hafo-lookup.py` reports the per-kg figure as the
  variant price — check the page text before using it for a pack.
- ArmSoft stock cost is **ex VAT**; Siruk `cost_price` is incl. VAT (a 20 %
  gap is normal, e.g. Felix 118.13 vs 141.75).
- Supplier boxes: cost per pouch = box cost ÷ pouches (RC 7,500 / 12 = 625).

## Cases checked

| Date | Good | Finding | Done |
|---|---|---|---|
| 2026-10-23 | Trixie 0403 0459 0516 0517 0552 (Siruk 350 383 379 380 381) | Siruk had the per-kg cost as the bag cost (3,935 for a 1.8 kg bag). hafo wholesale per kg 3,935 / 2,875 / 2,515 / 2,515 (Giants 2,590 from the receipt only) | Siruk cost fixed: bag 7,083 / 3,737.5 / 3,269.5 / 3,269.5 / 3,237.5, 100 g 393.5 / 287.5 / 251.5 / 251.5 / 259 |
| 2026-10-23 | Monge VetSolution Gastrointestinal cat 100 g, good 1341 (014617) | cost 470 was a sibling guess; hafo wholesale 470; hafo/nemo/zoovet retail 600 = ours | confirmed |
| 2026-10-23 | same Trixie treats, selling | bags = zoovet exactly; our loose per-kg (×10 of the 100 g price) is the highest in town: 6,600 vs 4,600 (Loops), 5,500 vs 3,900 (Cookie Snack); hafo's Cookie Snack bucket 5,070 > our 4,900 | no change asked |

## Brands and makers

- **Dog Fest = Деревенские Лакомства's export pack.** EAN 6921499711830
  (good 0483, Siruk 1201 Rabbit Ears for Puppies 90 g): hafo names the maker
  Деревенские Лакомства, dogfest.com prints the same EAN. A Dog Fest photo with
  our EAN is the right photo (2026-10-23).
