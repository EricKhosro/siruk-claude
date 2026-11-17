"""Admin marketing and delivery. Shapes come from siruk-web/backend: routes/admin.php (Marketing, Delivery),
Http/Controllers/Admin/Common/{Promotion,Voucher,Segment,DeliveryZone}Controller.php, Admin/Campaign/*,
Admin/Inventory/DeliverySettingsController.php, Http/Requests/Admin/{Voucher,DeliveryZone}/*, and the
Resources under Http/Resources/Admin/{Voucher,Campaign,Segment,DeliveryZone}."""
import json

import pytest

from siruk import cli

NOUNS = ("promotions", "vouchers", "segments", "campaign-templates", "campaigns", "delivery-zones")
WRITE_TIER = {"promotions": "real-world", "vouchers": "real-world", "delivery-zones": "real-world",
              "segments": "draft", "campaign-templates": "draft", "campaigns": "draft"}


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def writes(fc):
    return [c for c in fc.calls if c[0] != "GET"]


def plan(capsys, argv):
    assert run([*argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)


# PromotionController::validated (name, status, discount_type, discount_value, applies_to, product_ids, ...)
PROMO = {"name": "Spring sale", "status": "active", "is_auto": True, "discount_type": "percentage",
         "discount_value": 15, "applies_to": "products", "product_ids": [4, 9], "eligibility": "all"}
# SingleVoucherResource::toArray
VOUCHER = {"id": 3, "code": "WELCOME", "amount": 1000.0, "end_date": "2026-12-31 00:00:00",
           "createdAt": "2026-01-02T03:04:05+00:00", "updatedAt": "2026-01-02T03:04:05+00:00"}
# SingleCampaignResource::toArray
CAMPAIGN = {"id": 12, "name": "Winter mail", "template_id": 2, "template_type": "view", "subject": "Hi",
            "recipients_type": "customer_segment", "segment_ids": [4], "user_ids": [], "status": "draft",
            "scheduled_at": None, "sent_at": None, "statistics": {"accepted_count": 0}}
# SingleSegmentResource::toArray; `customers` is there when SegmentController::show has isShow, items per SegmentCustomerResource
SEGMENT = {"id": 4, "name": "Cat owners", "description": None, "rules_summary": "Orders >= 3", "product_ids": [],
           "customers": [{"id": 1, "name": "A", "email": "a@b.am", "orders": 3}, {"id": 2, "name": "B", "email": "c@d.am", "orders": 4}]}
# DeliverySettings::rules and admin-panel-guide.md 6.3 (crawl_start 09:00, crawl_end 22:00)
SETTINGS = {"cutoff_time": "16:00", "non_working_weekdays": [7], "holidays": ["2026-12-31"],
            "stale_after_minutes": 180, "crawl_start": "09:00", "crawl_end": "22:00"}


# ------------------------------------------------------------ the manifest ----
def test_every_noun_and_verb_exists_with_its_tier(capsys):
    assert run(["commands", "--json"]) == 0
    by = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    for noun in NOUNS:
        for verb in ("list", "show", "create", "update", "delete"):
            r = by[f"admin {noun} {verb}"]
            assert r["backend"] == "admin" and r["help"] and r["example"] and r["api"]
        assert by[f"admin {noun} list"]["tier"] == by[f"admin {noun} show"]["tier"] == "read"
        assert by[f"admin {noun} create"]["tier"] == by[f"admin {noun} update"]["tier"] == WRITE_TIER[noun]
        assert by[f"admin {noun} delete"]["tier"] == "irreversible"
    for name, tier in (("admin segments fields", "read"), ("admin campaigns logs", "read"),
                       ("admin campaigns send", "real-world"), ("admin delivery-settings show", "read"),
                       ("admin delivery-settings set", "real-world")):
        r = by[name]
        assert r["tier"] == tier and r["backend"] == "admin" and r["api"] and r["help"] and r["example"]


# --------------------------------------------------------------- writes ----
def test_promotion_create_posts_the_body_and_is_real_world(admin_fake, capsys):
    admin_fake.on("GET", "/promotions", {"data": []}).on("POST", "/promotions", {"data": {"id": 7, **PROMO}})
    argv = ["admin", "promotions", "create", json.dumps(PROMO)]
    p = plan(capsys, argv)
    assert p["tier"] == "real-world" and p["requests"][0]["path"] == "/promotions" and writes(admin_fake) == []
    assert run([*argv, "--apply", p["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/promotions", PROMO)]


def test_voucher_update_puts_the_whole_body_and_shows_the_diff(admin_fake, capsys):
    admin_fake.on("GET", "/vouchers/3", {"data": VOUCHER}).on("PUT", "/vouchers/3", {"data": VOUCHER})
    body = {"code": "WELCOME", "amount": 2000, "end_date": "2026-12-31 00:00:00"}
    argv = ["admin", "vouchers", "update", "3", json.dumps(body)]
    p = plan(capsys, argv)
    assert p["tier"] == "real-world" and "amount: 1000.0 → 2000" in p["summary"] and writes(admin_fake) == []
    assert run([*argv, "--apply", p["code"]]) == 0
    assert writes(admin_fake) == [("PUT", "/vouchers/3", body)]


def test_delivery_settings_set_puts_only_the_keys_sent(admin_fake, capsys):
    admin_fake.on("GET", "/delivery-settings", {"data": SETTINGS}).on("PUT", "/delivery-settings", {"data": SETTINGS})
    argv = ["admin", "delivery-settings", "set", '{"cutoff_time": "15:00", "holidays": ["2026-12-31", "2027-01-01"]}']
    p = plan(capsys, argv)
    assert p["tier"] == "real-world" and "cutoff_time: '16:00' → '15:00'" in p["summary"] and writes(admin_fake) == []
    assert run([*argv, "--apply", p["code"]]) == 0
    assert writes(admin_fake) == [("PUT", "/delivery-settings",
                                   {"cutoff_time": "15:00", "holidays": ["2026-12-31", "2027-01-01"]})]


def test_a_translatable_update_goes_out_with_its_language(admin_fake, capsys):
    admin_fake.on("GET", "/promotions/7", {"data": PROMO}).on("PUT", "/promotions/7", {"data": PROMO})
    argv = ["admin", "promotions", "update", "7", json.dumps({**PROMO, "name": "Весенняя"}), "--lang", "ru"]
    p = plan(capsys, argv)
    assert run([*argv, "--apply", p["code"]]) == 0
    assert admin_fake.langs[-1] == "ru" and writes(admin_fake)[0][2]["name"] == "Весенняя"


# ------------------------------------------------------ campaigns send ----
def send_fake(fc, status="draft"):
    state = {"status": status}
    fc.on("GET", "/campaigns/12", lambda _: {"data": {**CAMPAIGN, **state}})
    fc.on("GET", "/segments/4", {"data": SEGMENT})

    def sent(_):
        state["status"] = "sent"
        return None   # CampaignController::send returns void: an empty 200
    fc.on("POST", "/campaigns/12/send", sent)


def test_campaign_send_dry_run_names_the_campaign_and_its_segment(admin_fake, capsys):
    send_fake(admin_fake)
    p = plan(capsys, ["admin", "campaigns", "send", "12"])
    assert p["tier"] == "real-world" and writes(admin_fake) == []
    assert "Winter mail" in p["summary"] and "'Cat owners' (2 members)" in p["summary"]
    assert ("GET", "/segments/4?isShow=1", {"isShow": "1"}) in admin_fake.calls
    assert p["requests"] == [{"method": "POST", "path": "/campaigns/12/send", "body": None, "label": "send campaign 12"}]


def test_campaign_send_twice_is_refused_the_second_time(admin_fake, capsys):
    send_fake(admin_fake)
    argv = ["admin", "campaigns", "send", "12"]
    first = plan(capsys, argv)["code"]
    assert run([*argv, "--apply", first]) == 0
    assert writes(admin_fake) == [("POST", "/campaigns/12/send", None)]
    assert run([*argv, "--apply", first]) == 1 and run(argv) == 1      # status is now sent: no plan, no second POST
    assert len(writes(admin_fake)) == 1


@pytest.mark.parametrize("state,words", [({"status": "failed"}, "failed: this sends to every recipient again"),
                                         ({"sent_at": "2026-11-01 10:00:00"}, "already sent at 2026-11-01 10:00:00")])
def test_campaign_send_says_when_it_goes_out_again(admin_fake, capsys, state, words):
    send_fake(admin_fake)
    admin_fake.on("GET", "/campaigns/12", {"data": {**CAMPAIGN, **state}})
    assert words in plan(capsys, ["admin", "campaigns", "send", "12"])["summary"]


def test_a_sending_or_sent_campaign_cannot_be_sent(admin_fake):
    for st in ("sending", "sent"):
        admin_fake.on("GET", "/campaigns/12", {"data": {**CAMPAIGN, "status": st}})
        assert run(["admin", "campaigns", "send", "12"]) == 1
    assert writes(admin_fake) == []


def test_campaign_send_refuses_the_unconfigured_sms_channel(admin_fake):
    admin_fake.on("GET", "/campaigns/12", {"data": {**CAMPAIGN, "template_type": "sms"}})
    assert run(["admin", "campaigns", "send", "12"]) == 1 and writes(admin_fake) == []


@pytest.mark.parametrize("status", ["published", " published", "scheduled", "sent", "sending", "failed", ""])
def test_campaign_create_and_update_take_no_status_but_draft(admin_fake, status):
    body = {"name": "x", "template_id": 2, "recipients_type": "all", "status": status}
    assert run(["admin", "campaigns", "create", json.dumps(body)]) == 1
    assert run(["admin", "campaigns", "update", "12", json.dumps(body)]) == 1
    assert admin_fake.calls == []


def test_a_sent_campaign_takes_no_status_at_all(admin_fake):
    body = {"name": "x", "template_id": 2, "recipients_type": "all", "status": "draft"}
    for st in ("sent", "sending"):
        admin_fake.on("GET", "/campaigns/12", {"data": {**CAMPAIGN, "status": st}})
        assert run(["admin", "campaigns", "update", "12", json.dumps(body)]) == 1
    assert writes(admin_fake) == []
    del body["status"]
    assert run(["admin", "campaigns", "update", "12", json.dumps(body)]) == 0   # without a status it is an ordinary dry run


@pytest.mark.parametrize("extra", [{}, {"status": "draft"}, {"status": " draft "}])
def test_a_draft_campaign_body_goes_through(admin_fake, capsys, extra):
    admin_fake.on("GET", "/campaigns", {"data": []})
    body = {"name": "x", "template_id": 2, "recipients_type": "all", **extra}
    assert plan(capsys, ["admin", "campaigns", "create", json.dumps(body)])["tier"] == "draft"


# --------------------------------------------------------------- refusals ----
CREATE_MISSING = [("promotions", {"status": "active"}), ("promotions", {"name": "x"}),
                  ("vouchers", {"code": "A"}), ("vouchers", {"amount": 1000}),
                  ("segments", {"name": "x"}), ("campaign-templates", {"name": "x"}),
                  ("campaigns", {"name": "x", "template_id": 2}),
                  ("delivery-zones", {"name": "x", "type": "circle", "geometry": {}, "shipping_cost": 500})]


@pytest.mark.parametrize("noun,body", CREATE_MISSING)
def test_create_missing_a_required_key_is_refused_before_any_call(admin_fake, noun, body):
    assert run(["admin", noun, "create", json.dumps(body)]) == 1
    assert admin_fake.calls == []


@pytest.mark.parametrize("noun,body", [c for c in CREATE_MISSING if c[0] != "delivery-zones"])
def test_update_missing_a_required_key_is_refused_before_any_call(admin_fake, noun, body):
    assert run(["admin", noun, "update", "3", json.dumps(body)]) == 1
    assert admin_fake.calls == []


def test_a_delivery_zone_update_with_geometry_but_no_type_is_refused(admin_fake):
    assert run(["admin", "delivery-zones", "update", "2", '{"geometry": {"center": {"lat": 40.1, "lng": 44.5}, "radius": 9}}']) == 1
    assert admin_fake.calls == []


def test_a_delivery_zone_update_may_send_part_of_the_form(admin_fake, capsys):
    # DeliveryZoneResource::toArray; UpdateDeliveryZoneRequest makes every key `sometimes`
    zone = {"id": 2, "name": "Yerevan", "type": "circle", "shipping_cost": 500, "priority": 3}
    admin_fake.on("GET", "/delivery-zones/2", {"data": zone})   # DeliveryZoneResource::toArray
    p = plan(capsys, ["admin", "delivery-zones", "update", "2", '{"shipping_cost": 600}'])
    assert p["requests"][0]["body"] == {"shipping_cost": 600} and p["tier"] == "real-world"
    assert run(["admin", "delivery-zones", "update", "2", '{"geometry": {"radius": 9}}']) == 1   # no type: the server skips the shape rules


# VoucherStoreRequest, PromotionController::validated (loyalty_tier_config.tiers.*), StoreDeliveryZoneRequest (geometry.center/radius),
# SegmentController::validated (rules.*.field/operator/value)
@pytest.mark.parametrize("argv", [
    ["vouchers", "create", '{"code": "A", "amount": 1005}'],
    ["promotions", "create", json.dumps({**PROMO, "discount_type": " fixed ", "discount_value": 1234})],
    ["promotions", "create", json.dumps({**PROMO, "discount_type": "fixed", "discount_value": 1234})],
    ["promotions", "create", json.dumps({**PROMO, "promotion_type": "loyalty_levels", "loyalty_tier_config": {
        "tiers": [{"order_count": 3, "discount_type": "fixed", "discount_value": 505}]}})],
    ["delivery-zones", "create", json.dumps({"name": "Z", "type": "circle", "geometry": {"center": {"lat": 40.1, "lng": 44.5},
                                                                                         "radius": 3000},
                                             "shipping_cost": 555, "priority": 2})],
    ["segments", "create", '{"name": "x", "rules": []}'],
    ["segments", "create", '{"name": "x", "rules": [{"field": "orders_count"}]}']])
def test_a_body_the_rules_refuse_sends_nothing(admin_fake, argv):
    assert run(["admin", *argv]) == 1 and admin_fake.calls == []


def test_a_percentage_discount_is_not_held_to_ten_dram(admin_fake, capsys):
    admin_fake.on("GET", "/promotions", {"data": []})
    assert plan(capsys, ["admin", "promotions", "create", json.dumps({**PROMO, "discount_value": 15})])["tier"] == "real-world"


@pytest.mark.parametrize("body", [
    "{}", '{"nope": 1}', '{"cutoff_time": "4pm"}', '{"stale_after_minutes": 2000}', '{"holidays": ["31/12/2026"]}',
    '{"holidays": ["2026-12-31", "2026-12-31"]}', '{"non_working_weekdays": [8]}',
    '{"non_working_weekdays": [1, 2, 3, 4, 5, 6, 7]}', '{"crawl_end": "08:00"}'])
def test_delivery_settings_set_refuses_what_the_server_would(admin_fake, body):
    admin_fake.on("GET", "/delivery-settings", {"data": SETTINGS})
    assert run(["admin", "delivery-settings", "set", body]) == 1 and writes(admin_fake) == []


# ------------------------------------------------------------- dry runs ----
def test_dry_runs_write_nothing(admin_fake, capsys):
    admin_fake.on("GET", "/vouchers", {"data": []}).on("GET", "/vouchers/3", {"data": VOUCHER})
    admin_fake.on("GET", "/delivery-settings", {"data": SETTINGS})
    send_fake(admin_fake)
    for argv in (["vouchers", "create", '{"code": "NEW", "amount": 500}'], ["vouchers", "delete", "3"],
                 ["vouchers", "update", "3", '{"code": "WELCOME", "amount": 500}'],
                 ["delivery-settings", "set", '{"stale_after_minutes": 60}'], ["campaigns", "send", "12"]):
        assert run(["admin", *argv]) == 0
    assert writes(admin_fake) == [] and "nothing sent" in capsys.readouterr().out


def test_a_voucher_delete_is_irreversible_and_a_wrong_code_sends_nothing(admin_fake, capsys):
    admin_fake.on("GET", "/vouchers/3", {"data": VOUCHER}).on("DELETE", "/vouchers/3", None)
    assert plan(capsys, ["admin", "vouchers", "delete", "3"])["tier"] == "irreversible"
    assert run(["admin", "vouchers", "delete", "3", "--apply", "deadbeef"]) == 1 and writes(admin_fake) == []


# ---------------------------------------------------------------- reads ----
def test_segment_fields_logs_and_settings_are_reads(admin_fake, capsys):
    # SegmentController::fields
    admin_fake.on("GET", "/segments/fields", {"data": [{"id": "orders_count", "label": "Orders", "help": "h",
                                                        "type": "number", "options": None,
                                                        "operators": [{"id": ">=", "name": "at least"}]}]})
    assert run(["admin", "segments", "fields"]) == 0
    assert "orders_count" in capsys.readouterr().out
    # CampaignRecipientLogResource::toArray
    admin_fake.on("GET", "/campaigns/search-logs", {"data": [{"campaign_id": 12, "recipient": "a@b.am", "user_name": "A",
                                                              "accepted_at": "-", "delivered_at": "-", "failed_at": "-"}]})
    assert run(["admin", "campaigns", "logs", "12", "--search", "a@b"]) == 0
    assert "a@b.am" in capsys.readouterr().out
    assert admin_fake.calls[-1] == ("GET", "/campaigns/search-logs?campaign_id=12&search=a%40b", {"campaign_id": "12", "search": "a@b"})
    admin_fake.on("GET", "/delivery-settings", {"data": SETTINGS})
    assert run(["admin", "delivery-settings", "show"]) == 0
    assert "cutoff_time" in capsys.readouterr().out
    assert run(["admin", "delivery-settings", "show", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"data": SETTINGS} and writes(admin_fake) == []


# ------------------------------------------------- updates that keep what the body leaves out ----
# PromotionResource::toArray (the show the update reads); relation lists are the request keys PromotionController::syncRelations reads
RECORD = {**PROMO, "id": 7, "code": None, "slug": "spring", "is_live": True, "runtime_status": "live", "schedule_summary": "-",
          "message": "m", "priority": 0, "discount_type": "fixed", "discount_value": 500, "promotion_type": "regular",
          "show_in_home_hero": True, "home_hero_url": "/spring", "home_hero_desktop_en": 31, "loyalty_tier_config": None,
          "product_ids": [4, 9], "category_ids": [2], "variant_ids": [], "attribute_value_ids": [], "segment_ids": [4],
          "user_ids": [], "gift_product_ids": [8], "gifts": [{"product_id": 8, "product_variant_id": None}],
          "conflicting_promotion_ids": [3], "createdAt": "x", "updatedAt": "y"}


# the keys PromotionController clears when the request leaves them out, as the show returns them
KEPT_FROM_RECORD = {"product_ids", "category_ids", "variant_ids", "attribute_value_ids", "segment_ids", "user_ids",
                    "conflicting_promotion_ids", "gifts", "promotion_type", "show_in_home_hero", "home_hero_url"}


def promo_fake(fc, rec=RECORD):
    fc.on("GET", "/promotions/7", lambda _: {"data": rec}).on("PUT", "/promotions/7", {"data": rec})


def test_a_partial_promotion_update_sends_the_record_under_the_body(admin_fake, capsys):
    promo_fake(admin_fake)
    p = plan(capsys, ["admin", "promotions", "update", "7", '{"name": "Spring sale", "status": "inactive"}'])
    body = p["requests"][0]["body"]
    assert body["status"] == "inactive" and body["name"] == "Spring sale"
    for k in ("product_ids", "category_ids", "variant_ids", "segment_ids", "conflicting_promotion_ids", "gifts",
              "promotion_type", "home_hero_url", "show_in_home_hero"):
        assert body[k] == RECORD[k], k
    assert set(body) == {"name", "status", *KEPT_FROM_RECORD}
    assert "status: 'active'" in p["summary"] or 'status: "active"' in p["summary"]
    assert "kept from the record: product_ids" in p["summary"] and "CLEARS" not in p["summary"]


def test_dates_and_media_are_not_echoed_back(admin_fake, capsys):
    # PromotionResource returns start_date/end_date as UTC ISO with Z; the model stores them without converting the zone
    rec = {**RECORD, "start_date": "2026-03-01T20:00:00.000000Z", "end_date": "2026-03-31T20:00:00.000000Z",
           "deal_tab_icon": 5, "home_hero_desktop_hy": 6, "home_hero_mobile_en": 7}
    promo_fake(admin_fake, rec)
    body = plan(capsys, ["admin", "promotions", "update", "7", '{"name": "n", "status": "active"}'])["requests"][0]["body"]
    assert not {"start_date", "end_date", "deal_tab_icon", "home_hero_desktop_hy", "home_hero_mobile_en",
                "home_hero_desktop_en", "discount_value", "code", "message"} & set(body)
    assert body["product_ids"] == [4, 9] and body["segment_ids"] == [4]


def test_a_relation_sent_empty_is_shown_as_cleared(admin_fake, capsys):
    promo_fake(admin_fake)
    argv = ["admin", "promotions", "update", "7", '{"name": "Spring sale", "status": "active", "product_ids": []}']
    p = plan(capsys, argv)
    assert "CLEARS product_ids (was [4, 9])" in p["summary"]
    assert p["requests"][0]["body"]["product_ids"] == [] and p["requests"][0]["body"]["segment_ids"] == [4]
    assert run([*argv, "--apply", p["code"]]) == 0
    assert writes(admin_fake)[0][2]["product_ids"] == [] and writes(admin_fake)[0][2]["gifts"] == RECORD["gifts"]


def test_the_promotion_update_code_follows_the_record(admin_fake, capsys):
    argv = ["admin", "promotions", "update", "7", '{"name": "Spring sale", "status": "active"}']
    promo_fake(admin_fake)
    first = plan(capsys, argv)["code"]
    promo_fake(admin_fake, {**RECORD, "segment_ids": [4, 5]})
    assert run([*argv, "--apply", first]) == 1 and writes(admin_fake) == []
    capsys.readouterr()
    assert plan(capsys, argv)["code"] != first


def test_gift_product_ids_in_the_body_stop_the_record_gifts_overriding_them(admin_fake, capsys):
    promo_fake(admin_fake)
    p = plan(capsys, ["admin", "promotions", "update", "7", '{"name": "n", "status": "active", "gift_product_ids": [1]}'])
    assert "gifts" not in p["requests"][0]["body"] and p["requests"][0]["body"]["gift_product_ids"] == [1]


def test_a_discount_value_alone_is_held_to_the_records_fixed_type(admin_fake):
    promo_fake(admin_fake)
    assert run(["admin", "promotions", "update", "7", '{"name": "n", "status": "active", "discount_value": 505}']) == 1
    assert writes(admin_fake) == []


# SingleSegmentResource::toArray; SegmentController::update syncs product_ids from the request
def test_a_segment_update_keeps_its_products(admin_fake, capsys):
    rec = {**SEGMENT, "rules": [{"field": "orders_count", "operator": ">=", "value": 3}], "product_ids": [4, 9]}
    admin_fake.on("GET", "/segments/4", {"data": rec})
    p = plan(capsys, ["admin", "segments", "update", "4", '{"name": "Cat owners", "rules": [{"field": "orders_count", '
                                                          '"operator": ">=", "value": 5}]}'])
    assert p["requests"][0]["body"]["product_ids"] == [4, 9] and "kept from the record: product_ids" in p["summary"]
    p = plan(capsys, ["admin", "segments", "update", "4", '{"name": "Cat owners", "rules": [{"field": "orders_count", '
                                                          '"operator": ">=", "value": 3}], "product_ids": []}'])
    assert "CLEARS product_ids (was [4, 9])" in p["summary"]


# ------------------------------------------------------------- gift promotions ----
def test_a_gift_promotion_counts_in_the_same_name_check_and_the_gift_list(admin_fake, capsys):
    # PromotionController::index: gifts are left out unless onlyGifts, and forConflicts returns every type
    admin_fake.on("GET", "/promotions", {"data": [{"id": 11, "name": "Spring sale", "discount_type": "gift"}]})
    p = plan(capsys, ["admin", "promotions", "create", json.dumps(PROMO)])
    assert admin_fake.calls[0][:2] == ("GET", "/promotions?forConflicts=1") and p["code"]
    admin_fake.on("GET", "/promotions", {"data": [{"id": 11, "name": "Free toy", "status": "active", "discount_type": "gift"}]})
    assert run(["admin", "promotions", "list", "--gifts"]) == 0
    assert admin_fake.calls[-1][:2] == ("GET", "/promotions?onlyGifts=1") and "Free toy" in capsys.readouterr().out


def test_a_promotion_create_in_another_language_is_refused(admin_fake):
    assert run(["admin", "promotions", "create", json.dumps(PROMO), "--lang", "ru"]) == 1 and admin_fake.calls == []


def test_the_list_help_does_not_promise_a_search_the_api_ignores(capsys):
    assert run(["commands", "--json"]) == 0
    by = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    for noun in ("promotions", "vouchers", "delivery-zones"):
        assert "--search" not in by[f"admin {noun} list"]["example"] and "ignores --search" in by[f"admin {noun} list"]["help"]
    assert "GET /segments/:id?isShow=1" in by["admin campaigns send"]["api"]
