"""S81-14 KB-SCHEMA: identity helpers and row builders for the kb_* tables.

A pure leaf: its own code does no I/O, no logging, no clock, no environment
read, no flag, and it never raises. No importer in app/ yet; S81-15..S81-22 call
it. Import hazard (F1-11): importing this leaf imports price_service, which
imports extraction_service, which calls ``load_dotenv(override=True)`` at
import; every S81-15..S81-22 script that imports the leaf inherits that
dotenv-override hazard (the one P8 pins: set a flag AFTER the first import).

Identity (rulings R-S14-3, F1-1): a JUICE id is ``spine_key(...)`` minus its ml
field (brand axis + identity tokens + concentration); a SKU id is the juice id
plus ``|<ml>``; no id when ``result_gate.product_is_placeholder`` says the
identity (brand + name deduplicated) OR the name alone is a placeholder. The
deny rule is ``deny_hosts.kb_source_allowed`` (read by module attribute at call
time); the 045 SQL label CHECKs are belts derived from
``deny_hosts.DENY_LABELS`` and a strict SUBSET of the rule (a belt hit is always
a whole-token hit of the rule, so a belt never refuses a row a builder accepted;
the rule also refuses path and query tokens, hyphenated labels and top-level
labels). kb_merchants deliberately carries no deny check: a denied host is
stored with deny = True and status 'blocked' (R-S14-2). Every host, and the
host of every URL, carries a letter in its top-level label (F1-6: no all-digit
host). Every builder refuses a NUL character or a lone surrogate in any text or
jsonb value, keys included (PostgreSQL 22P05 / 22P02, F1-8).
"""
from __future__ import annotations

import ipaddress
import json
import math
import re
import uuid
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple, Union, get_type_hints
from urllib.parse import urlsplit

from app.services import deny_hosts as _deny
from app.services import price_service as _ps
from app.services import result_gate as _rg
from app.services import spec_spine_service as _spine

KB_CATEGORY = "fragrances"

KB_TABLES: Tuple[str, ...] = (
    "kb_merchants", "kb_products", "kb_variants", "kb_offers", "kb_images",
    "kb_specs", "kb_reviews", "kb_gaps", "kb_feedback", "kb_coverage_daily",
)

KB_COLUMNS: Dict[str, Tuple[str, ...]] = {
    "kb_merchants": (
        "host", "country", "currency_hint", "platform", "platform_confidence", "adapter",
        "search_template", "registry", "robots", "politeness", "health", "challenge", "tos",
        "deny", "status", "blocked_reason", "partner", "created_at", "updated_at",
    ),
    "kb_products": (
        "id", "brand", "line", "name", "concentration", "audience", "identity_confidence",
        "created_at", "updated_at",
    ),
    "kb_variants": (
        "id", "product_id", "concentration", "size_ml", "gtin", "sku", "created_at", "updated_at",
    ),
    "kb_offers": (
        "id", "variant_id", "merchant_id", "market", "amount", "observed_currency",
        "evidence_rung", "size_ml", "list_vs_sale", "in_stock", "first_seen", "last_seen",
        "captured_at", "canonical_url",
    ),
    "kb_images": (
        "id", "product_id", "variant_id", "url", "provenance_host", "source", "captured_at",
    ),
    "kb_specs": (
        "id", "product_id", "field", "lang", "value", "source_url", "extractor", "model",
        "cited", "captured_at",
    ),
    "kb_reviews": (
        "id", "product_id", "source", "aggregate_rating", "review_count", "source_url",
        "captured_at",
    ),
    "kb_gaps": (
        "id", "product_key", "field", "demand_count", "first_seen", "last_seen", "state",
        "source_hint",
    ),
    "kb_feedback": (
        "id", "compare_request_id", "product_id", "field", "verdict", "device_key", "created_at",
    ),
    "kb_coverage_daily": ("day", "metric", "value", "n"),
}

#: Tables whose ``id`` is a server-side uuid (never built by the leaf).
KB_UUID_ID_TABLES: Tuple[str, ...] = (
    "kb_offers", "kb_images", "kb_specs", "kb_reviews", "kb_gaps", "kb_feedback",
)

#: What a builder emits: the columns minus a uuid ``id`` and minus ``created_at``
#: (``updated_at`` IS emitted where the table has it: the trigger is a belt).
KB_BUILDER_KEYS: Dict[str, Tuple[str, ...]] = {
    t: tuple(
        c for c in cols
        if c != "created_at" and not (c == "id" and t in KB_UUID_ID_TABLES)
    )
    for t, cols in KB_COLUMNS.items()
}

