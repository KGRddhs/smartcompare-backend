"""S81-19 GAP-QUEUE: the off-clock KB enrich worker and the KB price refresh.

Flags (new names, default OFF, read per call):

* ``ENABLE_KB_ENRICH_WORKER`` - the run, the G2 mode idiom read FIRST (unset /
  garbage OFF, the house truthy set DRY RUN, the exact word ``apply`` WRITE; the
  CLI ``--dry-run`` downgrades apply). OFF = one env read and one INFO line:
  nothing of the app is imported, no client, no Redis.
* ``ENABLE_KB_GAP_FILL`` - the gap-ladder leg inside a run (house boolean). OFF =
  the price refresh only.
* ``ENABLE_KB_GAP_WEB_SEARCH`` - INERT in G4: ON logs ONE
  ``step=web_search status=not_built`` line per run and skips; no provider call,
  no LLM module import (S81-21 builds the step).

The gap ladder (APPLY): the open, non-``pdp_`` kb_gaps rows of the demand window,
ranked per product by (max demand_count, latest last_seen), walked per product
under a Redis single flight ``SET kbenrich:sf:<sha256(product_key)[:32]> <run id>
NX EX`` that fails CLOSED (no Redis or a raising SET = the product is skipped,
``lock_unavailable``; a held lock = ``locked``) and is released by an owner check
(GET, then DELETE only when it still holds this run's id). ``specs`` gaps move to
``licence`` (never fetched). The other fields walk (1) the registry search
template of live, ToS-allowed hosts, (2) the product's queued G2 ``pdp_`` hints,
(3) the inert web-search step, (4) the operator queue (``needs_operator``) when
every candidate host refused for a blocked status or the ToS. Every fetch is the
named robots agent's ``PoliteFetcher(require_tos=True)`` (the persisted robots verdict + the
ToS on the first URL and every hop) at ``KB_ENRICH_FETCH_TIMEOUT_SECONDS``; no
fallback adapter, no render tier. Every kb_gaps state move is ONE compare-and-set
update whose payload is ``{"state": <new>}`` only, never retried.

The price refresh (APPLY): the ``KB_ENRICH_HEAD_N`` most-demanded products daily
and, on ISO weekday ``KB_ENRICH_TAIL_WEEKDAY``, up to ``KB_ENRICH_TAIL_MAX`` other
products holding offers (the oldest last_seen first): each stored canonical URL is
re-fetched politely and a new observation is written (the same amount moves
last_seen through the KB_OFFER_UPSERT_SET re-observation update).

Rows go only through the S81-14 builders and ``kb_seed_common.KbWriter``
(insert-ignore). No LLM call exists here, so the off-clock spend cap is printed
as a DRY bound and the breaker is never called. DRY reads only and prints the
ranked queue, the ladder plan, the refresh plan counts and the spend bound (JSON
``--report``). Log lines carry constants, host names and ints only.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import re
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import quote_plus, urljoin, urlsplit

import scripts.kb_seed_common as common

logger = logging.getLogger("cron_kb_enrich")

PREFIX = "[KB_ENRICH]"
FLAG = "ENABLE_KB_ENRICH_WORKER"
FILL_FLAG = "ENABLE_KB_GAP_FILL"
WEB_FLAG = "ENABLE_KB_GAP_WEB_SEARCH"
LOCK_PREFIX = "kbenrich:sf:"
HINT_PREFIX = "pdp_"
LICENCE_GAP_FIELDS: Tuple[str, ...] = ("specs",)
FETCH_GAP_FIELDS: Tuple[str, ...] = ("price", "image", "size", "concentration", "rating", "review_count")
LADDER_STEPS: Tuple[str, ...] = ("search", "pdp_hint", "web_search", "operator")
OPERATOR_REFUSALS: Tuple[str, ...] = ("refused:tos", "refused:not_live")
CANDIDATES_PER_SEARCH = 2
TOTAL_KEYS: Tuple[str, ...] = (
    "gaps", "filled", "closed", "needs_operator", "licence", "hints_closed", "locked",
    "lock_unavailable", "refresh_fetched", "refresh_written", "refused", "web_search_not_built",
)
_ML_RE = re.compile(r"^\s*(\d{1,5})\s*ml\s*$", re.IGNORECASE)
_HREF_RE = re.compile(r"""href\s*=\s*["']([^"'#\s]+)["']""", re.IGNORECASE)
_MARKET_RE = re.compile(r"^[A-Z]{2,3}$")
_REASON_RE = re.compile(r"[^a-z_]")


# ---------------------------------------------------------------------------
# flags and knobs (read per call)
# ---------------------------------------------------------------------------

def enrich_mode() -> str:
    return common.run_mode(FLAG)


def gap_fill_enabled() -> bool:
    return common.house_flag(FILL_FLAG)


def web_search_requested() -> bool:
    return common.house_flag(WEB_FLAG)


def max_gaps() -> int:
    return common.int_knob("KB_ENRICH_MAX_GAPS", 200, 1, 2000)


def hosts_per_gap() -> int:
    return common.int_knob("KB_ENRICH_HOSTS_PER_GAP", 3, 1, 10)


def head_n() -> int:
    return common.int_knob("KB_ENRICH_HEAD_N", 50, 1, 1000)


def tail_max() -> int:
    return common.int_knob("KB_ENRICH_TAIL_MAX", 500, 1, 5000)


def tail_weekday() -> int:
    return common.int_knob("KB_ENRICH_TAIL_WEEKDAY", 7, 1, 7)


def demand_days() -> int:
    return common.int_knob("KB_ENRICH_DEMAND_DAYS", 7, 1, 30)


def fetch_timeout() -> float:
    return common.float_knob("KB_ENRICH_FETCH_TIMEOUT_SECONDS", 4.0, 1.0, 4.0)


def lock_seconds() -> int:
    return common.int_knob("KB_ENRICH_LOCK_SECONDS", 900, 60, 3600)


# ---------------------------------------------------------------------------
# reads
# ---------------------------------------------------------------------------

def _ts(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        out = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return out if out.tzinfo is not None else out.replace(tzinfo=timezone.utc)


def _data(resp: Any) -> List[Dict[str, Any]]:
    data = getattr(resp, "data", None)
    return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []


def _is_hint(field: Any) -> bool:
    return str(field or "").startswith(HINT_PREFIX)


def _window_start(now: datetime) -> str:
    return (now - timedelta(days=demand_days())).isoformat()


def read_queue(client: Any, now: datetime) -> List[Dict[str, Any]]:
    """The ranked queue: one entry per product_key of the open, non-pdp_ gaps of the
    demand window (at most KB_ENRICH_MAX_GAPS rows read), ranked by the product's max
    demand_count, then its latest last_seen."""
    resp = (client.table(common.KB_GAPS_TABLE)
            .select("product_key,field,demand_count,last_seen,state,source_hint")
            .eq("state", "open").gte("last_seen", _window_start(now))
            .order("demand_count", desc=True).order("last_seen", desc=True)
            .limit(max_gaps()).execute())
    floor = datetime.min.replace(tzinfo=timezone.utc)
    by_key: Dict[str, Dict[str, Any]] = {}
    for row in _data(resp):
        key, field = row.get("product_key"), row.get("field")
        if not isinstance(key, str) or not isinstance(field, str) or _is_hint(field):
            continue
        entry = by_key.setdefault(key, {"product_key": key, "fields": [], "demand": 0, "last": floor})
        if field not in entry["fields"]:
            entry["fields"].append(field)
        demand = row.get("demand_count")
        if isinstance(demand, int) and not isinstance(demand, bool):
            entry["demand"] = max(entry["demand"], demand)
        seen = _ts(row.get("last_seen"))
        if seen is not None and seen > entry["last"]:
            entry["last"] = seen
    ranked = sorted(by_key.values(), key=lambda e: (e["demand"], e["last"]), reverse=True)
    return ranked


def read_merchants(client: Any) -> List[Dict[str, Any]]:
    """Every merchant registry row with the search template (paged, ordered by host)."""
    from app.services import merchant_registry as _mr

    rows: List[Dict[str, Any]] = []
    for page in range(common.MAX_PAGES):
        start = page * common.PAGE_SIZE
        resp = (client.table(_mr.KB_MERCHANTS_TABLE).select(common.READ_COLUMNS + ",search_template")
                .order("host").range(start, start + common.PAGE_SIZE - 1).execute())
        data = getattr(resp, "data", None)
        if not isinstance(data, list):
            raise TypeError("registry page is not a list")
        rows.extend(r for r in data if isinstance(r, dict))
        if len(data) < common.PAGE_SIZE:
            break
    return rows


def read_products(client: Any, ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    ids = list(dict.fromkeys(i for i in ids if isinstance(i, str)))
    for i in range(0, len(ids), 100):
        resp = (client.table(common.KB_PRODUCTS_TABLE).select("id,brand,name")
                .in_("id", ids[i:i + 100]).execute())
        for row in _data(resp):
            if isinstance(row.get("id"), str):
                out[row["id"]] = row
    return out


def refresh_order(client: Any, now: datetime) -> Tuple[List[str], List[str]]:
    """(head, tail): the head = the KB_ENRICH_HEAD_N product ids with the largest
    summed demand_count (non-pdp_ gaps of the window, any state), then by id; the
    tail (only on KB_ENRICH_TAIL_WEEKDAY) = up to KB_ENRICH_TAIL_MAX other products
    holding offers, the oldest latest last_seen first."""
    resp = (client.table(common.KB_GAPS_TABLE).select("product_key,field,demand_count,last_seen")
            .gte("last_seen", _window_start(now)).execute())
    demand: Dict[str, int] = {}
    for row in _data(resp):
        key, n = row.get("product_key"), row.get("demand_count")
        if not isinstance(key, str) or _is_hint(row.get("field")):
            continue
        if isinstance(n, bool) or not isinstance(n, int):
            n = 0
        demand[key] = demand.get(key, 0) + n
    head = [k for k, _n in sorted(demand.items(), key=lambda kv: (-kv[1], kv[0]))][:head_n()]
    tail: List[str] = []
    if now.isoweekday() == tail_weekday():
        latest: Dict[str, datetime] = {}
        for page in range(common.MAX_PAGES):
            start = page * common.PAGE_SIZE
            resp = (client.table(common.KB_OFFERS_TABLE).select("variant_id,last_seen")
                    .range(start, start + common.PAGE_SIZE - 1).execute())
            data = _data(resp)
            for row in data:
                vid, seen = row.get("variant_id"), _ts(row.get("last_seen"))
                if not isinstance(vid, str) or "|" not in vid or seen is None:
                    continue
                pid = vid.rsplit("|", 1)[0]
                if pid not in latest or seen > latest[pid]:
                    latest[pid] = seen
            if len(data) < common.PAGE_SIZE:
                break
        taken = set(head)
        tail = [p for p, _s in sorted(latest.items(), key=lambda kv: (kv[1], kv[0])) if p not in taken]
        tail = tail[:tail_max()]
    return head, tail


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def lock_key(product_key: str) -> str:
    return LOCK_PREFIX + hashlib.sha256(product_key.encode("utf-8")).hexdigest()[:32]


def _host(url: Any) -> str:
    try:
        return (urlsplit(str(url)).hostname or "").lower()
    except ValueError:
        return ""


def search_candidates(body: Any, url: str) -> List[str]:
    """PDP candidates of a search response on the SAME host: the Shopify suggest JSON
    ``resources.results.products[].url`` (resolved against the origin), else the
    same-host anchors whose path is not the search path."""
    parts = urlsplit(url)
    origin = "%s://%s" % (parts.scheme, parts.netloc)
    found: List[str] = []
    text = body if isinstance(body, str) else ""
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        parsed = None
    if isinstance(parsed, dict):
        results = parsed.get("resources")
        results = results.get("results") if isinstance(results, dict) else None
        products = results.get("products") if isinstance(results, dict) else None
        for item in products if isinstance(products, list) else []:
            if isinstance(item, dict) and isinstance(item.get("url"), str):
                found.append(urljoin(origin + "/", item["url"]))
    else:
        for href in _HREF_RE.findall(text):
            full = urljoin(url, href)
            if urlsplit(full).path != parts.path:
                found.append(full)
    same_host = [u for u in found if urlsplit(u).netloc == parts.netloc]
    return list(dict.fromkeys(same_host))


def _size_from(price: Dict[str, Any]) -> Optional[int]:
    match = _ML_RE.match(str(price.get("size") or ""))
    if not match:
        return None
    ml = int(match.group(1))
    return ml if 1 <= ml <= 9999 else None


# ---------------------------------------------------------------------------
# the APPLY run
# ---------------------------------------------------------------------------

class EnrichRun:
    def __init__(self, client: Any, redis: Any, now: datetime, web: bool) -> None:
        self.client, self.redis, self.now, self.web = client, redis, now, web
        self.counts: Counter = Counter(dict.fromkeys(TOTAL_KEYS, 0))
        self.writer = common.KbWriter(client)
        self.run_id = uuid.uuid4().hex
        self.fetcher = common.PoliteFetcher(require_tos=True)
        self._merchants: Optional[List[Dict[str, Any]]] = None

    # -- registry --------------------------------------------------------------
    def merchants(self) -> List[Dict[str, Any]]:
        if self._merchants is None:
            self._merchants = read_merchants(self.client)
        return self._merchants

    # -- the single flight (fail-closed) ---------------------------------------
    def acquire(self, product_key: str) -> Optional[str]:
        if self.redis is None:
            self.counts["lock_unavailable"] += 1
            return None
        key = lock_key(product_key)
        try:
            ok = self.redis.set(key, self.run_id, nx=True, ex=lock_seconds())
        except Exception:  # noqa: BLE001 - fail closed: never fetch without the lock
            self.counts["lock_unavailable"] += 1
            return None
        if not ok:
            self.counts["locked"] += 1
            return None
        return key

    def release(self, key: str) -> None:
        """Owner check: DELETE only while the key still holds this run's id (a lost
        race leaves the TTL to expire it; stated limit S81-19-L4)."""
        try:
            held = self.redis.get(key)
            if isinstance(held, bytes):
                held = held.decode("utf-8", "replace")
            if held == self.run_id:
                self.redis.delete(key)
        except Exception:  # noqa: BLE001 - the TTL expires it
            return

    # -- the gap state compare-and-set -----------------------------------------
    def move(self, product_key: str, field: str, old: str, new: str) -> bool:
        if new not in common.kb_leaf().KB_GAP_STATES:
            return False
        resp = (self.client.table(common.KB_GAPS_TABLE).update({"state": new})
                .eq("product_key", product_key).eq("field", field).eq("state", old).execute())
        return bool(_data(resp))

    # -- one polite fetch --------------------------------------------------------
    async def fetch(self, step: str, url: Any, row: Any) -> Tuple[str, Any]:
        host = row.get("host") if isinstance(row, dict) and row.get("host") else "-"
        try:
            res = await self.fetcher.get(url, row, self.now, timeout=fetch_timeout())
        except Exception as exc:  # noqa: BLE001 - one fetch error, the ladder goes on
            outcome = "error:" + type(exc).__name__
            logger.info("%s product step=%s host=%s outcome=%s", PREFIX, step, host, outcome)
            return outcome, None
        if res.refused:
            reason = res.gate if res.refused == "gate" else res.refused
            outcome = "refused:" + (_REASON_RE.sub("_", str(reason).lower()) or "unknown")
            self.counts["refused"] += 1
        elif common.ok_status(res.status):
            return "ok", res
        else:
            outcome = "error:http_status"
        logger.info("%s product step=%s host=%s outcome=%s", PREFIX, step, host, outcome)
        return outcome, res

    # -- extraction to rows ------------------------------------------------------
    def harvest(self, step: str, pid: str, product: Dict[str, Any], row: Dict[str, Any], res: Any,
                url: str, offer: Optional[Dict[str, Any]] = None) -> Set[str]:
        """The deterministic page extractor -> builder rows -> KbWriter. ``offer``
        = the stored offer a refresh re-observes (its variant and size are kept)."""
        from app.services import jsonld_widen, kb_ingest, price_service

        kb = common.kb_leaf()
        host = row.get("host")
        filled: Set[str] = set()
        final_url = res.url if isinstance(res.url, str) and res.url else url
        price = price_service.extract_price_from_html(
            res.body, "%s %s" % (product.get("brand") or "", product.get("name") or ""),
            common.row_currency(row), host, url, category=kb.KB_CATEGORY, final_url=final_url)
        market = str(row.get("country") or "").strip().upper()
        amount = price.get("amount") if isinstance(price, dict) else None
        rung = kb_ingest.rung_for(price.get("source_method")) if isinstance(price, dict) else None
        if (not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0
                or price.get("estimated") is True or rung is None or not _MARKET_RE.match(market)):
            logger.info("%s product step=%s host=%s outcome=empty", PREFIX, step, host)
            return filled
        conc = pid.split("|")[3]
        conc = conc if conc in kb.kb_concentrations() else None
        if offer is not None:
            variant_id = offer.get("variant_id")
            size_ml = offer.get("size_ml") if isinstance(offer.get("size_ml"), int) else None
            if size_ml is None and isinstance(variant_id, str) and variant_id.rsplit("|", 1)[-1].isdigit():
                size_ml = int(variant_id.rsplit("|", 1)[-1])
        else:
            size_ml = _size_from(price)
            variant_id = kb.kb_variant_key(pid, conc, size_ml)
            self.writer.variants([kb.build_variant_row(
                id=variant_id, product_id=pid, updated_at=self.now, concentration=conc, size_ml=size_ml)])
        stock = price.get("in_stock")
        built = kb.build_offer_row(
            variant_id=variant_id, merchant_id=host, market=market, amount=amount,
            observed_currency=price.get("currency"), evidence_rung=rung,
            canonical_url=kb.canonical_offer_url(final_url), captured_at=self.now, size_ml=size_ml,
            in_stock=stock if isinstance(stock, bool) else None)
        if built is not None:
            self.writer.offers([built])
            filled.add("price")
            if step == "refresh":
                self.counts["refresh_written"] += 1
        if size_ml:
            filled.add("size")
        if conc:
            filled.add("concentration")
        image = price.get("image_url")
        if isinstance(image, str) and jsonld_widen.allowed_image_url(
                image, final_url, price_service.OFFICIAL_BRAND_DOMAINS) is not None:
            image_row = kb.build_image_row(product_id=pid, url=image, provenance_host=host,
                                           source="retailer_jsonld", captured_at=self.now)
            if image_row is not None:
                self.writer.upsert(kb_ingest.KB_IMAGES_TABLE, [image_row], "product_id,url")
                filled.add("image")
        facts = price.get("_jsonld_facts")
        rating = facts.get("rating") if isinstance(facts, dict) else None
        if isinstance(rating, dict):
            count = rating.get("count")
            count = count if isinstance(count, int) and not isinstance(count, bool) and count > 0 else None
            review_row = kb.build_review_row(
                product_id=pid, source="retailer_jsonld", source_url=kb.canonical_offer_url(final_url),
                aggregate_rating=rating.get("value"), review_count=count, captured_at=self.now)
            if review_row is not None:
                self.writer.upsert(kb_ingest.KB_REVIEWS_TABLE, [review_row], "product_id,source_url")
                filled.add("rating")
                if count is not None:
                    filled.add("review_count")
        logger.info("%s product step=%s host=%s outcome=%s", PREFIX, step, host,
                    "filled" if filled else "empty")
        return filled

    # -- the gap ladder ------------------------------------------------------------
    async def ladder(self, pid: str, product: Dict[str, Any], fields: List[str]) -> None:
        for field in fields:
            if field in LICENCE_GAP_FIELDS:
                self.counts["licence"] += 1
                self.move(pid, field, "open", "licence")
        want = [f for f in fields if f in FETCH_GAP_FIELDS]
        if not want:
            return
        rows = self.merchants()
        by_host = common.rows_by_host(rows)
        filled: Set[str] = set()
        refusals: List[str] = []

        def done() -> bool:
            return set(want) <= filled

        # (1) the registry search template of live, ToS-allowed hosts
        search_rows = [r for r in rows if r.get("status") == "live" and isinstance(r.get("search_template"), str)
                       and "{q}" in r["search_template"] and isinstance(r.get("tos"), dict)
                       and r["tos"].get("verdict") == "allowed"]
        search_rows.sort(key=lambda r: (str(r.get("country") or "") != "BH", str(r.get("host") or "")))
        query = quote_plus("%s %s" % (product.get("brand") or "", product.get("name") or ""))
        for row in search_rows[:hosts_per_gap()]:
            if done():
                break
            url = row["search_template"].replace("{q}", query)
            outcome, res = await self.fetch("search", url, row)
            if outcome != "ok":
                refusals.append(outcome)
                continue
            for cand in search_candidates(res.body, res.url or url)[:CANDIDATES_PER_SEARCH]:
                got, page = await self.fetch("search", cand, row)
                if got != "ok":
                    refusals.append(got)
                    continue
                filled |= self.harvest("search", pid, product, row, page, cand)
                if done():
                    break

        # (2) the product's queued G2 pdp_ hints (R-G2-13)
        if not done():
            resp = (self.client.table(common.KB_GAPS_TABLE).select("product_key,field,state,source_hint")
                    .eq("product_key", pid).eq("state", "queued").execute())
            for hint in [h for h in _data(resp) if _is_hint(h.get("field"))]:
                if done():
                    break
                url = hint.get("source_hint")
                row = common.merchant_for_host(by_host, _host(url))
                outcome, res = await self.fetch("pdp_hint", url, row)
                if outcome == "ok":
                    filled |= self.harvest("pdp_hint", pid, product, row, res, str(url))
                    if self.move(pid, hint["field"], "queued", "closed"):
                        self.counts["hints_closed"] += 1
                    continue
                refusals.append(outcome)
                blocked = isinstance(row, dict) and row.get("status") == "blocked"
                if outcome == "refused:tos" or (outcome == "refused:not_live" and blocked):
                    self.move(pid, hint["field"], "queued", "needs_operator")

        missing = [f for f in want if f not in filled]
        # (3) web search: NOT BUILT in G4 (S81-21); the sub-flag only logs, once per run
        if missing and self.web and not self.counts["web_search_not_built"]:
            self.counts["web_search_not_built"] = 1
            logger.info("%s step=web_search status=not_built", PREFIX)
        for field in want:
            if field in filled:
                self.counts["filled"] += 1
                if self.move(pid, field, "open", "closed"):
                    self.counts["closed"] += 1
        # (4) refused everywhere for a blocked status or the ToS -> the operator queue
        if missing and refusals and all(r in OPERATOR_REFUSALS for r in refusals):
            for field in missing:
                if self.move(pid, field, "open", "needs_operator"):
                    self.counts["needs_operator"] += 1

    async def gaps_leg(self) -> None:
        queue = read_queue(self.client, self.now)
        self.counts["gaps"] = sum(len(e["fields"]) for e in queue)
        if not queue:
            return
        products = read_products(self.client, [e["product_key"] for e in queue])
        for entry in queue:
            pid = entry["product_key"]
            product = products.get(pid)
            if product is None:
                continue  # never a new identity minted from a page (S81-19-L5)
            key = self.acquire(pid)
            if key is None:
                continue
            try:
                await self.ladder(pid, product, entry["fields"])
            finally:
                self.release(key)

    async def refresh_leg(self) -> None:
        head, tail = refresh_order(self.client, self.now)
        order = head + tail
        if not order:
            return
        by_host = common.rows_by_host(self.merchants())
        products = read_products(self.client, order)
        cols = "variant_id,merchant_id,market,observed_currency,amount,canonical_url,last_seen,list_vs_sale,size_ml"
        for pid in order:
            product = products.get(pid)
            if product is None:
                continue
            key = self.acquire(pid)
            if key is None:
                continue
            try:
                resp = (self.client.table(common.KB_OFFERS_TABLE).select(cols)
                        .like("variant_id", pid + "|%").execute())
                latest: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
                for offer in _data(resp):
                    k = (offer.get("variant_id"), offer.get("merchant_id"), offer.get("market"),
                         offer.get("observed_currency"))
                    seen = _ts(offer.get("last_seen"))
                    prev = _ts(latest[k].get("last_seen")) if k in latest else None
                    if k not in latest or (seen is not None and (prev is None or seen > prev)):
                        latest[k] = offer
                for offer in latest.values():
                    row = common.merchant_for_host(by_host, offer.get("merchant_id"))
                    url = offer.get("canonical_url")
                    outcome, res = await self.fetch("refresh", url, row)
                    if outcome != "ok":
                        continue
                    self.counts["refresh_fetched"] += 1
                    self.harvest("refresh", pid, product, row, res, str(url), offer=offer)
            finally:
                self.release(key)


# ---------------------------------------------------------------------------
# DRY
# ---------------------------------------------------------------------------

def _spend_bound() -> Dict[str, Any]:
    try:
        from app.services import llm_spend_breaker as _br

        cap = float(_br.cap_usd(_br.LANE_OFFCLOCK))
    except Exception:  # noqa: BLE001 - the bound is informational
        cap = 0.0
    return {"lane": "offclock", "cap_usd": cap, "planned_usd": 0.0}


def dry_run(client: Any, now: datetime, legs: Set[str], report_path: Optional[str]) -> None:
    queue = read_queue(client, now) if "gaps" in legs else []
    head, tail = refresh_order(client, now) if "refresh" in legs else ([], [])
    spend = _spend_bound()
    report = {
        "queue": [{"product_key": e["product_key"], "fields": list(e["fields"]), "demand": e["demand"],
                   "last_seen": e["last"].isoformat()} for e in queue],
        "plan": [{"product_key": e["product_key"],
                  "licence": [f for f in e["fields"] if f in LICENCE_GAP_FIELDS],
                  "ladder": [f for f in e["fields"] if f in FETCH_GAP_FIELDS],
                  "steps": list(LADDER_STEPS)} for e in queue],
        "refresh": {"head": len(head), "tail": len(tail), "legs": sorted(legs)},
        "spend": spend,
    }
    for rank, entry in enumerate(queue, 1):
        logger.info("%s dry queue rank=%d demand=%d fields=%d", PREFIX, rank, entry["demand"], len(entry["fields"]))
    logger.info("%s dry refresh head=%d tail=%d", PREFIX, len(head), len(tail))
    logger.info("%s dry spend lane=offclock cap_usd=%.2f planned_usd=0.00", PREFIX, spend["cap_usd"])
    common.write_report(report_path, report)


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------

def _default_redis() -> Any:
    try:
        from app.services import cache_service

        return cache_service.redis_client
    except Exception:  # noqa: BLE001 - no Redis = every product lock_unavailable
        return None


def main(argv: Optional[List[str]] = None, client: Any = None, redis: Any = None) -> int:
    mode = enrich_mode()
    if mode == common.MODE_OFF:
        logger.info("%s mode=off %s not set; skipping run", PREFIX, FLAG)
        return 0
    parser = argparse.ArgumentParser(prog="cron_kb_enrich")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", default=None)
    parser.add_argument("--leg", choices=("all", "gaps", "refresh"), default="all")
    args = parser.parse_args(argv)
    mode = common.cli_mode(mode, args.dry_run)
    fill, web = gap_fill_enabled(), web_search_requested()
    logger.info("%s mode=%s gap_fill=%d web_search=%d", PREFIX, mode, int(fill), int(web))
    client = common.resolve_client(client, PREFIX)
    if client is None:
        return 0
    legs: Set[str] = set()
    if args.leg in ("all", "gaps") and fill:
        legs.add("gaps")
    if args.leg in ("all", "refresh"):
        legs.add("refresh")
    now = common._now()
    if mode == common.MODE_DRY:
        try:
            dry_run(client, now, legs, args.report)
        except Exception as exc:  # noqa: BLE001 - one WARNING, exit 0
            logger.warning("%s dry run failed (%s)", PREFIX, type(exc).__name__)
        return 0
    if redis is None:
        redis = _default_redis()
    run = EnrichRun(client, redis, now, web)

    async def _go() -> None:
        for leg, fn in (("gaps", run.gaps_leg), ("refresh", run.refresh_leg)):
            if leg not in legs:
                continue
            try:
                await fn()
            except Exception as exc:  # noqa: BLE001 - a failed leg ends, the run goes on
                logger.warning("%s leg=%s failed (%s)", PREFIX, leg, type(exc).__name__)

    asyncio.run(_go())
    logger.info("%s totals %s", PREFIX, " ".join("%s=%d" % (k, run.counts[k]) for k in TOTAL_KEYS))
    return 0


run = main

if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
