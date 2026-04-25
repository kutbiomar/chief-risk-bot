#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_BASE="${CRB_APP_BASE:-https://app.chiefriskbot.com}"
API_BASE="${CRB_API_BASE:-https://api.chiefriskbot.com/api}"
SMOKE_EMAIL="${CRB_SMOKE_EMAIL:-cio@demo.chiefriskbot.com}"
SMOKE_PASSWORD="${CRB_SMOKE_PASSWORD:-DemoPass2026!}"

python3 - "$APP_BASE" "$API_BASE" "$SMOKE_EMAIL" "$SMOKE_PASSWORD" <<'PY'
import json
import sys
import urllib.error
import urllib.request

app_base, api_base, smoke_email, smoke_password = [arg.rstrip("/") for arg in sys.argv[1:]]


def request(url, *, method="GET", headers=None, body=None):
    payload = None
    req_headers = {
        "User-Agent": "ChiefRiskBotSmoke/1.0 (+https://app.chiefriskbot.com)",
        "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
        **dict(headers or {}),
    }
    if body is not None:
      payload = json.dumps(body).encode("utf-8")
      req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=payload, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()


def expect(condition, message):
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def expect_status(url, expected, **kwargs):
    status, headers, body = request(url, **kwargs)
    expect(status == expected, f"{kwargs.get('method', 'GET')} {url} -> {status}, expected {expected}")
    return headers, body


print(f"Smoke target app: {app_base}")
print(f"Smoke target api: {api_base}")

headers, body = expect_status(f"{app_base}/login", 200)
csp = headers.get("content-security-policy", "")
expect("connect-src" in csp and "https://api.chiefriskbot.com" in csp, "frontend CSP missing api.chiefriskbot.com connect-src")
print("PASS: frontend login page and CSP")

_, health_body = expect_status(f"{api_base}/health", 200)
health = json.loads(health_body.decode("utf-8"))
expect(health.get("status") == "ok", f"health payload not ok: {health}")
print("PASS: api health")

_, login_body = expect_status(
    f"{api_base}/auth/login",
    200,
    method="POST",
    headers={"Origin": app_base},
    body={"email": smoke_email, "password": smoke_password},
)
login = json.loads(login_body.decode("utf-8"))
token = login.get("access_token", "")
expect(token, "login response missing access_token")
expect(login.get("user", {}).get("workspace_name") == "Whitmore Family Office", "login workspace mismatch")
auth_headers = {"Authorization": f"Bearer {token}", "Origin": app_base}
print("PASS: api login")

for path in (
    "/auth/session",
    "/onboarding/state",
    "/cockpit",
    "/liquidity/summary",
    "/briefings",
    "/settings",
    "/documents",
):
    _, payload = expect_status(f"{api_base}{path}", 200, headers=auth_headers)
    if path == "/auth/session":
        session = json.loads(payload.decode("utf-8"))
        expect(session.get("user", {}).get("workspace_name") == "Whitmore Family Office", "session workspace mismatch")
    print(f"PASS: {path}")

print("Production smoke complete.")
PY
