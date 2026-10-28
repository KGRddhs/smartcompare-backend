"""S81-15 REGISTRY-ROBOTS-DENY: the merchant registry read from ``kb_merchants``.

Behind ``ENABLE_MERCHANT_REGISTRY_DB`` (default OFF, read PER CALL as the first
statement of every gated function) the registry the router consumes comes from
the ``kb_merchants`` table (migration 045, S81-14) instead of the in-code
``source_router.SOURCE_REGISTRY``.

TWO SETS (ruling R-S15-1). ``registry_rows`` is the SELECTION set: the entries of
rows with status ``live``, ``deny`` false and a host that
``deny_hosts.is_denied_host`` does not match (a flag-free belt, so a mis-seeded
banned host never routes). Only ``source_router._routable_registry`` reads it:
the category selectors, the fan-out selectors and ``score_source`` /
``source_usage`` / ``is_render_only_domain`` (a cron-blocked host scores as
off-registry, which is the point of blocking it). ``registry_lookup_rows`` is the
LOOKUP set: every loaded row, live AND blocked, banned hosts included (their
``Source.status`` reads "blocked" and ``Source.deny`` is set). The tier,
currency and host-evidence consumers read it (``_registry_row_for_host`` and so
``registry_tier`` / ``match_registry_apex`` / ``descriptor_for_host``, plus the
three direct readers in price_service, cache_service and
magento_graphql_service), so a host that leaves selection keeps its tier and
every global-tier refusal it had.

THE MEMO (ruling R-S15-7). Per process, window ``MERCHANT_REGISTRY_MEMO_SECONDS``
(default 600, clamped 300..900). A stale or empty memo schedules ONE refresh task
on the caller's running loop (single flight per loop; a call from a thread with no
running loop schedules nothing) and the caller is served what the memo holds, or
the fallback, at once: it never awaits the read. The refresh is ONE paged read
(``status in (live, blocked)``, ordered by host, 500-row pages until a short page;
candidates never reach the request path) dispatched with ``asyncio.to_thread``
under ``asyncio.wait_for(MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS)`` (default 5,
clamped 1..30). The snapshot is a sha256 over the decode columns (host, status,
deny, blocked_reason, registry, partner) of every fetched row plus the
``ENABLE_BH_GCC_CATALOG_SOURCES`` state, never ``max(updated_at)``: an equal
snapshot keeps the SAME list objects, so the D03 ``_ROUTABLE_MEMO`` identity holds.

FAILURES never raise. With no good load the fallback (the code registry) is
served; after a good load a failed refresh keeps the last good lists for up to
``MERCHANT_REGISTRY_MAX_STALE_SECONDS`` (default 3600, clamped 900..21600), then
the fallback. ONE WARNING per window carries the reason (an exception TYPE name
or a constant), never a host, a URL or an exception message.

FLAG OFF: both accessors return the fallback they were handed (SOURCE_REGISTRY by
identity), ``partner_for_host`` returns None; no read, no task, no log line.

The off-clock seed builders (``source_to_entry``, ``build_seed_rows``,
``plan_seed``) live here so the seed script and the tests share one definition.
``kb_service`` (it imports price_service) and ``source_router`` are imported
lazily inside the functions that need them, so importing this module loads
neither.
"""
from __future__ import annotations

import asyncio
import copy
import dataclasses
import hashlib
import json
import logging
import math
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.services import deny_hosts

logger = logging.getLogger(__name__)

KB_MERCHANTS_TABLE = "kb_merchants"
#: The decode columns: the only columns the request path reads (R-S15-11).
READ_COLUMNS = "host,status,deny,blocked_reason,registry,partner"
#: The server-side status filter (R-S15-10): candidates never reach the request path.
READ_STATUSES: Tuple[str, ...] = ("live", "blocked")
#: Page size of the paged read; a page shorter than this ends the read.
PAGE_SIZE = 500
#: A read longer than this many pages is refused as truncated (a server that ignores the range).
MAX_PAGES = 200

#: The Source fields an entry carries verbatim, except ``deny``: deny is a ROW column
#: (the owner's blocked list) applied by the decode, never an entry key.
_ROW_ONLY_FIELDS = ("deny",)

