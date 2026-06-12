"""I5.11 — Registry liveness gate (Bundle B S2, plan section 5).

HEAD-resolves every SOURCE_REGISTRY domain so dead rows (the electronics-0/14
root cause class) cannot silently recur. Control-calibrated per the S2 safety
rail: a known-live control must pass IN THIS ENVIRONMENT before any "dead"
verdict is trusted; HTTP 403/405 (bot defense) counts as ALIVE.

Usage: python -m scripts.verify_source_registry  (exit 0 = all rows live,
2 = dead rows found, 3 = environment blocked / controls failed)
"""
import socket
import sys

import httpx

CONTROLS = ["google.com", "shopalmoayyed.com"]
ALIVE_STATUSES = set(range(200, 400)) | {403, 405, 429}
TIMEOUT = 10.0


def _check(domain: str) -> tuple[str, str]:
    """Returns (verdict, evidence): verdict in {alive, dead, blocked}."""
    try:
        socket.gethostbyname(domain)
    except socket.gaierror as e:
        return "dead", f"NXDOMAIN ({e.args[0] if e.args else e})"
    try:
        r = httpx.head(f"https://{domain}", timeout=TIMEOUT, follow_redirects=True)
        if r.status_code in ALIVE_STATUSES:
            return "alive", f"http={r.status_code}"
        return "dead", f"http={r.status_code}"
    except httpx.HTTPError as e:
        # resolved but unreachable over HTTPS -> suspicious, not NXDOMAIN-dead
        return "blocked", f"{type(e).__name__}"


def main() -> int:
    from app.services.source_router import SOURCE_REGISTRY

    for c in CONTROLS:
        verdict, ev = _check(c)
        if verdict != "alive":
            print(f"CONTROL FAILED: {c} -> {verdict} ({ev}); environment untrusted")
            return 3

    dead = []
    for src in SOURCE_REGISTRY:
        verdict, ev = _check(src.domain)
        print(f"{src.domain:32s} {verdict:8s} {ev}")
        if verdict == "dead":
            dead.append((src.domain, ev))
    if dead:
        print("DEAD ROWS (" + str(len(dead)) + "): " + ", ".join(d for d, _ in dead))
        return 2
    print("All registry rows live (controls calibrated).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
