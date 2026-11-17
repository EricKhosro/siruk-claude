"""The write guard every Ops command goes through: dry run first, then `--apply <code>`.

The code is 8 hex over the exact requests plus the state the dry run showed, so a plan
that changed between the two runs gets a different code and writes nothing. The code is also bound
to the target, so a dry run must be repeated per environment. Every step
is checked against the policy before the first one is sent. Exit codes: 0 ok, 1 refused,
2 API error, 3 outcome unknown.
"""
import dataclasses, hashlib, json, sys, uuid
from typing import Any

from siruk import client as _admin, config, output
from siruk.ops import client as _ops, policy as _policy

TIERS = {"draft": "editable or deletable afterwards",
         "irreversible": "posts stock or money",
         "real-world": "reaches siruk or a third party — the owner's yes, each time"}


@dataclasses.dataclass(frozen=True)
class Step:
    method: str
    path: str
    body: Any = None
    label: str = ""


def _canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _idem_hex(kind, parts):
    return hashlib.sha256((kind + _canon(list(parts))).encode("utf-8")).hexdigest()[:32]


def idem_key(kind, *parts):
    """Same inputs, same key. For `idempotencyKey` (documents: a string up to 100 characters); the
    `@IsUUID` fields requestId, clientPaymentId, clientAdjustmentId and clientRequestId take `idem_uuid`."""
    return "cli-" + _idem_hex(kind, parts)


def idem_uuid(kind, *parts):
    """The same 32 hex as `idem_key`, shaped as a v4 UUID, for the `@IsUUID` fields."""
    return str(uuid.UUID(hex=_idem_hex(kind, parts), version=4))


def confirm_code(steps, shown_state=None, target=None):
    reqs = [[s.method.upper(), s.path, s.body] for s in steps]
    return hashlib.sha256(_canon([reqs, shown_state, target]).encode("utf-8")).hexdigest()[:8]


def _dry_run(steps, summary, tier, code, base, production, as_json):
    if as_json:
        output.dump({"dry_run": True, "target": base, "production": production, "tier": tier,
                     "summary": summary, "code": code,
                     "requests": [{"method": s.method.upper(), "path": s.path, "body": s.body,
                                   "label": s.label} for s in steps]})
        return
    print(f"target     {base}  ({'PRODUCTION' if production else 'not production'})")
    print(f"tier       {tier} — {TIERS[tier]}")
    print(f"summary    {summary}")
    for i, s in enumerate(steps, 1):
        print(f"  {i}. {s.method.upper()} {s.path}" + (f"   # {s.label}" if s.label else ""))
        if s.body is not None:
            print("     " + json.dumps(s.body, ensure_ascii=False, default=str))
    print(f"\nnothing sent; re-run with --apply {code}")


def run(args, *, steps, summary, tier, shown_state=None, verify="", client=None, policy=None):
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {tuple(TIERS)}")
    as_json = bool(getattr(args, "json", False))
    for s in steps:
        why = (policy or _policy.allowed)(s.method, s.path)
        if why:
            print(f"refused: {s.method.upper()} {s.path} — {why}", file=sys.stderr)
            return 1
    client = client or _ops.default()
    base = (getattr(client, "base", None) or config.ops_api_base()).rstrip("/")
    production = config.url_is_production(base)
    code = confirm_code(steps, shown_state, base)
    given = getattr(args, "apply", None)
    if not given:
        _dry_run(steps, summary, tier, code, base, production, as_json)
        return 0
    if given != code:
        print("refused: that code is for a different plan or a state that has since changed — "
              "the plan now is:", file=sys.stderr)
        _dry_run(steps, summary, tier, code, base, production, as_json)
        return 1
    results = []

    def failed(i, s, e, unknown):
        where = f" (step {i} of {len(steps)}; {i - 1} before it were applied)" if len(steps) > 1 else ""
        print(f"error: {e}{where}", file=sys.stderr)
        if unknown:
            print("outcome unknown: check with " + (f"`{verify}`" if verify else "the Ops app")
                  + " before repeating", file=sys.stderr)
        if as_json:
            output.dump({"dry_run": False, "applied": results,
                         "failed": {"step": i, "method": s.method.upper(), "path": s.path, "label": s.label,
                                    "error": str(e), "outcome_unknown": unknown}})
        return 3 if unknown else 2

    for i, s in enumerate(steps, 1):
        try:
            answer = client.write(s.method.upper(), s.path, s.body)
        except _ops.UnknownOutcome as e:
            return failed(i, s, e, True)
        except _admin.ApiError as e:
            return failed(i, s, e, False)
        results.append({"method": s.method.upper(), "path": s.path, "label": s.label, "response": answer})
        if not as_json:
            print(f"ok  {i}. {s.method.upper()} {s.path}" + (f"   # {s.label}" if s.label else ""))
            if answer is not None:
                output.dump(answer)
    if as_json:
        output.dump({"dry_run": False, "applied": results})
    return 0
