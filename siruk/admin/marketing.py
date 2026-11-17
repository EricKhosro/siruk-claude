"""Admin marketing and delivery: promotions, vouchers, segments, campaigns, delivery zones and settings.

Rules: a body missing a required key is refused before any call; money a customer pays or is given is a
multiple of 10 AMD; a campaign is sent only by `campaigns send` (a create/update with status "published"
would send it too, so it is refused). Shapes: siruk-web/backend Http/Controllers/Admin/{Common,Campaign,Inventory}.
"""
import datetime, json, re

from siruk import client as _client
from siruk.admin import guard, resource
from siruk.admin.resource import Resource
from siruk.payload import PayloadError

CTRL = "app/Http/Controllers/Admin/"
PROMOTIONS = Resource("promotion", "/promotions", required=("name", "status"), translatable=True,
                      source=CTRL + "Common/PromotionController.php (validated)")
VOUCHERS = Resource("voucher", "/vouchers", required=("code", "amount"), label="code",
                    source="app/Http/Requests/Admin/Voucher/VoucherStoreRequest.php")
SEGMENTS = Resource("segment", "/segments", required=("name", "rules"), translatable=True,
                    source=CTRL + "Common/SegmentController.php (validated)")
TEMPLATES = Resource("campaign template", "/campaign-templates", required=("name", "template_type"),
                     source=CTRL + "Campaign/CampaignTemplateController.php (store)")
CAMPAIGNS = Resource("campaign", "/campaigns", required=("name", "template_id", "recipients_type"),
                     translatable=True, source=CTRL + "Campaign/CampaignController.php (validationRules)")
ZONES = Resource("delivery zone", "/delivery-zones",
                 required=("name", "type", "geometry", "shipping_cost", "priority"), translatable=True,
                 source="app/Http/Requests/Admin/DeliveryZone/StoreDeliveryZoneRequest.php")
SETTINGS_PATH = "/delivery-settings"
SETTINGS_SOURCE = "app/Services/Delivery/DeliverySettings.php (rules)"
HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


def _amd(body, *keys):
    for k in keys:
        v = body.get(k)
        if isinstance(v, bool) or v in (None, ""):
            continue
        try:
            n = float(v)
        except (TypeError, ValueError):
            continue   # the API refuses a non-number itself
        if n % 10:
            raise PayloadError(f"{k} {v} is not a multiple of 10 AMD (app/Support/Money.php)")


def check_promotion(body):
    if str(body.get("discount_type")).strip() == "fixed":
        _amd(body, "discount_value")
    cfg = body.get("loyalty_tier_config")
    tiers = cfg.get("tiers") if isinstance(cfg, dict) else None
    for t in tiers if isinstance(tiers, list) else ():
        if isinstance(t, dict) and str(t.get("discount_type")).strip() == "fixed":
            _amd(t, "discount_value")


def check_voucher(body):
    _amd(body, "amount")


def check_zone(body):
    if body.get("geometry") is not None and not body.get("type"):
        raise PayloadError("geometry needs type: the server skips the shape rules without it (DeliveryZoneController update)")
    _amd(body, "shipping_cost")


def check_segment(body):
    rules = body.get("rules")
    if rules is None:
        return
    if not isinstance(rules, list) or not rules:
        raise PayloadError("rules must be a non-empty list of {field, operator, value}")
    for i, r in enumerate(rules):
        gone = [k for k in ("field", "operator", "value") if not isinstance(r, dict) or r.get(k) in (None, "")]
        if gone:
            raise PayloadError(f"rules[{i}] is missing {', '.join(gone)} (siruk admin segments fields lists them)")


def refuse_status_on_sent(id, body):
    """A sent or sending campaign cannot be reset to draft from the CLI (that would allow a second send)."""
    if body.get("status") is not None and resource.get(CAMPAIGNS, id).get("status") in ("sending", "sent"):
        raise PayloadError(f"campaign {id} is already sent or sending: its status cannot be changed from the CLI")


def check_campaign(body):
    st = body.get("status")
    if st is not None and not (isinstance(st, str) and st.strip() == "draft"):
        raise PayloadError(f"status {st!r} is not for the CLI: 'published' sends the campaign and 'scheduled' has no "
                           "scheduler; leave status out or use 'draft', then `siruk admin campaigns send`")


