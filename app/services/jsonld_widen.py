"""S81-G1 unit D08 JSONLD-WIDEN: the JSON-LD image / identifier / rating leaf.

Two flags, new names, default OFF, read PER CALL (never cached at import):

  ENABLE_IMAGE_PIPELINE_V2  the Product node's first ALLOWED image rides the
                            reduced price result as ``price["image_url"]`` and
                            its identifiers (a GTIN with a valid GS1 check digit,
                            the sku, the node's size text) ride it as the
                            internal ``price["_jsonld_facts"]``; the Tier 1.5
                            piggyback promotes a page image only under the same
                            image policy (http refused).
  ENABLE_JSONLD_RATING      rating channel 1: the Product node's own
                            AggregateRating, rescaled to 5, as
                            ``_jsonld_facts["rating"]``; the orchestrator fills
                            an EMPTY rating slot with it only for a host whose
                            persisted robots record allows the page (see
                            ``rating_host_allowed``), and the callers stop
                            asking the model for a rating.

THE IMAGE POLICY (``allowed_image_url``): https only, a public host name (no IP
literal, no localhost, no private or reserved suffix), a raster type judged by
the PATH extension (no fetch, no sniff), never a DENY_HOSTS host (fragrantica /
parfumo / basenotes / fimgs.net; checked unconditionally, not behind the D03
flag), and an allowlisted host: first-party to the page, a named platform CDN
(``IMAGE_CDN_HOSTS``) or an official brand domain handed in by the caller.

THE CHANNEL-1 HOST RULE (``rating_host_allowed``) is fail-CLOSED: the host's
registry row must be live and not denied, its persisted robots record
(``kb_merchants.robots``, the S81-15 contract) must say ``allow``, be fresh
(before ``next_reread`` + ``ROBOTS_GRACE``), allow the page path under BOTH
of its stored rule lists, ``rules.qarenbot`` (our named agent) and
``rules.star`` (``*``), the most restrictive of the two (``rules_allow``; this
leaf only evaluates the persisted lists, it sends no user agent), carry no
``rules_truncated`` marker, and the host must have no parked challenge. The
record reader is the seam ``ROBOTS_ENTRY_LOOKUP``, which answers nothing until
D14 LIVE-ROBOTS wires it (RULINGS_S81_G1 R-G1-1), so before D14 no channel-1
rating is ever produced.

A stdlib leaf: it imports only os / re / math / ipaddress / datetime /
urllib.parse and the in-repo leaves ``deny_hosts`` and ``robots_eval``; never
price_service, the orchestrator or any I/O module; it has no logger (no new log
line). Every public function is pure and total: it never raises.
"""
from __future__ import annotations

import ipaddress
import math
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Mapping, Optional
from urllib.parse import urlsplit

from app.services import deny_hosts, robots_eval

_TRUTHY = ("true", "1", "yes", "on")


def image_pipeline_v2_enabled() -> bool:
    """True iff ``ENABLE_IMAGE_PIPELINE_V2`` is set truthy. Read PER CALL."""
    return os.getenv("ENABLE_IMAGE_PIPELINE_V2", "false").strip().lower() in _TRUTHY


def jsonld_rating_enabled() -> bool:
    """True iff ``ENABLE_JSONLD_RATING`` is set truthy. Read PER CALL."""
    return os.getenv("ENABLE_JSONLD_RATING", "false").strip().lower() in _TRUTHY


# ---------------------------------------------------------------------------
# constants (test seams)
# ---------------------------------------------------------------------------
#: Raster image types, judged by the URL PATH extension (query and fragment are
#: ignored). No fetch and no content sniff, by design (spec Q5).
RASTER_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")

#: The platform CDNs of the registry's $0-adapter platforms (Shopify, Salla,
#: Zid). Matched by suffix. A retailer whose JSON-LD image sits on another CDN
#: keeps the eager cascade image (a stated limit; a measured follow-up widens it).
IMAGE_CDN_HOSTS = ("cdn.shopify.com", "cdn.salla.sa", "cdn.salla.network", "media.zid.store")

