"""`siruk admin report|stock|search|algolia`. Shapes come from siruk-web/backend:
routes/admin.php (what exists, EnsureRole groups), Http/Controllers/Admin/Analytics/{AbstractReportController,
Concerns/ParsesDateRange,SearchesReportController,StockStatisticsController}.php (startDate / endDate in d/m/Y; the
report body is `{data}`; an export is an .xlsx download), Services/Analytics/{SalesReportService,PromotionsReportService,
AbstractReportService}.php (report keys, `kpi` = value / previous / change, `period`), Http/Controllers/Admin/Search/*
(playground reads q and engine local|algolia; settings, index and rebuild answer `{data}`),
Http/Requests/Admin/Search/{SearchSynonymRequest,SearchRuleRequest}.php, Http/Controllers/Admin/Catalog/{AlgoliaController,
StockController}.php (`index` reads q, category_id, warehouse_id, status, policy, page, perPage and answers meta.pages)."""
import json, os

import pytest

from siruk import cli, client as C
from siruk.admin import insights

BASE_NAMES = ("overview", "sales", "products", "customers", "promotions", "margin", "searches")


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def writes(fc):
    return [c for c in fc.calls if c[0] != "GET"]


def plan_code(capsys, argv):
    assert run([*argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)["code"]


def kpi(v, p=0, c=0.0):
    return {"value": v, "previous": p, "change": c}


# SalesReportService::report
SALES = {"data": {"period": {"startDate": "01 Oct 2026", "endDate": "31 Oct 2026", "prevStartDate": "01 Sep 2026",
                             "prevEndDate": "30 Sep 2026"},
                  "kpis": {"revenue": kpi(125000, 100000, 25.0), "orders": kpi(12, 10, 20.0)},
                  "chart": [], "by_payment_method": [], "by_platform": []}}
# PromotionsReportService::report
PROMOTIONS = {"data": {"period": SALES["data"]["period"], "kpis": {"discount_total": kpi(5000, 0, 0.0)},
                       "promotions": [], "gifts": []}}


# ------------------------------------------------------------ the manifest ----
def test_every_command_is_registered_and_only_search_and_algolia_writes_are_not_read(capsys):
    assert run(["commands", "--json"]) == 0
    by = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    mine = {n: r for n, r in by.items() if n.startswith(("admin report", "admin stock", "admin search", "admin algolia"))}
    want = {f"admin report {n}" for n in BASE_NAMES} | {"admin report search-queries", "admin stock stats",
            "admin stock dashboard", "admin stock list", "admin search settings show", "admin search settings set",
            "admin search playground", "admin search index show", "admin search index rebuild", "admin algolia status",
            "admin algolia sync", "admin algolia sync-all"}
    want |= {f"admin search {n} {v}" for n in ("synonyms", "rules") for v in ("list", "show", "create", "update", "delete")}
    assert want <= set(mine)
    for n in want:
        r = by[n]
        assert r["backend"] == "admin" and r["api"] and r["roles"] and r["help"] and r["example"], n
    non_read = {n for n in want if by[n]["tier"] != "read"}
    assert non_read == {"admin search settings set", "admin search index rebuild", "admin algolia sync",
                        "admin algolia sync-all", *(f"admin search {n} {v}" for n in ("synonyms", "rules")
                                                    for v in ("create", "update", "delete"))}
    assert by["admin algolia sync"]["tier"] == by["admin algolia sync-all"]["tier"] == "real-world"
    assert by["admin search settings set"]["tier"] == by["admin search index rebuild"]["tier"] == "draft"
    assert by["admin report sales"]["roles"] == "developer, admin, analytics_manager"
    assert by["admin search playground"]["roles"] == "developer, admin"


# ------------------------------------------------------ report parameters ----
def test_sales_report_sends_dates_as_d_m_y(admin_fake, capsys):
    admin_fake.on("GET", "/analytics/sales", SALES)
    assert run(["admin", "report", "sales", "--from", "2026-10-01", "--to", "2026-10-31"]) == 0
    assert admin_fake.calls == [("GET", "/analytics/sales?startDate=01%2F10%2F2026&endDate=31%2F10%2F2026",
                                 {"startDate": "01/10/2026", "endDate": "31/10/2026"})]
    out = capsys.readouterr().out
    assert "revenue" in out and "125000" in out and "startDate" in out


def test_promotions_report_takes_d_m_y_and_sends_nothing_when_no_dates(admin_fake):
    admin_fake.on("GET", "/analytics/promotions", PROMOTIONS)
    assert run(["admin", "report", "promotions", "--from", "05/10/2026"]) == 0
    assert run(["admin", "report", "promotions"]) == 0
    assert [c[2] for c in admin_fake.calls] == [{"startDate": "05/10/2026"}, {}]
    assert admin_fake.calls[1][1] == "/analytics/promotions"


def test_report_json_is_the_api_answer_unmodified(admin_fake, capsys):
    admin_fake.on("GET", "/analytics/sales", SALES)
    assert run(["admin", "report", "sales", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == SALES


@pytest.mark.parametrize("argv", [["--from", "2026-13-01"], ["--from", "2026-10-31", "--to", "2026-10-01"]])
def test_a_bad_date_range_is_refused_before_any_call(admin_fake, argv):
    assert run(["admin", "report", "sales", *argv]) == 1
    assert admin_fake.calls == []


def test_search_queries_params(admin_fake, capsys):
    # SearchReportService::queries returns {data: [queryRow], meta: {total, page, perPage, lastPage}}
    row = {"query": "kitten", "searches": 7, "avg_results": 0, "zero_rate": 100.0,
           "last_searched_at": "2026-10-30 10:00:00", "finds_now": 0}
    admin_fake.on("GET", "/analytics/searches/queries",
                  {"data": [row], "meta": {"total": 1, "page": 1, "perPage": 10, "lastPage": 1}})
    assert run(["admin", "report", "search-queries", "--type", "zero", "--still-failing", "--per-page", "10",
                "--from", "2026-10-01"]) == 0
    assert admin_fake.calls[0][2] == {"startDate": "01/10/2026", "type": "zero", "still_failing": "1", "perPage": "10"}
    assert "kitten" in capsys.readouterr().out
    assert run(["admin", "report", "search-queries", "--type", "top", "--per-page", "4"]) == 1
    assert len(admin_fake.calls) == 1


# ------------------------------------------------------------------ export ----
class _Resp:
    status = 200

    def __init__(self, data, name):
        self._d, self.headers = data, {"Content-Disposition": f'attachment; filename="{name}"'}

    def read(self):
        return self._d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _serve(fc, data, name="sales-report_2026-10-01_2026-10-31.xlsx"):
    seen = []

    def opener(req, timeout=None):
        seen.append(req.full_url)
        return _Resp(data, name)
    fc.opener = opener
    return seen


def test_export_writes_the_bytes_to_the_path_and_prints_it(admin_fake, tmp_path, capsys):
    seen = _serve(admin_fake, b"PK\x03\x04sheet")
    dest = tmp_path / "out" / "sales.xlsx"
    assert run(["admin", "report", "sales", "--export", "-o", str(dest), "--from", "2026-10-01", "--to", "2026-10-31"]) == 0
    assert dest.read_bytes() == b"PK\x03\x04sheet"
    assert capsys.readouterr().out.strip() == str(dest)
    assert seen == ["https://offline.test/api/admin/analytics/sales/export?startDate=01%2F10%2F2026&endDate=31%2F10%2F2026"]


def test_export_into_a_folder_uses_the_servers_file_name(admin_fake, tmp_path, capsys):
    _serve(admin_fake, b"PK\x03\x04sheet")
    assert run(["admin", "report", "sales", "-o", str(tmp_path) + os.sep]) == 0
    assert (tmp_path / "sales-report_2026-10-01_2026-10-31.xlsx").exists()


def test_an_export_that_is_not_an_xlsx_is_not_saved(admin_fake, tmp_path):
    _serve(admin_fake, b"<html>login</html>")
    dest = tmp_path / "x.xlsx"
    assert run(["admin", "report", "sales", "-o", str(dest)]) == 2
    assert not dest.exists()


def test_export_path_defaults_to_runs_today():
    p = insights.export_path(None, "sales", "a.xlsx", today="2026-11-16")
    assert p.endswith(os.path.join("runs", "2026-11-16", "a.xlsx"))
    assert insights.export_path(None, "sales", None, today="2026-11-16").endswith("sales-report.xlsx")


# ------------------------------------------------------------------- stock ----
def test_stock_list_params_and_table(admin_fake, capsys):
    # StockController::variantPayload and index meta
    v = {"id": 9, "product_id": 3, "product_name": "Royal", "name": "2 kg", "label": "2 kg", "sku": "RC-2",
         "sale_mode": None, "available": 4, "status": "low_stock", "policy": "deny", "track_inventory": True,
         "is_purchasable": True, "backordered": 0, "supplier_stock": None, "levels": []}
    admin_fake.on("GET", "/stock", {"data": [{"id": 3, "name": "Royal", "variants": [v]}],
                                    "meta": {"total": 1, "page": 2, "perPage": 25, "pages": 3}})
    assert run(["admin", "stock", "list", "--search", "royal", "--status", "low_stock", "--category", "5",
                "--warehouse", "1", "--policy", "deny", "--page", "2"]) == 0
    assert admin_fake.calls[0][2] == {"q": "royal", "category_id": "5", "warehouse_id": "1", "status": "low_stock",
                                      "policy": "deny", "page": "2"}
    out = capsys.readouterr().out
    assert "RC-2" in out and "page 2 of 3" in out


def test_stock_stats_and_dashboard_are_reads(admin_fake, capsys):
    # StockStatisticsService::all: the dates, sales_per_day, top_selling_variants, low/out_of_stock_alerts
    admin_fake.on("GET", "/stock-statistics", {"data": {"startDate": "01 Oct 2026", "endDate": "31 Oct 2026",
                                                        "prevStartDate": "01 Sep 2026", "prevEndDate": "30 Sep 2026",
                                                        "sales_per_day": [], "top_selling_variants": [],
                                                        "low_stock_alerts": [], "out_of_stock_alerts": []}})
    # StockController::dashboard
    admin_fake.on("GET", "/stock/dashboard", {"summary": {"out_of_stock": 1, "low_stock": 0, "backordered": 0,
                                                          "dropship_ready": 0, "low_stock_threshold": 5,
                                                          "low_stock_grams": 500},
                                              "out_of_stock": [], "low_stock": [], "categories": [],
                                              "truncated": {"out_of_stock": False, "low_stock": False}})
    assert run(["admin", "stock", "stats", "--from", "2026-10-01", "--category", "4"]) == 0
    assert admin_fake.calls[0][2] == {"startDate": "01/10/2026", "categoryId": "4"}
    assert run(["admin", "stock", "dashboard", "--search", "royal", "--category", "4"]) == 0
    assert admin_fake.calls[1][2] == {"q": "royal", "category_id": "4"}
    out = capsys.readouterr().out
    assert "out_of_stock" in out and "sales_per_day" in out
    assert writes(admin_fake) == []


# ------------------------------------------------------------------ search ----
# SearchPlaygroundController::__invoke
PLAYGROUND = {"data": {"query": "royal", "engine": "local", "tookMs": 3, "total": 1, "tokens": [],
                       "rules": [{"id": 1, "query": "royal", "match_type": "exact"}],
                       "results": [{"position": 1, "id": 12, "name": "Royal Canin", "brand": "Royal",
                                    "pinned": True, "why": None}],
                       "hidden": [{"id": 13, "name": "Old"}]}}


def test_playground_params(admin_fake, capsys):
    admin_fake.on("GET", "/search/playground", PLAYGROUND)
    assert run(["admin", "search", "playground", "royal canin", "--engine", "algolia"]) == 0
    assert run(["admin", "search", "playground", " royal "]) == 0
    assert [c[2] for c in admin_fake.calls] == [{"q": "royal canin", "engine": "algolia"}, {"q": "royal"}]
    out = capsys.readouterr().out
    assert "Royal Canin" in out and "hidden by rules" in out


def test_playground_refuses_the_fallback_engine_and_an_empty_query(admin_fake):
    assert run(["admin", "search", "playground", "x", "--engine", "algolia_fallback"]) == 2   # argparse choice
    assert run(["admin", "search", "playground", "   "]) == 1
    assert admin_fake.calls == []


def test_settings_set_is_a_draft_and_sends_only_the_given_keys(admin_fake, capsys):
    # SearchSettings::DEFAULTS; GET adds algolia_configured
    cur = {"engine": "algolia_fallback", "typo_tolerance": True, "min_word_size_1_typo": 4,
           "min_word_size_2_typos": 8, "algolia_configured": False}
    admin_fake.on("GET", "/search-settings", {"data": cur})
    admin_fake.on("PUT", "/search-settings", lambda body: {"data": {**cur, **body}})
    argv = ["admin", "search", "settings", "set", '{"engine": "local", "min_word_size_2_typos": 9}']
    assert run(argv) == 0
    assert "engine: algolia_fallback → local" in capsys.readouterr().out and writes(admin_fake) == []
    code = plan_code(capsys, argv)
    assert run([*argv, "--apply", code]) == 0
    assert writes(admin_fake) == [("PUT", "/search-settings", {"engine": "local", "min_word_size_2_typos": 9})]


@pytest.mark.parametrize("body", ['{"algolia_configured": true}', '{"typo_tolerance": "yes"}', '{"engine": "x"}',
                                  '{"min_word_size_1_typo": 21}', '{}', '[1]'])
def test_settings_set_refuses_a_bad_body_before_any_call(admin_fake, body):
    assert run(["admin", "search", "settings", "set", body]) == 1
    assert admin_fake.calls == []


def test_settings_set_refuses_two_typos_not_longer_than_one_typo(admin_fake):
    admin_fake.on("GET", "/search-settings", {"data": {"min_word_size_1_typo": 4, "min_word_size_2_typos": 8}})
    assert run(["admin", "search", "settings", "set", '{"min_word_size_1_typo": 8}']) == 1
    assert writes(admin_fake) == []


@pytest.mark.parametrize("body", ['{"terms": ["kitten"]}', '{"terms": []}', '{"terms": ["Kitten", "kitten"]}',
                                  '{"terms": [" a ", "A"]}', '{}', '{"terms": "a,b"}', '{"terms": ["a", ""]}'])
def test_a_synonym_with_fewer_than_two_terms_is_refused_before_any_call(admin_fake, body):
    assert run(["admin", "search", "synonyms", "create", body]) == 1
    assert run(["admin", "search", "synonyms", "update", "4", body]) == 1
    assert admin_fake.calls == []


def test_synonym_refusal_names_the_rule(admin_fake, capsys):
    assert run(["admin", "search", "synonyms", "create", '{"terms": ["kitten"]}']) == 1
    assert "SearchSynonymRequest.php" in capsys.readouterr().err


def test_synonym_create_and_update_and_delete_go_through_the_guard(admin_fake, capsys):
    # SearchSynonymResource::toArray
    syn = {"id": 4, "terms": ["kitten", "kitty"], "is_active": True, "createdAt": None, "updatedAt": None}
    admin_fake.on("GET", "/search-synonyms/4", {"data": syn})
    admin_fake.on("POST", "/search-synonyms", {"data": syn})
    admin_fake.on("PUT", "/search-synonyms/4", {"data": syn})
    admin_fake.on("DELETE", "/search-synonyms/4", None)
    create = ["admin", "search", "synonyms", "create", '{"terms": ["kitten", "kitty"]}']
    assert run(create) == 0 and writes(admin_fake) == []
    capsys.readouterr()
    assert run([*create, "--apply", plan_code(capsys, create)]) == 0
    capsys.readouterr()
    update = ["admin", "search", "synonyms", "update", "4", '{"terms": ["kitten", "kitty", "kit"], "is_active": true}']
    assert run([*update, "--apply", plan_code(capsys, update)]) == 0
    capsys.readouterr()
    delete = ["admin", "search", "synonyms", "delete", "4"]
    assert run([*delete, "--apply", plan_code(capsys, delete)]) == 0
    assert [(m, p) for m, p, _ in writes(admin_fake)] == [("POST", "/search-synonyms"), ("PUT", "/search-synonyms/4"),
                                                          ("DELETE", "/search-synonyms/4")]
    assert writes(admin_fake)[1][2] == {"terms": ["kitten", "kitty", "kit"], "is_active": True}


@pytest.mark.parametrize("body", ['{"query": "x", "match_type": "exact"}',
                                  '{"query": "x", "match_type": "like", "pinned_product_ids": [1]}',
                                  '{"match_type": "exact", "pinned_product_ids": [1]}',
                                  '{"query": "x", "match_type": "exact", "pinned_product_ids": [1, 1]}',
                                  '{"query": "x", "match_type": "exact", "hidden_product_ids": ["1"]}'])
def test_a_bad_rule_is_refused_before_any_call(admin_fake, body):
    assert run(["admin", "search", "rules", "create", body]) == 1
    assert admin_fake.calls == []


def test_rule_create_plans_one_post(admin_fake, capsys):
    admin_fake.on("GET", "/search-rules", {"data": []})
    admin_fake.on("POST", "/search-rules", {"data": {"id": 2}})
    argv = ["admin", "search", "rules", "create",
            '{"query": "royal", "match_type": "contains", "pinned_product_ids": [12]}']
    assert run([*argv, "--apply", plan_code(capsys, argv)]) == 0
    assert writes(admin_fake) == [("POST", "/search-rules",
                                   {"query": "royal", "match_type": "contains", "pinned_product_ids": [12]})]


def test_synonyms_and_rules_list_and_show_are_reads(admin_fake, capsys):
    admin_fake.on("GET", "/search-synonyms", {"data": [{"id": 4, "terms": ["a", "b"], "is_active": True}]})
    admin_fake.on("GET", "/search-rules", {"data": [{"id": 2, "query": "royal", "match_type": "exact",
                                                      "pinned_product_ids": [1], "hidden_product_ids": [],
                                                      "note": None, "is_active": True}]})
    admin_fake.on("GET", "/search-rules/2", {"data": {"id": 2, "query": "royal"}})
    assert run(["admin", "search", "synonyms", "list"]) == 0
    assert run(["admin", "search", "rules", "list"]) == 0
    assert run(["admin", "search", "rules", "show", "2"]) == 0
    assert run(["admin", "search", "rules", "show", "x"]) == 1
    out = capsys.readouterr().out
    assert "a, b" in out and "royal" in out
    assert writes(admin_fake) == []


def test_index_show_and_rebuild(admin_fake, capsys):
    # LocalSearchService::status
    status = {"built": True, "builtAt": None, "buildMs": 10, "stale": True, "staleSince": None, "counts": {},
              "vocabulary": 5, "fileKb": 2, "opcache": False}
    admin_fake.on("GET", "/search/index", {"data": status})
    admin_fake.on("POST", "/search/index/rebuild", {"message": "Local index rebuilt.", "data": status})
    assert run(["admin", "search", "index", "show"]) == 0
    assert "stale" in capsys.readouterr().out
    argv = ["admin", "search", "index", "rebuild"]
    assert run(argv) == 0 and writes(admin_fake) == []
    capsys.readouterr()
    assert run([*argv, "--apply", plan_code(capsys, argv)]) == 0
    assert writes(admin_fake) == [("POST", "/search/index/rebuild", None)]


# ----------------------------------------------------------------- algolia ----
def test_algolia_status_is_a_read(admin_fake, capsys):
    # AlgoliaController::status and AlgoliaSyncService::status
    admin_fake.on("GET", "/algolia/status", {"data": {"configured": True, "autoSync": False, "fallbackActive": False,
                                                      "sync": {"state": "idle", "queuedAt": None, "startedAt": None,
                                                               "finishedAt": None, "counts": [], "error": None}}})
    assert run(["admin", "algolia", "status"]) == 0
    assert "autoSync" in capsys.readouterr().out and writes(admin_fake) == []


def test_sync_all_is_a_dry_run_without_apply_and_real_world(admin_fake, capsys):
    admin_fake.on("POST", "/algolia/sync-all", {"message": "Full sync queued.", "data": {"state": "queued"}})
    assert run(["admin", "algolia", "sync-all", "--json"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["dry_run"] is True and plan["tier"] == "real-world"
    assert plan["requests"][0]["method"] == "POST" and plan["requests"][0]["path"] == "/algolia/sync-all"
    assert admin_fake.calls == []
    assert run(["admin", "algolia", "sync-all", "--apply", "deadbeef"]) == 1   # a wrong code sends nothing
    assert admin_fake.calls == []
    assert run(["admin", "algolia", "sync-all", "--apply", plan["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/algolia/sync-all", None)]


def test_sync_one_record_is_real_world_and_checks_type_and_id(admin_fake, capsys):
    admin_fake.on("POST", "/algolia/sync/product/1234", {"message": "Synced to Algolia.", "data": {"pushed": 2}})
    argv = ["admin", "algolia", "sync", "product", "1234"]
    assert run([*argv, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["tier"] == "real-world" and admin_fake.calls == []
    assert run([*argv, "--apply", plan_code(capsys, argv)]) == 0
    assert writes(admin_fake) == [("POST", "/algolia/sync/product/1234", None)]
    assert run(["admin", "algolia", "sync", "product", "12a"]) == 1
    assert run(["admin", "algolia", "sync", "variant", "1"]) == 2   # argparse choice
    assert len(admin_fake.calls) == 1
