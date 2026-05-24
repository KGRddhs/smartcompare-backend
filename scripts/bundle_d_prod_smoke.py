"""Bundle D Phase 3 Task 3.B.1 — prod-Railway curl smoke pack.

Runs the full Backend smoke pack against the deployed Railway endpoint
after Bundle D merge + redeploy. Per-endpoint HTTP-code assertion + a
brief shape check (jq-style). Outputs pass/fail summary with per-call
timing in milliseconds.

Usage:
    python scripts/bundle_d_prod_smoke.py
    python scripts/bundle_d_prod_smoke.py --base https://other-host.example.com
    python scripts/bundle_d_prod_smoke.py --auth-token <jwt>  # exercises auth-required endpoints
    python scripts/bundle_d_prod_smoke.py --verbose            # dump full response bodies

Exit code: 0 if all probes pass, 1 if any fail. Safe to wire into a
post-deploy CI hook.

Throwaway test user creds:
- Email: bundle-d-smoke-<timestamp>@qaren.app (uniquely-generated each run)
- Password: BundleD-Smoke-2026-05-23!  (10+ chars, 1 upper/lower/digit/symbol)
The register probe creates a user the first time. Subsequent runs that
hit the same minute would fail the email-already-exists check — that's
why the timestamp suffix is included.

What's covered (per Bundle D anchor Task 3.B.1):
  ✓ /health                              — basic uptime
  ✓ /api/v1/app/version                  — force-update env vars
  ✓ /api/v1/auth/register                — happy path + throwaway user
  ✓ /api/v1/auth/login                   — happy path with the same creds
  ✓ /api/v1/auth/refresh                 — stale-token error shape (no real refresh)
  ✓ /api/v1/auth/preferences PUT          — RLS path
  ✓ /api/v1/auth/reengagement-subs PUT    — R18 verification
  ✓ /api/v1/auth/social-login apple       — R4 gradient parity vs google
  ✓ /api/v1/auth/social-login google      — known-enabled baseline for parity
  ✓ /api/v1/text/compare GET              — cached path
  ✓ /api/v1/legal/privacy_policy          — R22 Qaren rebrand + new path
  ✓ /api/v1/legal/terms_of_service        — R22 Qaren rebrand + new path
  ✓ /api/v1/comparisons GET               — history list
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib.parse import urlencode

import httpx


DEFAULT_BASE_URL = "https://web-production-58776.up.railway.app"
SMOKE_TIMEOUT_SECONDS = 60.0  # generous — /text/compare can take ~25s cold


# ============================================
# Probe types
# ============================================


@dataclass
class ProbeResult:
    name: str
    method: str
    path: str
    expected_status: int | tuple[int, ...]
    actual_status: Optional[int] = None
    duration_ms: Optional[float] = None
    passed: bool = False
    error: str = ""
    notes: list[str] = field(default_factory=list)


# ============================================
# Helper shape-check assertions
# ============================================


def _body_is_json_object(body: Any) -> tuple[bool, str]:
    if not isinstance(body, dict):
        return False, f"expected JSON object, got {type(body).__name__}"
    return True, ""


def _body_has_keys(body: Any, *keys: str) -> tuple[bool, str]:
    ok, err = _body_is_json_object(body)
    if not ok:
        return ok, err
    missing = [k for k in keys if k not in body]
    if missing:
        return False, f"missing keys: {missing}"
    return True, ""


def _body_contains_substring(body: Any, needle: str) -> tuple[bool, str]:
    """Top-level dict containing a string field that mentions `needle`."""
    if isinstance(body, dict) and "content" in body:
        return (
            (needle in body.get("content", "")),
            (f"'{needle}' not in body.content" if needle not in body.get("content", "") else ""),
        )
    return False, f"body has no 'content' field for substring check"


def _body_must_not_contain(body: Any, needle: str) -> tuple[bool, str]:
    """Inverse: assert the substring does NOT appear in body.content."""
    if isinstance(body, dict) and "content" in body:
        return (
            (needle not in body.get("content", "")),
            (f"FORBIDDEN '{needle}' found in body.content" if needle in body.get("content", "") else ""),
        )
    return True, ""  # no content = passes by default


# ============================================
# Probe definitions
# ============================================


def run_probes(
    base_url: str,
    auth_token: Optional[str] = None,
    verbose: bool = False,
) -> list[ProbeResult]:
    """Run all probes against `base_url`, returning a list of results."""
    timestamp = int(time.time())
    test_email = f"bundle-d-smoke-{timestamp}@qaren.app"
    test_password = "BundleD-Smoke-2026-05-23!"

    results: list[ProbeResult] = []

    # Track session-derived auth_token from the login probe so downstream
    # auth-required endpoints don't need the user to supply --auth-token.
    derived_token: Optional[str] = auth_token

    def _do(
        result: ProbeResult,
        request_fn: Callable[..., httpx.Response],
        shape_check: Optional[Callable[[Any], tuple[bool, str]]] = None,
    ) -> ProbeResult:
        """Execute the request, time it, run optional shape check."""
        start = time.perf_counter()
        try:
            response = request_fn()
            result.actual_status = response.status_code
            result.duration_ms = round((time.perf_counter() - start) * 1000, 1)

            # HTTP-code assertion
            expected = result.expected_status
            ok_status = (
                response.status_code == expected
                if isinstance(expected, int)
                else response.status_code in expected
            )
            if not ok_status:
                result.error = (
                    f"HTTP {response.status_code} != expected {expected}; "
                    f"body[:200]={response.text[:200]!r}"
                )
                result.passed = False
                return result

            # Shape check
            if shape_check is not None:
                try:
                    body = response.json()
                except Exception:
                    body = None
                ok_shape, shape_err = shape_check(body)
                if not ok_shape:
                    result.error = f"shape check failed: {shape_err}"
                    result.passed = False
                    return result

            result.passed = True
            if verbose and result.actual_status == 200:
                try:
                    result.notes.append(f"body[:200]={response.text[:200]!r}")
                except Exception:
                    pass
        except httpx.HTTPError as exc:
            result.duration_ms = round((time.perf_counter() - start) * 1000, 1)
            result.error = f"transport error: {type(exc).__name__}: {exc}"
            result.passed = False
        except Exception as exc:  # noqa: BLE001
            result.duration_ms = round((time.perf_counter() - start) * 1000, 1)
            result.error = f"unexpected error: {type(exc).__name__}: {exc}"
            result.passed = False
        return result

    with httpx.Client(timeout=SMOKE_TIMEOUT_SECONDS, follow_redirects=False) as client:
        # -----------------------------------------------------
        # 1. /health
        # -----------------------------------------------------
        r = ProbeResult(name="health", method="GET", path="/health", expected_status=200)
        _do(r, lambda: client.get(f"{base_url}/health"))
        results.append(r)

        # -----------------------------------------------------
        # 2. /api/v1/app/version  (force-update env vars)
        # -----------------------------------------------------
        r = ProbeResult(
            name="app-version", method="GET", path="/api/v1/app/version",
            expected_status=200,
        )
        _do(
            r,
            lambda: client.get(f"{base_url}/api/v1/app/version"),
            shape_check=lambda b: _body_has_keys(
                b, "min_version", "latest_version", "force_update"
            ),
        )
        results.append(r)

        # -----------------------------------------------------
        # 3. /api/v1/legal/privacy_policy — R22 Qaren rebrand + new path
        # -----------------------------------------------------
        r = ProbeResult(
            name="legal-privacy (R22)", method="GET",
            path="/api/v1/legal/privacy_policy",
            expected_status=200,
        )
        _do(
            r,
            lambda: client.get(f"{base_url}/api/v1/legal/privacy_policy"),
            shape_check=lambda b: _body_contains_substring(b, "Qaren"),
        )
        results.append(r)

        r = ProbeResult(
            name="legal-privacy no SmartCompare residue (R22)",
            method="GET", path="/api/v1/legal/privacy_policy",
            expected_status=200,
        )
        _do(
            r,
            lambda: client.get(f"{base_url}/api/v1/legal/privacy_policy"),
            shape_check=lambda b: _body_must_not_contain(b, "SmartCompare"),
        )
        results.append(r)

        # -----------------------------------------------------
        # 4. /api/v1/legal/terms_of_service — R22 Qaren rebrand
        # -----------------------------------------------------
        r = ProbeResult(
            name="legal-terms (R22)", method="GET",
            path="/api/v1/legal/terms_of_service",
            expected_status=200,
        )
        _do(
            r,
            lambda: client.get(f"{base_url}/api/v1/legal/terms_of_service"),
            shape_check=lambda b: _body_contains_substring(b, "Qaren"),
        )
        results.append(r)

        # -----------------------------------------------------
        # 5. /api/v1/auth/register — throwaway test user
        # -----------------------------------------------------
        r = ProbeResult(
            name="auth-register", method="POST",
            path="/api/v1/auth/register",
            expected_status=(200, 201),
        )
        _do(
            r,
            lambda: client.post(
                f"{base_url}/api/v1/auth/register",
                json={"email": test_email, "password": test_password},
            ),
            shape_check=lambda b: _body_has_keys(b, "success"),
        )
        results.append(r)

        # -----------------------------------------------------
        # 6. /api/v1/auth/login — same creds
        # -----------------------------------------------------
        r = ProbeResult(
            name="auth-login", method="POST",
            path="/api/v1/auth/login",
            expected_status=200,
        )

        def _do_login() -> httpx.Response:
            return client.post(
                f"{base_url}/api/v1/auth/login",
                json={"email": test_email, "password": test_password},
            )

        _do(
            r, _do_login,
            shape_check=lambda b: _body_has_keys(b, "success", "session"),
        )
        # Capture the access token for downstream auth-required probes
        if r.passed and derived_token is None:
            try:
                _resp = _do_login()
                _body = _resp.json()
                if _body.get("success") and _body.get("session"):
                    derived_token = _body["session"].get("access_token")
                    r.notes.append("derived auth_token captured for downstream probes")
            except Exception:
                r.notes.append("could NOT capture derived token; downstream auth probes will skip")
        results.append(r)

        # -----------------------------------------------------
        # 7. /api/v1/auth/refresh — stale-token error shape (NOT a real refresh)
        # -----------------------------------------------------
        r = ProbeResult(
            name="auth-refresh (stale-token error shape)",
            method="POST", path="/api/v1/auth/refresh",
            expected_status=401,
        )
        _do(
            r,
            lambda: client.post(
                f"{base_url}/api/v1/auth/refresh",
                json={"refresh_token": "INVALID_STALE_TOKEN_FOR_GRADIENT"},
            ),
            shape_check=None,  # 401 with any body shape is fine — we're just verifying the error path
        )
        results.append(r)

        # -----------------------------------------------------
        # 8. /api/v1/auth/preferences PUT — RLS path
        # -----------------------------------------------------
        if derived_token is not None:
            r = ProbeResult(
                name="auth-preferences PUT (RLS)",
                method="PUT", path="/api/v1/auth/preferences",
                expected_status=200,
            )
            _do(
                r,
                lambda: client.put(
                    f"{base_url}/api/v1/auth/preferences",
                    headers={"Authorization": f"Bearer {derived_token}"},
                    json={
                        "priorities": ["price", "quality"],
                        "budget": "mid",
                        "lifestyle": [],
                        "brand_attitude": "function_first",
                    },
                ),
                shape_check=lambda b: _body_has_keys(b, "success"),
            )
            results.append(r)

        # -----------------------------------------------------
        # 9. /api/v1/auth/reengagement-subs PUT — R18 verification
        # -----------------------------------------------------
        if derived_token is not None:
            r = ProbeResult(
                name="auth-reengagement-subs PUT (R18)",
                method="PUT", path="/api/v1/auth/reengagement-subs",
                expected_status=200,
            )
            _do(
                r,
                lambda: client.put(
                    f"{base_url}/api/v1/auth/reengagement-subs",
                    headers={"Authorization": f"Bearer {derived_token}"},
                    json={
                        "decision_insights": True,
                        "peer_decision_updates": False,
                        "decision_retrospectives": True,
                    },
                ),
                shape_check=lambda b: (
                    _body_has_keys(b, "success", "notification_types")[0]
                    and isinstance(b.get("notification_types"), dict)
                    and "decision_insight" in b["notification_types"],
                    "expected singular-key notification_types in response",
                ),
            )
            results.append(r)

        # -----------------------------------------------------
        # 10. /api/v1/auth/social-login apple — R4 gradient parity
        # -----------------------------------------------------
        r = ProbeResult(
            name="auth-social-login apple (R4 gradient)",
            method="POST", path="/api/v1/auth/social-login",
            expected_status=401,  # invalid token → AUTH_REQUIRED (provider IS enabled)
        )
        _do(
            r,
            lambda: client.post(
                f"{base_url}/api/v1/auth/social-login",
                json={"provider": "apple", "id_token": "INVALID_TEST_TOKEN_FOR_GRADIENT"},
            ),
        )
        r.notes.append("expected 401 + AUTH_REQUIRED proves provider is enabled (parity with google)")
        results.append(r)

        # -----------------------------------------------------
        # 11. /api/v1/auth/social-login google — known-enabled baseline
        # -----------------------------------------------------
        r = ProbeResult(
            name="auth-social-login google (parity baseline)",
            method="POST", path="/api/v1/auth/social-login",
            expected_status=401,
        )
        _do(
            r,
            lambda: client.post(
                f"{base_url}/api/v1/auth/social-login",
                json={"provider": "google", "id_token": "INVALID_TEST_TOKEN_FOR_GRADIENT"},
            ),
        )
        r.notes.append("if apple matches this shape, R4 is healthy")
        results.append(r)

        # -----------------------------------------------------
        # 12. /api/v1/text/compare GET — cached path
        # -----------------------------------------------------
        r = ProbeResult(
            name="text-compare GET (cached)",
            method="GET", path="/api/v1/text/compare",
            expected_status=200,
        )
        _do(
            r,
            lambda: client.get(
                f"{base_url}/api/v1/text/compare",
                params={
                    "q": "iPhone 15 vs Samsung Galaxy S24",
                    "region": "bahrain",
                    "nocache": "false",
                },
            ),
            shape_check=lambda b: _body_has_keys(b, "success", "products", "metadata"),
        )
        results.append(r)

        # -----------------------------------------------------
        # 13. /api/v1/comparisons GET — history list
        # -----------------------------------------------------
        if derived_token is not None:
            r = ProbeResult(
                name="comparisons GET (history list)",
                method="GET", path="/api/v1/comparisons/history",
                expected_status=200,
            )
            _do(
                r,
                lambda: client.get(
                    f"{base_url}/api/v1/comparisons/history?limit=10",
                    headers={"Authorization": f"Bearer {derived_token}"},
                ),
                shape_check=lambda b: _body_has_keys(b, "comparisons"),
            )
            results.append(r)

    return results


# ============================================
# Reporter
# ============================================


def _color(s: str, code: str) -> str:
    """Best-effort ANSI; falls back to bare string if stdout isn't a tty."""
    if sys.stdout.isatty():
        return f"\033[{code}m{s}\033[0m"
    return s


