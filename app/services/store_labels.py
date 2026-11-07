"""S81-18b STORE-LABEL: the display name of a price's store, from a repo data table.

Flag ``ENABLE_STORE_LABEL`` (default OFF, read PER CALL by :func:`store_label_enabled`,
the house boolean idiom): the response builder's price-dict pass calls
:func:`label_prices` only under it, so with the flag OFF the table is never read
(no stat, no open) and every body is byte-identical.

The table ``data/merchant_labels.json`` (``{"version": 1, "labels": {<host>: {"en": ...,
"ar": ...}}}``) is keyed by ``deny_hosts.normalize_host``; every value is a non-empty
display name with no URL shape and the AR values carry no harakat, shadda, tanween or
superscript alef. Any invalid row makes the WHOLE table unavailable (fail safe: every
price then renders its retailer string, today's behaviour) with ONE WARNING per file
state. The file is read through a stat-keyed cache (the category_gate lexicon pattern):
one os.stat per load, a parse only when (path, mtime_ns, size) changes.

:func:`label_for`: the row of the normalised retailer host, else the row of the
normalised host of the price url (a name-shaped retailer such as a brand store), in
the request's language (``ar`` -> the AR label, anything else -> EN); no row -> the
retailer string as-is when it is a non-empty str, else None.

Test seams: ``LABELS_PATH`` (a module attribute read per load) and
:func:`_reset_label_cache`. Log lines carry constants and type names only, never a
label, a host or a URL.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from app.services.deny_hosts import normalize_host

logger = logging.getLogger(__name__)

_TRUTHY = ("true", "1", "yes", "on")
LABELS_PATH = Path(__file__).resolve().parents[2] / "data" / "merchant_labels.json"
LABEL_LANGS: Tuple[str, ...] = ("en", "ar")
# A bare lower-case DNS host with at least one dot (the kb_merchants host shape).
_HOST_RX = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
# Arabic tanween, harakat, shadda, sukun (U+064B..U+0652) and the superscript alef (U+0670).
_DIACRITICS = frozenset(list(range(0x064B, 0x0653)) + [0x0670])

_LABEL_LOCK = threading.Lock()
_LABEL_CACHE: Dict[str, Any] = {"key": None, "labels": None}
_LABEL_WARNED: set = set()
_LABEL_WARNED_CAP = 64


def store_label_enabled() -> bool:
    """True iff ``ENABLE_STORE_LABEL`` is truthy. Read PER CALL."""
    return os.getenv("ENABLE_STORE_LABEL", "false").strip().lower() in _TRUTHY


def _reset_label_cache() -> None:
    """Test seam: forget the cached table and the warned file states."""
    with _LABEL_LOCK:
        _LABEL_CACHE["key"] = None
        _LABEL_CACHE["labels"] = None
        _LABEL_WARNED.clear()


def _valid_value(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    return not ("/" in value or ":" in value or "http" in value.lower())


def _compile(raw: Any) -> Dict[str, Dict[str, str]]:
    if not isinstance(raw, dict) or raw.get("version") != 1:
        raise ValueError("labels version")
    labels = raw.get("labels")
    if not isinstance(labels, dict):
        raise ValueError("labels section")
    out: Dict[str, Dict[str, str]] = {}
    for host, row in labels.items():
        if not isinstance(host, str) or host != normalize_host(host) or not _HOST_RX.match(host):
            raise ValueError("labels host")
        if not isinstance(row, dict) or set(row) != set(LABEL_LANGS):
            raise ValueError("labels row")
        if not all(_valid_value(row[lang]) for lang in LABEL_LANGS):
            raise ValueError("labels value")
        if any(ord(ch) in _DIACRITICS for ch in row["ar"]):
            raise ValueError("labels diacritic")
        out[host] = {"en": row["en"], "ar": row["ar"]}
    return out


def _unavailable(state: tuple, exc: BaseException) -> Dict[str, Dict[str, str]]:
    with _LABEL_LOCK:
        if state not in _LABEL_WARNED:
            if len(_LABEL_WARNED) >= _LABEL_WARNED_CAP:
                _LABEL_WARNED.clear()
            _LABEL_WARNED.add(state)
            logger.warning("[STORE_LABEL] table unavailable type=%s", type(exc).__name__)
    return {}


def load_labels() -> Dict[str, Dict[str, str]]:
    """The validated table (host -> {en, ar}); ``{}`` when missing / invalid, with ONE
    WARNING per file state. Never raises."""
    path = LABELS_PATH
    try:
        stat = os.stat(path)
    except OSError as exc:
        return _unavailable((str(path), None, None), exc)
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    with _LABEL_LOCK:
        if _LABEL_CACHE["key"] == key and _LABEL_CACHE["labels"] is not None:
            return _LABEL_CACHE["labels"]
    try:
        with open(path, "r", encoding="utf-8") as handle:
            labels = _compile(json.load(handle))
    except Exception as exc:  # noqa: BLE001 -- fail safe: an unusable table labels nothing
        labels = _unavailable(key, exc)
    with _LABEL_LOCK:
        _LABEL_CACHE["key"] = key
        _LABEL_CACHE["labels"] = labels
    return labels


def _url_host(url: Any) -> str:
    if not isinstance(url, str):
        return ""
    text = url.strip()
    if not text.lower().startswith(("http://", "https://")):
        return ""
    try:
        return normalize_host(urlsplit(text).hostname or "")
    except ValueError:
        return ""


def label_for(price: Any, lang: Any, labels: Optional[Dict[str, Dict[str, str]]] = None) -> Optional[str]:
    """The store label of one price dict in the request's language (see the module doc)."""
    if not isinstance(price, dict):
        return None
    table = load_labels() if labels is None else labels
    retailer = price.get("retailer")
    row = table.get(normalize_host(retailer))
    if row is None:
        host = _url_host(price.get("url"))
        row = table.get(host) if host else None
    if row is not None:
        is_ar = isinstance(lang, str) and lang.strip().lower() == "ar"
        return row["ar"] if is_ar else row["en"]
    if isinstance(retailer, str) and retailer:
        return retailer
    return None


def _price_slots(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    slots: List[Dict[str, Any]] = []
    overview = result.get("overview")
    for products in (result.get("products"), overview.get("products") if isinstance(overview, dict) else None):
        if not isinstance(products, list):
            continue
        for product in products:
            if isinstance(product, dict) and isinstance(product.get("price"), dict):
                slots.append(product)
    return slots


def label_prices(result: Any, lang: Any) -> None:
    """Add ``store_label`` to every price dict of the built body (``products[i].price``
    and ``overview.products[i].price``). Every label is computed FIRST, then each slot
    gets a NEW price dict (``{**price, "store_label": label}``): a price object is never
    mutated. A non-dict price is skipped."""
    if not isinstance(result, dict):
        return
    labels = load_labels()
    slots = _price_slots(result)
    computed = [label_for(product["price"], lang, labels) for product in slots]
    for product, label in zip(slots, computed, strict=True):
        product["price"] = {**product["price"], "store_label": label}