#: How long past ``next_reread`` a persisted robots record still counts as fresh.
ROBOTS_GRACE = timedelta(hours=24)

#: Caps on the identifier texts carried in ``_jsonld_facts``.
SKU_MAX_CHARS = 64
SIZE_MAX_CHARS = 64

_NON_PUBLIC_SUFFIXES = (".local", ".internal", ".localhost", ".test", ".invalid")
# Whitespace, control characters and the backslash have no place inside an
# image URL a client will load (a WHATWG parser reads a backslash as a path
# separator, so the authority would differ from the one checked here).
_UNSAFE_URL_CHARS = re.compile("[\\x00-\\x20\\x7f\\\\]")
_ASCII_DIGITS = re.compile("[0-9]+")
_GTIN_LENGTHS = (8, 12, 13, 14)
_ROBOTS_ACTIONS = ("allow", "disallow")


# ---------------------------------------------------------------------------
# small total helpers
# ---------------------------------------------------------------------------
def _finite_number(value: Any) -> Optional[float]:
    """A real, finite int / float as a float; None for anything else (a bool,
    a string, inf, nan)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def _url_host(url: Any) -> str:
    """The lower-cased host of an absolute URL without port, userinfo or a
    trailing dot; "" when there is none or the URL does not parse."""
    if not isinstance(url, str):
        return ""
    try:
        host = urlsplit(url.strip()).hostname or ""
    except ValueError:
        return ""
    return host.rstrip(".")


def _public_host(host: str) -> bool:
    """A host NAME the public internet can resolve: not an IP literal, not
    localhost, at least one dot, no private / reserved suffix, and a last label
    that is not all digits (``1.2.3`` style numeric forms are IP-like)."""
    if not host or "." not in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    if host == "localhost" or host.endswith(_NON_PUBLIC_SUFFIXES):
        return False
    return not host.rsplit(".", 1)[-1].isdigit()


def _domain_set(values: Any) -> set:
    out = set()
    if isinstance(values, (set, frozenset, list, tuple)):
        for value in values:
            if isinstance(value, str):
                host = _strip_www(value.strip().lower().rstrip("."))
                if host:
                    out.add(host)
    return out


def _image_host_allowlisted(host: str, page_url: Any, brand_domains: Any) -> bool:
    bare = _strip_www(host)
    page_host = _strip_www(_url_host(page_url))
    if page_host and (bare == page_host or bare.endswith("." + page_host)):
        return True
    for cdn in IMAGE_CDN_HOSTS:
        if host == cdn or host.endswith("." + cdn):
            return True
    return bare in _domain_set(brand_domains)


# ---------------------------------------------------------------------------
# the image and identifier policy
# ---------------------------------------------------------------------------
def allowed_image_url(url: Any, page_url: Any, brand_domains: Any = ()) -> Optional[str]:
    """The stripped ``url`` when it passes the image policy (module docstring),
    else None. Pure, never raises, never fetches."""
    if not isinstance(url, str):
        return None
    text = url.strip()
    if not text or _UNSAFE_URL_CHARS.search(text):
        return None
    try:
        parts = urlsplit(text)
        host = (parts.hostname or "").rstrip(".")
    except ValueError:
        return None
    if parts.scheme.lower() != "https" or not parts.netloc or "@" in parts.netloc:
        return None
    if not _public_host(host):
        return None
    if not (parts.path or "").lower().endswith(RASTER_EXTENSIONS):
        return None
    if deny_hosts.is_denied_url(text):
        return None
    if not _image_host_allowlisted(host, page_url, brand_domains):
        return None
    return text


def valid_gtin(text: Any) -> Optional[str]:
    """A GTIN-8 / -12 / -13 / -14 as its digit string, or None.

    Spaces and hyphens are removed; what remains must be ASCII digits only, of
    one of the four GTIN lengths, not all zeros (a placeholder, never an
    allocated GTIN), and the GS1 mod-10 check digit must match (weights 3, 1,
    3, ... from the right, the check digit excluded)."""
    if not isinstance(text, str):
        return None
    digits = text.replace(" ", "").replace("-", "")
    if len(digits) not in _GTIN_LENGTHS or not _ASCII_DIGITS.fullmatch(digits):
        return None
    if digits.strip("0") == "":
        return None
    body = digits[:-1]
    total = 0
    for index, char in enumerate(reversed(body)):
        total += int(char) * (3 if index % 2 == 0 else 1)
    check = (10 - total % 10) % 10
    return digits if check == int(digits[-1]) else None


def _scalar_text(value: Any) -> str:
    """A schema.org Text-ish scalar as one stripped string ("" when unusable):
    a string, a finite number (an integral float without its ``.0``), or the
    first usable member of a list. Never raises."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        if value.is_integer():
            try:
                return str(int(value))
            except (OverflowError, ValueError):
                return ""
        return repr(value)
    if isinstance(value, int):
        try:
            return str(value)
        except ValueError:
            return ""
    if isinstance(value, list):
        for item in value:
            text = _scalar_text(item)
            if text:
                return text
    return ""


