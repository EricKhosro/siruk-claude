"""Admin insights: report dates and export paths, the search-admin body rules, and a generic report renderer.

Rules: analytics dates go out as d/m/Y (AbstractReportController / ParsesDateRange); a synonym needs two
distinct terms (SearchSynonymRequest); a rule pins or hides a product (SearchRuleRequest); settings keys and
values follow SearchSettings::DEFAULTS and rules(). Shapes: siruk-web/backend/app/Http/{Controllers,Requests}/Admin.
"""
import datetime, os

from siruk import config
from siruk.payload import PayloadError

REPORTS = ("overview", "sales", "products", "customers", "promotions", "margin", "searches")
QUERY_TYPES = ("top", "zero")                                     # SearchesReportController::queries
QUERY_SORTS = ("searches", "avg_results", "zero_rate", "last_searched_at")   # SearchReportService::QUERY_SORTS
SOURCES = ("web", "mobile")
LOCALES = ("en", "hy", "ru")                                      # config/app.php locales
STOCK_STATUSES = ("in_stock", "low_stock", "backorder", "dropship", "out_of_stock")   # App\Enums\StockStatus
STOCK_POLICIES = ("deny", "backorder", "dropship")                # App\Enums\OutOfStockPolicy
ENGINES = ("algolia_fallback", "local", "algolia")                # App\Enums\SearchEngine (settings)
PLAYGROUND_ENGINES = ("local", "algolia")                         # SearchPlaygroundController: algolia_fallback is refused
MATCH_TYPES = ("exact", "contains")                               # App\Enums\SearchRuleMatch
SYNC_TYPES = ("product", "category", "brand", "post")             # AlgoliaSyncService::RECORD_TYPES

# SearchSettings::DEFAULTS: the engine, the booleans and the two typo word sizes (1 to 20)
SETTING_BOOLS = ("typo_tolerance", "prefix_last_word", "optional_words", "ignore_plurals", "transliteration",
                 "synonyms", "in_stock_first", "rank_merch_boost", "rank_best_seller", "rank_sales_count")
SETTING_INTS = ("min_word_size_1_typo", "min_word_size_2_typos")


def day(text, what="date"):
    """YYYY-MM-DD (as `siruk ops report`) or d/m/Y → date."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(str(text).strip(), fmt).date()
        except ValueError:
            pass
    raise PayloadError(f"{what} {text!r} is not a date: use YYYY-MM-DD or d/m/Y")


def date_params(start=None, end=None):
    """{startDate, endDate} in d/m/Y; a missing end sends nothing (the server defaults to the month so far)."""
    out, a, b = {}, None, None
    if start:
        a = day(start, "--from")
        out["startDate"] = a.strftime("%d/%m/%Y")
    if end:
        b = day(end, "--to")
        out["endDate"] = b.strftime("%d/%m/%Y")
    if a and b and b < a:
        raise PayloadError("--to must be on or after --from")
    return out


def export_path(out, report, filename=None, today=None):
    """-o a file → that file; -o a folder (existing, or written with a trailing slash) or nothing → the
    server's file name in it (default runs/<date>/)."""
    name = os.path.basename((filename or "").replace("\\", "/"))
    if name in ("", ".", ".."):
        name = f"{report}-report.xlsx"
    if out and not (os.path.isdir(out) or out.endswith(("/", os.sep))):
        return out
    return os.path.join(out or os.path.join(config.ROOT, "runs", today or datetime.date.today().isoformat()), name)


def _words(terms):
    return [t.strip() for t in terms]


def check_synonym(body):
    """Refuse a synonym the server would refuse or shrink below two terms (SearchSynonymRequest, SearchSynonymController::fields)."""
    if not isinstance(body, dict):
        raise PayloadError("the synonym body must be a JSON object")
    terms = body.get("terms")
    if not isinstance(terms, list) or not all(isinstance(t, str) and t.strip() for t in terms):
        raise PayloadError('a synonym needs "terms": a list of at least two words (see SearchSynonymRequest.php)')
    seen = {w.casefold() for w in _words(terms)}
    if len(terms) < 2 or len(seen) < 2:
        raise PayloadError("a synonym needs at least two different terms (SearchSynonymRequest.php: terms min 2)")
    if len(terms) != len({t.casefold() for t in terms}):
        raise PayloadError("synonym terms must be different from each other (distinct, ignoring case)")
    if any(len(t) > 100 for t in terms):
        raise PayloadError("a synonym term is at most 100 characters")
    return body


