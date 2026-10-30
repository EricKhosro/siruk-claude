"""The `siruk tui` main screen: search on the left, the product on the right.

Keys: / search · enter open · e edit variant · t translate · s stock · n rename
· h hafo price · l language · r reload · q quit. Every write goes through an
editor → dry run → diff → confirm (siruk/tui/editors.py)."""
import csv, os, time

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Input, Static, TabbedContent, TabPane

from siruk import client as _client
from siruk import config, lookups, products, refdata, stock
from siruk.config import ROOT
from siruk.tui.editors import RenameEditor, StockEditor, TranslationEditor, VariantEditor, err_text, short

LANGS = ("en", "ru", "hy")

CSS = """
Screen { background: $surface; }
#left { width: 38%; min-width: 34; border-right: tall $primary-background; }
#search { margin: 0 1; }
#results { height: 1fr; }
#right { width: 1fr; }
#head { height: auto; padding: 0 1; background: $boost; }
#variants { height: auto; max-height: 45%; }
#tabs { height: 1fr; }
#details, #hafo, #welcome { padding: 0 1; }
.below { color: $error; }
#dialog { width: 90%; height: 90%; border: thick $primary; background: $panel; padding: 1 2; }
#dialog.small { width: 72; height: auto; max-height: 90%; }
#dialog.confirm { width: 110; height: auto; max-height: 90%; border: thick $error; }
#dialog .env { margin-bottom: 1; }
#diff { height: auto; max-height: 24; }
.form { grid-size: 2; grid-columns: 30 1fr; grid-rows: auto; grid-gutter: 0 1; height: auto; }
.form Label { padding-top: 1; }
.text { height: 6; }
.multi { height: auto; max-height: 8; }
.buttons { height: auto; margin-top: 1; align-horizontal: right; }
.buttons Button { margin-left: 2; }
.toolbar { height: auto; }
.toolbar Select { width: 30; }
ModalScreen { align: center middle; background: $background 60%; }
"""


def open_items():
    path = os.path.join(ROOT, "state", "open-items.csv")
    try:
        with open(path, encoding="utf-8") as f:
            return sum(1 for _ in csv.DictReader(f))
    except OSError:
        return None