# noun, resource, write tier, body check, whether update needs every required key (the delivery-zone update does not)
GROUPS = (("promotions", PROMOTIONS, "real-world", check_promotion, True),
          ("vouchers", VOUCHERS, "real-world", check_voucher, True),
          ("segments", SEGMENTS, "draft", check_segment, True),
          ("campaign-templates", TEMPLATES, "draft", None, True),
          ("campaigns", CAMPAIGNS, "draft", check_campaign, True),
          ("delivery-zones", ZONES, "real-world", check_zone, False))


def refuse_missing(res, body, what):
    """`what` names the call ("new promotion", "promotion 7 update"); an update replaces the form, so the keys it always sends must be there."""
    if not isinstance(body, dict):
        raise PayloadError(f"the {res.name} body must be a JSON object")
    gone = [k for k in res.required if body.get(k) in (None, "")]
    if gone:
        raise PayloadError(f"{what} is missing {', '.join(gone)} (see {res.source})")


# ------------------------------------------- updates that would clear what the body leaves out ----
# Only what PromotionController clears when absent (syncRelations, loyalty config, home_hero_*): the rest, dates
# and media included, stays as the server holds it.
CLEARED_WHEN_ABSENT = ("product_ids", "category_ids", "variant_ids", "attribute_value_ids", "segment_ids", "user_ids",
                       "conflicting_promotion_ids", "gifts", "loyalty_tier_config", "promotion_type", "show_in_home_hero",
                       "home_hero_url", "home_hero_app_url")


def _short(v, n=60):
    t = json.dumps(v, ensure_ascii=False, default=str)
    return t if len(t) <= n else t[:n - 1] + "…"


def _kept(res, cur, body):
    """The record's values for the keys the controller would clear because the body leaves them out."""
    keys = ("product_ids",) if res is SEGMENTS else CLEARED_WHEN_ABSENT
    kept = {k: cur[k] for k in keys if cur.get(k) is not None and k not in body}
    if "gift_product_ids" in body:
        kept.pop("gifts", None)   # the server prefers `gifts` rows when both are sent
    return kept


def plan_merged_update(res, id, body, lang=None):
    """(steps, summary, shown_state): the body over the current record, and every sent key that changes the record."""
    cur = resource.get(res, id, lang)
    cur = cur if isinstance(cur, dict) else {}
    if res is PROMOTIONS and "discount_type" not in body:
        check_promotion({**body, "discount_type": cur.get("discount_type")})
    kept = _kept(res, cur, body)
    changes = []
    for k, v in body.items():
        old = cur.get(k)
        if old == v:
            continue
        gone = v in ([], None, "") and old not in ([], None, "")
        changes.append(f"CLEARS {k} (was {_short(old)})" if gone else f"{k}: {_short(old)} → {_short(v)}")
    summary = f"update {res.name} {id} ({resource._label(res, cur)}) — " + ("; ".join(changes) or "no sent key differs")
    held = [k for k, v in kept.items() if isinstance(v, (list, dict)) and v]
    if held:
        summary += f"; kept from the record: {', '.join(held)}"
    step = guard.Step("PUT", resource._record_path(res, id), {**kept, **body}, f"update {res.name} {id}")
    return [step], summary, cur


def plan_create_promotion(body):
    """Like resource.plan_create, but the same-name look uses forConflicts so gift promotions are seen too."""
    refuse_missing(PROMOTIONS, body, "new promotion")
    try:
        same = [r.get("id") for r in resource.list_rows(PROMOTIONS, params={"forConflicts": 1})
                if resource._label(PROMOTIONS, r) == body["name"]]
    except _client.ApiError:
        same = None
    return ([guard.Step("POST", PROMOTIONS.path, body, "create promotion")],
            f"create promotion {body['name']!r}", {"same_label": same})


# ---------------------------------------------------------- campaigns send ----
SEND_STATE = ("id", "name", "template_type", "subject", "recipients_type", "segment_ids", "user_ids", "status",
              "scheduled_at", "sent_at")


def _segment(id):
    try:   # isShow adds the members: the only count the API offers, before opt-outs and push tokens narrow it
        r = _client.default().get(f"/segments/{_client.quote(id)}?isShow=1") or {}
    except _client.ApiError:
        return {"id": id, "name": None}
    s = r.get("data", r) if isinstance(r, dict) else {}
    members = s.get("customers")
    return {"id": id, "name": resource._label(SEGMENTS, s), "rules_summary": s.get("rules_summary"),
            "members": len(members) if isinstance(members, list) else None}


