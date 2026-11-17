"""Ops e-invoices and goods links. Field names are copied from the Ops sources:
ops/packages/contracts/src/api/einvoices.ts (EInvoiceDetail, EInvoiceLine, EInvoiceLineProblem, EInvoiceList),
ops/apps/api/src/modules/einvoices/einvoices.controller.ts + dto/*.dto.ts (paths and bodies),
goods-links.controller.ts + goods-link.service.ts (UnlinkedGood, LinkInput) and contracts backoffice.ts (GoodsItem)."""
import copy, json, re

import pytest

from siruk import cli
from siruk.ops import client as O, einvoices as E
from siruk.payload import PayloadError

INV_ID = "5a1e0c36-0f1d-4b7a-9a41-2f7c1d0a7b01"
LINE1 = "b3f0a6d2-1a54-4c0e-8f33-0a7d5e21c001"
LINE2 = "b3f0a6d2-1a54-4c0e-8f33-0a7d5e21c002"
VARIANT = "0b9c3a52-7c1d-4e0a-9d52-3f1d6c1f0a11"
VARIANT2 = "0b9c3a52-7c1d-4e0a-9d52-3f1d6c1f0a12"
LOC = "9c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e5f"
PO = "7e2f1a90-3b4c-4d5e-8f60-1a2b3c4d5e6f"
INVOICE_MADE = "11111111-2222-4333-8444-555555555555"


# contracts/src/api/einvoices.ts: EInvoiceDetail extends EInvoiceListItem, lines are EInvoiceLine
def invoice(**over):
    inv = {"id": INV_ID, "serial": "A6840667000", "status": "new", "supplierName": "Pet House LLC",
           "supplierTin": "01234567", "supplierId": "s1", "issuedAt": "2026-11-10T00:00:00.000Z",
           "pulledAt": "2026-11-11T08:00:00.000Z", "totalMinor": "1300000", "vatMinor": "0", "comment": None,
           "replacesSerial": None, "replacesStatus": None, "replacedBySerial": None, "lineCount": 2,
           "unmatchedCount": 0, "purchaseOrderId": None, "receiptDocumentId": None, "purchaseOrder": None,
           "receipt": None, "suggestedPurchaseOrder": None, "webOrderReasons": [], "linesTotalMinor": "1300000",
           "totalDifferenceMinor": "0", "blockers": [], "problems": [],
           "lines": [line(LINE1, 1, VARIANT, 4, "800000"), line(LINE2, 2, VARIANT2, 10, "500000")]}
    inv.update(over)
    return inv


def line(lid, seq, variant_id, qty, total):
    return {"id": lid, "seqNo": seq, "name": f"Royal Canin {seq}", "unit": "հատ", "quantityText": str(qty),
            "unitPriceMinor": "100000", "totalMinor": total, "classifier": None, "barcode": None,
            "variantId": variant_id, "quantityBase": qty, "matchNote": "barcode",
            "variant": {"id": variant_id, "sku": f"SKU-{seq}", "label": None, "barcode": None,
                        "productName": {"en": "x", "ru": None, "hy": None}, "stockUnit": "pack",
                        "salePriceMinor": "200000", "isDiscontinued": False} if variant_id else None}


# contracts/src/api/backoffice.ts GoodsItem (the fields resolve.variant and the commands read)
def good(variant_id, sku, unit="pack", **over):
    return {"variantId": variant_id, "sku": sku, "barcode": None, "accountingCode": None, "extraBarcodes": [],
            "productName": {"en": sku}, "label": None, "stockUnit": unit, "isActive": True,
            "isDiscontinued": False, "sirukVariantId": 4711, **over}


# goods-link.service.ts UnlinkedGood
def unlinked_good(**over):
    g = {"variantId": INVOICE_MADE, "sku": "INV-900", "name": "Kitten pouch 85g", "measureType": "count",
         "stockUnit": "pack", "barcode": "4607000000001", "stock": [{"locationId": LOC, "quantity": 26,
                                                                      "reserved": 0}],
         "lines": [{"serial": "A6840667000", "supplierTin": "01234567", "supplierName": "Pet House LLC",
                    "issuedAt": None, "name": "Kitten 85", "unit": "հատ", "quantity": "26",
                    "unitPriceMinor": "30000", "barcode": None}], "hafoCandidates": []}
    g.update(over)
    return g