def size_text(value: Any) -> str:
    """The schema.org ``size`` of a Product node as a short text ("" when
    unusable): a Text as is, a QuantitativeValue node as "<value> <unitText or
    unitCode>", a list by its first usable member; capped at SIZE_MAX_CHARS."""
    if isinstance(value, list):
        for item in value:
            text = size_text(item)
            if text:
                return text
        return ""
    if isinstance(value, dict):
        amount = _scalar_text(value.get("value"))
        unit = _scalar_text(value.get("unitText")) or _scalar_text(value.get("unitCode"))
        if amount and unit:
            text = amount + " " + unit
        else:
            text = _scalar_text(value.get("name")) or amount
        return text[:SIZE_MAX_CHARS].strip()
    return _scalar_text(value)[:SIZE_MAX_CHARS].strip()


def rating_fact(aggregate_rating: Any) -> Optional[Dict[str, Any]]:
    """The candidate's ``aggregate_rating`` ({rating_value[, review_count]
    [, best_rating]}) rescaled to a 5-point scale: {"value": v5, "count": n or
    None}, or None. ``v5 = round(rating_value * 5 / best, 1)`` with ``best``
    the declared bestRating (5 when undeclared); kept only inside 1.0..5.0.
    ``worstRating`` is ignored (a stated limit)."""
    if not isinstance(aggregate_rating, dict):
        return None
    value = _finite_number(aggregate_rating.get("rating_value"))
    if value is None or value <= 0:
        return None
    best = _finite_number(aggregate_rating.get("best_rating"))
    if best is None or best <= 0:
        best = 5.0
    scaled = round(value * 5.0 / best, 1)
    if not (math.isfinite(scaled) and 1.0 <= scaled <= 5.0):
        return None
    count = aggregate_rating.get("review_count")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        count = None
    return {"value": scaled, "count": count}


def stamp_jsonld_facts(result: Any, price_data: Any, page_url: Any,
                       brand_domains: Any = ()) -> Any:
    """Stamp the JSON-LD facts of ``price_data`` (the matched candidate) onto
    the reduced price ``result``, in place, and return it.

    Under ENABLE_IMAGE_PIPELINE_V2: ``result["image_url"]`` = the FIRST entry of
    the candidate's image list that ``allowed_image_url`` accepts (the key is
    omitted when none is accepted), and the gtin / sku / size members of
    ``result["_jsonld_facts"]``. Under ENABLE_JSONLD_RATING: its ``rating``
    member (``rating_fact``). The facts key is omitted when it would be empty;
    the ``_`` prefix keeps it out of the public price (``public_price_view``
    with the exact gate ON). Each flag is re-read here for its own members."""
    image_on = image_pipeline_v2_enabled()
    rating_on = jsonld_rating_enabled()
    if not (image_on or rating_on):
        return result
    if not isinstance(result, dict) or not isinstance(price_data, dict):
        return result
    facts: Dict[str, Any] = {}
    if image_on:
        images = price_data.get("image")
        if isinstance(images, str):
            images = [images]
        if isinstance(images, list):
            for candidate in images:
                accepted = allowed_image_url(candidate, page_url, brand_domains)
                if accepted:
                    result["image_url"] = accepted
                    break
        gtin = valid_gtin(price_data.get("gtin"))
        if gtin:
            facts["gtin"] = gtin
        sku = price_data.get("sku")
        if isinstance(sku, str) and sku.strip():
            facts["sku"] = sku.strip()[:SKU_MAX_CHARS]
        size = price_data.get("size")
        if isinstance(size, str) and size.strip():
            facts["size"] = size.strip()[:SIZE_MAX_CHARS]
    if rating_on:
        rating = rating_fact(price_data.get("aggregate_rating"))
        if rating:
            facts["rating"] = rating
    if facts:
        result["_jsonld_facts"] = facts
    return result


