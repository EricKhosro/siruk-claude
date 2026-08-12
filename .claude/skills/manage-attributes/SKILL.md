---
name: manage-attributes
description: Create or manage Siruk admin attributes, attribute values, and attribute families via the admin JSON API. Use when the user asks to add/create attributes, values, or families, rebuild the attribute system (e.g. from reference/attribute-redesign.md), or refresh the attribute menu file. Never deletes anything without an explicit ask.
argument-hint: [what to create: inline list, a file path, or "from redesign doc"]
---

Create/manage attributes, attribute values, and attribute families in the
Siruk admin. Input (inline list, file path, or "from redesign doc" =
`reference/attribute-redesign.md`):

$ARGUMENTS

Read `CLAUDE.md` first (credentials, API notes). For large batches (>15
creations), delegate to the `attribute-manager` agent instead of doing it
inline — pass it the exact list and these rules.

## API (all verified unless marked)

Base `https://demo-api.siruk.am/api/admin` · header
`Authorization: Bearer <JWT>` · always send a real User-Agent (WAF 403s
`Python-urllib`; curl default is fine).

**Use `scripts/api.sh METHOD PATH [payload.json|-]` for every call** (it handles
auth, status codes and error dumps) and `scripts/ids.sh` to see what exists —
see `scripts/README.md`. The paths below are what to pass it.

- Token: `.siruk-token` in the repo root (gitignored, survives reboots). Verify
  with `scripts/api.sh GET /account`; only if that 401s, re-capture from the
  logged-in SPA via chrome-devtools MCP
  (`JSON.parse(localStorage.access_token).token`) and rewrite that file.
- List: `GET /attributes?forProducts=true` → `{data:[{id,code,name,values:[{id,label,value}]}]}`
- List families: `GET /attribute-families?forProducts=true` → `{data:[{id,name,code,attributes:[...]}]}`
- Create attribute: `POST /attributes` `{code, name}` → `{data:{id,...}}`
  (defaults `isVariant/isFilterable: true`)
- Create value: `POST /attribute-values` `{attribute_id, value, label}` → `{data:{id,...}}`
- Rename attribute: `PUT /attributes/<id>` `{code, name}` (PATCH equivalent) →
  renames in place; value ids/labels and family membership survive, and each
  value's derived `name` re-derives from the new code. Verified 2026-08-12
  (`size`/"Size" → `product-weight`/"Product Weight").
- Create family: **endpoint not yet verified.** Try
  `POST /attribute-families` `{name, code, attribute_ids:[...]}` (also try
  `attributes:[{id,position}]` if that 422s). If both fail, capture the real
  payload from the admin UI network tab while creating one family manually,
  then append the verified shape to CLAUDE.md.
- Delete (only on explicit user ask, see Safety): try
  `DELETE /attribute-values/<id>`, `DELETE /attributes/<id>`,
  `DELETE /attribute-families/<id>` (other admin resources use this pattern;
  products verified → 204).

## Workflow

1. **Parse the request** into a plan: attributes to create (code+name), values
   per attribute (label), families (name + ordered attribute codes).
2. **Fetch existing** attributes+values+families FIRST. Dedupe
   case-insensitively (and ignoring `-`/space differences: "Grain Free" ==
   "Grain-Free"). Existing → skip, report as "already present". Near-match →
   do NOT create; flag for the user ("'Joint Care' vs existing 'Hip & Joint
   Support' — same thing?").
3. **Enforce naming conventions** (from `reference/attribute-redesign.md`):
   kebab-case singular codes; Title Case labels; one spelling per concept;
   weights as `400 g` / `1.5 kg` (dot decimal, space, lowercase unit).
   Auto-fix casing/format silently; flag anything ambiguous instead of
   guessing.
   **Never name an attribute after a brand's word for it** — brands reuse words
   for different concepts (Royal Canin "Size" = breed size, not pack weight).
   Pack weight is `product-weight` / "Product Weight"; **do not (re)create a
   `size` attribute.** Full brand-wording → our-name mapping: table 3 of
   `reference/data-tables.md`.
4. **Create** in order: attributes → values → families (families reference
   attribute ids). Verify each response has an id.
5. **Refresh the menu**: `scripts/refresh-attributes.sh` (regenerates
   `reference/attribute-values.json` from a fresh
   `GET /attributes?forProducts=true`, atomic write).
6. **Report**: table of created (name → id), skipped-as-duplicate,
   flagged near-matches/questions, and any endpoint discoveries appended to
   CLAUDE.md.

## Safety

- **Never delete anything unless the user explicitly asked for deletion in
  this conversation.** Bulk wipes: list exactly what will be deleted and get a
  confirmation first. Check `GET /products` for variants referencing the
  value ids about to be deleted and warn if any.
- Never modify values the user created by hand (rename/merge) without asking.
- Demo junk values (`xlllllrr`, `flavor test`, …) are known — do not touch
  unless asked; never pick them for anything.
- This skill writes to the demo admin. If `SIRUK_API` points anywhere else,
  stop and confirm with the user first.
