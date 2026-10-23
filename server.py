"""
Cloudflare ZTNA Lab — Waitress entry point.

Starts the Flask application bound exclusively to the loopback address
127.0.0.1:8080.  The host is a hardcoded string literal and cannot be
overridden by an environment variable; this prevents accidental exposure
on a LAN or public interface.

Usage:
    python server.py
"""

from waitress import serve

from app import app

_HOST = "127.0.0.1"
_PORT = 8080

if __name__ == "__main__":
    print(f"Starting Waitress on http://{_HOST}:{_PORT}/")
    print("Bound to loopback only — not reachable from LAN or internet.")
    print("Press Ctrl+C to stop.")
    serve(app, host=_HOST, port=_PORT)
