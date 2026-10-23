# Cloudflare ZTNA Lab — Implementation Plan

## Top-Level Overview

**Goal:** Build a self-contained learning project that demonstrates Zero-Trust Network Access
using Cloudflare Tunnel, Cloudflare Access, and MFA. The project exists purely for educational
purposes. It must never contain real credentials, real administrative data, or destructive
operations.

**Scope:**
- A harmless Python Flask "admin console" demo served by Waitress, bound only to 127.0.0.1:8080
- `/admin` and `/healthz` HTTP endpoints
- Automated pytest unit tests with pinned dependencies
- A README that covers full setup, verification, and manual test scenarios
- `.gitignore` and `.bobignore`
- Clear documentation separating application unit tests from live Cloudflare security tests
- Explicit pass/fail acceptance criteria for every testable scenario

**Non-Goals / Explicit Exclusions:**
- No pretend / fake MFA logic in the application itself (MFA is enforced by Cloudflare Access)
- No real Cloudflare credentials, tunnel tokens, or API calls
- No deployment to any real infrastructure
- No destructive operations or real administrator data anywhere in the codebase

**Cloudflare Account Dependency:** Every step that requires the learner's own Cloudflare account
is marked with `[CLOUDFLARE ACCOUNT REQUIRED]` throughout the plan and README.

---

## Architecture

```
Internet User
     │
     ▼
Cloudflare Edge  ──────────────────────────────────────────────┐
  (Cloudflare Access)                                          │
  • Identity check (IdP login)                                │
  • MFA enforcement policy                                    │
  • Zero-trust policy: allow/deny by email or group           │
     │ (only after policy passes)                             │
     ▼                                                        │
Cloudflare Tunnel (cloudflared)                               │
  • Outbound-only connection from your machine to Cloudflare  │
  • No inbound firewall ports needed                         │
  • Terminates at 127.0.0.1:8080                             │
     │                                                        │
     ▼                                                        │
Waitress (WSGI server)                                        │
  • Bound exclusively to 127.0.0.1:8080                      │
  • Not reachable from the LAN or internet directly          │
     │                                                        │
     ▼                                                        │
Flask Application                                             │
  GET /admin    — fake admin console (static HTML)            │
  GET /healthz  — JSON health probe                           │
└─────────────────────────────────────────────────────────────┘
```

**Trust Boundary:** The only network path to the Flask app from the internet is
Cloudflare Edge → cloudflared tunnel → 127.0.0.1:8080. Direct LAN or internet access
to port 8080 is prevented by the loopback binding.

---

## Threat Assumptions

| Threat | Mitigation |
|---|---|
| Attacker bypasses Cloudflare and hits 8080 directly from LAN | Waitress binds only to 127.0.0.1 — LAN packets cannot reach it |
| Attacker guesses the public Cloudflare URL | Cloudflare Access policy blocks unauthenticated requests before they reach the tunnel |
| Tunnel token is exposed | No token is stored in this repo. Token is provided by the learner at runtime via env var or CLI only |
| MFA is not enforced | Cloudflare Access policy is configured with MFA as a required authentication method — the app itself has no role in this |
| Tunnel crashes; learner is locked out | Recovery procedure documented in README; healthz endpoint verifies recovery |
| Learner accidentally commits credentials | .gitignore excludes .env and token files; README warns explicitly |

---

## Failure Cases Documented

- **Tunnel not running:** Browser receives a Cloudflare error page; `/healthz` is unreachable externally.
- **Access policy misconfigured (too permissive):** Unauthenticated user reaches `/admin` — manual test TC-03 catches this.
- **MFA not required in policy:** Authenticated-but-no-MFA user reaches `/admin` — manual test TC-04 catches this.
- **Port 8080 accessible from LAN:** Direct curl from another machine succeeds — manual test TC-06 catches this.
- **Tunnel restarts:** All active sessions are dropped; after restart the app is reachable again — manual test TC-07 covers recovery.

---

## Implementation Phases

| Phase | Description |
|---|---|
| 1 | Project scaffold: directory layout, .gitignore, .bobignore, pinned requirements.txt |
| 2 | Flask application: /admin and /healthz endpoints, Waitress entry point |
| 3 | Automated pytest tests for application logic |
| 4 | README: architecture, setup, Cloudflare account steps, verification, acceptance criteria |

---

## Sub-Tasks

---

### Sub-Task 1 — Project Scaffold

**Status:** `[ ] pending`

**Intent:**
Establish the project skeleton so every subsequent sub-task has a clean, conventional place to
land. This includes dependency pinning, ignore files, and the top-level directory structure.

**Expected Outcomes:**
- `requirements.txt` exists with all runtime and test dependencies pinned to exact versions
- `.gitignore` suppresses Python artifacts, virtual environments, `.env` files, and any tunnel
  token files
- `.bobignore` suppresses the same noisy paths from Bob's file context
- `src/` directory exists for application code
- `tests/` directory exists for test code

