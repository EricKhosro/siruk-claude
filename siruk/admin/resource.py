"""A declarative layer over the admin CRUD endpoints: one `Resource` per route family, the plans for
create / update / delete, and `register_crud` for `siruk admin <noun> <verb>`.

Rules: a create is refused before any call when a required key is missing; an update sends the
caller's body as it is (the admin PUT replaces the form) and shows what differs from the record;
translatable records are created in `en`, then updated once per `--lang ru|hy`.
"""
import dataclasses, json, os, urllib.parse

from siruk import client as _client, output
from siruk.admin import guard
from siruk.payload import PayloadError

LANGS = ("en", "ru", "hy")


@dataclasses.dataclass(frozen=True)
class Resource:
    name: str
    path: str
    _: dataclasses.KW_ONLY
    required: tuple = ()
    translatable: bool = False
    deletable: bool = True
    label: str = "name"
    source: str = ""   # the controller / FormRequest the shape was read from
    volatile: tuple = ()   # record keys that change on their own: left out of the code's shown state


def _rows(r):
    return (r.get("data") if isinstance(r, dict) else r) or []


def _query(path, search=None, page=None, params=None):
    q = {k: v for k, v in (params or {}).items() if v is not None}
    if search:
        q["search"] = search
    if page not in (None, "all"):
        q["page"] = page
    return path + ("?" + urllib.parse.urlencode(q, doseq=True) if q else "")


def list_page(res, *, search=None, page=None, params=None, lang=None):
    """The API's own answer for one page."""
    return _client.default().get(_query(res.path, search, page, params), lang=lang)


def list_rows(res, *, search=None, page=None, params=None, lang=None):
    """One page of rows; page="all" walks every page."""
    if page == "all":
        return _client.default().paginate(_query(res.path, search, None, params), lang=lang)
    return _rows(list_page(res, search=search, page=page, params=params, lang=lang))


def _record_path(res, id):
    return f"{res.path}/{_client.quote(id)}"


def _get_raw(res, id, lang=None):
    return _client.default().get(_record_path(res, id), lang=lang)


def get(res, id, lang=None):
    r = _get_raw(res, id, lang) or {}
    return r.get("data", r) if isinstance(r, dict) else r


def _label(res, rec):
    v = (rec or {}).get(res.label)
    return (v.get("en") or next(iter(v.values()), "")) if isinstance(v, dict) else v


def _short(v, n=40):
    s = json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n - 1] + "…"


def _body(res, body):
    if not isinstance(body, dict):
        raise PayloadError(f"the {res.name} body must be a JSON object")
    return body


def plan_create(res, body):
    """(steps, summary, shown_state); refuses a body missing a required key before any call."""
    body = _body(res, body)
    missing = [k for k in res.required if body.get(k) in (None, "")]
    if missing:
        raise PayloadError(f"new {res.name} is missing {', '.join(missing)}"
                           + (f" (see {res.source})" if res.source else ""))
    label = _label(res, body)
    same = []
    if isinstance(label, str) and label:
        try:
            same = [r.get("id") for r in list_rows(res, search=label) if _label(res, r) == label]
        except _client.ApiError:
            same = None   # the list refused a search: the dry run shows no neighbours
    summary = f"create {res.name}" + (f" {label!r}" if label else "")
    return [guard.Step("POST", res.path, body, f"create {res.name}")], summary, {"same_label": same}


_MISSING = object()


def _alias(k):
    """snake_case ↔ camelCase: the form of the key the other side of the API would use."""
    if "_" in k:
        head, *rest = k.split("_")
        return head + "".join(w[:1].upper() + w[1:] for w in rest)
    return "".join("_" + c.lower() if c.isupper() else c for c in k)


def _current(cur, k):
    """The record's value for a sent key, under either spelling; _MISSING when it has neither."""
    return cur[k] if k in cur else cur.get(_alias(k), _MISSING)


def _stable(res, cur):
    skip = {x for k in res.volatile for x in (k, _alias(k))}
    return {k: v for k, v in cur.items() if k not in skip}


def plan_update(res, id, body, lang=None):
    """(steps, summary, shown_state): the summary diffs the keys the body sends against the record."""
    body = _body(res, body)
    cur = get(res, id, lang)
    cur = cur if isinstance(cur, dict) else {}
    seen = {k: _current(cur, k) for k in body}
    changed = [f"{k}: {_short(seen[k])} → {_short(v)}" for k, v in body.items()
               if seen[k] is not _MISSING and seen[k] != v]
    same = [k for k, v in body.items() if seen[k] is not _MISSING and seen[k] == v]
    new = [k for k in body if seen[k] is _MISSING]
    summary = f"update {res.name} {id}" + (f" ({_label(res, cur)})" if _label(res, cur) else "")
    summary += " — " + ("; ".join(changed) if changed else "no sent key differs")
    if same and changed:
        summary += f"; unchanged: {', '.join(same)}"
    if new:
        summary += f"; new/unknown to the record: {', '.join(new)}"
    return [guard.Step("PUT", _record_path(res, id), body, f"update {res.name} {id}")], summary, _stable(res, cur)


