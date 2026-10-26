"""Product translations (ru / hy) — the port of scripts/set-translation.py.

A product's name and each variant's three texts are stored per locale (PUT with
"locale"); labels, slug, sku, prices, images and attributes are single-language,
so they are always copied from the `en` record. Keys the translation leaves out
keep what the locale already holds (falling back to en only where it has
nothing) — a file that translates one new variant must not wipe the others
(product 1150, 2026-09-23).

translation = {"name": "…", "variants": {"<sku>": {"about_this_item": "…", …}}}
"""
from siruk import client as _client
from siruk import payload as P
from siruk.products import WriteResult

VTEXT = P.VTEXT
LANGS = ("ru", "hy")
PayloadError = P.PayloadError


def _get(pid, lang):
    return (_client.default().get(f"/products/{int(pid)}", lang=lang) or {}).get("data") or {}


def build(pid, lang, tr):
    """→ (body, en, current-locale record). Raises on anything the file must not carry."""
    if lang not in LANGS:
        raise PayloadError("lang must be ru or hy (en is the source language)")
    for bad in ("slug", "sku", "price", "variants_list"):
        if bad in tr:
            raise PayloadError(f"translation must not carry '{bad}' — single-language fields come from en")
    en = _get(pid, "en")
    if not en:
        raise PayloadError(f"product {pid} not found")
    skus = {v["sku"] for v in en["variants"]}
    unknown = set(tr.get("variants") or {}) - skus
    if unknown:
        raise PayloadError(f"translation names SKUs not on product {pid}: {sorted(unknown)}")
    for sku, t in (tr.get("variants") or {}).items():
        extra = set(t) - set(VTEXT)
        if extra:
            raise PayloadError(f"variant {sku}: only {VTEXT} are translatable, got {sorted(extra)}")

    cur = _get(pid, lang)
    cur_v = {v["sku"]: v for v in cur.get("variants") or []}

    def kept(sku, f, en_val):
        c = (cur_v.get(sku) or {}).get(f)
        return c if c and c != en_val else (en_val or "")

    body = P.product_body(en)
    body["name"] = tr.get("name") or (cur.get("name") if cur.get("name") and cur.get("name") != en["name"]
                                      else en["name"])
    body["meta"] = tr.get("meta") if tr.get("meta") is not None else en.get("meta")
    body["locale"] = lang
    body["variants"] = []
    allowed = {a["id"] for a in P.product_type(en["attribute_family_id"]).get("attributes") or []}
    for v in en["variants"]:
        nv = P.to_variant_payload(v, allowed)
        t = (tr.get("variants") or {}).get(v["sku"], {})
        for f in VTEXT:
            nv[f] = t.get(f) if t.get(f) is not None else kept(v["sku"], f, v.get(f))
        body["variants"].append(nv)
    return body, en, cur


def current(pid, lang):
    """The locale's own texts next to en's: {name, en_name, variants: {sku: {f: (en, locale)}}}."""
    en, loc = _get(pid, "en"), _get(pid, lang)
    lv = {v["sku"]: v for v in loc.get("variants") or []}
    return {"name": loc.get("name"), "en_name": en.get("name"),
            "variants": {v["sku"]: {f: {"en": v.get(f) or "", lang: (lv.get(v["sku"]) or {}).get(f) or ""}
                                    for f in VTEXT} for v in en.get("variants") or []}}


def set_translation(pid, lang, tr, dry_run=False):
    body, en, cur = build(pid, lang, tr)
    diff = []
    if body["name"] != cur.get("name"):
        diff.append({"sku": None, "field": f"name[{lang}]", "old": cur.get("name"), "new": body["name"]})
    cur_v = {v["sku"]: v for v in cur.get("variants") or []}
    for nv in body["variants"]:
        for f in VTEXT:
            old = (cur_v.get(nv["sku"]) or {}).get(f) or ""
            if (nv.get(f) or "") != old:
                diff.append({"sku": nv["sku"], "field": f"{f}[{lang}]", "old": old, "new": nv.get(f)})
    res = WriteResult(f"set_translation:{lang}", int(pid), dry_run, body, diff, [])
    if dry_run:
        return res
    before_en = {"name": en["name"], "vnames": [v["name"] for v in en["variants"]],
                 "texts": [[v.get(f) or "" for f in VTEXT] for v in en["variants"]]}
    _client.default().put(f"/products/{int(pid)}", body, lang=lang)
    got, en2 = _get(pid, lang), _get(pid, "en")
    problems = []
    if got.get("name") != body["name"]:
        problems.append(f"{lang} name not stored: {got.get('name')!r}")
    if en2.get("name") != before_en["name"]:
        problems.append(f"EN NAME OVERWRITTEN: {en2.get('name')!r}")
    if [v["name"] for v in en2["variants"]] != before_en["vnames"]:
        problems.append("EN VARIANT LABELS CHANGED")
    if [[v.get(f) or "" for f in VTEXT] for v in en2["variants"]] != before_en["texts"]:
        problems.append("EN VARIANT TEXTS OVERWRITTEN")
    for v in got.get("variants") or []:
        t = (tr.get("variants") or {}).get(v["sku"], {})
        for f in VTEXT:
            if t.get(f) is not None and (v.get(f) or "") != t[f]:
                problems.append(f"{lang} {v['sku']}.{f} not stored")
    res.after = got
    res.warnings = problems
    if problems:
        raise PayloadError(f"product {pid} [{lang}] written but read-back shows: " + "; ".join(problems))
    return res
