"""D16 OPERATOR-INGEST: the operator view and the captured-payload ingest for the
knowledge base (two admin JSON routes in app/api/admin_routes.py).

Flag ``ENABLE_OPERATOR_INGEST`` (new name, default OFF, read PER CALL, the house
boolean idiom). Knob ``KB_OPERATOR_PAGE_MAX`` (50, clamped 1..200; unset, blank,
garbage, inf, nan or <= 0 fall back to 50): the page size of the view.

Flag OFF: :func:`operator_gate`, declared as the FIRST dependency of both routes,
raises the Starlette base-class 404, so ``GET /api/v1/admin/kb/operator`` and
``POST /api/v1/admin/kb/ingest`` answer exactly what an unregistered path answers
(``{"detail": "Not Found"}``): the admin-key dependency, the body handler and the
service-role client are never reached. Both routes are ``include_in_schema=False``.

Flag ON (behind the EXISTING ``verify_admin_key`` dependency and the existing
30/min limiter):

* :func:`read_view` - the blocked registry hosts (robots state / fetched_at, the
  ToS verdict / reviewed_at), the ``needs_operator`` gaps by demand, and the
  latest kb_coverage_daily day; bounded pages; no user, device or query field
  exists in these tables.
* :func:`ingest` - a payload the operator captured in their own browser (the
  bookmarklet of docs/runbooks/2026-11-kb-operator-ingest.md copies it to the
  clipboard; it never posts): the URL belts, the registry row (live, or blocked
  WITH ``tos.reviewed_at``), the identity, then builder rows only (insert-ignore),
  then ONE compare-and-set close of the matching open / needs_operator gaps.
  The licence spec fields (``kb_serve.LICENCE_FIELDS``) are accepted only from
  ``source == "partner"`` (R-G4-7). Refusals raise :class:`OperatorRefusal`
  with one of the ``KB_*`` codes; the route answers 400 (never a bare 503).
  A ``captured_at`` later than now + ``kb_serve.FUTURE_SKEW_SECONDS`` fails body
  validation (the existing 422 ``VALIDATION_ERROR``; D16b).

Test seams (module attributes read at call time): ``_now`` and ``_admin_client``.
Log lines carry constants, the registry host and ints only.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

KB_SPECS_TABLE = "kb_specs"
KB_COVERAGE_TABLE = "kb_coverage_daily"

_TRUTHY = ("true", "1", "yes", "on")
_PAGE_DEFAULT = 50
_PAGE_MIN = 1
_PAGE_MAX = 200
MAX_PAYLOAD_BYTES = 262_144
COVERAGE_ROWS_MAX = 200
SOURCE_OPERATOR = "operator"
SOURCE_PARTNER = "partner"
_SPEC_FIELD_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

#: The refusal codes (each a 400 with the house envelope) and their constant texts.
REFUSALS: Dict[str, str] = {
    "KB_URL_REFUSED": "The page URL is not accepted.",
    "KB_HOST_UNKNOWN": "The page host is not in the merchant registry.",
    "KB_HOST_CANDIDATE": "The page host is a registry candidate.",
    "KB_HOST_NOT_REVIEWED": "The blocked host has no reviewed terms record.",
    "KB_IDENTITY_UNRESOLVED": "The product identity could not be resolved.",
    "KB_PAYLOAD_TOO_LARGE": "The payload is too large.",
    "KB_STORE_UNAVAILABLE": "The knowledge base store is unavailable.",
    "KB_LICENCE_FIELD": "A licensed spec field needs the partner source.",
}


class OperatorRefusal(Exception):
    """An ingest refusal: ``code`` is one of :data:`REFUSALS`."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def detail(self) -> Dict[str, str]:
        return {"code": self.code, "error": REFUSALS.get(self.code, "Refused.")}


# --------------------------------------------------------------------------- flag, knob
def operator_ingest_enabled() -> bool:
    """True iff ``ENABLE_OPERATOR_INGEST`` is truthy. Read PER CALL."""
    return os.getenv("ENABLE_OPERATOR_INGEST", "false").strip().lower() in _TRUTHY


