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

## Documents (newest first)

| Doc | Date | What it is | Status |
|---|---|---|---|
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
