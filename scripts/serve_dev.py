"""Serve web/ for local testing with caching off, so a reload always runs the current files.

Usage: python scripts/serve_dev.py [port]   (default 8765, bound to 127.0.0.1)
"""

from __future__ import annotations

import functools
import http.server
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"


class NoStore(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    handler = functools.partial(NoStore, directory=str(WEB))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as srv:
        print(f"serving {WEB} on http://127.0.0.1:{port} (no-store)")
        srv.serve_forever()