def plan_delete(res, id):
    if not res.deletable:
        raise PayloadError(f"{res.name} cannot be deleted from the CLI")
    cur = get(res, id)
    cur = cur if isinstance(cur, dict) else {}
    label = _label(res, cur)
    record = json.dumps(cur, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    if len(record) > 2000:
        record = record[:2000] + "… (truncated; run show --json first)"
    return ([guard.Step("DELETE", _record_path(res, id), None, f"delete {res.name} {id}")],
            f"delete {res.name} {id}" + (f" ({label})" if label else "") + f"\nrecord {record}", _stable(res, cur))


# ------------------------------------------------------------ the commands ----
def _load_body(arg):
    from siruk.cli import _load_json
    try:
        return _load_json(arg)
    except (OSError, ValueError) as e:
        raise PayloadError(f"the body is not JSON: {e}")


def _page_arg(s):
    if s == "all" or s.isdigit():
        return s
    raise PayloadError("--page is a number or 'all'")


def _cell(v):
    return v if v is None or isinstance(v, (str, int, float, bool)) else _short(v)


def _columns(res, rows):
    first = rows[0] if rows else {}
    extra = [k for k, v in first.items() if k not in ("id", res.label) and _cell(v) is v][:4]
    return [("id", "id"), (res.label, res.label), *[(k, k) for k in extra]]


def register_crud(reg, noun, res, *, verbs=("list", "show", "create", "update", "delete"),
                  tier_write="draft", tier_delete="irreversible", roles=""):
    """Register `siruk admin <noun> <verb>` for each verb."""
    def lang_flag(p):
        if res.translatable:
            p.add_argument("--lang", choices=LANGS, help="the language to read / write (default en)")

    def lang_of(a):
        return getattr(a, "lang", None)

    def cmd_list(a):
        if a.json and a.page != "all":
            output.dump(list_page(res, search=a.search, page=a.page, lang=lang_of(a)))
            return 0
        rows = list_rows(res, search=a.search, page=a.page, lang=lang_of(a))
        if a.json:
            output.dump({"data": rows})
            return 0
        output.table([{k: _cell(v) for k, v in r.items()} for r in rows], _columns(res, rows))
        return 0

    def cmd_show(a):
        raw = _get_raw(res, a.id, lang_of(a))
        if a.json:
            output.dump(raw)
            return 0
        rec = raw.get("data", raw) if isinstance(raw, dict) else {}
        output.table([{"field": k, "value": _cell(v)} for k, v in rec.items()],
                     [("field", "field"), ("value", "value")])
        return 0

    def cmd_create(a):
        lang = lang_of(a)
        said = lang or (os.environ.get("SIRUK_LANG") or None if res.translatable else None)
        if said not in (None, "en"):
            raise PayloadError(f"create the {res.name} in en first, then `update --lang {said}`")
        steps, summary, shown = plan_create(res, _load_body(a.body))
        return guard.run(a, steps=steps, summary=summary, tier=tier_write, shown_state=shown,
                         verify=f"siruk admin {noun} list", lang=lang)

    def cmd_update(a):
        steps, summary, shown = plan_update(res, a.id, _load_body(a.body), lang_of(a))
        return guard.run(a, steps=steps, summary=summary, tier=tier_write, shown_state=shown,
                         verify=f"siruk admin {noun} show {a.id}", lang=lang_of(a))

    def cmd_delete(a):
        steps, summary, shown = plan_delete(res, a.id)
        return guard.run(a, steps=steps, summary=summary, tier=tier_delete, shown_state=shown,
                         verify=f"siruk admin {noun} show {a.id}")

    sample = json.dumps({k: "…" for k in res.required or (res.label,)}, ensure_ascii=False)
    one = f"{res.path}/:id"
    if "list" in verbs:
        p = reg.command(("admin", noun, "list"), cmd_list, f"list {noun} (one page, or --page all)",
                        api=[f"GET {res.path}"], roles=roles, example=f"siruk admin {noun} list --search royal")
        p.add_argument("--search")
        p.add_argument("--page", type=_page_arg, help="a page number, or 'all'")
        lang_flag(p)
    if "show" in verbs:
        p = reg.command(("admin", noun, "show"), cmd_show, f"one {res.name}", api=[f"GET {one}"], roles=roles,
                        example=f"siruk admin {noun} show 5")
        p.add_argument("id")
        lang_flag(p)
    if "create" in verbs:
        p = reg.command(("admin", noun, "create"), cmd_create, f"create a {res.name} from a JSON body",
                        api=[f"POST {res.path}"], tier=tier_write, roles=roles,
                        example=f"siruk admin {noun} create '{sample}'")
        p.add_argument("body", help="JSON (file, '-' or inline)")
        lang_flag(p)
    if "update" in verbs:
        p = reg.command(("admin", noun, "update"), cmd_update, f"replace a {res.name}'s form with a JSON body",
                        api=[f"GET {one}", f"PUT {one}"], tier=tier_write, roles=roles,
                        example=f"siruk admin {noun} update 5 '{sample}'")
        p.add_argument("id")
        p.add_argument("body", help="JSON (file, '-' or inline): every field the form sends")
        lang_flag(p)
    if "delete" in verbs and res.deletable:
        p = reg.command(("admin", noun, "delete"), cmd_delete, f"delete a {res.name}",
                        api=[f"GET {one}", f"DELETE {one}"], tier=tier_delete, roles=roles,
                        example=f"siruk admin {noun} delete 5")
        p.add_argument("id")