#: The 045 text of the host CHECK (one constant; the RED pins it equal to the SQL).
KB_HOST_REGEX = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"
#: F1-6: the top-level label carries a letter, so no all-digit host (an IPv4
#: literal shape: a WHATWG URL parser reads a host whose last label is a number
#: as IPv4) is stored; the 045 constraint kb_merchants_host_top_label_letter
#: carries the same text. A digit registrable label (4711.com) stays valid.
KB_HOST_TOP_LABEL_REGEX = "[a-z][a-z0-9-]*$"
_HOST_CORE = KB_HOST_REGEX[1:-1]
KB_OFFER_URL_REGEX = "^https?://" + _HOST_CORE + "/[^?#[:space:]]*$"
KB_IMAGE_URL_REGEX = "^https://" + _HOST_CORE + "/[^#[:space:]]*$"
KB_SOURCE_URL_REGEX = "^https?://" + _HOST_CORE + "/[^#[:space:]]*$"
KB_MARKET_REGEX = "^[A-Z]{2,3}$"
KB_CURRENCY_REGEX = "^[A-Z]{3}$"
KB_FIELD_REGEX = "^[a-z][a-z0-9_]{0,63}$"
KB_METRIC_REGEX = "^[a-z][a-z0-9_.:-]{0,127}$"
KB_DEVICE_KEY_REGEX = "^[a-f0-9]{64}$"

KB_AUDIENCES: Tuple[str, ...] = ("men", "women", "unisex")
KB_IDENTITY_CONFIDENCE: Tuple[str, ...] = ("high", "medium", "low")
KB_MERCHANT_STATUS: Tuple[str, ...] = ("candidate", "live", "blocked")
KB_PLATFORM_CONFIDENCE: Tuple[str, ...] = ("mechanism", "probe", "url", "operator")
KB_REGISTRY_ORIGINS: Tuple[str, ...] = ("literal", "catalog", "operator", "discovery")
KB_EVIDENCE_RUNGS: Tuple[str, ...] = (
    "own_token", "page_evidence", "expected_missing", "platform_api", "operator",
)
KB_LIST_VS_SALE: Tuple[str, ...] = ("list", "sale", "unknown")
KB_IMAGE_SOURCES: Tuple[str, ...] = (
    "retailer_jsonld", "retailer_og", "brand_site", "partner_feed", "operator",
)
KB_REVIEW_SOURCES: Tuple[str, ...] = ("retailer_jsonld", "retailer_widget", "brand_site", "marketplace")
KB_GAP_STATES: Tuple[str, ...] = ("open", "queued", "needs_operator", "licence", "closed")
KB_VERDICTS: Tuple[str, ...] = ("correct", "wrong", "unsure")
KB_SPEC_LANGS: Tuple[str, ...] = ("en", "ar")

#: R-S14-1: the identity of one observation row and the columns a re-observation sets.
KB_OFFER_OBSERVATION_KEY: Tuple[str, ...] = (
    "variant_id", "merchant_id", "market", "observed_currency", "amount", "list_vs_sale",
)
KB_OFFER_UPSERT_SET: Tuple[str, ...] = ("last_seen", "in_stock", "evidence_rung", "canonical_url")

_DEFAULT_PORTS = {"http": 80, "https": 443}
_MAX_SKU_ML = 5000
_INT4_MAX = 2 ** 31 - 1


def kb_concentrations() -> Tuple[str, ...]:
    """The concentration labels of the price path, read at call time."""
    return tuple(label for _pat, label in _ps._CONCENTRATION_PATTERNS)


def kb_deny_label_group() -> str:
    """``(basenotes|fimgs|...)`` built from ``deny_hosts.DENY_LABELS`` at call time."""
    return "(" + "|".join(sorted(_deny.DENY_LABELS)) + ")"


def kb_host_deny_regex() -> str:
    """The 045 belt on a host column."""
    return "(^|[.])" + kb_deny_label_group() + "[.]"


def kb_url_deny_regex() -> str:
    """The 045 belt on a URL column."""
    return "^https?://([^/]*[.])?" + kb_deny_label_group() + "[.]"


