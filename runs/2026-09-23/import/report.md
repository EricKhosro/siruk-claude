# Import 2026-09-23 — the 4 "ready" rows of csv/products.csv (first card-pipeline trial)

Pipeline: `scripts/prepare-run.py` → Sonnet worker (`reference/worker-brief.md`) →
`scripts/validate-card.py` → hand review → `create-product.sh`.

## Brands
- **Dogman — 43** created; logo from dogman.ru header (`wp-content/uploads/logo.png`, ~350 px, low-res — the only one the site has).
- **Inteko — 44** created **without a logo** (`NO_LOGO=1`): no official site exists, only retailers.
- `4 Թաթ` was NOT created — it is Club 4 Paws (17); prepare-run.py now maps it.

## Rows
| Code | Result | Detail |
|---|---|---|
| 03623K | **created — product 1194** "Litter Tray with Mesh", variant M | Inteko; 1700 AMD (register; hafo 1650), cost 1030; leaf 67; `size` = "M, with mesh" (quote: hafo "Ցանցով / Չափս՝ M"); image = hafo watermarked placeholder → `needs-image.csv`; ru/hy OK |
| 61001K | hold | Dogman tray 42.5×31×8 cm: dogman.ru "Туалет большой" is 41×31×7.5 no mesh, magizoo DOGMAN 06222 is 42×31×8 with mesh — neither matches every axis; no hafo listing |
| 147245 | hold | Myau sterilised turkey in sauce 85 g: hafo does not confirm the code, its EAN is off Myau's prefix; separate from 1050 (Adult) or not can't be settled |
| 142535 | hold | Club 4 Paws jelly 85 g: register price 8300 vs cost 225 (36.9×) — SUSPECT, PM to confirm |

All four are in `state/open-items.csv`.

## Trial notes
- The Sonnet worker spent ~125K tokens on 3 rows, mostly printing whole web pages; the brief now forbids that.
- It held 03623K although hafo confirms the code — the brief now says a hafo-confirmed row needs only images/texts and may ship on the hafo placeholder.
- The orchestrator's prompt wrongly said 61001K had a mesh; the brief now says rows.jsonl beats prompt notes.
