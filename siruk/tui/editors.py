"""The TUI's modal screens. Each editor builds a request, asks siruk.* for a dry
run, shows the diff in ConfirmScreen, and only then writes — through the same
functions (and rules) as the CLI and the MCP server."""
import json

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (Button, Checkbox, DataTable, Input, Label, Rule, Select, SelectionList,
                             Static, TextArea)

from siruk import client as _client
from siruk import config, products, stock, translations
from siruk.payload import VTEXT, PayloadError

TEXT_LABELS = {"about_this_item": "About this item", "ingredient_information": "Ingredients",
               "feeding_instructions": "Feeding"}


def short(x, n=60):
    if x is None:
        return "—"
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def err_text(e):
    return str(e) if isinstance(e, (PayloadError, _client.ApiError)) else f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------- confirm ----
class ConfirmScreen(ModalScreen[bool]):
    """The last stop before a write: what changes, where, and a deliberate yes."""
    BINDINGS = [("escape", "dismiss(False)", "Cancel"), ("y", "dismiss(True)", "Write")]

    def __init__(self, title, diff, warnings=(), body_lines=None):
        super().__init__()
        self.title_text, self.diff, self.warnings, self.body_lines = title, diff, list(warnings), body_lines

    def compose(self) -> ComposeResult:
        prod = config.is_production()
        with Vertical(id="dialog", classes="confirm"):
            yield Label(f"[b]{self.title_text}[/b]")
            yield Label(("[reverse red] PRODUCTION [/] " if prod else "[reverse green] demo [/] ")
                        + config.api_base(), classes="env")
            table = DataTable(id="diff", zebra_stripes=True, cursor_type="row")
            yield table
            for w in self.warnings:
                yield Label(f"[yellow]⚠ {w}[/]")
            if self.body_lines:
                yield Static("\n".join(self.body_lines), classes="body")
            with Horizontal(classes="buttons"):
                yield Button("Write (y)", id="ok", variant="error" if prod else "success")
                yield Button("Cancel (esc)", id="cancel")

    def on_mount(self):
        t = self.query_one("#diff", DataTable)
        t.add_columns("variant", "field", "old", "new")
        for d in self.diff:
            t.add_row(d.get("sku") or "product", d["field"], short(d.get("old")), short(d.get("new")))
        if not self.diff:
            t.add_row("—", "no changes", "", "")
            self.query_one("#ok", Button).disabled = True

    @on(Button.Pressed, "#ok")
    def ok(self):
        self.dismiss(True)

    @on(Button.Pressed, "#cancel")
    def cancel(self):
        self.dismiss(False)


class BaseEditor(ModalScreen[bool]):
    """Preview → ConfirmScreen → write → dismiss(True) so the caller reloads."""
    BINDINGS = [("escape", "dismiss(False)", "Cancel"), ("ctrl+s", "preview", "Preview & write")]

    def build(self):
        """→ (title, run(dry_run) → result) or raise PayloadError."""
        raise NotImplementedError

    def action_preview(self):
        self.run_preview()

    @on(Button.Pressed, "#preview")
    def _pressed_preview(self):
        self.run_preview()

    @on(Button.Pressed, "#cancel")
    def _pressed_cancel(self):
        self.dismiss(False)

    def run_preview(self):
        try:
            title, run = self.build()
        except (PayloadError, ValueError) as e:
            self.notify(err_text(e), severity="error", timeout=10)
            return
        self._dry(title, run)

    @work(thread=True, exclusive=True, group="editor")
    def _dry(self, title, run):
        try:
            res = run(True)
        except Exception as e:
            self.app.call_from_thread(self.notify, err_text(e), severity="error", timeout=12)
            return
        d = res.as_dict() if hasattr(res, "as_dict") else res
        diff = d.get("diff")
        if diff is None:  # stock: show the request body as the diff
            diff = [{"sku": None, "field": k, "old": None, "new": v} for k, v in (d.get("body") or {}).items()]
        self.app.call_from_thread(self._ask, title, diff, d.get("warnings") or [], run)

    def _ask(self, title, diff, warns, run):
        def done(yes):
            if yes:
                self._write(run)
        self.app.push_screen(ConfirmScreen(title, diff, warns), done)

    @work(thread=True, exclusive=True, group="editor")
    def _write(self, run):
        try:
            run(False)
        except Exception as e:
            self.app.call_from_thread(self.notify, err_text(e), severity="error", timeout=15)
            return
        self.app.call_from_thread(self.notify, "written and read back ✓", severity="information")
        self.app.call_from_thread(self.dismiss, True)

    def buttons(self):
        with Horizontal(classes="buttons"):
            yield Button("Preview & write (ctrl+s)", id="preview", variant="primary")
            yield Button("Cancel (esc)", id="cancel")


# ---------------------------------------------------------------- variant ----
NUM_FIELDS = (("price", "Sale price (AMD, pack)"), ("cost_price", "Cost (AMD)"),
              ("compare_at_price", "Compare-at price"), ("content", "Net content (g / ml / pcs)"),
              ("pack_count", "Pack count"))
