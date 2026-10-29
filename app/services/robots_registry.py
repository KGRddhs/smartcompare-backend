"""S81-15 REGISTRY-ROBOTS-DENY: the daily robots registry cron (ENABLE_ROBOTS_REGISTRY_CRON).

OFF-CLOCK ONLY. The cron entry script under ``scripts/`` (a dedicated Railway
cron service, ``railway.robots.json``) calls ``run_cron`` once a day; nothing on
the request path imports this module, and no live fetcher reads its verdicts in
this unit (D14 LIVE-ROBOTS owns the per-fetch lookup of the persisted record).

WHAT A RUN DOES. It reads every kb_merchants row, picks the due ones (never read
first, then the oldest ``robots.next_reread``, then host; at most
``ROBOTS_CRON_MAX_HOSTS``; a host is due when its ``next_reread`` is at or before
the run start plus ``ROBOTS_DUE_SLACK_SECONDS``, read once per run, the belt for
cron-start jitter; ``next_reread`` is computed from the run start, + 24 h (the
RFC 9309 cache bound), so a run of any length under 24 h re-reads every host the
previous daily run read, and once the first pass is done no record is older than
24 h + one run), and for each, strictly one request at a time:

* reads ``/robots.txt`` as the named robots agent (``robots_eval.QARENBOT_UA``,
  never a browser impersonation) from the probe ORIGIN: the origin of the row's
  sample PDP when that URL lives on the row's own site (the host or a subdomain
  of it; www and apex are different origins), else the row's own
  ``https://<host>``, with the sample's origin listed under
  ``robots.other_origins`` (a sample on a PARENT host, the salla.sa store pages,
  included; D14 treats an origin without a record as missing: skip and queue);
* follows redirects ITSELF (``allow_redirects=False`` on every fetch, at most 5
  hops, the SSRF validator on the first URL and on EVERY hop; a refused first URL
  is ``robots_unreadable`` with ``health.ssrf = "initial"``, a refused hop is
  ``ssrf_redirect``, and a host that does not resolve is ``robots_unreadable``
  with ``health.dns = "unresolved"``, never an SSRF label); a redirected
  robots.txt governs the ORIGINAL origin; every body is capped at
  ``MAX_BODY_BYTES`` before it is decoded;
* decides fail-closed (``decide_robots``): 404/410 allow-all; any other non-2xx,
  a timeout, a network error or a challenge page is unreadable; a challenge is
  ONLY a wall signature on an HTML-shaped body (``price_service.classify_capture``)
  or a ``cf-mitigated: challenge`` header, so a 5xx origin outage behind a CDN is
  unreadable but never parked; the verdict is the most restrictive of the named
  agent's group and the ``*`` group over the probed paths (``/``, the sample
  path, the adapter endpoint path);
* records the D14 contract (``robots_record``: state, status, body_sha,
  fetched_at, next_reread, crawl_delay, origin, source, the allow / disallow
  rules of both agents verbatim, capped at 200 each, and the per-path probed
  states) and applies the transition table (``next_row_update``): live ->
  blocked on any failure (robots_disallow / robots_unreadable / challenge /
  ssrf_redirect); a cron-blocked row rejoins its prior status on a later allow
  (ruling Option A); a candidate is never blocked: it names its first failing
  promotion gate (robots, tos, pdp, platform) and becomes live only when robots
  allow AND ``tos.verdict == "allowed"`` AND one validated PDP with a priced
  extraction AND a known platform; a challenged host is parked
  (``challenge.parked_until``); rows blocked for deny / owner / tos, and every
  deny_hosts host, are never fetched and never written (``probe_host`` and
  ``classify_host`` refuse a deny_hosts host by name before any request, so the
  seed's residential read and the classifier keep the same belt);
* honours the 2026-08-31 ruling's Option C rider: a residential or operator
  record younger than 30 days is never replaced by a datacenter result, which is
  kept under ``health.last_datacenter_result`` only (``robots.next_reread`` moves
  to the day the protection lapses, so the row is not re-read every run);
* writes each row with ONE conditional update (``eq('updated_at', <seen>)``); a
  lost race is logged by host and skipped until the next run.

Politeness: the sleep before every request after the first of the run is
max(crawl-delay of the host about to be fetched, 2 s) (the stored delay of the
previous read until this read lands; Crawl-delay is parsed in-house and capped
at 60 s). Log lines carry the host and constants or ints only, never a URL, a
body, a header value or an exception message.

Flag OFF the entry script logs one INFO and returns: no read, no fetch. Importing
this module loads neither price_service nor database_service (they are imported
lazily inside the cron-only functions).
"""
from __future__ import annotations

import asyncio
import hashlib
import html as _html
import inspect
import ipaddress
import logging
import math
import os
import re
import socket
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlsplit

from app.services import deny_hosts
from app.services import robots_eval
# The table name is defined ONCE, in the light merchant_registry leaf.
from app.services.merchant_registry import KB_MERCHANTS_TABLE
from app.services.robots_eval import NAMED_AGENT, QARENBOT_UA, can_fetch

logger = logging.getLogger(__name__)

