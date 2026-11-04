"""S81-17 KB-INGEST + D05 FIELD-STATUS: ONE off-loop knowledge-base ingest job per
successful compare, and the per-product field_status vocabulary.

Flags (new names, default OFF, read PER CALL, the price_service.exact_gate_enabled
idiom; independent of each other):

* ``ENABLE_KB_INGEST`` - at the two success exits (REST after the L3 moderation
  pass, before ``return result``; stream after it, before the ``settle_complete``
  yield; the camera path through the REST exit) the orchestrator builds a
  plain-data projection on the loop (:func:`build_job`, no I/O) and hands
  :func:`run_job` to ONE ``asyncio.to_thread`` inside ONE fire-and-forget task
  (label ``kb_ingest``), never awaited by the response.
* ``ENABLE_FIELD_STATUS_METADATA`` - the additive ``metadata.field_status`` key
  only (:func:`field_status`, the closed 2.2 vocabulary).

Knob: ``KB_INGEST_GAP_MAX`` (16, clamped 1..64): the most kb_gaps rows one job
writes.

The job (a worker thread) writes ONLY through the S81-14 builders with the
service-role client, insert-ignore: kb_products / kb_variants at identity
confidence high; kb_offers for a genuine non-render method on a live registry
host whose PERSISTED robots verdict allows the price URL (live_robots.url_verdict,
flag-free), market BH; kb_images (the page image under the D08 image policy);
kb_reviews (channel-1 JSON-LD aggregates only); kb_gaps for the unknown D05 fields
of an identity high or medium product (insert-ignore, then compare-and-set
demand_count). Never kb_specs, kb_feedback or the merchant registry; no LLM call, no
Serper call, no fetch; no request-context read. One INFO count line per job,
ints only.

Test seams (module attributes read at call time): ``_now`` (aware datetime) and
``_admin_client`` (called to obtain the service-role client).
"""
from __future__ import annotations

import copy
import logging
import math
import os
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.services import deny_hosts, jsonld_widen
from app.services import result_gate as _rg

logger = logging.getLogger(__name__)

KB_PRODUCTS_TABLE = "kb_products"
KB_VARIANTS_TABLE = "kb_variants"
KB_OFFERS_TABLE = "kb_offers"
KB_IMAGES_TABLE = "kb_images"
KB_REVIEWS_TABLE = "kb_reviews"
KB_GAPS_TABLE = "kb_gaps"

_TRUTHY = ("true", "1", "yes", "on")

#: The D05 fields, in the order every field_status entry carries them.
D05_FIELDS: Tuple[str, ...] = (
    "identity", "image", "price", "size", "concentration", "specs", "rating", "review_count",
)
#: The evidence rung of a source method (None: converted, render tiers, estimates).
_PAGE_EVIDENCE_METHODS = frozenset({"page_scrape", "page_scrape_jsonld", "local_bhd"})
_PLATFORM_API_METHODS = frozenset({
    "shopify_json", "woo_store_api", "salla_api", "occ_rest_bhd", "magento_graphql_bhd",
    "rest_json_bhd",
})
_GAP_RESERVED_PREFIX = "pdp_"  # the G2 kb_gaps namespace (R-G2-13): never written here
_GAP_DEFAULT = 16
_GAP_MIN = 1
_GAP_MAX = 64
_ML_RE = re.compile(r"^\s*(\d{1,5})\s*ml\s*$", re.IGNORECASE)
_COUNT_KEYS: Tuple[str, ...] = (
    "products", "variants", "offers", "offer_updates", "images", "reviews", "gaps",
    "gap_increments", "gap_cas_lost", "not_built",
)


# --------------------------------------------------------------------------- flags
def kb_ingest_enabled() -> bool:
    """True iff ``ENABLE_KB_INGEST`` is truthy. Read PER CALL."""
    return os.getenv("ENABLE_KB_INGEST", "false").strip().lower() in _TRUTHY


def field_status_metadata_enabled() -> bool:
    """True iff ``ENABLE_FIELD_STATUS_METADATA`` is truthy. Read PER CALL."""
    return os.getenv("ENABLE_FIELD_STATUS_METADATA", "false").strip().lower() in _TRUTHY


def gap_max() -> int:
    """``KB_INGEST_GAP_MAX``: default 16, clamped 1..64; unset, blank, garbage, inf,
    nan or <= 0 fall back to the default."""
    raw = os.getenv("KB_INGEST_GAP_MAX")
    if raw is None:
        return _GAP_DEFAULT
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return _GAP_DEFAULT
    if not math.isfinite(value) or value <= 0:
        return _GAP_DEFAULT
    return int(min(max(value, _GAP_MIN), _GAP_MAX))


