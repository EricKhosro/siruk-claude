"""The write guard for the admin API: `siruk.ops.guard.run` with an admin writer and the admin policy.

The writer makes one attempt and never retries; an answer that never arrived (0, 502, 504) or arrived
unreadable counts as an unknown outcome, so the caller looks before repeating. `lang` is part of the code.
"""
import os

from siruk import client as _client
from siruk.ops import client as _ops, guard as _guard
from siruk.ops.guard import Step  # noqa: F401  (commands build their steps from here)
from siruk.admin import policy as _policy


class Writer:
    """What guard.run needs of a client, on the admin API: a `.base` and a `.write` with one attempt."""

    def __init__(self, lang=None):
        self._c = _client.default()
        self.base = self._c.base
        self.lang = lang or os.environ.get("SIRUK_LANG") or None

    def write(self, method, path, body=None):
        self._c.token()   # no token is a refusal before anything is sent, not an unknown outcome
        try:
            return self._c.request(method, path, body=body, lang=self.lang, retry=False)
        except _client.ApiError as e:
            if e.status in (0, 502, 504) or (e.status < 400 and str(e.body).startswith("not JSON")):
                raise _ops.UnknownOutcome(e.status, method, path, e.body) from e   # a 2xx we cannot read probably ran
            raise


def writer(lang=None):
    return Writer(lang)


def run(args, *, steps, summary, tier, shown_state=None, verify="", lang=None):
    w = writer(lang)
    if w.lang:
        shown_state = {"lang": w.lang, "state": shown_state}
        summary += f" (Content-Language {w.lang})"
    return _guard.run(args, steps=steps, summary=summary, tier=tier, shown_state=shown_state, verify=verify,
                      client=w, policy=_policy.allowed)
