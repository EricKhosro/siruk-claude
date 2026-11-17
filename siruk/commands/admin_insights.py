"""`siruk admin report|stock|search|algolia …` — the admin's reports and exports, the stock views, and the search admin.

Reads never write. Search settings, synonyms, rules and the index rebuild are drafts; `algolia sync` and
`sync-all` write to Algolia, so they are real-world and a dry run until `--apply <code>`.
Shapes: siruk-web/backend/routes/admin.php and Http/Controllers/Admin/{Analytics,Search,Catalog}.
"""
import os, urllib.parse

from siruk import client as _client, output
from siruk.admin import guard, insights as ins, resource
from siruk.payload import PayloadError

ANALYTICS = "developer, admin, analytics_manager"   # EnsureRole on the analytics group
SEARCH_ROLES = "developer, admin"                   # EnsureRole on search and algolia status / sync-all
ANY_ADMIN = "any admin role"                        # routes outside an EnsureRole group (Admin middleware only)
SYNONYMS = resource.Resource("synonym", "/search-synonyms", required=("terms",), label="terms",
                             source="Http/Controllers/Admin/Search/SearchSynonymController.php")
RULES = resource.Resource("rule", "/search-rules", required=("query", "match_type"), label="query",
                          source="Http/Controllers/Admin/Search/SearchRuleController.php")


def _get(path, **params):
    q = {k: v for k, v in params.items() if v is not None}
    return _client.default().get(path + ("?" + urllib.parse.urlencode(q) if q else ""))


def _data(r):
    return r.get("data", r) if isinstance(r, dict) else r


def _body(arg):
    from siruk.cli import _load_json
    try:
        return _load_json(arg)
    except (OSError, ValueError) as e:
        raise PayloadError(f"the body is not JSON: {e}")


def _id(text):
    if not str(text).isdigit():
        raise PayloadError("the id is a whole number")
    return str(int(text))


def _show(a, raw, render):
    if a.json:
        output.dump(raw)
        return 0
    render(raw)
    return 0


def _rows(title, rows, cols=None, more=10):
    rows = [r for r in rows if isinstance(r, dict)]
    print(f"{title}" + (f"  ({len(rows)} rows; --json for all)" if len(rows) > more else ""))
    output.table(rows[:more], cols or ins.columns(rows) or [("id", "id")])


def _report_view(raw):
    fields, kpis, lists = ins.walk(_data(raw))
    if fields:
        output.table(fields, [("field", "field"), ("value", "value")])
    if kpis:
        print()
        output.table(kpis, [("metric", "metric"), ("value", "value"), ("previous", "previous"), ("change", "change %")])
    for name, rows in lists.items():
        print()
        _rows(name, rows)


# ------------------------------------------------------------------ reports ----
def cmd_report(a):
    params = ins.date_params(a.from_, a.to)
    if not (a.export or a.out):
        return _show(a, _get(f"/analytics/{a.report}", **params), _report_view)
    path = f"/analytics/{a.report}/export" + ("?" + urllib.parse.urlencode(params) if params else "")
    data, filename = _client.default().download(path)
    if not data.startswith(b"PK"):
        raise _client.ApiError(200, "GET", path, f"not an xlsx: {data[:200]!r}")
    dest = ins.export_path(a.out, a.report, filename)
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    if a.json:
        output.dump({"path": dest, "bytes": len(data)})
    else:
        print(dest)
    return 0


def cmd_search_queries(a):
    if a.per_page is not None and not 5 <= a.per_page <= 50:
        raise PayloadError("--per-page is 5 to 50")
    r = _get("/analytics/searches/queries", **ins.date_params(a.from_, a.to), type=a.type, search=a.search,
             source=a.source, locale=a.locale, sort=a.sort, direction=a.direction,
             still_failing=1 if a.still_failing else None, page=a.page, perPage=a.per_page)

    def view(raw):
        rows, meta = raw.get("data") or [], raw.get("meta") or {}
        output.table(rows, [("query", "query"), ("searches", "searches"), ("avg_results", "avg results"),
                            ("zero_rate", "zero %"), ("last_searched_at", "last searched"), ("finds_now", "finds now")])
        print(f"page {meta.get('page')} of {meta.get('lastPage')}  ({meta.get('total')} queries)")
    return _show(a, r, view)


# -------------------------------------------------------------------- stock ----
def cmd_stock_stats(a):
    return _show(a, _get("/stock-statistics", **ins.date_params(a.from_, a.to), categoryId=a.category), _report_view)


def _stock_rows(products):
    return [{"product": p.get("name"), "variant": v.get("label") or v.get("name"), "sku": v.get("sku"),
             "available": v.get("available"), "status": v.get("status"), "policy": v.get("policy"),
             "backordered": v.get("backordered")} for p in products for v in p.get("variants") or []]


