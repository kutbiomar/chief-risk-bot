#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_BASE="${CRB_APP_BASE:-https://app.chiefriskbot.com}"
API_BASE="${CRB_API_BASE:-https://api.chiefriskbot.com/api}"
SMOKE_EMAIL="${CRB_SMOKE_EMAIL:-cio@demo.chiefriskbot.com}"
SMOKE_PASSWORD="${CRB_SMOKE_PASSWORD:-DemoPass2026!}"
SMOKE_REQUIRE_RESET="${CRB_SMOKE_REQUIRE_RESET:-0}"
SMOKE_RESET_TOKEN="${CRB_SMOKE_RESET_TOKEN:-}"
SMOKE_ROTATED_PASSWORD="${CRB_SMOKE_ROTATED_PASSWORD:-}"

python3 - "$APP_BASE" "$API_BASE" "$SMOKE_EMAIL" "$SMOKE_PASSWORD" "$SMOKE_REQUIRE_RESET" "$SMOKE_RESET_TOKEN" "$SMOKE_ROTATED_PASSWORD" <<'PY'
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

app_base, api_base, smoke_email, smoke_password = [arg.rstrip("/") for arg in sys.argv[1:5]]
require_reset = sys.argv[5] == "1"
reset_token = sys.argv[6]
rotated_password = sys.argv[7]
api_origin = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(api_base))
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


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
        with opener.open(req, timeout=20) as response:
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


def cookie_value(name):
    for cookie in cookie_jar:
        if cookie.name == name:
            return cookie.value
    return ""


def login(password, *, expected=200):
    status, headers, body = request(
        f"{api_base}/auth/login",
        method="POST",
        headers={"Origin": app_base},
        body={"email": smoke_email, "password": password},
    )
    expect(status == expected, f"POST {api_base}/auth/login -> {status}, expected {expected}")
    return headers, body


print(f"Smoke target app: {app_base}")
print(f"Smoke target api: {api_base}")

headers, body = expect_status(f"{app_base}/login", 200)
csp = headers.get("content-security-policy", "")
expect("connect-src" in csp and api_origin in csp, f"frontend CSP missing {api_origin} connect-src")
print("PASS: frontend login page and CSP")

_, health_body = expect_status(f"{api_base}/health", 200)
health = json.loads(health_body.decode("utf-8"))
expect(health.get("status") == "ok", f"health payload not ok: {health}")
print("PASS: api health")

evil_status, evil_headers, _ = request(
    f"{api_base}/cockpit",
    method="OPTIONS",
    headers={
        "Origin": "https://evil.example",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    },
)
expect(evil_status in {200, 204, 400}, f"unexpected CORS preflight status for evil origin: {evil_status}")
expect(evil_headers.get("access-control-allow-origin") != "https://evil.example", "evil origin received permissive ACAO")
print("PASS: unauthorized CORS origin blocked")

request_id = "smoke-request-id"
health_headers, _ = expect_status(f"{api_base}/health", 200, headers={"X-Request-Id": request_id})
expect(health_headers.get("x-request-id") == request_id, "health did not echo X-Request-Id")
print("PASS: request id echo")

login_headers, login_body = login(smoke_password)
login = json.loads(login_body.decode("utf-8"))
token = login.get("access_token", "")
expect(token, "login response missing access_token")
expect(login.get("user", {}).get("workspace_name") == "Whitmore Family Office", "login workspace mismatch")
set_cookie = login_headers.get("set-cookie", "")
if set_cookie:
    expect("Secure" in set_cookie, "session cookie missing Secure")
    expect("HttpOnly" in set_cookie, "session cookie missing HttpOnly")
    expect("SameSite=Lax" in set_cookie or "SameSite=None" in set_cookie, "session cookie missing SameSite")
auth_headers = {"Authorization": f"Bearer {token}", "Origin": app_base}
print("PASS: api login")

invalid_status, _, _ = request(
    f"{api_base}/auth/session",
    headers={"Authorization": "Bearer invalid-smoke-token", "Origin": app_base},
)
expect(invalid_status == 401, f"invalid bearer returned {invalid_status}, expected 401")
print("PASS: invalid bearer rejected")

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

csrf = cookie_value("__crb_csrf")
expect(csrf, "login did not set __crb_csrf cookie")
logout_status, _, _ = request(
    f"{api_base}/auth/logout",
    method="POST",
    headers={"Origin": app_base, "X-CSRF-Token": csrf},
)
expect(logout_status == 200, f"logout returned {logout_status}, expected 200")
logged_out_status, _, _ = request(f"{api_base}/auth/session", headers=auth_headers)
expect(logged_out_status == 401, f"logged-out bearer returned {logged_out_status}, expected 401")
print("PASS: logout revokes session")

if require_reset:
    expect(reset_token, "CRB_SMOKE_RESET_TOKEN is required when CRB_SMOKE_REQUIRE_RESET=1")
    expect(rotated_password, "CRB_SMOKE_ROTATED_PASSWORD is required when CRB_SMOKE_REQUIRE_RESET=1")
    login(smoke_password)
    csrf = cookie_value("__crb_csrf")
    expect(csrf, "reset preflight login did not set __crb_csrf cookie")
    _, _ = expect_status(
        f"{api_base}/auth/forgot-password",
        200,
        method="POST",
        headers={"Origin": app_base, "X-CSRF-Token": csrf},
        body={"email": smoke_email},
    )
    _, _ = expect_status(
        f"{api_base}/auth/reset-password",
        200,
        method="POST",
        headers={"Origin": app_base, "X-CSRF-Token": csrf},
        body={"token": reset_token, "new_password": rotated_password},
    )
    login(smoke_password, expected=401)
    login_headers, login_body = login(rotated_password)
    rotated = json.loads(login_body.decode("utf-8"))
    expect(rotated.get("access_token"), "rotated-password login response missing access_token")
    print("PASS: staging reset request/completion and password rotation")
else:
    print("SKIP: destructive reset/rotation smoke (set CRB_SMOKE_REQUIRE_RESET=1 for staging)")

print("Production smoke complete.")
PY