#: Seed column ownership (R-S15-11). On an EXISTING row the seed writes only these,
#: plus platform / platform_confidence where the stored platform is NULL and the
#: deny triple for a banned host; it never writes deny False, status,
#: blocked_reason, robots, challenge, tos, partner, health or politeness.
SEED_OWNED_COLUMNS: Tuple[str, ...] = (
    "country", "currency_hint", "adapter", "search_template", "registry", "updated_at",
)
#: A registry mechanism with a commerce platform the router already knows.
PLATFORM_FOR_MECHANISM: Dict[str, str] = {
    "shopify": "shopify",
    "woo_store_json": "woocommerce",
    "salla_api": "salla",
    "magento_graphql": "magento",
    "occ_rest": "sap_hybris",
}
#: Order base of catalog entries: ``1000 + json index`` (literals keep 0..43).
CATALOG_ORDER_BASE = 1000
#: The three hosts the 2026-08-31 robots ruling read from a residential connection
#: (docs/policies/2026-08-31-robots-unreadable-ruling.md, Table 2: robots 200 and
#: permissive there, walled from the datacenter): seeded with that recorded allow
#: and source "residential" (ruling R-S15-4). The read is dated the ruling's day.
RESIDENTIAL_READ_HOSTS: Tuple[str, ...] = ("klinq.com", "nazih.qa", "numberc.com")
RESIDENTIAL_READ_AT = "2026-08-31T00:00:00Z"

_TRUTHY = ("true", "1", "yes", "on")


# ---------------------------------------------------------------------------
# flag and knobs (read per call)
# ---------------------------------------------------------------------------

def merchant_registry_db_enabled() -> bool:
    """True iff ``ENABLE_MERCHANT_REGISTRY_DB`` is set truthy. Read PER CALL."""
    return os.getenv("ENABLE_MERCHANT_REGISTRY_DB", "false").strip().lower() in _TRUTHY


def _float_knob(name: str, default: float, low: float, high: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value) or value <= 0:
        return default
    return min(max(value, low), high)


def memo_seconds() -> float:
    """``MERCHANT_REGISTRY_MEMO_SECONDS``: default 600, clamped 300..900."""
    return _float_knob("MERCHANT_REGISTRY_MEMO_SECONDS", 600.0, 300.0, 900.0)


def read_timeout_seconds() -> float:
    """``MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS``: default 5, clamped 1..30."""
    return _float_knob("MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", 5.0, 1.0, 30.0)


def max_stale_seconds() -> float:
    """``MERCHANT_REGISTRY_MAX_STALE_SECONDS``: default 3600, clamped 900..21600."""
    return _float_knob("MERCHANT_REGISTRY_MAX_STALE_SECONDS", 3600.0, 900.0, 21600.0)


# ---------------------------------------------------------------------------
# test seams (production values; tests patch the module attributes)
# ---------------------------------------------------------------------------

_monotonic = time.monotonic


def _admin_client() -> Any:
    from app.services.database_service import get_admin_supabase_client

    return get_admin_supabase_client()


# ---------------------------------------------------------------------------
# the memo
# ---------------------------------------------------------------------------

_LOCK = threading.Lock()


def _empty_state() -> Dict[str, Any]:
    return {
        "selection": None,   # the last good SELECTION list (None: no good load yet)
        "lookup": None,      # the last good LOOKUP list
        "partners": {},      # host -> partner dict of the last good load
        "snapshot": None,    # the sha256 of the last good load
        "loaded_at": None,   # monotonic time of the last refresh (good or failed)
        "good_at": None,     # monotonic time of the last good refresh
        "failed": False,     # True while the newest refresh failed
        "warned_at": None,   # monotonic time of the last WARNING
    }


_STATE: Dict[str, Any] = _empty_state()
#: The in-flight refresh: (loop, task), held strongly so the task is never collected.
_REFRESH: Optional[Tuple[Any, Any]] = None


def _reset_for_tests() -> None:
    """Clear the memo, the refresh handle and the warning window."""
    global _STATE, _REFRESH
    with _LOCK:
        _STATE = _empty_state()
        _REFRESH = None


def _usable(state: Dict[str, Any], now: float) -> bool:
    """A good load exists and, if the newest refresh failed, it is not past max stale."""
    if state["selection"] is None or state["good_at"] is None:
        return False
    if not state["failed"]:
        return True
    return (now - state["good_at"]) <= max_stale_seconds()


def _schedule_refresh() -> None:
    """Create ONE refresh task on the running loop of this thread; never awaits."""
    global _REFRESH
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # a sync caller or a worker thread: schedule nothing
    with _LOCK:
        current = _REFRESH
        if current is not None and current[0] is loop and not current[1].done():
            return
        coro = refresh_merchant_registry()
        try:
            task = loop.create_task(coro)
        except Exception:  # noqa: BLE001 - a closing loop: serve what we have
            coro.close()
            return
        _REFRESH = (loop, task)