def _sql_match(sql_regex: str, value: Any) -> bool:
    """Python emulation of a PostgreSQL ``value ~ 'sql_regex'`` (case-sensitive)."""
    if not isinstance(value, str):
        return False
    pattern = sql_regex.replace("[:space:]", r"\s")
    if pattern.endswith("$"):
        pattern = pattern[:-1] + r"\Z"
    return re.search(pattern, value) is not None


def _top_label_ok(host: Any) -> bool:
    return _sql_match(KB_HOST_TOP_LABEL_REGEX, host)


def _belted_host(value: Any) -> bool:
    return (
        _sql_match(KB_HOST_REGEX, value)
        and _top_label_ok(value)
        and not _sql_match(kb_host_deny_regex(), value)
    )


def _belted_url(sql_regex: str, value: Any, limit: Optional[int] = 2048) -> bool:
    if not isinstance(value, str):
        return False
    if limit is not None and len(value) > limit:
        return False
    return (
        _sql_match(sql_regex, value)
        and _top_label_ok(_url_host(value))
        and not _sql_match(kb_url_deny_regex(), value)
    )


def kb_source_allowed(value: Any) -> bool:
    """``deny_hosts.kb_source_allowed`` read at CALL time (flag-free)."""
    try:
        return bool(_deny.kb_source_allowed(value))
    except Exception:
        return False


def kb_product_id(brand: Any, name: Any, variant: Any = None) -> Optional[str]:
    """The JUICE id (spine_key minus ml), or None when no id can be minted."""
    try:
        if not isinstance(brand, str) or not isinstance(name, str):
            return None
        if variant is not None and not isinstance(variant, str):
            return None
        if not brand.strip() and not name.strip():
            return None
        # R-A5 / F1-1: the house rule, the identity OR the name alone.
        if _rg.product_is_placeholder({"brand": brand, "name": name}):
            return None
        key = _spine.spine_key(brand, name, variant)
        if not isinstance(key, str):
            return None
        parts = key.split("|")
        if len(parts) != 5 or parts[0] != KB_CATEGORY or not parts[1] or not parts[2] or not parts[3]:
            return None
        return "|".join(parts[:4])
    except Exception:
        return None


def kb_variant_key(product_id: Any, concentration: Any, size_ml: Any) -> Optional[str]:
    """The SKU id: ``product_id + "|" + ml``; None when the pieces disagree."""
    try:
        if not isinstance(product_id, str):
            return None
        parts = product_id.split("|")
        if len(parts) != 4 or parts[0] != KB_CATEGORY or not all(parts[1:]):
            return None
        if concentration is not None and not isinstance(concentration, str):
            return None
        if (concentration or "-") != parts[3]:
            return None
        if size_ml is None:
            ml = "-"
        elif isinstance(size_ml, bool) or not isinstance(size_ml, int) or size_ml < 0:
            return None
        elif size_ml == 0 or size_ml > _MAX_SKU_ML:
            ml = "-"
        else:
            ml = str(size_ml)
        return product_id + "|" + ml
    except Exception:
        return None


def canonical_offer_url(url: Any) -> Optional[str]:
    """scheme + lower host + path (query and fragment dropped), or None."""
    try:
        if not isinstance(url, str) or not url:
            return None
        if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 or ch == "\\" for ch in url):
            return None
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        if scheme not in _DEFAULT_PORTS:
            return None
        if "@" in parts.netloc or parts.username is not None or parts.password is not None:
            return None
        host = parts.hostname or ""
        if host.endswith("."):
            host = host[:-1]
        if not _sql_match(KB_HOST_REGEX, host):
            return None
        try:
            ipaddress.ip_address(host)
            return None
        except ValueError:
            pass
        try:
            port = parts.port
        except ValueError:
            return None
        if port is not None and port != _DEFAULT_PORTS[scheme]:
            return None
        out = scheme + "://" + host + (parts.path or "/")
        if not _belted_url(KB_OFFER_URL_REGEX, out, limit=None):
            return None
        return out
    except Exception:
        return None


def gtin_check_digit_ok(gtin: Any) -> bool:
    """8, 12, 13 or 14 ASCII digits with a valid GS1 mod-10 check digit."""
    try:
        if not isinstance(gtin, str) or len(gtin) not in (8, 12, 13, 14):
            return False
        if not (gtin.isascii() and gtin.isdigit()):
            return False
        n = len(gtin)
        total = 0
        for i in range(1, n):
            total += int(gtin[i - 1]) * (3 if (n - i) % 2 == 1 else 1)
        return (10 - total % 10) % 10 == int(gtin[-1])
    except Exception:
        return False