**Todo List:**
1. Create `requirements.txt` pinning: `flask`, `waitress`, `pytest`, `pytest-cov`, and
   `requests` (for test HTTP calls). Use exact versions compatible with Python 3.11+.
2. Create `.gitignore` covering: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `.env`,
   `*.env`, `tunnel-token.txt`, `*.token`, `dist/`, `*.egg-info/`, `.pytest_cache/`,
   `htmlcov/`, `.coverage`.
3. Create `.bobignore` with the same paths plus `cloudflare-ztna-plan.md` (plan is not
   source code).
4. Create empty `src/__init__.py` and `tests/__init__.py` placeholder files.

**Relevant Context:**
- Python 3.11+ target; Windows-compatible paths
- No `setup.py` or `pyproject.toml` needed — this is a scripts-style lab, not a package

---

### Sub-Task 2 — Flask Application

**Status:** `[ ] pending`

**Intent:**
Implement the two HTTP endpoints that serve as the "protected resource" the lab secures.
The application must be completely harmless: no real data, no real credentials, no mutations.

**Expected Outcomes:**
- `src/app.py` contains a Flask application with exactly two routes
- `GET /admin` returns a clearly-labelled fake admin console HTML page. The page must
  include a visible disclaimer that it contains no real data.
- `GET /healthz` returns `{"status": "ok"}` with HTTP 200
- `src/server.py` contains a Waitress entry point that binds to `127.0.0.1:8080` only.
  The host is hardcoded — it must not be overridable by an environment variable to prevent
  accidental exposure.
- Running `python src/server.py` starts the server and logs the bound address

**Todo List:**
1. Create `src/app.py`:
   - Import Flask
   - Define `app = Flask(__name__)`
   - `GET /healthz` — return `jsonify({"status": "ok"})`, 200
   - `GET /admin` — return an HTML response with a prominent fake-data disclaimer,
     a heading "Demo Admin Console", and a table of five clearly fake rows
     (e.g., "user-1@example.invalid", role "viewer", last login "never"). No forms,
     no POST routes, no mutations.
2. Create `src/server.py`:
   - Import `waitress.serve` and `app` from `src.app`
   - Call `serve(app, host="127.0.0.1", port=8080)` — host is a literal string, never
     an env var
   - Print startup message before calling serve

**Relevant Context:**
- Waitress is a production-quality pure-Python WSGI server; it replaces Flask's dev server
- The loopback binding (127.0.0.1) is the primary local security control
- The app carries no state; every request is stateless and read-only

---

### Sub-Task 3 — Automated Pytest Tests

**Status:** `[ ] pending`

**Intent:**
Provide automated tests that verify application behaviour without requiring any Cloudflare
account or running cloudflared. These are pure unit/integration tests of the Flask app itself.

**Expected Outcomes:**
- `tests/test_app.py` contains at least five test functions
- All tests pass with `pytest tests/` from the project root
- Test coverage report is generatable with `pytest --cov=src tests/`
- Tests do NOT mock or simulate Cloudflare Access, MFA, or any tunnel behaviour

**Todo List:**
1. Create `tests/test_app.py`:
   - Import `pytest` and the Flask `app` from `src.app`
   - Use `app.test_client()` as a pytest fixture
   - `test_healthz_returns_200` — GET `/healthz`, assert 200 and `{"status":"ok"}`
   - `test_healthz_content_type` — assert response Content-Type is `application/json`
   - `test_admin_returns_200` — GET `/admin`, assert 200
   - `test_admin_contains_disclaimer` — assert response body contains the disclaimer text
   - `test_admin_contains_fake_data_only` — assert response body contains "example.invalid"
     (confirming only fake addresses are present) and does NOT contain any real domain
     (a simple check that no `@gmail.com`, `@company.com` etc. appears)
   - `test_unknown_route_returns_404` — GET `/nonexistent`, assert 404
2. Add a `pytest.ini` (or `[tool.pytest.ini_options]` equivalent) that sets `testpaths = tests`
   and enables verbose output by default.

**Relevant Context:**
- Flask's built-in test client does not start a real HTTP server — tests run in-process
- No network calls, no Cloudflare dependency, no tunnel needed for these tests
- These tests are explicitly *not* the same as the live Cloudflare security tests documented
  in the README (see Sub-Task 4)

---

### Sub-Task 4 — README and Acceptance Criteria

**Status:** `[ ] pending`

**Intent:**
Produce comprehensive documentation that guides a learner from zero to a fully-verified
ZTNA lab. The README must clearly separate what can be tested automatically (pytest) from
what must be tested manually against a live Cloudflare account.

**Expected Outcomes:**
- `README.md` is complete and self-contained
- Every step requiring a Cloudflare account is clearly marked
- All acceptance criteria are written as explicit pass/fail test cases
- Architecture diagram (ASCII) is included
- The difference between application unit tests and live Cloudflare security tests is
  explained in a dedicated section

**Todo List:**