def _serve(fallback: List[Any], which: str) -> List[Any]:
    try:
        now = _monotonic()
        with _LOCK:
            state = _STATE
            usable = _usable(state, now)
            current = state[which] if usable else None
            loaded_at = state["loaded_at"]
        fresh = loaded_at is not None and (now - loaded_at) < memo_seconds()
        if not fresh:
            _schedule_refresh()
        return current if current is not None else fallback
    except Exception:  # noqa: BLE001 - the accessor must never break a consumer
        return fallback


def registry_rows(fallback: List[Any]) -> List[Any]:
    """The SELECTION set (R-S15-1). Flag OFF: ``fallback`` itself, nothing read."""
    if not merchant_registry_db_enabled():
        return fallback
    return _serve(fallback, "selection")


def registry_lookup_rows(fallback: List[Any]) -> List[Any]:
    """The LOOKUP set (R-S15-1): live and blocked rows. Flag OFF: ``fallback`` itself."""
    if not merchant_registry_db_enabled():
        return fallback
    return _serve(fallback, "lookup")


def partner_for_host(host: Any) -> Optional[Dict[str, Any]]:
    """The stored partner / CTA dict of ``host`` from the last good load, else None.

    Flag OFF: None with no read. Stored data only: no caller in this unit and never
    read by scoring (a later CTA / "Sponsored" unit renders it)."""
    if not merchant_registry_db_enabled():
        return None
    try:
        h = deny_hosts.normalize_host(host)
        now = _monotonic()
        with _LOCK:
            state = _STATE
            partners = state["partners"] if _usable(state, now) else {}
            value = partners.get(h)
        if isinstance(value, dict) and value:
            return copy.deepcopy(value)
        return None
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# the refresh
# ---------------------------------------------------------------------------

