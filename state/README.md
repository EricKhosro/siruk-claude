# state/ — what the next run needs

`runs/<date>/` is a run's scratch: logs, plans, backups, per-run reports. It
can be cleared once the run is closed. **`state/` is what outlives a run** —
data a later run reads back, and the one list of what is still open. Scripts
default to these paths; update the files here instead of starting a new copy
in a run folder.

Created 2026-09-23, when the runs up to then were closed and cleared (see
`final-report-2026-09-23.md`).

| File | What it is | Written by | Read by |
|---|---|---|---|
| `open-items.csv` | **The worklist.** Everything still to do, one line per item: area, priority (1 = blocks a sale or breaks a rule, 3 = cosmetic), issue, the register row / article / product / variant it is on, and where it came from. Replaces every old `no-hafo-price` / `not-found` / `needs-image` / `needs-packshot` / `held-rows` / `no-pack-weight` CSV. | rebuilt from the register audit + a live check | you |
| `missing-translations.json` | every product field whose ru/hy text is empty or identical to English (594 on 2026-09-23, 99 products — mostly the 2026-09-15/16 imports' ingredients and feeding guides) | `scripts/verify-translations.py --out` | the translation backlog |
| `import-sources.json` | per article code: the page its name/images/description came from, and the zoovet/nemo/sibling price source where a fallback priced it | collected from every old run report | `scripts/build-import-ledger.py` |
| `fixes-report-2026-09-23.md` | what was fixed after that report, and what is still open and why | 2026-09-23 | you |
| `carried-items.json` | open items no automatic check can re-derive (a picture judged by eye); the worklist rebuild keeps them — delete an entry once fixed | by hand | worklist rebuild |
| `final-report-2026-09-23.md` | the register (`csv/AllAngineProduct.xlsx`) vs the live site, in full | 2026-09-23 | you |
| `register/register.csv` | the register rows: `csv/AllAngineProduct.xlsx`, with `Վաճառքի գին` filled from `csv/Product.numbers` where the xlsx is blank (the two files are otherwise identical) | `scripts/read-register.py` | `match-register.py` |
| `register/register-match.json` | register row → article code from the invoice CSV (exact name, or fuzzy name + equal cost) | `scripts/match-register.py` | `register-status.py` |
| `register/hafo-recovered.json` | register row → article code recovered from hafo by name + cost (network; slow to rebuild) | `scripts/hafo-by-name-cost.py` | `register-status.py` |
| `register/match-overrides.json` | **hand decisions**: register row → article code, overriding the automatic match. Includes every row accepted in `identified-by-name.csv`. | by hand / `identify-by-name.py --accept` | `register-status.py` |
| `register/identified-by-name.csv` | the codeless rows identified by name (rule 6), with source, url and evidence | by hand | `identify-by-name.py --accept` |
| `register/hafo-name-candidates.json` | hafo (+ nemo/zoovet) name-search candidates for the codeless rows — the research for the "identify article code" items | `scripts/identify-by-name.py` | you |
| `register/research-missing.json` | brand-site research (page url, EAN, images, texts) for register rows that are still not live, keyed by article code | 2026-09-16 research | the next import |
| `register/twin-plan.json` | per-kg twins to create | 2026-09-16 | `scripts/make-perkg-twin.py` |
| `register/register-status.json` | per register row: code, where it came from, live or not | `register-status.py` | `register-audit.py`, the planners (`REGISTER_STATUS=`) |
| `register/register-audit.{csv,json}`, `register-ledger.csv`, `register-extras.csv` | the audit: per row exists / price / per-kg / family / completeness; the PM-facing ledger; live variants no register row points at | `register-audit.py` | you, `register-price-sync.py` |

## Re-running the register audit

```bash
scripts/catalogue-snapshot.py --refresh          # live catalogue → .siruk-cache (≈40 min)
scripts/match-register.py                        # defaults to state/register
scripts/register-status.py
scripts/register-audit.py
```

A new register from the PM: `scripts/read-register.py --src <file> --csv
state/register/register.csv`, then the three steps above. Keep
`match-overrides.json` — register numbers (`Կոդ`) have been stable between
versions, and it is the only place the hand decisions live.
