"""`siruk ops docs list | show | new | lines | post | delete` — the manual stock documents that replace ArmSoft's.

Flow: `new` saves a draft, `lines` edits it, `post` is final (a mistake is fixed with a new document),
`delete` removes a draft. There is no command that creates and posts in one step.
"""
import sys, urllib.parse

from siruk import output
from siruk.ops import client as _ops, documents as D, guard, resolve, units
from siruk.payload import PayloadError

ROLES = "manager, warehouse"


def _id(ref):
    ref = str(ref).strip()
    if not resolve.UUID.fullmatch(ref):
        raise PayloadError(f"{ref!r} is not a document id (see `siruk ops docs list`)")
    return ref


def _doc(ref):
    return _ops.default().get(f"/documents/{urllib.parse.quote(_id(ref), safe='')}") or {}


def _draft(doc):
    if doc.get("status") != "draft":
        raise PayloadError(f"{doc.get('number') or doc.get('id')} is {doc.get('status')}: "
                           "a posted document never changes or goes; fix it with a new document")
    return doc


def _lines_arg(arg):
    from siruk.cli import _load_json
    try:
        return _load_json(arg)
    except (OSError, ValueError) as e:
        raise PayloadError(f"--lines is not JSON: {e}")


def _amd(minor):
    return "-" if minor is None else units.minor_to_amd(minor)


def _line_rows(doc):
    return [{"n": n, "sku": l.get("sku"), "name": (l.get("productName") or {}).get("en") or "",
             "label": l.get("label"),
             "qty": units.format_quantity(l.get("quantity") or 0, l.get("stockUnit")),
             "counted": None if l.get("countedQuantity") is None
             else units.format_quantity(l["countedQuantity"], l.get("stockUnit")),
             "total": _amd(l.get("amountMinor")), "target": l.get("targetSku"), "note": l.get("note")}
            for n, l in enumerate(doc.get("lines") or [], 1)]


def cmd_list(a):
    params = {k: v for k, v in (("type", a.type), ("status", a.status), ("from", a.date_from), ("to", a.date_to),
                                ("page", a.page), ("pageSize", a.page_size)) if v is not None}
    if a.location:
        params["locationId"] = resolve.location(a.location)["id"]
    r = _ops.default().get("/documents", params) or {}
    if a.json:
        output.dump(r)
        return 0
    rows = [{**d, "date": (d.get("documentDate") or "")[:10], "total": _amd(d.get("totalAmountMinor")),
             "route": (d.get("locationName") or "") + (f" → {d['toLocationName']}" if d.get("toLocationName") else "")}
            for d in r.get("items") or []]
    output.table(rows, [("number", "number"), ("type", "type"), ("status", "status"), ("date", "date"),
                        ("route", "location"), ("supplierName", "supplier"), ("lineCount", "lines"),
                        ("total", "total AMD"), ("id", "id")])
    print(f"{len(rows)} of {r.get('total')} (page {r.get('page')})", file=sys.stderr)
    return 0


def cmd_show(a):
    d = _doc(a.id)
    if a.json:
        output.dump(d)
        return 0
    print(f"{d.get('number')}  {d.get('type')}  {d.get('status')}  {(d.get('documentDate') or '')[:10]}")
    print(f"location  {d.get('locationName')}" + (f" → {d['toLocationName']}" if d.get("toLocationName") else ""))
    for k, label in (("supplierName", "supplier"), ("invoiceSerial", "invoice"), ("reason", "reason"),
                     ("note", "note")):
        if d.get(k):
            print(f"{label:<9} {d[k]}")
    if d.get("totalAmountMinor") is not None:
        print(f"total     {_amd(d['totalAmountMinor'])} AMD")
    print(f"id        {d.get('id')}\n")
    output.table(_line_rows(d), [("n", "#"), ("sku", "sku"), ("name", "name"), ("label", "label"), ("qty", "qty"),
                                 ("counted", "counted"), ("total", "total AMD"), ("target", "pours into"),
                                 ("note", "note")])
    return 0