STOCK_COLS = [("product", "product"), ("variant", "variant"), ("sku", "sku"), ("available", "available"),
              ("status", "status"), ("policy", "policy"), ("backordered", "backordered")]


def cmd_stock_list(a):
    if a.per_page is not None and not 1 <= a.per_page <= 100:
        raise PayloadError("--per-page is 1 to 100")
    r = _get("/stock", q=a.search, category_id=a.category, warehouse_id=a.warehouse, status=a.status,
             policy=a.policy, page=a.page, perPage=a.per_page)

    def view(raw):
        output.table(_stock_rows(raw.get("data") or []), STOCK_COLS)
        m = raw.get("meta") or {}
        print(f"page {m.get('page')} of {m.get('pages')}  ({m.get('total')} products)")
    return _show(a, r, view)


def cmd_stock_dashboard(a):
    def view(raw):
        output.table([{"field": k, "value": v} for k, v in (raw.get("summary") or {}).items()],
                     [("field", "field"), ("value", "value")])
        for key, title in (("out_of_stock", "out of stock"), ("low_stock", "low stock")):
            rows = [{**v, "product": v.get("product_name"), "variant": v.get("label") or v.get("name")}
                    for v in raw.get(key) or []]
            print()
            _rows(title + (" (first 200 only)" if (raw.get("truncated") or {}).get(key) else ""), rows,
                  STOCK_COLS, more=50)
    return _show(a, _get("/stock/dashboard", q=a.search, category_id=a.category), view)


# ------------------------------------------------------------------- search ----
def cmd_settings_show(a):
    return _show(a, _get("/search-settings"),
                 lambda raw: output.table([{"field": k, "value": v} for k, v in _data(raw).items()],
                                          [("field", "field"), ("value", "value")]))


def cmd_settings_set(a):
    body = ins.check_settings(_body(a.body))
    current = _data(_get("/search-settings")) or {}
    ins.check_settings(body, current)
    diff = [f"{k}: {current.get(k)} → {v}" for k, v in body.items() if current.get(k) != v]
    summary = "search settings — " + ("; ".join(diff) if diff else "no sent key differs")
    return guard.run(a, steps=[guard.Step("PUT", "/search-settings", body, "save search settings")],
                     summary=summary, tier="draft", shown_state=current, verify="siruk admin search settings show")


def cmd_playground(a):
    q = a.query.strip()
    if not q or len(q) > 255:
        raise PayloadError("the query is 1 to 255 characters")

    def view(raw):
        d = _data(raw)
        print(f"{d.get('query')!r}  engine {d.get('engine')}  {d.get('tookMs')} ms  {d.get('total')} results")
        print(f"tokens: {', '.join(map(str, d.get('tokens') or [])) or '-'}")
        if d.get("rules"):
            output.table(d["rules"], [("id", "rule"), ("query", "query"), ("match_type", "match")])
        output.table(d.get("results") or [], [("position", "#"), ("id", "id"), ("name", "name"), ("brand", "brand"),
                                              ("pinned", "pinned")])
        if d.get("hidden"):
            print("hidden by rules")
            output.table(d["hidden"], [("id", "id"), ("name", "name")])
    return _show(a, _get("/search/playground", q=q, engine=a.engine), view)


def cmd_index_show(a):
    return _show(a, _get("/search/index"), lambda raw: output.table(
        [{"field": k, "value": v} for k, v in _data(raw).items()], [("field", "field"), ("value", "value")]))


def cmd_index_rebuild(a):
    return guard.run(a, steps=[guard.Step("POST", "/search/index/rebuild", None, "rebuild the local search index")],
                     summary="rebuild the local search index", tier="draft", verify="siruk admin search index show")


def _syn_rows(rows):
    return [{"id": r.get("id"), "terms": ", ".join(map(str, r.get("terms") or [])), "active": r.get("is_active")}
            for r in rows]


def _rule_rows(rows):
    return [{"id": r.get("id"), "query": r.get("query"), "match": r.get("match_type"),
             "pinned": len(r.get("pinned_product_ids") or []), "hidden": len(r.get("hidden_product_ids") or []),
             "active": r.get("is_active"), "note": r.get("note")} for r in rows]