# ---------------------------------------------------------------------------
# the channel-1 host rule (robots, fail-closed)
# ---------------------------------------------------------------------------
def rules_allow(rules: Any, url: Any) -> bool:
    """True iff the persisted robots ``rules`` list ([[allow|disallow, pattern],
    ...], one agent's merged rules) allows the path + query of ``url``.

    Unlike ``robots_eval.can_fetch``, a ';' path param is kept (D14 picks one normalisation); same rule order (the longest matching
    pattern wins by ``robots_eval._match_len``, allow wins a tie, an empty list
    allows) but FAIL-CLOSED: a non-list, a malformed rule (wrong arity, an
    unknown action, a non-str pattern), a non-str URL or any error is False."""
    try:
        if not isinstance(rules, (list, tuple)) or not isinstance(url, str):
            return False
        text = url.strip()
        parsed = urlsplit(text if "://" in text else "//" + text)
        path = parsed.path or "/"
        if parsed.query:
            path = path + "?" + parsed.query
        best_len, best_allow = 0, True
        for rule in rules:
            if not isinstance(rule, (list, tuple)) or len(rule) != 2:
                return False
            action, pattern = rule[0], rule[1]
            if action not in _ROBOTS_ACTIONS or not isinstance(pattern, str):
                return False
            is_allow = action == "allow"
            length = robots_eval._match_len(pattern, path)
            if length > best_len or (length == best_len and length > 0 and is_allow):
                best_len, best_allow = length, is_allow
        return best_allow is True
    except Exception:  # noqa: BLE001 -- fail-closed: an error never allows
        return False


def _aware(moment: Any) -> Optional[datetime]:
    if not isinstance(moment, datetime):
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def _parse_ts(value: Any) -> Optional[datetime]:
    """An ISO-8601 timestamp ("Z" accepted) or a datetime as an aware UTC-based
    datetime; None when absent or unparseable."""
    if isinstance(value, datetime):
        return _aware(value)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return _aware(parsed)


def _challenge_clear(challenge: Any, now: datetime) -> bool:
    """No parked challenge: absent, a DB NULL (None, GATE GC-3) or {}; or a
    ``parked_until`` that parses and is not in the future. A vendor without a
    parsable ``parked_until`` counts as parked."""
    if challenge is None:
        return True
    if not isinstance(challenge, dict):
        return False
    if not challenge:
        return True
    parked_until = _parse_ts(challenge.get("parked_until"))
    return parked_until is not None and parked_until <= now


