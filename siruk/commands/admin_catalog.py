"""`siruk admin categories|brands|attributes|attribute-values|product-types|price-types|reviews|review-reports`.

Reads come from `register_crud`; every write is a dry run until `--apply <code>`, and runs the noun's
rules (siruk/admin/catalog.py) before the guard. Translatable nouns are created in en, then updated per --lang.
"""
import json, os

from siruk.admin import catalog as C, guard, resource as R
from siruk.payload import PayloadError

ROLES = "developer, admin"   # panel menu (config.js:77); the backend enforces only the Admin middleware
ASK = "Create only on an explicit ask: new attributes, values and categories are not made on the agent's own initiative."


def _body(arg):
    from siruk.cli import _load_json
    try:
        return _load_json(arg)
    except (OSError, ValueError) as e:
        raise PayloadError(f"the body is not JSON: {e}")


def _need_keys(res, body):
    missing = [k for k in res.required if body.get(k) in (None, "")]
    if missing:
        raise PayloadError(f"{res.name} body is missing {', '.join(missing)} (the form is replaced whole; see {res.source})")


def _writes(reg, noun, res, *, verbs=("create", "update", "delete"), body_rule=None, update_rule=None,
            delete_rule=None, note=None, notes=None, example=None, eid=5):
    """create / update / delete for one noun: `R.plan_*` with the noun's rules run before the guard."""
    notes = notes or {}

    def lang_flag(p):
        if res.translatable:
            p.add_argument("--lang", choices=R.LANGS, help="the language to write (create is en; update per language)")

    def create(a):
        lang = getattr(a, "lang", None)
        said = lang or (os.environ.get("SIRUK_LANG") or None if res.translatable else None)
        if said not in (None, "en"):
            raise PayloadError(f"create the {res.name} in en first, then `update --lang {said}`")
        body = _body(a.body)
        if isinstance(body, dict) and body_rule:
            body_rule(body)
        steps, summary, shown = R.plan_create(res, body)
        return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=shown,
                         verify=f"siruk admin {noun} list", lang=lang)

    def update(a):
        lang = getattr(a, "lang", None)
        body = _body(a.body)
        if isinstance(body, dict):
            if body_rule:
                body_rule(body)
            _need_keys(res, body)
        steps, summary, cur = R.plan_update(res, a.id, body, lang)
        if update_rule:
            update_rule(cur, body)
        if note and (extra := note(cur, body)):
            summary += f"; {extra}"
        return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=cur,
                         verify=f"siruk admin {noun} show {a.id}", lang=lang)

    def delete(a):
        steps, summary, cur = R.plan_delete(res, a.id)
        if delete_rule:
            delete_rule(cur)
        return guard.run(a, steps=steps, summary=summary, tier="irreversible", shown_state=cur,
                         verify=f"siruk admin {noun} show {a.id}")

    sample = example or json.dumps({k: "…" for k in res.required or (res.label,)}, ensure_ascii=False)
    one = f"{res.path}/:id"
    if "create" in verbs:
        p = reg.command(("admin", noun, "create"), create,
                        f"create a {res.name} from a JSON body" + (" (only on an explicit ask)" if notes.get("ask") else ""),
                        api=[f"GET {res.path}", f"POST {res.path}"], tier="draft", roles=ROLES,
                        example=f"siruk admin {noun} create '{sample}'")
        p.description = " ".join(filter(None, [notes.get("ask"), notes.get("create")]))
        p.add_argument("body", help="JSON (file, '-' or inline)")
        lang_flag(p)
    if "update" in verbs:
        p = reg.command(("admin", noun, "update"), update, f"replace a {res.name}'s form with a JSON body",
                        api=[f"GET {one}", f"PUT {one}"], tier="draft", roles=ROLES,
                        example=f"siruk admin {noun} update {eid} '{sample}'")
        p.description = notes.get("update", "")
        p.add_argument("id")
        p.add_argument("body", help="JSON (file, '-' or inline): every field the form sends")
        lang_flag(p)
    if "delete" in verbs:
        p = reg.command(("admin", noun, "delete"), delete, f"delete a {res.name}",
                        api=[f"GET {one}", f"DELETE {one}"], tier="irreversible", roles=ROLES,
                        example=f"siruk admin {noun} delete 5")
        p.description = notes.get("delete", "")
        p.add_argument("id")


def register(reg):
    def reads(noun, res):
        R.register_crud(reg, noun, res, verbs=("list", "show"), roles=ROLES)

    reads("categories", C.CATEGORIES)
    _writes(reg, "categories", C.CATEGORIES, body_rule=C.category_body, update_rule=C.category_update,
            delete_rule=C.category_delete,
            notes={"ask": ASK, "create": "image and featured_image are media ids (`siruk media`); a product goes in a leaf.",
                   "update": "image and featured_image are media ids (`siruk media`). A body without list_as_products turns it off.",
                   "delete": "Refused while the category has subcategories, products or promotions; the count is shown."})
    reads("brands", C.BRANDS)
    _writes(reg, "brands", C.BRANDS, body_rule=C.brand_body,
            notes={"create": "image (the logo) is a media id from `siruk media`.",
                   "update": "image (the logo) is a media id from `siruk media`.",
                   "delete": "The API refuses a brand that still has products."})
    reads("attributes", C.ATTRIBUTES)
    _writes(reg, "attributes", C.ATTRIBUTES,
            notes={"ask": ASK, "update": ASK + " `values` replaces the value list: an entry without an id "
                                               "creates a value, and a value in use cannot be left out."})
    reads("attribute-values", C.ATTRIBUTE_VALUES)
    _writes(reg, "attribute-values", C.ATTRIBUTE_VALUES, body_rule=C.value_body,
            notes={"ask": ASK, "create": "value is a lower-case slug; image is a media id."})
    reads("product-types", C.PRODUCT_TYPES)
    _writes(reg, "product-types", C.PRODUCT_TYPES, body_rule=C.product_type_body, note=C.product_type_note,
            notes={"create": "attributes: [{id, role: option|attribute, is_required, is_filterable, show_on_product_card}].",
                   "update": "attributes replaces the set: an attribute left out is detached. Roles and flags: CLAUDE.md 8b-8c.",
                   "delete": "The API refuses a product type that products still use."})
    reads("price-types", C.PRICE_TYPES)
    _writes(reg, "price-types", C.PRICE_TYPES, body_rule=C.price_type_body, update_rule=C.price_type_update,
            delete_rule=C.price_type_delete,
            notes={"create": "code matches ^[a-z0-9-]+$ (up to 40).",
                   "update": "code matches ^[a-z0-9-]+$; the website type is never re-coded or deactivated.",
                   "delete": "Never the website type; a type with prices or order lines is deactivated instead."})
    reads("reviews", C.REVIEWS)
    _writes(reg, "reviews", C.REVIEWS, verbs=("update",), update_rule=C.review_update,
            example='{"is_approved": true, "reply": "…"}', eid=9,
            notes={"update": "is_approved, is_recommended, is_seen, reply. A body without reply clears an existing one, "
                             "and sending a reply re-stamps replied_at and the replier as you. The dry run's read "
                             "marks the review and its reports seen. Reviews have no create or delete in the API."})
    reads("review-reports", C.REVIEW_REPORTS)
    _writes(reg, "review-reports", C.REVIEW_REPORTS, verbs=("update",), example='{"is_resolved": true}', eid=2,
            notes={"update": "is_resolved, is_seen. The dry run's read marks the report seen."})
