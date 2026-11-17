"""Where command groups plug into the parser.

Each module in GROUPS defines `register(reg)` and adds its commands with `reg.command(...)`;
a group whose module does not exist yet is skipped, any other import error is raised.
`reg` also fills the manifest `siruk commands` prints, so nothing else lists the commands.
"""
import importlib, sys

GROUPS = ("ops_core", "prices", "ops_goods", "ops_docs", "ops_purchasing", "ops_einvoices", "ops_office",
          "ops_prep", "ops_admin", "admin_core", "admin_orders", "admin_marketing", "admin_content",
          "admin_insights", "admin_catalog", "admin_lifecycle")
TIERS = ("read", "draft", "irreversible", "real-world")
PARENT_HELP = {("ops",): "Siruk Ops: stock, till, receiving (the person's own key)",
               ("admin",): "the admin panel through its API: dry run first, then --apply <code>"}
MANIFEST_KEYS = ("name", "backend", "api", "tier", "roles", "help", "example")


def entry(name, backend, api, tier, roles, help, example):
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {TIERS}, got {tier!r}")
    return dict(zip(MANIFEST_KEYS, (name, backend, list(api or []), tier, roles or "", help or "", example or "")))


def register_all(reg):
    for name in GROUPS:
        full = f"{__name__}.{name}"
        try:
            module = importlib.import_module(full)
        except ModuleNotFoundError as e:
            if e.name != full:
                raise
            continue
        module.register(reg)


class Registry:
    """What a group's `register(reg)` talks to: nested subparsers made on demand, one manifest entry each."""

    def __init__(self, sub, common, manifest):
        self.root, self.common, self.manifest = sub, common, manifest
        self._nodes = {}

    def _parent(self, path):
        sub = self.root
        for depth, seg in enumerate(path[:-1], 1):
            key = tuple(path[:depth])
            if key not in self._nodes:
                node = sub.add_parser(seg, help=PARENT_HELP.get(key) or f"{' '.join(key)} commands")
                self._nodes[key] = node.add_subparsers(dest=f"cmd{depth + 1}", required=True, metavar="<command>")
            sub = self._nodes[key]
        return sub

    def command(self, path, fn, help, *, api, tier="read", roles="", example=""):
        path = tuple(path)
        backend = "ops" if path[0] == "ops" else "admin"
        self.manifest.append(entry(" ".join(path), backend, api, tier, roles, help, example))
        p = self._parent(path).add_parser(path[-1], help=help, parents=[self.common],
                                          epilog=f"example: {example}" if example else None)
        if tier != "read":
            p.add_argument("--apply", metavar="CODE", help="send it: the code a dry run printed")
        p.set_defaults(fn=self._wrap(fn, backend))
        return p

    @staticmethod
    def _wrap(fn, backend):
        if backend != "ops":
            return fn

        def run(args):
            from siruk.ops import client as _ops
            c = _ops.default()
            if isinstance(c, _ops.OpsClient) and not getattr(args, "quiet", False):
                c.log = _ops.stderr_log
            try:
                return fn(args)
            except _ops.UnknownOutcome as e:
                print(f"error: {e}\noutcome unknown: check before repeating", file=sys.stderr)
                return 3
        return run