def rating_host_allowed(entry: Any, page_url: Any, now: Any) -> bool:
    """The fail-closed channel-1 rule (module docstring) over one host's
    registry row view ``entry`` = {"status", "deny", "robots", "challenge"}
    (the ``kb_merchants`` columns of those names) for ``page_url`` at ``now``."""
    try:
        if not isinstance(entry, dict) or entry.get("deny"):
            return False
        if entry.get("status") != "live":
            return False
        if not isinstance(page_url, str):
            return False
        host = _url_host(page_url)
        if not host or deny_hosts.is_denied_host(host) or deny_hosts.is_denied_url(page_url):
            return False
        robots = entry.get("robots")
        if not isinstance(robots, dict) or robots.get("state") != "allow":
            return False
        if robots.get("rules_truncated"):
            return False
        moment = _aware(now)
        fetched_at = _parse_ts(robots.get("fetched_at"))
        next_reread = _parse_ts(robots.get("next_reread"))
        if moment is None or fetched_at is None or next_reread is None:
            return False
        if not moment < next_reread + ROBOTS_GRACE:
            return False
        rules = robots.get("rules")
        if not isinstance(rules, dict):
            return False
        if not rules_allow(rules.get("qarenbot"), page_url):
            return False
        if not rules_allow(rules.get("star"), page_url):
            return False
        return _challenge_clear(entry.get("challenge"), moment)
    except Exception:  # noqa: BLE001 -- fail-closed: an error never allows
        return False


# ---------------------------------------------------------------------------
# the reader seam (the D14 hand-off) and the clock seam
# ---------------------------------------------------------------------------
def _no_entry(host: str) -> Optional[Mapping[str, Any]]:
    """The default robots-record reader: no entry for any host. D08 reads no
    database (no live reader of the persisted verdict exists yet); D14
    LIVE-ROBOTS assigns ``ROBOTS_ENTRY_LOOKUP`` (RULINGS_S81_G1 R-G1-1)."""
    return None


#: host (``deny_hosts.normalize_host`` form) -> the host's registry row view or
#: None. Read as a module attribute at call time, so an assignment (D14, or a
#: test patch) takes effect on the next call.
ROBOTS_ENTRY_LOOKUP: Callable[[str], Optional[Mapping[str, Any]]] = _no_entry


def _now() -> datetime:
    """The clock seam: the current UTC time."""
    return datetime.now(timezone.utc)


def iso_z(moment: Any) -> Optional[str]:
    """``moment`` as ``%Y-%m-%dT%H:%M:%SZ`` in UTC (the S81-15 record form);
    None for a non-datetime."""
    aware = _aware(moment)
    if aware is None:
        return None
    return aware.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def channel1_rating(price: Any, now: Any) -> Optional[Dict[str, Any]]:
    """The channel-1 rating of one product's price dict, or None.

    Reads ``price["_jsonld_facts"]["rating"]`` (the stamp's rating member) and
    ``price["url"]``, looks the page host up through ``ROBOTS_ENTRY_LOOKUP`` and
    applies ``rating_host_allowed``; returns {"value", "count", "source": the
    host, "url": the price url, "extract_method": "jsonld_aggregate_rating"}.
    A lookup that raises answers None (fail-closed)."""
    if not isinstance(price, dict):
        return None
    facts = price.get("_jsonld_facts")
    if not isinstance(facts, dict):
        return None
    rating = facts.get("rating")
    if not isinstance(rating, dict):
        return None
    value = _finite_number(rating.get("value"))
    if value is None or not 1.0 <= value <= 5.0:
        return None
    count = rating.get("count")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        count = None
    url = price.get("url")
    if not isinstance(url, str) or not url.strip():
        return None
    url = url.strip()
    host = deny_hosts.normalize_host(_url_host(url))
    if not host:
        return None
    try:
        entry = ROBOTS_ENTRY_LOOKUP(host)
    except Exception:  # noqa: BLE001 -- a failing reader is no entry
        return None
    if not rating_host_allowed(entry, url, now):
        return None
    return {
        "value": value,
        "count": count,
        "source": host,
        "url": url,
        "extract_method": "jsonld_aggregate_rating",
    }


def channel1_rating_source(ch1: Mapping[str, Any], now: Any) -> Dict[str, Any]:
    """The ``rating_source`` a channel-1 rating writes into an EMPTY rating
    slot (``rating_verified`` stays False: one retailer's aggregate, not the
    cross-seller consensus)."""
    return {
        "name": "%s (product page)" % ch1.get("source"),
        "url": ch1.get("url"),
        "retrieved_at": iso_z(now),
        "extract_method": "jsonld_aggregate_rating",
        "confidence": "medium",
    }
