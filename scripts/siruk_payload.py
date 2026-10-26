#!/usr/bin/env python3
"""Shim: the payload builder now lives in siruk/payload.py (2026-10-26).

`from siruk_payload import …` and the CLI below keep working unchanged:
  siruk_payload.py put-body   <get.json> [<new-variant.json>] [--patch-sku SKU --patch JSON [--replace-attrs]]
  siruk_payload.py post-body  <payload.json>
Importing this file hands back the siruk.payload module itself (same caches, same rules).
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import siruk.payload as _payload  # noqa: E402

if __name__ == "__main__":
    _payload.main(sys.argv[1:])
else:
    sys.modules[__name__] = _payload