def plan_send(id):
    """(steps, summary, shown_state): the campaign, who it goes to and its state now; a sending or sent one is refused."""
    cur = resource.get(CAMPAIGNS, id)
    cur = cur if isinstance(cur, dict) else {}
    if cur.get("template_type") == "sms":
        raise PayloadError("the sms channel is not configured in Siruk: sending would only mark the campaign failed")
    status = cur.get("status")
    if status in ("sending", "sent"):
        raise PayloadError(f"campaign {id} is already {status}: the server would ignore a second send")
    segs = [_segment(i) for i in cur.get("segment_ids") or []]
    kind = cur.get("recipients_type")
    if kind == "customer_segment":
        who = "segment " + ", ".join(f"{s['name'] or s['id']!r} ({s['members']} members)" if s.get("members") is not None
                                     else repr(s["name"] or s["id"]) for s in segs) + " (before opt-outs and push tokens)"
    elif kind == "specific_customers":
        who = f"{len(cur.get('user_ids') or [])} named customers"
    else:
        who = "all customers (the API gives no recipient count)"
    note = f" — status {status}"
    if cur.get("sent_at"):
        note += f"; already sent at {cur['sent_at']}: this sends to every recipient again"
    elif status == "failed":
        note += "; failed: this sends to every recipient again"
    summary = f"SEND campaign {id} {cur.get('name')!r} ({cur.get('template_type')}) to {who}{note}"
    state = {**{k: cur.get(k) for k in SEND_STATE}, "segments": segs}
    return [guard.Step("POST", f"/campaigns/{_client.quote(id)}/send", None, f"send campaign {id}")], summary, state


# ------------------------------------------------------- delivery settings ----
def get_settings():
    r = _client.default().get(SETTINGS_PATH) or {}
    return r.get("data", r) if isinstance(r, dict) else {}


def _time(k, v):
    if not (isinstance(v, str) and HHMM.fullmatch(v)):
        raise PayloadError(f"{k} must be HH:MM")


def _day(v):
    try:
        datetime.datetime.strptime(v, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise PayloadError(f"holiday {v!r} must be Y-m-d")


def check_settings(body, cur):
    if not isinstance(body, dict) or not body:
        raise PayloadError("the settings body must be a JSON object with at least one key")
    odd = [k for k in body if k not in cur]
    if odd:
        raise PayloadError(f"unknown delivery setting {', '.join(odd)} (known: {', '.join(cur)}; see {SETTINGS_SOURCE})")
    for k in ("cutoff_time", "crawl_start", "crawl_end"):
        if k in body:
            _time(k, body[k])
    if "stale_after_minutes" in body:
        v = body["stale_after_minutes"]
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 1440:
            raise PayloadError("stale_after_minutes must be a whole number of minutes, 0 to 1440")
    if "holidays" in body:
        h = body["holidays"]
        if not isinstance(h, list) or len(set(map(str, h))) != len(h):
            raise PayloadError("holidays must be a list of distinct Y-m-d dates")
        for d in h:
            _day(d)
    if "non_working_weekdays" in body:
        w = body["non_working_weekdays"]
        if (not isinstance(w, list) or len(set(map(str, w))) != len(w) or len(w) > 6
                or any(isinstance(d, bool) or not isinstance(d, int) or not 1 <= d <= 7 for d in w)):
            raise PayloadError("non_working_weekdays must be at most 6 distinct weekdays, 1 (Monday) to 7")
    merged = {**cur, **body}
    if "crawl_start" in body or "crawl_end" in body:
        if not (isinstance(merged.get("crawl_start"), str) and isinstance(merged.get("crawl_end"), str)
                and merged["crawl_end"] > merged["crawl_start"]):
            raise PayloadError("crawl_end must be after crawl_start")


def plan_settings(body):
    """(steps, summary, shown_state): the PUT carries only the keys sent; the server fills the rest from what is stored."""
    cur = get_settings()
    check_settings(body, cur)
    changed = [f"{k}: {cur.get(k)!r} → {v!r}" for k, v in body.items() if cur.get(k) != v]
    summary = "set delivery settings — " + ("; ".join(changed) if changed else "no sent key differs")
    return [guard.Step("PUT", SETTINGS_PATH, body, "set delivery settings")], summary, cur
