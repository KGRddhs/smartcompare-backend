"""D17 MEASURE-COVERAGE: the daily kb_coverage_daily rollup (an off-clock cron).

Flag ENABLE_KB_COVERAGE_ROLLUP, the G2 mode idiom read FIRST (unset / garbage
OFF, the house truthy set DRY RUN, the exact word ``apply`` WRITE; the CLI
``--dry-run`` downgrades apply). OFF is one env read and one INFO line: nothing
of the app is imported and nothing is read.

One run measures the previous UTC day (``--day YYYY-MM-DD`` overrides) over the
closed metric list below, prints one ``[KB_COVERAGE] metric=...`` line per
metric, writes the optional ``--report`` markdown and, in APPLY only, sends ONE
upsert of every row (``on_conflict="day,metric"``: a re-run replaces) built by
the S81-14 coverage-row builder. Reads go through the service-role client in
pages; the ``search_logs`` proxy selects exactly four columns (never a user id,
the query text or an error message); the per-host D14 counters are read with
ONE pipeline of HGETALL over the live + blocked registry hosts, and a host
whose hash is absent or empty emits nothing (absent is never zero). A family
whose read raises is omitted with one WARNING naming the exception type.
"""
from __future__ import annotations

import argparse
import logging
import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import scripts.kb_seed_common as common

logger = logging.getLogger("cron_kb_coverage")

PREFIX = "[KB_COVERAGE]"
FLAG = "ENABLE_KB_COVERAGE_ROLLUP"
KB_COVERAGE_TABLE = "kb_coverage_daily"
KB_OFFERS_LATEST_VIEW = "kb_offers_latest"
SEARCH_LOGS_TABLE = "search_logs"
SEARCH_LOG_COLUMNS = "products_found,success,is_synthetic,created_at"

#: The fragrance spec fields a KB card must cite for a full hit (the S81-18
#: required set: the critical schema list minus the licence fields).
REQUIRED_SPEC_FIELDS: Tuple[str, ...] = ("concentration", "scent_family", "season")
GAP_STATES: Tuple[str, ...] = ("open", "queued", "needs_operator", "licence", "closed")
HINT_STATES: Tuple[str, ...] = ("queued", "closed", "needs_operator")
HINT_PREFIX = "pdp_"
FRESH_DAYS = 7
METRIC_MAX_LEN = 128
SHARE_PLACES = 4


def coverage_mode() -> str:
    """off | dry | apply, read per call (the FIRST statement of the run)."""
    return common.run_mode(FLAG)


def max_hosts() -> int:
    """KB_COVERAGE_MAX_HOSTS (500, clamped 1..5000; unusable -> 500)."""
    return common.int_knob("KB_COVERAGE_MAX_HOSTS", 500, 1, 5000)


# ---------------------------------------------------------------------------
# small pure helpers
# ---------------------------------------------------------------------------