STR_FIELDS = (("name", "Label"), ("barcode", "Barcode (EAN / 5-digit PLU)"),
              ("accounting_code", "ArmSoft code"), ("price_source_url", "Price source url"))


class VariantEditor(BaseEditor):
    """Edit one variant of a product. `product` is a fresh en GET; `ptype` the live product
    type; `menu` = {attribute id: {name, inputType, values: [(label, id)]}}."""

    def __init__(self, product, variant, ptype, menu):
        super().__init__()
        self.product, self.v, self.ptype, self.menu = product, variant, ptype, menu

    def compose(self) -> ComposeResult:
        v = self.v
        with Vertical(id="dialog", classes="editor"):
            yield Label(f"[b]Edit variant[/b] {v.get('sku')} — {self.product.get('name')}  "
                        f"[dim](product {self.product.get('id')}, {self.ptype.get('name')})[/]")
            with VerticalScroll():
                with Grid(classes="form"):
                    for key, label in NUM_FIELDS + STR_FIELDS:
                        yield Label(label)
                        val = v.get(key)
                        yield Input("" if val is None else str(val), id=f"f-{key}",
                                    type="number" if key in dict(NUM_FIELDS) else "text")
                yield Rule()
                for a in sorted(self.ptype.get("attributes") or [], key=lambda a: a.get("position") or 0):
                    m = self.menu.get(a["id"]) or {}
                    cur = (v.get("attribute_values") or {}).get(str(a["id"])) or []
                    tag = "option" if a.get("role") == "option" else "attribute"
                    req = " *" if a.get("isRequired") else ""
                    yield Label(f"{a['name']}{req} [dim]({tag})[/]")
                    if a.get("role") != "option" and (m.get("inputType") or a.get("inputType")) == "multiselect":
                        yield SelectionList(*[(lbl, vid, vid in cur) for lbl, vid in m.get("values") or []],
                                            id=f"a-{a['id']}", classes="multi")
                    else:
                        yield Select(m.get("values") or [], id=f"a-{a['id']}", allow_blank=True,
                                     value=cur[0] if cur else Select.NULL, prompt="— none —")
                yield Rule()
                for f in VTEXT:
                    yield Label(f"{TEXT_LABELS[f]} [dim](en)[/]")
                    yield TextArea(v.get(f) or "", id=f"t-{f}", classes="text")
                yield Checkbox("The user explicitly approved a price at or below cost", id="below-cost")
            yield from self.buttons()

    def _patch(self):
        v, patch = self.v, {}
        for key, _ in NUM_FIELDS:
            raw = self.query_one(f"#f-{key}", Input).value.strip()
            new = None if raw == "" else (float(raw) if "." in raw else int(raw))
            old = v.get(key)
            if (old if old is None else float(old)) != (new if new is None else float(new)):
                if key in ("price", "cost_price") and new is None:
                    raise PayloadError(f"{key} cannot be empty")
                patch[key] = new
        for key, _ in STR_FIELDS:
            new = self.query_one(f"#f-{key}", Input).value.strip()
            if new != (v.get(key) or ""):
                patch[key] = new or None
        attrs = {}
        for a in self.ptype.get("attributes") or []:
            cur = sorted((v.get("attribute_values") or {}).get(str(a["id"])) or [])
            w = self.query_one(f"#a-{a['id']}")
            if isinstance(w, SelectionList):
                new = sorted(w.selected)
            else:
                new = [] if w.value in (Select.NULL, Select.BLANK, None) else [w.value]
            if new != cur:
                attrs[str(a["id"])] = new
        if attrs:
            patch["attribute_values"] = attrs
        for f in VTEXT:
            new = self.query_one(f"#t-{f}", TextArea).text
            if new != (v.get(f) or ""):
                patch[f] = new
        return patch

    def build(self):
        patch = self._patch()
        if not patch:
            raise PayloadError("nothing changed")
        allow = self.query_one("#below-cost", Checkbox).value
        pid, sku = self.product["id"], self.v["sku"]
        return (f"Update variant {sku} of product {pid}",
                lambda dry: products.update_variant(pid, sku, patch, dry_run=dry, allow_below_cost=allow))


