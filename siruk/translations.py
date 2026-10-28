"""Product translations (ru / hy) — the port of scripts/set-translation.py.

A product's name and each variant's three texts are stored per locale (PUT with
"locale"); labels, slug, sku, prices, images and attributes are single-language,
so they are always copied from the `en` record. Keys the translation leaves out
keep what the locale already holds (falling back to en only where it has
nothing) — a file that translates one new variant must not wipe the others
(product 1150, 2026-09-23).

translation = {"name": "…", "meta": {"title": "…", "description": "…"},
               "variants": {"<sku>": {"about_this_item": "…", …}}}

SEO meta (siruk-web HasSeo): not a ProductRequest field — the product's `saved` hook reads a
top-level `meta` from the request and fills the translatable `seo` row in the request's locale
(the Content-Language header, then the body's `locale`). A body without `meta` leaves every
locale's meta alone, so meta is sent only when the translation carries it (it used to copy en's
meta into ru/hy on every translate). set_meta() writes one locale's meta, en included.
"""
from siruk import client as _client
from siruk import payload as P
from siruk.products import WriteResult

VTEXT = P.VTEXT
LANGS = ("ru", "hy")
PayloadError = P.PayloadError


def _get(pid, lang):
    return (_client.default().get(f"/products/{int(pid)}", lang=lang) or {}).get("data") or {}


def _meta(m):
    if not isinstance(m, dict) or set(m) - {"title", "description"}:
        raise PayloadError("meta must be {title, description}")
    return {k: m[k] for k in ("title", "description") if m.get(k) is not None}


def build(pid, lang, tr, en=None, cur=None):
    """→ (body, en, current-locale record). Raises on anything the file must not carry.
    `en` / `cur` may be passed in when the caller has just read them (saves two GETs)."""
    if lang not in LANGS:
        raise PayloadError("lang must be ru or hy (en is the source language)")
    for bad in ("slug", "sku", "price", "variants_list"):
        if bad in tr:
            raise PayloadError(f"translation must not carry '{bad}' — single-language fields come from en")
    en = en or _get(pid, "en")
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

    cur = cur or _get(pid, lang)
    cur_v = {v["sku"]: v for v in cur.get("variants") or []}

    def kept(sku, f, en_val):
        c = (cur_v.get(sku) or {}).get(f)
        return c if c and c != en_val else (en_val or "")

    body = P.product_body(en)
    body["name"] = tr.get("name") or (cur.get("name") if cur.get("name") and cur.get("name") != en["name"]
                                      else en["name"])
    if tr.get("meta") is not None:
        body["meta"] = _meta(tr["meta"])
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
    if "meta" not in tr:
        from siruk import seo
        brand = seo.brand_name(en.get("brand_id"))
        if brand and body.get("name"):
            body["meta"] = seo.meta(lang, brand, body["name"])   # the locale's SEO follows its name
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


def set_meta(pid, lang, meta, dry_run=False, en=None, cur=None):
    """Write one locale's SEO meta {title, description} and nothing else.

    en: the en record re-sent as is (product_body + to_variant_payload) with `meta` on top.
    ru / hy: build() with only `meta`, so the locale keeps its own name and texts.
    The request's Content-Language picks the seo row's locale. Read back in `lang`;
    WriteResult.after is that GET. Raises when the stored meta differs."""
    from siruk.products import _check_invariants
    meta = _meta(meta)
    if lang == "en":
        en = en or _get(pid, "en")
        if not en:
            raise PayloadError(f"product {pid} not found")
        cur = en
        allowed = {a["id"] for a in P.product_type(en["attribute_family_id"]).get("attributes") or []}
        body = P.product_body(en)
        body["variants"] = [P.to_variant_payload(v, allowed) for v in en["variants"]]
        body["meta"] = meta
    elif lang in LANGS:
        body, en, cur = build(pid, lang, {"meta": meta}, en=en, cur=cur)
    else:
        raise PayloadError("lang must be en, ru or hy")
    _check_invariants(en, body)
    old = cur.get("meta") or {}
    diff = [{"sku": None, "field": f"meta.{k}[{lang}]", "old": old.get(k), "new": meta.get(k)}
            for k in ("title", "description") if old.get(k) != meta.get(k)]
    res = WriteResult(f"set_meta:{lang}", int(pid), dry_run, body, diff, [])
    if dry_run:
        return res
    _client.default().put(f"/products/{int(pid)}", body, lang=lang)
    got = _get(pid, lang)
    res.after = got
    stored = got.get("meta") or {}
    bad = [k for k in meta if stored.get(k) != meta[k]]
    if bad:
        raise PayloadError(f"product {pid} [{lang}] written but meta {bad} reads back as {stored!r}")
    return res