def page_max() -> int:
    """``KB_OPERATOR_PAGE_MAX``: 50, clamped 1..200; unusable -> 50."""
    raw = os.getenv("KB_OPERATOR_PAGE_MAX")
    if raw is None:
        return _PAGE_DEFAULT
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return _PAGE_DEFAULT
    if not math.isfinite(value) or value <= 0:
        return _PAGE_DEFAULT
    return int(min(max(value, _PAGE_MIN), _PAGE_MAX))


def page_limit(raw: Any) -> int:
    """The view's ``limit`` query value: an int clamped 1..page_max(); anything
    else -> page_max()."""
    cap = page_max()
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return cap
    return min(max(value, 1), cap)


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


# --------------------------------------------------------------------------- the gate
def operator_gate() -> None:
    """The FIRST dependency of both routes: flag OFF raises the Starlette base-class
    404, rendered exactly like an unregistered path."""
    if not operator_ingest_enabled():
        raise StarletteHTTPException(status_code=404)
    return None


# --------------------------------------------------------------------------- models
class OperatorPrice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float = Field(gt=0, lt=1e11)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class OperatorIngest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["operator", "partner"] = "operator"
    page_url: str = Field(min_length=1, max_length=2048)
    brand: Optional[str] = Field(default=None, min_length=1, max_length=128)
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    variant: Optional[str] = Field(default=None, min_length=1, max_length=64)
    jsonld: List[Dict[str, Any]] = Field(default_factory=list, max_length=20)
    og_image: Optional[str] = Field(default=None, max_length=2048)
    price: Optional[OperatorPrice] = None
    market: str = Field(default="BH", pattern=r"^[A-Z]{2,3}$")
    size_ml: Optional[int] = Field(default=None, ge=1, le=9999)
    in_stock: Optional[bool] = None
    captured_at: Optional[datetime] = None
    specs: Dict[str, str] = Field(default_factory=dict, max_length=32)

    @field_validator("specs")
    @classmethod
    def _specs_shape(cls, value: Dict[str, str]) -> Dict[str, str]:
        for key, text in value.items():
            if not _SPEC_FIELD_RE.match(key):
                raise ValueError("spec field name")
            if not 1 <= len(text) <= 2000:
                raise ValueError("spec value length")
        return value

    @field_validator("captured_at")
    @classmethod
    def _captured_at_not_future(cls, value: Optional[datetime]) -> Optional[datetime]:
        # D16b: a capture later than now + kb_serve.FUTURE_SKEW_SECONDS is refused
        # (ValueError -> the existing 422 VALIDATION_ERROR). A naive value is read
        # as UTC, as _aware does; the clock is the module seam _now.
        if value is None:
            return value
        from app.services import kb_serve

        moment = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        if kb_serve.beyond_skew(moment, _now()):
            raise ValueError("captured_at is in the future")
        return value


