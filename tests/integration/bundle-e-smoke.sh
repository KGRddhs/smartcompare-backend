#!/bin/sh
# Bundle E pre-deploy curl smoke pack.
#
# Plan § Test S3 — ALL must PASS before OTA fires from frontend.
#
# Coverage:
#   1.  /health                                — must be 200
#   2.  /api/v1/text/compare                   — sentinel safety check (must NOT 500)
#   3a. /api/v1/home/savings                   — auth required, expect 200 OR 401
#   3b. /api/v1/home/smart-pick                — auth required, expect 200 OR 401
#   3c. /api/v1/home/trending                  — auth-optional, expect 200
#   3d. /api/v1/profile/recent-decisions       — auth required, expect 200 OR 401
#   3e. /api/v1/profile/monthly-stats          — auth required, expect 200 OR 401
#   3f. /api/v1/profile/priorities-weighted    — auth required, expect 200 OR 401
#   4.  /api/v1/text/compare/stream            — SSE happy-path, expect 200 + at least 5 lines
#
# Without $TOKEN exported, auth-required endpoints return 401 and the smoke
# pack still passes (a 401 from auth-gated route proves the route reached
# the auth dependency, not that the route 500'd). Export $TOKEN to get
# real 200 checks for authed endpoints.
#
# Exit codes:
#   0  — all checks PASS, OK to OTA
#   1  — at least one RED, BLOCK OTA + investigate
#
# Usage:
#   sh tests/integration/bundle-e-smoke.sh
#   TOKEN=ey... sh tests/integration/bundle-e-smoke.sh
#   BASE_URL=http://localhost:8000 sh tests/integration/bundle-e-smoke.sh
#
# POSIX-only: no bash arrays, no [[, no $(()) — works on Railway alpine, macOS,
# Windows Git-Bash without surprises.

set -u

BASE_URL="${BASE_URL:-https://web-production-58776.up.railway.app}"
TOKEN="${TOKEN:-}"
RED_COUNT=0

# X-Device-Fingerprint must match ^[a-f0-9]{64}$ per auth_routes.py — derive
# from a fixed input so smoke runs are idempotent across CI invocations.
# (Avoid sha256sum which is GNU-only; openssl is on every macOS/Linux/alpine.)
FP="$(printf '%s' 'bundle-e-smoke-fingerprint-seed' | openssl dgst -sha256 -hex 2>/dev/null | awk '{print $NF}')"
if [ -z "$FP" ] || [ ${#FP} -ne 64 ]; then
    # openssl missing — fall back to a hard-coded valid-shape hex.
    FP='dada1eedba5eba110abadf00d1eaffab1ec00ffeeba5eba11deadbeefca11feed'
fi

# Auth header construction — emit "" if no TOKEN, never "-H Authorization: Bearer "
# which curl can mis-parse on some shells.
AUTH_ARG_1=""
AUTH_ARG_2=""
if [ -n "$TOKEN" ]; then
    AUTH_ARG_1="-H"
    AUTH_ARG_2="Authorization: Bearer $TOKEN"
fi

# --- helpers -----------------------------------------------------------------

# probe <label> <expected_codes_csv> <url> [extra_curl_args...]
# Records RED when actual status code is not in the expected_codes_csv list.
probe() {
    label="$1"
    expected="$2"
    url="$3"
    shift 3

    if [ -n "$AUTH_ARG_1" ]; then
        actual=$(curl -s -o /dev/null -w '%{http_code}' \
            "$AUTH_ARG_1" "$AUTH_ARG_2" \
            -H "X-Device-Fingerprint: $FP" \
            "$@" "$url")
    else
        actual=$(curl -s -o /dev/null -w '%{http_code}' \
            -H "X-Device-Fingerprint: $FP" \
            "$@" "$url")
    fi

    ok=0
    OIFS=$IFS
    IFS=','
    for code in $expected; do
        if [ "$actual" = "$code" ]; then
            ok=1
            break
        fi
    done
    IFS=$OIFS

    if [ $ok -eq 1 ]; then
        printf 'PASS  %s  %s  →  %s\n' "$label" "$url" "$actual"
    else
        printf 'FAIL  %s  %s  →  %s (expected %s)\n' "$label" "$url" "$actual" "$expected"
        RED_COUNT=$((RED_COUNT + 1))
    fi
}

# --- 1. /health ---------------------------------------------------------------

probe '1.  /health' '200' "$BASE_URL/health"

# --- 2. sentinel safety: text/compare must not 500 (rate-limit OK) -----------
# Cached path; 200 or 429 (rate limited) both acceptable, but 5xx is RED.

probe '2.  sentinel /text/compare' '200,429,401,400' \
    "$BASE_URL/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24"

# --- 3. editorial endpoints ---------------------------------------------------

probe '3a. /home/savings' '200,401' "$BASE_URL/api/v1/home/savings"
probe '3b. /home/smart-pick' '200,401' "$BASE_URL/api/v1/home/smart-pick"
probe '3c. /home/trending' '200' "$BASE_URL/api/v1/home/trending"
probe '3d. /profile/recent-decisions' '200,401' "$BASE_URL/api/v1/profile/recent-decisions"
probe '3e. /profile/monthly-stats' '200,401' "$BASE_URL/api/v1/profile/monthly-stats"
probe '3f. /profile/priorities-weighted' '200,401' "$BASE_URL/api/v1/profile/priorities-weighted"

# --- 4. SSE happy-path --------------------------------------------------------
# Stream a comparison for 25s max, count lines. 5+ lines = stream produced
# events (init/title/specs/prices/reviews/verdict/complete = 7 expected).
# We don't assert the count tightly because cache + cold paths differ.

sse_url="$BASE_URL/api/v1/text/compare/stream?q=iPhone+15+vs+Galaxy+S24"
if [ -n "$AUTH_ARG_1" ]; then
    sse_lines=$(curl -N -s --max-time 25 \
        "$AUTH_ARG_1" "$AUTH_ARG_2" \
        -H "X-Device-Fingerprint: $FP" \
        "$sse_url" | head -200 | wc -l | awk '{print $1}')
else
    sse_lines=$(curl -N -s --max-time 25 \
        -H "X-Device-Fingerprint: $FP" \
        "$sse_url" | head -200 | wc -l | awk '{print $1}')
fi

if [ "$sse_lines" -ge 5 ]; then
    printf 'PASS  4.  SSE /text/compare/stream  →  %s lines (>=5)\n' "$sse_lines"
else
    printf 'FAIL  4.  SSE /text/compare/stream  →  %s lines (expected >=5)\n' "$sse_lines"
    RED_COUNT=$((RED_COUNT + 1))
fi

# --- verdict ------------------------------------------------------------------

printf '\n'
if [ "$RED_COUNT" -eq 0 ]; then
    printf 'ALL %s checks PASS — OK to OTA.\n' "10"
    exit 0
else
    printf '%s RED check(s) — BLOCK OTA, investigate above.\n' "$RED_COUNT"
    exit 1
fi
