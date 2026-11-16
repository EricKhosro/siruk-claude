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

- **The restock checks prices first** (2026-11-16, user). `hafo-watch.py crawl` now
  keeps each row's `wholesale` (and `kg_price`) in the snapshot and logs a
  "wholesale" change when it moves. `scripts/restock-price-check.py` compares,
  for the lines we may order, wholesale vs our cost, hafo/zoovet/nemo retail vs
  our price, and our Glovo price vs Zoovet's. Proposals only.
  hafo's `kg_price` (checked 2026-11-16): on a by-weight listing it equals
  `price` (Trixie Bony Mix 31526Tx: 6,300 / 6,300, wholesale 3,935 per kg). On a
  bag listing it is hafo's loose per-kg retail (Monge Medium Adult 15 kg: price
  39,000, wholesale 29,500 = our cost, kg_price 2,700).
  **Cost = hafo wholesale × 0.97 on about 50 goods** (2026-11-16, whole-catalogue
  compare). These are some Trixie (19510 1,212.46 vs 1,250; 41110 300.69 vs 310), GoSi
  and Деревенские Лакомства goods; about 1,200 others equal wholesale exactly.
  This looks like a 3% invoice discount. Not confirmed against a receipt yet.
  The price check counts it as no change. Still open: does the
  hafo basket charge retail or wholesale? Order #12126's page needs the user's
  hafo sign-in, so it wasn't checked. Settle it at the next basket.

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