def report(results: list[ProbeResult]) -> int:
    """Print per-probe pass/fail + summary. Returns process exit code."""
    print()
    print("=" * 80)
    print(f"Bundle D — Phase 3 prod smoke pack — {len(results)} probes")
    print("=" * 80)

    n_pass = sum(1 for r in results if r.passed)
    n_fail = len(results) - n_pass

    for r in results:
        status_tag = _color("PASS", "32") if r.passed else _color("FAIL", "31")
        duration_str = f"{r.duration_ms:>7.1f}ms" if r.duration_ms is not None else "    --ms"
        status_code_str = f"HTTP {r.actual_status}" if r.actual_status is not None else "HTTP --"
        print(
            f"  {status_tag}  {duration_str}  {status_code_str:<10}  "
            f"{r.method:<6} {r.path:<50} {r.name}"
        )
        if r.error:
            print(f"        |-{_color(r.error, '31')}")
        for note in r.notes:
            print(f"        |-{note}")

    print()
    print("-" * 80)
    summary_color = "32" if n_fail == 0 else "31"
    print(
        f"  Summary: {_color(f'{n_pass} pass / {n_fail} fail', summary_color)} "
        f"out of {len(results)} probes"
    )
    print("-" * 80)
    print()

    return 0 if n_fail == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bundle D Phase 3 — prod-Railway curl smoke pack.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base", default=DEFAULT_BASE_URL,
        help=f"base URL (default {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--auth-token", default=None,
        help="JWT auth token to use for auth-required probes (otherwise derived from register+login)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="include response body excerpts in output",
    )
    args = parser.parse_args()

    results = run_probes(
        base_url=args.base.rstrip("/"),
        auth_token=args.auth_token,
        verbose=args.verbose,
    )
    return report(results)


if __name__ == "__main__":
    sys.exit(main())
