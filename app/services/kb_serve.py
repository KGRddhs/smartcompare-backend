"""S81-18 KB-FIRST-SERVE and the verdict-cache key log.

Flags (new names, default OFF, read PER CALL, the house boolean idiom; independent):

* ``ENABLE_KB_FIRST_SERVE`` - the compare orchestrator starts ONE task before the
  product gather (:func:`fetch_cards`: the two ``kb_product_card`` RPCs through the
  service-role client, each inside ``run_db``, in ONE gather under ONE
  ``wait_for``); each product slot classifies its card (:func:`classify`) and the
  slots serve the legs the card holds (a full hit skips every paid leg; a partial
  hit runs only the missing legs; a miss is the base path). The route reader
  :func:`client_price_asof` reads the ``X-Client-Capabilities`` header only under
  this flag. ``metadata.kb_hit`` is written only under it.
* ``ENABLE_VERDICT_CACHE_LOG`` - :func:`log_verdict_key` logs ONE
  ``[VERDICT_CACHE] would_hit=<0|1> key=<16 hex>`` INFO line for a compare with no
  explicit preferences, no cohort and no behaviour profile; :func:`seed_verdict_key`
  seeds the per-process LRU after a successful verdict only. Nothing is cached and
  nothing is served from it.

Knobs (unset / blank / garbage / inf / nan / <= 0 -> the default, else clamped):
``KB_FIRST_SERVE_TIMEOUT_SECONDS`` (1.0, 0.2..3.0), ``KB_FIRST_SERVE_MAX_ASOF_DAYS``
(30, 8..90), ``VERDICT_CACHE_LOG_MAX_KEYS`` (10000, 100..100000).

The KB price (R-G4-2) is a genuine BH page observation: ``source_method``
``page_scrape``, the additive ``as_of`` (the offer's ``last_seen``, ISO-8601 Z,
R-G4-4) and the internal ``_cached`` / ``_cache_source = "kb"`` keys, which
``public_price_view`` strips. A price older than the 7-day genuine window is
served only to a client that declared ``price_asof`` and only up to the as-of
knob. The verdict key's prompt digest is PRODUCT-FREE (R-G4-3): the verdict
prompt rendered over two identity-only stubs.

Only the standard library is imported at module top; the S81-14 leaf through
:func:`kb_leaf`, everything else lazily. Test seams: ``_now``, ``_admin_client``,
``fetch_cards``, ``_SEEN``. Log lines carry constants, type names and 16 hex only.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

KB_PRODUCT_CARD_RPC = "kb_product_card"
LICENCE_FIELDS: Tuple[str, ...] = ("notes_top", "notes_heart", "notes_base", "longevity", "sillage")
KB_HIT_VALUES: Tuple[str, ...] = ("full", "partial", "miss")
PRICE_STATES: Tuple[str, ...] = ("fresh", "asof", "stale_refused", "none")
KB_SOURCE = "kb"
MAX_CAPABILITY_CHARS = 512

_TRUTHY = ("true", "1", "yes", "on")
_SEEN: "OrderedDict[str, bool]" = OrderedDict()
_SEEN_LOCK = threading.Lock()


# --------------------------------------------------------------------------- flags, knobs
def kb_first_serve_enabled() -> bool:
    """True iff ``ENABLE_KB_FIRST_SERVE`` is truthy. Read PER CALL."""
    return os.getenv("ENABLE_KB_FIRST_SERVE", "false").strip().lower() in _TRUTHY


def verdict_cache_log_enabled() -> bool:
    """True iff ``ENABLE_VERDICT_CACHE_LOG`` is truthy. Read PER CALL."""
    return os.getenv("ENABLE_VERDICT_CACHE_LOG", "false").strip().lower() in _TRUTHY


def _knob(name: str, default: float, low: float, high: float) -> float:
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


def timeout_seconds() -> float:
    return float(_knob("KB_FIRST_SERVE_TIMEOUT_SECONDS", 1.0, 0.2, 3.0))


def max_asof_days() -> int:
    return int(_knob("KB_FIRST_SERVE_MAX_ASOF_DAYS", 30, 8, 90))


def max_log_keys() -> int:
    return int(_knob("VERDICT_CACHE_LOG_MAX_KEYS", 10000, 100, 100000))


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


# --------------------------------------------------------------------------- the capability
def client_price_asof(request: Any) -> bool:
    """True iff the flag is ON and the request's ``X-Client-Capabilities`` lists
    ``price_asof`` (comma-separated tokens, stripped, case-insensitive). The flag is
    read FIRST: OFF reads no header. The value is never logged."""
    if not kb_first_serve_enabled():
        return False
    try:
        value = request.headers.get("x-client-capabilities")
        if not isinstance(value, str) or len(value) > MAX_CAPABILITY_CHARS:
            return False
        return "price_asof" in {token.strip().lower() for token in value.split(",")}
    except Exception:  # noqa: BLE001 - an unreadable header is no capability
        return False


def required_spec_fields(category: Any) -> Tuple[str, ...]:
    """The category's critical spec fields minus the licence fields (order kept)."""
    from app.services.extraction_service import CRITICAL_SCHEMA_FIELDS

    return tuple(f for f in CRITICAL_SCHEMA_FIELDS.get(category, []) if f not in LICENCE_FIELDS)


