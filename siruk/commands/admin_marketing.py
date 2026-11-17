"""`siruk admin promotions|vouchers|segments|campaign-templates|campaigns|delivery-zones ...` and
`delivery-settings show|set`, `segments fields`, `campaigns logs|send`.

Writes go through the admin guard; a promotion, voucher, delivery zone or setting write and a campaign send
reach customers, so they are "real-world". Rules and shapes: siruk/admin/marketing.py.
"""
import json, os, urllib.parse

from siruk import client as _client, output
from siruk.admin import guard, marketing as M, resource
from siruk.payload import PayloadError

ROLES = "admin"
LOG_COLUMNS = [("recipient", "recipient"), ("user_name", "name"), ("accepted_at", "accepted"),
               ("delivered_at", "delivered"), ("opened_at", "opened"), ("failed_at", "failed")]


NO_SEARCH = {"promotions", "vouchers", "delivery-zones"}   # their index ignores `search`
GIFT_COLUMNS = [("id", "id"), ("name", "name"), ("status", "status"), ("discount_type", "discount_type")]


def cmd_gifts(a):
    """`promotions list --gifts`: the index hides gift promotions unless onlyGifts is sent."""
    params = {"onlyGifts": 1}
    if a.json:
        output.dump(resource.list_page(M.PROMOTIONS, params=params))
        return 0
    output.table(resource.list_rows(M.PROMOTIONS, params=params), GIFT_COLUMNS)
    return 0


class _Checked:
    """`register_crud` talks to `reg.command` only: put the body rules in front of create and update."""

    def __init__(self, reg, noun, res, check, update_needs_all):
        self.reg, self.noun, self.res, self.check, self.all = reg, noun, res, check, update_needs_all

    def command(self, path, fn, help, **kw):
        verb = path[-1]
        if verb in ("create", "update"):
            fn = self._ruled(verb, fn, kw["tier"])
        if verb == "list" and self.noun in NO_SEARCH:
            help = f"list {self.noun} (all of them: the API ignores --search)"
            kw["example"] = f"siruk admin {self.noun} list" + (" --gifts" if self.res is M.PROMOTIONS else "")
        if verb == "list" and self.res is M.PROMOTIONS:
            fn = lambda a, plain=fn: cmd_gifts(a) if a.gifts else plain(a)
        p = self.reg.command(path, fn, help, **kw)
        if verb == "list" and self.res is M.PROMOTIONS:
            p.add_argument("--gifts", action="store_true", help="the gift promotions, which the plain list hides")
        return p

    def _ruled(self, verb, fn, tier):
        def run(a):
            body = resource._load_body(a.body)
            a.body = json.dumps(body, ensure_ascii=False)   # stdin is read once; the plan reads the same body
            if not isinstance(body, dict):
                return fn(a)
            if verb == "update" and self.all:
                M.refuse_missing(self.res, body, f"{self.res.name} {a.id} update")
            if self.check:
                self.check(body)
            lang = getattr(a, "lang", None)
            if verb == "update" and self.res is M.CAMPAIGNS:
                M.refuse_status_on_sent(a.id, body)
            if verb == "update" and self.res in (M.PROMOTIONS, M.SEGMENTS):
                steps, summary, shown = M.plan_merged_update(self.res, a.id, body, lang)
                return guard.run(a, steps=steps, summary=summary, tier=tier, shown_state=shown,
                                 verify=f"siruk admin {self.noun} show {a.id}", lang=lang)
            if verb == "create" and self.res is M.PROMOTIONS:
                said = lang or os.environ.get("SIRUK_LANG") or None
                if said not in (None, "en"):
                    raise PayloadError(f"create the promotion in en first, then `update --lang {said}`")
                steps, summary, shown = M.plan_create_promotion(body)
                return guard.run(a, steps=steps, summary=summary, tier=tier, shown_state=shown,
                                 verify=f"siruk admin {self.noun} list", lang=lang)
            return fn(a)
        return run


def cmd_fields(a):
    r = _client.default().get("/segments/fields")
    if a.json:
        output.dump(r)
        return 0
    rows = [{"id": f.get("id"), "label": f.get("label"), "type": f.get("type"),
             "operators": ", ".join(str(o.get("id")) for o in f.get("operators") or [])}
            for f in (r.get("data") if isinstance(r, dict) else r) or []]
    output.table(rows, [("id", "id"), ("label", "label"), ("type", "type"), ("operators", "operators")])
    return 0


def cmd_logs(a):
    q = {"campaign_id": a.campaign_id, **({"search": a.search} if a.search else {})}
    r = _client.default().get("/campaigns/search-logs?" + urllib.parse.urlencode(q))
    if a.json:
        output.dump(r)
        return 0
    output.table((r.get("data") if isinstance(r, dict) else r) or [], LOG_COLUMNS)
    return 0


def cmd_send(a):
    steps, summary, shown = M.plan_send(a.id)
    return guard.run(a, steps=steps, summary=summary, tier="real-world", shown_state=shown,
                     verify=f"siruk admin campaigns show {a.id}")


def cmd_settings_show(a):
    r = _client.default().get(M.SETTINGS_PATH)
    if a.json:
        output.dump(r)
        return 0
    rec = r.get("data", r) if isinstance(r, dict) else {}
    output.table([{"field": k, "value": json.dumps(v, ensure_ascii=False)} for k, v in rec.items()],
                 [("field", "field"), ("value", "value")])
    return 0


def cmd_settings_set(a):
    steps, summary, shown = M.plan_settings(resource._load_body(a.body))
    return guard.run(a, steps=steps, summary=summary, tier="real-world", shown_state=shown,
                     verify="siruk admin delivery-settings show")


def register(reg):
    for noun, res, tier, check, update_needs_all in M.GROUPS:
        resource.register_crud(_Checked(reg, noun, res, check, update_needs_all), noun, res, tier_write=tier, roles=ROLES)

    reg.command(("admin", "segments", "fields"), cmd_fields, "the fields and operators a segment rule may use",
                api=["GET /segments/fields"], roles=ROLES, example="siruk admin segments fields")
    p = reg.command(("admin", "campaigns", "logs"), cmd_logs, "who a campaign went to and what happened to it",
                    api=["GET /campaigns/search-logs"], roles=ROLES, example="siruk admin campaigns logs 12 --search @gmail")
    p.add_argument("campaign_id")
    p.add_argument("--search", help="part of the recipient")
    p = reg.command(("admin", "campaigns", "send"), cmd_send, "send a campaign to its recipients, for real",
                    api=["GET /campaigns/:id", "GET /segments/:id?isShow=1", "POST /campaigns/:id/send"], tier="real-world",
                    roles=ROLES, example="siruk admin campaigns send 12")
    p.add_argument("id")
    reg.command(("admin", "delivery-settings", "show"), cmd_settings_show,
                "cut-off time, non-working days, holidays and the stale-stock window",
                api=["GET /delivery-settings"], roles=ROLES, example="siruk admin delivery-settings show")
    p = reg.command(("admin", "delivery-settings", "set"), cmd_settings_set,
                    "change the delivery promise settings (only the keys sent)",
                    api=["GET /delivery-settings", "PUT /delivery-settings"], tier="real-world",
                    roles=ROLES, example="siruk admin delivery-settings set '{\"cutoff_time\": \"15:00\"}'")
    p.add_argument("body", help="JSON (file, '-' or inline): cutoff_time, stale_after_minutes, crawl_start, "
                                "crawl_end, holidays, non_working_weekdays")
