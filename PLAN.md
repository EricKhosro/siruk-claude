# Build Plan — AI Categorization & Import Pipeline v2

Goal: close the gap found in the Chewy taxonomy research — attributes are empty,
products sit in one category, and the tree can't grow without surprises.
Companion docs: `INVESTIGATION.md` (admin API + data source),
Chewy research report (artifact, 2026-08-11).

Work through phases in order; each phase is independently useful.
Check items off as they land.

---

## Phase 0 — Decisions & access (user / PM — nothing blocks Phase 1–4 except ①)

- [x] ① **Confirm source strategy:** brand official sites remain the primary
      source (per `INVESTIGATION.md`). Chewy only as optional enrichment.
      *(Confirmed 2026-08-11.)*
- [x] ② **parse.bot — pilot or skip?** → **Skip.** Keeping current
      browser-script extraction (works today). *(Decided 2026-08-11.)*
- [ ] ③ **Legal/PM sign-off** on automated reading of brand sites (and on any
      Chewy use via third party, if ② includes Chewy).
- [ ] ④ **Request production credentials** from backend team: dedicated
      catalog-only service account + first-party API token (replaces personal
      login + localStorage JWT). Needed before production, not for demo pilot.

## Phase 1 — Attribute foundation (~0.5 day) — ✅ DONE 2026-08-11

- [x] Pull current attributes + values: `GET /api/admin/attributes?forProducts=true`
      and `GET /api/admin/attribute-values` — snapshot in
      `reference/attributes-snapshot-raw.json`.
- [x] Define the vocabularies (borrow Chewy's proven lists from the research
      report):
      - lifestage: puppy/kitten · adult · senior · all
      - breed size (dogs): XS · S · M · L · Giant · all
      - special diet (~10): grain-free · veterinary · weight-control ·
        limited-ingredient · hydrolyzed · low-fat · high-protein · with-grain ·
        organic · indoor (cat)
      - health feature (~10): digestive · joint · skin-coat · urinary ·
        weight · diabetic · kidney · dental · calming · hairball (cat)
      - food form: dry · wet · freeze-dried · topper · supplement
      - texture (wet): pate · chunks-in-gravy · shredded · minced · stew
      - packaging: bag · can · pouch · tray · box · tub
- [x] Write `scripts/seed_attributes.py` — created the Phase-1 values via API.
      *(Script deleted 2026-08-11 after the clean-slate decision — its
      hardcoded vocab was stale. Attribute creation now goes through the
      `/manage-attributes` skill / `attribute-manager` agent, driven by
      `reference/attribute-redesign.md`.)*
- [x] **Done when:** admin UI shows the values; the id map file exists.
      *(24 values created incl. new Health Feature attribute id 16; map
      written from post-create re-fetch. Note: 7 junk/test values exist in
      demo env — listed by the script, left for the team to delete.)*

## Phase 2 — Attribute extraction in the importer — ✅ BUILT 2026-08-11

- [x] Add a classification step to the `add-products` flow: input = CSV row +
      brand-site extract; output = strict JSON over the Phase-1 vocabulary
      (values or null — never free text). *(Implemented as skill instructions
      in `.claude/skills/add-products/SKILL.md` step 6, per user request —
      skill + CLAUDE.md edits only, no standalone scripts.)*
- [x] Map extracted values → ids via `reference/attribute-values.json`; put
      them in the variant's `attribute_value_ids`. *(Skill step 6 + 8; menu
      refresh command documented in CLAUDE.md for after hand-edits.)*
- [x] Confidence gate: inferred (not directly stated) picks are left empty and
      listed in the run report as flagged candidates. Never guess.
- [x] **Done when:** dry run on the POC product (Royal Canin Mini Adult 8kg,
      id 31) yields correct picks — see `runs/2026-08-11-dryrun-demo.md`
      (3 filled with evidence, 2 flagged, rest correctly blank).
- [ ] **Pending:** first live run with attributes (start of Phase 5 pilot) —
      awaiting user go. Open user decisions from the dry run: does
      "maintains healthy weight" count as Weight Management (recommend no)?
      Is "dry kibble → Packaging: Bag" an acceptable auto-fill rule?

## Phase 3 — Category rule table (~0.5 day)

- [ ] Create `reference/category-rules.yaml`; starter rules:
      - pet=dog ∧ food ∧ form=dry → 6 (Dog/Dry) · form=wet → 7 (Dog/Wet)
      - pet=cat ∧ food ∧ form=dry → 8 · form=wet → 9
      - pet=dog ∧ treats → 11
      - form=supplement → 14 (Vitamins & Supplements)
      - product_type=accessory → 15 (Accessories)
      - special_diet ∋ veterinary ∧ pet=dog → **also** 13 (Health Condition)
      - CSV `Category` column always wins if it conflicts (existing rule).
- [ ] Resolver: run all rules over the extracted attributes → collect ALL
      matching ids into `category_ids` (multi-membership is the point).
- [ ] **Done when:** a veterinary dry dog food lands in BOTH 6 and 13.

## Phase 4 — Run report v2 (~0.5 day)

- [ ] Per-row: created / skipped / fallback source used (existing), plus
      fields dropped for low confidence, values the model wanted that aren't
      in the vocabulary (out-of-vocab misses), rows matching no category rule.
- [ ] Emit `runs/<date>-report.md` per import. This file IS the human review
      queue — no UI needed.

## Phase 5 — Pilot, then full import

- [ ] Import top-priority 10 CSV rows end-to-end with Phases 1–4 live.
- [ ] Review the run report together; fix vocab/rules; re-run flagged rows.
- [ ] Full CSV import.
- [ ] Replace the placeholder Stuzzy logo (carried over from 2026-08-10 run).

## Phase 6 — Taxonomy growth job (~1 day)

- [ ] `scripts/propose-categories` — after each import (or nightly): count
      products per attribute combination; flag clusters ≥ 8 products with no
      covering rule, and accumulated out-of-vocab misses (e.g. first bird
      products) → `proposals.md` with product lists as evidence.
- [ ] On human approval: create category via `POST /api/admin/categories`
      (name, parent, slug, drafted SEO meta), append the rule line, re-run the
      resolver to back-fill members.
- [ ] **Guardrail:** categories are never created without approval; proposals
      only.

## Phase 7 — Later / production hardening (as needed)

- [ ] Back-fill script: run Phases 2–3 over products created before this
      pipeline existed.
- [ ] Embedding cross-check: flag products whose categories disagree with
      their nearest already-categorized neighbors.
- [ ] Restructure flat categories (Vitamins, Accessories) under pet types if
      navigation needs it — memberships regenerate from rules, so this is
      cheap.
- [ ] Switch to production env with the Phase-0 service account + token.

---

**Effort:** Phases 1–4 ≈ 2.5 days → Phase 5 pilot → Phase 6 ≈ 1 day.
**Order matters:** 1 → 2 → 3 → 4 → 5 → 6; Phase 0 items ②–④ can run in
parallel; only ① (source strategy) gates the pilot.
