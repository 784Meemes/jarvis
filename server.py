#!/usr/bin/env python3
"""Serve the viewer/ folder only, at http://localhost:4700/."""
import functools
import http.server
from pathlib import Path

PORT = 4700
VIEWER_DIR = Path(__file__).resolve().parent / "viewer"


def main():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(VIEWER_DIR))
    with http.server.ThreadingHTTPServer(("0.0.0.0", PORT), handler) as httpd:
        print(f"Serving {VIEWER_DIR} at http://localhost:{PORT}/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
