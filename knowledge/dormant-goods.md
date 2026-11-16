# Dormant goods — hidden or at 0, and what to do when they come back

Moved here from `state/open-items.csv` on 2026-11-16 (user: close the watch
rows). Newest first. Check this file when a receipt brings in one of these.

- 2026-11-16 — **~70 products have no text source** (Kotoffey, KorMell, Mooor,
  Iv San Bernard Traditional, some Trixie collars/leads): no page prints our
  article or EAN. Closed by the user: the texts stay empty (rule 8) until a
  photo of the back label turns up; then write them from the label. Same for
  SmartBones Peanut Butter Bones (02721S): its text is hafo's (smartbones.eu has
  no page for it). Old watermarked SmartBones media 17572, 17638, 17608 are
  unused (delete only on the user's ask).
- 2026-11-16 — **711536 Derevenskie Lakomstva Duck Wedges 55 g** (product 1331,
  variant 2065, ArmSoft 0488): ArmSoft 0, hafo 0, seller found none on 11/11 →
  Siruk stock set to 0 (correction). When received: back to 10.
  Same check that day: 3176 Premio Pâté Liver already 0 (hafo 0 too); 3156
  Stripes Poultry and 31748 Wheels are 0 in ArmSoft but on hafo (194 / 12), so
  Siruk keeps 10 — reorder candidates for `/hafo-restock`.
- 2026-11-13 — **0470 Derevenskie Lakomstva Veal & Sesame Training Treats 90 g**
  (product 1142, variant 1629, SKU 212836): the last unit was lost (ArmSoft
  issue order 0008), Siruk stock 0, Glovo off. hafo also had 0 on 2026-11-16, so
  0 is right. When a receipt brings it in: the receipt run switches Glovo back
  on (`--on-codes 0470`); set Siruk stock back to 10 by hand
  (`siruk stock set 1629 10`). hafo's price on 2026-11-16 was 2,250 (ours 2,800,
  from nemo) — run `siruk recheck-prices` on it at the restock.
- 2026-10-27 — **Royal Canin pouches never received** (not on any invoice,
  user-approved): products 1252 1254 1255 1259 1260 1261 1265 1266 1267
  discontinued; variants 1850 1852 1856 1868 at stock 0 (products 1256 1258
  1262). If one arrives on an invoice: untick discontinued / receive the stock,
  take it off `state/glovo-exclude.csv`, and re-check the old photo questions for
  1259 (11+ vs 12+) and 1267 (can vs pouch).