class State:
    """The faked Ops: the invoice can change between two calls the way it does on the server."""

    def __init__(self, ops_fake, inv=None):
        self.inv = inv or invoice()
        ops_fake.on("GET", f"/einvoices/{INV_ID}", lambda p: copy.deepcopy(self.inv))
        ops_fake.on("GET", "/einvoices", lambda p: {"items": [{"id": INV_ID, "serial": self.inv["serial"]}],
                                                    "total": 1, "page": 1, "pageSize": 200})
        ops_fake.on("GET", "/locations", [{"id": LOC, "code": "MAIN"}])
        ops_fake.on("GET", "/goods", lambda p: {"items": [good(VARIANT, "RC-MED-4KG")], "total": 1, "page": 1,
                                                "pageSize": 50})
        for m in ("POST", "PUT", "DELETE"):  # every action answers the invoice (EInvoiceDetail)
            ops_fake.on(m, re.compile(r"/einvoices/[^/]+/.+"), lambda b: copy.deepcopy(self.inv))
        self.fake = ops_fake


@pytest.fixture
def ops(ops_fake):
    return State(ops_fake)


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def writes(fake):
    return [c for c in fake.calls if c[0] != "GET"]


def apply(argv, capsys, fake):
    """Dry run (no write), then the same command with its code; returns the apply exit code."""
    capsys.readouterr()
    assert run([*argv, "--json"]) == 0
    dry = json.loads(capsys.readouterr().out)
    assert dry["dry_run"] is True and writes(fake) == []
    return run([*argv, "--apply", dry["code"]]), dry


# ----------------------------------------------------------- the manifest ----
def manifest(capsys):
    assert run(["commands", "--json"]) == 0
    return {r["name"]: r for r in json.loads(capsys.readouterr().out)}


def test_every_p5_command_exists_with_its_tier(capsys):
    rows = manifest(capsys)
    names = ("list show pull rematch match unmatch link unlink receive post discard settle not-stock").split()
    tiers = {"list": "read", "show": "read", "pull": "real-world", "post": "irreversible", "settle": "irreversible",
             "link": "irreversible", "unlink": "irreversible", "not-stock": "irreversible"}
    for n in names:
        r = rows[f"ops einvoices {n}"]
        assert r["backend"] == "ops" and r["api"] and r["help"] and r["roles"] and r["example"], n
        assert r["tier"] == tiers.get(n, "draft"), n
    assert "GET /goods/:variantId" in rows["ops einvoices match"]["api"]
    assert "GET /goods/:variantId" in rows["ops goods-links link"]["api"]
    for n, tier in (("list", "read"), ("link", "irreversible")):
        r = rows[f"ops goods-links {n}"]
        assert r["tier"] == tier and r["api"] and r["help"] and r["roles"] and r["example"]
    assert "POST /einvoices/pull" in rows["ops einvoices pull"]["api"]


def test_no_command_reaches_the_connector_or_acknowledges_a_replacement(capsys):
    for r in manifest(capsys).values():
        for api in r["api"]:
            path = api.split(" ")[-1]
            assert not path.startswith("/connectors") and not path.endswith("acknowledge-replacement"), r["name"]
    assert not [n for n in manifest(capsys) if "acknowledge" in n or "connector" in n]


# ----------------------------------------------------------------- reads ----
def test_list_passes_the_dto_query(ops_fake, capsys):
    ops_fake.on("GET", "/einvoices", {"items": [], "total": 0, "page": 1, "pageSize": 50})
    assert run(["ops", "einvoices", "list", "--status", "new", "--search", "pet", "--from", "2026-11-01",
                "--to", "2026-11-15", "--json"]) == 0
    assert ops_fake.calls == [("GET", "/einvoices", {"status": "new", "q": "pet", "from": "2026-11-01",
                                                      "to": "2026-11-15"})]
    assert json.loads(capsys.readouterr().out)["total"] == 0