def _ts(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        out = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return out if out.tzinfo is not None else out.replace(tzinfo=timezone.utc)


def _share(part: int, whole: int) -> float:
    return round(part / whole, SHARE_PLACES) if whole else 0.0


def _hours(now: datetime, moment: datetime) -> float:
    return (now - moment).total_seconds() / 3600.0


def _norm_name(text: Any) -> str:
    """casefold, every non-alphanumeric to a space, spaces collapsed."""
    if not isinstance(text, str):
        return ""
    folded = "".join(ch if ch.isalnum() else " " for ch in text.casefold())
    return " ".join(folded.split())


def _product_of(variant_id: Any) -> Optional[str]:
    """The product id of a variant id (``<product>|<ml>``)."""
    if isinstance(variant_id, str) and "|" in variant_id:
        return variant_id.rsplit("|", 1)[0]
    return None


def _paged(client: Any, table: str, columns: str,
           filters: Tuple[Tuple[str, Tuple[Any, ...]], ...] = ()) -> List[Dict[str, Any]]:
    """Every row of ``table`` in pages of PAGE_SIZE (at most MAX_PAGES pages)."""
    rows: List[Dict[str, Any]] = []
    for page in range(common.MAX_PAGES):
        start = page * common.PAGE_SIZE
        query = client.table(table).select(columns)
        for name, args in filters:
            query = getattr(query, name)(*args)
        data = getattr(query.range(start, start + common.PAGE_SIZE - 1).execute(), "data", None)
        if not isinstance(data, list):
            raise TypeError("page is not a list")
        rows.extend(r for r in data if isinstance(r, dict))
        if len(data) < common.PAGE_SIZE:
            break
    return rows


# ---------------------------------------------------------------------------
# the rollup
# ---------------------------------------------------------------------------

class _Rollup:
    """Collects (metric, value, n) triples in the closed 2.2 order."""

    def __init__(self, client: Any, redis: Any, day: date, now: datetime) -> None:
        self.client, self.redis, self.day, self.now = client, redis, day, now
        self.out: List[Tuple[str, Any, int]] = []
        self.redis_read = 0

    def add(self, name: str, value: Any, n: int) -> None:
        self.out.append((name, value, int(n)))

    def guarded(self, label: str, fn: Callable[[], Any]) -> Any:
        """Run one read family; a raise omits it with ONE WARNING (type name)."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - one family omitted, the rest kept
            logger.warning("%s family=%s read failed (%s)", PREFIX, label, type(exc).__name__)
            return None

    # -- reads ---------------------------------------------------------------
    def _products(self) -> List[Dict[str, Any]]:
        return _paged(self.client, common.KB_PRODUCTS_TABLE, "id,brand,name,identity_confidence,concentration")

    def _offers(self) -> List[Dict[str, Any]]:
        return _paged(self.client, KB_OFFERS_LATEST_VIEW, "variant_id,last_seen,captured_at")

    def _sized(self) -> Set[str]:
        rows = _paged(self.client, common.KB_VARIANTS_TABLE, "product_id,size_ml")
        return {r.get("product_id") for r in rows if r.get("size_ml") is not None}

    def _imaged(self) -> Set[str]:
        from app.services import kb_ingest

        return {r.get("product_id") for r in _paged(self.client, kb_ingest.KB_IMAGES_TABLE, "product_id")}

    def _rated(self) -> Set[str]:
        from app.services import kb_ingest

        return {r.get("product_id") for r in _paged(self.client, kb_ingest.KB_REVIEWS_TABLE, "product_id")}

    def _cited(self) -> Set[str]:
        fields: Dict[Any, Set[Any]] = {}
        for r in _paged(self.client, common.KB_SPECS_TABLE, "product_id,field,cited"):
            if r.get("cited") is True:
                fields.setdefault(r.get("product_id"), set()).add(r.get("field"))
        need = set(REQUIRED_SPEC_FIELDS)
        return {pid for pid, have in fields.items() if need <= have}

    # -- families ------------------------------------------------------------
    def run(self) -> None:
        products = self.guarded("products", self._products)
        offers = self.guarded("offers", self._offers)
        sized = self.guarded("variants", self._sized)
        imaged = self.guarded("images", self._imaged)
        cited = self.guarded("specs", self._cited)
        rated = self.guarded("reviews", self._rated)

        if products:
            self._field_shares(products, offers, sized, imaged, cited, rated)
        if offers:
            self._ages(offers)
        self.guarded("gaps", self._gap_states)
        if products is not None:
            self.guarded("proxy", lambda: self._proxy(products))
        self._hosts()

    def _field_shares(self, products, offers, sized, imaged, cited, rated) -> None:
        ids = [p.get("id") for p in products]
        total = len(ids)

        def share(members: Set[Any]) -> float:
            return _share(sum(1 for i in ids if i in members), total)

        self.add("kb.products.total", total, total)
        high = {p.get("id") for p in products if p.get("identity_confidence") == "high"}
        self.add("kb.products.identity_high_share", share(high), total)
        fresh: Optional[Set[Any]] = None
        if offers is not None:
            cut = self.now - timedelta(days=FRESH_DAYS)
            with_offer = {_product_of(o.get("variant_id")) for o in offers}
            fresh = {_product_of(o.get("variant_id")) for o in offers
                     if (_ts(o.get("last_seen")) is not None and _ts(o.get("last_seen")) >= cut)}
            self.add("kb.field.offer_share", share(with_offer), total)
            self.add("kb.field.offer_fresh_share", share(fresh), total)
        if imaged is not None:
            self.add("kb.field.image_share", share(imaged), total)
        if cited is not None:
            self.add("kb.field.specs_cited_share", share(cited), total)
        if rated is not None:
            self.add("kb.field.rating_share", share(rated), total)
        if sized is not None:
            self.add("kb.field.size_share", share(sized), total)
        concentrated = {p.get("id") for p in products if p.get("concentration")}
        self.add("kb.field.concentration_share", share(concentrated), total)
        if None not in (fresh, imaged, cited, sized):
            complete = fresh & imaged & cited & sized & concentrated
            self.add("kb.field.complete_share", share(complete), total)

    def _ages(self, offers: List[Dict[str, Any]]) -> None:
        seen = [_hours(self.now, t) for t in (_ts(o.get("last_seen")) for o in offers) if t is not None]
        caps = [_hours(self.now, t) for t in (_ts(o.get("captured_at")) for o in offers) if t is not None]
        if seen:
            self.add("kb.price.age_median_hours", round(statistics.median(seen), 2), len(seen))
        if caps:
            self.add("kb.price.capture_age_median_hours", round(statistics.median(caps), 2), len(caps))

    def _gap_states(self) -> None:
        rows = _paged(self.client, common.KB_GAPS_TABLE, "field,state")
        gaps = [r for r in rows if not str(r.get("field") or "").startswith(HINT_PREFIX)]
        hints = [r for r in rows if str(r.get("field") or "").startswith(HINT_PREFIX)]
        for state in GAP_STATES:
            count = sum(1 for r in gaps if r.get("state") == state)
            self.add("kb.gaps.state." + state, count, count)
        for state in HINT_STATES:
            count = sum(1 for r in hints if r.get("state") == state)
            self.add("kb.hints.state." + state, count, count)

    def _proxy(self, products: List[Dict[str, Any]]) -> None:
        start = datetime(self.day.year, self.day.month, self.day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        rows = _paged(self.client, SEARCH_LOGS_TABLE, SEARCH_LOG_COLUMNS,
                      (("gte", ("created_at", start.isoformat())), ("lt", ("created_at", end.isoformat()))))
        known: Set[str] = set()
        for p in products:
            known.add(_norm_name(p.get("name")))
            known.add(_norm_name("%s %s" % (p.get("brand") or "", p.get("name") or "")))
        known.discard("")
        names = hits = pairs = pair_hits = 0
        for row in rows:
            if row.get("success") is not True or row.get("is_synthetic") is True:
                continue
            found = row.get("products_found")
            matched = []
            for item in found if isinstance(found, list) else []:
                label = item.get("name") if isinstance(item, dict) else item
                matched.append(_norm_name(label) in known)
            names += len(matched)
            hits += sum(1 for m in matched if m)
            if len(matched) == 2:
                pairs += 1
                pair_hits += 1 if all(matched) else 0
        self.add("proxy.identity_hit_share", _share(hits, names), names)
        self.add("proxy.pair_hit_share", _share(pair_hits, pairs), pairs)

    def _hosts(self) -> None:
        if self.redis is None:
            return
        rows = self.guarded("registry", lambda: common.read_merchant_rows(self.client))
        if rows is None:
            return
        hosts = sorted({str(r["host"]) for r in rows
                        if r.get("status") in ("live", "blocked") and r.get("host")})[:max_hosts()]
        stamp = self.day.strftime("%Y%m%d")

        def read() -> List[Any]:
            pipe = self.redis.pipeline()
            for host in hosts:
                pipe.hgetall("kbh:" + stamp + ":" + host)
            return list(pipe.exec() or [])

        result = self.guarded("hosts", read)
        if result is None:
            return
        self.redis_read = 1
        for host, fields in zip(hosts, result, strict=False):
            if not isinstance(fields, dict) or not fields:
                continue  # absent is never zero
            attempts = skips = challenges = 0
            for key, raw in fields.items():
                try:
                    count = int(raw)
                except (TypeError, ValueError):
                    continue
                name = key.decode("ascii", "replace") if isinstance(key, bytes) else str(key)
                attempts += count
                if name.endswith(":robots_skip"):
                    skips += count
                elif name.endswith(":challenge"):
                    challenges += count
            self.add("host.robots_skip:" + host, skips, attempts)
            self.add("host.challenge:" + host, challenges, attempts)


def _write_report(path: Optional[str], day: date, metrics: List[Tuple[str, Any, int]]) -> None:
    if not path:
        return
    lines = ["# KB coverage " + day.isoformat(), "", "| metric | value | n |", "|---|---|---|"]
    lines += ["| %s | %s | %d |" % (name, value, n) for name, value, n in metrics]
    lines += ["", "The proxy.* metrics are a PROXY from search_logs product names (success, not synthetic), "
              "not compare_runs (S81-22)."]
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def _default_redis() -> Any:
    try:
        from app.services import cache_service

        return cache_service.redis_client
    except Exception:  # noqa: BLE001 - no Redis = no host metrics
        return None


def main(argv: Optional[List[str]] = None, client: Any = None, redis: Any = None) -> int:
    mode = coverage_mode()
    if mode == common.MODE_OFF:
        logger.info("%s mode=off %s not set; skipping run", PREFIX, FLAG)
        return 0
    parser = argparse.ArgumentParser(prog="cron_kb_coverage")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", default=None)
    parser.add_argument("--day", default=None)
    args = parser.parse_args(argv)
    mode = common.cli_mode(mode, args.dry_run)
    now = common._now()
    try:
        day = datetime.strptime(args.day, "%Y-%m-%d").date() if args.day else (now - timedelta(days=1)).date()
    except ValueError:
        logger.warning("%s bad --day; skipping run", PREFIX)
        return 0
    logger.info("%s mode=%s day=%s", PREFIX, mode, day.isoformat())
    client = common.resolve_client(client, PREFIX)
    if client is None:
        return 0
    if redis is None:
        redis = _default_redis()
    rollup = _Rollup(client, redis, day, now)
    rollup.run()
    kb = common.kb_leaf()
    rows: List[Dict[str, Any]] = []
    not_built = skipped_long = 0
    for name, value, n in rollup.out:
        if len(name) > METRIC_MAX_LEN:
            skipped_long += 1
            continue
        logger.info("%s metric=%s value=%s n=%d", PREFIX, name, value, n)
        row = kb.build_coverage_row(day=day, metric=name, value=value, n=n)
        if row is None:
            not_built += 1
            continue
        rows.append(row)
    _write_report(args.report, day, rollup.out)
    if mode == common.MODE_APPLY and rows:
        try:
            client.table(KB_COVERAGE_TABLE).upsert(rows, on_conflict="day,metric").execute()
        except Exception as exc:  # noqa: BLE001 - one WARNING, exit 0
            logger.warning("%s upsert failed (%s)", PREFIX, type(exc).__name__)
    logger.info("%s totals rows=%d not_built=%d skipped_long=%d redis=%d",
                PREFIX, len(rows), not_built, skipped_long, rollup.redis_read)
    return 0


run = main

if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