def _ids(body, key):
    v = body.get(key)
    if v is None:
        return []
    if not isinstance(v, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in v) or len(set(v)) != len(v):
        raise PayloadError(f"{key} must be a list of different product ids")
    return v


def check_rule(body):
    """SearchRuleRequest: query, match_type, and at least one pinned or hidden product."""
    if not isinstance(body, dict):
        raise PayloadError("the rule body must be a JSON object")
    q = body.get("query")
    if not isinstance(q, str) or not q.strip() or len(q) > 255:
        raise PayloadError('a rule needs "query": the search text, up to 255 characters')
    if body.get("match_type") not in MATCH_TYPES:
        raise PayloadError(f'a rule needs "match_type": one of {", ".join(MATCH_TYPES)}')
    if not _ids(body, "pinned_product_ids") and not _ids(body, "hidden_product_ids"):
        raise PayloadError("a rule pins or hides at least one product (pinned_product_ids / hidden_product_ids)")
    note = body.get("note")
    if note is not None and (not isinstance(note, str) or len(note) > 255):
        raise PayloadError("note is text of up to 255 characters")
    if "is_active" in body and not isinstance(body["is_active"], bool):
        raise PayloadError("is_active is true or false")
    return body


def check_settings(body, current=None):
    """A partial settings body: only known keys, typed as SearchSettings::rules(); two typos need a longer word than one."""
    if not isinstance(body, dict) or not body:
        raise PayloadError("settings set needs a JSON object with at least one setting")
    known = ("engine", *SETTING_BOOLS, *SETTING_INTS)
    bad = [k for k in body if k not in known]
    if bad:
        raise PayloadError(f"unknown setting {', '.join(bad)}: the server would drop it (known: {', '.join(known)})")
    for k, v in body.items():
        if k == "engine" and v not in ENGINES:
            raise PayloadError(f"engine is one of {', '.join(ENGINES)}")
        if k in SETTING_BOOLS and not isinstance(v, bool):
            raise PayloadError(f"{k} is true or false")
        if k in SETTING_INTS and not (isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 20):
            raise PayloadError(f"{k} is a whole number from 1 to 20")
    merged = {**(current or {}), **body}
    one, two = merged.get("min_word_size_1_typo"), merged.get("min_word_size_2_typos")
    if isinstance(one, int) and isinstance(two, int) and two <= one:
        raise PayloadError("min_word_size_2_typos must be greater than min_word_size_1_typo")
    return body


def sync_target(kind, id):
    if kind not in SYNC_TYPES:
        raise PayloadError(f"type is one of {', '.join(SYNC_TYPES)}")
    if not str(id).isdigit():
        raise PayloadError("the id is a whole number")
    return f"/algolia/sync/{kind}/{int(id)}"


# ------------------------------------------------------------ rendering ----
def _scalar(v):
    return v is None or isinstance(v, (str, int, float, bool))


def _is_kpi(v):
    return isinstance(v, dict) and {"value", "previous", "change"} <= set(v)


def walk(data, prefix="", out=None):
    """A report body → (field rows, kpi rows, {name: list of rows}); nested dicts are read to two levels."""
    fields, kpis, lists = out or ([], [], {})
    for k, v in (data or {}).items():
        name = f"{prefix}{k}"
        if _is_kpi(v):
            kpis.append({"metric": name, "value": v["value"], "previous": v["previous"], "change": v["change"]})
        elif isinstance(v, dict) and prefix.count(".") < 1:
            walk(v, name + ".", (fields, kpis, lists))
        elif isinstance(v, list):
            lists[name] = v
        elif _scalar(v):
            fields.append({"field": name, "value": v})
        else:
            fields.append({"field": name, "value": "(see --json)"})
    return fields, kpis, lists


def columns(rows, limit=7):
    first = next((r for r in rows if isinstance(r, dict)), {})
    return [(k, k) for k, v in first.items() if _scalar(v)][:limit]