# --------------------------------------------------------------------------- the card read
async def fetch_cards(products: Sequence[Any], lang: Optional[str]) -> List[Optional[Dict[str, Any]]]:
    """Two entries in product order (a card dict or None). Total: a timeout over the
    knob, no client or any exception -> [None, None] and ONE WARNING carrying the
    exception type name; never raises, never retries."""
    try:
        from app.utils import db_offload

        kb = kb_leaf()
        client = _admin_client()
        if client is None:
            raise RuntimeError("no service-role client")
        p_lang = "ar" if lang == "ar" else "en"

        async def _one(product: Any) -> Optional[Dict[str, Any]]:
            info = product if isinstance(product, dict) else {}
            pid = kb.kb_product_id(info.get("brand"), info.get("name"), info.get("variant"))
            if pid is None:
                return None
            resp = await db_offload.run_db(
                lambda: client.rpc(KB_PRODUCT_CARD_RPC, {"p_product_id": pid, "p_lang": p_lang}).execute())
            data = getattr(resp, "data", None)
            if isinstance(data, dict) and isinstance(data.get("product"), dict):
                return data
            return None

        slots = list(products or [])[:2]
        slots += [None] * (2 - len(slots))
        cards = await asyncio.wait_for(asyncio.gather(*(_one(p) for p in slots)), timeout=timeout_seconds())
        return list(cards)
    except Exception as exc:  # noqa: BLE001 - total: the base path runs
        logger.warning("[KB_SERVE] card read failed: %s", type(exc).__name__)
        return [None, None]


