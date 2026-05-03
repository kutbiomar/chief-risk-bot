#!/usr/bin/env bash
set -euo pipefail

API_BASE="${CRB_API_BASE:-https://api-staging.chiefriskbot.com/api}"
REQUEST_ID="${CRB_OBSERVABILITY_REQUEST_ID:-observability-smoke-$(date +%s)}"

python3 - "$API_BASE" "$REQUEST_ID" "${CRB_SYNTHETIC_ERROR:-0}" <<'PY'
import sys
import urllib.error
import urllib.request

api_base, request_id, synthetic_enabled = [arg.rstrip("/") for arg in sys.argv[1:]]


def request(path: str):
    req = urllib.request.Request(
        f"{api_base}{path}",
        headers={
            "User-Agent": "ChiefRiskBotObservabilitySmoke/1.0",
            "X-Request-Id": request_id,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


status, headers, _ = request("/health")
expect(status == 200, f"/health returned {status}, expected 200")
expect(headers.get("x-request-id") == request_id, "/health did not echo X-Request-Id")
print("PASS: health request id echo")

if synthetic_enabled == "1":
    status, headers, _ = request("/health/synthetic-error")
    expect(status == 500, f"/health/synthetic-error returned {status}, expected 500")
    expect(headers.get("x-request-id") == request_id, "synthetic error did not echo X-Request-Id")
    print("PASS: synthetic error endpoint fired")
else:
    status, _, _ = request("/health/synthetic-error")
    expect(status == 404, f"synthetic endpoint should be disabled by default, got {status}")
    print("PASS: synthetic error endpoint disabled by default")

print("Observability smoke complete.")
PY
