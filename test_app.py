"""
Cloudflare ZTNA Lab — Application unit tests.

These tests exercise the Flask routes in-process using Flask's built-in test
client.  They require NO running server, NO Cloudflare account, NO cloudflared
tunnel, and NO network connectivity.

They verify:
  - Correct HTTP status codes
  - Response body content
  - Content-Type headers
  - 404 handling for unknown routes

They do NOT test:
  - Cloudflare Access authentication or authorisation
  - MFA enforcement (handled by Cloudflare policy, not the app)
  - Tunnel availability or network routing

See README.md § "Two kinds of tests" for a full explanation of the
distinction between these unit tests and the live Cloudflare security tests.
"""

import json

import pytest

from app import app as flask_app


@pytest.fixture()
def client():
    """Flask test client — in-process, no real HTTP server started."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# /healthz
# ---------------------------------------------------------------------------

def test_healthz_returns_200(client):
    response = client.get("/healthz")
    assert response.status_code == 200


def test_healthz_json_body(client):
    response = client.get("/healthz")
    data = json.loads(response.data)
    assert data == {"status": "ok"}


def test_healthz_content_type(client):
    response = client.get("/healthz")
    assert "application/json" in response.content_type


# ---------------------------------------------------------------------------
# /admin
# ---------------------------------------------------------------------------

def test_admin_returns_200(client):
    response = client.get("/admin")
    assert response.status_code == 200


def test_admin_content_type_is_html(client):
    response = client.get("/admin")
    assert "text/html" in response.content_type


def test_admin_contains_disclaimer(client):
    response = client.get("/admin")
    body = response.data.decode("utf-8")
    assert "DEMONSTRATION ONLY" in body


def test_admin_contains_fake_data_marker(client):
    """All email addresses must use the RFC 2606 reserved domain."""
    response = client.get("/admin")
    body = response.data.decode("utf-8")
    assert "example.invalid" in body


def test_admin_contains_no_real_domains(client):
    """No real email domains must appear anywhere in the admin page."""
    response = client.get("/admin")
    body = response.data.decode("utf-8").lower()
    for real_domain in ("@gmail.com", "@yahoo.com", "@outlook.com", "@company.com"):
        assert real_domain not in body, (
            f"Real domain {real_domain!r} found in admin page — "
            "all demo data must use @example.invalid"
        )


def test_admin_shows_all_fake_users(client):
    """Every individual fake email address must appear in the rendered table."""
    response = client.get("/admin")
    body = response.data.decode("utf-8")
    for email in (
        "alice@example.invalid",
        "bob@example.invalid",
        "carol@example.invalid",
        "dave@example.invalid",
        "eve@example.invalid",
    ):
        assert email in body, f"Expected fake user {email!r} to appear in /admin"


# ---------------------------------------------------------------------------
# Unknown routes
# ---------------------------------------------------------------------------

def test_unknown_route_returns_404(client):
    response = client.get("/nonexistent")
    assert response.status_code == 404
