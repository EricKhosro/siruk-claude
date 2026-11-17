"""A fake admin client for command tests: routes are registered with `.on`, every call is recorded
in `.calls` (and its Content-Language in `.langs`), an unregistered route is an AssertionError,
and no socket is ever opened. `request` is the one choke point, so get, paginate and the guard's
writer all land in `.calls`."""
import re
import urllib.parse

from siruk import client as _client


def _no_network(*a, **kw):
    raise AssertionError("a test tried to reach the network")


class FakePacer:
    def pace(self, *a, **kw):
        pass

    def read_state(self, ch):
        return 0, 0


class FakeAdminClient(_client.Client):
    def __init__(self, base="https://offline.test/api/admin"):
        super().__init__(base=base, token="T", opener=_no_network, pacer=FakePacer())
        self.routes, self.calls, self.langs = [], [], []

    def on(self, method, path_or_regex, response):
        """response: JSON, an Exception instance (raised), or a callable(query_dict_or_body) → either."""
        self.routes.append((method.upper(), path_or_regex, response))
        return self

    def request(self, method, path, body=None, lang=None, **kw):
        method = method.upper()
        bare, _, query = path.partition("?")
        data = dict(urllib.parse.parse_qsl(query)) if method == "GET" else body
        self.calls.append((method, path, data))
        self.langs.append(lang)
        for m, route, response in reversed(self.routes):  # the latest registration wins
            hit = route.fullmatch(bare) if isinstance(route, re.Pattern) else route in (path, bare)
            if m == method and hit:
                out = response(data) if callable(response) else response
                if isinstance(out, Exception):
                    raise out
                return out
        raise AssertionError(f"unexpected {method} {path}")