# --------------------------------------------------------------------------- seams
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _admin_client() -> Any:
    from app.services.database_service import get_admin_supabase_client

    return get_admin_supabase_client()


def kb_leaf() -> Any:
    """The S81-14 leaf, imported here only (the P01 rule: one function-local import)."""
    from app.services import kb_service as _kb
    return _kb


# --------------------------------------------------------------------------- helpers
def rung_for(method: Any) -> Optional[str]:
    """The KB evidence rung of a price source method, or None."""
    if method in _PAGE_EVIDENCE_METHODS:
        return "page_evidence"
    if method in _PLATFORM_API_METHODS:
        return "platform_api"
    return None


def _iso_z(moment: Any) -> Optional[str]:
    if not isinstance(moment, datetime) or moment.tzinfo is None:
        return None
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _url_host(url: Any) -> str:
    return deny_hosts.normalize_host(jsonld_widen._url_host(url)) if isinstance(url, str) else ""


def _size_ml(price: Dict[str, Any]) -> Optional[int]:
    match = _ML_RE.match(str(price.get("size") or ""))
    if not match:
        return None
    ml = int(match.group(1))
    return ml if 1 <= ml <= 9999 else None


def _item(state: str, source: Optional[str] = None, reason: Optional[str] = None
          ) -> Dict[str, Any]:
    return {"state": state, "source": source, "reason": reason}


def _is_fragrance(category: Any, kb: Any) -> bool:
    return isinstance(category, str) and category.strip().lower() == kb.KB_CATEGORY


# --------------------------------------------------------------------------- D05
def _status_one(product: Dict[str, Any], captured_at: Any, vision: bool) -> Dict[str, Any]:
    from app.services.price_service import OFFICIAL_BRAND_DOMAINS

    kb = kb_leaf()
    price = _dict(product.get("price"))
    specs = _dict(product.get("specs"))
    tier3 = _rg._tier3_fields(specs)
    out: Dict[str, Any] = {}

    id_source = "vision" if vision else "parse"
    if _rg.product_is_placeholder({"brand": product.get("brand"), "name": product.get("name")}):
        out["identity"] = _item("unknown", id_source, "placeholder_identity")
    elif kb.kb_product_id(product.get("brand"), product.get("name"),
                         product.get("variant")) is None:
        out["identity"] = _item("unknown", id_source, "no_product_id")
    else:
        out["identity"] = _item("known", id_source)

    served = product.get("image_url")
    if isinstance(served, str) and served.strip().lower().startswith("https://"):
        page_image = price.get("image_url")
        on_page = (isinstance(page_image, str) and served == page_image
                   and jsonld_widen.allowed_image_url(
                       page_image, price.get("url"), OFFICIAL_BRAND_DOMAINS) is not None)
        out["image"] = _item("known", "retailer_page" if on_page else "search")
    else:
        out["image"] = _item("unknown", None, "no_image")

    if _rg.price_is_showable(price):
        host = _url_host(price.get("url")) or None
        rung = rung_for(price.get("source_method"))
        if price.get("_cached") is False:
            entry = _item("fresh", host)
            entry.update(as_of=_iso_z(captured_at), rung=rung)
        else:
            reason = "served_from_cache" if price.get("_cached") is True else "unmarked"
            entry = _item("stale", host, reason)
            entry.update(as_of=None, rung=rung)
    else:
        estimated = price.get("estimated") is True or price.get("source_method") == "estimated"
        entry = _item("unknown", None, "estimated" if estimated else "no_price")
        entry.update(as_of=None, rung=None)
    out["price"] = entry

    volume = specs.get("volume")
    if _size_ml(price) is not None:
        out["size"] = _item("known", "listing")
    elif not _rg._is_na(volume) and "volume" not in tier3:
        out["size"] = _item("known", "specs")
    elif not _rg._is_na(volume):
        out["size"] = _item("unknown", None, "model_knowledge")
    else:
        out["size"] = _item("unknown", None, "no_size")

    concentration = specs.get("concentration")
    if not _rg._is_na(concentration) and "concentration" not in tier3:
        out["concentration"] = _item("known", "specs")
    elif not _rg._is_na(concentration):
        out["concentration"] = _item("unknown", None, "model_knowledge")
    else:
        out["concentration"] = _item("unknown", None, "no_concentration")

    present = [k for k, v in specs.items() if not str(k).startswith("_") and not _rg._is_na(v)]
    if any(k not in tier3 for k in present):
        out["specs"] = _item("known", "search")
    elif present:
        out["specs"] = _item("unknown", None, "model_knowledge")
    else:
        out["specs"] = _item("unknown", None, "no_specs")

    rating_source = "retailer_jsonld" if isinstance(product.get("jsonld_rating"), dict) else "provider"
    if _rg.rating_is_real(product):
        out["rating"] = _item("known", rating_source)
    elif product.get("rating_derived") is True:
        out["rating"] = _item("unknown", None, "derived_rating")
    else:
        out["rating"] = _item("unknown", None, "no_rating")

    count = product.get("review_count")
    if isinstance(count, int) and not isinstance(count, bool) and count > 0:
        out["review_count"] = _item("known", rating_source)
    else:
        out["review_count"] = _item("unknown", None, "no_review_count")
    return out


