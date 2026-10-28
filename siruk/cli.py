"""`siruk` — the admin from the command line.

    siruk doctor                         token, API, config, pacing
    siruk find "royal canin mini"        search before create (rule 9)
    siruk show 874 [--lang hy]           one line per variant
    siruk add-variant 874 v.json --dry-run
    siruk bulk-create runs/<date>/bulk/*.json --dry-run
    siruk verify-translations --only 874,875
    siruk recheck-prices --only 874 [--apply]
    siruk export [--lang hy] [--format csv] | siruk export --audit
    siruk listing-order show | set groups.json --dry-run
    siruk tui                            the full-screen editor
    siruk mcp                            the MCP server on stdio

Every write builds its body through siruk.payload (the rules) and reads the
product back. --dry-run prints the diff and writes nothing. Guards: the same
env vars as the scripts (ALLOW_BELOW_COST, ALLOW_NO_IMAGE, ALLOW_NO_SIZE, FORCE)
or the flags --allow-below-cost / --allow-no-image / --force — only on the
user's explicit say-so. Exit codes: 0 ok, 1 refused by a rule, 2 API error.
"""
import argparse, json, os, sys, time

from siruk import client as _client
from siruk import config, output
from siruk.payload import PayloadError


def _load_json(arg):
    if arg == "-":
        return json.load(sys.stdin)
    if os.path.exists(arg):
        with open(arg, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(arg)


def _write_report(a, res):
    d = res.as_dict() if hasattr(res, "as_dict") else res
    if a.json:
        output.dump(d)
        return
    for w in d.get("warnings") or []:
        print(f"⚠ {w}", file=sys.stderr)
    head = "DRY RUN — nothing written" if d.get("dry_run") else "written"
    print(f"{d.get('action')} product {d.get('product_id') or '(new)'}: {head}")
    if "diff" in d:
        output.diff(d["diff"])
    if d.get("after"):
        output.product(d["after"])


def _confirm(a, what):
    if a.dry_run or a.yes or not sys.stdin.isatty():
        return True
    env = "PRODUCTION" if config.is_production() else "demo"
    ans = input(f"write {what} to {env} ({config.api_base()})? [y/N] ")
    return ans.strip().lower() in ("y", "yes")


def _env_flag(flag, var):
    return True if flag else (os.environ.get(var) == "1")


# ---------------------------------------------------------------- commands ----
def cmd_doctor(a):
    info = {"api": config.api_base(), "production": config.is_production(),
            "token_file": config.token_file(), "token": bool(config.token()),
            "config": config.config_path(), "python": sys.version.split()[0]}
    try:
        u = (_client.default().get("/account") or {}).get("currentUser") or {}
        info["account"] = f"{u.get('email')} ({u.get('role')})"
        info["api_ok"] = True
    except _client.ApiError as e:
        info["api_ok"], info["error"] = False, str(e)
    pacer = _client.default().pacer
    for ch in ("api", "media"):
        last, count = pacer.read_state(ch)
        info[f"pace_{ch}"] = f"{count} in chunk, last {int(time.time() - last / 1000)}s ago" if last else "idle"
    for mod in ("textual", "mcp", "PIL"):
        try:
            __import__(mod)
            info[f"has_{mod}"] = True
        except ImportError:
            info[f"has_{mod}"] = False
    if a.json:
        output.dump(info)
    else:
        for k, v in info.items():
            print(f"{k:<12} {v}")
    return 0 if info["api_ok"] else 2


def cmd_token(a):
    tok = a.value or sys.stdin.read()
    tok = "".join(tok.split())
    if tok.startswith("{"):  # the whole localStorage.access_token value
        tok = json.loads(tok).get("token", "")
    if not tok:
        print("error: empty token", file=sys.stderr)
        return 1
    c = _client.Client(token=tok)
    u = (c.get("/account") or {}).get("currentUser") or {}
    with open(config.token_file(), "w", encoding="utf-8") as f:
        f.write(tok + "\n")
    print(f"token ok for {u.get('email')} — wrote {config.token_file()}")
    return 0


def cmd_ids(a):
    from siruk import refdata
    kinds = [a.kind] if a.kind else list(refdata.KINDS)
    data = {k: refdata.ids(k) for k in kinds}
    if a.json:
        output.dump(data if len(kinds) > 1 else data[kinds[0]])
        return 0
    for k, rows in data.items():
        print(f"\n## {k} ({len(rows)})")
        cols = [(c, c) for c in rows[0].keys()] if rows else [("id", "id")]
        output.table(rows, cols)
    return 0


def cmd_refresh(a):
    from siruk import refdata
    r = refdata.refresh()
    for f, n in r.items():
        print(f"wrote reference/{f} ({n} entries)")
    return 0


def cmd_find(a):
    from siruk import products
    rows = products.find(" ".join(a.text))
    if a.json:
        output.dump(rows)
        return 0
    if not rows:
        print("no match — safe to create a new product")
        return 0
    for r in rows:
        r["categories"] = ", ".join(r["categories"])
    output.table(rows, [("id", "id"), ("name", "name"), ("brand", "brand"), ("categories", "categories")])
    print(f"\n{len(rows)} match(es) — same identity (brand + line + lifestage + form + diet)? "
          f"add the row as a variant: siruk add-variant <id> variant.json")
    return 0


def cmd_show(a):
    from siruk import products
    p = products.get(a.id, lang=a.lang)
    if not p:
        print(f"product {a.id} not found", file=sys.stderr)
        return 1
    if a.raw:
        output.dump(p)
    elif a.json:
        output.dump(products.summary(p))
    else:
        output.product(products.summary(p))
    return 0


def cmd_check(a):
    from siruk import products
    bad = 0
    for path in a.files:
        try:
            warns = products.check_payload(_load_json(path))
            print(f"ok   {path}" + (f"  ({len(warns)} warning(s))" if warns else ""))
            for w in warns:
                print(f"     ⚠ {w}")
        except PayloadError as e:
            bad += 1
            print(f"FAIL {path}: {e}")
    print(f"\n{len(a.files) - bad}/{len(a.files)} payloads pass")
    return 1 if bad else 0


def cmd_create(a):
    from siruk import products
    payload = _load_json(a.payload)
    kw = dict(force=_env_flag(a.force, "FORCE"), allow_below_cost=_env_flag(a.allow_below_cost, "ALLOW_BELOW_COST"),
              allow_no_image=_env_flag(a.allow_no_image, "ALLOW_NO_IMAGE"))
    res = products.create(payload, dry_run=True, **kw)
    if not a.dry_run:
        if not _confirm(a, f"new product '{payload.get('name')}'"):
            return 1
        res = products.create(payload, dry_run=False, **kw)
    _write_report(a, res)
    return 0


def cmd_add_variant(a):
    from siruk import products
    v = _load_json(a.variant)
    kw = dict(allow_below_cost=_env_flag(a.allow_below_cost, "ALLOW_BELOW_COST"),
              allow_no_image=_env_flag(a.allow_no_image, "ALLOW_NO_IMAGE"))
    res = products.add_variant(a.id, v, dry_run=True, **kw)
    if not a.dry_run:
        output.diff(res.diff, sys.stderr)
        if not _confirm(a, f"variant {v.get('sku')} on product {a.id}"):
            return 1
        res = products.add_variant(a.id, v, dry_run=False, **kw)
    _write_report(a, res)
    return 0


def cmd_set_variant(a):
    from siruk import products
    patch = _load_json(a.patch)
    replace = a.replace_attrs or os.environ.get("REPLACE_ATTRS") == "1"
    allow = _env_flag(a.allow_below_cost, "ALLOW_BELOW_COST")
    res = products.update_variant(a.id, a.sku, patch, replace, dry_run=True, allow_below_cost=allow)
    if not a.dry_run:
        output.diff(res.diff, sys.stderr)
        if not res.diff:
            print("nothing to change")
            return 0
        if not _confirm(a, f"patch of {a.sku} on product {a.id}"):
            return 1
        res = products.update_variant(a.id, a.sku, patch, replace, dry_run=False, allow_below_cost=allow)
    _write_report(a, res)
    return 0


def cmd_rename(a):
    from siruk import products
    res = products.rename(a.id, a.name, a.slug, dry_run=True)
    if not a.dry_run:
        if not res.diff:
            print("nothing to change")
            return 0
        if not _confirm(a, f"rename of product {a.id}"):
            return 1
        res = products.rename(a.id, a.name, a.slug, dry_run=False)
    _write_report(a, res)
    return 0


def cmd_translate(a):
    from siruk import translations
    tr = _load_json(a.file)
    res = translations.set_translation(a.id, a.lang, tr, dry_run=True)
    if not a.dry_run:
        output.diff(res.diff, sys.stderr)
        if not _confirm(a, f"{a.lang} translation of product {a.id}"):
            return 1
        res = translations.set_translation(a.id, a.lang, tr, dry_run=False)
    d = res.as_dict()
    d["after"] = None  # a locale read-back is not a summary table
    if a.json:
        output.dump(d)
    else:
        print(f"product {a.id} [{a.lang}]: " + ("DRY RUN" if a.dry_run else "OK — read back verified"))
        output.diff(res.diff)
    return 0


def cmd_stock(a):
    from siruk import stock
    if a.action == "show":
        rows = stock.movements(a.variant_id) or []
        if a.json:
            output.dump(rows)
        else:
            output.table(rows, [(k, k) for k in (rows[0].keys() if rows else ["id"])
                                if not isinstance(rows[0].get(k) if rows else None, (dict, list))])
        return 0
    fn = {"receive": lambda d: stock.receive(a.variant_id, a.quantity, a.note, a.unit_cost, dry_run=d),
          "write-off": lambda d: stock.write_off(a.variant_id, a.quantity, a.reason, a.note, dry_run=d),
          "set": lambda d: stock.set_count(a.variant_id, a.quantity, a.reason, a.note, dry_run=d)}[a.action]
    res = fn(True)
    if not a.dry_run:
        if not _confirm(a, f"stock {a.action} on variant {a.variant_id}"):
            return 1
        res = fn(False)
    output.dump(res)
    return 0


def cmd_listing_order(a):
    from siruk import listing
    if a.action == "show":
        rows = listing.show()
        if a.json:
            output.dump(rows)
        elif not rows:
            print("no listing order set — Relevance is relevance_score + merch_boost only")
        else:
            output.table(rows, [("position", "#"), ("brand", "brand"), ("category", "category"),
                                ("brand_id", "brand id"), ("category_id", "cat id")])
        return 0
    fn = {"set": lambda d: listing.set_groups(_load_json(a.groups), dry_run=d),
          "add": lambda d: listing.add(a.brand, a.category, a.at, dry_run=d),
          "remove": lambda d: listing.remove(a.position, dry_run=d),
          "clear": lambda d: listing.set_groups([], dry_run=d, allow_empty=True)}[a.action]
    if a.action == "set" and not a.groups:
        raise PayloadError("set needs the groups: [{\"brand\": \"Monge\", \"category\": 3}, …] (file, '-' or inline)")
    if a.action == "add" and not a.brand:
        raise PayloadError("add needs --brand (id or name)")
    if a.action == "remove" and not a.position:
        raise PayloadError("remove needs --position")
    res = fn(True)
    if not a.dry_run and res["changed"]:
        if not _confirm(a, f"listing order ({len(res['after'])} groups)"):
            return 1
        res = fn(False)
    if a.json:
        output.dump(res)
        return 0
    print("listing order: " + ("unchanged" if not res["changed"] else
                               "DRY RUN — nothing written" if res["dry_run"] else "written, read back verified"))
    cols = [("position", "#"), ("brand", "brand"), ("category", "category")]
    if res["changed"]:
        print("before:")
        output.table(res["before"], cols)
        print("after:")
    output.table(res["after"], cols)
    return 0


def _ids_arg(s):
    return [int(x) for x in s.split(",") if x.strip()] if s else None


def cmd_verify_translations(a):
    from siruk import verify
    if not a.paced:
        os.environ["SIRUK_NO_PACE"] = "1"  # a read-only sweep, as the script always did
    only = _ids_arg(a.only)
    progress = None if a.json or a.quiet else (
        lambda i, n: print(f"\r  products {i}/{n}", end="" if i < n else "\n", file=sys.stderr))
    res = verify.translations(only=only, catalogue=not a.products_only, progress=progress)
    if a.json:
        output.dump(res)
    else:
        verify.print_report(res, a.out)
    return 0 if res["complete"] else 1


def cmd_recheck_prices(a):
    from siruk import pricecheck
    if not a.paced:
        os.environ["SIRUK_NO_PACE"] = "1"
    show = None if a.json else (lambda pid, p, rows: print(
        f"{pid:>4} {(p.get('name') or '')[:40]:<40} " + "  ".join(
            f"{r['sku']}:{r['siruk_price']}→{r['hafo_price'] or '?'} {r['status'][:9]}" for r in rows)))
    rows = pricecheck.check(_ids_arg(a.only), progress=show)
    path = pricecheck.write_csv(rows, a.out)
    fx = pricecheck.fixes(rows)
    if a.json and not a.apply:
        output.dump({"summary": pricecheck.summary(rows), "fixable": fx, "csv": path, "rows": rows})
        return 0
    if not a.json:
        print("\n== summary ==", pricecheck.summary(rows), "\n→", path)
    if not a.apply:
        print(f"{sum(len(v) for v in fx.values())} variant(s) would be updated; run with --apply")
        return 0
    bad = 0
    for pid, skus in fx.items():
        try:
            res = pricecheck.apply_prices(pid, skus, dry_run=True)
            output.diff(res.diff)
            if not _confirm(a, f"hafo prices on product {pid}"):
                continue
            res = pricecheck.apply_prices(pid, skus, dry_run=a.dry_run)
            for w in res.warnings:
                print(f"  !! {pid}/{w}")
            print(("dry run " if a.dry_run else "ok  ") + f"{pid}: " + ", ".join(
                f"{d['sku']}→{d['new']}" for d in res.diff if d["field"] == "price"))
        except PayloadError as e:
            bad += 1
            print(f"  !! {e}")
    return 1 if bad else 0


def cmd_bulk_create(a):
    from siruk import bulk, verify
    items = []
    for f in a.files:
        try:
            items.append((f, _load_json(f)))
        except (OSError, ValueError) as e:
            items.append((f, {"_unreadable": str(e)}))
    kw = dict(en_only=a.en_only, force=_env_flag(a.force, "FORCE"),
              allow_below_cost=_env_flag(a.allow_below_cost, "ALLOW_BELOW_COST"),
              allow_no_image=_env_flag(a.allow_no_image, "ALLOW_NO_IMAGE"))
    log = (lambda m: None) if a.json else (lambda m: print(m, file=sys.stderr))
    results = bulk.create(items, dry_run=True, log=log, **kw)
    ready = sum(1 for r in results.values() if r["status"] == "ready")
    if not a.dry_run and ready:
        if not _confirm(a, f"{ready} new product(s)"):
            return 1
        results = bulk.create(items, dry_run=False, log=lambda m: None, **kw)
    for r in results.values():
        r.pop("body", None)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
    if a.json:
        output.dump(results)
    else:
        rows = [{"item": k, "status": r["status"], "id": r.get("id"), "detail":
                 (r.get("read_back") if r.get("read_back") not in (None, "ok") else "")
                 or str(r.get("errors") or "")[:90] or r.get("name")} for k, r in results.items()]
        output.table(rows, [("item", "item"), ("status", "status"), ("id", "id"), ("detail", "detail")])
        if a.dry_run:
            print(f"\ndry run: {ready} ready, {len(results) - ready} refused — nothing sent")
    ids = [r["id"] for r in results.values() if r["status"] == "created"]
    if ids and not a.json:
        print("\n# translations (CLAUDE.md 13 — report from this, not from what was sent):")
        os.environ["SIRUK_NO_PACE"] = "1"
        verify.print_report(verify.translations(only=ids, catalogue=False))
    return 0 if bulk.ok(results) else 1


def cmd_export(a):
    from siruk import export
    kw = dict(lang=a.lang, updated_since=a.since, search=a.search, dates=a.dates)
    if a.audit:
        res = export.audit(export.records(**kw), examples=a.examples)
        if a.json:
            output.dump(res)
            return 0
        print(f"{res['products']} products · {res['variants']} variants · "
              + ", ".join(f"{k}: {n}" for k, n in sorted(res["by_type"].items(), key=lambda x: -x[1])))
        output.table([{"check": k, "n": res["counts"][k], "what": res["checks"][k]} for k in res["checks"]],
                     [("check", "check"), ("n", "n"), ("what", "what")])
        for k, ex in res["examples"].items():
            if k in ("no_price_source", "out_of_stock") and not a.all:
                continue
            print(f"\n## {k}")
            for e in ex:
                if "variants" in e:
                    print(f"  {e.get('barcode') or e.get('sku')}: "
                          + ", ".join(f"{v['product_id']}/{v['sku']}" for v in e["variants"]))
                else:
                    print(f"  {e['product_id']:>5} {e['sku'] or '-':<18} {e['price']} / {e['cost']}  {e['product']}")
        return 0
    r = export.save(a.out, a.format, **kw)
    if a.json:
        output.dump(r)
    else:
        print(f"{r['path']}  ({r.get('rows', '')}{' rows' if 'rows' in r else str(r['bytes']) + ' bytes'})")
    return 0


def cmd_media(a):
    from siruk import media
    log = _client.stderr_log
    if a.action == "check":
        ok = all(media.media_ok(i, log) for i in a.target)
        print("ok" if ok else "BROKEN")
        return 0 if ok else 1
    folder = a.folder or os.environ.get("MEDIA_DIR", "")
    r = media.upload(a.target[0], folder, keep_alpha=a.keep_alpha or os.environ.get("KEEP_ALPHA") == "1",
                     dry_run=a.dry_run, log=log, alt=a.alt)
    if a.json:
        output.dump(r)
    else:
        print(r["id"] if r.get("id") else json.dumps(r, ensure_ascii=False))
    return 0


def cmd_price(a):
    from siruk import lookups
    if a.source == "hafo":
        if not a.code:
            print("error: --code is required for hafo", file=sys.stderr)
            return 1
        r = lookups.hafo(a.code, a.name or "")
    else:
        r = getattr(lookups, a.source)(search=a.search or a.name, brand=a.brand, url=a.url, limit=a.limit)
    output.dump(r)
    return 0


def cmd_api(a):
    body = _load_json(a.body) if a.body else None
    if a.method.upper() not in ("GET", "HEAD") and not _confirm(a, f"{a.method.upper()} {a.path}"):
        return 1
    output.dump(_client.default().request(a.method, a.path, body=body, lang=a.lang))
    return 0


def cmd_pace(a):
    _client.default().pacer.pace(a.channel, _client.stderr_log)
    return 0


def cmd_tui(a):
    try:
        from siruk.tui.app import run
    except ImportError as e:
        print(f"the TUI needs textual: run it as `uv run siruk tui` ({e})", file=sys.stderr)
        return 1
    run()
    return 0


def cmd_mcp(a):
    try:
        from siruk.mcp_server import main as mcp_main
    except ImportError as e:
        print(f"the MCP server needs the mcp package: `uv run siruk-mcp` ({e})", file=sys.stderr)
        return 1
    mcp_main()
    return 0


# ------------------------------------------------------------------ parser ----
def build_parser():
    def globals_parser(default):
        # the subcommands repeat the global flags with SUPPRESS defaults, so
        # `siruk -q show 1` and `siruk show 1 -q` both work (argparse would
        # otherwise reset the top-level value with the subparser's default)
        g = argparse.ArgumentParser(add_help=False)
        g.add_argument("--json", action="store_true", default=default, help="machine-readable output")
        g.add_argument("--no-pace", action="store_true", default=default, help="skip pacing (single ad-hoc calls)")
        g.add_argument("-q", "--quiet", action="store_true", default=default, help="no HTTP log on stderr")
        return g
    top = globals_parser(False)
    common = globals_parser(argparse.SUPPRESS)
    w = argparse.ArgumentParser(add_help=False)
    w.add_argument("--dry-run", action="store_true", help="show the body/diff, write nothing")
    w.add_argument("-y", "--yes", action="store_true", help="don't ask (non-interactive runs never ask)")

    ap = argparse.ArgumentParser(prog="siruk", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter, parents=[top])
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="<command>")

    def add(name, fn, help, writes=False, **kw):
        p = sub.add_parser(name, help=help, parents=[common] + ([w] if writes else []), **kw)
        p.set_defaults(fn=fn)
        return p

    add("doctor", cmd_doctor, "check token, API, config and pacing")
    p = add("token", cmd_token, "store a JWT (validated with /account)")
    p.add_argument("action", choices=["set"])
    p.add_argument("value", nargs="?", help="the token (default: read stdin)")
    p = add("ids", cmd_ids, "live ids: brands, categories, types, attributes")
    p.add_argument("kind", nargs="?", choices=["brands", "categories", "types", "attributes"])
    add("refresh", cmd_refresh, "rewrite reference/attribute-values.json + product-types.json")
    p = add("find", cmd_find, "search products by name (before any create)")
    p.add_argument("text", nargs="+")
    p = add("show", cmd_show, "one product, one line per variant")
    p.add_argument("id", type=int)
    p.add_argument("--lang", choices=["en", "ru", "hy"])
    p.add_argument("--raw", action="store_true", help="the full GET body")
    p = add("check", cmd_check, "validate payloads against the live product types (no write)")
    p.add_argument("files", nargs="+")
    p = add("create", cmd_create, "create a product from a payload", writes=True)
    p.add_argument("payload")
    p.add_argument("--force", action="store_true", help="create even if a similar name exists")
    p.add_argument("--allow-below-cost", action="store_true")
    p.add_argument("--allow-no-image", action="store_true")
    p = add("add-variant", cmd_add_variant, "append a variant to an existing product", writes=True)
    p.add_argument("id", type=int)
    p.add_argument("variant", help="file, '-' for stdin, or inline JSON")
    p.add_argument("--allow-below-cost", action="store_true")
    p.add_argument("--allow-no-image", action="store_true")
    p = add("set-variant", cmd_set_variant, "patch one variant in place", writes=True)
    p.add_argument("id", type=int)
    p.add_argument("sku")
    p.add_argument("patch", help="JSON object (file, '-' or inline)")
    p.add_argument("--replace-attrs", action="store_true")
    p.add_argument("--allow-below-cost", action="store_true")
    p = add("rename", cmd_rename, "rename a product (no brand, no size in the name)", writes=True)
    p.add_argument("id", type=int)
    p.add_argument("name")
    p.add_argument("--slug")
    p = add("translate", cmd_translate, "store a ru/hy translation", writes=True)
    p.add_argument("id", type=int)
    p.add_argument("lang", choices=["ru", "hy"])
    p.add_argument("file")
    p = add("stock", cmd_stock, "stock ledger of a variant", writes=True)
    p.add_argument("action", choices=["show", "receive", "write-off", "set"])
    p.add_argument("variant_id", type=int)
    p.add_argument("quantity", nargs="?", type=float, help="receive/write-off: qty; set: on_hand")
    p.add_argument("--note", default="")
    p.add_argument("--reason", default="correction")
    p.add_argument("--unit-cost", type=float)
    p = add("listing-order", cmd_listing_order,
            "brand + category groups that lead Relevance listings (the PM's / user's order)", writes=True)
    p.add_argument("action", choices=["show", "set", "add", "remove", "clear"])
    p.add_argument("groups", nargs="?", help="set: the whole ordered list as JSON (file, '-' or inline)")
    p.add_argument("--brand", help="add: brand id or exact name")
    p.add_argument("--category", type=int, help="add: category id (default: the whole brand)")
    p.add_argument("--at", type=int, help="add: 1-based position (default: the end)")
    p.add_argument("--position", type=int, help="remove: the group's position")
    p = add("bulk-create", cmd_bulk_create, "create many NEW products in one call (en/ru/hy)", writes=True)
    p.add_argument("files", nargs="+", help="create payloads (bulk-create.py's shape)")
    p.add_argument("--en-only", action="store_true", help="allow a missing ru/hy (translate after)")
    p.add_argument("--out", help="write the results JSON here")
    p.add_argument("--force", action="store_true", help="create even if a similar name exists")
    p.add_argument("--allow-below-cost", action="store_true")
    p.add_argument("--allow-no-image", action="store_true")
    p = add("verify-translations", cmd_verify_translations, "the ru/hy audit (rule 13); exit 1 if anything missing")
    p.add_argument("--only", help="product ids, comma-separated (default: every product)")
    p.add_argument("--products-only", action="store_true", help="skip categories and brands")
    p.add_argument("--out", help="write the full missing list as JSON")
    p.add_argument("--paced", action="store_true", help="keep config.json pacing (default: off, as the script)")
    p = add("recheck-prices", cmd_recheck_prices, "hafo price recheck (rule 4) → runs/<date>/price-check.csv",
            writes=True)
    p.add_argument("--only", help="product ids, comma-separated (default: the whole catalogue)")
    p.add_argument("--apply", action="store_true", help="also fix the unflagged mismatches (asks per product)")
    p.add_argument("--out", help="csv path (default runs/<date>/price-check.csv)")
    p.add_argument("--paced", action="store_true", help="keep config.json pacing (default: off, as the script)")
    p = add("export", cmd_export, "the catalogue export (one row per variant) → xlsx/json/csv, or --audit")
    p.add_argument("--lang", choices=["en", "ru", "hy"], default="en")
    p.add_argument("--format", choices=["xlsx", "json", "csv"], default="xlsx")
    p.add_argument("-o", "--out", help="file path (default runs/<date>/products_<lang>_<date>.<format>)")
    p.add_argument("--since", help="only products/variants updated after this date (2026-10-20 or an ISO time)")
    p.add_argument("--search", help="the admin list's search")
    p.add_argument("--dates", help="created between d/m/Y,d/m/Y (the admin list's date filter)")
    p.add_argument("--audit", action="store_true",
                   help="print catalogue checks instead of saving (below cost, missing codes/images/size, duplicates)")
    p.add_argument("--examples", type=int, default=20, help="--audit: rows shown per check")
    p.add_argument("--all", action="store_true", help="--audit: also list no-price-source and out-of-stock rows")
    p = add("media", cmd_media, "upload / check media", writes=True)
    p.add_argument("action", choices=["upload", "check"])
    p.add_argument("target", nargs="+", help="upload: file or url; check: media ids")
    p.add_argument("--folder", help="products/<brand-slug>/<type> | logos | categories | banners")
    p.add_argument("--keep-alpha", action="store_true")
    p.add_argument("--alt", help='alt = caption, e.g. "{Brand} {Name}" (SEO); default the file name')
    p = add("price", cmd_price, "rival price lookups: hafo (by code), zoovet / nemo (by name)")
    p.add_argument("source", choices=["hafo", "zoovet", "nemo"])
    p.add_argument("--code")
    p.add_argument("--name")
    p.add_argument("--search")
    p.add_argument("--brand")
    p.add_argument("--url")
    p.add_argument("--limit", type=int, default=10)
    p = add("api", cmd_api, "raw API call (escape hatch)", writes=True)
    p.add_argument("method")
    p.add_argument("path")
    p.add_argument("body", nargs="?")
    p.add_argument("--lang", choices=["en", "ru", "hy"])
    p = add("pace", cmd_pace, "wait like pace.sh (between rows: `siruk pace product`)")
    p.add_argument("channel", choices=["product", "api", "media"])
    add("tui", cmd_tui, "full-screen browser and editor")
    add("mcp", cmd_mcp, "run the MCP server on stdio")
    return ap


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    a = build_parser().parse_args(argv)
    if a.no_pace:
        os.environ["SIRUK_NO_PACE"] = "1"
    for k in ("dry_run", "yes"):
        if not hasattr(a, k):
            setattr(a, k, False)
    c = _client.default()
    if a.cmd not in ("tui", "mcp") and isinstance(c, _client.Client) and not a.quiet:
        c.log = _client.stderr_log
    try:
        sys.exit(a.fn(a) or 0)
    except PayloadError as e:
        print(f"refused: {e}", file=sys.stderr)
        sys.exit(1)
    except _client.ApiError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        sys.exit(130)
