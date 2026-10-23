# Cloudflare ZTNA Lab

A self-contained learning project demonstrating **Zero-Trust Network Access** using
[Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/),
[Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/), and MFA.

The "protected resource" is a harmless Python Flask demo admin console served by Waitress.
It contains **no real data, no real credentials, and no destructive operations**.
Authentication and MFA are enforced entirely by Cloudflare Access; the application
performs no identity checks of its own.

---

## Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Local setup](#local-setup)
- [Running the automated tests](#running-the-automated-tests)
- [Starting the application](#starting-the-application)
- [Cloudflare account setup](#cloudflare-account-setup)
- [Two kinds of tests](#two-kinds-of-tests)
- [Manual acceptance tests](#manual-acceptance-tests)
- [Threat model](#threat-model)
- [Known failure cases](#known-failure-cases)
- [Security reminders](#security-reminders)

---

## Architecture

```
Internet User
     │
     ▼
Cloudflare Edge  (Cloudflare Access)
  • Identity check via IdP (Google, GitHub, or One-Time PIN)
  • MFA enforcement — requires mfaVerified: true
  • Allow/deny policy scoped to your email address
     │  (request proceeds only after policy passes)
     ▼
Cloudflare Tunnel  (cloudflared process on your machine)
  • Outbound-only encrypted connection — no inbound firewall rules needed
  • Terminates locally at http://127.0.0.1:8080
     │
     ▼
Waitress  (WSGI server, bound to 127.0.0.1:8080 only)
  • Not reachable from the LAN or the public internet directly
     │
     ▼
Flask Application
  GET /admin   — read-only demo admin console (fake data, visible disclaimer)
  GET /healthz — returns {"status": "ok"} JSON
```

**Trust boundary:** The only path from the internet to the Flask app is
`Cloudflare Edge → cloudflared → 127.0.0.1:8080`.
Direct LAN or internet access to port 8080 is physically blocked by the loopback binding.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11 or later | <https://python.org/downloads/> |
| pip | Bundled with Python 3.11+ |
| A terminal | PowerShell on Windows; bash/zsh on macOS/Linux |
| `[CLOUDFLARE ACCOUNT REQUIRED]` A Cloudflare account | Free tier is sufficient — <https://dash.cloudflare.com/sign-up> |
| `[CLOUDFLARE ACCOUNT REQUIRED]` A domain registered in Cloudflare | Needed to issue a public hostname for the tunnel |

---

## Local setup

### Windows (PowerShell)

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install pinned dependencies
pip install -r requirements.txt

# 3. Verify the install
python -c "import flask, waitress, pytest; print('OK')"
```

### macOS / Linux

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install pinned dependencies
pip install -r requirements.txt

# 3. Verify the install
python -c "import flask, waitress, pytest; print('OK')"
```

---

## Running the automated tests

> These tests require **no Cloudflare account, no running tunnel, and no network
> connectivity**.  They run entirely in-process.  See
> [Two kinds of tests](#two-kinds-of-tests) for why.

### Windows (PowerShell)

```powershell
# Activate the virtual environment first (if not already active)
.\.venv\Scripts\Activate.ps1

# Run all tests
pytest

# Run with coverage report
pytest --cov=app tests/
```

### macOS / Linux

```bash
source .venv/bin/activate
pytest
pytest --cov=app tests/
```

**Expected output:** all tests pass, exit code 0.  Coverage on `app.py` should be ≥ 90 %.

---

## Starting the application

The server binds **only** to `127.0.0.1:8080`.  This is a hardcoded literal in
[`server.py`](server.py) — it cannot be changed by an environment variable.

> ⚠️ **Always start the server with `python server.py`.  Do not use
> `waitress-serve app:app` directly** — that command bypasses `server.py` and
> Waitress defaults to binding on `0.0.0.0` (all interfaces), which would expose
> the application on your LAN.

### Windows (PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
python server.py
```

### macOS / Linux

```bash
source .venv/bin/activate
python server.py
```

**Expected startup output:**

```
Starting Waitress on http://127.0.0.1:8080/
Bound to loopback only — not reachable from LAN or internet.
Press Ctrl+C to stop.
```

### Verify the listening address

While the server is running, open a second terminal and run:

#### Windows (PowerShell)

```powershell
# Confirm the app responds
Invoke-RestMethod http://127.0.0.1:8080/healthz

# Confirm Waitress is only listening on 127.0.0.1, not 0.0.0.0
netstat -ano | Select-String "8080"
```

The `netstat` output should show `127.0.0.1:8080`, **not** `0.0.0.0:8080`.
Any entry showing `0.0.0.0:8080` would mean the server is reachable from the LAN — stop it immediately.

#### macOS / Linux

```bash
curl -s http://127.0.0.1:8080/healthz
# Expected: {"status": "ok"}

# Confirm loopback-only binding
ss -tlnp | grep 8080        # Linux
lsof -i TCP:8080            # macOS
```

The output must show `127.0.0.1:8080`, not `0.0.0.0:8080` or `*:8080`.

---

## Cloudflare account setup

> Every step in this section is marked **`[CLOUDFLARE ACCOUNT REQUIRED]`**.
> None of this is automated by the code in this repository.
> You perform these steps in the Cloudflare Zero Trust dashboard and on your machine.
> **Never commit a tunnel token or credential to this repository.**

### Step 1 — Install cloudflared  `[CLOUDFLARE ACCOUNT REQUIRED]`

Download the `cloudflared` binary for your platform:
<https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/>

#### Windows

```powershell
# Download the MSI from the link above and run it, or use winget:
winget install --id Cloudflare.cloudflared
```

#### macOS

```bash
brew install cloudflare/cloudflare/cloudflared
```

#### Linux

```bash
# Example for Debian/Ubuntu — check the docs for your distro
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

Verify:

```bash
cloudflared --version
```

---

### Step 2 — Create the tunnel  `[CLOUDFLARE ACCOUNT REQUIRED]`

1. Log in to <https://one.dash.cloudflare.com/> → **Networks → Tunnels**.
2. Click **Create a tunnel** → choose **Cloudflared** as the connector type.
3. Name the tunnel `ztna-lab-tunnel` and click **Save tunnel**.
4. On the next screen Cloudflare displays a `cloudflared tunnel run --token <TOKEN>` command.
   **Copy that token value and keep it somewhere safe (a password manager).
   Do not write it to any file inside this repository.**

---

### Step 3 — Configure the public hostname  `[CLOUDFLARE ACCOUNT REQUIRED]`

Still on the tunnel configuration screen:

1. Click the **Public Hostname** tab.
2. Click **Add a public hostname**.
3. Fill in:
   - **Subdomain:** e.g. `ztna-lab`
   - **Domain:** your domain registered in Cloudflare
   - **Type:** `HTTP`
   - **URL:** `127.0.0.1:8080`
4. Click **Save hostname**.

Your tunnel URL is now `https://ztna-lab.yourdomain.example/`.

---

### Step 4 — Run cloudflared with your token  `[CLOUDFLARE ACCOUNT REQUIRED]`

With the Flask app already running in another terminal:

#### Windows (PowerShell)

```powershell
# Replace <YOUR_TOKEN> with the token from Step 2 — do NOT commit this command to git history
$env:CF_TOKEN = "<YOUR_TOKEN>"
cloudflared tunnel run --token $env:CF_TOKEN
```

#### macOS / Linux

```bash
cloudflared tunnel run --token <YOUR_TOKEN>
```

Cloudflare will confirm the tunnel is connected.  Leave this terminal open.

---

### Step 5 — Create a Cloudflare Access application  `[CLOUDFLARE ACCOUNT REQUIRED]`

1. In the Zero Trust dashboard → **Access → Applications**.
2. Click **Add an application** → **Self-hosted**.
3. Fill in:
   - **Application name:** `ZTNA Lab Admin Console`
   - **Application domain:** `ztna-lab.yourdomain.example/admin`
     (scope only `/admin`, not the whole hostname, so `/healthz` remains an unprotected probe)
4. Click **Next**.

---

### Step 6 — Set an Identity Provider  `[CLOUDFLARE ACCOUNT REQUIRED]`

1. In the Access application wizard → **Authentication** tab.
2. Select an Identity Provider you have configured (Google, GitHub, or **One-Time PIN** which requires no separate IdP setup).
3. To configure One-Time PIN: **Settings → Authentication → Login methods → Add new → One-time PIN**.

---

### Step 7 — Create an Access policy with MFA  `[CLOUDFLARE ACCOUNT REQUIRED]`

1. Still in the Access application wizard → **Policies** tab → **Add a policy**.
2. Set:
   - **Policy name:** `Allow lab owner with MFA`
   - **Action:** Allow
   - **Include rule:** `Emails` → enter your own email address
3. Add a **Require** rule:
   - **Selector:** `Authentication Method`
   - **Value:** `mfaVerified` (also labelled "Multi-factor authentication" in the UI)
4. Click **Save policy**, then **Save application**.

> **What this achieves:** only your specific email address can access `/admin`, and only
> after completing MFA.  Any other email receives "Access denied".  Any user who
> authenticates without MFA is also denied.

---

### Step 8 — Verify the Access application is active  `[CLOUDFLARE ACCOUNT REQUIRED]`

In the dashboard, the application should show **Active** status.
Open `https://ztna-lab.yourdomain.example/admin` in a browser — you should be
redirected to a Cloudflare Access login page.

---

## Two kinds of tests

This project has two distinct categories of tests with different requirements and purposes.

### Application unit tests (automated, `pytest`)

| Property | Value |
|---|---|
| Tool | `pytest` |
| Cloudflare account needed | ❌ No |
| Network needed | ❌ No |
| Tunnel needed | ❌ No |
| Run time | < 1 second |
| What they verify | Flask route logic, HTTP status codes, response bodies, Content-Type headers |
| What they do NOT verify | Authentication gates, MFA enforcement, tunnel routing, LAN isolation |

These tests use Flask's built-in test client which calls route functions directly in the
same Python process.  No real HTTP port is opened.  They can be run on any machine at any
time, with or without a Cloudflare account.

### Live Cloudflare security tests (manual)

| Property | Value |
|---|---|
| Tool | Browser, curl, second machine |
| Cloudflare account needed | ✅ Yes |
| Network needed | ✅ Yes |
| Tunnel needed | ✅ Yes (cloudflared running) |
| What they verify | Auth gate, MFA enforcement, deny policy, LAN isolation, tunnel recovery |
| What they do NOT verify | Flask route logic (that is covered by pytest) |

These tests require the full ZTNA stack to be running: Flask app → Waitress →
cloudflared tunnel → Cloudflare Access policy.  They are described in detail below.

---

## Manual acceptance tests

Run the automated `pytest` suite **first** and confirm all pass before attempting any
manual test.

For all manual tests below:

- **Flask app:** running (`python server.py`)
- **cloudflared:** running and connected (unless the test involves stopping it)
- **Access application:** active in Cloudflare dashboard

---

### TC-01 — Local app responds on loopback

**Preconditions:** Waitress running.  cloudflared not required.

**Steps:**

```powershell
# Windows
Invoke-RestMethod http://127.0.0.1:8080/healthz
```

```bash
# macOS / Linux
curl -s http://127.0.0.1:8080/healthz
```

**PASS:** Response is `{"status": "ok"}` with HTTP 200.

**FAIL:** Connection refused, timeout, or any non-200 response.
Check that `python server.py` is running in another terminal.

---

### TC-02 — Authenticated + MFA user can reach /admin

**Preconditions:** Flask running, cloudflared connected, Access application active,
your email address in the Allow policy, an MFA method enrolled.

**Steps:**

1. Open a **private/incognito browser window**.
2. Navigate to `https://ztna-lab.yourdomain.example/admin`.
3. Complete the Cloudflare Access login with your allowed email.
4. Complete MFA when prompted.

**PASS:** The browser displays the "Demo Admin Console" page with the disclaimer banner.

**FAIL:** Access denied page, redirect loop, or connection error.
Verify the tunnel is connected and the Access policy includes your email.

---

### TC-03 — Unauthenticated request is blocked

**Preconditions:** Flask running, cloudflared connected, Access application active.

**Steps:**

1. Open a **private/incognito browser window** (ensures no existing session cookie).
2. Navigate to `https://ztna-lab.yourdomain.example/admin`.
3. Do **not** log in — close the window or navigate away at the login page.

**PASS:** The browser is redirected to a Cloudflare Access login page and never reaches the admin console.

**FAIL:** The admin console is displayed without any login prompt.
Your Access policy is misconfigured — review the application's policy in the dashboard.

---

### TC-04 — MFA-less authentication is blocked

**Preconditions:** Flask running, cloudflared connected, Access policy has the
`mfaVerified` Require rule.

**Steps:**

1. Temporarily use an identity provider that does **not** prompt for MFA (e.g., configure
   a test login with no authenticator app enrolled), or use a second account with no MFA
   method registered.
2. In a private window, navigate to `https://ztna-lab.yourdomain.example/admin`.
3. Log in successfully (valid email, correct password) but without completing any MFA step.

**PASS:** Cloudflare Access returns an "Access denied" or "Authentication required" error.
The admin console page is never displayed.

**FAIL:** The admin console is displayed without MFA being completed.
Remove the `mfaVerified` Require rule from your Access policy and re-add it correctly.

---

### TC-05 — Denied user (wrong email) cannot reach /admin

**Preconditions:** Flask running, cloudflared connected, Access policy allows only your
specific email address.

**Steps:**

1. In a private window, navigate to `https://ztna-lab.yourdomain.example/admin`.
2. Log in with a **different email address** (one not in the Allow rule), completing MFA
   if prompted.

**PASS:** Cloudflare Access displays an "Access denied" page.  The admin console is never shown.

**FAIL:** The admin console is displayed for an email address not in the policy.
Check the Include rule in your Access policy.

---

### TC-06 — Direct LAN access to port 8080 is refused

**Preconditions:** Waitress running.  A second device on the same LAN (a phone, second
laptop, or a VM with a bridged network adapter).

**Steps:**

1. Find the LAN IP of the machine running Waitress:
   - Windows: `ipconfig` → look for the IPv4 address under your active adapter (e.g., `192.168.1.50`)
   - macOS/Linux: `ip addr` or `ifconfig`
2. From the **second device**, attempt:

```bash
curl -v --connect-timeout 5 http://192.168.1.50:8080/admin
```

(Replace `192.168.1.50` with the actual LAN IP.)

**PASS:** The connection is refused or times out immediately.  The second device receives
no HTTP response from the Flask app.

**FAIL:** The second device receives the admin console page.
Waitress is not bound to 127.0.0.1.  Stop the server, verify `server.py` has
`host="127.0.0.1"`, and restart.

---

### TC-07 — Recovery after tunnel restart

**Preconditions:** Flask running, cloudflared running, TC-02 has passed (admin page
is reachable through the public URL).

**Steps:**

1. In the terminal running `cloudflared`, press **Ctrl+C** to stop it.
2. In a browser, navigate to `https://ztna-lab.yourdomain.example/admin`.
   **Expected:** Cloudflare displays a "Tunnel not found" or "502 Bad Gateway" error.
3. Restart cloudflared in the same terminal:
   ```powershell
   # Windows
   cloudflared tunnel run --token $env:CF_TOKEN
   ```
   ```bash
   # macOS / Linux
   cloudflared tunnel run --token <YOUR_TOKEN>
   ```
4. Wait for the "connected" message (usually within 5–15 seconds).
5. Refresh the browser tab from step 2.

**PASS:** After cloudflared reconnects, the admin console is reachable again (following a
successful Access login) within 30 seconds.

**FAIL:** The page remains unreachable after cloudflared reconnects.
Check the cloudflared logs for errors.  Confirm the tunnel's public hostname is still
configured correctly in the dashboard.

---

## Threat model

| Threat | Mitigation |
|---|---|
| Attacker on LAN hits port 8080 directly | Waitress binds only to `127.0.0.1` — LAN packets are dropped at the OS level |
| Attacker guesses the public Cloudflare URL | Cloudflare Access blocks unauthenticated requests before they reach the tunnel |
| Tunnel token is exposed via git | No token is stored in this repository; `.gitignore` excludes all `*.token` and `.env` files |
| MFA is not enforced | Access policy has a `mfaVerified` Require rule — the app has no role in MFA |
| Tunnel crashes and the learner is locked out | Recovery procedure in TC-07; `/healthz` confirms app is still alive locally |
| Learner accidentally commits credentials | `.gitignore` excludes `.env`, `*.env`, `*.token`, `tunnel-token.txt`; see Security reminders |

---

## Known failure cases

| Failure | Symptom | Resolution |
|---|---|---|
| Tunnel not running | Browser sees Cloudflare 1033 / 502 error | Restart `cloudflared tunnel run --token <TOKEN>` |
| Access policy too permissive (no mfaVerified rule) | Unauthenticated user reaches `/admin` | TC-03 / TC-04 detect this; fix the policy in the dashboard |
| Port 8080 exposed on LAN | Direct `curl` from another machine succeeds | TC-06 detects this; verify `server.py` uses `127.0.0.1` |
| Wrong email in Allow rule | Allowed user receives "Access denied" | Add the correct email to the Include rule in the Access policy |
| Flask not running | `cloudflared` connected but `/admin` returns 502 | Start `python server.py` |

---

## Security reminders

> **These reminders apply every time you work with this lab.**

1. **Never commit a tunnel token.**
   The token grants anyone who has it the ability to create a tunnel in your account.
   Store it in a password manager or your OS keychain only.

2. **Verify `.gitignore` before every commit.**
   Run `git status` and confirm no `.env`, `*.token`, or `tunnel-token.txt` files are staged.

3. **This application is a demo only.**
   Do not connect it to real databases, real user accounts, or any system that holds real data.

4. **Stop cloudflared when you are not actively using the lab.**
   There is no reason to keep the tunnel open when you have finished a session.

5. **The app performs no authentication.**
   Every HTTP request that reaches the Flask app has already passed Cloudflare Access.
   If you ever bypass Cloudflare (e.g., direct loopback access), the app will serve the
   page without any identity check.  That is by design for this lab, and is why the
   loopback binding is the critical local control.