# --------------------------------------------------------------------------- classify
def _ts(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        out = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return out if out.tzinfo is not None else out.replace(tzinfo=timezone.utc)


def _iso_z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _amount(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) and out > 0 else None


def _miss() -> Dict[str, Any]:
    return {"hit": "miss", "pid": None, "version": None, "price": None, "price_state": "none",
            "candidates": [], "specs": None, "specs_complete": False, "image_url": None,
            "reviews": None, "rating": None, "review_count": None}


def _price_dict(product: Dict[str, Any], offer: Dict[str, Any], amount: float, seen: datetime,
                size_ml: Optional[int]) -> Dict[str, Any]:
    parts = [product.get(k) for k in ("brand", "name", "concentration")]
    title = " ".join(str(p) for p in parts if isinstance(p, str) and p)
    if size_ml is not None:
        title = ("%s %dml" % (title, size_ml)).strip()
    price: Dict[str, Any] = {
        "amount": amount, "currency": "BHD", "retailer": offer.get("merchant_id"),
        "url": offer.get("canonical_url"), "source_method": "page_scrape", "estimated": False,
        "title": title,
    }
    if size_ml is not None:
        price["size"] = "%dml" % size_ml
    price["as_of"] = _iso_z(seen)
    price["_cached"] = True
    price["_cache_source"] = KB_SOURCE
    if isinstance(offer.get("in_stock"), bool):
        price["in_stock"] = offer["in_stock"]
    return price


def classify(card: Any, *, category: Any, region: Any, now: datetime, accepts_asof: bool) -> Dict[str, Any]:
    """Pure: what the card can serve for one product slot (the 2.2 contract)."""
    if not isinstance(card, dict) or not isinstance(card.get("product"), dict):
        return _miss()
    from app.services import image_service, product_data_service

    kb = kb_leaf()
    product = card["product"]
    out = _miss()
    out["pid"] = product.get("id") if isinstance(product.get("id"), str) else None
    version = product.get("updated_at")
    if not (isinstance(version, str) and version):
        blob = json.dumps(card, sort_keys=True, separators=(",", ":"), default=str)
        version = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
    out["version"] = version

    sizes: Dict[Any, Any] = {}
    for variant in card.get("variants") or []:
        if isinstance(variant, dict):
            sizes[variant.get("id")] = variant.get("size_ml")

    # -- the price: BH / BHD offers of an allowed source, fresh within the genuine
    #    window, else as-of for a capable client up to the knob, else refused
    fresh_window = product_data_service.GENUINE_PRICE_DB_TTL
    asof_seconds = max_asof_days() * 86400
    graded: List[Tuple[str, datetime, float, str, Dict[str, Any]]] = []
    for offer in card.get("offers") or []:
        if not isinstance(offer, dict):
            continue
        amount = _amount(offer.get("amount"))
        seen = _ts(offer.get("last_seen"))
        if (region != "bahrain" or offer.get("market") != "BH" or offer.get("observed_currency") != "BHD"
                or amount is None or offer.get("in_stock") is False or seen is None
                or not kb.kb_source_allowed(offer.get("canonical_url"))):
            continue
        age = now - seen
        if age <= fresh_window:
            grade = "fresh"
        elif accepts_asof and age.total_seconds() <= asof_seconds:
            grade = "asof"
        else:
            grade = "stale"
        graded.append((grade, seen, amount, str(offer.get("variant_id") or ""), offer))
    for grade in ("fresh", "asof"):
        group = sorted((g for g in graded if g[0] == grade), key=lambda g: (-g[1].timestamp(), g[2], g[3]))
        if not group:
            continue
        dicts = []
        for _grade, seen, amount, _vid, offer in group:
            size = sizes.get(offer.get("variant_id"))
            if not (isinstance(size, int) and not isinstance(size, bool)):
                size = offer.get("size_ml") if isinstance(offer.get("size_ml"), int) else None
            if isinstance(size, bool) or (isinstance(size, int) and size <= 0):
                size = None
            dicts.append(_price_dict(product, offer, amount, seen, size))
        out["price"], out["price_state"], out["candidates"] = dicts[0], grade, dicts
        break
    else:
        out["price_state"] = "stale_refused" if graded else "none"

    # -- the cited specs
    specs: Dict[str, Any] = {}
    for row in card.get("specs") or []:
        if (isinstance(row, dict) and isinstance(row.get("field"), str) and row.get("cited") is not False
                and row.get("value") not in (None, "")):
            specs.setdefault(row["field"], row["value"])
    if specs:
        out["specs"] = dict(specs)
        out["specs"]["_field_confidence"] = dict.fromkeys(specs, "kb_cited")
        out["specs"]["_cached"] = True
        out["specs"]["_cache_source"] = KB_SOURCE
    out["specs_complete"] = bool(specs) and set(required_spec_fields(category)) <= set(specs)

    # -- the image (https, a valid image URL, an allowed source)
    for image in card.get("images") or []:
        url = image.get("url") if isinstance(image, dict) else None
        if (isinstance(url, str) and url.startswith("https://") and image_service._is_valid_image_url(url)
                and kb.kb_source_allowed(url)):
            out["image_url"] = url
            break

    # -- the rating
    rating = card.get("rating") if isinstance(card.get("rating"), dict) else {}
    value, sources = rating.get("rating"), rating.get("sources")
    if (isinstance(sources, int) and not isinstance(sources, bool) and sources > 0
            and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)):
        count = rating.get("review_count")
        count = count if isinstance(count, int) and not isinstance(count, bool) else None
        out["reviews"] = {"average_rating": float(value), "total_reviews": count, "_cached": True,
                          "_cache_source": KB_SOURCE}
        out["rating"], out["review_count"] = float(value), count

    full = (product.get("identity_confidence") == "high" and out["price_state"] in ("fresh", "asof")
            and out["specs_complete"] and out["image_url"] is not None)
    out["hit"] = "full" if full else "partial"
    return out