class SirukApp(App):
    TITLE = "Siruk admin"
    CSS = CSS
    BINDINGS = [
        Binding("slash", "focus_search", "Search"),
        Binding("e", "edit_variant", "Edit variant"),
        Binding("t", "translate", "Translate"),
        Binding("s", "stock", "Stock"),
        Binding("n", "rename", "Rename"),
        Binding("h", "hafo", "hafo price"),
        Binding("l", "cycle_lang", "Lang"),
        Binding("r", "reload", "Reload"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.product = None      # GET body in the current display language
        self.variant = None
        self.lang = "en"
        self.menu = None         # attribute id → {name, inputType, values}
        self.brands = {}
        self._search_timer = None

    # ---------------------------------------------------------------- layout
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="left"):
                yield Input(placeholder="Search products…  (/)", id="search")
                yield DataTable(id="results", cursor_type="row", zebra_stripes=True)
            with Vertical(id="right"):
                yield Static("", id="head")
                yield DataTable(id="variants", cursor_type="row", zebra_stripes=True)
                with TabbedContent(id="tabs"):
                    with TabPane("Overview", id="tab-overview"):
                        yield VerticalScroll(Static("loading…", id="welcome"))
                    with TabPane("Variant", id="tab-details"):
                        yield VerticalScroll(Static("select a variant", id="details"))
                    with TabPane("Stock", id="tab-stock"):
                        yield DataTable(id="moves", zebra_stripes=True)
                    with TabPane("hafo", id="tab-hafo"):
                        yield VerticalScroll(Static("press h on a variant", id="hafo"))
        yield Footer()

    def on_mount(self):
        _client.set_default(_client.Client())   # quiet: stderr would tear the screen
        self.sub_title = ("PRODUCTION · " if config.is_production() else "demo · ") + config.api_base()
        self.query_one("#results", DataTable).add_columns("id", "name", "brand")
        self.query_one("#variants", DataTable).add_columns(
            "", "sku", "label", "size", "price", "cost", "margin", "stock", "barcode", "acct", "img", "options")
        self.query_one("#moves", DataTable).add_columns("when", "type", "reason", "Δ on hand", "after", "note", "user")
        self.query_one("#search", Input).focus()
        self.load_overview()

    # -------------------------------------------------------------- overview
    @work(thread=True, group="overview")
    def load_overview(self):
        lines = []
        try:
            u = (_client.default().get("/account") or {}).get("currentUser") or {}
            lines.append(f"[b]Account[/b]   {u.get('email')} ({u.get('role')})")
        except _client.ApiError as e:
            lines.append(f"[red]API: {e}[/]")
        lines.append(f"[b]API[/b]       {config.api_base()} "
                     + ("[reverse red] PRODUCTION [/]" if config.is_production() else "[reverse green] demo [/]"))
        try:
            b = refdata.ids("brands")
            self.brands = {x["id"]: x["name"] for x in b}
            t = refdata.ids("types")
            lines.append(f"[b]Catalogue[/b] {len(b)} brands · {len(t)} product types: "
                         + ", ".join(x["name"] for x in t))
        except _client.ApiError as e:
            lines.append(f"[red]{e}[/]")
        n = open_items()
        if n is not None:
            lines.append(f"[b]Open items[/b] {n} rows in state/open-items.csv")
        pacer = _client.default().pacer
        for ch in ("api", "media"):
            last, count = pacer.read_state(ch)
            ago = f"{int(time.time() - last / 1000)}s ago" if last else "idle"
            lines.append(f"[b]Pace {ch:<5}[/b] {count} in chunk, last {ago}")
        lines += ["", "[dim]/ search · enter open · e edit variant · t translate · s stock · n rename · "
                      "h hafo · l language · r reload · q quit[/]",
                  "[dim]Every write shows its diff first and asks for a yes.[/]"]
        self.call_from_thread(self.query_one("#welcome", Static).update, "\n".join(lines))

    # ---------------------------------------------------------------- search
    @on(Input.Changed, "#search")
    def search_changed(self, ev):
        if self._search_timer:
            self._search_timer.stop()
        if len(ev.value.strip()) >= 3:
            self._search_timer = self.set_timer(0.5, lambda: self.run_search(ev.value.strip()))

    @on(Input.Submitted, "#search")
    def search_submitted(self, ev):
        if ev.value.strip():
            self.run_search(ev.value.strip())
            self.query_one("#results", DataTable).focus()

    @work(thread=True, exclusive=True, group="search")
    def run_search(self, text):
        try:
            rows = products.find(text, max_pages=3)
        except Exception as e:
            self.call_from_thread(self.notify, err_text(e), severity="error")
            return
        self.call_from_thread(self._fill_results, rows)

    def _fill_results(self, rows):
        t = self.query_one("#results", DataTable)
        t.clear()
        for r in rows:
            t.add_row(str(r["id"]), r["name"] or "", r["brand"] or "", key=str(r["id"]))
        if not rows:
            self.notify("no match — safe to create a new product")

    @on(DataTable.RowSelected, "#results")
    def result_selected(self, ev):
        self.load_product(int(ev.row_key.value))

    # --------------------------------------------------------------- product
    @work(thread=True, exclusive=True, group="product")
    def load_product(self, pid, keep_sku=None):
        try:
            p = products.get(pid, lang=self.lang)
            if self.menu is None:
                self.menu = {a["id"]: {"name": a["name"], "inputType": a.get("inputType"),
                                       "values": [(v["label"], v["id"]) for v in a.get("values") or []]}
                             for a in (_client.default().get("/attributes?forProducts=true") or {}).get("data") or []}
        except Exception as e:
            self.call_from_thread(self.notify, err_text(e), severity="error")
            return
        self.call_from_thread(self._show_product, p, keep_sku)

    def _show_product(self, p, keep_sku=None):
        self.product = p
        s = products.summary(p)
        brand = self.brands.get(s["brand_id"], s["brand_id"])
        below = sum(1 for v in s["variants"] if v["below_cost"])
        self.query_one("#head", Static).update(
            f"[b]{s['name']}[/b]  [dim]#{s['id']} · {brand} · {s['product_type']} · categories {s['category_ids']}"
            f" · lang {self.lang}[/]" + (f"  [reverse red] {below} BELOW COST [/]" if below else ""))
        t = self.query_one("#variants", DataTable)
        t.clear()
        target = 0
        for i, v in enumerate(s["variants"]):
            m = "—" if v["margin_pct"] is None else f"{v['margin_pct']}%"
            if v["below_cost"]:
                m = f"[red]{m} ✗[/]"
            t.add_row("★" if v["default"] else "", v["sku"], short(v["label"], 34), v["size"] or "—",
                      f"{v['price']:,}".replace(",", " ") if v["price"] else "—",
                      f"{int(v['cost']):,}".replace(",", " ") if v["cost"] else "—",
                      m, str(v["stock"] if v["stock"] is not None else "—"), v["barcode"] or "—",
                      v["accounting_code"] or "—", str(v["images"]),
                      ", ".join(f"{k}: {x}" for k, x in v["options"].items()), key=v["sku"])
            if keep_sku and v["sku"] == keep_sku:
                target = i
        if s["variants"]:
            t.move_cursor(row=target)
            self._select_variant(p["variants"][target])
        t.focus()
        self.query_one("#tabs", TabbedContent).active = "tab-details"

    @on(DataTable.RowHighlighted, "#variants")
    def variant_highlighted(self, ev):
        if not self.product or ev.row_key is None:
            return
        v = next((x for x in self.product["variants"] if x["sku"] == ev.row_key.value), None)
        if v and v is not self.variant:
            self._select_variant(v)

    def _select_variant(self, v):
        self.variant = v
        r = products.variant_row(v)
        lines = [f"[b]{v.get('name')}[/b]  sku {v.get('sku')} · variant id {v.get('id')} · "
                 f"{v.get('sale_mode')} {v.get('size_label') or ''}",
                 f"price {v.get('price')} · cost {v.get('cost_price')} · compare-at {v.get('compare_at_price') or '—'}"
                 + (f" · margin {r['margin_pct']}%" if r["margin_pct"] is not None else ""),
                 f"barcode {v.get('barcode') or '—'} · ArmSoft {v.get('accounting_code') or '—'}",
                 f"price source {v.get('price_source_url') or '—'}",
                 "options: " + (", ".join(f"{k}: {x}" for k, x in r["options"].items()) or "—"),
                 "attributes: " + (", ".join(f"{k}: {x}" for k, x in r["attributes"].items()) or "—"),
                 "stock: " + (", ".join(f"{l.get('warehouse_name')} {l.get('on_hand')} on hand / "
                                        f"{l.get('available')} available" for l in r["stock_levels"]) or "—"),
                 f"images ({len(r['image_urls'])}):"] + [f"  {u}" for u in r["image_urls"]]
        for f, label in (("about_this_item", "About"), ("ingredient_information", "Ingredients"),
                         ("feeding_instructions", "Feeding")):
            lines += ["", f"[b]{label}[/b] [dim]({self.lang})[/]", short(v.get(f) or "—", 600)]
        self.query_one("#details", Static).update("\n".join(lines))
        self.load_moves(v["id"])

    @work(thread=True, exclusive=True, group="moves")
    def load_moves(self, vid):
        try:
            rows = stock.movements(vid) or []
        except Exception:
            rows = []
        self.call_from_thread(self._fill_moves, rows)

    def _fill_moves(self, rows):
        t = self.query_one("#moves", DataTable)
        t.clear()
        for m in rows:
            t.add_row((m.get("created_at") or "")[:16].replace("T", " "), m.get("type") or "",
                      m.get("reason") or "", str(m.get("on_hand_delta")), str(m.get("on_hand_after")),
                      short(m.get("note") or "", 40), m.get("user_name") or "")

    # --------------------------------------------------------------- actions
    def action_focus_search(self):
        self.query_one("#search", Input).focus()

    def action_reload(self):
        if self.product:
            self.load_product(self.product["id"], keep_sku=(self.variant or {}).get("sku"))

    def action_cycle_lang(self):
        self.lang = LANGS[(LANGS.index(self.lang) + 1) % len(LANGS)]
        self.notify(f"display language: {self.lang} (edits always start from en)")
        self.action_reload()

    def _need(self, variant=True):
        if not self.product or (variant and not self.variant):
            self.notify("open a product first (search, then enter)", severity="warning")
            return False
        return True

    def _after_edit(self, changed):
        if changed:
            self.action_reload()

    def action_edit_variant(self):
        if self._need():
            self._open_variant_editor(self.product["id"], self.variant["sku"])

    @work(thread=True, exclusive=True, group="editor-open")
    def _open_variant_editor(self, pid, sku):
        try:
            en = products.get(pid, lang="en")        # edits start from a fresh en record
            ptype = refdata.product_type(en["attribute_family_id"])
        except Exception as e:
            self.call_from_thread(self.notify, err_text(e), severity="error")
            return
        v = next((x for x in en["variants"] if x["sku"] == sku), None)
        if v is None:
            self.call_from_thread(self.notify, f"variant {sku} is gone — reload", severity="error")
            return
        self.call_from_thread(self.push_screen, VariantEditor(en, v, ptype, self.menu or {}), self._after_edit)

    def action_translate(self):
        if self._need(variant=False):
            self.push_screen(TranslationEditor(self.product["id"], "ru" if self.lang == "en" else self.lang),
                             self._after_edit)

    def action_stock(self):
        if self._need():
            self.push_screen(StockEditor(self.variant), self._after_edit)

    def action_rename(self):
        if self._need(variant=False):
            self.push_screen(RenameEditor(self.product), self._after_edit)

    def action_hafo(self):
        if self._need():
            self.query_one("#tabs", TabbedContent).active = "tab-hafo"
            self.query_one("#hafo", Static).update(f"looking up {self.variant['sku']} on hafo.am…")
            self.run_hafo(self.variant)

    @work(thread=True, exclusive=True, group="hafo")
    def run_hafo(self, v):
        try:
            r = lookups.hafo(v["sku"], "")
        except Exception as e:
            self.call_from_thread(self.query_one("#hafo", Static).update, f"[red]{err_text(e)}[/]")
            return
        ours, cost = v.get("price"), v.get("cost_price")
        if not r.get("hafo_id"):
            text = f"[yellow]hafo has no product for article {v['sku']}[/] (tried {r.get('tried')})"
        else:
            hp = r.get("price_amd")
            ok = r.get("confirmed") and r.get("price_source") == "variant"
            verdict = ("[green]usable[/]" if ok else "[red]not usable as a sale price[/]")
            cmp = ""
            if hp and ours:
                cmp = (" · [green]same as ours[/]" if int(hp) == int(ours)
                       else f" · ours {ours} ({'+' if ours > int(hp) else ''}{ours - int(hp)})")
            text = "\n".join([
                f"[b]{r.get('title_hy')}[/b]  {r.get('url') or ''}",
                f"matched by {r.get('matched_by')} · brand {r.get('brand')} · confirmed {r.get('confirmed')}",
                f"variant price [b]{hp}[/b] AMD ({r.get('price_source')}) — {verdict}{cmp}",
                f"wholesale {r.get('wholesale_price_amd')} · our cost {cost} · in stock {r.get('variant_in_stock')}",
                f"variant {r.get('variant_name_hy')} · sku {r.get('variant_sku')} · barcodes {r.get('barcodes')}",
                "", "[dim]listing price (cheapest size — never price from it): "
                    f"{r.get('listing_price_amd')}[/]"])
        self.call_from_thread(self.query_one("#hafo", Static).update, text)


def run():
    SirukApp().run()
