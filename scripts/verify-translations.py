#!/usr/bin/env python3
"""Audit ru/hy coverage of everything on the server that stores per-locale text:
products (name + variant texts), categories (name), brands (name + meta).
A locale counts as missing when its value is empty or identical to the English
one (a fallback, not a translation) — except brand names, which are Latin by policy.

    scripts/verify-translations.py [--only id,id] [--out missing.json]

The logic lives in siruk/verify.py since 2026-10-26 (also: `siruk verify-translations`,
and the MCP tool verify_translations). Exit 1 if anything is missing.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SIRUK_NO_PACE"] = "1"  # as before: a read-only sweep, one call at a time
from siruk import verify  # noqa: E402


def main(argv):
    only = [int(x) for x in argv[argv.index("--only") + 1].split(",")] if "--only" in argv else None
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    res = verify.translations(only=only)
    verify.print_report(res, out)
    sys.exit(0 if res["complete"] else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
