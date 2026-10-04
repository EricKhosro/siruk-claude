#!/usr/bin/env python3
"""agent-results3.json from pass 3: results3/match-NN.json + results3/verify-NN.json (+ results3/tiebreak-NN.json).

Per variant, the final answer for zoovet and nemo is:
  verifier agrees            -> the verifier's answer           (source "verifier-agreed")
  verifier disagrees         -> the tie-break answer if present (source "tiebreak"), else listed as disputed
Shape matches agent-results2.json: {"variant_id", "final": {"zoovet", "nemo", "confidence"}, "source", "disputed"}.
Prints the batches still missing a match / verify file and the disputed variant ids per batch."""
import glob, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results3")


def load(p):
    return {r["variant_id"]: r for r in json.load(open(p, encoding="utf-8"))["results"]} if os.path.exists(p) else None


def same(a, b):
    a, b = a or {}, b or {}
    if bool(a.get("found")) != bool(b.get("found")):
        return False
    return not a.get("found") or a.get("price") == b.get("price")


out, todo, disputes = [], [], {}
for bp in sorted(glob.glob(os.path.join(HERE, "batches3", "batch-*.json"))):
    nn = re.search(r"batch-(\d+)", bp).group(1)
    batch = [b["variant_id"] for b in json.load(open(bp, encoding="utf-8"))]
    m, v, t = (load(os.path.join(R, f"{k}-{nn}.json")) for k in ("match", "verify", "tiebreak"))
    if m is None or v is None:
        todo.append((nn, "match" if m is None else "verify"))
        continue
    for vid in batch:
        mv, vv = m.get(vid), v.get(vid)
        if vv is None:
            disputes.setdefault(nn, []).append(vid)
            continue
        agree = vv.get("verdict") == "agree" and mv is not None and all(same(mv.get(s), vv.get(s)) for s in ("zoovet", "nemo"))
        if agree:
            out.append({"variant_id": vid, "final": {s: vv[s] for s in ("zoovet", "nemo", "confidence") if s in vv},
                        "source": "verifier-agreed", "disputed": False})
        elif t and vid in t:
            tv = t[vid]
            out.append({"variant_id": vid, "final": {s: tv[s] for s in ("zoovet", "nemo", "confidence") if s in tv},
                        "source": "tiebreak", "disputed": True})
        else:
            disputes.setdefault(nn, []).append(vid)

json.dump(out, open(os.path.join(HERE, "agent-results3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("final answers:", len(out), "| batches not finished:", todo)
print("disputed, no tie-break yet:", {k: v for k, v in disputes.items()})
