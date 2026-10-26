"""Live ids and the two reference snapshots the skills read.

refresh() writes reference/attribute-values.json (refresh-attributes.sh's shape)
and reference/product-types.json (product-types.py --dump's shape), atomically.
"""
import json, os

from siruk import client as _client
from siruk.config import ROOT

KINDS = {"brands": "/brands?forProducts=true", "categories": "/categories?forProducts=true",
         "types": "/attribute-families?forProducts=true", "attributes": "/attributes?forProducts=true"}


def ids(kind):
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {list(KINDS)}")
    data = (_client.default().get(KINDS[kind]) or {}).get("data") or []
    if kind == "categories":
        return [{"id": c.get("id"), "name": c.get("name"), "parent_id": c.get("parent_id") or c.get("parentId")}
                for c in data]
    if kind == "attributes":
        return [{"id": a.get("id"), "code": a.get("code"), "name": a.get("name"),
                 "values": len(a.get("values") or [])} for a in data]
    if kind == "types":
        return [{"id": t.get("id"), "name": t.get("name"), "code": t.get("code"),
                 "measure_type": t.get("measureType")} for t in data]
    return [{"id": b.get("id"), "name": b.get("name"), "slug": b.get("slug")} for b in data]


def product_type(type_id):
    return (_client.default().get(f"/attribute-families/{int(type_id)}") or {}).get("data") or {}


def _atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def attribute_values_snapshot():
    data = (_client.default().get("/attributes?forProducts=true") or {}).get("data") or []
    return {a["code"]: {"attribute_id": a["id"], "name": a["name"],
                        "values": {v["label"]: v["id"] for v in a.get("values") or []}} for a in data}


def product_types_snapshot():
    types = (_client.default().get("/attribute-families") or {}).get("data") or []
    return [{k: t.get(k) for k in ("id", "name", "code", "defaultSaleMode", "measureType", "unitPriceBasis")}
            | {"attributes": [{k: a.get(k) for k in ("id", "code", "name", "inputType", "role", "isRequired",
                                                      "isFilterable", "showOnProductCard", "position")}
                              for a in sorted(t.get("attributes") or [], key=lambda a: a.get("position") or 0)]}
            for t in types]


def refresh():
    av, pt = attribute_values_snapshot(), product_types_snapshot()
    if not av or not pt:
        raise RuntimeError("refusing to write: the API returned no attributes / product types")
    a_path = os.path.join(ROOT, "reference", "attribute-values.json")
    t_path = os.path.join(ROOT, "reference", "product-types.json")
    _atomic_write(a_path, av)
    _atomic_write(t_path, pt)
    return {"attribute-values.json": len(av), "product-types.json": len(pt)}