def field_status(product_data: Any, result: Any, *, captured_at: Any, vision: bool = False
                 ) -> List[Dict[str, Any]]:
    """D05: per product (the body's order) {field: {state, source, reason}} for the
    eight D05 fields; ``price`` also carries ``as_of`` (ISO-8601 Z or None) and
    ``rung``. Pure; the closed 2.2 vocabulary; never a name, URL or free text
    (the price source is the normalized price host). ``result`` is accepted for the
    contract and not read."""
    products = list(product_data or [])[:2]
    return [_status_one(p if isinstance(p, dict) else {}, captured_at, bool(vision))
            for p in products]


# --------------------------------------------------------------------------- the job
_PRICE_KEYS: Tuple[str, ...] = (
    "amount", "currency", "url", "source_method", "estimated", "_cached", "size", "image_url",
    "in_stock", "_cache_source",
)


def build_job(result: Any, product_data: Any, *, product_categories: Any, region: Any,
              vision: Any, captured_at: Any) -> Dict[str, Any]:
    """The plain-data, deep-copied projection the worker thread writes from. Runs on
    the loop: pure, no I/O. ``identity_confidence`` is the PAIR value of
    result_gate.assess_result (flag-free)."""
    assessment = _rg.assess_result(result, product_categories=product_categories)
    statuses = field_status(product_data, result, captured_at=captured_at, vision=bool(vision))
    products = []
    for product, status in zip(list(product_data or [])[:2], statuses):
        product = product if isinstance(product, dict) else {}
        price = _dict(product.get("price"))
        facts = price.get("_jsonld_facts")
        rating = product.get("jsonld_rating")
        products.append({
            "brand": product.get("brand"),
            "name": product.get("name"),
            "variant": product.get("variant"),
            "category": product.get("category"),
            "price": {key: copy.deepcopy(price.get(key)) for key in _PRICE_KEYS},
            "jsonld_facts": copy.deepcopy(facts) if isinstance(facts, dict) else None,
            "jsonld_rating": copy.deepcopy(rating) if isinstance(rating, dict) else None,
            "field_status": copy.deepcopy(status),
        })
    return {
        "captured_at": captured_at,
        "region": region,
        "identity_confidence": _dict(assessment).get("identity_confidence"),
        "products": products,
        "field_status": copy.deepcopy(statuses),
    }


def _norm_key_value(column: str, value: Any) -> str:
    """GC-6: a numeric observation column compares through Decimal (PostgREST
    returns ``amount`` as a number, the builder sends a 3-place string)."""
    if column == "amount" and value is not None and not isinstance(value, bool):
        try:
            return str(Decimal(str(value)).normalize())
        except (InvalidOperation, ValueError):
            return str(value)
    return str(value)


def _row_key(row: Dict[str, Any], columns: Iterable[str]) -> Tuple[str, ...]:
    return tuple(_norm_key_value(c, row.get(c)) for c in columns)


def _insert_ignore(client: Any, table: str, rows: List[Dict[str, Any]],
                   conflict: Tuple[str, ...]) -> List[Dict[str, Any]]:
    if not rows:
        return []
    resp = client.table(table).upsert(
        rows, on_conflict=",".join(conflict), ignore_duplicates=True).execute()
    data = getattr(resp, "data", None)
    return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []


