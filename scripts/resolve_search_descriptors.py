#!/usr/bin/env python3
"""UNIT D3 — the OFF-CLOCK resolver for per-host SEARCH DESCRIPTORS.

WHAT IT DOES. For each host it is given, it works out ONCE where that store's
product search lives and whether robots.txt lets us use it, and writes the
answer to ``data/search_descriptors.json``. The next
``python -m scripts.build_source_registry_data`` folds those answers onto the
registry rows in ``data/bh_gcc_sources.json``, and — with
``ENABLE_SEARCH_DESCRIPTOR`` on — the discovery path reads them instead of
probing.

WHY IT IS A SCRIPT AND NOT A STARTUP TASK. The cost is fetches, and fetches on
the request path are the thing this unit removes. B8 measured that 71 of the 95
live fragrance rows carry no mechanism, so each of them pays a platform probe on
every cold compare; resolving is the same work done once, throttled, off the
clock, with robots consulted first.

THE FOUR SAFETY RULES, ENFORCED IN CODE
  1. **robots-first.** Every host's ``/robots.txt`` is fetched before anything
     else, and every candidate path is evaluated against it with
     ``app.services.robots_eval`` — the RFC 9309-correct evaluator, because
     ``urllib.robotparser`` gives the WRONG (fail-open) answer on real files
     from B8's panel in two ways: it lets a later ``User-agent: *`` group
     overwrite an earlier one, and it prefix-matches a browser UA into a
     ``User-agent: Mozilla`` group. We identify as a NAMED token
     (``robots_eval.NAMED_AGENT``), never as a browser.
  2. **A hard 12-host live cap** (``MAX_LIVE_HOSTS``). A run larger than that is
     refused, not truncated.
  3. **A >= 2s throttle per host** (``MIN_THROTTLE_SECONDS``), floor-enforced.
  4. **Never fragrantica.com or parfumo.com** — ``probe_search_descriptor``
     raises before a fetch (house rule 7).

USAGE
    # plan only — prints what WOULD be resolved, spends nothing:
    python scripts/resolve_search_descriptors.py --from-registry --category fragrances

    # replay from a directory of cached robots/homepage files, zero network:
    python scripts/resolve_search_descriptors.py --hosts fragrancebh.com --cache-dir _proof/robots

    # the real, throttled, capped run:
    python scripts/resolve_search_descriptors.py --hosts a.com,b.com --live

The default is the PLAN. ``--live`` is the only thing that opens a socket.
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from app.services import robots_eval  # noqa: E402
from app.services.search_descriptor_service import (  # noqa: E402
    DENY_HOSTS,
    SearchDescriptor,
    parse_search_descriptor,
    probe_search_descriptor,
)

logger = logging.getLogger("resolve_search_descriptors")

#: Hard ceiling on hosts touched in ONE live run. Not a default — a refusal.
MAX_LIVE_HOSTS = 12
#: Floor on the per-host delay. A smaller --throttle is raised to this.
MIN_THROTTLE_SECONDS = 2.0
#: Per-request timeout, seconds.
FETCH_TIMEOUT = 20
#: The named product token we identify as (see rule 1 above).
USER_AGENT = "%s/1.0 (+https://qaren.app/bot; contact: kingzatel@gmail.com)" % (
    robots_eval.NAMED_AGENT
)

_DEFAULT_OUT = _ROOT / "data" / "search_descriptors.json"
_REGISTRY = _ROOT / "data" / "bh_gcc_sources.json"


# ---------------------------------------------------------------------------
# store
# ---------------------------------------------------------------------------
def read_descriptors(path: Path) -> Dict[str, dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a missing/garbage store starts empty
        return {}
    hosts = data.get("hosts") if isinstance(data, dict) else None
    return {k: v for k, v in hosts.items() if isinstance(v, dict)} if isinstance(hosts, dict) else {}


def write_descriptors(path: Path, resolved: Dict[str, SearchDescriptor]) -> Dict[str, dict]:
    """MERGE ``resolved`` into the store at ``path`` and write it back.

    Merge, never replace: a run that resolves 12 hosts must not delete the 40
    a previous run resolved. Sorted keys so the diff of two runs is readable.
    """
    hosts = read_descriptors(path)
    for host, descriptor in resolved.items():
        hosts[str(host).lower()] = descriptor.to_row()
    payload = {
        "_what": (
            "Per-host SEARCH DESCRIPTORS (M7 D3). Written by "
            "scripts/resolve_search_descriptors.py, folded onto the registry rows by "
            "scripts/build_source_registry_data.py, read at runtime behind "
            "ENABLE_SEARCH_DESCRIPTOR. Each entry is one host's resolved search "
            "surface: where it is, and whether robots.txt allows it."
        ),
        "_updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
        "hosts": {k: hosts[k] for k in sorted(hosts)},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return payload["hosts"]


# ---------------------------------------------------------------------------
# hosts
# ---------------------------------------------------------------------------
def registry_hosts(category: str = "", unresolved_only: bool = True) -> List[Tuple[str, str]]:
    """``[(domain, mechanism), ...]`` for LIVE registry rows, worst-first.

    Worst-first = rows with NO mechanism come before rows that have one: those
    are the 71-of-95 that pay a probe today, so they are where the descriptor
    buys the most. ``unresolved_only`` skips rows that already carry a
    descriptor, which is what makes repeat runs cheap.
    """
    try:
        rows = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print("WARN: cannot read %s: %s" % (_REGISTRY.name, exc), file=sys.stderr)
        return []
    out: List[Tuple[str, str]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or row.get("status") != "live":
            continue
        if category and category not in (row.get("categories") or []):
            continue
        if unresolved_only and parse_search_descriptor(row.get("search")) is not None:
            continue
        if row.get("is_render_only"):
            continue
        domain = str(row.get("domain") or "").strip().lower()
        if not domain or any(domain == d or domain.endswith("." + d) for d in DENY_HOSTS):
            continue
        out.append((domain, str(row.get("mechanism") or "")))
    out.sort(key=lambda t: (bool(t[1]), t[0]))
    return out


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------
def live_fetcher(throttle: float) -> Callable[..., Tuple[int, str]]:
    """A throttled, named-agent fetcher. ``curl_cffi``, falling back to httpx.

    Deliberately NOT ``impersonate="chrome"``: B8's klinq.com finding is that a
    browser-shaped UA falls into a ``User-agent: Mozilla`` / ``Disallow: /``
    group, so impersonating makes us LESS entitled to the bytes, not more.
    """
    state = {"last": 0.0}

    def fetch(url: str, **_kw) -> Tuple[int, str]:
        wait = throttle - (time.monotonic() - state["last"])
        if wait > 0:
            time.sleep(wait)
        state["last"] = time.monotonic()
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        try:
            from curl_cffi import requests as cffi_requests

            resp = cffi_requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
            return int(resp.status_code), resp.text or ""
        except ImportError:
            import httpx

            resp = httpx.get(
                url, headers=headers, timeout=FETCH_TIMEOUT, follow_redirects=True
            )
            return int(resp.status_code), resp.text or ""

    return fetch


def cache_fetcher(cache_dir: Path) -> Callable[..., Tuple[int, str]]:
    """Replay a resolution from files on disk — ZERO network.

    Looks for ``<host>.robots.txt`` and ``<host>.home.html`` in ``cache_dir``;
    anything else is a 404. This is how a resolution is re-run (and reviewed)
    without spending a single fetch.
    """

    def fetch(url: str, **_kw) -> Tuple[int, str]:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.netloc
        name = "%s.robots.txt" % host if parsed.path == "/robots.txt" else (
            "%s.home.html" % host if parsed.path in ("", "/") else ""
        )
        if not name:
            return (404, "")
        path = cache_dir / name
        if not path.exists():
            return (404, "")
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            return (200, fh.read())

    return fetch


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def resolve_hosts(
    hosts: List[Tuple[str, str]],
    fetch: Callable[..., Tuple[int, str]],
) -> Dict[str, SearchDescriptor]:
    resolved: Dict[str, SearchDescriptor] = {}
    for host, mechanism in hosts:
        try:
            descriptor = probe_search_descriptor(host, fetch, mechanism=mechanism)
        except ValueError as exc:  # house rule 7 refusal
            print("SKIP %s: %s" % (host, exc))
            continue
        except Exception as exc:  # noqa: BLE001 — one host must not end the run
            print("FAIL %s: %s" % (host, exc))
            continue
        resolved[host] = descriptor
        print(
            "%-32s kind=%-12s robots_allowed=%-5s via=%s"
            % (host, descriptor.kind, descriptor.robots_allowed, descriptor.discovered_via)
        )
    return resolved


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hosts", default="", help="comma-separated hosts")
    parser.add_argument("--from-registry", action="store_true",
                        help="take LIVE registry rows that have no descriptor yet")
    parser.add_argument("--category", default="", help="registry category filter")
    parser.add_argument("--limit", type=int, default=MAX_LIVE_HOSTS)
    parser.add_argument("--live", action="store_true",
                        help="actually fetch (default: plan only)")
    parser.add_argument("--cache-dir", default="",
                        help="replay from cached <host>.robots.txt/<host>.home.html")
    parser.add_argument("--throttle", type=float, default=2.5,
                        help="seconds between requests (floor %.1f)" % MIN_THROTTLE_SECONDS)
    parser.add_argument("--out", default=str(_DEFAULT_OUT))
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    explicit: List[Tuple[str, str]] = []
    if args.hosts:
        known = dict(registry_hosts(unresolved_only=False))
        for raw in args.hosts.split(","):
            host = raw.strip().lower()
            if host:
                explicit.append((host, known.get(host, "")))
    # An EXPLICIT list is never silently truncated — an over-cap request is a
    # refusal, checked BEFORE any selection so no fetch can precede it.
    if len(explicit) > MAX_LIVE_HOSTS:
        parser.error(
            "refused: %d hosts named, cap is %d. Resolving spends fetches on "
            "someone else's servers — run it in batches."
            % (len(explicit), MAX_LIVE_HOSTS)
        )
    hosts: List[Tuple[str, str]] = list(explicit)
    if args.from_registry:
        hosts.extend(registry_hosts(args.category))
    seen: set = set()
    hosts = [h for h in hosts if not (h[0] in seen or seen.add(h[0]))]
    limit = max(0, args.limit)
    if args.live or args.cache_dir:
        limit = min(limit, MAX_LIVE_HOSTS)
    hosts = hosts[:limit]

    if not hosts:
        parser.error("no hosts selected — pass --hosts or --from-registry")

    if not args.live and not args.cache_dir:
        print("PLAN ONLY (pass --live to fetch, --cache-dir to replay). %d hosts:"
              % len(hosts))
        for host, mechanism in hosts:
            print("  %-32s mechanism=%s" % (host, mechanism or "(none)"))
        return 0

    if args.cache_dir:
        fetch = cache_fetcher(Path(args.cache_dir))
    else:
        fetch = live_fetcher(max(float(args.throttle), MIN_THROTTLE_SECONDS))

    resolved = resolve_hosts(hosts, fetch)
    if not resolved:
        print("nothing resolved — store untouched")
        return 0
    out = Path(args.out)
    stored = write_descriptors(out, resolved)
    print("wrote %d host(s); store now holds %d -> %s"
          % (len(resolved), len(stored), out))
    print("next: python -m scripts.build_source_registry_data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