#: The columns a cron run reads (the transition table needs the ops columns).
CRON_COLUMNS = ",".join((
    "host", "status", "deny", "blocked_reason", "registry", "robots", "challenge", "health", "tos",
    "platform", "platform_confidence", "currency_hint", "updated_at",
))
PAGE_SIZE = 500
MAX_PAGES = 200
MIN_DELAY_SECONDS = 2.0
MAX_CRAWL_DELAY_SECONDS = 60.0
ROBOTS_TIMEOUT_SECONDS = 20
PDP_TIMEOUT_SECONDS = 20
REREAD_HOURS = 24
MAX_REDIRECT_HOPS = 5
MAX_RULES_PER_AGENT = 200
MAX_BODY_CHARS = 3_000_000
#: The byte cap of every fetched body, applied BEFORE decoding (F1-11).
MAX_BODY_BYTES = MAX_BODY_CHARS
#: ``ROBOTS_DUE_SLACK_SECONDS`` (F1-3): a host is due when its ``next_reread`` is at or
#: before the run start plus this slack (default 1 h, capped at 6 h): the belt for
#: cron-start jitter, since ``next_reread`` is computed from the run start (RB15-2).
DUE_SLACK_DEFAULT_SECONDS = 3600.0
DUE_SLACK_MAX_SECONDS = 21600.0
#: ``default_validate``'s answers (F1-13): fetch / a refused name or address / no resolution.
VALIDATE_OK = "ok"
VALIDATE_SSRF = "ssrf"
VALIDATE_DNS = "dns"
#: The bound of the one extra resolve that tells a resolver failure from a refused address.
DNS_CLASSIFY_TIMEOUT_SECONDS = 5.0
#: The refusal every entry point gives a deny_hosts host before any request (F1-10).
DENY_REFUSAL = "deny_hosts"
#: Record sources the datacenter cron never downgrades while younger than the window (R-S15-4).
TRUSTED_SOURCES: Tuple[str, ...] = ("residential", "operator")
TRUSTED_RECORD_DAYS = 30
#: The live -> blocked reasons this cron manages (GATE_S81_15 GC-1).
CRON_REASONS: Tuple[str, ...] = ("robots_unreadable", "robots_disallow", "challenge", "ssrf_redirect")
#: Owner / D16 blocks the cron never touches (no fetch, no write).
STICKY_REASONS: Tuple[str, ...] = ("deny", "owner", "tos")
BLOCKED_REASONS: Tuple[str, ...] = STICKY_REASONS + CRON_REASONS
#: The adapter endpoint each same-site mechanism fetches (joins the probed paths, R-S15-3).
ADAPTER_PATHS: Dict[str, str] = {
    "shopify": "/products.json",
    "woo_store_json": "/wp-json/wc/store/products",
    "magento_graphql": "/graphql",
    "occ_rest": "/occ/v2/",
    "noon_catalog": "/_svc/catalog/api/v3/search",
}
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_REQUEST_HEADERS: Dict[str, str] = {"User-Agent": QARENBOT_UA, "Accept": "*/*"}
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_TRUTHY = ("true", "1", "yes", "on")


# ---------------------------------------------------------------------------
# flag and knobs (read per call)
# ---------------------------------------------------------------------------

def robots_registry_cron_enabled() -> bool:
    """True iff ``ENABLE_ROBOTS_REGISTRY_CRON`` is set truthy. Read PER CALL."""
    return os.getenv("ENABLE_ROBOTS_REGISTRY_CRON", "false").strip().lower() in _TRUTHY


def _int_knob(name: str, default: int, low: int, high: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value) or value <= 0:
        return default
    return min(max(int(value), low), high)  # 0 < value < 1 clamps to low (spec 2.1, F1-23)


def max_hosts_per_run() -> int:
    """``ROBOTS_CRON_MAX_HOSTS``: default 500, clamped 1..5000."""
    return _int_knob("ROBOTS_CRON_MAX_HOSTS", 500, 1, 5000)


def challenge_park_days() -> int:
    """``ROBOTS_CHALLENGE_PARK_DAYS``: default 7, clamped 1..30."""
    return _int_knob("ROBOTS_CHALLENGE_PARK_DAYS", 7, 1, 30)


