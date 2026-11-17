"""Stock is a ledger (CLAUDE.md 10a): an existing variant's count changes only
through /stock/variants/<id>, never the product PUT. New variants get initial_stock on a flat-price
server only. reference/admin-api.md → "Stock". When the admin reports stock_in_ops the ledger lives
in Siruk Ops and every write here is refused with a pointer to `siruk ops docs new …`.
"""
from siruk import client as _client
from siruk.payload import PayloadError

MAIN_WAREHOUSE = 1
SET_REASONS = ("correction", "damaged", "lost", "found", "expired", "write_off")
WRITE_OFF_REASONS = ("damaged", "lost", "expired", "write_off")


def movements(variant_id):
    r = _client.default().get(f"/stock/variants/{int(variant_id)}/movements") or {}
    return r.get("data") if isinstance(r, dict) else r


def _not_in_ops(post):
    """GET /stock says in meta.stock_in_ops whether Siruk Ops keeps the ledger; an absent flag means this server does."""
    try:
        r = _client.default().get("/stock?perPage=1") or {}
    except _client.ApiError as e:
        if e.status == 404:
            return
        raise
    if (r.get("meta") or {}).get("stock_in_ops"):
        raise PayloadError(f"this server keeps stock in Siruk Ops — post it there: `siruk ops docs new {post} …`")


def _write(method, path, body, dry_run, action):
    if dry_run:
        return {"action": action, "dry_run": True, "written": False, "request": f"{method} {path}", "body": body}
    r = _client.default().request(method, path, body=body)
    return {"action": action, "dry_run": False, "written": True, "request": f"{method} {path}",
            "body": body, "response": (r or {}).get("data", r)}


def _need_note(note):
    if not (note or "").strip():
        raise PayloadError("a stock change needs a note saying why")


def receive(variant_id, quantity, note, unit_cost=None, warehouse_id=MAIN_WAREHOUSE, dry_run=False):
    if quantity is None or float(quantity) <= 0:
        raise PayloadError("quantity must be > 0")
    _need_note(note)
    _not_in_ops("receipt")
    body = {"warehouse_id": warehouse_id, "quantity": quantity, "note": note}
    if unit_cost is not None:
        body["unit_cost"] = unit_cost
    return _write("POST", f"/stock/variants/{int(variant_id)}/receive", body, dry_run, "stock_receive")


def write_off(variant_id, quantity, reason, note, warehouse_id=MAIN_WAREHOUSE, dry_run=False):
    if quantity is None or float(quantity) <= 0:
        raise PayloadError("quantity must be > 0")
    if reason not in WRITE_OFF_REASONS:
        raise PayloadError(f"reason must be one of {WRITE_OFF_REASONS}")
    _need_note(note)
    _not_in_ops("write_off")
    body = {"warehouse_id": warehouse_id, "quantity": quantity, "reason": reason, "note": note}
    return _write("POST", f"/stock/variants/{int(variant_id)}/write-off", body, dry_run, "stock_write_off")


def set_count(variant_id, on_hand, reason, note, warehouse_id=MAIN_WAREHOUSE, dry_run=False):
    if on_hand is None or float(on_hand) < 0:
        raise PayloadError("on_hand must be ≥ 0")
    if reason not in SET_REASONS:
        raise PayloadError(f"reason must be one of {SET_REASONS}")
    _need_note(note)
    _not_in_ops("count")
    body = {"warehouse_id": warehouse_id, "on_hand": on_hand, "reason": reason, "note": note}
    return _write("PUT", f"/stock/variants/{int(variant_id)}", body, dry_run, "stock_set")
