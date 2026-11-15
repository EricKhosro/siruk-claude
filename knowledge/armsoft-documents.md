# ArmSoft documents — what each one is

Database "Siruk", warehouse 01. Receipts = Պահեստի մուտքի օրդեր (e-invoicing →
Գնման փաստաթղթեր); issue orders = Պահեստի ելքի օրդեր; tax invoices =
"Ստացված հարկային հաշիվներ".

## Reading the tax-invoice list

- It loads slowly and can look incomplete: use ribbon "Փոխել պարամետրերը",
  both periods from 01/01/25, and **Սերիա և համար** = the invoice number, then
  wait ~8 s. A6840667000 looked missing until filtered (2026-10-23).
- Open an invoice (double-click) → tabs Ընդհանուր (the **Մեկնաբանություն**
  field says "<number>հաշվի փոխարեն" when it replaces an earlier invoice),
  Մատակարար, Գնորդ, **Ապրանքացանկ** (the lines).
- Not every goods invoice is stock: equipment and supplies have no warehouse
  receipt, and that is right.

- **New invoices must be pulled** (PM, 2026-10-27): e-invoicing → "Ստացված
  հաշիվների ներմուծում" → source 1 e-invoicing (ուղիղ կապ). Run 2026-10-27 for
  01/10–27/10: 11 invoices, all already in; newest goods invoice A6840667000
  (21/10). The journal also holds non-stock invoices: B7599085058 (22/10,
  «ՏՈՊՐԱԿ ՄՈԼ», 255,000, no VAT) = shop carrier bags 28×24×14 and 37×32×20,
  supplies, no receipt; Ucom A4320961395 A5995523535 A3029868195 and
  Toz-Master A7715964500 = services.
- Pull run 2026-10-28 for 01/10–28/10: 13 invoices, all already in ("Ոչ");
  nothing new since A1412872447 (27/10, receipt 0022). Re-run the same day:
  same 13. A2193010659 (08/10, «ՀԱՅԿԱԿԱՆ ԾՐԱ…», ՀՎՀՀ 00807555, 19,000)
  = services (likely the ArmSoft vendor), no receipt.
- Third pull 2026-10-28 (17:19) imported **A3297411457** (Pet House, 28/10,
  56,500 incl. VAT): Monge Indoor cat 10 kg 27,000 (0039, Siruk 1162) and
  Monge Medium Adult 15 kg 29,500 (0043, Siruk 1319), 1 bag each; costs equal
  Siruk's → receipt 0023.
- Fourth pull 2026-10-28 imported **A1081354321** (Pet House, 28/10, 23,185
  incl. VAT, 4 × 1): Trixie Be Eco Vico 40×40×56 grey-green 6,125 (Trixie
  40210 per Galaxus — no hafo/zoovet/nemo row; ArmSoft 0302 is a different
  Be Eco tray, EAN 4011905402116); flexi New Neon M tape blue 8,000 (hafo
  032118 → ArmSoft **1615**, Siruk 1150 variant 2236); flexi Black Design S
  cord black/pink 4,000 (hafo 033318 → ArmSoft **1616**, Siruk 1441); leash
  "S, 12 kg 5 m blue, S Color" 5,060 — not identified (no hafo row at that
  cost). The toilet: user approved **9,800** (recommendation 9,820; hafo's
  plain Vico same size/cost sells at 9,800) → ArmSoft **1617** (price by XML),
  Siruk **1442** (EAN 4011905402109). ArmSoft 0302 is named "Vico Be Eco" but
  is the Be Eco **Carlo** tray 40211 (Siruk 1062) — name to fix. The "S Color"
  leash = EAN **4000498014219** (box label "flexi Colo… blau") = flexi Color
  Dots S cord 5 m blue (PetSky prints the EAN; discontinued on flexi.de); no
  rival price, user approved the recommendation **8,100** → ArmSoft **1618**,
  Siruk **1443**. All four on **receipt 0024**, posted.

- Pull 2026-11-02 for 25/10–02/11: 8 invoices, 4 new. **A5514649574** (Pet
  House, 31/10, 31,000: Monge All Breeds Adult Monoprotein Beef & Rice 12 kg,
  0005, Siruk 1152) → receipt 0026; **A4577070686** (Pet House, 01/11, 20,300:
  Acana Bountiful Catch 4.5 kg, 0010, Siruk 969) → receipt 0027 — both costs
  equal the 09/09 receipt A6833625890. **A2847444750** (Pet House, 30/10,
  37,000: 1 × "Կեր շն MONGE Speciality Line HYPOALLEGENIC 15կգ") was held
  (no ArmSoft good, no Siruk product), then imported the same day on the
  user's yes: hafo 006437 / EAN 8009470006439 = Monge **Best for Breeders**
  Speciality Line Adult Hypo Salmon & Tuna 15 kg (mongebestforbreeders.com
  code 800947000643) → Siruk **1444** (bag 51,000 + 1 kg 3,550 = hafo's own
  per-kg price, user approved), ArmSoft good **1619** (303 + 003 × 15, PLU
  00121, prices by XML) → receipt 0028. **A2943992285** («ԱՈՒԹՕՄԱՖԻՆԳ» ՓԲԸ, ՀՎՀՀ 00101514,
  31/10, 120,000) = accounting/tax services, no receipt.
  The pull's report opens as a **tab** ("Ստացված հաշիվների ներմուծում"), not a
  window.
- Pull 2026-11-03 for 30/10–03/11: 6 invoices, 2 new, both Pet House 02/11:
  **A1973228940** (58,000: Monge Turkey 12 kg 0018 + Indoor 10 kg 0039) →
  receipt 0031; **A6045547258** (6,815) = the invoice temporary 0029 was
  waiting for, plus 4 goods Siruk lacked — hafo identified them exactly
  (207766 / 207796 / 207756 Derevenskie Lakomstva cat pillows 30 g, TX427161
  Trixie Premio Duck Filet Bites 50 g; the invoice's "բադի մսով Bites 50g" is
  **not** 0800 Hearts, though both cost 685) → Siruk 1445 / 1446, ArmSoft
  1620–1623 (prices by XML) → receipt 0032. A pull from 30/09 timed out
  ("connection attempt failed … e-invoicing.taxservice.am:443"); the shorter
  period worked.