def _offer_rows_changed(client: Any, kb: Any, sent: List[Dict[str, Any]],
                        returned: List[Dict[str, Any]], counts: Dict[str, int]) -> None:
    """Every offer the insert did not return is a re-observation: ONE update of
    KB_OFFER_UPSERT_SET filtered on the observation key."""
    observed = kb.KB_OFFER_OBSERVATION_KEY
    inserted = {_row_key(r, observed) for r in returned}
    for row in sent:
        if _row_key(row, observed) in inserted:
            continue
        query = client.table(KB_OFFERS_TABLE).update(
            {col: row[col] for col in kb.KB_OFFER_UPSERT_SET})
        for col in observed:
            query = query.eq(col, row[col])
        query.execute()
        counts["offer_updates"] += 1


def _bump_gaps(client: Any, gaps: List[Dict[str, Any]], returned: List[Dict[str, Any]],
               last_seen_iso: Optional[str], counts: Dict[str, int]) -> None:
    """For the gap rows the insert did not return: ONE select, then per existing row
    ONE compare-and-set update of demand_count + last_seen; a lost race is counted,
    never retried. state / source_hint / first_seen never move."""
    key_cols = ("product_key", "field")
    inserted = {_row_key(r, key_cols) for r in returned}
    missing = [g for g in gaps if _row_key(g, key_cols) not in inserted]
    if not missing:
        return
    resp = (
        client.table(KB_GAPS_TABLE)
        .select("product_key,field,demand_count,state")
        .in_("product_key", sorted({g["product_key"] for g in missing}))
        .in_("field", sorted({g["field"] for g in missing}))
        .execute()
    )
    data = getattr(resp, "data", None)
    existing = {_row_key(r, key_cols): r for r in (data if isinstance(data, list) else [])
                if isinstance(r, dict)}
    for gap in missing:
        current = existing.get(_row_key(gap, key_cols))
        n = current.get("demand_count") if isinstance(current, dict) else None
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            continue
        out = (
            client.table(KB_GAPS_TABLE)
            .update({"demand_count": n + 1, "last_seen": last_seen_iso})
            .eq("product_key", gap["product_key"])
            .eq("field", gap["field"])
            .eq("demand_count", n)
            .execute()
        )
        if getattr(out, "data", None):
            counts["gap_increments"] += 1
        else:
            counts["gap_cas_lost"] += 1