def _crud(reg, noun, res, check, rows, cols):
    """`siruk admin search <noun> list|show|create|update|delete`; a body is checked before any call."""
    def cmd_list(a):
        if a.json:
            output.dump(resource.list_page(res))
            return 0
        output.table(rows(resource.list_rows(res)), cols)
        return 0

    def cmd_show(a):
        raw = _get(f"{res.path}/{_id(a.id)}")
        return _show(a, raw, lambda r: output.table([{"field": k, "value": v} for k, v in _data(r).items()],
                                                    [("field", "field"), ("value", "value")]))

    def cmd_create(a):
        steps, summary, shown = resource.plan_create(res, check(_body(a.body)))
        return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=shown,
                         verify=f"siruk admin search {noun} list")

    def cmd_update(a):
        steps, summary, shown = resource.plan_update(res, _id(a.id), check(_body(a.body)))
        return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=shown,
                         verify=f"siruk admin search {noun} show {a.id}")

    def cmd_delete(a):
        steps, summary, shown = resource.plan_delete(res, _id(a.id))
        return guard.run(a, steps=steps, summary=summary, tier="irreversible", shown_state=shown,
                         verify=f"siruk admin search {noun} list")

    one = f"{res.path}/:id"
    sample = {"synonyms": '{"terms": ["kitten", "kitty"]}',
              "rules": '{"query": "royal canin", "match_type": "contains", "pinned_product_ids": [12]}'}[noun]
    cmd = ("admin", "search", noun)
    reg.command((*cmd, "list"), cmd_list, f"list the search {noun}", api=[f"GET {res.path}"], roles=SEARCH_ROLES,
                example=f"siruk admin search {noun} list")
    p = reg.command((*cmd, "show"), cmd_show, f"one search {res.name}", api=[f"GET {one}"], roles=SEARCH_ROLES,
                    example=f"siruk admin search {noun} show 3")
    p.add_argument("id")
    p = reg.command((*cmd, "create"), cmd_create, f"create a search {res.name} from a JSON body",
                    api=[f"POST {res.path}"], tier="draft", roles=SEARCH_ROLES,
                    example=f"siruk admin search {noun} create '{sample}'")
    p.add_argument("body", help="JSON (file, '-' or inline)")
    p = reg.command((*cmd, "update"), cmd_update, f"replace a search {res.name}'s form with a JSON body",
                    api=[f"GET {one}", f"PUT {one}"], tier="draft", roles=SEARCH_ROLES,
                    example=f"siruk admin search {noun} update 3 '{sample}'")
    p.add_argument("id")
    p.add_argument("body", help="JSON (file, '-' or inline): every field the form sends")
    p = reg.command((*cmd, "delete"), cmd_delete, f"delete a search {res.name}", api=[f"GET {one}", f"DELETE {one}"],
                    tier="irreversible", roles=SEARCH_ROLES, example=f"siruk admin search {noun} delete 3")
    p.add_argument("id")


# ------------------------------------------------------------------ algolia ----
def cmd_algolia_status(a):
    def view(raw):
        d = _data(raw)
        output.table([{"field": k, "value": v} for k, v in d.items() if k != "sync"], [("field", "field"), ("value", "value")])
        print()
        output.table([{"field": k, "value": v} for k, v in (d.get("sync") or {}).items()],
                     [("field", "sync"), ("value", "value")])
    return _show(a, _get("/algolia/status"), view)


def cmd_algolia_sync(a):
    path = ins.sync_target(a.type, a.id)
    return guard.run(a, steps=[guard.Step("POST", path, None, f"push the {a.type} to Algolia")],
                     summary=f"sync {a.type} {int(a.id)} to Algolia", tier="real-world",
                     verify="siruk admin algolia status")


def cmd_algolia_sync_all(a):
    return guard.run(a, steps=[guard.Step("POST", "/algolia/sync-all", None, "queue a full Algolia sync")],
                     summary="queue a full sync of the whole catalogue to Algolia", tier="real-world",
                     verify="siruk admin algolia status")


# ----------------------------------------------------------------- register ----
def _range(p):
    p.add_argument("--from", dest="from_", metavar="DATE", help="YYYY-MM-DD or d/m/Y; default the 1st of this month")
    p.add_argument("--to", metavar="DATE", help="YYYY-MM-DD or d/m/Y; default today")


