"""A fake Ops client for command tests: routes are registered with `.on`, every call is recorded
in `.calls`, an unregistered route is an AssertionError, and no socket is ever opened."""
import re

from siruk.ops.client import OpsClient


def _no_network(*a, **kw):
    raise AssertionError("a test tried to reach the network")


class FakeOpsClient(OpsClient):
    def __init__(self, base="https://ops.offline.test/api", token="ops_FAKEKEYFAKEKEYFAKEKEY"):
        super().__init__(base=base, token=token, opener=_no_network)
        self.routes, self.calls, self.tokens = [], [], []

    def on(self, method, path_or_regex, response):
        """response: JSON, an Exception instance (raised), or a callable(params_or_body) → either."""
        self.routes.append((method.upper(), path_or_regex, response))
        return self

    def with_token(self, token):
        self.tokens.append(token)
        return self

    def _answer(self, method, path, data):
        self.calls.append((method, path, data))
        bare = path.split("?")[0]
        for m, route, response in reversed(self.routes):  # the latest registration wins
            hit = route.fullmatch(bare) if isinstance(route, re.Pattern) else route in (path, bare)
            if m == method and hit:
                out = response(data) if callable(response) else response
                if isinstance(out, Exception):
                    raise out
                return out
        raise AssertionError(f"unexpected {method} {path}")

    def get(self, path, params=None):
        return self._answer("GET", path, params)

    def write(self, method, path, body=None):
        return self._answer(method.upper(), path, body)

    def download(self, path, params=None):
        return self._answer("GET", path, params)