# ------------------------------------------------------------ translation ----
class TranslationEditor(BaseEditor):
    """ru / hy name and variant texts, English shown above each box."""

    def __init__(self, product_id, lang="ru"):
        super().__init__()
        self.pid, self.lang, self.cur = product_id, lang, None

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog", classes="editor"):
            with Horizontal(classes="toolbar"):
                yield Label(f"[b]Translation[/b] of product {self.pid}  ")
                yield Select([("Русский (ru)", "ru"), ("Հայերեն (hy)", "hy")], value=self.lang,
                             allow_blank=False, id="lang")
            yield VerticalScroll(Label("loading…"), id="tr-body")
            yield from self.buttons()

    def on_mount(self):
        self.load()

    @on(Select.Changed, "#lang")
    def lang_changed(self, ev):
        if ev.value != self.lang:
            self.lang = ev.value
            self.load()

    @work(thread=True, exclusive=True, group="tr-load")
    def load(self):
        try:
            cur = translations.current(self.pid, self.lang)
        except Exception as e:
            self.app.call_from_thread(self.notify, err_text(e), severity="error")
            return
        self.app.call_from_thread(self._fill, cur)

    def _fill(self, cur):
        self.cur = cur
        body = self.query_one("#tr-body", VerticalScroll)
        body.remove_children()
        lg = self.lang
        widgets = [Label(f"Name [dim](en: {cur['en_name']})[/]"),
                   Input(cur.get("name") if cur.get("name") != cur["en_name"] else "", id="tr-name",
                         placeholder=f"{lg} name")]
        for i, (sku, fields) in enumerate(cur["variants"].items()):
            widgets.append(Rule())
            widgets.append(Label(f"[b]{sku}[/b]"))
            for f in VTEXT:
                widgets.append(Label(f"{TEXT_LABELS[f]} [dim]en: {short(fields[f]['en'], 90)}[/]"))
                own = fields[f][lg] if fields[f][lg] != fields[f]["en"] else ""
                widgets.append(TextArea(own, id=f"tr-{i}-{f}", classes="text"))
        body.mount_all(widgets)

    def build(self):
        if not self.cur:
            raise PayloadError("still loading")
        tr, vs = {}, {}
        name = self.query_one("#tr-name", Input).value.strip()
        if name:
            tr["name"] = name
        for i, (sku, fields) in enumerate(self.cur["variants"].items()):
            for f in VTEXT:
                new = self.query_one(f"#tr-{i}-{f}", TextArea).text
                own = fields[f][self.lang] if fields[f][self.lang] != fields[f]["en"] else ""
                if new != own and new.strip():
                    vs.setdefault(sku, {})[f] = new
        if vs:
            tr["variants"] = vs
        if not tr:
            raise PayloadError("nothing changed")
        pid, lang = self.pid, self.lang
        return (f"Store the {lang} translation of product {pid}",
                lambda dry: translations.set_translation(pid, lang, tr, dry_run=dry))


# ------------------------------------------------------------------ stock ----
class StockEditor(BaseEditor):
    def __init__(self, variant):
        super().__init__()
        self.v = variant

    def compose(self) -> ComposeResult:
        v = self.v
        levels = ", ".join(f"{l.get('warehouse_name')}: {l.get('on_hand')} on hand / {l.get('available')} available"
                           for l in v.get("stock_levels") or []) or "no stock rows"
        with Vertical(id="dialog", classes="small"):
            yield Label(f"[b]Stock[/b] {v.get('sku')} — {v.get('name')}")
            yield Label(f"[dim]{levels}[/]")
            with Grid(classes="form"):
                yield Label("Action")
                yield Select([("Receive", "receive"), ("Write off", "write-off"), ("Set on-hand count", "set")],
                             value="receive", allow_blank=False, id="s-action")
                yield Label("Quantity / on hand")
                yield Input(id="s-qty", type="number")
                yield Label("Reason (write-off / set)")
                yield Select([(r, r) for r in stock.SET_REASONS], value="correction", allow_blank=False,
                             id="s-reason")
                yield Label("Unit cost (receive)")
                yield Input(id="s-cost", type="number")
                yield Label("Note (required)")
                yield Input(id="s-note")
            yield from self.buttons()

    def build(self):
        act = self.query_one("#s-action", Select).value
        raw = self.query_one("#s-qty", Input).value.strip()
        if not raw:
            raise PayloadError("quantity is required")
        qty = float(raw)
        qty = int(qty) if qty.is_integer() else qty
        reason = self.query_one("#s-reason", Select).value
        note = self.query_one("#s-note", Input).value
        cost_raw = self.query_one("#s-cost", Input).value.strip()
        cost = float(cost_raw) if cost_raw else None
        vid = self.v["id"]
        if act == "receive":
            run = lambda dry: stock.receive(vid, qty, note, cost, dry_run=dry)
        elif act == "write-off":
            run = lambda dry: stock.write_off(vid, qty, reason, note, dry_run=dry)
        else:
            run = lambda dry: stock.set_count(vid, qty, reason, note, dry_run=dry)
        return f"Stock {act} on variant {vid} ({self.v.get('sku')})", run


# ----------------------------------------------------------------- rename ----
class RenameEditor(BaseEditor):
    def __init__(self, product):
        super().__init__()
        self.p = product

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog", classes="small"):
            yield Label(f"[b]Rename[/b] product {self.p.get('id')}  [dim](no brand, no pack size)[/]")
            with Grid(classes="form"):
                yield Label("Name (en)")
                yield Input(self.p.get("name") or "", id="r-name")
                yield Label("Slug")
                yield Input(self.p.get("slug") or "", id="r-slug")
            yield from self.buttons()

    def build(self):
        name = self.query_one("#r-name", Input).value.strip()
        slug = self.query_one("#r-slug", Input).value.strip()
        if not name:
            raise PayloadError("name cannot be empty")
        pid = self.p["id"]
        slug = slug if slug != self.p.get("slug") else None
        return f"Rename product {pid}", lambda dry: products.rename(pid, name, slug, dry_run=dry)