def payload_too_large(body: OperatorIngest) -> bool:
    try:
        size = len(json.dumps(body.model_dump(mode="json"), ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError):
        return True
    return size > MAX_PAYLOAD_BYTES


def licence_violation(body: OperatorIngest) -> bool:
    """R-G4-7: a licence spec field from any source but ``partner``."""
    from app.services import kb_serve

    if body.source == SOURCE_PARTNER:
        return False
    return any(field in kb_serve.LICENCE_FIELDS for field in body.specs)


# --------------------------------------------------------------------------- the view
def _data(resp: Any) -> List[Dict[str, Any]]:
    data = getattr(resp, "data", None)
    return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []


def _obj(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def read_view(client: Any, limit: int) -> Dict[str, Any]:
    """The operator view (sync; the route runs it through run_db)."""
    from app.services import kb_ingest, merchant_registry

    blocked = []
    resp = (client.table(merchant_registry.KB_MERCHANTS_TABLE).select("host,status,blocked_reason,robots,tos")
            .eq("status", "blocked").order("host").limit(limit).execute())
    for row in _data(resp):
        robots, tos = _obj(row.get("robots")), _obj(row.get("tos"))
        blocked.append({
            "host": row.get("host"), "status": row.get("status"), "blocked_reason": row.get("blocked_reason"),
            "robots_state": robots.get("state"), "robots_fetched_at": robots.get("fetched_at"),
            "tos_verdict": tos.get("verdict"), "tos_reviewed_at": tos.get("reviewed_at"),
        })
    resp = (client.table(kb_ingest.KB_GAPS_TABLE)
            .select("product_key,field,demand_count,last_seen,source_hint")
            .eq("state", "needs_operator").order("demand_count", desc=True).order("last_seen", desc=True)
            .limit(limit).execute())
    needs = [{k: row.get(k) for k in ("product_key", "field", "demand_count", "last_seen", "source_hint")}
             for row in _data(resp)]
    latest = _data(client.table(KB_COVERAGE_TABLE).select("day").order("day", desc=True).limit(1).execute())
    day = latest[0].get("day") if latest else None
    metrics: List[Dict[str, Any]] = []
    if day is not None:
        resp = (client.table(KB_COVERAGE_TABLE).select("metric,value,n").eq("day", day)
                .order("metric").limit(COVERAGE_ROWS_MAX).execute())
        metrics = [{k: row.get(k) for k in ("metric", "value", "n")} for row in _data(resp)]
    return {"blocked": blocked, "needs_operator": needs, "coverage": {"day": day, "metrics": metrics},
            "limit": limit}


# --------------------------------------------------------------------------- the ingest
def _registry_row(client: Any, host: str) -> Optional[Dict[str, Any]]:
    """The exact host's row, else the row of its longest registered parent (ONE
    select over the host and its parent domains)."""
    from app.services import merchant_registry

    labels = host.split(".")
    candidates = [".".join(labels[i:]) for i in range(len(labels) - 1)]
    rows = _data(client.table(merchant_registry.KB_MERCHANTS_TABLE).select("host,status,deny,tos")
                 .in_("host", candidates).execute())
    by_host = {str(r.get("host") or "").strip().lower(): r for r in rows}
    for cand in candidates:  # longest first
        if cand in by_host:
            return by_host[cand]
    return None


def _jsonld_identity(nodes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The first JSON-LD node whose @type is or contains Product (one @graph level)."""
    flat: List[Dict[str, Any]] = []
    for node in nodes:
        flat.append(node)
        graph = node.get("@graph")
        if isinstance(graph, list):
            flat.extend(g for g in graph if isinstance(g, dict))
    for node in flat:
        kind = node.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if "Product" not in kinds:
            continue
        brand = node.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")
        if isinstance(brand, list) and brand:
            first = brand[0]
            brand = first.get("name") if isinstance(first, dict) else first
        return {"brand": brand if isinstance(brand, str) else None,
                "name": node.get("name") if isinstance(node.get("name"), str) else None}
    return None


def _aware(moment: Optional[datetime], fallback: datetime) -> datetime:
    if not isinstance(moment, datetime):
        return fallback
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def ingest(client: Any, body: OperatorIngest, now: datetime) -> Dict[str, int]:
    """Validate, then write builder rows insert-ignore and close the matching gaps
    (sync; the route runs it through run_db). Raises :class:`OperatorRefusal`
    before any write; a raising client call propagates (the route maps it to
    KB_STORE_UNAVAILABLE)."""
    from app.services import deny_hosts, kb_ingest

    kb = kb_leaf()
    # (1) the URL belts
    canonical = kb.canonical_offer_url(body.page_url)
    if canonical is None or not kb.kb_source_allowed(canonical) or deny_hosts.is_denied_url(body.page_url):
        raise OperatorRefusal("KB_URL_REFUSED")
    host = kb_ingest._url_host(canonical)
    if not host:
        raise OperatorRefusal("KB_URL_REFUSED")
    # (2) the registry row
    row = _registry_row(client, host)
    if row is None:
        raise OperatorRefusal("KB_HOST_UNKNOWN")
    if row.get("deny"):
        raise OperatorRefusal("KB_URL_REFUSED")
    status = row.get("status")
    if status == "candidate":
        raise OperatorRefusal("KB_HOST_CANDIDATE")
    if status == "blocked":
        reviewed = _obj(row.get("tos")).get("reviewed_at")
        if not (isinstance(reviewed, str) and reviewed.strip()):
            raise OperatorRefusal("KB_HOST_NOT_REVIEWED")
    elif status != "live":
        raise OperatorRefusal("KB_HOST_UNKNOWN")
    merchant = str(row.get("host") or "").strip().lower()
    # (3) the identity
    if body.brand and body.name:
        brand, name = body.brand, body.name
    else:
        found = _jsonld_identity(body.jsonld) or {}
        brand, name = found.get("brand"), found.get("name")
    pid = kb.kb_product_id(brand, name, body.variant)
    if pid is None:
        raise OperatorRefusal("KB_IDENTITY_UNRESOLVED")

    # (4) builder rows only
    captured = _aware(body.captured_at, now)
    conc = pid.split("|")[3]
    conc = conc if conc in kb.kb_concentrations() else None
    counts = {"products": 0, "variants": 0, "offers": 0, "images": 0, "specs": 0, "gaps_closed": 0,
              "not_built": 0}
    filled: List[str] = []

    def built(row_out: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if row_out is None:
            counts["not_built"] += 1
            return []
        return [row_out]

    products = built(kb.build_product_row(id=pid, brand=brand, name=name, identity_confidence="high",
                                          updated_at=now, concentration=conc))
    vid = kb.kb_variant_key(pid, conc, body.size_ml)
    variants = built(kb.build_variant_row(id=vid, product_id=pid, updated_at=now, concentration=conc,
                                          size_ml=body.size_ml)) if vid is not None else []
    offers: List[Dict[str, Any]] = []
    if body.price is not None and vid is not None:
        offers = built(kb.build_offer_row(
            variant_id=vid, merchant_id=merchant, market=body.market, amount=body.price.amount,
            observed_currency=body.price.currency, evidence_rung="operator", canonical_url=canonical,
            captured_at=captured, size_ml=body.size_ml, in_stock=body.in_stock))
    images: List[Dict[str, Any]] = []
    if isinstance(body.og_image, str) and body.og_image.startswith("https://"):
        images = built(kb.build_image_row(product_id=pid, url=body.og_image, provenance_host=merchant,
                                          source="operator", captured_at=captured))
    specs: List[Dict[str, Any]] = []
    for field, value in body.specs.items():
        specs.extend(built(kb.build_spec_row(product_id=pid, field=field, value=value, extractor="operator",
                                             captured_at=captured, lang="en", source_url=canonical, cited=True)))

    kb_ingest._insert_ignore(client, kb_ingest.KB_PRODUCTS_TABLE, products, ("id",))
    kb_ingest._insert_ignore(client, kb_ingest.KB_VARIANTS_TABLE, variants, ("id",))
    returned = kb_ingest._insert_ignore(client, kb_ingest.KB_OFFERS_TABLE, offers,
                                        tuple(kb.KB_OFFER_OBSERVATION_KEY))
    reobserved = {"offer_updates": 0}
    kb_ingest._offer_rows_changed(client, kb, offers, returned, reobserved)
    kb_ingest._insert_ignore(client, kb_ingest.KB_IMAGES_TABLE, images, ("product_id", "url"))
    kb_ingest._insert_ignore(client, KB_SPECS_TABLE, specs, ("product_id", "field", "lang"))
    counts.update(products=len(products), variants=len(variants), offers=len(offers), images=len(images),
                  specs=len(specs))

    # (5) close the matching open / needs_operator gaps (never a pdp_ hint, never demand)
    if offers:
        filled.append("price")
    if images:
        filled.append("image")
    if variants and body.size_ml is not None:
        filled.append("size")
    if conc is not None:
        filled.append("concentration")
    if specs:
        filled.append("specs")
    if filled:
        resp = (client.table(kb_ingest.KB_GAPS_TABLE).update({"state": "closed"})
                .eq("product_key", pid).in_("field", filled).in_("state", ["open", "needs_operator"])
                .execute())
        counts["gaps_closed"] = len(_data(resp))

    logger.info(
        "[KB_OPERATOR] ingest source=%s host=%s products=%d variants=%d offers=%d images=%d specs=%d "
        "gaps_closed=%d not_built=%d",
        SOURCE_PARTNER if body.source == SOURCE_PARTNER else SOURCE_OPERATOR, merchant, counts["products"],
        counts["variants"], counts["offers"], counts["images"], counts["specs"], counts["gaps_closed"],
        counts["not_built"],
    )
    return counts