def register(reg):
    for name in ins.REPORTS:
        p = reg.command(("admin", "report", name), cmd_report, f"the {name} report, or its xlsx with --export",
                        api=[f"GET /analytics/{name}", f"GET /analytics/{name}/export"], roles=ANALYTICS,
                        example=f"siruk admin report {name} --from 2026-10-01 --to 2026-10-31")
        p.set_defaults(report=name)
        _range(p)
        p.add_argument("--export", action="store_true", help="download the xlsx instead of printing")
        p.add_argument("-o", "--out", metavar="FILE", help="file or folder for the xlsx (implies --export); default runs/<today>/")
    p = reg.command(("admin", "report", "search-queries"), cmd_search_queries,
                    "the paged top searches / searches with no results", api=["GET /analytics/searches/queries"],
                    roles=ANALYTICS, example="siruk admin report search-queries --type zero --still-failing")
    _range(p)
    p.add_argument("--type", choices=ins.QUERY_TYPES, required=True, help="top searches, or searches with no results")
    p.add_argument("--search", help="part of the query text")
    p.add_argument("--source", choices=ins.SOURCES)
    p.add_argument("--locale", choices=ins.LOCALES)
    p.add_argument("--sort", choices=ins.QUERY_SORTS, help="default searches")
    p.add_argument("--direction", choices=("asc", "desc"), help="default desc")
    p.add_argument("--still-failing", action="store_true", help="with --type zero: only queries the engine still misses")
    p.add_argument("--page", type=int)
    p.add_argument("--per-page", type=int, metavar="N", help="5 to 50; default 10")

    p = reg.command(("admin", "stock", "stats"), cmd_stock_stats, "stock statistics for a period",
                    api=["GET /stock-statistics"], roles=ANY_ADMIN, example="siruk admin stock stats --from 2026-10-01")
    _range(p)
    p.add_argument("--category", metavar="ID")
    p = reg.command(("admin", "stock", "dashboard"), cmd_stock_dashboard, "out-of-stock and low-stock variants",
                    api=["GET /stock/dashboard"], roles=ANY_ADMIN, example="siruk admin stock dashboard")
    p.add_argument("--search", metavar="TEXT", help="product, variant name or SKU")
    p.add_argument("--category", metavar="ID")
    p = reg.command(("admin", "stock", "list"), cmd_stock_list, "one page of products with their variants' stock",
                    api=["GET /stock"], roles=ANY_ADMIN, example="siruk admin stock list --status low_stock")
    p.add_argument("--search", metavar="TEXT", help="product, variant name or SKU")
    p.add_argument("--category", metavar="ID")
    p.add_argument("--warehouse", metavar="ID")
    p.add_argument("--status", choices=ins.STOCK_STATUSES)
    p.add_argument("--policy", choices=ins.STOCK_POLICIES)
    p.add_argument("--page", type=int)
    p.add_argument("--per-page", type=int, metavar="N", help="1 to 100; default 25")

    reg.command(("admin", "search", "settings", "show"), cmd_settings_show, "the search settings",
                api=["GET /search-settings"], roles=SEARCH_ROLES, example="siruk admin search settings show")
    p = reg.command(("admin", "search", "settings", "set"), cmd_settings_set, "change search settings (only the keys sent)",
                    api=["GET /search-settings", "PUT /search-settings"], tier="draft", roles=SEARCH_ROLES,
                    example="siruk admin search settings set '{\"engine\": \"local\"}'")
    p.add_argument("body", help="JSON (file, '-' or inline): the settings to change")
    _crud(reg, "synonyms", SYNONYMS, ins.check_synonym, _syn_rows,
          [("id", "id"), ("terms", "terms"), ("active", "active")])
    _crud(reg, "rules", RULES, ins.check_rule, _rule_rows,
          [("id", "id"), ("query", "query"), ("match", "match"), ("pinned", "pinned"), ("hidden", "hidden"),
           ("active", "active"), ("note", "note")])
    p = reg.command(("admin", "search", "playground"), cmd_playground, "run a query and see why each result ranked",
                    api=["GET /search/playground"], roles=SEARCH_ROLES,
                    example="siruk admin search playground 'royal canin' --engine local")
    p.add_argument("query", metavar="Q")
    p.add_argument("--engine", choices=ins.PLAYGROUND_ENGINES, help="default local")
    reg.command(("admin", "search", "index", "show"), cmd_index_show, "the local search index status",
                api=["GET /search/index"], roles=SEARCH_ROLES, example="siruk admin search index show")
    reg.command(("admin", "search", "index", "rebuild"), cmd_index_rebuild, "rebuild the local search index",
                api=["POST /search/index/rebuild"], tier="draft", roles=SEARCH_ROLES,
                example="siruk admin search index rebuild")

    reg.command(("admin", "algolia", "status"), cmd_algolia_status, "Algolia: configured, auto-sync, last full sync",
                api=["GET /algolia/status"], roles=SEARCH_ROLES, example="siruk admin algolia status")
    p = reg.command(("admin", "algolia", "sync"), cmd_algolia_sync, "push one record to Algolia (a dry run until --apply)",
                    api=["POST /algolia/sync/:type/:id"], tier="real-world", roles=ANY_ADMIN,
                    example="siruk admin algolia sync product 1234")
    p.add_argument("type", choices=ins.SYNC_TYPES)
    p.add_argument("id")
    reg.command(("admin", "algolia", "sync-all"), cmd_algolia_sync_all,
                "queue a full catalogue sync to Algolia (a dry run until --apply)", api=["POST /algolia/sync-all"],
                tier="real-world", roles=SEARCH_ROLES, example="siruk admin algolia sync-all")