async def served(value: Any) -> Any:
    """The coroutine a Phase-1 slot awaits in place of a live leg (same shapes for
    ``_timed_task`` / ``wait_for`` / the done callbacks)."""
    return value


# --------------------------------------------------------------------------- the verdict-cache key
def verdict_key(*, pids: Sequence[Any], versions: Sequence[Any], scores_summary: Any, winner_index: Any,
                lang: Any, model: Any, prompt: Any) -> str:
    def digest(text: Any) -> str:
        return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()

    parts = [
        pids[0] or "-", pids[1] or "-", versions[0] or "-", versions[1] or "-",
        digest(scores_summary), str(int(winner_index)), lang or "en", model or "-", digest(prompt),
    ]
    return hashlib.sha256("\x1f".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def _identity_stub(product: Any) -> Dict[str, Any]:
    """R-G4-3: identity fields only (the pid axes); no specs, price or reviews."""
    info = product if isinstance(product, dict) else {}
    return {"brand": info.get("brand"), "name": info.get("name"), "variant": info.get("variant"),
            "specs": {}, "price": None, "reviews": None}


def _prompt_digest_input(category: Any, comparison_quality: Any, product_data: Any) -> str:
    """The verdict system prompt rendered over two identity-only stubs: it tracks the
    template, the category personality and the quality framing, never live text."""
    from app.services import extraction_service

    slots = list(product_data or [])[:2]
    slots += [None] * (2 - len(slots))
    return extraction_service.build_verdict_prompt(
        products=[_identity_stub(p) for p in slots], comparison_quality=comparison_quality,
        user_cohort=None, category=category,
    )


def log_verdict_key(*, user_preferences: Any, demographics_profile: Any, behavior_profile: Any,
                    product_data: Any, scores_summary: Any, winner_index: Any, lang: Any, category: Any,
                    comparison_quality: Any = None, views: Any = None) -> Optional[str]:
    """ONE would-hit line for an eligible compare; returns the key (None when the flag
    is OFF, the compare is personalised, or anything raises)."""
    if not verdict_cache_log_enabled():
        return None
    try:
        if user_preferences or demographics_profile is not None or behavior_profile is not None:
            return None
        from app.services import model_config

        if comparison_quality is None:
            # GC-4 (c): the REST key runs before the verdict's own quality value exists.
            from app.services.structured_comparison_service import verdict_comparison_quality

            comparison_quality = verdict_comparison_quality(product_data)
        kb = kb_leaf()
        data = list(product_data or [])[:2]
        data += [None] * (2 - len(data))
        pids: List[str] = []
        versions: List[str] = []
        for slot in range(2):
            view = views[slot] if isinstance(views, (list, tuple)) and len(views) > slot else None
            if isinstance(view, dict) and view.get("hit") in ("full", "partial") and view.get("pid"):
                pids.append(str(view["pid"]))
                versions.append(str(view.get("version") or "-"))
                continue
            info = data[slot] if isinstance(data[slot], dict) else {}
            pids.append(kb.kb_product_id(info.get("brand"), info.get("name"), info.get("variant")) or "-")
            versions.append("-")
        prompt = _prompt_digest_input(category, comparison_quality, data)
        key = verdict_key(pids=pids, versions=versions, scores_summary=scores_summary,
                          winner_index=winner_index, lang=lang, model=model_config.verdict_model(),
                          prompt=prompt)
        with _SEEN_LOCK:
            would_hit = key in _SEEN
        logger.info("[VERDICT_CACHE] would_hit=%d key=%s", int(would_hit), key[:16])
        return key
    except Exception as exc:  # noqa: BLE001 - a log instrument never fails a compare
        logger.debug("[VERDICT_CACHE] key not computed: %s", type(exc).__name__)
        return None


def seed_verdict_key(key: Optional[str]) -> None:
    """Seed the per-process LRU (called only after a successful verdict); the oldest
    keys past ``VERDICT_CACHE_LOG_MAX_KEYS`` are evicted."""
    if key is None:
        return
    with _SEEN_LOCK:
        _SEEN[key] = True
        _SEEN.move_to_end(key)
        cap = max_log_keys()
        while len(_SEEN) > cap:
            _SEEN.popitem(last=False)