1. **Prerequisites section** — list Python 3.11+, pip, a terminal, a Cloudflare account
   (free tier is sufficient), and a registered domain on Cloudflare.

2. **Architecture section** — reproduce the ASCII diagram from this plan.

3. **Local setup section:**
   - Clone / download the repo
   - Create and activate a virtual environment
   - `pip install -r requirements.txt`
   - `python src/server.py` to start Waitress
   - Verify with `curl http://127.0.0.1:8080/healthz`

4. **Cloudflare account setup section** — mark every bullet `[CLOUDFLARE ACCOUNT REQUIRED]`:
   - Create a Cloudflare Tunnel in the Zero Trust dashboard (or via CLI): name it
     `ztna-lab-tunnel`
   - Configure the tunnel's public hostname to route `yourdomain.example.com/*` to
     `http://127.0.0.1:8080`
   - Install `cloudflared` on the lab machine
   - Obtain the tunnel token from the dashboard and run cloudflared with it:
     `cloudflared tunnel run --token <YOUR_TOKEN>` — **never commit the token**
   - Create a Cloudflare Access application covering `yourdomain.example.com/admin`
   - Set the Identity Provider (Google, GitHub, or Cloudflare One-Time PIN)
   - Create an Access Policy that: allows only your email address, requires MFA (set
     the "Authentication methods" condition to "mfaVerified: true")
   - Save and verify the Access application is active

5. **Running automated tests section:**
   - `pytest` — explain these tests verify app logic only, require no Cloudflare account,
     and run entirely locally
   - `pytest --cov=src tests/` for coverage

6. **Difference between test types section:**
   - **Application unit tests (pytest):** Test Flask route logic in-process. No network,
     no Cloudflare, no tunnel. Run anytime, no account needed. Verify: correct HTTP status
     codes, response bodies, content-type headers.
   - **Live Cloudflare security tests (manual):** Test the full ZTNA enforcement chain.
     Require a running tunnel, an active Access policy, and a Cloudflare account. Verify:
     authentication gates work, MFA is enforced, unauthenticated access is blocked,
     the loopback binding prevents direct LAN access.

7. **Manual test scenarios (acceptance criteria) section** — each test case has:
   - TC ID, description, preconditions, steps, expected result (PASS), failure result (FAIL)

   | TC | Scenario | Preconditions |
   |---|---|---|
   | TC-01 | Local app responds on loopback | Waitress running |
   | TC-02 | Tunnel delivers authenticated request to /admin | Tunnel + Access policy active, user logged in with MFA |
   | TC-03 | Unauthenticated access is blocked | Tunnel + Access policy active, user NOT logged in |
   | TC-04 | MFA-less authentication is blocked | Access policy requires mfaVerified; user logs in without MFA method |
   | TC-05 | Denied user cannot reach /admin | Policy allows only your email; use a different email |
   | TC-06 | Direct LAN access to port 8080 is impossible | Waitress running; attempt from a second machine on the same LAN |
   | TC-07 | Recovery after tunnel restart | Kill cloudflared; verify /admin is unavailable; restart cloudflared; verify /admin is reachable again |

   Write each TC as a full prose block with steps and explicit PASS/FAIL wording.

8. **Threat assumptions section** — reproduce the threat table from this plan.

9. **Failure cases section** — reproduce the failure cases from this plan.

10. **Security reminders section:**
    - Never commit a tunnel token, `.env` file, or any credential
    - The `.gitignore` already excludes token files — verify before every `git commit`
    - The app is a demo only; do not connect it to real systems or real data

---

## Acceptance Criteria Summary

The lab is complete when ALL of the following are true:

### Automated (pytest)
- [ ] `pytest tests/` exits 0 with all tests passing
- [ ] `pytest --cov=src tests/` reports ≥ 90% coverage on `src/app.py`
- [ ] No test imports or references Cloudflare, cloudflared, or any live network resource

### Manual (live Cloudflare account required)
- [ ] TC-01 PASS: `curl http://127.0.0.1:8080/healthz` returns `{"status":"ok"}` 200
- [ ] TC-02 PASS: Authenticated + MFA user reaches `/admin` through public Cloudflare URL
- [ ] TC-03 PASS: Unauthenticated browser request to public URL is redirected to Cloudflare login
- [ ] TC-04 PASS: Policy with mfaVerified condition blocks a user who authenticates without MFA
- [ ] TC-05 PASS: A different email address receives an "Access denied" page
- [ ] TC-06 PASS: `curl http://<LAN-IP>:8080/admin` from a second machine fails to connect (connection refused)
- [ ] TC-07 PASS: After killing and restarting cloudflared, `/admin` becomes reachable again within 30 seconds

### Structural
- [ ] `requirements.txt` has all versions pinned (no bare package names without `==`)
- [ ] `.gitignore` excludes `.env`, `*.token`, `tunnel-token.txt`
- [ ] No real credentials, real email addresses, or real domain names appear in any source file
- [ ] `src/server.py` binds to the literal string `"127.0.0.1"` — no env-var override path exists