def test_show_by_serial_prints_lines_and_json_is_unmodified(ops, capsys):
    assert run(["ops", "einvoices", "show", "a6840667000"]) == 0
    out = capsys.readouterr().out
    assert "A6840667000" in out and "SKU-1" in out and "13000 AMD" in out
    assert run(["ops", "einvoices", "show", INV_ID, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == ops.inv


def test_unknown_serial_is_refused(ops, capsys):
    assert run(["ops", "einvoices", "show", "NOPE"]) == 1
    assert "0 e-invoices" in capsys.readouterr().err


# ---------------------------------------------------- bodies of the writes ----
def test_match_puts_variant_and_quantity_base(ops, capsys):
    argv = ["ops", "einvoices", "match", "A6840667000", "2", "RC-MED-4KG", "6"]
    code, dry = apply(argv, capsys, ops.fake)
    assert code == 0 and dry["tier"] == "draft"
    # einvoices.controller.ts setLine + match-einvoice-line.dto.ts {variantId, quantityBase}
    assert writes(ops.fake) == [("PUT", f"/einvoices/{INV_ID}/lines/{LINE2}/match",
                                 {"variantId": VARIANT, "quantityBase": 6})]


def test_match_converts_a_loose_quantity_and_refuses_zero(ops, capsys):
    ops.fake.on("GET", "/goods", {"items": [good(VARIANT, "RC-MED-4KG", unit="loose")], "total": 1, "page": 1,
                                  "pageSize": 50})
    code, _ = apply(["ops", "einvoices", "match", INV_ID, LINE1, "RC-MED-4KG", "1.8kg"], capsys, ops.fake)
    assert code == 0 and writes(ops.fake)[0][2] == {"variantId": VARIANT, "quantityBase": 1800}
    ops.fake.calls.clear()
    assert run(["ops", "einvoices", "match", INV_ID, "1", "RC-MED-4KG", "0"]) == 1
    assert writes(ops.fake) == []


def test_unmatch_rematch_discard_not_stock_unlink_paths(ops, capsys):
    for sub, extra, method, tail in (("unmatch", ["1"], "DELETE", f"/lines/{LINE1}/match"),
                                     ("rematch", [], "POST", "/rematch"),
                                     ("discard", [], "POST", "/discard-draft")):
        ops.fake.calls.clear()
        code, dry = apply(["ops", "einvoices", sub, INV_ID, *extra], capsys, ops.fake)
        assert code == 0 and dry["tier"] == "draft", sub
        assert writes(ops.fake) == [(method, f"/einvoices/{INV_ID}{tail}", None)], sub


def order(kind="restock"):
    # hafo.ts HafoPurchaseOrder (id, number, kind, status); GET /purchase-orders/:id
    return {"id": PO, "number": "PO-12", "kind": kind, "status": "placed"}


def test_link_posts_the_purchase_order_id_and_says_whether_a_payable_posts(ops, capsys):
    ops.fake.on("GET", f"/purchase-orders/{PO}", order("restock"))
    code, dry = apply(["ops", "einvoices", "link", INV_ID, PO], capsys, ops.fake)
    # einvoices.controller.ts link + link-einvoice.dto.ts {purchaseOrderId}
    assert code == 0 and dry["tier"] == "irreversible" and "nothing is booked" in dry["summary"]
    assert writes(ops.fake) == [("POST", f"/einvoices/{INV_ID}/link", {"purchaseOrderId": PO})]
    ops.fake.on("GET", f"/purchase-orders/{PO}", order("web_order"))
    capsys.readouterr()
    assert run(["ops", "einvoices", "link", INV_ID, PO, "--json"]) == 0
    assert "PASSES THROUGH" in json.loads(capsys.readouterr().out)["summary"]


def test_a_link_code_is_bound_to_the_order_kind_and_invoice_status(ops, capsys):
    ops.fake.on("GET", f"/purchase-orders/{PO}", order("restock"))
    assert run(["ops", "einvoices", "link", INV_ID, PO, "--json"]) == 0
    code = json.loads(capsys.readouterr().out)["code"]
    ops.fake.on("GET", f"/purchase-orders/{PO}", order("web_order"))
    assert run(["ops", "einvoices", "link", INV_ID, PO, "--apply", code]) == 1
    ops.fake.on("GET", f"/purchase-orders/{PO}", order("restock"))
    ops.inv = invoice(status="not_stock")
    assert run(["ops", "einvoices", "link", INV_ID, PO, "--apply", code]) == 1
    assert writes(ops.fake) == []


def test_unlink_is_irreversible_and_bound_to_the_invoice_status(ops, capsys):
    assert run(["ops", "einvoices", "unlink", INV_ID, "--json"]) == 0
    dry = json.loads(capsys.readouterr().out)
    assert dry["tier"] == "irreversible" and "REVERSED" not in dry["summary"]
    ops.inv = invoice(status="passthrough", purchaseOrderId=PO)
    assert run(["ops", "einvoices", "unlink", INV_ID, "--apply", dry["code"]]) == 1
    assert writes(ops.fake) == []
    capsys.readouterr()
    code, dry = apply(["ops", "einvoices", "unlink", INV_ID], capsys, ops.fake)
    assert code == 0 and "REVERSED" in dry["summary"]
    assert writes(ops.fake) == [("DELETE", f"/einvoices/{INV_ID}/link", None)]


def test_not_stock_is_irreversible_and_bound_to_status_and_totals(ops, capsys):
    code, dry = apply(["ops", "einvoices", "not-stock", INV_ID], capsys, ops.fake)
    assert code == 0 and dry["tier"] == "irreversible" and "13000 AMD" in dry["summary"]
    assert writes(ops.fake) == [("POST", f"/einvoices/{INV_ID}/not-stock", None)]
    ops.fake.calls.clear()
    capsys.readouterr()
    assert run(["ops", "einvoices", "not-stock", INV_ID, "--json"]) == 0
    code = json.loads(capsys.readouterr().out)["code"]
    ops.inv["totalMinor"] = "1300100"
    assert run(["ops", "einvoices", "not-stock", INV_ID, "--apply", code]) == 1
    assert writes(ops.fake) == []


def test_receive_posts_the_location_and_shows_override_in_the_dry_run(ops, capsys):
    argv = ["ops", "einvoices", "receive", INV_ID, "--location", "main"]
    code, dry = apply(argv, capsys, ops.fake)
    # receive-einvoice.dto.ts {locationId, override?}: override is left out unless asked for
    assert code == 0 and writes(ops.fake) == [("POST", f"/einvoices/{INV_ID}/receive", {"locationId": LOC})]
    assert "OVERRIDE" not in dry["summary"]

    ops.inv = invoice(problems=[{"lineId": LINE1, "seqNo": 1, "variantId": VARIANT, "kind": "cost_jump",
                                 "message": "cost moved 40%"}])
    ops.fake.calls.clear()
    assert run(argv) == 1 and "cost moved 40%" in capsys.readouterr().err
    code, dry = apply([*argv, "--override"], capsys, ops.fake)
    assert code == 0 and dry["requests"][0]["body"] == {"locationId": LOC, "override": True}
    assert "OVERRIDE" in dry["summary"]
    assert writes(ops.fake) == [("POST", f"/einvoices/{INV_ID}/receive", {"locationId": LOC, "override": True})]


def test_receive_counts_only_the_lines_the_server_will_place(ops, capsys):
    # einvoice-receive.service / invoice-goods.ts: a good is made only for a line whose matchNote is NO_MATCH
    ops.inv = invoice(unmatchedCount=1, blockers=["unmatched_lines"])
    ops.inv["lines"][1].update(variantId=None, quantityBase=None, variant=None, matchNote=E.NO_MATCH)
    code, dry = apply(["ops", "einvoices", "receive", INV_ID, "--location", "MAIN"], capsys, ops.fake)
    assert code == 0 and "1 unmatched line(s) get a good" in dry["summary"]
    assert "stays even if the draft is discarded" in dry["summary"] and len(writes(ops.fake)) == 1


def test_receive_refuses_a_line_cleared_by_hand_before_any_write(ops, capsys):
    # einvoice-rules.ts CLEARED_BY_HAND; the server answers 409 LINES_UNMATCHED
    ops.inv = invoice(unmatchedCount=1, blockers=["unmatched_lines"])
    ops.inv["lines"][1].update(variantId=None, quantityBase=None, variant=None, matchNote="Match removed by hand")
    assert run(["ops", "einvoices", "receive", INV_ID, "--location", "MAIN"]) == 1
    assert "line(s) 2" in capsys.readouterr().err and writes(ops.fake) == []


def test_receive_refuses_a_non_new_invoice_and_one_without_lines(ops, capsys):
    ops.inv = invoice(status="matched")
    assert run(["ops", "einvoices", "receive", INV_ID, "--location", "MAIN"]) == 1
    ops.inv = invoice(lines=[], lineCount=0, blockers=["no_lines"])
    assert run(["ops", "einvoices", "receive", INV_ID, "--location", "MAIN"]) == 1
    assert writes(ops.fake) == []


def draft_invoice(**over):
    receipt = {"documentId": "d1", "number": "RC-0001", "status": "draft", "locationId": LOC,
               "totalMinor": "1300000"}
    return invoice(status="matched", receipt=receipt, receiptDocumentId="d1", **over)


def test_post_has_no_body_and_is_irreversible(ops, capsys):
    ops.inv = draft_invoice()
    code, dry = apply(["ops", "einvoices", "post", INV_ID], capsys, ops.fake)
    assert code == 0 and dry["tier"] == "irreversible"
    assert writes(ops.fake) == [("POST", f"/einvoices/{INV_ID}/post", None)]


def test_post_books_an_invoice_whose_receipt_was_already_posted(ops, capsys):
    # einvoice-receive.service.ts post: a receipt posted on the documents screen still has to be booked here
    ops.inv = draft_invoice()
    ops.inv["receipt"]["status"] = "posted"
    code, dry = apply(["ops", "einvoices", "post", INV_ID], capsys, ops.fake)
    assert code == 0 and "already posted" in dry["summary"]
    assert writes(ops.fake) == [("POST", f"/einvoices/{INV_ID}/post", None)]


def test_post_without_a_draft_is_refused(ops, capsys):
    assert run(["ops", "einvoices", "post", INV_ID]) == 1
    assert "receive" in capsys.readouterr().err


def test_settle_posts_accept_differences(ops, capsys):
    order = {"id": PO, "number": "PO-12", "kind": "restock", "status": "received", "externalRef": None,
             "orderReceived": True}
    ops.inv = invoice(purchaseOrder=order, purchaseOrderId=PO)
    code, dry = apply(["ops", "einvoices", "settle", INV_ID], capsys, ops.fake)
    # einvoices.controller.ts settleOrder + settle-order-einvoice.dto.ts {acceptDifferences?}
    assert code == 0 and dry["tier"] == "irreversible"
    assert writes(ops.fake) == [("POST", f"/einvoices/{INV_ID}/settle-order", {})]
    ops.fake.calls.clear()
    code, _ = apply(["ops", "einvoices", "settle", INV_ID, "--accept-differences"], capsys, ops.fake)
    assert code == 0 and writes(ops.fake) == [("POST", f"/einvoices/{INV_ID}/settle-order",
                                               {"acceptDifferences": True})]


def test_settle_needs_an_order_already_received_from_and_matched_lines(ops, capsys):
    assert run(["ops", "einvoices", "settle", INV_ID]) == 1
    order = {"id": PO, "number": "PO-12", "kind": "restock", "status": "received", "externalRef": None,
             "orderReceived": True}
    ops.inv = invoice(purchaseOrder=order, purchaseOrderId=PO, unmatchedCount=1)
    assert run(["ops", "einvoices", "settle", INV_ID]) == 1
    assert writes(ops.fake) == []


def test_pull_is_real_world_and_sends_from_and_to(ops_fake, capsys):
    argv = ["ops", "einvoices", "pull", "--from", "2026-11-01", "--to", "2026-11-15"]
    assert run([*argv, "--json"]) == 0
    dry = json.loads(capsys.readouterr().out)
    assert dry["tier"] == "real-world" and writes(ops_fake) == []
    ops_fake.on("POST", "/einvoices/pull", {"fetched": 3, "created": 3, "notStock": 0, "replaced": 0,
                                           "passthrough": 0, "needMatching": 3, "failed": 0, "failures": []})
    assert run([*argv, "--apply", dry["code"]]) == 0
    # pull-einvoices.dto.ts {from, to}
    assert writes(ops_fake) == [("POST", "/einvoices/pull", {"from": "2026-11-01", "to": "2026-11-15"})]


@pytest.mark.parametrize("a,b", [("2026-11-15", "2026-11-01"), ("11/01/2026", "2026-11-02")])
def test_pull_refuses_bad_days(ops_fake, a, b):
    assert run(["ops", "einvoices", "pull", "--from", a, "--to", b]) == 1
    assert ops_fake.calls == []


# ---------------------------------------------------------- goods links ----
def link_routes(fake, entry=None, target=None):
    fake.on("POST", re.compile(r"/goods-links/[^/]+/link"), {"merged": True})
    fake.on("GET", "/goods-links/unlinked", [entry or unlinked_good()])
    t = target or good(VARIANT, "RC-MED-4KG")
    made = good(INVOICE_MADE, "INV-900", sirukVariantId=None, barcode="4607000000001")
    fake.on("GET", "/goods", lambda p: {"items": [made if (p or {}).get("q") == "INV-900" else t],
                                        "total": 1, "page": 1, "pageSize": 50})


def test_goods_links_list(ops_fake, capsys):
    ops_fake.on("GET", "/goods-links/unlinked", [unlinked_good()])
    assert run(["ops", "goods-links", "list"]) == 0
    assert "INV-900" in capsys.readouterr().out
    assert run(["ops", "goods-links", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == [unlinked_good()]


def test_goods_link_posts_target_factor_evidence_source(ops_fake, capsys):
    link_routes(ops_fake)
    argv = ["ops", "goods-links", "link", "INV-900", "RC-MED-4KG", "--evidence", "EAN 4607000000001",
            "--factor", "26", "--source", "claude"]
    code, dry = apply(argv, capsys, ops_fake)
    # goods-links.controller.ts link + link-good.dto.ts {targetVariantId, factor?, evidence?, source?}
    assert code == 0 and dry["tier"] == "irreversible"
    assert writes(ops_fake) == [("POST", f"/goods-links/{INVOICE_MADE}/link",
                                 {"targetVariantId": VARIANT, "factor": 26, "evidence": "EAN 4607000000001",
                                  "source": "claude"})]


def test_goods_link_needs_evidence_and_an_unlinked_source(ops_fake, capsys):
    link_routes(ops_fake)
    assert run(["ops", "goods-links", "link", "INV-900", "RC-MED-4KG"]) == 1
    assert "evidence" in capsys.readouterr().err
    ops_fake.on("GET", "/goods-links/unlinked", [])
    assert run(["ops", "goods-links", "link", "INV-900", "RC-MED-4KG", "--evidence", "x"]) == 1
    assert writes(ops_fake) == []


def test_goods_link_code_changes_when_the_good_changes(ops_fake, capsys):
    link_routes(ops_fake)
    argv = ["ops", "goods-links", "link", "INV-900", "RC-MED-4KG", "--evidence", "EAN"]
    assert run([*argv, "--json"]) == 0
    code = json.loads(capsys.readouterr().out)["code"]
    link_routes(ops_fake, entry=unlinked_good(stock=[{"locationId": LOC, "quantity": 99, "reserved": 0}]))
    assert run([*argv, "--apply", code]) == 1
    assert writes(ops_fake) == []


# ----------------------------------------------------------- the guard ----
def test_a_changed_match_invalidates_the_post_code(ops, capsys):
    ops.inv = draft_invoice()
    assert run(["ops", "einvoices", "post", INV_ID, "--json"]) == 0
    code = json.loads(capsys.readouterr().out)["code"]
    ops.inv["lines"][1]["quantityBase"] = 100
    assert run(["ops", "einvoices", "post", INV_ID, "--apply", code]) == 1
    assert "state that has since changed" in capsys.readouterr().err
    assert writes(ops.fake) == []
    ops.inv = draft_invoice()
    ops.inv["lines"][0]["variantId"] = VARIANT2
    assert run(["ops", "einvoices", "post", INV_ID, "--apply", code]) == 1
    assert writes(ops.fake) == []


def test_a_changed_invoice_invalidates_the_settle_code(ops, capsys):
    order = {"id": PO, "number": "PO-12", "kind": "restock", "status": "received", "externalRef": None,
             "orderReceived": True}
    ops.inv = invoice(purchaseOrder=order, purchaseOrderId=PO)
    assert run(["ops", "einvoices", "settle", INV_ID, "--json"]) == 0
    code = json.loads(capsys.readouterr().out)["code"]
    ops.inv["totalMinor"] = "1300100"
    assert run(["ops", "einvoices", "settle", INV_ID, "--apply", code]) == 1
    assert writes(ops.fake) == []


def test_dry_runs_record_no_write(ops, capsys):
    ops.inv = draft_invoice()
    ops.fake.on("GET", f"/purchase-orders/{PO}", order())
    for argv in (["post", INV_ID], ["match", INV_ID, "1", "RC-MED-4KG", "1"], ["unmatch", INV_ID, "1"],
                 ["rematch", INV_ID], ["link", INV_ID, PO], ["unlink", INV_ID], ["discard", INV_ID],
                 ["not-stock", INV_ID], ["pull", "--from", "2026-11-01", "--to", "2026-11-02"]):
        assert run(["ops", "einvoices", *argv]) == 0, argv
    assert "nothing sent" in capsys.readouterr().out
    assert writes(ops.fake) == []


def test_post_with_an_unknown_outcome_exits_3_with_the_show_check(ops, capsys):
    ops.inv = draft_invoice()
    ops.fake.on("POST", f"/einvoices/{INV_ID}/post", O.UnknownOutcome(0, "POST", f"/einvoices/{INV_ID}/post",
                                                                       "network error: reset"))
    code, _ = apply(["ops", "einvoices", "post", INV_ID], capsys, ops.fake)
    assert code == 3
    assert f"siruk ops einvoices show {INV_ID}" in capsys.readouterr().err
    assert len(writes(ops.fake)) == 1


def test_an_api_refusal_on_post_exits_2(ops, capsys):
    ops.inv = draft_invoice()
    ops.fake.on("POST", f"/einvoices/{INV_ID}/post", O.OpsError(409, "POST", f"/einvoices/{INV_ID}/post",
                                                                 '{"message": "no", "error": "NO_DRAFT"}'))
    code, _ = apply(["ops", "einvoices", "post", INV_ID], capsys, ops.fake)
    assert code == 2


def test_every_write_is_allowed_by_the_policy():
    from siruk.ops import policy
    inv = invoice()
    for steps, *_ in (E.rematch(inv), E.link(inv, order()), E.unlink(inv), E.post(draft_invoice()), E.discard(inv),
                      E.not_stock(inv), E.pull("2026-11-01", "2026-11-02")):
        assert all(policy.allowed(s.method, s.path) is None for s in steps)
    assert policy.allowed("POST", f"/einvoices/{INV_ID}/acknowledge-replacement")
    assert policy.allowed("PUT", "/connectors/einvoice")


def test_line_of_takes_a_number_or_an_id():
    inv = invoice()
    assert E.line_of(inv, "2")["id"] == LINE2 and E.line_of(inv, LINE1)["seqNo"] == 1
    with pytest.raises(PayloadError):
        E.line_of(inv, "9")