- Pull 2026-11-04 (15:57) for 30/10–04/11: the same 6 invoices, all already
  in ("Ոչ"); nothing new, no receipt. Again at 16:43 for 28/10–04/11: 8
  invoices (+ A1081354321 / A3297411457 of 28/10, receipts 0024 / 0023), all
  already in. Third try 17:51–17:54 (28/10–04/11, then 01/11–04/11, three
  runs): every run failed with "Առկա է տեխնիկական սխալ …
  e-invoicing.taxservice.am/api/invoice/invoice-count կանչը պատասխան չի
  վերադարձրել" — the tax service's API didn't answer (its website did,
  HTTP 200). 18:41 (28/10–04/11): "e-invoicing: The operation has timed
  out." 18:45 for 02/11–04/11 worked: 2 invoices (A6045547258, A1973228940),
  both already in — nothing new. ArmSoft's start-up notice: the
  subscription (key TCLD2879) ends **07/11/26**, renewal 19,000 AMD.
- Pull 2026-11-05: 01/11–05/11 failed twice at 11:46 and 12:04 ("A connection
  attempt failed … e-invoicing.taxservice.am:443"), although the site
  answered a plain GET in 5–15 s and the API endpoint at once (405 to a GET).
  03/11–05/11 at 12:05 worked: 1 invoice, new — **A1077764349** (Pet House,
  05/11, 44,576 incl. VAT, no replacement note): Monge All Breeds Adult
  Salmon & Rice 12 kg × 1 @ 33,500 (0015, Siruk 1648); Kormell cat pâté beef &
  liver 75 g × 28 @ 117 (0348, Siruk 1347); Kotoffey hygienic litter
  2.7 kg / 4.8 l × 2 @ 1,090 (0237, Siruk 2030) — costs equal the last
  receipts; and **Kotoffey hygienic litter 8.1 kg / 14.4 l × 2 @ 2,810** =
  hafo **KF5200611** (EAN 4627106520063, sale 4,500, wholesale 2,810), **not
  1441**: 1441 / Siruk 2102 is the *clumping* 14.4 l, KF5200511 (A0969245265
  of 01/10 named it «գնդվող»; today's line says «հիգիենիկ», hafo's exact
  name). Same cost, so cost can't tell them apart — the name does. No ArmSoft
  good, no Siruk variant → invoice held, then added the same day on the user's
  yes: Siruk **1316 variant 2246** (8.1 kg (14.4 l), volume 14,400 ml like its
  2.7 kg sister, 4,500 / cost 2,810, photo = zoovet's unwatermarked packshot
  printed «ГИГИЕНИЧЕСКИЙ 8,1 кг … 14,4 л», media 17179; kotoffey.ru, the
  barcode lookup, 4lapy and a web search for the EAN had nothing), ArmSoft
  good **1624** (001 piece, EAN on 001, price 4,500 by XML,
  `final/armsoft-2026-11-05/new-good-1624.xml`) → **receipt 0033**, posted.
- **hafo orders vs invoices** (checked 2026-11-05 from the user's hafo.am
  "Իմ Պատվերները" page): an order usually equals one or two invoices to the
  dram — #11934 (31/10, 20,300) = A4577070686; #11968 (02/11, 10 units,
  64,815) = A1973228940 + A6045547258. **#11997** (03/11, 52,608) does not
  match A1077764349: Club 4 Paws chicken in gravy 85 g × 24 @ 225 ordered and
  **delivered** (user) but not invoiced; Kormell 24 ordered, 28 invoiced;
  Monge 12 kg shown as 44,400 on the order page, invoiced 33,500; the 4
  Kotoffey bags are invoiced but not on this order. User: wait for Pet
  House's invoice, no temporary receipt (state/open-items.csv). The order
  page needs the user's hafo login — Claude can't open it; ask for a
  screenshot of the order's lines.
- Pull 2026-11-05 14:09 for 03/11–05/11: 1 invoice, A1077764349, already in
  ("Ոչ") — the Club 4 Paws invoice has not been issued yet.
- **2026-11-09: ArmSoft won't open the Siruk database.** At login (Կատարել)
  it says the monthly key **TCLD2879** is deactivated, so the monthly services
  need a renewed subscription, and offers the demo version (Այո / Ոչ). Ոչ goes
  back to the login screen. The subscription ended 07/11/26 (renewal 19,000
  AMD, start-up notice of 04/11). No pull possible until it is renewed. The
  user decides whether to renew or try the demo version.
  11:11 the same day the login went through (key working again; status bar
  still "Ծրագիրը սպասարկման մեջ չէ"). The pull 03/11–09/11 then failed:
  "e-invoicing սխալ. «20092252n» օգտագործողի մուտքը համակարգ հնարավոր է որոշ
  ժամանակ անց" (the tax service lets that user log in only after a while).
  A few minutes later ArmSoft showed its own **e-invoicing login box** (ՀՎՀՀ
  20092252, user 20092252n, password saved, Մուտք) — the user's sign-in,
  not Claude's to press. The user signed in and the pull ran by itself.