class _Recording:
    """The Ops client, plus the answers its writes got: a replayed key answers with an old document."""

    def __init__(self, client):
        self.client, self.base, self.answers = client, client.base, []

    def write(self, method, path, body=None):
        self.answers.append(self.client.write(method, path, body))
        return self.answers[-1]


def cmd_new(a):
    clean = D.check_header(a.type, to_location=a.to_location, supplier=a.supplier, invoice=a.invoice,
                           reason=a.reason, note=a.note, date=a.date)
    raw = _lines_arg(a.lines)
    D.check_lines_shape(a.type, raw)
    location = resolve.location(a.location)
    to_location = resolve.location(a.to_location) if a.to_location else None
    supplier = resolve.supplier(a.supplier) if a.supplier else None
    body = D.build_body(a.type, location=location, to_location=to_location, supplier=supplier,
                        invoice=clean["invoice"], reason=a.reason, note=clean["note"], date=a.date, key=a.key,
                        lines=D.build_lines(a.type, raw))
    where = location["code"] + (f" → {to_location['code']}" if to_location else "")
    summary = f"draft {a.type} at {where}, {len(body['lines'])} line(s)" + (f", {supplier['name']}" if supplier else "")
    seen = _Recording(_ops.default())
    rc = guard.run(a, steps=[guard.Step("POST", "/documents", body, f"{a.type} draft")], summary=summary,
                   tier="draft", verify="siruk ops docs list --status draft", client=seen)
    answer = seen.answers[0] if seen.answers else None
    if rc == 0 and isinstance(answer, dict) and answer.get("status") != "draft":
        print(f"refused: Ops returned existing document {answer.get('number')}, {answer.get('status')} since "
              f"{answer.get('postedAt')}; nothing new was made; --key makes a second one", file=sys.stderr)
        return 1
    return rc


def cmd_lines(a):
    doc = _draft(_doc(a.id))
    lines = D.build_lines(doc["type"], _lines_arg(a.lines))
    return guard.run(a, steps=[guard.Step("PUT", f"/documents/{doc['id']}/lines", {"lines": lines}, "replace lines")],
                     summary=f"replace the lines of draft {doc.get('number')} ({len(doc.get('lines') or [])} → {len(lines)})",
                     tier="draft", shown_state=D.state(doc), verify=f"siruk ops docs show {doc['id']}")


def cmd_post(a):
    doc = _draft(_doc(a.id))
    if not a.apply:
        cache = {}
        many = len(doc.get("lines") or []) >= resolve.BULK_FROM
        catalogue = resolve.Catalogue.load() if many else None

        def fetch(variant_id):
            if variant_id not in cache:
                cache[variant_id] = (catalogue.variant(variant_id) if catalogue else
                                     _ops.default().get(f"/goods/{variant_id}") or {})
            return cache[variant_id]

        rows = D.review(doc, fetch)
        for r in rows:
            r["flag"] = "NEGATIVE" if r["negative"] else ""
        out = sys.stderr if a.json else sys.stdout
        print(f"{doc.get('number')}  {doc.get('type')}  {len(doc.get('lines') or [])} line(s), "
              f"total {_amd(doc.get('totalAmountMinor'))} AMD — this is what posting does to the stock\n", file=out)
        output.table(rows, [("line", "#"), ("sku", "sku"), ("where", "location"), ("now", "stock now"),
                            ("change", "change"), ("after", "stock after"), ("flag", "")], out)
        print(file=out)
    return guard.run(a, steps=[guard.Step("POST", f"/documents/{doc['id']}/post", None, "post — final")],
                     summary=f"POST {doc.get('type')} {doc.get('number')}: stock moves now and the document never changes",
                     tier="irreversible", shown_state=D.state(doc), verify=f"siruk ops docs show {doc['id']}")


def cmd_delete(a):
    doc = _draft(_doc(a.id))
    return guard.run(a, steps=[guard.Step("DELETE", f"/documents/{doc['id']}", None, "delete draft")],
                     summary=f"delete draft {doc.get('number')} ({len(doc.get('lines') or [])} line(s))",
                     tier="draft", shown_state=D.state(doc), verify=f"siruk ops docs show {doc['id']}")


