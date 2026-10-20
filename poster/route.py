#!/usr/bin/env python3
"""Say which platforms post directly (GitHub Action) and which still need the fallback.

  python3 poster/route.py careerwithcode
  -> {"direct": ["youtube"], "fallback": ["instagram", "facebook"]}

Reads poster/status.json, which the Post Shorts GitHub Action rewrites whenever tokens are
added. Once every platform is direct, the fallback (Metricool / Zapier) is never used again.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
channel = sys.argv[1]
platforms = json.load(open(os.path.join(ROOT, "poster", "channels.json")))[channel]["default_platforms"]
try:
    ready = json.load(open(os.path.join(ROOT, "poster", "status.json")))["ready"].get(channel, {})
except (FileNotFoundError, KeyError, ValueError):
    ready = {}
print(json.dumps({"direct": [p for p in platforms if ready.get(p)],
                  "fallback": [p for p in platforms if not ready.get(p)]}))
