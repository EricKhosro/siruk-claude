"""`siruk admin faq-categories|faqs|post-categories|authors|vets|posts <verb>` and `siruk admin pages show|set <slug>`.

A write is a dry run until `--apply <code>`. Rules: create in `en`, then update once per `--lang ru|hy`;
an image is a media id, never a URL. The blog translation script stays as it is; this is the plain CRUD beside it.
"""
import json, os

from siruk import output
from siruk.admin import content, guard, resource as R
from siruk.payload import PayloadError

ROLES = "admin"


def _noun_commands(reg, noun, res):
    def lang_flag(p):
        p.add_argument("--lang", choices=R.LANGS, help="the language to write (default en)")

    def cmd_create(a):
        said = a.lang or os.environ.get("SIRUK_LANG") or None
        if said not in (None, "en"):
            raise PayloadError(f"create the {res.name} in en first, then `update --lang {said}`")
        body = R._load_body(a.body)
        content.check_images(body)
        steps, summary, shown = R.plan_create(res, body)
        return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=shown,
                         verify=f"siruk admin {noun} list", lang=a.lang)

    def cmd_update(a):
        body = R._load_body(a.body)
        if res is content.POSTS:
            body = content.unwrap(body)
        content.check_images(body)
        steps, summary, shown = R.plan_update(res, a.id, body, a.lang)
        if res is content.POSTS:
            content.check_post_update(a.id, body, shown)
        return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=shown,
                         verify=f"siruk admin {noun} show {a.id}", lang=a.lang)

    def cmd_delete(a):
        steps, summary, shown = R.plan_delete(res, a.id)
        note = content.DELETE_NOTES.get(res.path)
        return guard.run(a, steps=steps, summary=summary + (f" — {note}" if note else ""), tier="irreversible",
                         shown_state=shown, verify=f"siruk admin {noun} show {a.id}")

    sample = json.dumps({k: "…" for k in res.required}, ensure_ascii=False)
    update_example = (f"siruk admin {noun} update 5 '{sample}' --lang ru" if res is not content.POSTS else
                      "siruk admin posts show 7 --json > post.json; edit it; siruk admin posts update 7 post.json --lang hy")
    p = reg.command(("admin", noun, "create"), cmd_create, f"create a {res.name} in en from a JSON body",
                    api=[f"GET {res.path}?search=", f"POST {res.path}"], tier="draft", roles=ROLES,
                    example=f"siruk admin {noun} create '{sample}'")
    p.add_argument("body", help="JSON (file, '-' or inline)")
    lang_flag(p)
    p = reg.command(("admin", noun, "update"), cmd_update,
                    f"replace a {res.name}'s form with a JSON body; --lang ru|hy writes that language",
                    api=[f"GET {res.path}/:id", f"PUT {res.path}/:id"], tier="draft", roles=ROLES,
                    example=update_example)
    p.add_argument("id")
    p.add_argument("body", help="JSON (file, '-' or inline): every field the form sends")
    lang_flag(p)
    p = reg.command(("admin", noun, "delete"), cmd_delete, f"delete a {res.name}" + (f" ({content.DELETE_NOTES[res.path]})"
                    if res.path in content.DELETE_NOTES else ""), api=[f"GET {res.path}/:id", f"DELETE {res.path}/:id"],
                    tier="irreversible", roles=ROLES, example=f"siruk admin {noun} delete 5")
    p.add_argument("id")


def _pages(reg):
    def cmd_show(a):
        raw = R._get_raw(content.PAGES, content.page_slug(a.slug), a.lang)
        if a.json:
            output.dump(raw)
            return 0
        rec = raw.get("data", raw) if isinstance(raw, dict) else {}
        output.table([{"field": k, "value": R._cell(v)} for k, v in rec.items()],
                     [("field", "field"), ("value", "value")])
        return 0

    def cmd_set(a):
        slug = content.page_slug(a.slug)
        body = R._load_body(a.body)
        content.check_images(body)
        steps, summary, shown = R.plan_update(content.PAGES, slug, body, a.lang)
        summary += "".join(f"; NOTE {n}" for n in content.page_notes(body))
        return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=shown,
                         verify=f"siruk admin pages show {slug}", lang=a.lang)

    p = reg.command(("admin", "pages", "show"), cmd_show, "one CMS page in one language", api=["GET /pages/:slug"],
                    roles=ROLES, example="siruk admin pages show about-us --lang ru")
    p.add_argument("slug", help=" | ".join(content.PAGE_SLUGS))
    p.add_argument("--lang", choices=R.LANGS, help="the language to read (default en)")
    p = reg.command(("admin", "pages", "set"), cmd_set,
                    "edit a CMS page: the keys sent are written in --lang (default en)",
                    api=["GET /pages/:slug", "PUT /pages/:slug"], tier="draft", roles=ROLES,
                    example="siruk admin pages set faqs '{\"title\": \"…\"}' --lang hy")
    p.add_argument("slug", help=" | ".join(content.PAGE_SLUGS))
    p.add_argument("body", help="JSON (file, '-' or inline): the keys to write")
    p.add_argument("--lang", choices=R.LANGS, help="the language to write (default en)")


def register(reg):
    for noun, res in content.NOUNS.items():
        R.register_crud(reg, noun, res, verbs=("list", "show"), roles=ROLES)
        _noun_commands(reg, noun, res)
    _pages(reg)
