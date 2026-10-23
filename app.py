"""
Cloudflare ZTNA Lab — Demo Flask application.

This application is a harmless learning demo.  It contains no real
administrator data, no real credentials, and no destructive operations.
Authentication and MFA are enforced entirely by Cloudflare Access; this
application performs no identity checks of its own.
"""

from flask import Flask, jsonify

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Fake user records — RFC 2606 reserved domain, not real people or accounts.
# ---------------------------------------------------------------------------
_FAKE_USERS = [
    {"email": "alice@example.invalid",   "role": "viewer",    "last_login": "2024-01-15"},
    {"email": "bob@example.invalid",     "role": "viewer",    "last_login": "2024-02-03"},
    {"email": "carol@example.invalid",   "role": "editor",    "last_login": "2024-03-22"},
    {"email": "dave@example.invalid",    "role": "editor",    "last_login": "2024-04-10"},
    {"email": "eve@example.invalid",     "role": "admin",     "last_login": "never"},
]


@app.get("/healthz")
def healthz():
    """Health probe — returns JSON 200 when the application is running."""
    return jsonify({"status": "ok"}), 200


@app.get("/admin")
def admin():
    """
    Demo admin console — read-only, contains only clearly fake data.

    In a real ZTNA deployment this page is only reachable after Cloudflare
    Access has verified the user's identity and MFA.  The application itself
    performs no authentication.
    """
    rows = "".join(
        f"<tr><td>{u['email']}</td><td>{u['role']}</td><td>{u['last_login']}</td></tr>"
        for u in _FAKE_USERS
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Demo Admin Console</title>
  <style>
    body  {{ font-family: system-ui, sans-serif; max-width: 760px;
             margin: 2rem auto; padding: 0 1rem; color: #1f2328; }}
    .disclaimer {{ background: #fff3cd; border: 1px solid #ffc107;
                   border-radius: 4px; padding: 0.75rem 1rem;
                   margin-bottom: 1.5rem; font-size: 0.9rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d0d7de; padding: 0.5rem 0.75rem;
              text-align: left; }}
    th {{ background: #f6f8fa; }}
  </style>
</head>
<body>
  <h1>Demo Admin Console</h1>
  <div class="disclaimer">
    &#9888;&#65039; <strong>THIS IS A DEMONSTRATION ONLY.</strong>
    All data below is entirely fictitious.  No real users, credentials, or
    administrator information are present.  This page exists solely to act
    as a protected resource in a Cloudflare ZTNA learning lab.
  </div>
  <h2>User Accounts</h2>
  <table>
    <thead>
      <tr><th>Email</th><th>Role</th><th>Last Login</th></tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>"""
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}
