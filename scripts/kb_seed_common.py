"""S81-G2 shared helpers for the three off-clock KB jobs (S81-16, D09, D11).

Only the standard library is imported at module top: every app import is lazy,
inside the function that needs it, so an entry script whose flag is OFF loads
nothing of the app (no client, no SDK, no settings, no dotenv). What lives here:

- the mode idiom shared by the three flags (``run_mode`` / ``cli_mode``);
- the defensive integer / float knob parsers (the robots_registry shape);
- the paged ``kb_merchants`` read and the per-host row lookup;
- ``url_gate``: the fail-closed per-URL rule over the PERSISTED robots record
  (deny list, live status, optional ToS, the record's own origin, then
  ``jsonld_widen.rating_host_allowed``);
- ``PoliteFetcher``: the robots registry's politeness, named headers, no blind
  redirect following, the SSRF validator on every hop and the 3,000,000 cap;
- ``KbWriter``: service-role writes of S81-14 builder outputs only
  (insert-ignore; the offer re-observation update of KB_OFFER_UPSERT_SET; the
  kb_gaps last_seen-only re-discovery update).

The five KB table names below are the only kb_* relation literals of G2 and
``kb_leaf`` is the only importer of the S81-14 leaf (tests/test_s81_kb_schema.py
E1 / E2 key both by exact line).
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence
from urllib.parse import urlsplit

logger = logging.getLogger("kb_seed_common")

MODE_OFF = "off"
MODE_DRY = "dry"
MODE_APPLY = "apply"
_TRUTHY = ("true", "1", "yes", "on")

READ_COLUMNS = "host,status,deny,blocked_reason,registry,robots,challenge,tos,currency_hint,country,platform,updated_at"
PAGE_SIZE = 500
MAX_PAGES = 200
WRITE_BATCH = 100
MAX_BODY_CHARS = 3_000_000

KB_PRODUCTS_TABLE = "kb_products"
KB_VARIANTS_TABLE = "kb_variants"
KB_OFFERS_TABLE = "kb_offers"
KB_SPECS_TABLE = "kb_specs"
KB_GAPS_TABLE = "kb_gaps"
LLM_SPEND_LEDGER_TABLE = "llm_spend_ledger"

#: Every reason ``url_gate`` can return (in the order the gate checks them).
GATE_REASONS = ("bad_url", "denied", "no_row", "not_live", "tos", "no_record", "origin", "robots")

_ISO3 = re.compile(r"^[A-Z]{3}$")


# ---------------------------------------------------------------------------
# mode and knobs (read per call, never memoised)
# ---------------------------------------------------------------------------

def run_mode(flag_name: str) -> str:
    """off | dry | apply for ``flag_name``; the FIRST statement reads the variable.

    The exact word ``apply`` (strip + lower) writes; the house truthy set is the
    DRY RUN; everything else (unset, blank, garbage, false, 0, no, off, dry) is
    OFF, so a stray truthy value can never write.
    """
    raw = os.getenv(flag_name, "false").strip().lower()
    if raw == MODE_APPLY:
        return MODE_APPLY
    if raw in _TRUTHY:
        return MODE_DRY
    return MODE_OFF


def cli_mode(mode: str, dry_run: bool) -> str:
    """A CLI ``--dry-run`` downgrades apply to dry; it never upgrades off."""
    return MODE_DRY if (mode == MODE_APPLY and dry_run) else mode


def house_flag(flag_name: str) -> bool:
    """The house boolean idiom (a sub-flag such as ENABLE_CC_CDX)."""
    return os.getenv(flag_name, "false").strip().lower() in _TRUTHY


def _knob_value(name: str) -> Optional[float]:
    """A finite, non-negative number, else None (unset / blank / garbage / inf /
    nan / negative)."""
    raw = os.getenv(name)
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def int_knob(name: str, default: int, low: int, high: int) -> int:
    """The robots_registry ``_int_knob`` shape: unusable -> ``default``; 0 ->
    ``default`` unless the clamp admits 0 (``low == 0``); else clamped to
    ``low..high``."""
    value = _knob_value(name)
    if value is None or (value == 0 and low > 0):
        return default
    return min(max(int(value), low), high)


def float_knob(name: str, default: float, low: float, high: float) -> float:
    """Unusable or <= 0 -> ``default``; else clamped to ``low..high``."""
    value = _knob_value(name)
    if value is None or value <= 0:
        return default
    return min(max(float(value), low), high)


# ---------------------------------------------------------------------------
# seams (module attributes the entries read at call time)
# ---------------------------------------------------------------------------

def _admin_client() -> Any:
    from app.services import database_service

    return database_service.get_admin_supabase_client()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def kb_leaf() -> Any:
    from app.services import kb_service as _kb
    return _kb


def bump(counts: Dict[str, int], key: str, by: int = 1) -> None:
    counts[key] = counts.get(key, 0) + by


def log_counts(prefix: str, counts: Dict[str, Any]) -> None:
    """One INFO line of sorted ``name=<int>`` pairs (ints only, never a value)."""
    parts = " ".join("%s=%d" % (k, int(v)) for k, v in sorted(counts.items()))
    logger.info("%s totals %s", prefix, parts)


def write_report(path: Optional[str], report: Any) -> None:
    """The --report file: ASCII JSON, LF, sorted keys (no-op without a path)."""
    if not path:
        return
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=True, indent=1, sort_keys=True)


def resolve_client(client: Any, prefix: str) -> Any:
    """The injected client, else the service-role client; None (logged at
    WARNING with the exception type only) when none can be built."""
    try:
        client = client if client is not None else _admin_client()
        if client is None:
            raise RuntimeError("no client")
        return client
    except Exception as exc:  # noqa: BLE001 - a missing client ends the run quietly
        logger.warning("%s no service-role client (%s)", prefix, type(exc).__name__)
        return None


# ---------------------------------------------------------------------------
# kb_merchants
# ---------------------------------------------------------------------------

def read_merchant_rows(client: Any) -> List[Dict[str, Any]]:
    """Every kb_merchants row: pages of PAGE_SIZE ordered by host until a short
    page (at most MAX_PAGES pages). A page that is not a list raises TypeError."""
    from app.services import merchant_registry as _mr

    rows: List[Dict[str, Any]] = []
    for page in range(MAX_PAGES):
        start = page * PAGE_SIZE
        resp = (client.table(_mr.KB_MERCHANTS_TABLE).select(READ_COLUMNS).order("host")
                .range(start, start + PAGE_SIZE - 1).execute())
        data = getattr(resp, "data", None)
        if not isinstance(data, list):
            raise TypeError("kb_merchants page is not a list")
        rows.extend(r for r in data if isinstance(r, dict))
        if len(data) < PAGE_SIZE:
            break
    return rows


def rows_by_host(rows: Iterable[Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows or []:
        if isinstance(row, dict) and isinstance(row.get("host"), str):
            out[row["host"].strip().lower()] = row
    return out


def merchant_for_host(by_host: Dict[str, Dict[str, Any]], host: Any) -> Optional[Dict[str, Any]]:
    """The exact host's row, else the row of the longest registry host that
    ``host`` is a subdomain of; None when nothing matches."""
    if not isinstance(host, str) or not host:
        return None
    h = host.strip().lower().rstrip(".")
    if h in by_host:
        return by_host[h]
    best_key: Optional[str] = None
    for key in by_host:
        if h.endswith("." + key) and (best_key is None or len(key) > len(best_key)):
            best_key = key
    return by_host[best_key] if best_key is not None else None


def registry_entries(row: Any) -> List[Dict[str, Any]]:
    """The row's registry entries sorted by ``order`` (entries without an int
    order last)."""
    reg = row.get("registry") if isinstance(row, dict) else None
    if not isinstance(reg, list):
        return []
    return sorted((e for e in reg if isinstance(e, dict)),
                  key=lambda e: e.get("order") if isinstance(e.get("order"), int) else 10 ** 9)


def row_currency(row: Any) -> Optional[str]:
    """``currency_hint`` (ISO-3), else the FIRST registry entry's ISO-3 currency,
    else None: never a default."""
    if not isinstance(row, dict):
        return None
    hint = row.get("currency_hint")
    if isinstance(hint, str) and _ISO3.match(hint.strip()):
        return hint.strip()
    entries = registry_entries(row)
    if entries:
        cur = entries[0].get("currency")
        if isinstance(cur, str) and _ISO3.match(cur.strip()):
            return cur.strip()
    return None


def url_gate(row: Any, url: Any, now: Any, *, require_tos: bool = False) -> Optional[str]:
    """None when ``url`` may be fetched under ``row``'s persisted robots record,
    else one of GATE_REASONS. Fail-closed: it never raises (an error is
    ``bad_url``)."""
    try:
        if not isinstance(url, str):
            return "bad_url"
        parts = urlsplit(url.strip())
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return "bad_url"
        from app.services import deny_hosts as _dh
        from app.services import jsonld_widen as _jw
        from app.services import robots_registry as _rr

        if _dh.is_denied_url(url):
            return "denied"
        if not isinstance(row, dict):
            return "no_row"
        if row.get("deny"):
            return "denied"
        if row.get("status") != "live":
            return "not_live"
        if require_tos:
            tos = row.get("tos")
            if not isinstance(tos, dict) or tos.get("verdict") != "allowed":
                return "tos"
        robots = row.get("robots")
        if not isinstance(robots, dict) or not robots.get("origin"):
            return "no_record"
        if robots.get("origin") != _rr._origin_of(url):
            return "origin"
        entry = {k: row.get(k) for k in ("status", "deny", "robots", "challenge")}
        if not _jw.rating_host_allowed(entry, url, now):
            return "robots"
        return None
    except Exception:  # noqa: BLE001 - fail-closed
        return "bad_url"


# ---------------------------------------------------------------------------
# polite fetch (the robots registry's emitter, politeness and hop rules)
# ---------------------------------------------------------------------------

class FetchResult(NamedTuple):
    status: Optional[int]
    headers: Any
    body: str
    url: str
    refused: Optional[str]
    gate: Optional[str]


class PoliteFetcher:
    """One run's sequential fetcher over robots_registry: ``Politeness`` (the
    stored crawl delay per host), the named request headers of
    ``default_fetch``, ``allow_redirects=False`` with each hop followed by
    ``_fetch_following`` only after the SSRF validator passes it and, with
    ``gate``, the per-URL robots gate on the first URL and on every hop."""

    def __init__(self, fetch: Any = None, validate: Any = None, sleep: Any = None,
                 require_tos: bool = False) -> None:
        from app.services import robots_registry as _rr

        self._rr = _rr
        self._fetch = fetch if fetch is not None else _rr.default_fetch
        self._validate = validate if validate is not None else _rr.default_validate
        self._polite = _rr.Politeness(sleep if sleep is not None else asyncio.sleep)
        self.require_tos = require_tos
        self.requests = 0

    def _may(self, row: Any, now: Any) -> Any:
        def may(u: str) -> bool:
            return url_gate(row, u, now, require_tos=self.require_tos) is None
        return may

    async def get(self, url: str, row: Any = None, now: Any = None, *, gate: bool = True,
                  timeout: float = 20.0, delay: Any = None) -> FetchResult:
        may = None
        if gate:
            reason = url_gate(row, url, now, require_tos=self.require_tos)
            if reason is not None:
                return FetchResult(None, {}, "", url, "gate", reason)
            may = self._may(row, now)
        if delay is None and isinstance(row, dict):
            delay = self._rr._stored_crawl_delay(row)
        self.requests += 1
        res = await self._rr._fetch_following(url, self._fetch, self._validate, self._polite, delay,
                                              timeout, may_fetch=may)
        body = res.body[:MAX_BODY_CHARS] if isinstance(res.body, str) else ""
        return FetchResult(res.status, res.headers, body, res.url, res.refused, None)


def ok_status(status: Any) -> bool:
    return isinstance(status, int) and 200 <= status < 300


# ---------------------------------------------------------------------------
# the KB writer (S81-14 builder outputs only, service role)
# ---------------------------------------------------------------------------

def _norm(value: Any) -> str:
    """A comparable text form of a key column (12.50 == 12.5)."""
    if isinstance(value, (int, float, str)) and not isinstance(value, bool):
        try:
            return str(Decimal(str(value)).normalize())
        except (InvalidOperation, ValueError):
            return str(value)
    return str(value)


class KbWriter:
    """Insert-ignore writes of builder outputs; a row whose key set is not the
    builder's exact key set is counted ``not_built`` and never sent."""

    def __init__(self, client: Any) -> None:
        self.client = client
        self.counts: Counter = Counter()

    def _built(self, table: str, rows: Sequence[Any]) -> List[Dict[str, Any]]:
        keys = set(kb_leaf().KB_BUILDER_KEYS[table])
        out = []
        for row in rows:
            if isinstance(row, dict) and set(row) == keys:
                out.append(row)
            else:
                self.counts["not_built"] += 1
        return out

    def _send(self, table: str, built: Sequence[Dict[str, Any]], on_conflict: str) -> List[Dict[str, Any]]:
        inserted: List[Dict[str, Any]] = []
        for i in range(0, len(built), WRITE_BATCH):
            batch = list(built[i:i + WRITE_BATCH])
            resp = (self.client.table(table)
                    .upsert(batch, on_conflict=on_conflict, ignore_duplicates=True).execute())
            data = getattr(resp, "data", None)
            if isinstance(data, list):
                inserted.extend(r for r in data if isinstance(r, dict))
            self.counts[table + "_sent"] += len(batch)
        return inserted

    def upsert(self, table: str, rows: Sequence[Any], on_conflict: str) -> List[Dict[str, Any]]:
        return self._send(table, self._built(table, rows), on_conflict)

    def products(self, rows: Sequence[Any]) -> List[Dict[str, Any]]:
        return self.upsert(KB_PRODUCTS_TABLE, rows, "id")

    def variants(self, rows: Sequence[Any]) -> List[Dict[str, Any]]:
        return self.upsert(KB_VARIANTS_TABLE, rows, "id")

    def specs(self, rows: Sequence[Any]) -> List[Dict[str, Any]]:
        return self.upsert(KB_SPECS_TABLE, rows, "product_id,field,lang")

    def offers(self, rows: Sequence[Any]) -> int:
        """Insert-ignore on the observation key; every row the insert did not
        return is a re-observation: ONE update of the KB_OFFER_UPSERT_SET columns
        (never captured_at / first_seen) per row. Returns the update count."""
        kb = kb_leaf()
        key_cols = kb.KB_OFFER_OBSERVATION_KEY
        built = self._built(KB_OFFERS_TABLE, rows)
        inserted = self._send(KB_OFFERS_TABLE, built, ",".join(key_cols))
        seen = {tuple(_norm(r.get(c)) for c in key_cols) for r in inserted}
        updates = 0
        for row in built:
            if tuple(_norm(row.get(c)) for c in key_cols) in seen:
                continue
            query = self.client.table(KB_OFFERS_TABLE).update({k: row[k] for k in kb.KB_OFFER_UPSERT_SET})
            for col in key_cols:
                query = query.eq(col, row[col])
            query.execute()
            updates += 1
        self.counts["offer_updates"] += updates
        return updates

    def gaps(self, rows: Sequence[Any]) -> int:
        """Insert-ignore on (product_key, field); a re-discovery updates
        last_seen ONLY (state, source_hint and demand_count never move)."""
        built = self._built(KB_GAPS_TABLE, rows)
        inserted = self._send(KB_GAPS_TABLE, built, "product_key,field")
        seen = {(r.get("product_key"), r.get("field")) for r in inserted}
        updates = 0
        for row in built:
            if (row["product_key"], row["field"]) in seen:
                continue
            (self.client.table(KB_GAPS_TABLE).update({"last_seen": row["last_seen"]})
             .eq("product_key", row["product_key"]).eq("field", row["field"]).execute())
            updates += 1
        self.counts["gap_updates"] += updates
        return updates

    def ledger(self, row: Dict[str, Any]) -> None:
        self.client.table(LLM_SPEND_LEDGER_TABLE).insert(row).execute()