class _RefreshFailure(Exception):
    """A refresh failure with a constant reason (logged as the reason)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _read_all_rows(client: Any) -> List[Dict[str, Any]]:
    """The paged read (runs in a worker thread). Raises on any failure."""
    rows: List[Dict[str, Any]] = []
    start = 0
    for _page in range(MAX_PAGES):
        result = (
            client.table(KB_MERCHANTS_TABLE)
            .select(READ_COLUMNS)
            .in_("status", list(READ_STATUSES))
            .order("host")
            .range(start, start + PAGE_SIZE - 1)
            .execute()
        )
        data = getattr(result, "data", None)
        if not isinstance(data, list):
            raise _RefreshFailure("not_a_list")
        rows.extend(data)
        if len(data) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE
    raise _RefreshFailure("truncated")


def _snapshot(rows: Sequence[Any], catalog_on: bool) -> str:
    """sha256 over the decode columns of every row (order-independent) + the catalog flag."""
    items = []
    for row in rows:
        if isinstance(row, dict):
            proj = {k: row.get(k) for k in ("host", "status", "deny", "blocked_reason", "registry", "partner")}
        else:
            proj = {"_row": row}
        items.append(json.dumps(proj, sort_keys=True, default=repr))
    items.sort()
    digest = hashlib.sha256()
    digest.update(("catalog=%d\n" % (1 if catalog_on else 0)).encode("utf-8"))
    for item in items:
        digest.update(item.encode("utf-8", "replace"))
        digest.update(b"\n")
    return digest.hexdigest()


def _decode(rows: Sequence[Any], catalog_on: bool) -> Dict[str, Any]:
    """Rows -> the SELECTION list, the LOOKUP list, the partners and the counts.

    Entries are sorted by (order, host, position); catalog-origin entries count only
    while the catalog flag is ON; the dedup is ``source_router._load_catalog_rows``'
    rule verbatim: a catalog entry whose domain equals or is a subdomain of ANY
    literal-origin domain (whatever that row's status), or repeats an earlier catalog
    domain, is dropped. Operator / discovery entries route in both catalog states."""
    from app.services import source_router as _sr

    counts = {"hosts": 0, "blocked": 0, "candidate": 0, "skipped": 0}
    collected: List[Tuple[int, str, int, str, Any, str, bool]] = []
    partners: Dict[str, Dict[str, Any]] = {}
    seen_hosts: set = set()
    for row in rows:
        if not isinstance(row, dict):
            counts["skipped"] += 1
            continue
        raw_host = row.get("host")
        raw_host = raw_host.strip().lower() if isinstance(raw_host, str) else ""
        host = deny_hosts.normalize_host(raw_host)
        if not host or host in seen_hosts:
            if not host:
                counts["skipped"] += 1
            continue
        status = row.get("status")
        if status == "candidate":
            counts["candidate"] += 1
            continue
        if status not in READ_STATUSES:
            counts["skipped"] += 1
            continue
        registry = row.get("registry")
        if not isinstance(registry, list):
            counts["skipped"] += 1
            continue
        seen_hosts.add(host)
        counts["hosts"] += 1
        if status == "blocked":
            counts["blocked"] += 1
        denied = (row.get("deny") is True) or deny_hosts.is_denied_host(host)
        partner = row.get("partner")
        if isinstance(partner, dict) and partner:
            partners[host] = copy.deepcopy(partner)
        for position, entry in enumerate(registry):
            src = _sr._source_from_entry(raw_host, entry)
            order = entry.get("order") if isinstance(entry, dict) else None
            origin = entry.get("origin") if isinstance(entry, dict) else None
            if (
                src is None
                or not isinstance(order, int)
                or isinstance(order, bool)
                or order < 0
                or not isinstance(origin, str)
            ):
                counts["skipped"] += 1
                continue
            if origin == "catalog" and not catalog_on:
                continue
            collected.append((order, host, position, origin, src, status, denied))
    collected.sort(key=lambda item: (item[0], item[1], item[2]))
    literal_domains = {
        item[4].domain.replace("www.", "").lower() for item in collected if item[3] == "literal"
    }
    selection: List[Any] = []
    lookup: List[Any] = []
    seen_catalog: set = set()
    for _order, _host, _pos, origin, src, status, denied in collected:
        if origin == "catalog":
            d = src.domain.replace("www.", "").lower()
            if d in seen_catalog:
                continue
            if any(d == ld or d.endswith("." + ld) for ld in literal_domains):
                continue
            seen_catalog.add(d)
        if status == "live" and not denied:
            selection.append(src)
            lookup.append(src)
        else:
            lookup.append(dataclasses.replace(src, status="blocked" if status == "blocked" else src.status,
                                              deny=bool(denied)))
    return {"selection": selection, "lookup": lookup, "partners": partners, "counts": counts}


def _record_failure(reason: str) -> None:
    now = _monotonic()
    window = memo_seconds()
    with _LOCK:
        state = _STATE
        state["failed"] = True
        state["loaded_at"] = now
        warned_at = state["warned_at"]
        warn = warned_at is None or (now - warned_at) >= window
        if warn:
            state["warned_at"] = now
    if warn:
        logger.warning("[MERCHANT_REGISTRY] refresh failed reason=%s", reason)


def _read_and_prepare(client_factory: Any) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Worker-thread body: read, snapshot, decode only when the snapshot changed."""
    from app.services import source_router as _sr

    client = client_factory()
    rows = _read_all_rows(client)
    catalog_on = _sr._catalog_sources_enabled()
    snap = _snapshot(rows, catalog_on)
    with _LOCK:
        same = _STATE["snapshot"] == snap and _STATE["selection"] is not None
    if same:
        return snap, None
    return snap, _decode(rows, catalog_on)


async def refresh_merchant_registry() -> None:
    """ONE paged read of ``kb_merchants`` into the memo. Never raises (cancellation aside)."""
    try:
        try:
            snap, decoded = await asyncio.wait_for(
                asyncio.to_thread(_read_and_prepare, _admin_client), read_timeout_seconds()
            )
        except asyncio.TimeoutError:
            _record_failure("timeout")
            return
        except _RefreshFailure as failure:
            _record_failure(failure.reason)
            return
        except Exception as exc:  # noqa: BLE001 - a failed read is a failed refresh
            _record_failure(type(exc).__name__)
            return
        now = _monotonic()
        if decoded is None:
            # The snapshot equals the memo's: keep the SAME list objects. If a
            # concurrent refresh replaced the memo meanwhile, the newer one stands.
            with _LOCK:
                if _STATE["snapshot"] == snap and _STATE["selection"] is not None:
                    _STATE["loaded_at"] = now
                    _STATE["good_at"] = now
                    _STATE["failed"] = False
            return
        if not decoded["selection"]:
            _record_failure("empty")
            return
        counts = decoded["counts"]
        with _LOCK:
            _STATE["selection"] = decoded["selection"]
            _STATE["lookup"] = decoded["lookup"]
            _STATE["partners"] = decoded["partners"]
            _STATE["snapshot"] = snap
            _STATE["loaded_at"] = now
            _STATE["good_at"] = now
            _STATE["failed"] = False
        logger.info(
            "[MERCHANT_REGISTRY] refreshed hosts=%d routed=%d blocked=%d candidate=%d skipped=%d",
            int(counts["hosts"]), len(decoded["selection"]), int(counts["blocked"]),
            int(counts["candidate"]), int(counts["skipped"]),
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - a refresh never raises
        _record_failure(type(exc).__name__)


# ---------------------------------------------------------------------------
# the seed builders (pure; used by the off-clock seed script)
# ---------------------------------------------------------------------------

def source_to_entry(source: Any, order: int, origin: str) -> Dict[str, Any]:
    """One registry entry: ``order``, ``origin`` and every ``Source`` field verbatim
    except ``deny`` (a row column); tuples become lists, the search descriptor its
    ``to_row()`` dict (key ``search_descriptor``, the field name, which the S81-14
    entry validator accepts)."""
    entry: Dict[str, Any] = {"order": int(order), "origin": str(origin)}
    for f in dataclasses.fields(source):
        if f.name in _ROW_ONLY_FIELDS:
            continue
        value = getattr(source, f.name)
        if f.name == "search_descriptor":
            value = value.to_row() if value is not None else None
        elif isinstance(value, tuple):
            value = list(value)
        entry[f.name] = value
    return entry


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _residential_record(host: str) -> Dict[str, Any]:
    """The 2026-08-31 residential read of ``host`` (ruling R-S15-4), in the D14 record
    shape with the rules not recorded (the ruling kept the verdict, not the body)."""
    return {
        "state": "allow",
        "status": 200,
        "body_sha": None,
        "fetched_at": RESIDENTIAL_READ_AT,
        "next_reread": RESIDENTIAL_READ_AT,
        "crawl_delay": None,
        "origin": "https://" + host,
        "source": "residential",
        "rules": {"qarenbot": [], "star": []},
        "probed": {"/": "allow"},
    }


def _platform_for(entries: Sequence[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
    for entry in entries:
        mech = entry.get("mechanism") or ""
        if mech in PLATFORM_FOR_MECHANISM:
            return PLATFORM_FOR_MECHANISM[mech], "mechanism"
    return None, None


def build_seed_rows(literal_rows: Sequence[Any], catalog_json_rows: Sequence[Any], now: datetime) -> List[Dict[str, Any]]:
    """The 410 kb_merchants rows of the off-clock seed (spec 2.7 as amended).

    Literal Sources keep orders 0..43 (noon.com carries two entries, 23 and 24); json
    rows get ``1000 + index``; a json host equal to a literal host is not seeded (the
    literal wins). Every row goes through ``kb_service.build_merchant_row`` (GATE
    GC-2, never a copy) and gains ``created_at = updated_at`` (the INSERT value; the
    builder emits no created_at). A banned host is stored deny true, status blocked,
    blocked_reason "deny" (the owner's blocked list). Json status live -> live, any
    other json status -> candidate (the cron's gates decide). Raises ValueError when
    the builder refuses a row (a seed must never silently drop a merchant)."""
    from app.services import kb_service as _kb
    from app.services import source_router as _sr

    specs: Dict[str, Dict[str, Any]] = {}
    order_of_hosts: List[str] = []
    literal_hosts: set = set()
    for index, src in enumerate(literal_rows):
        host = deny_hosts.normalize_host(src.domain)
        spec = specs.get(host)
        if spec is None:
            spec = {"host": host, "registry": [], "country": None,
                    "currency_hint": (src.currency or None), "adapter": None,
                    "search_template": None, "status": "live"}
            specs[host] = spec
            order_of_hosts.append(host)
            literal_hosts.add(host)
        spec["registry"].append(source_to_entry(src, index, "literal"))
    for index, row in enumerate(catalog_json_rows):
        if not isinstance(row, dict):
            continue
        host = deny_hosts.normalize_host(row.get("domain"))
        if not host or host in literal_hosts or host in specs:
            continue
        src = _sr._row_to_source(dict(row, status="live"))
        if src is None:
            raise ValueError("catalog row %d does not build a Source" % index)
        src = dataclasses.replace(src, status=str(row.get("status") or ""))
        search = row.get("search") if isinstance(row.get("search"), dict) else {}
        specs[host] = {
            "host": host,
            "registry": [source_to_entry(src, CATALOG_ORDER_BASE + index, "catalog")],
            "country": row.get("country") or None,
            "currency_hint": row.get("currency") or None,
            "adapter": row.get("genuine_method") or None,
            "search_template": search.get("url_template") or None,
            "status": "live" if row.get("status") == "live" else "candidate",
        }
        order_of_hosts.append(host)
    out: List[Dict[str, Any]] = []
    for host in order_of_hosts:
        spec = specs[host]
        platform, confidence = _platform_for(spec["registry"])
        denied = deny_hosts.is_denied_host(host)
        robots = _residential_record(host) if host in RESIDENTIAL_READ_HOSTS else None
        built = _kb.build_merchant_row(
            host=host, updated_at=now, country=spec["country"], currency_hint=spec["currency_hint"],
            platform=platform, platform_confidence=confidence, adapter=spec["adapter"],
            search_template=spec["search_template"], registry=spec["registry"], robots=robots,
            deny=denied, status="blocked" if denied else spec["status"],
            blocked_reason="deny" if denied else None,
        )
        if built is None:
            raise ValueError("kb_service.build_merchant_row refused a seed row")
        built["created_at"] = built["updated_at"]
        out.append(built)
    return out


def plan_seed(seed_rows: Sequence[Dict[str, Any]], existing: Any) -> Tuple[List[Dict[str, Any]], List[Tuple[str, Dict[str, Any]]]]:
    """(inserts, updates) for one seed run against ``existing`` (host -> stored row).

    Inserts are the full seed rows of new hosts. An update of an existing host
    carries only ``SEED_OWNED_COLUMNS``, plus ``platform`` / ``platform_confidence``
    when the stored platform is NULL, plus deny true / status blocked /
    blocked_reason deny for a banned host not already stored that way. The seed
    never writes deny False and never touches a cron- or owner-managed column."""
    known = existing if isinstance(existing, dict) else {}
    inserts: List[Dict[str, Any]] = []
    updates: List[Tuple[str, Dict[str, Any]]] = []
    for row in seed_rows:
        host = row["host"]
        stored = known.get(host)
        if stored is None:
            inserts.append(copy.deepcopy(row))
            continue
        stored = stored if isinstance(stored, dict) else {}
        payload = {col: copy.deepcopy(row[col]) for col in SEED_OWNED_COLUMNS}
        if stored.get("platform") is None and row.get("platform") is not None:
            payload["platform"] = row["platform"]
            payload["platform_confidence"] = row.get("platform_confidence")
        if row.get("deny") is True and not (
            stored.get("deny") is True and stored.get("status") == "blocked"
            and stored.get("blocked_reason") == "deny"
        ):
            payload["deny"] = True
            payload["status"] = "blocked"
            payload["blocked_reason"] = "deny"
        updates.append((host, payload))
    return inserts, updates


def seed_counts(rows: Sequence[Dict[str, Any]], literal_rows: Sequence[Any], catalog_json_rows: Sequence[Any]) -> Dict[str, int]:
    """The dry-run count line of the seed: rows, statuses, collisions, entries."""
    literal_hosts = {deny_hosts.normalize_host(s.domain) for s in literal_rows}
    collisions = sum(
        1 for r in catalog_json_rows
        if isinstance(r, dict) and deny_hosts.normalize_host(r.get("domain")) in literal_hosts
    )
    by_status: Dict[str, int] = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    return {
        "rows": len(rows),
        "live": by_status.get("live", 0),
        "candidate": by_status.get("candidate", 0),
        "blocked": by_status.get("blocked", 0),
        "collisions": collisions,
        "entries": sum(len(r["registry"]) for r in rows),
    }


def iso_utc(dt: datetime) -> str:
    """``YYYY-MM-DDTHH:MM:SSZ`` for an aware datetime (naive is read as UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return _iso_z(dt)


__all__ = [
    "KB_MERCHANTS_TABLE", "READ_COLUMNS", "SEED_OWNED_COLUMNS", "PLATFORM_FOR_MECHANISM",
    "merchant_registry_db_enabled", "memo_seconds", "read_timeout_seconds", "max_stale_seconds",
    "registry_rows", "registry_lookup_rows", "partner_for_host", "refresh_merchant_registry",
    "source_to_entry", "build_seed_rows", "plan_seed", "seed_counts", "iso_utc",
]