- Pull 2026-11-09 11:17 for 03/11–09/11: 6 invoices, 5 new. Services, no
  receipt (by supplier, lines not opened): **A8251288089** Toz-Master 07/11
  3,600; **A0964047876** Ucom 06/11 1,800; **A1897768240** Ucom 05/11 6,500
  (Ucom / Toz-Master dates are supply dates of 31/10; the journal lists them
  only from a start date before 01/11). Goods, both Pet House 08/11, no
  replacement note, **not received yet**:
  - **A6814768463**, 12,580 incl. VAT: Monge Fresh kitten pâté beef 85 g
    × 28 @ 310 (8,680); clumping litter 2.7 kg / 4.8 l × 1 @ 1,090; clumping
    litter 8.1 kg / 14.4 l × 1 @ 2,810 (ArmSoft maps it to 1441).
  - **A2631104009**, 42,815 incl. VAT, 11 lines: kitten scratcher wave
    38×7×18 light purple/green 1 @ 2,000; scratcher wood/cardboard 4 legs
    46×4×25 1 @ 5,125; Mnyams cat treats Healthy Teeth (ատամներ) 60 g (707953) 2 @ 515;
    Mnyams sterilised cat treats L-carnitine 60 g (706273) 2 @ 515; square
    scratcher 35×4×35 1 @ 4,875; cat purée chicken 5×14 g 3 @ 625; tuna &
    shrimp (ծովախեցգետին) 5×14 g 3 @ 625; tuna & whitefish 5×14 g 3 @ 625;
    deep cardboard scratcher 45×10 open purple 1 @ 7,560; Rolf Club flea &
    tick spray dogs 200 ml (R422) 2 @ 3,785; Petmil pads 60×40 (100 per
    pack) 100 @ 80 (8,000). None mapped to an ArmSoft code by the invoice.
  - **Against the hafo orders** (hafo.am/my-orders, read in the built-in
    browser after the user signed in; `/my-orders/<id>` is server-rendered
    HTML with name | SKU | qty | price | total per line): the two invoices
    together are exactly order **#12073** (06/11, 31,010) — 55,395 = 31,010 +
    24,385 from 4 lines billed differently: Monge Fresh kitten 85 g ordered 1,
    invoiced 28; Petmil pads ordered 1 (@ 80), invoiced 100; replacement
    cardboards 48021-10Tx (655) and 48020-10Tx (1,250) invoiced as the full
    46×4×25 (5,125) and 35×4×35 (4,875) boards. Orders #12105 (30,465), #12106
    (15,395), #12110 (4,150), all 08/11, and #11997's Club 4 Paws × 24 are not
    invoiced yet (state/open-items.csv).
  - **User 2026-11-09 (asked Pet House):** Monge Fresh × 28 and the 100 pads
    are right as invoiced; the two scratching boards 48020 / 48021 were **sent
    by mistake — skip them**. So receipt 0036 takes A2631104009 **without** those
    two lines: 32,815 against the invoice's 42,815 (comment on the receipt).
    Pet House owes a corrected invoice or takes the boards back.
- Pull 2026-11-09 17:12 for 05/11–09/11: 8 invoices, 2 new, both Pet House
  09/11: **A2576225977** (19,330, 11 lines) = order #12106's six leads (Trixie
  Cavo 144201 / 144213 3,090 each, Trixie Premium 200002 1,875, Kaskad canvas
  00597K 2,500 / 05847K 3,185 / 05704K 1,655) + #12105's three Derevenskie
  pillows (355 each) + #12110's pizza toy 35952 (1,655) and hedgehog 34748
  (1,215); **A8770854680** (23,000) = #12105's Club 4 Paws rabbit 14 kg (order
  page said 29,400; invoiced 23,000 = our cost). Still not invoiced: #12110's
  Premio chicken pâté 3179Tx (1,280) and #11997's Club 4 Paws × 24.
  The supplier's leash codes ("…02445", "…02447") are EAN digits 8–12, and
  "72120011" / "02125012" / "72125017" are Kaskad articles.
- **2026-11-09 new goods 1637–1645** (`final/armsoft-2026-11-09/new-goods-1637-1645.xml`,
  group 00009, VAT off, price type 01 by XML): 1637 Monge Fresh Kitten beef 85 g
  (450), 1638 Trixie Scratching Bed Lilly 48014 (12,100, CPA 4823), 1639 Petmil
  plain pad 60×40 (001 = one pad, code **00122**, price 130; 004 × 100 = the bag
  EAN 4627104433808, no price — like 1612), 1640 / 1641 Trixie Cavo lead L–XL
  black / blue (4,950), 1642 Kaskad canvas lead 25 mm × 3 m (4,000), 1643 / 1644
  Kaskad stitched canvas lead 25 mm × 5 m / 20 mm × 2 m (5,100 / 2,650), 1645
  Trixie Premium lead XS royal blue (3,000); leads CPA 4201. Siruk first:
  products 1469–1475 (variants 2259–2267) with these accounting codes.
- Pull 2026-11-15 11:23 for 07/11–15/11 (office; driven from PowerShell, the
  computer-use tools were not loaded): 13 invoices, 4 imported now
  (A8519891402, A8707682798, A0750259960, A3595953555), 9 already in.
  **A3595953555** («ՀԱՅԿԱԿԱՆ ԾՐԱԳՐԵՐ», 09/11, 19,000) = the ArmSoft
  subscription, a service, no receipt. Found in Գնման փաստաթղթեր and not in
  these notes before: **receipt 0039** (12/11, A9066878431 of 10/11, 31,175)
  and **receipt 0040** (12/11, A1771977413 of 10/11, 34,640), both Pet House,
  posted — together 65,815 = hafo order #12126's total; and two **0.00**
  receipts with reused numbers, no supplier, no comment: **0019** (11/11) and
  **0020** (14/11) — lines not opened, who made them not checked.
  **Five Pet House invoices have no receipt** (none has a replacement note;
  no line is mapped to an ArmSoft code by the invoice; prices incl. VAT;
  candidates from the 05/11 goods export by name only — cost, Siruk variant
  and goods added after 05/11 not checked):
  - **A1433256986** (13/11, 10,055): ceramic bowl wide-rim 0.6 l / 23 cm grey
    1 @ 3,215; ceramic bowl with cat picture, grey, 0.25 l / 13 cm 1 @ 1,250;
    ceramic bowl «Մալինոլի», white petals, high, 0.15 l / 13 cm 1 @ 1,935;
    puppy toilet with rubber base 49 × 41 cm beige 1 @ 3,655. No candidate.
  - **A2164605176** (13/11, 7,300): cat litter light wood 2 kg / 6 l 1 @ 1,060
    (0235); light wood 6 kg / 18 l 1 @ 2,590 (none); dark wood 2 kg / 6 l
    1 @ 1,060 (0238); dark wood 6 kg / 18 l 1 @ 2,590 (none).
  - **A8519891402** (14/11, 11,400): Filet chicken PRO DENTAL 80 g 3 @ 1,190
    (1001); dog duck sticks 90 g 3 @ 1,450 (0499); calcium bone for dogs'
    teeth 4 pcs 90 g 3 @ 1,160 (none: 0510 is 60 g).
  - **A8707682798** (14/11, 4,305): cat pillows salmon purée 30 g 3 @ 355
    (1620); cat purée 5×14 g chicken / tuna & shrimp / tuna & whitefish 1 each
    @ 625 (1121 1122 1123); cat treat pillow-shaped 35 g 1 @ 805 (none);
    Dentinos Denta Fun 50 g cat 1 @ 560 (none).
  - **A0750259960** (14/11, 5,400): Club 4 Paws jelly for cats Sterilised 80 g
    24 @ 225 (0399 by exact name). Not the 24 chicken-in-gravy 85 g pouches
    (0342) still awaited for order #11997 — same count and price, other name.
  - **Against the hafo orders** (hafo.am/my-orders, built-in browser,
    2026-11-15): #12126 (09/11, 65,815) = A9066878431 + A1771977413 by total
    (receipts 0039 / 0040; lines not compared). **#12190** (12/11, 18,230,
    9 lines) = A1433256986 + A2164605176 (17,355) **minus one line not
    invoiced: cat teaser with feather TX 045091 × 1 @ 875**. Its hafo SKUs:
    puppy toilet 23415Tx, bowls 24652Tx / 24797Tx / 24802Tx, Kotoffey wood
    litter KF 5200811 (light 18 l), KF 5200411 (light 6 l), KF 5200311 (dark
    6 l), KF 5200711 (dark 18 l). **#12211** (13/11, 11,400) = A8519891402
    line for line: 11235S, DL 711226, DL 304006 (the "calcium bone 4 pcs
    90 g"). **#12220** (14/11, 4,305) = A8707682798: 207766, TX 042661
    (Dentinos), 11406 (pillow-shaped 35 g), 42681Tx / 42682Tx / 42683Tx.
    **#12225** (14/11, 5,400) = A0750259960: 908935 Club 4 Paws Sterilised
    chicken jelly 80 g × 24. **Not invoiced yet**: #12237 (14/11 17:38,
    42,855, 21 lines / 27 units, dog dental treats) and #12238 (14/11 19:42,
    5,870: plush bear toy 35859Tx 2,215 + Simple'n'Clean silicate litter 5 l
    TX 040261 3,655); still also #11997's Club 4 Paws chicken × 24 and
    #12110's Premio pâté 3179Tx.