# ---------------------------------------------------------------------------
# value checks shared by the builders (each mirrors one 045 CHECK)
# ---------------------------------------------------------------------------

def _str_len(value: Any, lo: int, hi: int) -> bool:
    return isinstance(value, str) and lo <= len(value) <= hi


def _opt_len(value: Any, lo: int, hi: int) -> bool:
    return value is None or _str_len(value, lo, hi)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _ts_iso(value: Any) -> Optional[str]:
    if isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None:
        return value.isoformat()
    return None


def _json_ok(value: Any, kind: type) -> bool:
    if not isinstance(value, kind):
        return False
    try:
        json.dumps(value, allow_nan=False)
        return True
    except (TypeError, ValueError):
        return False


def _decimal(value: Any, places: int) -> Optional[Decimal]:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return None
    try:
        if isinstance(value, float) and not math.isfinite(value):
            return None
        d = Decimal(str(value))
        if not d.is_finite():
            return None
        # PostgreSQL rounds numeric(p, s) half away from zero; mirror it so a
        # value the builder accepts is the value the column stores.
        return d.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None


def _pg_text_ok(value: Any) -> bool:
    """F1-8: no NUL character and no lone surrogate in a text or jsonb value, keys
    included (PostgreSQL refuses both: 22P05 / 22P02); other types pass."""
    if isinstance(value, str):
        if chr(0) in value:
            return False
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            return False
        return True
    if isinstance(value, dict):
        return all(_pg_text_ok(k) and _pg_text_ok(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return all(_pg_text_ok(v) for v in value)
    return True


def _source_value_ok(ftype: Any, value: Any) -> bool:
    """A present registry entry value against the declared type of its Source field."""
    origin = getattr(ftype, "__origin__", None)
    args = getattr(ftype, "__args__", None) or ()
    if origin is Union:
        return value is None or any(_source_value_ok(a, value) for a in args if a is not type(None))
    if origin is tuple:
        elem = args[0] if args else str
        return isinstance(value, (list, tuple)) and all(_source_value_ok(elem, x) for x in value)
    if ftype is bool:
        return isinstance(value, bool)
    if ftype is int:
        return _is_int(value)
    if ftype is float:
        return _is_int(value) or (isinstance(value, float) and math.isfinite(value))
    if ftype is str:
        return isinstance(value, str)
    if hasattr(ftype, "__dataclass_fields__"):
        return isinstance(value, dict)
    return False


def _registry_ok(value: Any, host: Any) -> bool:
    """F1-3: the PRESENT keys of every entry and their types. Keys within origin,
    order and the ``source_router.Source`` field names (read by module attribute
    at call time, imported here so the leaf stays import-light); each present
    value of its field's declared type; origin one of the four; order an int
    >= 0, unique within the array; domain (when present) == the row's host.
    Presence of every Source field is S81-15's seed contract, not this check."""
    if not _json_ok(value, list):
        return False
    from app.services import source_router as _sr

    fields = get_type_hints(_sr.Source)
    orders = []
    for entry in value:
        if not isinstance(entry, dict):
            return False
        if entry.get("origin") not in KB_REGISTRY_ORIGINS:
            return False
        order = entry.get("order")
        if not _is_int(order) or order < 0:
            return False
        if order in orders:
            return False
        orders.append(order)
        if any(k not in fields and k not in ("origin", "order") for k in entry):
            return False
        if not all(_source_value_ok(fields[k], v) for k, v in entry.items() if k in fields):
            return False
        if "domain" in entry and entry["domain"] != host:
            return False
    return True


def _url_host(url: str) -> str:
    return url.split("://", 1)[1].split("/", 1)[0]


# ---------------------------------------------------------------------------
# row builders: a dict whose key set equals KB_BUILDER_KEYS[table], or None
# ---------------------------------------------------------------------------

def build_merchant_row(
    *, host: Any, updated_at: Any, country: Any = None, currency_hint: Any = None,
    platform: Any = None, platform_confidence: Any = None, adapter: Any = None,
    search_template: Any = None, registry: Any = None, robots: Any = None,
    politeness: Any = None, health: Any = None, challenge: Any = None, tos: Any = None,
    deny: Any = False, status: Any = "candidate", blocked_reason: Any = None,
    partner: Any = None,
) -> Optional[Dict[str, Any]]:
    try:
        registry = [] if registry is None else registry
        objs = {
            "robots": {} if robots is None else robots,
            "politeness": {} if politeness is None else politeness,
            "health": {} if health is None else health,
            "challenge": {} if challenge is None else challenge,
            "tos": {} if tos is None else tos,
            "partner": {} if partner is None else partner,
        }
        upd = _ts_iso(updated_at)
        if not _pg_text_ok((
            host, country, currency_hint, platform, platform_confidence, adapter, search_template,
            registry, objs, deny, status, blocked_reason,
        )):
            return None
        ok = (
            _sql_match(KB_HOST_REGEX, host)
            and _top_label_ok(host)
            and (country is None or _sql_match(KB_MARKET_REGEX, country))
            and (currency_hint is None or _sql_match(KB_CURRENCY_REGEX, currency_hint))
            and _opt_len(platform, 1, 32)
            and (platform_confidence is None or platform_confidence in KB_PLATFORM_CONFIDENCE)
            and _opt_len(adapter, 1, 64)
            and _opt_len(search_template, 1, 1024)
            and _registry_ok(registry, host)
            and all(_json_ok(v, dict) for v in objs.values())
            and isinstance(deny, bool)
            and status in KB_MERCHANT_STATUS
            and _opt_len(blocked_reason, 1, 64)
            and (not deny or status == "blocked")
            and (status != "blocked" or blocked_reason is not None)
            and upd is not None
        )
        if not ok:
            return None
        return {
            "host": host, "country": country, "currency_hint": currency_hint,
            "platform": platform, "platform_confidence": platform_confidence,
            "adapter": adapter, "search_template": search_template, "registry": registry,
            "robots": objs["robots"], "politeness": objs["politeness"],
            "health": objs["health"], "challenge": objs["challenge"], "tos": objs["tos"],
            "deny": deny, "status": status, "blocked_reason": blocked_reason,
            "partner": objs["partner"], "updated_at": upd,
        }
    except Exception:
        return None


def build_product_row(
    *, id: Any, brand: Any, name: Any, identity_confidence: Any, updated_at: Any,
    line: Any = None, concentration: Any = None, audience: Any = None,
) -> Optional[Dict[str, Any]]:
    try:
        upd = _ts_iso(updated_at)
        if not _pg_text_ok((id, brand, name, identity_confidence, line, concentration, audience)):
            return None
        ok = (
            _str_len(id, 14, 512) and id.startswith(KB_CATEGORY + "|")
            and _str_len(brand, 1, 128)
            and _opt_len(line, 1, 256)
            and _str_len(name, 1, 256)
            and (concentration is None or concentration in kb_concentrations())
            and (audience is None or audience in KB_AUDIENCES)
            and identity_confidence in KB_IDENTITY_CONFIDENCE
            and upd is not None
        )
        if not ok:
            return None
        return {
            "id": id, "brand": brand, "line": line, "name": name,
            "concentration": concentration, "audience": audience,
            "identity_confidence": identity_confidence, "updated_at": upd,
        }
    except Exception:
        return None


def build_variant_row(
    *, id: Any, product_id: Any, updated_at: Any, concentration: Any = None,
    size_ml: Any = None, gtin: Any = None, sku: Any = None,
) -> Optional[Dict[str, Any]]:
    try:
        upd = _ts_iso(updated_at)
        if not _pg_text_ok((id, product_id, concentration, size_ml, gtin, sku)):
            return None
        ok = (
            isinstance(id, str) and _str_len(product_id, 1, 10 ** 6)
            and id.startswith(product_id + "|")
            and len(product_id) + 2 <= len(id) <= len(product_id) + 5
            and (concentration is None or concentration in kb_concentrations())
            and (size_ml is None or (_is_int(size_ml) and 1 <= size_ml <= 9999))
            and (gtin is None or gtin_check_digit_ok(gtin))
            and _opt_len(sku, 1, 128)
            and upd is not None
        )
        if not ok:
            return None
        return {
            "id": id, "product_id": product_id, "concentration": concentration,
            "size_ml": size_ml, "gtin": gtin, "sku": sku, "updated_at": upd,
        }
    except Exception:
        return None


def build_offer_row(
    *, variant_id: Any, merchant_id: Any, market: Any, amount: Any,
    observed_currency: Any, evidence_rung: Any, canonical_url: Any, captured_at: Any,
    size_ml: Any = None, list_vs_sale: Any = "unknown", in_stock: Any = None,
    first_seen: Any = None, last_seen: Any = None,
) -> Optional[Dict[str, Any]]:
    try:
        first_seen = captured_at if first_seen is None else first_seen
        last_seen = captured_at if last_seen is None else last_seen
        cap, fst, lst = _ts_iso(captured_at), _ts_iso(first_seen), _ts_iso(last_seen)
        amt = _decimal(amount, 3)
        if not _pg_text_ok((
            variant_id, merchant_id, market, observed_currency, evidence_rung, canonical_url, list_vs_sale,
        )):
            return None
        ok = (
            _str_len(variant_id, 1, 10 ** 6)
            and _sql_match(KB_HOST_REGEX, merchant_id)
            and _sql_match(KB_MARKET_REGEX, market)
            and amt is not None and amt > 0 and amt < Decimal(10) ** 11
            and _sql_match(KB_CURRENCY_REGEX, observed_currency)
            and evidence_rung in KB_EVIDENCE_RUNGS
            and (size_ml is None or (_is_int(size_ml) and 1 <= size_ml <= 9999))
            and list_vs_sale in KB_LIST_VS_SALE
            and (in_stock is None or isinstance(in_stock, bool))
            and None not in (cap, fst, lst)
            and first_seen <= last_seen
            and isinstance(canonical_url, str)
            # canonical_offer_url applies the 045 regex, the top label and the belt to
            # its output, so equality alone carries them (F1-7: one clause per row)
            and canonical_offer_url(canonical_url) == canonical_url
            and kb_source_allowed(canonical_url)
            and (
                _url_host(canonical_url) == merchant_id
                or _url_host(canonical_url).endswith("." + merchant_id)
            )
        )
        if not ok:
            return None
        return {
            "variant_id": variant_id, "merchant_id": merchant_id, "market": market,
            "amount": str(amt), "observed_currency": observed_currency,
            "evidence_rung": evidence_rung, "size_ml": size_ml, "list_vs_sale": list_vs_sale,
            "in_stock": in_stock, "first_seen": fst, "last_seen": lst, "captured_at": cap,
            "canonical_url": canonical_url,
        }
    except Exception:
        return None


def build_image_row(
    *, product_id: Any, url: Any, provenance_host: Any, source: Any, captured_at: Any,
    variant_id: Any = None,
) -> Optional[Dict[str, Any]]:
    try:
        cap = _ts_iso(captured_at)
        if not _pg_text_ok((product_id, url, provenance_host, source, variant_id)):
            return None
        ok = (
            _str_len(product_id, 1, 10 ** 6)
            and (variant_id is None or _str_len(variant_id, 1, 10 ** 6))
            and _belted_url(KB_IMAGE_URL_REGEX, url)
            and kb_source_allowed(url)
            and _belted_host(provenance_host)
            and kb_source_allowed(provenance_host)
            and source in KB_IMAGE_SOURCES
            and cap is not None
        )
        if not ok:
            return None
        return {
            "product_id": product_id, "variant_id": variant_id, "url": url,
            "provenance_host": provenance_host, "source": source, "captured_at": cap,
        }
    except Exception:
        return None


def build_spec_row(
    *, product_id: Any, field: Any, value: Any, extractor: Any, captured_at: Any,
    lang: Any = "en", source_url: Any = None, model: Any = None, cited: Any = False,
) -> Optional[Dict[str, Any]]:
    try:
        cap = _ts_iso(captured_at)
        if not _pg_text_ok((product_id, field, value, extractor, lang, source_url, model)):
            return None
        ok = (
            _str_len(product_id, 1, 10 ** 6)
            and _sql_match(KB_FIELD_REGEX, field)
            and lang in KB_SPEC_LANGS
            and _str_len(value, 1, 2000)
            and (source_url is None or (
                _belted_url(KB_SOURCE_URL_REGEX, source_url) and kb_source_allowed(source_url)
            ))
            and _str_len(extractor, 1, 64)
            and _opt_len(model, 1, 64)
            and isinstance(cited, bool)
            and (not cited or source_url is not None)
            and cap is not None
        )
        if not ok:
            return None
        return {
            "product_id": product_id, "field": field, "lang": lang, "value": value,
            "source_url": source_url, "extractor": extractor, "model": model,
            "cited": cited, "captured_at": cap,
        }
    except Exception:
        return None


def build_review_row(
    *, product_id: Any, source: Any, source_url: Any, captured_at: Any,
    aggregate_rating: Any = None, review_count: Any = None,
) -> Optional[Dict[str, Any]]:
    try:
        cap = _ts_iso(captured_at)
        rating = None if aggregate_rating is None else _decimal(aggregate_rating, 2)
        if not _pg_text_ok((product_id, source, source_url)):
            return None
        ok = (
            _str_len(product_id, 1, 10 ** 6)
            and source in KB_REVIEW_SOURCES
            and (aggregate_rating is None or rating is not None)
            # F1-6: the RAW value is bounded (stricter than PostgreSQL, which would
            # round -0.001 and 5.001 into range); the stored value is the rounded one
            and (aggregate_rating is None or rating is None or 0 <= Decimal(str(aggregate_rating)) <= 5)
            and (review_count is None or (_is_int(review_count) and 0 <= review_count <= _INT4_MAX))
            and (aggregate_rating is not None or review_count is not None)
            and _belted_url(KB_SOURCE_URL_REGEX, source_url)
            and kb_source_allowed(source_url)
            and cap is not None
        )
        if not ok:
            return None
        return {
            "product_id": product_id, "source": source,
            "aggregate_rating": None if rating is None else str(rating),
            "review_count": review_count, "source_url": source_url, "captured_at": cap,
        }
    except Exception:
        return None


def build_gap_row(
    *, product_key: Any, field: Any, first_seen: Any, last_seen: Any = None,
    demand_count: Any = 1, state: Any = "open", source_hint: Any = None,
) -> Optional[Dict[str, Any]]:
    try:
        last_seen = first_seen if last_seen is None else last_seen
        fst, lst = _ts_iso(first_seen), _ts_iso(last_seen)
        if not _pg_text_ok((product_key, field, demand_count, state, source_hint)):
            return None
        hint_ok = source_hint is None or (
            _str_len(source_hint, 1, 256)
            and (_belted_host(source_hint) or _belted_url(KB_OFFER_URL_REGEX, source_hint, limit=None))
            and kb_source_allowed(source_hint)
        )
        ok = (
            _str_len(product_key, 14, 520)
            and _sql_match(KB_FIELD_REGEX, field)
            and _is_int(demand_count) and 0 <= demand_count <= _INT4_MAX
            and state in KB_GAP_STATES
            and hint_ok
            and None not in (fst, lst)
            and first_seen <= last_seen
        )
        if not ok:
            return None
        return {
            "product_key": product_key, "field": field, "demand_count": demand_count,
            "first_seen": fst, "last_seen": lst, "state": state, "source_hint": source_hint,
        }
    except Exception:
        return None


def build_feedback_row(
    *, compare_request_id: Any, field: Any, verdict: Any, product_id: Any = None,
    device_key: Any = None,
) -> Optional[Dict[str, Any]]:
    try:
        if not _pg_text_ok((field, verdict, product_id, device_key)):
            return None
        if isinstance(compare_request_id, uuid.UUID):
            req = str(compare_request_id)
        elif isinstance(compare_request_id, str):
            req = str(uuid.UUID(compare_request_id))
        else:
            return None
        ok = (
            (product_id is None or _str_len(product_id, 1, 10 ** 6))
            and _sql_match(KB_FIELD_REGEX, field)
            and verdict in KB_VERDICTS
            and (device_key is None or _sql_match(KB_DEVICE_KEY_REGEX, device_key))
        )
        if not ok:
            return None
        return {
            "compare_request_id": req, "product_id": product_id, "field": field,
            "verdict": verdict, "device_key": device_key,
        }
    except Exception:
        return None


def build_coverage_row(*, day: Any, metric: Any, value: Any, n: Any) -> Optional[Dict[str, Any]]:
    try:
        num = None
        if (
            not isinstance(value, bool)
            and isinstance(value, (int, float, Decimal))
            and not (isinstance(value, float) and not math.isfinite(value))
        ):
            num = Decimal(str(value))
        ok = (
            isinstance(day, date) and not isinstance(day, datetime)
            and _sql_match(KB_METRIC_REGEX, metric)
            and num is not None and num.is_finite()
            and _is_int(n) and 0 <= n <= _INT4_MAX
        )
        if not ok:
            return None
        # str(date) is its isoformat(); the date CHECK above is the one barrier (F1-7)
        return {"day": str(day), "metric": metric, "value": str(num), "n": n}
    except Exception:
        return None
