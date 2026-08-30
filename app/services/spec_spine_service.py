"""UNIT D2 — the fragrance SPEC SPINE lookup (``ENABLE_SPEC_SPINE``, default OFF).

WHAT THIS IS. A read-only index of fragrance spec facts that do not change
between comparisons — scent family, the top/heart/base note lists,
concentration, longevity/sillage, season/occasion — keyed on a normalised
brand+name identity. The per-compare specs path consults it BEFORE the specs
LLM call; a hit fills those fields for free and the LLM is then asked only for
what the spine lacks.

WHY IT EXISTS (B5's measurement, not a guess). The signal is ALREADY on the
PDPs the corpora cache: of 79 CAPTURED Gulf fragrance pages, 47 carry note
lists, 56 carry family/accords, 48 carry concentration, 57 carry a size. Today
that prose is parsed for a price and then discarded, and every single
comparison pays a fresh specs completion to re-derive facts that were true
last week and will be true next week. The spine turns that per-compare cost
into ONE amortised extraction per FRAGRANCE, run off-clock by
``scripts/seed_spec_spine.py``.

WHAT IS DELIBERATELY ABSENT. ``perfumer`` (13/79) and ``launch_year`` (7/79)
are too sparse in the corpora to seed honestly — a field that is present on
one page in six is a field the extractor would be tempted to fill from memory,
which is precisely the fabrication A3/D1 just closed. They are not in
``SPINE_FIELDS`` and ``spine_specs_for`` drops them even if a hand-written
store row carries them. ``volume`` is absent for a different reason: it is a
per-LISTING fact (the 50ml and the 100ml bottle are different SKUs at
different prices), so it belongs to the price/identity path, not to a
per-fragrance spine. ``heat_stability`` is absent because it is an INFERENCE
about Gulf climate performance, not something a PDP states.

THE KEY, AND WHY IT REUSES THE PRICE PATH'S MACHINERY. A spine row is a claim
about one specific juice, so the key must (a) collapse the same fragrance
written by different retailers onto one row and (b) never merge two juices
that differ on a real axis. Both properties already exist, tested, on the
price path, so the key COMPOSES those helpers instead of introducing a second
normaliser that would drift:

  * ``price_service._identity_tokens_ps`` — diacritic-folded identity tokens
    minus the brand (and its alias group), the concentration phrase, every
    measurement token and the form noise. This is what makes "Sauvage Eau de
    Parfum 100ml Spray for Men" and "Sauvage EDP 100 ml Natural Spray" the
    same set.
  * ``price_service._category_padding("fragrances")`` — the fragrance
    marketing/gender/product-word padding ("for", "natural", "spray",
    "perfume", "pour homme"). ``_identity_tokens_ps`` applies the VARIANT
    qualifiers, not this padding set, so it is subtracted here — otherwise a
    retailer that writes "for Men" gets its own row.
  * ``price_service._BRAND_ALIAS_GROUPS`` — so "YSL" and "Yves Saint Laurent",
    "Dior" and "Christian Dior" resolve to one brand axis.
  * ``price_service.extract_concentration`` / ``extract_size_ml_any`` — the
    two axes that must SPLIT. EDP and EDT are different compositions with
    different notes; merging them would let the spine serve one fragrance's
    notes for another with total confidence. Size is split for the same
    reason the price path splits it: it is a stated axis of the product name,
    and an entry seeded from a 100ml page has not been shown to describe the
    5ml decant. That costs hit-rate (a 50ml query misses a 100ml row) and it
    is the conservative side of the trade: a spine MISS is one ordinary LLM
    call, a spine mis-hit is a confident wrong answer cached for 7 days.

STORAGE. A local JSON file, ``data/spec_spine.json``, which ships EMPTY
(``{}``) — the unit is dark on arrival twice over: the flag is off AND there
is nothing to serve. ``migrations/035_spec_spine.sql`` (UNAPPLIED, see its
header) carries the Supabase table this should become once the store outgrows
a file; until that migration is applied and ``SPEC_SPINE_TABLE`` names the
table, no Supabase call is ever made.

FLAG DISCIPLINE (house rule 1). ``ENABLE_SPEC_SPINE`` is read PER CALL via
``os.getenv`` — never cached at import — copying
``price_service.exact_gate_enabled``, so Railway can flip it without a
restart. Flag OFF, ``spine_specs_for`` returns ``{}`` before it touches the
store, and the specs path is byte-identical to main.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# The provenance tag stamped on every field the spine fills. It rides the
# existing ``<field>_source`` channel (the same one `extract_specs` uses for
# "snippet_3" / "training"), so a spine value is distinguishable from a
# snippet-cited one everywhere downstream without a new response key.
SPINE_SOURCE_TAG = "spec_spine"

# The ONLY fields a spine entry may serve. A subset of
# CATEGORY_SPEC_SCHEMAS["fragrances"] — see the module docstring for why
# volume / heat_stability (and the never-schema'd perfumer / launch_year) are
# excluded. Anything else in a store row is dropped on read.
SPINE_FIELDS: Tuple[str, ...] = (
    "scent_family",
    "notes_top",
    "notes_heart",
    "notes_base",
    "longevity",
    "sillage",
    "season",
    "occasion",
    "concentration",
)

# The spine is a FRAGRANCE artifact. Every other category short-circuits to a
# miss regardless of what the store happens to contain.
SPINE_CATEGORY = "fragrances"

# repo_root/data/spec_spine.json  (this file is repo_root/app/services/…)
DEFAULT_STORE_PATH = str(Path(__file__).resolve().parents[2] / "data" / "spec_spine.json")

# Parsed-store memo, keyed on (path, mtime_ns, size). A store edit (or a seed
# run) invalidates it on the next call without a restart; `reset_store_cache`
# exists for tests. This is NOT a flag cache — the flag is re-read every call.
_STORE_CACHE: Dict[Tuple[str, int, int], Dict[str, Any]] = {}


def spec_spine_enabled() -> bool:
    """True iff the spec spine may be consulted (default OFF).

    Read per call from ``os.getenv`` — never cached at import — so Railway can
    flip it without a restart (the ``price_service.exact_gate_enabled`` idiom,
    house rule 1). Flag OFF is byte-identical to main: ``spine_specs_for``
    returns ``{}`` before it reads the store, so ``_get_specs`` never grows a
    ``skip_fields`` argument and the specs prompt renders exactly as it does
    today.
    """
    return os.getenv("ENABLE_SPEC_SPINE", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def store_path() -> str:
    """The local JSON store to read. ``SPEC_SPINE_STORE_PATH`` overrides the
    shipped ``data/spec_spine.json`` (used by the seeder's ``--out`` and by
    tests); read per call for the same reason the flag is."""
    return (os.getenv("SPEC_SPINE_STORE_PATH") or "").strip() or DEFAULT_STORE_PATH


def _supabase_table() -> Optional[str]:
    """The Supabase table to read INSTEAD of the local file, or None.

    Two conditions, both required: the feature flag is ON and
    ``SPEC_SPINE_TABLE`` names a table. Migration 035 is deliberately NOT
    applied, so on today's infrastructure this is always None and no Supabase
    client is ever constructed.
    """
    if not spec_spine_enabled():
        return None
    return (os.getenv("SPEC_SPINE_TABLE") or "").strip() or None


def reset_store_cache() -> None:
    """Drop the parsed-store memo (tests; also safe to call operationally)."""
    _STORE_CACHE.clear()


def load_store(path: Optional[str] = None) -> Dict[str, Any]:
    """The parsed local store, or ``{}``.

    NEVER raises: a missing file (the normal state before the first seed run),
    a truncated write, or a hand-edit that broke the JSON all degrade to an
    empty store — i.e. to a spine MISS, which costs one ordinary LLM call. A
    spine that could crash the specs path would be worse than no spine.
    """
    p = path or store_path()
    try:
        st = os.stat(p)
        cache_key = (p, st.st_mtime_ns, st.st_size)
    except OSError:
        return {}
    cached = _STORE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        with io.open(p, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        logger.warning("[spec_spine] store %s unreadable (%s) — treating as empty", p, exc)
        return {}
    if not isinstance(data, dict):
        logger.warning("[spec_spine] store %s is not a JSON object — treating as empty", p)
        return {}
    _STORE_CACHE.clear()  # only ever one store in play; keep the memo O(1)
    _STORE_CACHE[cache_key] = data
    return data


def _brand_axis(brand: str) -> str:
    """The brand component of the key, folded through the price path's
    ``_BRAND_ALIAS_GROUPS`` so an abbreviation and the spelled-out house name
    ("YSL" / "Yves Saint Laurent", "Dior" / "Christian Dior") produce the SAME
    axis. When the brand is in a group, the GROUP itself is the canonical form
    — that is alias-order-independent, so it cannot matter which spelling the
    seeder happened to see first."""
    from app.services.price_service import (
        _BRAND_ALIAS_GROUPS,
        _fold_identity,
        normalize_words,
    )

    words = normalize_words(_fold_identity(brand or ""))
    for group in _BRAND_ALIAS_GROUPS:
        if words & group:
            return "+".join(sorted(group))
    return "+".join(sorted(words))


def spine_key(
    brand: str,
    name: str,
    variant: Optional[str] = None,
    category: str = SPINE_CATEGORY,
) -> str:
    """The store key for one fragrance: ``<cat>|<brand>|<identity>|<conc>|<ml>``.

    Composed entirely from the price path's identity machinery (see the module
    docstring). Two retailer titles for the same juice produce the same string;
    a different concentration or a different bottle size produces a different
    one. Pure and deterministic — no I/O, no flag read — so the seeder and the
    runtime lookup cannot disagree about what a fragrance is.
    """
    from app.services.price_service import (
        _category_padding,
        _identity_tokens_ps,
        extract_concentration,
        extract_size_ml_any,
    )

    cat = (category or SPINE_CATEGORY).strip().lower()
    surface = " ".join(x for x in (brand, name, variant) if x).strip()
    tokens = _identity_tokens_ps(surface, brand=brand or "", category=cat)
    # `_identity_tokens_ps` strips the VARIANT qualifiers but not the category
    # PADDING, so "for"/"natural"/"spray"/"perfume"/"pour homme" survive it and
    # would give every retailer phrasing its own row. Subtract the padding set
    # the superset guard already uses for this category.
    tokens = tokens - _category_padding(cat)
    identity = "-".join(sorted(tokens))
    conc = extract_concentration(surface) or "-"
    ml = extract_size_ml_any(surface)
    return "|".join((cat, _brand_axis(brand), identity, conc, str(ml) if ml else "-"))


def _entry_specs(entry: Any) -> Dict[str, str]:
    """The ``SPINE_FIELDS`` a store entry actually carries, as strings.

    Filters hard: a row that carries ``launch_year``/``perfumer`` (B5: too
    sparse to seed honestly) or any non-spine key contributes nothing. Empty /
    "N/A" values are treated as ABSENT so a placeholder in the store can never
    displace a real LLM answer downstream.
    """
    if not isinstance(entry, dict):
        return {}
    raw = entry.get("specs")
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for field in SPINE_FIELDS:
        val = raw.get(field)
        if val is None:
            continue
        text = ", ".join(str(v) for v in val) if isinstance(val, list) else str(val)
        text = text.strip()
        if not text or text.lower() in ("n/a", "na", "null", "none"):
            continue
        out[field] = text
    return out


def _lookup_supabase_sync(key: str, table: str) -> Optional[Dict[str, Any]]:
    """One row from the Supabase spine table, or None. Blocking — always
    called through ``asyncio.to_thread``. Never raises: any client/schema/
    network failure degrades to None, which falls back to the local store."""
    try:
        from app.services.database_service import get_admin_supabase_client

        client = get_admin_supabase_client()
        res = (
            client.table(table)
            .select("spine_key,specs,seed_pages,seeded_at")
            .eq("spine_key", key)
            .limit(1)
            .execute()
        )
        rows = getattr(res, "data", None) or []
        return rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001 — a spine read must never break specs
        logger.warning("[spec_spine] supabase lookup failed for %s (%s)", key, exc)
        return None


async def lookup(
    brand: str,
    name: str,
    variant: Optional[str] = None,
    category: str = SPINE_CATEGORY,
) -> Optional[Dict[str, Any]]:
    """The raw store entry for this fragrance, or None.

    Supabase FIRST but only when ``_supabase_table()`` names one (flag ON +
    ``SPEC_SPINE_TABLE`` set + migration 035 applied); otherwise, and on any
    Supabase failure, the local JSON store. Does NOT check the feature flag
    itself — ``spine_specs_for`` is the gate — so the seeder and tests can read
    the store directly.
    """
    key = spine_key(brand, name, variant, category)
    table = _supabase_table()
    if table:
        row = await asyncio.to_thread(_lookup_supabase_sync, key, table)
        if row:
            return row
    entry = load_store().get(key)
    return entry if isinstance(entry, dict) else None


async def spine_specs_for(
    brand: str,
    name: str,
    variant: Optional[str] = None,
    category: str = SPINE_CATEGORY,
) -> Dict[str, str]:
    """Spine-known spec fields for this product, ``{}`` on flag-off or a miss.

    Returns each hit field TWICE: ``{field: value}`` and
    ``{f"{field}_source": SPINE_SOURCE_TAG}``, so the value carries its
    provenance through the same ``<field>_source`` channel snippet citations
    already use.

    Three ways to get ``{}``, in order:
      1. the flag is off — nothing is read, nothing is logged;
      2. the category is not ``fragrances`` — the spine is a fragrance
         artifact and must not answer for a phone;
      3. no entry for the key, or an entry carrying no ``SPINE_FIELDS``.

    NEVER raises. The specs path treats a spine miss and a spine failure
    identically: it just pays for the LLM call it would have paid for anyway.
    """
    if not spec_spine_enabled():
        return {}
    try:
        from app.services.extraction_service import canonicalize_category

        if canonicalize_category(category or "") != SPINE_CATEGORY:
            return {}
        entry = await lookup(brand, name, variant, category)
        specs = _entry_specs(entry)
        if not specs:
            return {}
        out: Dict[str, str] = {}
        for field, value in specs.items():
            out[field] = value
            out[f"{field}_source"] = SPINE_SOURCE_TAG
        logger.info(
            "[spec_spine] hit for %s %s -> %d field(s): %s",
            brand, name, len(specs), ",".join(sorted(specs)),
        )
        return out
    except Exception as exc:  # noqa: BLE001 — a spine read must never break specs
        logger.warning("[spec_spine] lookup failed for %s %s (%s)", brand, name, exc)
        return {}