- Pull 2026-11-15 14:24 for 10/11–15/11 (office, user asked to check again):
  7 invoices, **all already in** (A8519891402, A8707682798, A0750259960,
  A1433256986, A2164605176, A9066878431, A1771977413), nothing new. hafo
  orders #12237 / #12238 still have no invoice.
- Pull 2026-11-15 18:09 for 10/11–15/11: 9 invoices, **2 imported now**, both
  Pet House, 15/11, **not received** (each has goods Siruk lacks; lines in
  `state/open-items.csv`): **A1614547319** (54,528) = hafo #12252 (15/11,
  53,124) with 28 of each Kormell pâté instead of 24 — turkey 83043J is new,
  chicken 0349, duck 0351, ACANA Grass-Fed Lamb 11.4 kg 0074 @ 44,700;
  **A3182055782** (53,130, 23 lines / 31 units) = hafo #12237 + #12238
  (48,725) plus one more Simple'n'Clean 5 l and one more Dentros 3173Tx —
  13 of its goods are not in Siruk. The journal shows prices without VAT
  (× 1.2 = the order price). Still not invoiced: TX 045091 (#12190), #11997
  Club 4 Paws × 24, #12110 3179Tx — 7,555 together.
- Pull 2026-11-15 21:15 for 10/11–15/11: 9 invoices, all already in, nothing new. hafo
  orders unchanged (newest still #12252); still not invoiced: TX 045091 (#12190, 875), #11997
  Club 4 Paws chicken × 24 (5,400), #12110 3179Tx (1,280) = 7,555.
- **2026-11-15 new goods 1653–1666** (`final/armsoft-2026-11-15/new-goods-1653-1666.xml`,
  group 00009, VAT off, unit 001, EAN on 001, price 01 by XML; CPA 2309, toy
  6307): 1653 KorMell turkey pâté 75 g 83043J (150), 1654 / 1655 Trixie Denta
  Fun Rolls duck 3 pcs/140 g 31373 (2,750) and chicken 30 pcs/240 g 31378
  (5,150), 1656 Trixie Dentros with Chicken 180 g 3173 (1,200), 1657 Trixie
  Teddy Bear 30 cm 35859 (3,550), 1658 8in1 PRO Dental Twisted Sticks XS 190 g
  12265S (7,600), 1659 / 1660 8in1 Delights Spirals chicken / duck 60 g 15476 /
  15482 (2,350), 1661 8in1 Tasties Calcium Bones 85 g 15278 (1,850), 1662
  SmartBones Peanut Butter Bones 2 pcs/158 g 02721S (2,850; new Siruk brand
  55), 1663 / 1664 Mnyams Dental Sticks beef / chlorophyll & rabbit 100 g
  170433 / 170453 (1,300), 1665 Mnyams Dental Bones beef 70 g 170423 (850),
  1666 Mnyams Dental Snack beef 95 g 176793 (950). Siruk: variants 2275–2278
  added to 1052 / 521 / 1047, new products 1481–1486 (variants 2279–2285),
  codes set; 1663–1665 = Siruk products 1487 Dental Sticks (variants 2286, 2287) and
  1488 Dental Bones (2288), created with `--force` on the user's yes after
  `siruk create` refused them as look-alikes of other brands' products. hafo "DENTAL - HARD chlorophyll" = mnyams.ru «Зубные палочки» с
  хлорофиллом и кроликом (art. 170456); hafo "MEDIUM bones, phytocomplex 70 g"
  = «Зубные косточки» с говядиной (170425). Glovo: ACANA Grass-Fed Lamb,
  31225, 4026, 31347 switched back on 19:10; 12 new goods sent to review, case
  **500bO000018w3IDQAY** (`final/glovo/new-2026-11-15b/`; KorMell turkey and
  SmartBones held back for a clean photo). Sent at Siruk + 14 %; the user then
  chose **Siruk + 20 %** (rounded up to 50) for these 12 — none is on Zoovet's
  Glovo store — and `glovo-portal.py set-price` applied it (3,300 6,200 1,450
  4,300 9,150 2,850 2,850 2,250 1,150 1,600 1,600 1,050). Whether +20 % becomes
  the general base instead of +14 % is not decided.
- **Lens on this Windows machine** (2026-11-15): `.venv-scrapling` did not exist; `python -m venv
  .venv-scrapling` + `pip install "scrapling[fetchers]"` and `scripts/google-lens.py` ran with
  `.venv-scrapling/Scripts/python.exe`, no CAPTCHA, 9 jobs in ~8 min. Lens results carry the page
  url, not the image: the photo comes from the page's `og:image`. `scripts/hafo-audit.py` is too
  slow here (reads every product) and its file-name test misfires on `…-s1350x1350.jpg`; a
  contact sheet of the suspects found the three real hafo photos (83043J, 02721S, 12265S), all
  replaced the same evening.
- **2026-11-15 new goods 1646–1652** (`final/armsoft-2026-11-15/new-goods-1646-1652.xml`,
  group 00009, VAT off, unit 001, EAN on 001, price type 01 by XML): 1646 Trixie
  puppy toilet Nappy Loo 49 × 41 cm 23415 (5,850, CPA 3924), 1647 / 1648 / 1649
  Trixie ceramic bowls 24652 / 24797 / 24802 (2,000 / 3,100 / 5,150, CPA 6912),
  1650 / 1651 Kotoffey light / dark wood litter 6 kg (18 l) (4,150, CPA 4401),
  1652 Trixie Dentinos with Vitamins 50 g, art. 4266 (900, CPA 2309). Siruk:
  variants 2268–2273 already existed without a code (products 1476–1479,
  1318, 1317; added 13/11) and got these codes; **Dentinos was new → Siruk
  1480**, variant 2274 (hafo TX 042661, EAN 4011905042664, 900 / cost 560,
  trixie.de texts and 4 photos, ru / hy). Glovo price type 02 not set for
  1646–1652 yet. The invoice's "pillow-shaped 35 g" is Beaphar Cat-a-dent
  Bits (hafo 11406, ArmSoft 0559); its "calcium bone 4 pcs 90 g" is DL304006
  (ArmSoft 0512).
- **Glovo after receipts 0041–0045** (2026-11-15): KF5200411 and KF5200311
  switched back on; the other nine restocked goods were already on. The seven
  new goods (23415 24652 24797 24802 KF5200811 KF5200711 4266) were sent to
  Glovo's review the same day: `final/glovo/new-2026-11-15/glovo-new-2026-11-15.xlsx`,
  price = Siruk + 14 % rounded up to 50 (no Zoovet match looked up), categories
  from the map (7074 / 20619 / 7077 / 7078), with their EANs, case
  **500bO000018v24qQAA** ("All the operations were successful"); `--review` the same
  afternoon: all 7 SUCCESS, prices and categories kept, Glovo reworded 6
  titles (KF5200811's hy title lost "light wood"). `jq` 1.8.2 was installed with
  winget for this (user yes) — it lands in `%LOCALAPPDATA%\Microsoft\WinGet\Links`,
  which a running session must add to PATH; `uv` is still not on PATH
  (`python -m siruk …` works; set `PYTHONUTF8=1` and, in Git Bash,
  `MSYS_NO_PATHCONV=1`). The stock check also listed 21 goods to switch off as
  sold out — applied at 12:52 from a second export taken at 12:51 (identical to the 11:54 one; user asked for a fresh one): 18 at stock 0 and 3 bags with no sealed bag left (0022 6.4 of 7 kg, 1450 7 of 8 kg, 1459 4 of 7 kg). `final/glovo/glovo-availability-2026-11-15-1250.xlsx`; the re-run says 0 to switch off. Two of the 21 (Trixie 31347, 4026) are on hafo orders #12237 / #12238, delivered per the user but not invoiced, so not in ArmSoft.
- **Driving ArmSoft without computer use** (2026-11-15): `scripts/armsoft-drive.ps1`
  (`-Do front|shot|click|dbl|drag|keys|paste|wins`, screen pixels, a capture
  after each step, Armenian text pasted from a UTF-8 file) did the pull, both
  exports, the XML imports and the posting.

## Documents (newest first)

| Doc | Date | What it is | Status |
|---|---|---|---|
| receipt **0047** | 15/11 | Pet House **A3182055782** (15/11, 53,130 incl. VAT, 23 lines / 31 pcs) = hafo #12237 + #12238 plus 1 more 0217 and 1 more 1656: 1007 @ 3,500; new 1654 × 2 @ 1,715; 0407 @ 685; 1011 @ 965; 1015 @ 1,685; new 1657 @ 2,215; new 1658 @ 4,900; new 1662 × 2 @ 1,835; new 1661 @ 1,190; new 1659, 1660 @ 1,515; new 1664, 1663 @ 810; new 1665 @ 530; new 1666 @ 590; 0449 × 3 @ 1,450; 0512 @ 1,160; 0217 × 2 @ 3,655; new 1656 × 2 @ 750; 0573 × 2 @ 1,340; new 1655 @ 3,215; 0632 @ 1,655; 0633 × 2 @ 1,625 | posted by Claude, user asked |
| receipt **0046** | 15/11 | Pet House **A1614547319** (15/11, 54,528) = hafo #12252 with 28 of each pâté instead of 24: new 1653 × 28, 0349 × 28, 0351 × 28 @ 117; 0074 ACANA Grass-Fed Lamb 11.4 kg as **003 × 1 @ 44,700**. Both in `final/armsoft-2026-11-15/pethouse-receipts-0046-0047.xml` | posted by Claude, user asked |
| receipt **0045** | 15/11 | Pet House **A0750259960** (14/11, 5,400 incl. VAT) = hafo order #12225: 0399 Club 4 Paws Sterilised chicken jelly 80 g × 24 @ 225. Siruk variant 885 was out of stock since 28/10 → stock set back to 10 | posted by Claude, user asked |
| receipt **0044** | 15/11 | Pet House **A8707682798** (14/11, 4,305) = hafo #12220: 1620 × 3 @ 355, 1121 1122 1123 × 1 @ 625, 0559 Beaphar Cat-a-dent Bits 35 g × 1 @ 805, new **1652** Trixie Dentinos 50 g × 1 @ 560 | posted by Claude, user asked |
| receipt **0043** | 15/11 | Pet House **A8519891402** (14/11, 11,400) = hafo #12211: 1001 × 3 @ 1,190, 0499 × 3 @ 1,450, 0512 × 3 @ 1,160 | posted by Claude, user asked |
| receipt **0042** | 15/11 | Pet House **A2164605176** (13/11, 7,300) = part of hafo #12190: 0235 and 0238 (2 kg / 6 l) × 1 @ 1,060, new **1650** light and **1651** dark wood litter 6 kg / 18 l × 1 @ 2,590 | posted by Claude, user asked |
| receipt **0041** | 15/11 | Pet House **A1433256986** (13/11, 10,055) = part of hafo #12190: new **1649** bowl 24802 @ 3,215, **1647** bowl 24652 @ 1,250, **1648** bowl 24797 @ 1,935, **1646** puppy toilet 23415 @ 3,655, 1 each. All five receipts in one file, `final/armsoft-2026-11-15/pethouse-receipts-0041-0045.xml` (five `MTIncome` in one XML import fine) | posted by Claude, user asked |
| receipt **0038** | 09/11 | Pet House **A8770854680** (09/11, 23,000 incl. VAT): 0071 Club 4 Paws rabbit 14 kg as **003 × 1 @ 23,000** (23,000 / 14 doesn't fit 2 decimals). Stock after 1.536 bags. File `final/armsoft-2026-11-09/pethouse-A8770854680-receipt-0038.xml` | posted by Claude, user yes |
| receipt **0037** | 09/11 | Pet House **A2576225977** (09/11, 19,330 incl. VAT, 11 pcs): new 1640 1641 (3,090), 1642 (2,500), 1643 (3,185), 1644 (1,655), 1645 (1,875); 1620 1621 1622 × 1 @ 355, 1038 @ 1,655, 1114 @ 1,215 | posted by Claude, user yes |
| receipt **0036** | 09/11 | Pet House **A2631104009** (08/11) **without** the boards 48020 / 48021 (sent by mistake, user): 32,815 of 42,815. 1606 @ 2,000, 0418 / 0421 × 2 @ 515, 1121 1122 1123 × 3 @ 625, new 1638 @ 7,560, 0153 × 2 @ 3,785, new 1639 × 100 (001) @ 80 | posted by Claude, user yes |
| receipt **0035** | 09/11 | Pet House **A6814768463** (08/11, 12,580 incl. VAT): new 1637 × 28 @ 310, 0236 × 1 @ 1,090, 1441 as **003 × 1 @ 2,810** | posted by Claude, user yes |
| issue **0007** | 09/11 | **1625** YOKO bull root S × 3 written off at cost 800 (2,400): sold at the shop without ArmSoft (user: "write them off"). Stock after 7 | posted by Claude, user asked |
| receipt **0034** | 09/11 | ԴԱՎԻԹ ԼԵՎՈՆՅԱՆ ԱՁ (ՀՎՀՀ 20169575) **B6860271375** (08/11, 48,400, no VAT), rows 1–3 and 5–12: new goods **1626–1636** (YOKO chews, imported the same day from `final/armsoft-2026-11-09/new-goods-1626-1636.xml`, CPA 2309, group 00004, sale price = cost × 1.5 per the user), 30 pcs, 40,400. No partner code (supplier not set up); invoice no. + supplier in the comment | posted by Claude, user asked |
| receipt **0018** (2nd use of the number) | 09/11 | Same invoice, row 4: **1625** Ցլի արմատ (փոքր) × 10. Typed by narek at **1,200 with VAT**; Claude turned it back to a draft and fixed it to **800, no VAT**, invoice B6860271375 + supplier in the comment, reposted (user yes). 1625 itself was made by hand with no ԱՏԳ ԱԱ code; Claude set **2309** (user yes) | fixed by Claude |
| issue **0006** | 06/11 | Stock count correction, user: "we don't have them" — both were off on Glovo by hand while ArmSoft still showed stock: **1456** RC Sterilised 15 kg −1.5 kg (303, PLU 00088; cost 5,200.01) and **1121** Trixie Creamy Snacks Chicken 5×14 g −1 (cost 625.00), total 5,825.01. Comment "Stock count correction: not on the shelf, Glovo off (user, 2026-11-06)". Stock after 0 / 0 (the line panel read 1.5 kg / 1 before) | posted by Claude, user asked |
| till sale **0000155** / HDM **00000138** | 05/11 | **Was left as a draft (Սևագիր), HDM N "XXXXXXXX"** after the shop's internet dropped mid-sale (~16:57): 0371 Monge Grain Free Monoproteico can 400 g × 1 @ 2,000 + 0372 the same, the other flavour, × 1 @ 2,000 = 4,000, card (Բանկ_POS). The bank terminal approved the card for 4,000 (merchant slip 16:57, RRN 630912680821, auth 680869). Draft = no stock moved; not in the offline journal (ՀԴՄ կտրոններ (Օֆլայն) held only return 0000002). Last fiscal number ArmSoft knows: 00000137 (0000154, 970, same day). "XXXXXXXX" = ArmSoft sent the print and never got the answer. **The register DID print it**: the seller's reprint on the register ("(Ֆ) Կրկնօրինակ", the last-receipt duplicate) reads **ԿՀ 00000138, fiscal number 81151246**, 05-11-26 16:56:51, cashier 3, 0371 + 0372 × 1 @ 2,000, Անկանխիկ 4,000; ԱՀ NCD300425106 = the same Newland N950 that printed the bank slip. Fix found in the journal's right-click menu: **Խմբագրել ՀԴՄ կտրոնի N-ը** (set 00000138), then **Գրանցել** (post) — never ՀԴՄ (F3) again (a second fiscal receipt). Menu also has Վերջին կտրոնի կրկնօրինակի տպում (reprint the last receipt) **Fixed 17:28**: HDM N set to 00000138 (right-click → Խմբագրել ՀԴՄ կտրոնի N-ը), then Գրանցել + Այո → **Գրանցված**; ՀԴՄ (F3) greyed out after; stock 0371 1 → 0, 0372 1 → 0 | fixed by Claude at the office, user yes |
| receipt **0033** | 05/11 | Pet House **A1077764349** (05/11, 44,576 incl. VAT): 0015 Monge All Breeds Adult Salmon & Rice 12 kg as **003 × 1 @ 33,500** (33,500 / 12 doesn't fit 2 decimals), 0348 Kormell pâté beef & liver 75 g × 28 @ 117, 0237 Kotoffey hygienic 2.7 kg × 2 @ 1,090, **1624** Kotoffey hygienic 8.1 kg × 2 @ 2,810 (new good, same day). Stock after: 0015 1 bag, 0348 28, 0237 2, 1624 2. File `final/armsoft-2026-11-05/pethouse-A1077764349-receipt-0033.xml` | posted by Claude, user yes |
| receipt **0032** | 03/11 | Pet House **A6045547258** (02/11, 6,815 incl. VAT, 8 pcs): new goods 1620 1621 1622 (Derevenskie Lakomstva cat Pillows with Purée 30 g salmon / crab / beef, 355 each) and 1623 (Trixie Premio Filet Bites with Duck Breast 50 g, 685), all imported the same day; 0507 calcium dental bones 2 pcs 105 g × 1 @ 1,420; **0536 Premio Stripes Lamb × 3 @ 1,215 = the 3 packs on temporary 0029**. 0536 stock after 4 (3 on 0029 − 2 sold 02/11 + 3 here); **0029 turned into a draft 04/11** (user asked) → 0536 stock 1 | posted by Claude, user asked |
| receipt **0031** | 03/11 | Pet House **A1973228940** (02/11, 58,000 incl. VAT): 0018 Monge All Breeds Adult Monoprotein Turkey & Rice 12 kg as **003 × 1 @ 31,000** (last receipt 33,000, −6 %; 31,000 / 12 doesn't fit 2 decimals), 0039 Monge Indoor 10 kg as 303 × 10 @ 2,700. Stock after: 0018 2 bags, 0039 26.74 kg | posted by Claude, user asked |
| receipt **0030** | 03/11 | 0015 Monge All Breeds Adult Salmon & Rice 12 kg **+0.9 kg** (303) at 2,791.67 (= 33,500 / 12, its own cost; 2,512.50), no supplier — other half of issue 0005. File `final/armsoft-2026-11-03/0017-to-0015-fix-receipt-0030.xml`. Stock after 12 kg, so the bag sells whole again | posted by Claude, user asked |
| issue **0005** | 03/11 | 0017 Monge All Breeds Puppy & Junior Salmon & Rice 12 kg **−0.9 kg** (cost 2,625): till sale **0000144 / HDM 127** (03/11, 10,520) rang 0.9 kg under PLU **00009 (0015)** at 3,800; the customer took **0017** (PLU 00011, 3,900). User chose a stock-only fix — **HDM 127 still prints 0015** at 3,420. Stock after 11.1 kg | posted by Claude, user asked |
| return **0000002** | 02/11 | HDM return slip **00000126** against till sale 0000142 (HDM 124, 2,200, rung as cash; the customer paid by card and sale 0000143 / HDM 125 rang it again on card): Felix Adult Cat 1479 Salmon × 2, 1483 Lamb × 4, 1484 Trout × 5. Made at the office, printed at the shop. **Checked 2026-11-03: the return restocks by itself** — journal 1479 / 1483 / 1484 = 20 / 20 / 17, the single real sale counted once; no warehouse receipt needed | made by Claude, user asked |
| receipt **0029** | 02/11 | **settled 04/11: turned into a draft** by Claude (user asked) after 0032 brought the same 3 packs; 0536 stock 1 (the receipt's Մնացորդ panel); delete is the user's. Was **temporary**: 0536 Premio Stripes Lamb 100 g × 3 at 1,215 (3,645), no supplier — 3 packs arrived 02/11, their e-invoice not issued yet (not in the 25/10–02/11 pull; a second pull timed out). Stock after 3 (user: "it should show 3", so issue 0004 stands). When the invoice arrives: receive it as usual, then turn 0029 into a draft (state/open-items.csv) | posted by Claude, user asked |
| receipt **0028** | 02/11 | Pet House **A2847444750** (30/10, 37,000 incl. VAT): 1619 Monge Speciality Line Adult Hypo Salmon & Tuna 15 kg (new good, same day) as 003 × 1 @ 37,000. Stock after 1 bag | posted by Claude, user asked |
| receipt **0027** | 02/11 | Pet House **A4577070686** (01/11, 20,300 incl. VAT): 0010 Acana Bountiful Catch 4.5 kg as 003 × 1 @ 20,300. Stock after 1.444 bags | posted by Claude, user asked |
| receipt **0026** | 02/11 | Pet House **A5514649574** (31/10, 31,000 incl. VAT): 0005 Monge All Breeds Adult Monoprotein Beef & Rice 12 kg as 003 × 1 @ 31,000. Stock after 1.761 bags | posted by Claude, user asked |
| issue **0004** | 02/11 | 0536 Premio Stripes Lamb 100 g −1 (cost 1,215), stock count correction (stock 1 → 0). Comment "Stock count correction: 1 Premio Stripes Lamb 100 g short" | posted by Claude, user asked |
| receipt **0025** | 28/10 | 0300 Carlo tray with rim 38×17×58 grey (Trixie 40121) +1 at 2,560, no supplier — other half of issue 0003 | posted by Claude, user yes |
| issue **0003** | 28/10 | 0302 −1 (cost 2,560): 0302 "Vico Be Eco" was a duplicate of 0300 (seller's tag on the tray: #40121, EAN 4011905401218, user 2026-10-28). Barcode 4011905402116 (Trixie 40211, ours by mistake) removed from 0302; 0302 stays unused. Siruk 1062 "Litter Tray Carlo" (40211) set discontinued, ArmSoft code cleared | posted by Claude, user yes |
| receipt **0024** | 28/10 | Pet House **A1081354321** (23,185 incl. VAT): 1617 Be Eco Vico 6,125 · 1615 Neon M blue 8,000 · 1616 Black Design S cord pink 4,000 · 1618 Color Dots S cord blue 5,060, 1 each | posted by Claude, user yes |
| receipt **0023** | 28/10 | Pet House **A3297411457** (56,500 incl. VAT): 0039 Monge Indoor 10 kg as 303 × 10 @ 2,700; 0043 Monge Medium Adult 15 kg as **003 × 1 @ 29,500** (29,500 / 15 kg doesn't fit 2 decimals). Stock after: 0039 16.74 kg, 0043 1.807 bags (27.1 kg) | posted by Claude, user yes |
| receipt **0022** | 27/10 | Pet House **A1412872447** (103,215 incl. VAT, 39 lines, 72 pcs): 29 existing goods at their last cost + 10 new goods 1605–1614 (imported the same day from `final/armsoft-2026-10-27/new-goods-1605-1614.xml`); 16 Nappy pads 0197 | posted by Claude |
| receipt **0021** | 27/10 | Pet House **A4477972797** (pulled with the e-invoice import, 57,865 incl. VAT): 0237 0238 litter ×1, 0040 Monge Kitten 10 kg (303 × 10 @ 2,700), 0049 Gemon Mini 20 kg (303 × 20 @ 1,000), 1499 Jimmy bed ×1. Bags booked in kg, not as 1 kg. All five already on Siruk, costs equal. User: under half of the order came; the nappy pads were not on it | posted by Claude (made from the XML, not from the e-invoice) |
| receipt **0020** | 27/10 | **settled 27/10: turned into a draft** after 0022 brought the real 16 pads (0197 stock 11 = 16 − 5 sold); delete is the user's. Was **temporary**: 0197 Nappy 60×90 × 8 pcs at 255 (2,040), no supplier — the delivery's e-invoice wasn't issued yet, a customer wanted it; fix when it arrives (state/open-items.csv) | posted by Claude, user asked |
| receipt **0019** | 23/10 | RC pouches: 12 × 625 on 1370 1378 1384 1388 1402 1400 1404 (52,500), the other half of issue 0002 | posted by Claude, user yes |
| issue **0002** | 23/10 | 1 box off each RC box good 1466–1472 (7 × 7,500) | posted by Claude |
| receipt **0018** | 23/10 | duplicates' stock onto the kept codes (10,264.11), other half of issue 0001 | posted |
| issue **0001** | 23/10 | 1 pc off each of the 13 old duplicate codes | posted |
| receipt **0017** | 23/10 | correction: 29 bag goods had been received as 1 kg; adds bag kg − 1 at price 0, per-kg cost on 1449 1451 1455 1456 (104,308.38) | posted |
| receipt **0016** | 22/10 | carriers 1601–1604 again, no supplier, at their **sale** prices (55,500), by narek.outstaffing | **duplicate** (user: carriers came once) — turned into a draft by Claude, **deleted by the user** 23/10; stock 1/1/0/1 |
| receipts 0013, 0014 | 22/10 | identical drafts of the bag fix | deleted by the user |
| receipt **0015** | 19/10 | Pet House A7873718283: carriers 1601–1604, 1 each (34,685) | ok |
| receipts 0011, 0012 | 20/10 | earlier bag fixes for 1461 and 1441 | ok |
| receipt **0009** | 18/10 | Pet House, cites **A3778015660** (204,338.28) | ok — invoice A6840667000 (21/10, 204,334.94) replaces A3778015660; 3.34 rounding |
| receipt **0007** | 01/10 | Zoo Ek A2516757106: RC boxes 1466–1472 at 7,500, bags 1443–1465 | ok (boxes moved by 0002/0019) |
| receipt **A6702909666** | 07/09 | Pet House: Trixie treats by the **kg** (0403 1.8 × 3,935 …) | ok — confirms per-kg cost |
| invoice **A7160667164** | 09/09 | ՅՈՒՆԻՏԵՔ: receipt printer TM-15A, scanner Sunlux XL-9620D, 18 till-paper rolls (156,710) | not stock — accountant books it as equipment |

- **Sale prices 1605–1614** set 2026-10-28 by Claude on the user's code/unit/price list (= Siruk prices): 2,400 · 3,200 · 350/pc · 13,900 · 16,000 · 6,200 · 4,350 · 220/pc · 4,650 · 4,650. Pack unit 004 of the pads 1607/1612 stays unpriced on purpose (user 2026-10-28: pads are sold one by one).

Receipts 0008 (A5393944409: 1496–1500) and 0010 (A9076732801: 1576 1577), both 18/10, checked 2026-10-27: every good is on Siruk.

Supplier codes seen: 0001 = Pet House («ՓԵԹ ՀԱՈՒՍ», ՀՎՀՀ 00169022; hafo.am's
wholesale prices match its invoices — likely the same company, not confirmed), 0005 = Zoo Ek («ԶՈՈ ԷԿՈ»), 000002 = Prestige Food.

## Invoice quantities vs ArmSoft receipts (checked 2026-10-26)

- Every goods line we hold (csv/products.csv + batches/) was compared with
  ArmSoft's supplier receipts and the 26/10 turnover, duplicates folded
  (`runs/2026-10-26/invoice-vs-armsoft-2026-10-26.xlsx`): 1,056 of 1,065
  matched goods agree. ArmSoft's received quantities are right wherever we can check.
- The invoices we have no scan of are all in e-invoicing → Ստացված
  հարկային հաշիվներ (29 invoices, 6,800,818.83). Checked 2026-10-26 on the
  e-invoice's Անվանացուցակ tab (footer = total quantity) against the
  receipts: A6833625890 81/81 lines (one bag each), A2516757106 30/30 (RC,
  one bag each), A2889221052 29, A7772326207 6, A9449097423 12,
  A0969245265 3, A6702909666 181.95 over 170 lines, A1938051747 600 (576
  invoice lines vs 574 receipt lines, same quantity). Every received
  quantity in ArmSoft matches its supplier e-invoice.
- Two goods where our scan transcription says 1 but the e-invoice says 2 (the e-invoice wins; our transcription was wrong):
  0592 (litter scoop L, 4046Tx) and 0773 (comb 22 cm, 23772Tx), both on A1938051747.
- **1456 RC Sterilised 15 kg — the 16 kg traced** (2026-10-26, operations
  journal): 01/10 receipt 0007 +1 (the bag, booked as 1 kg) · 15/10 till
  check 0000042 −1 kg loose (PLU 00088, 4,150) · 23/10 correction 0017 +14 ·
  25/10 till check 0000098 −1 **bag** (unit 003, 60,000 −10 % = 54,000), taken
  as −14 and −1 · 25/10 a **second receipt numbered 0017**, +1 kg at price 0,
  no supplier, no comment, author narek.outstaffing. Only one 15 kg bag ever
  came in. After the 1 kg loose sale the bag was sold whole with 14 kg left
  (likely the opened bag, hence −10 %), and the extra +1 kg covered the
  shortfall. Real: 15 kg in, 15 kg out, stock 0. ArmSoft's 16 kg sold
  overstates it by 1 kg. The user decided (2026-10-26) the +1 kg receipt
  stays as it is.
