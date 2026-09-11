# Attribute translations — admin UI check (2026-09-10)

Goal: translate attribute names and value labels to ru/hy the way the admin UI does.

## What the UI does (captured with Chrome DevTools)
- `/admin/catalog/attributes/edit/16` and `/admin/catalog/attribute-values/edit/25` both show an En/Ru/Hy dropdown.
- Switching it re-fetches `GET /api/admin/attributes/16?isEdit=true` with `Content-Language: ru`.
- Save sends `PUT /api/admin/attributes/16` body `{"locale":"ru","name":…,"code":"toy-size","is_variant":true,"is_filterable":false,"btnType":"saving"}`.
- Value save sends `PUT /api/admin/attribute-values/25` body `{"locale":"ru","attribute_id":3,"value":"puppy","label":…,"color_hex":null,"sort_order":0,"image":null,"btnType":"saving"}`.
- That is exactly the shape `scripts/translate-attributes.py` already uses.

## Result
- After the Russian save, `GET` with `Content-Language` en / ru / hy all returned the Russian text: the backend keeps ONE name per attribute and ONE label per value.
- Both records restored to English (`Toy Size`, `Puppy`) and verified in all three locales.
- No other route exists: `/global-data` has no translation table; public `/api/attributes`, `/api/filters` are 404.

## Conclusion
Attribute names, value labels (and per earlier check, family names, variant labels) cannot be translated with the current backend, from the UI or the API. `reference/translations-attributes.json` (17 attributes, 629 values) is ready; `scripts/translate-attributes.py` will apply it as soon as the backend stores these fields per locale (it probes first and refuses otherwise).

## Ask for the backend team
Make `attributes.name`, `attribute_values.label`, `attribute_families.name` and product-variant `name` translatable the same way `products.name` and `categories.name` are (respect the `locale` key on PUT, `Content-Language` on GET). The admin UI already sends `locale`; no frontend change needed.

## Update — applied (same day, after the backend change)
- Probe passed: a `ru` PUT no longer touches the `en` name/label.
- `scripts/translate-attributes.py` wrote ru + hy for 17 attribute names and 629 value labels; 5 family names written the same way.
- Read-back in en/ru/hy: 0 mismatches, English untouched, family attribute lists intact.
- Log: `runs/2026-09-10/translate-attributes.log`.
- Still single-language on the backend: product-variant `name` (variant selector label).

## Update — applied (same day, after the backend change)
- Probe passed: a `ru` PUT no longer touches the `en` name/label.
- `scripts/translate-attributes.py` wrote ru + hy for 17 attribute names and 629 value labels; 5 family names written the same way.
- Read-back in en/ru/hy: 0 mismatches, English untouched, family attribute lists intact.
- Log: `runs/2026-09-10/translate-attributes.log`.
- Still single-language on the backend: product-variant `name` (variant selector label).