def register(reg):
    p = reg.command(("ops", "docs", "list"), cmd_list, "list stock documents (newest first)",
                    api=["GET /documents", "GET /locations"], roles=ROLES,
                    example="siruk ops docs list --status draft --type receipt")
    p.add_argument("--type", choices=("opening_balance", "receipt", "supplier_return", "write_off", "count",
                                      "transfer", "bag_opening", "sale", "sale_return", "web_order", "stock_hold",
                                      "good_merge", "cost_correction"))
    p.add_argument("--status", choices=("draft", "posted"))
    p.add_argument("--from", dest="date_from", metavar="DATE", help="document date from (ISO)")
    p.add_argument("--to", dest="date_to", metavar="DATE", help="document date to; a date alone includes that day")
    p.add_argument("--location", help="location code or id")
    p.add_argument("--page", type=int)
    p.add_argument("--page-size", type=int)
    p = reg.command(("ops", "docs", "show"), cmd_show, "one document with its lines",
                    api=["GET /documents/:id"], roles=ROLES, example="siruk ops docs show <id>")
    p.add_argument("id")
    p = reg.command(("ops", "docs", "new"), cmd_new,
                    "save a draft document (opening_balance, receipt, supplier_return, write_off, count, transfer, bag_opening)",
                    api=["POST /documents", "GET /goods", "GET /goods/:variantId", "GET /locations",
                         "GET /suppliers"], tier="draft",
                    roles=ROLES,
                    example="siruk ops docs new receipt --location shop --supplier Hafo --invoice AB123456 "
                            "--lines '[{\"variant\": \"RC-2KG\", \"quantity\": 12, \"unit_cost_amd\": 1300}]'")
    p.add_argument("type", metavar="TYPE", help=", ".join(D.TYPES))
    p.add_argument("--location", required=True, help="location code or id (the source of a transfer)")
    p.add_argument("--to-location", help="transfer: the destination")
    p.add_argument("--supplier", help="receipt, supplier_return: id, TIN or name")
    p.add_argument("--invoice", help="receipt, supplier_return: the supplier's invoice number")
    p.add_argument("--reason", help=f"write_off: {', '.join(D.REASONS)}")
    p.add_argument("--note")
    p.add_argument("--date", help="document date, ISO (default: now)")
    p.add_argument("--lines", required=True, metavar="FILE|-|JSON",
                   help='[{"variant": "<sku|barcode|uuid>", "quantity": 12 | "2.5kg", "unit_cost_amd": 1300 | '
                        '"amount_amd": 15600, "counted": 9, "target": "<loose sku>", "note": ""}]')
    p.add_argument("--key", help="the same document twice gives the same idempotency key (the draft already made "
                                 "is returned, even if posted); a different --key makes a second one")
    p = reg.command(("ops", "docs", "lines"), cmd_lines, "replace every line of a draft",
                    api=["GET /documents/:id", "GET /goods", "GET /goods/:variantId", "PUT /documents/:id/lines"], tier="draft", roles=ROLES,
                    example="siruk ops docs lines <id> --lines lines.json")
    p.add_argument("id")
    p.add_argument("--lines", required=True, metavar="FILE|-|JSON", help="the full new list, as for `docs new`")
    p = reg.command(("ops", "docs", "post"), cmd_post,
                    "post a draft: stock moves and the document never changes (the dry run shows stock now and after)",
                    api=["GET /documents/:id", "GET /goods/:id", "POST /documents/:id/post"], tier="irreversible",
                    roles=ROLES, example="siruk ops docs post <id>")
    p.add_argument("id")
    p = reg.command(("ops", "docs", "delete"), cmd_delete, "delete a draft (a posted document is never deleted)",
                    api=["GET /documents/:id", "DELETE /documents/:id"], tier="draft", roles=ROLES,
                    example="siruk ops docs delete <id>")
    p.add_argument("id")