def due_slack_seconds() -> float:
    """``ROBOTS_DUE_SLACK_SECONDS``: default 3600; unset / garbage / inf / nan / < 0 -> 3600;
    capped at 21600; 0 is allowed. Read ONCE per run by ``run_cron`` (F1-3)."""
    raw = os.getenv("ROBOTS_DUE_SLACK_SECONDS")
    if raw is None:
        return DUE_SLACK_DEFAULT_SECONDS
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return DUE_SLACK_DEFAULT_SECONDS
    if not math.isfinite(value) or value < 0:
        return DUE_SLACK_DEFAULT_SECONDS
    return min(value, DUE_SLACK_MAX_SECONDS)


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _g(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _header(headers: Any, name: str) -> str:
    try:
        items = headers.items() if hasattr(headers, "items") else []
        want = name.lower()
        for key, value in items:
            if str(key).lower() == want:
                return str(value)
    except Exception:  # noqa: BLE001 - an odd header object reads as absent
        return ""
    return ""


def _html_shaped(headers: Any, body: Any) -> bool:
    if "text/html" in _header(headers, "content-type").lower():
        return True
    return isinstance(body, str) and body.lstrip()[:1] == "<"


def _path_key(url: str) -> str:
    try:
        parts = urlsplit(url if "://" in url else "//" + url)
    except ValueError:
        return "/"
    path = parts.path or "/"
    return path + ("?" + parts.query if parts.query else "")


def _origin_of(url: str) -> str:
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return ""
    if parts.scheme not in ("http", "https") or not host:
        return ""
    return parts.scheme + "://" + host + (":" + str(port) if port else "")


def _host_of(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _row_host(row: Dict[str, Any]) -> str:
    host = row.get("host")
    return host.strip().lower() if isinstance(host, str) else ""


def _entries(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    registry = row.get("registry")
    if not isinstance(registry, list):
        return []
    entries = [e for e in registry if isinstance(e, dict)]

    def _order(e: Dict[str, Any]) -> int:
        o = e.get("order")
        return o if isinstance(o, int) and not isinstance(o, bool) else 1 << 30

    return sorted(entries, key=_order)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


# ---------------------------------------------------------------------------
# crawl delay, challenge, decide
# ---------------------------------------------------------------------------

def _delay_groups(body: Any) -> List[Tuple[frozenset, List[float]]]:
    """``[(agents, [crawl delays])]`` with ``robots_eval.parse_groups``' grouping:
    consecutive User-agent lines share a record, a User-agent line after an
    allow / disallow rule starts a new one."""
    groups: List[Tuple[frozenset, List[float]]] = []
    agents: set = set()
    delays: List[float] = []
    has_rule = False
    text = body[: robots_eval.MAX_ROBOTS_CHARS] if isinstance(body, str) else ""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if has_rule:
                groups.append((frozenset(agents), delays))
                agents, delays, has_rule = set(), [], False
            if value:
                agents.add(value.lower())
        elif key in ("allow", "disallow"):
            if agents:
                has_rule = True
        elif key == "crawl-delay" and agents:
            try:
                number = float(value)
            except ValueError:
                continue
            if math.isfinite(number) and number >= 0:
                delays.append(number)
    if agents:
        groups.append((frozenset(agents), delays))
    return groups


def parse_crawl_delay(body: Any, agent: str) -> Optional[float]:
    """The ``Crawl-delay`` addressed to ``agent``: the most specific named token,
    else every ``*`` group (same-token records merge); the LARGEST value of the
    selected groups, capped at 60 s; a non-number, nan, inf or a negative value
    is ignored; None when nothing applies. Never raises."""
    try:
        groups = _delay_groups(body)
        low = (agent or "").lower()
        best: Optional[str] = None
        for tokens, _ in groups:
            for token in tokens:
                if token == "*":
                    continue
                if token in low and (best is None or len(token) > len(best)):
                    best = token
        values: List[float] = []
        for tokens, delays in groups:
            if best is not None:
                if best in tokens:
                    values.extend(delays)
            elif "*" in tokens:
                values.extend(delays)
        if not values:
            return None
        return float(min(max(values), MAX_CRAWL_DELAY_SECONDS))
    except Exception:  # noqa: BLE001 - a robots reader never raises
        return None


def challenge_vendor(status: Any, headers: Any, body: Any) -> str:
    """The bot-wall vendor a response names (case-insensitive), else "unknown".
    Consulted only once a challenge was detected (see ``decide_robots``)."""
    server = _header(headers, "server").lower()
    mitigated = _header(headers, "cf-mitigated").lower()
    text = body[:200000].lower() if isinstance(body, str) else ""
    if (mitigated or "cloudflare" in server or "cf_chl" in text or "just a moment" in text
            or "cf-browser-verification" in text):
        return "cloudflare"
    if "akamaighost" in server or ("reference #" in text and "access denied" in text):
        return "akamai"
    if "px-captcha" in text or "perimeterx" in text:
        return "perimeterx"
    if "_incapsula_" in text or "incap_ses" in text:
        return "imperva"
    if "distil" in text:
        return "distil"
    return "unknown"


def _challenge(status: Any, headers: Any, body: str) -> Optional[str]:
    """A vendor when the response IS a challenge, else None (ruling R-S15-12)."""
    if _header(headers, "cf-mitigated").strip().lower() == "challenge":
        return challenge_vendor(status, headers, body)
    if body and _html_shaped(headers, body):
        from app.services import price_service as _ps

        if _ps.classify_capture(body, None, None) == _ps.CAPTURE_WALLED:
            return challenge_vendor(status, headers, body)
    return None


class RobotsVerdict(NamedTuple):
    """One robots read. ``state``: allow | disallow | unreadable (the most
    restrictive over ``probed``); ``challenge_vendor`` is set only when the
    response was a challenge; ``ssrf`` ("initial" | "hop") when the validator
    refused the robots URL or a redirect hop; ``dns`` ("unresolved") when the
    host did not resolve (never an SSRF label, F1-13)."""

    state: str
    status: Optional[int]
    body_sha: Optional[str]
    crawl_delay: Optional[float]
    challenge_vendor: Optional[str]
    rules: Dict[str, List[List[str]]]
    probed: Dict[str, str]
    rules_truncated: bool = False
    ssrf: Optional[str] = None
    dns: Optional[str] = None


def _rules_of(text: str) -> Tuple[Dict[str, List[List[str]]], bool]:
    """The allow / disallow rules addressed to the named agent and to ``*``
    (``robots_eval``'s own merged selection, the one ``can_fetch`` evaluates),
    verbatim, file order, empty patterns dropped (they match nothing), each list
    capped at ``MAX_RULES_PER_AGENT``."""
    groups = robots_eval.parse_groups(text)
    out: Dict[str, List[List[str]]] = {}
    truncated = False
    for key, agent in (("qarenbot", NAMED_AGENT), ("star", "*")):
        rules = robots_eval.rules_for_agent(groups, agent) if groups else []
        listed = [["allow" if is_allow else "disallow", pattern] for is_allow, pattern in rules if pattern]
        if len(listed) > MAX_RULES_PER_AGENT:
            listed = listed[:MAX_RULES_PER_AGENT]
            truncated = True
        out[key] = listed
    return out, truncated


def decide_robots(status: Any, headers: Any, body: Any, probe_urls: Sequence[str]) -> RobotsVerdict:
    """The fail-closed verdict of one robots read (pure; ruling 2026-08-31).

    ``status`` None (timeout, network error, SSRF refusal) -> unreadable. A
    challenge (a ``cf-mitigated: challenge`` header, or a wall signature on an
    HTML-shaped body; never a plain-text body) -> unreadable with its vendor.
    2xx -> the named agent AND ``*`` must both allow every probe URL, else
    disallow. 404 / 410 -> allow-all (no policy published). Anything else (3xx
    after the redirect cap, 401, 403, 429, 5xx ...) -> unreadable."""
    urls = [u for u in (probe_urls or []) if isinstance(u, str) and u]
    paths: List[str] = []
    for url in urls:
        key = _path_key(url)
        if key not in paths:
            paths.append(key)
    text = body if isinstance(body, str) else ""
    st = status if isinstance(status, int) and not isinstance(status, bool) else None

    def _empty() -> Dict[str, List[List[str]]]:
        return {"qarenbot": [], "star": []}

    if st is None:
        return RobotsVerdict("unreadable", None, None, None, None, _empty(), dict.fromkeys(paths, "unreadable"))
    vendor = _challenge(st, headers, text)
    if vendor is None and 200 <= st < 300:
        probed: Dict[str, str] = {}
        for url in urls:
            key = _path_key(url)
            ok = can_fetch(text, NAMED_AGENT, url) and can_fetch(text, "*", url)
            probed[key] = "disallow" if (probed.get(key) == "disallow" or not ok) else "allow"
        state = "disallow" if "disallow" in probed.values() else "allow"
        rules, truncated = _rules_of(text)
        delays = [d for d in (parse_crawl_delay(text, NAMED_AGENT), parse_crawl_delay(text, "*")) if d is not None]
        return RobotsVerdict(
            state, st, hashlib.sha256(text.encode("utf-8")).hexdigest(),
            max(delays) if delays else None, None, rules, probed, truncated,
        )
    if vendor is None and st in (404, 410):
        return RobotsVerdict("allow", st, "", None, None, _empty(), dict.fromkeys(paths, "allow"))
    return RobotsVerdict("unreadable", st, None, None, vendor, _empty(), dict.fromkeys(paths, "unreadable"))


def robots_record(verdict: Any, now: datetime, origin: str, source: str, *,
                  reread_from: Optional[datetime] = None) -> Dict[str, Any]:
    """The persisted ``kb_merchants.robots`` record: the D14 / D09 / S81-16 input
    contract, frozen by ``tests/fixtures/s81_s15_robots_record.json``. Consumers
    answer per URL by evaluating ``rules`` with ``robots_eval.can_fetch``; a
    ``rules_truncated`` key appears only when a list was capped (a consumer must
    then treat a URL the stored rules allow as unknown). ``fetched_at`` is the
    read time; ``next_reread`` is ``reread_from`` (the cron's run start, RB15-2)
    + 24 h, or the read time + 24 h for every other caller."""
    rules = _g(verdict, "rules") or {}
    record = {
        "state": _g(verdict, "state"),
        "status": _g(verdict, "status"),
        "body_sha": _g(verdict, "body_sha"),
        "fetched_at": _iso(now),
        "next_reread": _iso((reread_from if reread_from is not None else now) + timedelta(hours=REREAD_HOURS)),
        "crawl_delay": _g(verdict, "crawl_delay"),
        "origin": origin,
        "source": source,
        "rules": {
            "qarenbot": [list(r) for r in (rules.get("qarenbot") or [])],
            "star": [list(r) for r in (rules.get("star") or [])],
        },
        "probed": dict(_g(verdict, "probed") or {}),
    }
    if _g(verdict, "rules_truncated"):
        record["rules_truncated"] = True
    return record


# ---------------------------------------------------------------------------
# the probe plan and the transition table
# ---------------------------------------------------------------------------

class ProbePlan(NamedTuple):
    host: str
    origin: str
    robots_url: str
    probe_urls: List[str]
    sample_url: str
    other_origins: List[str]
    mechanism: str


def probe_plan(row: Dict[str, Any]) -> ProbePlan:
    """Where one row's robots record is read from (ruling R-S15-2, GATE GC-7).

    The probe origin is the origin of the row's first sample PDP when that URL
    lives on the row's own site (the host or a subdomain of it); otherwise the
    row's own ``https://<host>``, and the sample's origin is listed in
    ``other_origins`` (not fetched). A sample on a PARENT host of the row is
    another origin (F1-4: ``https://salla.sa/<store>/...`` is not the origin of
    ``<store>.salla.sa``). The probed paths are ``/``, the sample
    path (same site only) and the adapter endpoint of the row's mechanism (when
    the adapter runs on that site)."""
    host = _row_host(row)
    entries = _entries(row)
    sample = ""
    mechanism = ""
    for entry in entries:
        if not sample and isinstance(entry.get("sample_url"), str) and entry["sample_url"].strip():
            sample = entry["sample_url"].strip()
        if not mechanism:
            mech = entry.get("mechanism")
            if isinstance(mech, str) and mech:
                mechanism = mech
            elif entry.get("is_shopify") is True:
                mechanism = "shopify"
    origin = "https://" + host
    others: List[str] = []
    same_sample = ""
    if sample:
        s_origin = _origin_of(sample)
        s_host = _host_of(sample)
        if s_origin and s_host and (s_host == host or s_host.endswith("." + host)):
            origin = s_origin
            same_sample = sample
        elif s_origin:
            others.append(s_origin)
    paths = ["/"]
    if same_sample:
        key = _path_key(same_sample)
        if key not in paths:
            paths.append(key)
    if same_sample or not sample:
        adapter = ADAPTER_PATHS.get(mechanism)
        if adapter and adapter not in paths:
            paths.append(adapter)
    return ProbePlan(host, origin, origin + "/robots.txt", [origin + p for p in paths], same_sample, others,
                     mechanism)


def _cron_may_touch(row: Dict[str, Any]) -> bool:
    """False for every row this cron must never fetch or write: a deny_hosts host,
    ``deny`` set, a sticky blocked_reason (deny / owner / tos), a blocked row whose
    reason is not cron-managed, or an unknown status."""
    host = deny_hosts.normalize_host(row.get("host"))
    if not host or deny_hosts.is_denied_host(host):
        return False
    if row.get("deny"):
        return False
    reason = row.get("blocked_reason")
    if reason in STICKY_REASONS:
        return False
    status = row.get("status")
    if status == "blocked":
        return reason in CRON_REASONS
    return status in ("live", "candidate")


def entry_refusal(row: Any) -> Optional[str]:
    """``DENY_REFUSAL`` for a row on a deny_hosts host, else None: the belt every
    entry point applies BEFORE any request (the cron run through ``_cron_may_touch``,
    the seed's residential read and the classifier through ``probe_host`` /
    ``classify_host``; F1-10)."""
    host = deny_hosts.normalize_host(_g(row, "host"))
    if host and deny_hosts.is_denied_host(host):
        return DENY_REFUSAL
    return None


def _young_trusted(stored: Any, now: datetime) -> bool:
    if not isinstance(stored, dict) or stored.get("source") not in TRUSTED_SOURCES:
        return False
    fetched = _parse_iso(stored.get("fetched_at"))
    return fetched is not None and (now - fetched) < timedelta(days=TRUSTED_RECORD_DAYS)


def _block_reason(state: Any, vendor: Optional[str], ssrf: Optional[str]) -> str:
    if vendor:
        return "challenge"
    if ssrf == "hop":
        return "ssrf_redirect"
    if state == "disallow":
        return "robots_disallow"
    return "robots_unreadable"


def _first_failing_gate(gates: Dict[str, Any]) -> Optional[str]:
    if not gates.get("tos"):
        return "tos"
    if not gates.get("pdp"):
        return "pdp"
    if not gates.get("platform"):
        return "platform"
    return None


def next_row_update(row: Dict[str, Any], verdict: Any, now: datetime, gates: Optional[Dict[str, Any]] = None,
                    *, source: str = "datacenter", reread_from: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """The ONE update a robots read makes to ``row`` (pure), or None (never touched).

    Transitions (ruling R-S15-11): live -> blocked on any failure, with
    ``health.pre_block_status`` = live; a cron-blocked row stays blocked (reason
    updated) or rejoins ``pre_block_status`` on an allow (Option A); a candidate
    is never blocked: a robots failure names ``failing_gate`` robots, an allow runs
    the promotion gates (``gates``; None = not evaluated: the robots record only).
    A challenge parks the host for ``ROBOTS_CHALLENGE_PARK_DAYS``. A residential or
    operator record younger than 30 days is never replaced by a datacenter read
    (``health.last_datacenter_result`` records it, GATE GC-5, and
    ``robots.next_reread`` moves to the day the protection lapses, F1-14)."""
    if not isinstance(row, dict) or not _cron_may_touch(row):
        return None
    status = row.get("status")
    stamp = _iso(now)
    plan = probe_plan(row)
    record = robots_record(verdict, now, plan.origin, source, reread_from=reread_from)
    if plan.other_origins:
        record["other_origins"] = list(plan.other_origins)
    health = dict(row["health"]) if isinstance(row.get("health"), dict) else {}
    state = _g(verdict, "state")
    vendor = _g(verdict, "challenge_vendor") or None
    ssrf = _g(verdict, "ssrf") or None
    dns = _g(verdict, "dns") or None
    if source == "datacenter" and _young_trusted(row.get("robots"), now):
        last = {"state": state, "status": _g(verdict, "status"), "fetched_at": stamp}
        if vendor:
            last["challenge_vendor"] = vendor
        if ssrf:
            last["ssrf"] = ssrf
        if dns:
            last["dns"] = dns
        health["last_datacenter_result"] = last
        # The stored verdict stands; the row is next due the day the protection lapses (F1-14).
        kept = dict(row["robots"])
        kept["next_reread"] = _iso(_parse_iso(kept.get("fetched_at")) + timedelta(days=TRUSTED_RECORD_DAYS))
        return {"robots": kept, "health": health, "updated_at": stamp}
    health["last_status"] = _g(verdict, "status")
    if ssrf:
        health["ssrf"] = ssrf
    else:
        health.pop("ssrf", None)
    if dns:
        health["dns"] = dns
    else:
        health.pop("dns", None)
    failing = state != "allow" or vendor is not None
    park = None
    if vendor is not None:
        park = {"vendor": vendor, "parked_until": _iso(now + timedelta(days=challenge_park_days()))}
    payload: Dict[str, Any] = {"robots": record, "health": health, "updated_at": stamp}
    if status == "live":
        if failing:
            health["pre_block_status"] = "live"
            payload.update(status="blocked", blocked_reason=_block_reason(state, vendor, ssrf), challenge=park or {})
        else:
            payload.update(status="live", blocked_reason=None, challenge={})
        return payload
    if status == "blocked":
        if failing:
            if health.get("pre_block_status") not in ("live", "candidate"):
                health["pre_block_status"] = "live"
            payload.update(status="blocked", blocked_reason=_block_reason(state, vendor, ssrf), challenge=park or {})
        else:
            back = health.pop("pre_block_status", None)
            payload.update(status=back if back in ("live", "candidate") else "live", blocked_reason=None,
                           challenge={})
        return payload
    # a candidate: never blocked by the cron
    if failing:
        health["promotion"] = {"failing_gate": "robots", "checked_at": stamp}
        payload["challenge"] = park or {}
        return payload
    if gates is None:
        return payload
    gate = _first_failing_gate(gates)
    if gate is None:
        health.pop("promotion", None)
        payload.update(status="live", blocked_reason=None, challenge={})
        probed_label = gates.get("platform_probed")
        if row.get("platform") in (None, "") and probed_label:
            payload["platform"] = probed_label
            payload["platform_confidence"] = "probe"
        return payload
    health["promotion"] = {"failing_gate": gate, "checked_at": stamp}
    if gate == "pdp" and gates.get("pdp_challenge"):
        payload["challenge"] = {"vendor": gates["pdp_challenge"],
                                "parked_until": _iso(now + timedelta(days=challenge_park_days()))}
    return payload


# ---------------------------------------------------------------------------
# fetching: politeness, redirects by hand, SSRF per hop
# ---------------------------------------------------------------------------

class Politeness:
    """One run's politeness: no wait before the first request, then
    max(crawl-delay of the host about to be fetched, 2 s) before every request."""

    def __init__(self, sleep: Any) -> None:
        self._sleep = sleep
        self._first = True

    async def before_request(self, delay: Any) -> None:
        if self._first:
            self._first = False
            return
        wait = MIN_DELAY_SECONDS
        if isinstance(delay, (int, float)) and not isinstance(delay, bool) and math.isfinite(delay):
            wait = max(min(float(delay), MAX_CRAWL_DELAY_SECONDS), MIN_DELAY_SECONDS)
        await _maybe_await(self._sleep(wait))


class _Fetched(NamedTuple):
    status: Optional[int]
    headers: Any
    body: str
    url: str
    refused: Optional[str]


def _validation_reason(result: Any) -> str:
    """A validator answer as a reason (F1-13): ``default_validate`` answers with a
    reason string; an injected seam may answer with a bool (truthy = fetch). Any
    other string is a refusal (fail closed)."""
    if isinstance(result, str):
        return result if result in (VALIDATE_OK, VALIDATE_DNS) else VALIDATE_SSRF
    return VALIDATE_OK if result else VALIDATE_SSRF


async def _fetch_following(url: str, fetch: Any, validate: Any, polite: Politeness, delay: Any, timeout: float,
                           may_fetch: Any = None) -> _Fetched:
    """GET ``url`` following redirects by hand: the SSRF validator on the first URL
    and on every hop, at most ``MAX_REDIRECT_HOPS`` hops, ``allow_redirects=False``
    on every request; the final status decides. ``refused`` = "initial" | "hop"
    (the validator refused a name or an address) | "dns" (the host did not
    resolve) | "robots" (``may_fetch`` refused a hop)."""
    current = url
    status: Optional[int] = None
    headers: Any = {}
    body = ""
    for hop in range(MAX_REDIRECT_HOPS + 1):
        try:
            reason = _validation_reason(await _maybe_await(validate(current)))
        except Exception:  # noqa: BLE001 - a validator failure fails closed
            reason = VALIDATE_SSRF
        if reason == VALIDATE_DNS:
            return _Fetched(None, {}, "", current, "dns")
        if reason != VALIDATE_OK:
            return _Fetched(None, {}, "", current, "initial" if hop == 0 else "hop")
        if may_fetch is not None and not may_fetch(current):
            return _Fetched(None, {}, "", current, "robots")
        await polite.before_request(delay)
        try:
            result = await _maybe_await(
                fetch(current, headers=dict(_REQUEST_HEADERS), timeout=timeout, allow_redirects=False)
            )
            status, headers, body = result
        except Exception:  # noqa: BLE001 - a failed fetch is unreadable, never an empty body
            return _Fetched(None, {}, "", current, None)
        if not isinstance(status, int) or isinstance(status, bool):
            return _Fetched(None, {}, "", current, None)
        body = body if isinstance(body, str) else ""
        if status in _REDIRECT_STATUSES:
            location = _header(headers, "location").strip()
            if not location:
                return _Fetched(status, headers, body, current, None)
            try:
                current = urljoin(current, location)
            except ValueError:
                return _Fetched(status, headers, body, current, None)
            continue
        return _Fetched(status, headers if headers is not None else {}, body, current, None)
    return _Fetched(status, headers if headers is not None else {}, body, current, None)


def _stored_crawl_delay(row: Dict[str, Any]) -> Optional[float]:
    stored = row.get("robots") if isinstance(row.get("robots"), dict) else {}
    value = stored.get("crawl_delay")
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
        return float(min(value, MAX_CRAWL_DELAY_SECONDS))
    return None


def _pdp_may_fetch(origin: str, robots_body: str) -> Any:
    def _check(url: str) -> bool:
        if _origin_of(url) != origin:
            return False
        return can_fetch(robots_body, NAMED_AGENT, url) and can_fetch(robots_body, "*", url)

    return _check


def pdp_product_name(page: Any) -> str:
    """The product name the PDP price gate hands the extractor (GATE GC-10): the
    page ``<title>``, entity-decoded and whitespace-collapsed, through the house
    name sanitiser ``prompt_sanitizer.sanitize_prompt_input`` (200 chars)."""
    try:
        match = _TITLE_RE.search(page[:200000]) if isinstance(page, str) else None
        raw = " ".join(_html.unescape(match.group(1)).split()) if match else ""
        from app.utils.prompt_sanitizer import sanitize_prompt_input

        return sanitize_prompt_input(raw, max_length=200)
    except Exception:  # noqa: BLE001
        return ""


def _row_currency(row: Dict[str, Any]) -> str:
    hint = row.get("currency_hint")
    if isinstance(hint, str) and re.fullmatch(r"[A-Z]{3}", hint):
        return hint
    for entry in _entries(row):
        cur = entry.get("currency")
        if isinstance(cur, str) and re.fullmatch(r"[A-Z]{3}", cur):
            return cur
    return "BHD"


def _price_ok(price: Any) -> bool:
    if not isinstance(price, dict):
        return False
    amount = price.get("amount")
    currency = price.get("currency")
    return (isinstance(amount, (int, float)) and not isinstance(amount, bool) and math.isfinite(amount)
            and amount > 0 and isinstance(currency, str) and bool(currency.strip()))


async def _promotion_gates(row: Dict[str, Any], plan: ProbePlan, verdict: RobotsVerdict, robots_body: str,
                           fetch: Any, validate: Any, polite: Politeness) -> Dict[str, Any]:
    """The candidate gates after a robots allow, in order (R-S15-18): ToS (no fetch
    before it passes), one PDP (``validate_scrape_url``, robots allow on every hop,
    2xx, not walled, not an empty shell, and a price WITH a currency from
    ``extract_price_from_html``), then a known platform."""
    gates: Dict[str, Any] = {"tos": False, "pdp": False, "platform": None, "platform_probed": None,
                             "pdp_challenge": None}
    tos = row.get("tos") if isinstance(row.get("tos"), dict) else {}
    if tos.get("verdict") != "allowed":
        return gates
    gates["tos"] = True
    sample = plan.sample_url
    from app.services import price_service as _ps

    if not sample or not _ps.validate_scrape_url(sample):
        return gates
    page = await _fetch_following(sample, fetch, validate, polite, verdict.crawl_delay,
                                  PDP_TIMEOUT_SECONDS, may_fetch=_pdp_may_fetch(plan.origin, robots_body))
    if page.status is None or not 200 <= page.status < 300:
        return gates
    outcome = _ps.classify_capture(page.body, None, page.status)
    if outcome == _ps.CAPTURE_WALLED:
        gates["pdp_challenge"] = challenge_vendor(page.status, page.headers, page.body)
        return gates
    if outcome == _ps.CAPTURE_EMPTY_SHELL:
        return gates
    # The extractor builds BeautifulSoup trees: run it off the event loop (the W0-4c rule
    # for every async def in app/services).
    price = await asyncio.to_thread(_ps.extract_price_from_html, page.body, pdp_product_name(page.body),
                                    _row_currency(row), _host_of(page.url), page.url)
    if not _price_ok(price):
        return gates
    gates["pdp"] = True
    from app.services import platform_router as _pr

    label = None
    try:
        label = getattr(_pr.detect_platform_verdict(page.body, page.url, robots_body), "commerce_platform", None)
    except Exception:  # noqa: BLE001 - an unknown platform, never a crash
        label = None
    probed = label if isinstance(label, str) and label and label != "unknown" else None
    known = row.get("platform") if isinstance(row.get("platform"), str) and row.get("platform") not in (
        "", "unknown") else None
    gates["platform_probed"] = probed
    gates["platform"] = known or probed
    return gates


async def probe_host(row: Dict[str, Any], fetch: Any, sleep: Any, now: datetime, validate: Any,
                     polite: Optional[Politeness] = None, *, run_gates: bool = True) -> Dict[str, Any]:
    """Read one row's robots record and, for a candidate whose robots allow, run
    the promotion gates (``run_gates=False``: the robots read only, as the seed's
    residential tool needs). Returns ``{"verdict", "gates", "plan", "refused"}``;
    never writes. A deny_hosts host is refused by name BEFORE any request
    (``refused`` = ``DENY_REFUSAL``, ``verdict`` None; F1-10)."""
    polite = polite or Politeness(sleep)
    plan = probe_plan(row)
    refusal = entry_refusal(row)
    if refusal:
        logger.info("[ROBOTS_REGISTRY] refused host=%s reason=%s", plan.host, refusal)
        return {"verdict": None, "gates": None, "plan": plan, "refused": refusal}
    fetched = await _fetch_following(plan.robots_url, fetch, validate, polite, _stored_crawl_delay(row),
                                     ROBOTS_TIMEOUT_SECONDS)
    verdict = decide_robots(fetched.status, fetched.headers, fetched.body, plan.probe_urls)
    if fetched.refused in ("initial", "hop"):
        verdict = verdict._replace(ssrf=fetched.refused)
    elif fetched.refused == "dns":
        verdict = verdict._replace(dns="unresolved")
    gates = None
    if (run_gates and row.get("status") == "candidate" and verdict.state == "allow"
            and not verdict.challenge_vendor and not _young_trusted(row.get("robots"), now)):
        robots_body = fetched.body if fetched.status is not None and 200 <= fetched.status < 300 else ""
        gates = await _promotion_gates(row, plan, verdict, robots_body, fetch, validate, polite)
    return {"verdict": verdict, "gates": gates, "plan": plan, "refused": None}


async def classify_host(row: Dict[str, Any], fetch: Any, sleep: Any, validate: Any,
                        polite: Optional[Politeness] = None) -> Optional[str]:
    """The robots-gated platform probe for one LIVE row (ruling R-S15-13): read the
    robots record of the probe origin; when it allows, fetch the row's same-site
    sample URL once (robots allow on every hop) and run
    ``platform_router.detect_platform`` over its bytes. A label, or None (a
    deny_hosts host is refused by name before any request, F1-10)."""
    polite = polite or Politeness(sleep)
    plan = probe_plan(row)
    refusal = entry_refusal(row)
    if refusal:
        logger.info("[ROBOTS_REGISTRY] refused host=%s reason=%s", plan.host, refusal)
        return None
    fetched = await _fetch_following(plan.robots_url, fetch, validate, polite, _stored_crawl_delay(row),
                                     ROBOTS_TIMEOUT_SECONDS)
    verdict = decide_robots(fetched.status, fetched.headers, fetched.body, plan.probe_urls)
    if verdict.state != "allow" or verdict.challenge_vendor or not plan.sample_url:
        return None
    robots_body = fetched.body if fetched.status is not None and 200 <= fetched.status < 300 else ""
    page = await _fetch_following(plan.sample_url, fetch, validate, polite, verdict.crawl_delay,
                                  PDP_TIMEOUT_SECONDS, may_fetch=_pdp_may_fetch(plan.origin, robots_body))
    if page.status is None or not 200 <= page.status < 300:
        return None
    from app.services import platform_router as _pr
    from app.services import price_service as _ps

    if _ps.classify_capture(page.body, None, page.status) == _ps.CAPTURE_WALLED:
        return None
    try:
        label = _pr.detect_platform(page.body, page.url)
    except Exception:  # noqa: BLE001
        return None
    return label if isinstance(label, str) and label and label != "unknown" else None


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------

def due_rows(rows: Sequence[Any], now: datetime, limit: int, slack_seconds: float = 0.0) -> List[Dict[str, Any]]:
    """The rows this run probes: touchable, not parked, due (``robots.next_reread``
    at or before ``now`` + ``slack_seconds``; ``run_cron`` passes
    ``ROBOTS_DUE_SLACK_SECONDS``, F1-3); never-read first (by host), then the
    oldest ``robots.next_reread``, then host; at most ``limit``."""
    horizon = now + timedelta(seconds=slack_seconds)
    keyed = []
    for row in rows:
        if not isinstance(row, dict) or not _cron_may_touch(row):
            continue
        challenge = row.get("challenge") if isinstance(row.get("challenge"), dict) else {}
        parked = _parse_iso(challenge.get("parked_until"))
        if parked is not None and parked > now:
            continue
        stored = row.get("robots") if isinstance(row.get("robots"), dict) else {}
        nxt = _parse_iso(stored.get("next_reread"))
        if nxt is not None and nxt > horizon:
            continue
        keyed.append(((0 if nxt is None else 1), nxt or _EPOCH, _row_host(row), row))
    keyed.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in keyed[: max(0, int(limit))]]


def _read_rows(client: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    start = 0
    for _page in range(MAX_PAGES):
        result = (
            client.table(KB_MERCHANTS_TABLE)
            .select(CRON_COLUMNS)
            .order("host")
            .range(start, start + PAGE_SIZE - 1)
            .execute()
        )
        data = getattr(result, "data", None)
        if not isinstance(data, list):
            raise TypeError("kb_merchants read did not return a list")
        rows.extend(r for r in data if isinstance(r, dict))
        if len(data) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE
    raise OverflowError("kb_merchants read exceeded the page bound")


def write_update(client: Any, row: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    """ONE conditional update (R-S15-11): matched on host AND the updated_at the
    run read, so a row the owner or another writer changed meanwhile is left
    alone. True when a row was written."""
    seen = row.get("updated_at")
    query = client.table(KB_MERCHANTS_TABLE).update(payload).eq("host", row.get("host"))
    query = query.eq("updated_at", seen) if seen is not None else query.is_("updated_at", "null")
    result = query.execute()
    data = getattr(result, "data", None)
    return isinstance(data, list) and len(data) > 0


async def run_cron(client: Any, fetch: Any, sleep: Any, now_clock: Any, validate: Any) -> Dict[str, int]:
    """One robots registry run (the entry script passes the production seams:
    the service-role client, ``default_fetch``, ``asyncio.sleep``, ``utc_now``,
    ``default_validate``). Sequential, polite, never raises; returns counts."""
    counts: Dict[str, int] = dict.fromkeys((
        "rows", "due", "probed", "allow", "disallow", "unreadable", "challenge", "promoted", "written", "lost",
        "failed"), 0)
    try:
        rows = _read_rows(client)
    except Exception as exc:  # noqa: BLE001 - a failed read ends the run quietly
        logger.warning("[ROBOTS_CRON] read failed reason=%s", type(exc).__name__)
        return counts
    counts["rows"] = len(rows)
    limit = max_hosts_per_run()
    slack = due_slack_seconds()  # read ONCE per run (F1-3)
    run_start = now_clock()  # ONCE: the due horizon and every record's next_reread (RB15-2)
    due = due_rows(rows, run_start, limit, slack)
    counts["due"] = len(due)
    logger.info("[ROBOTS_CRON] start rows=%d due=%d limit=%d", counts["rows"], counts["due"], limit)
    polite = Politeness(sleep)
    for row in due:
        host = _row_host(row)
        try:
            now = now_clock()
            result = await probe_host(row, fetch, sleep, now, validate, polite)
            verdict = result["verdict"]
            update = next_row_update(row, verdict, now, result["gates"], reread_from=run_start)
        except Exception as exc:  # noqa: BLE001 - one host never ends the run
            counts["failed"] += 1
            logger.warning("[ROBOTS_CRON] probe failed reason=%s", type(exc).__name__)
            continue
        if verdict is None:  # refused by name (the deny belt): never fetched, never written
            continue
        label = "challenge" if verdict.challenge_vendor else verdict.state
        counts["probed"] += 1
        counts[label] = counts.get(label, 0) + 1
        logger.info("[ROBOTS_CRON] host=%s state=%s", host, label)
        if not update:
            continue
        try:
            written = write_update(client, row, update)
        except Exception as exc:  # noqa: BLE001
            counts["failed"] += 1
            logger.warning("[ROBOTS_CRON] write failed reason=%s", type(exc).__name__)
            continue
        if not written:
            counts["lost"] += 1
            logger.warning("[ROBOTS_CRON] lost race host=%s; skipped until the next run", host)
            continue
        counts["written"] += 1
        if row.get("status") == "candidate" and update.get("status") == "live":
            counts["promoted"] += 1
    logger.info(
        "[ROBOTS_CRON] done rows=%d due=%d probed=%d allow=%d disallow=%d unreadable=%d challenge=%d "
        "promoted=%d written=%d lost=%d failed=%d",
        counts["rows"], counts["due"], counts["probed"], counts["allow"], counts["disallow"],
        counts["unreadable"], counts["challenge"], counts["promoted"], counts["written"], counts["lost"],
        counts["failed"],
    )
    return counts


# ---------------------------------------------------------------------------
# production seams
# ---------------------------------------------------------------------------

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def default_fetch(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = ROBOTS_TIMEOUT_SECONDS,
                        allow_redirects: bool = False) -> Tuple[int, Dict[str, str], str]:
    """One GET as the named agent (curl_cffi in a worker thread, NO browser
    impersonation, redirects never followed by the library). The body is capped
    at ``MAX_BODY_BYTES`` BEFORE it is decoded (F1-11; the client still receives
    the whole response). Raises on a network error (the caller maps it to
    unreadable)."""

    def _get() -> Tuple[int, Dict[str, str], str]:
        from curl_cffi import requests as cffi_requests

        resp = cffi_requests.get(url, headers=dict(headers or _REQUEST_HEADERS), timeout=timeout,
                                 allow_redirects=bool(allow_redirects))
        response_headers = {str(k): str(v) for k, v in (resp.headers or {}).items()}
        capped = (resp.content or b"")[:MAX_BODY_BYTES]
        return int(resp.status_code), response_headers, _decode_body(capped, getattr(resp, "encoding", None))

    return await asyncio.to_thread(_get)


def _decode_body(raw: bytes, encoding: Any) -> str:
    """The capped body bytes as text: the response charset, else utf-8; an
    undecodable byte is replaced and an unknown charset falls back to utf-8."""
    try:
        return raw.decode(encoding if isinstance(encoding, str) and encoding else "utf-8", errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


async def default_validate(url: str) -> str:
    """The SSRF check of every robots / PDP URL and redirect hop, answered as a
    REASON (F1-13): ``VALIDATE_OK`` for an http(s) URL whose host is not a local or
    internal name and resolves to no private, loopback, link-local or reserved
    address (``url_validator``); ``VALIDATE_SSRF`` for a refused scheme, name or
    address; ``VALIDATE_DNS`` when the refusal was the resolver's (NXDOMAIN, an
    error, a timeout), which the cron records as ``health.dns``, never as an SSRF
    label. Only a refused URL pays the one extra resolve that tells them apart."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
    except ValueError:
        return VALIDATE_SSRF
    if (parts.scheme not in ("http", "https") or not host or host == "localhost"
            or host.endswith((".localhost", ".local", ".internal"))):
        return VALIDATE_SSRF
    from app.utils.url_validator import validate_external_url_async

    try:
        if await validate_external_url_async(url):
            return VALIDATE_OK
    except Exception:  # noqa: BLE001 - a validator failure fails closed
        pass
    return await _refusal_reason(host)


def _all_public(infos: Any) -> bool:
    """True when every resolved address is public (none private, loopback,
    link-local, reserved or multicast); False for an empty or odd answer."""
    try:
        addresses = [ipaddress.ip_address(str(info[4][0]).split("%", 1)[0]) for info in infos]
    except Exception:  # noqa: BLE001 - an odd resolver answer reads as not public
        return False
    return bool(addresses) and not any(
        a.is_private or a.is_loopback or a.is_link_local or a.is_reserved or a.is_multicast for a in addresses)


async def _refusal_reason(host: str) -> str:
    """Why the validator refused ``host``: ``VALIDATE_DNS`` when it does not resolve
    within ``DNS_CLASSIFY_TIMEOUT_SECONDS``, or resolves only to public addresses
    (the refusal was the resolver's: a timeout or a transient error), else
    ``VALIDATE_SSRF``. No fetch follows either answer."""
    try:
        infos = await asyncio.wait_for(asyncio.to_thread(socket.getaddrinfo, host, None),
                                       DNS_CLASSIFY_TIMEOUT_SECONDS)
    except Exception:  # noqa: BLE001 - gaierror, a timeout or an OS error: the name did not resolve
        return VALIDATE_DNS
    return VALIDATE_DNS if _all_public(infos) else VALIDATE_SSRF


__all__ = [
    "QARENBOT_UA", "RobotsVerdict", "ProbePlan", "Politeness", "CRON_REASONS", "STICKY_REASONS", "BLOCKED_REASONS",
    "robots_registry_cron_enabled", "max_hosts_per_run", "challenge_park_days", "parse_crawl_delay",
    "challenge_vendor", "decide_robots", "robots_record", "probe_plan", "next_row_update", "probe_host",
    "classify_host", "due_rows", "write_update", "run_cron", "pdp_product_name", "utc_now", "default_fetch", "default_validate",
    "MAX_BODY_BYTES", "VALIDATE_OK", "VALIDATE_SSRF", "VALIDATE_DNS", "DENY_REFUSAL", "due_slack_seconds",
    "entry_refusal",
]
