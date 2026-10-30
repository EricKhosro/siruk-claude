"""SEO text: product meta title / description and image alt / caption (user, 2026-10-27/28).

Meta, per locale: "Buy {Brand} {Name}" and "Shop {Brand} {Name} online at Siruk. …", fitted to
Google's limits — title ≤ 60 chars, description ≤ 160 (dev, 2026-10-28). {Brand} is the brand's
stored name (Latin, every locale); {Name} the product's name in that locale (it never carries the
brand, rule 12). Image alt = caption = "{Brand} {Name}" in English (the fields are single-language).

create / rename / translate send the meta in their own PUT; bulk create and add-variant call
apply_meta / set_image_alts afterwards. scripts/set-seo-meta.py and set-media-alt.py back-fill
the live catalogue with the same texts.
"""
import functools

from siruk import client as _client
from siruk import refdata

LANGS = ("en", "ru", "hy")
TITLE_MAX, DESC_MAX, ALT_MAX = 60, 160, 255
BUY = {"en": "Buy", "ru": "Купить", "hy": "Գնել"}
# longest first; the first that fits wins
DESCRIPTIONS = {
    "en": ("Shop {Brand} {Name} online at Siruk. Pet food, toys, treats and supplies delivered in Yerevan.",
           "Shop {Brand} {Name} online at Siruk, delivered in Yerevan.",
           "{Brand} {Name} at Siruk, delivered in Yerevan."),
    "ru": ("Купите {Brand} {Name} онлайн в Siruk. Корм, игрушки, лакомства и товары для питомцев "
           "с доставкой по Еревану.",
           "Купите {Brand} {Name} онлайн в Siruk с доставкой по Еревану.",
           "{Brand} {Name} в Siruk с доставкой по Еревану."),
    "hy": ("Գնեք {Brand} {Name} առցանց Siruk-ում։ Կեր, խաղալիքներ, համեղանքներ և պարագաներ՝ "
           "առաքմամբ Երևանում։",
           "Գնեք {Brand} {Name} առցանց Siruk-ում՝ առաքմամբ Երևանում։",
           "{Brand} {Name} Siruk-ում՝ առաքմամբ Երևանում։"),
}


def fit_title(lang, brand, name):
    """Buy {Brand} {Name} → {Brand} {Name} → {Name} → drop trailing ", …" parts → cut at a word."""
    parts = name.split(", ")
    tries = [f"{BUY[lang]} {brand} {name}", f"{brand} {name}", name]
    tries += [f"{brand} {', '.join(parts[:k])}" for k in range(len(parts) - 1, 0, -1)]
    for t in tries:
        if len(t) <= TITLE_MAX:
            return t
    out = ""
    for w in f"{brand} {parts[0]}".split(" "):
        if len(f"{out} {w}".strip()) > TITLE_MAX:
            break
        out = f"{out} {w}".strip()
    return out.rstrip(",;/&-– ")


def meta(lang, brand, name):
    """{title, description} for one locale, both within the limits."""
    descs = [d.format(Brand=brand, Name=name) for d in DESCRIPTIONS[lang]]
    desc = next((d for d in descs if len(d) <= DESC_MAX), descs[-1][:DESC_MAX])
    return {"title": fit_title(lang, brand, name), "description": desc}


def alt(brand, name):
    return f"{brand} {name}".strip()[:ALT_MAX]


@functools.lru_cache(maxsize=1)
def _brands():
    return {b["id"]: b["name"] for b in refdata.ids("brands")}


def brand_name(brand_id):
    name = _brands().get(brand_id)
    if name is None:
        _brands.cache_clear()          # a brand created since the first call
        name = _brands().get(brand_id)
    return name


def _get(pid, lang):
    return (_client.default().get(f"/products/{int(pid)}", lang=lang) or {}).get("data") or {}


def apply_meta(pid, langs=LANGS, dry_run=False):
    """Write the template meta in each locale whose stored meta differs. → {lang: "written"|"same"}."""
    from siruk import translations
    recs = {l: _get(pid, l) for l in LANGS}
    brand = brand_name(recs["en"].get("brand_id"))
    if not brand:
        raise ValueError(f"product {pid}: brand {recs['en'].get('brand_id')} not found")
    en_name = (recs["en"].get("name") or "").strip()
    out, en = {}, recs["en"]
    for l in langs:
        want = meta(l, brand, (recs[l].get("name") or "").strip() or en_name)
        if (recs[l].get("meta") or {}) == want:
            out[l] = "same"
            continue
        res = translations.set_meta(pid, l, want, dry_run=dry_run, en=en, cur=None if l == "en" else recs[l])
        if l == "en" and not dry_run:
            en = res.after
        out[l] = "written"
    return out


def set_image_alts(pid, dry_run=False):
    """alt = caption = "{Brand} {Name}" on every image of the product's variants. → [media ids written]."""
    p = _get(pid, "en")
    brand = brand_name(p.get("brand_id"))
    if not brand:
        return []
    text = alt(brand, p.get("name") or "")
    c, done, seen = _client.default(), [], set()
    for v in p.get("variants") or []:
        for m in v.get("images_media") or []:
            mid = m.get("id")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            if m.get("alt") == text and m.get("caption") == text:
                continue
            if not dry_run:
                c.put(f"/medias/{mid}", {"alt": text, "caption": text})
            done.append(mid)
    return done