def run_job(snap: Dict[str, Any]) -> None:
    """The worker-thread job (never on the loop). Raises only what the client raises
    (the fire-and-forget done-callback logs it as one WARNING)."""
    started = time.monotonic()
    counts = dict.fromkeys(_COUNT_KEYS, 0)
    client = _admin_client()
    if client is None:
        logger.warning("[KB_INGEST] no service-role client")
        return
    from app.services import live_robots
    from app.services.price_service import OFFICIAL_BRAND_DOMAINS, _GENUINE_BH_SOURCE_METHODS

    kb = kb_leaf()
    records = live_robots.records_snapshot()
    if records is None:
        records = live_robots.load_records_sync(client)
    captured = snap.get("captured_at")
    confidence = snap.get("identity_confidence")
    limit = gap_max()
    rows: Dict[str, List[Dict[str, Any]]] = {t: [] for t in (
        KB_PRODUCTS_TABLE, KB_VARIANTS_TABLE, KB_OFFERS_TABLE, KB_IMAGES_TABLE,
        KB_REVIEWS_TABLE, KB_GAPS_TABLE)}

    def _add(table: str, row: Optional[Dict[str, Any]]) -> None:
        if row is None:
            counts["not_built"] += 1
        else:
            rows[table].append(row)

    if confidence in ("high", "medium"):
        for product in snap.get("products") or []:
            if not isinstance(product, dict) or not _is_fragrance(product.get("category"), kb):
                continue
            pid = kb.kb_product_id(product.get("brand"), product.get("name"),
                                   product.get("variant"))
            if pid is None:
                continue
            price = _dict(product.get("price"))
            url = price.get("url")
            host = _url_host(url)
            row = live_robots.match_row(records, host) if host else None
            allowed = (isinstance(url, str) and isinstance(row, dict)
                       and live_robots.url_verdict(url, row, captured) is None)

            if confidence == "high":
                conc = pid.split("|")[3]
                conc = conc if conc in kb.kb_concentrations() else None
                _add(KB_PRODUCTS_TABLE, kb.build_product_row(
                    id=pid, brand=product.get("brand"), name=product.get("name"),
                    identity_confidence="high", updated_at=captured, concentration=conc))
                size_ml = _size_ml(price)
                vid = kb.kb_variant_key(pid, conc, size_ml)
                facts = _dict(product.get("jsonld_facts"))
                gtin = facts.get("gtin") if kb.gtin_check_digit_ok(facts.get("gtin")) else None
                sku = facts.get("sku") if isinstance(facts.get("sku"), str) else None
                _add(KB_VARIANTS_TABLE, kb.build_variant_row(
                    id=vid, product_id=pid, updated_at=captured, concentration=conc,
                    size_ml=size_ml, gtin=gtin, sku=sku))

                method = price.get("source_method")
                rung = rung_for(method)
                canonical = kb.canonical_offer_url(url)
                if (method in _GENUINE_BH_SOURCE_METHODS and rung is not None
                        and price.get("estimated") is not True and canonical is not None
                        and allowed and snap.get("region") == "bahrain" and vid is not None
                        and price.get("_cache_source") != "kb"):  # S81-18 C4: never re-observe a KB price
                    stock = price.get("in_stock")
                    _add(KB_OFFERS_TABLE, kb.build_offer_row(
                        variant_id=vid, merchant_id=row.get("host"), market="BH",
                        amount=price.get("amount"), observed_currency=price.get("currency"),
                        evidence_rung=rung, canonical_url=canonical, captured_at=captured,
                        size_ml=size_ml, in_stock=stock if isinstance(stock, bool) else None))

                image = price.get("image_url")
                if (isinstance(image, str) and allowed and jsonld_widen.allowed_image_url(
                        image, url, OFFICIAL_BRAND_DOMAINS) is not None):
                    _add(KB_IMAGES_TABLE, kb.build_image_row(
                        product_id=pid, url=image, provenance_host=host,
                        source="retailer_jsonld" if product.get("jsonld_facts") else "retailer_og",
                        captured_at=captured))

                rating = product.get("jsonld_rating")
                if isinstance(rating, dict):
                    review_count = rating.get("count")
                    if not isinstance(review_count, int) or isinstance(review_count, bool):
                        review_count = None
                    _add(KB_REVIEWS_TABLE, kb.build_review_row(
                        product_id=pid, source="retailer_jsonld", source_url=rating.get("url"),
                        aggregate_rating=rating.get("value"), review_count=review_count,
                        captured_at=captured))

            blocked = isinstance(row, dict) and row.get("status") == "blocked"
            hint = row.get("host") if isinstance(row, dict) else None
            status = _dict(product.get("field_status"))
            for field in D05_FIELDS:
                if field == "identity" or field.startswith(_GAP_RESERVED_PREFIX):
                    continue
                if _dict(status.get(field)).get("state") != "unknown":
                    continue
                if len(rows[KB_GAPS_TABLE]) >= limit:
                    break
                _add(KB_GAPS_TABLE, kb.build_gap_row(
                    product_key=pid, field=field, first_seen=captured, demand_count=1,
                    state="needs_operator" if blocked else "open", source_hint=hint))

    counts["products"] = len(_insert_ignore(
        client, KB_PRODUCTS_TABLE, rows[KB_PRODUCTS_TABLE], ("id",)))
    counts["variants"] = len(_insert_ignore(
        client, KB_VARIANTS_TABLE, rows[KB_VARIANTS_TABLE], ("id",)))
    offers = _insert_ignore(client, KB_OFFERS_TABLE, rows[KB_OFFERS_TABLE],
                            tuple(kb.KB_OFFER_OBSERVATION_KEY))
    counts["offers"] = len(offers)
    _offer_rows_changed(client, kb, rows[KB_OFFERS_TABLE], offers, counts)
    counts["images"] = len(_insert_ignore(
        client, KB_IMAGES_TABLE, rows[KB_IMAGES_TABLE], ("product_id", "url")))
    counts["reviews"] = len(_insert_ignore(
        client, KB_REVIEWS_TABLE, rows[KB_REVIEWS_TABLE], ("product_id", "source_url")))
    gaps = _insert_ignore(client, KB_GAPS_TABLE, rows[KB_GAPS_TABLE], ("product_key", "field"))
    counts["gaps"] = len(gaps)
    _bump_gaps(client, rows[KB_GAPS_TABLE], gaps, kb._ts_iso(captured), counts)
    logger.info(
        "[KB_INGEST] job products=%d variants=%d offers=%d offer_updates=%d images=%d "
        "reviews=%d gaps=%d gap_increments=%d gap_cas_lost=%d not_built=%d elapsed_ms=%d",
        counts["products"], counts["variants"], counts["offers"], counts["offer_updates"],
        counts["images"], counts["reviews"], counts["gaps"], counts["gap_increments"],
        counts["gap_cas_lost"], counts["not_built"],
        int((time.monotonic() - started) * 1000),
    )
