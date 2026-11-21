"""INC-M1b MATCHER FOLD (ENABLE_MATCH_FOLD, default OFF, read per call): the RED file.

The matcher fold of the incident data lane, spec INC_M1_SPEC.md section 2 as amended and
corrected by RULINGS_INC_M1b.md (M1bR-1..M1bR-13; where they disagree the rulings win):
  - the brand alias fold in the SELECTION identity subset (price_service._BRAND_ALIAS_GROUPS,
    unchanged, plus a new private _M1B_EXTRA_ALIAS_GROUPS = {mfk, maison francis kurkdjian,
    francis kurkdjian}), triggered only by a group the QUERY core names, with the house-only
    guard (M1bR-4);
  - the houseless distinctive line (M1bR-5), read through ONE new read-only accessor of
    product_resolver, named here seeded_line_profiles() (M1bR-7);
  - the single-concentration default in the fragrance branch of
    _vd_candidate_missing_query_axis, SELECTION mode only (M1bR-6);
  - padding: the six words are already stripped at the base, so nothing is added (M1bR-8).
Fragrances only (the category after the "other" re-inference), SELECTION mode only: EXACT,
BACKSTOP and every other category stay byte-identical with the flag ON (M1bR-3).

Row classes (the gate reads them by name):
  test_red_*     RED: fail at the base on an AssertionError only (a missing symbol is read
                 through getattr and ASSERTED, never raised).
  test_accept    RED (parametrized): rejected with the flag OFF, accepted with it ON.
  test_guard     GUARD (parametrized): rejected with the flag OFF and with it ON.
  test_pin_*     PIN: green at the base; flag-ON pins run with the full configuration.
  test_walk_mix  the 64-mix walk of M1bR-10, one row per mix (ENABLE_MATCH_FOLD x
                 ENABLE_PRICE_NOT_LOST x ENABLE_VARIANT_DESCRIPTOR_AXES x
                 ENABLE_LISTING_MATCH_GUARD x ENABLE_DATA_GUARDS_V2 x the query shape).
                 A fold-OFF row pins the base verdict of every check on every pair
                 (GOLDEN, recorded AT THE BASE d0b5a761 by the RED author) and that the
                 accessor is never called with the flag OFF; a fold-ON row asserts THE RULE
                 (the accepted-wrong set of every check is a SUBSET of the fold-OFF set),
                 that EXACT / BACKSTOP / the chokepoint and the untouched checks are
                 identical, that no GUARD probe and no Arabic title changes, and (a RED
                 addition, reported to the gate) that no fold-OFF accept is lost.

The corpus: the R4 title corpus, copied verbatim from research-2026-11-16/work/R4/corpus.py
(109 titles over 8 lines, 27 of them Arabic; 8 quoted from the 2026-11-15 investigation, the
rest written by R4), its per-line amounts, and R4's truth rule (R4_matching.md section 3,
run_matrix.py truth_price): a price is right when the listing is the base or another bottle
of the same line with the same concentration, and (when a size was typed) that size. The
check functions are run_matrix.py's, unchanged. The query shapes: typed = the owner's text
(ENABLE_PRODUCT_RESOLVER OFF); resolved = the full_name the resolver's lexicon arm and
apply_resolution produce for that text (ENABLE_PRODUCT_RESOLVER ON), frozen here and pinned
against the live resolver by test_pin_resolved_queries (no model call).

Hermetic: no network, no .env, no credential; every row deletes every ENABLE_* name and
WARMER_CONTEXT and sets the flags it depends on explicitly. Pure ASCII, LF: every Arabic
title is built from chr() code points at run time. A hermetic count is not the production
proof: a merged unit is "merged, NOT yet proven" until the owner's phone shows it.
"""

from __future__ import annotations

import base64
import builtins
import dataclasses
import inspect
import json
import os
import pathlib
import socket

import pytest

from app.services import price_service as ps
from app.services import product_resolver as pr

ROOT = pathlib.Path(__file__).resolve().parents[1]
LINES_FILE = ROOT / "data" / "fragrance_lines.json"
FLAG = "ENABLE_MATCH_FOLD"
READER = "match_fold_enabled"
ACCESSOR = "seeded_line_profiles"
EXTRA_TABLE = "_M1B_EXTRA_ALIAS_GROUPS"
PNL = "ENABLE_PRICE_NOT_LOST"
VDA = "ENABLE_VARIANT_DESCRIPTOR_AXES"
LMG = "ENABLE_LISTING_MATCH_GUARD"
DG2 = "ENABLE_DATA_GUARDS_V2"
RESOLVER_FLAG = "ENABLE_PRODUCT_RESOLVER"
CAT = "fragrances"
MFK_Q = "Maison Francis Kurkdjian Baccarat Rouge 540 EDP"
ON_SPELLINGS = ("true", " TRUE ", "1", "yes", "On", "on ")
OFF_SPELLINGS = (None, "false", "0", "", "no", "off", " OFF ", "garbage")


# ---------------------------------------------------------------- environment and seams


def _env(setenv, delenv, **flags):
    """Delete every ENABLE_* name and WARMER_CONTEXT, then set the given flags."""
    for name in list(os.environ):
        if name.startswith("ENABLE_") or name == "WARMER_CONTEXT":
            delenv(name)
    for name, value in flags.items():
        if value is not None:
            setenv(name, value)
    ps._extract_variant_descriptor_cached.cache_clear()


def _clean(monkeypatch, **flags):
    _env(monkeypatch.setenv, lambda n: monkeypatch.delenv(n, raising=False), **flags)


def _on(monkeypatch, **extra):
    flags = {FLAG: "true"}
    flags.update(extra)
    _clean(monkeypatch, **flags)


def _reader():
    fn = getattr(ps, READER, None)
    assert callable(fn), "price_service.%s (the ENABLE_MATCH_FOLD reader) is missing" % READER
    return fn


def _accessor():
    fn = getattr(pr, ACCESSOR, None)
    assert callable(fn), "product_resolver.%s (the seeded-line accessor) is missing" % ACCESSOR
    return fn


def _sel(query, title, category=CAT, brand=""):
    return bool(ps._selection_match(query, title, category, candidate_brand=brand))


def _verdict(query, title, category=CAT, mode=None):
    q = ps.extract_variant_descriptor(query, category, "")
    c = ps.extract_variant_descriptor(title, category, "")
    return ps.descriptor_verdict(q, c, category, mode or ps.DESCRIPTOR_MODE_SELECTION)


def _cp(*points):
    return "".join(chr(p) for p in points)


def _is_arabic(text):
    return any(0x0600 <= ord(ch) <= 0x06FF for ch in text)


def _with(record, **changes):
    """A copy of one accessor record with fields changed (the record is a frozen dataclass
    or a NamedTuple: the pinned contract)."""
    if dataclasses.is_dataclass(record):
        return dataclasses.replace(record, **changes)
    if hasattr(record, "_replace"):
        return record._replace(**changes)
    raise AssertionError("an accessor record must be a frozen dataclass or a NamedTuple")


# ---------------------------------------------------------------- the R4 corpus (copied)
# R4 corpus.py ROWS, verbatim (line, title, true_conc, true_size_ml, cls, flanker, src);
# an Arabic title is written as its code points (a comment names its line and class).
ROWS = (
    ('sauvage', 'DIOR Sauvage Eau de Parfum Spray', 'EDP', 100, 'base', None, 'log'),
    ('sauvage', 'Dior Sauvage Parfum', 'Parfum', 100, 'conc', None, 'log'),
    ('sauvage', 'Sauvage EDP 100ml', 'EDP', 100, 'base', None, 'log'),
    ('sauvage', 'SAUVAGE 100ML', 'EDT', 100, 'base', None, 'log'),
    ('sauvage', 'Sauvage 3.4 oz', 'EDT', 100, 'base', None, 'log'),
    ('sauvage', 'Dior Sauvage Edt M 100Ml', 'EDT', 100, 'conc', None, 'log'),
    ('sauvage', 'Dior Sauvage Eau de Parfum 100 ml for Men', 'EDP', 100, 'base', None, 'syn'),
    ('sauvage', 'Christian Dior Sauvage EDP 60ml', 'EDP', 60, 'size', None, 'syn'),
    ('sauvage', 'Dior Sauvage Eau de Parfum 200ml', 'EDP', 200, 'size', None, 'syn'),
    ('sauvage', 'Dior Sauvage Elixir 100ml', 'Elixir', 100, 'conc', None, 'syn'),
    ('sauvage', 'Dior Sauvage Eau de Parfum Refill 300ml', 'EDP', 300, 'refill', None, 'syn'),
    ('sauvage', 'Dior Sauvage EDP 100ml Tester (No Box)', 'EDP', 100, 'tester', None, 'syn'),
    ('sauvage', 'Dior Sauvage EDP 100ml + 10ml Travel Spray Gift Set', 'EDP', 100, 'gift', None, 'syn'),
    ('sauvage', 'Dior Sauvage Eau de Parfum 10ml Travel Spray', 'EDP', 10, 'mini', None, 'syn'),
    ('sauvage', 'Dior Sauvage Deodorant Stick 75g', None, None, 'body', None, 'syn'),
    ('sauvage', 'Dior Sauvage Shower Gel 250ml', None, 250, 'body', None, 'syn'),
    ('sauvage', 'Inspired by Sauvage EDP 100ml Men Perfume', 'EDP', 100, 'dupe', None, 'syn'),
    # sauvage base (Arabic)
    ('sauvage', _cp(0x062F, 0x064A, 0x0648, 0x0631, 0x0020, 0x0633, 0x0648, 0x0641, 0x0627, 0x062C, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'base', None, 'syn'),
    # sauvage conc (Arabic)
    ('sauvage', _cp(0x0639, 0x0637, 0x0631, 0x0020, 0x0633, 0x0648, 0x0641, 0x0627, 0x062C, 0x0020, 0x0645, 0x0646, 0x0020, 0x062F, 0x064A, 0x0648, 0x0631, 0x0020, 0x0644, 0x0644, 0x0631, 0x062C, 0x0627, 0x0644, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x064A, 0x0020, 0x062A, 0x0648, 0x0627, 0x0644, 0x064A, 0x062A, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDT', 100, 'conc', None, 'syn'),
    # sauvage conc (Arabic)
    ('sauvage', _cp(0x062F, 0x064A, 0x0648, 0x0631, 0x0020, 0x0633, 0x0648, 0x0641, 0x0627, 0x062C, 0x0020, 0x0625, 0x0644, 0x0643, 0x0633, 0x064A, 0x0631, 0x0020, 0x0036, 0x0030, 0x0020, 0x0645, 0x0644), 'Elixir', 60, 'conc', None, 'syn'),
    # sauvage tester (Arabic)
    ('sauvage', _cp(0x062A, 0x0633, 0x062A, 0x0631, 0x0020, 0x062F, 0x064A, 0x0648, 0x0631, 0x0020, 0x0633, 0x0648, 0x0641, 0x0627, 0x062C, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'tester', None, 'syn'),
    ('bleu', 'Chanel Bleu de Chanel Eau de Parfum 100ml', 'EDP', 100, 'base', None, 'syn'),
    ('bleu', 'BLEU DE CHANEL EAU DE PARFUM POUR HOMME SPRAY 3.4 FL OZ', 'EDP', 100, 'base', None, 'syn'),
    ('bleu', 'Bleu de Chanel EDP 50ml', 'EDP', 50, 'size', None, 'syn'),
    ('bleu', 'Bleu De Chanel Eau De Parfum 150ml', 'EDP', 150, 'size', None, 'syn'),
    ('bleu', 'Chanel Bleu de Chanel Eau de Toilette 100ml', 'EDT', 100, 'conc', None, 'syn'),
    ('bleu', 'Chanel Bleu de Chanel Parfum 100ml', 'Parfum', 100, 'conc', None, 'syn'),
    ('bleu', 'Bleu de Chanel Eau de Parfum Twist and Spray 3 x 20ml Refill', 'EDP', 20, 'refill', None, 'syn'),
    ('bleu', 'Chanel Bleu de Chanel EDP Tester 100ml', 'EDP', 100, 'tester', None, 'syn'),
    ('bleu', 'Bleu de Chanel Deodorant Stick 75ml', None, 75, 'body', None, 'syn'),
    ('bleu', 'Bleu de Chanel After Shave Lotion 100ml', None, 100, 'body', None, 'syn'),
    ('bleu', 'Bleu de Chanel EDP 100ml Gift Set with Shower Gel', 'EDP', 100, 'gift', None, 'syn'),
    ('bleu', 'Blue Chanel Inspired Perfume EDP 100ml', 'EDP', 100, 'dupe', None, 'syn'),
    # bleu base (Arabic)
    ('bleu', _cp(0x0628, 0x0644, 0x0648, 0x0020, 0x062F, 0x064A, 0x0020, 0x0634, 0x0627, 0x0646, 0x064A, 0x0644, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'base', None, 'syn'),
    # bleu conc (Arabic)
    ('bleu', _cp(0x0634, 0x0627, 0x0646, 0x064A, 0x0644, 0x0020, 0x0628, 0x0644, 0x0648, 0x0020, 0x062F, 0x064A, 0x0020, 0x0634, 0x0627, 0x0646, 0x064A, 0x0644, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0031, 0x0035, 0x0030, 0x0020, 0x0645, 0x0644), 'Parfum', 150, 'conc', None, 'syn'),
    # bleu body (Arabic)
    ('bleu', _cp(0x0645, 0x0632, 0x064A, 0x0644, 0x0020, 0x0639, 0x0631, 0x0642, 0x0020, 0x0628, 0x0644, 0x0648, 0x0020, 0x062F, 0x064A, 0x0020, 0x0634, 0x0627, 0x0646, 0x064A, 0x0644, 0x0020, 0x0633, 0x062A, 0x064A, 0x0643, 0x0020, 0x0037, 0x0035, 0x0020, 0x0645, 0x0644), None, 75, 'body', None, 'syn'),
    ('y', 'Yves Saint Laurent Y Eau de Parfum 100ml', 'EDP', 100, 'base', None, 'syn'),
    ('y', 'YSL Y EDP 60ml for Men', 'EDP', 60, 'size', None, 'syn'),
    ('y', 'YSL Y Eau de Toilette 100ml', 'EDT', 100, 'conc', None, 'syn'),
    ('y', 'Yves Saint Laurent Y Le Parfum 100ml', 'Parfum', 100, 'conc', None, 'syn'),
    ('y', 'YSL Y Elixir Parfum 60ml', 'Elixir', 60, 'conc', None, 'syn'),
    ('y', 'YSL Y Eau de Parfum Intense 100ml', 'Parfum Intense', 100, 'conc', 'intense', 'syn'),
    ('y', 'YSL Y EDP 100ml Gift Set + 10ml', 'EDP', 100, 'gift', None, 'syn'),
    ('y', 'YSL Y EDP Tester 100ml', 'EDP', 100, 'tester', None, 'syn'),
    ('y', 'YSL Y Deodorant Stick 75g', None, None, 'body', None, 'syn'),
    # y base (Arabic)
    ('y', _cp(0x0627, 0x064A, 0x0641, 0x0020, 0x0633, 0x0627, 0x0646, 0x0020, 0x0644, 0x0648, 0x0631, 0x0627, 0x0646, 0x0020, 0x0648, 0x0627, 0x064A, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'base', None, 'syn'),
    # y size (Arabic)
    ('y', _cp(0x0639, 0x0637, 0x0631, 0x0020, 0x0648, 0x0627, 0x064A, 0x0020, 0x0645, 0x0646, 0x0020, 0x0627, 0x064A, 0x0641, 0x0020, 0x0633, 0x0627, 0x0646, 0x0020, 0x0644, 0x0648, 0x0631, 0x0627, 0x0646, 0x0020, 0x0644, 0x0644, 0x0631, 0x062C, 0x0627, 0x0644, 0x0020, 0x0036, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 60, 'size', None, 'syn'),
    ('libre', 'Yves Saint Laurent Libre Eau de Parfum 90ml', 'EDP', 90, 'base', None, 'syn'),
    ('libre', 'YSL Libre EDP 50ml', 'EDP', 50, 'size', None, 'syn'),
    ('libre', 'YSL Libre Eau de Parfum for Women 3 oz', 'EDP', 90, 'base', None, 'syn'),
    ('libre', 'YSL Libre Intense EDP 90ml', 'EDP', 90, 'flanker', 'intense', 'syn'),
    ('libre', 'YSL Libre Le Parfum 90ml', 'Parfum', 90, 'conc', None, 'syn'),
    ('libre', 'YSL Libre Eau de Toilette 90ml', 'EDT', 90, 'conc', None, 'syn'),
    ('libre', 'YSL Libre EDP Refill 100ml', 'EDP', 100, 'refill', None, 'syn'),
    ('libre', 'YSL Libre Hair Mist 30ml', None, 30, 'body', None, 'syn'),
    ('libre', 'YSL Libre Body Lotion 200ml', None, 200, 'body', None, 'syn'),
    ('libre', 'YSL Libre EDP 90ml Tester', 'EDP', 90, 'tester', None, 'syn'),
    ('libre', 'YSL Libre EDP 50ml Gift Set with Mascara', 'EDP', 50, 'gift', None, 'syn'),
    ('libre', 'YSL Libre EDP 7.5ml Miniature', 'EDP', 7, 'mini', None, 'syn'),
    # libre base (Arabic)
    ('libre', _cp(0x0644, 0x064A, 0x0628, 0x0631, 0x0020, 0x0627, 0x064A, 0x0641, 0x0020, 0x0633, 0x0627, 0x0646, 0x0020, 0x0644, 0x0648, 0x0631, 0x0627, 0x0646, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0644, 0x0644, 0x0646, 0x0633, 0x0627, 0x0621, 0x0020, 0x0039, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 90, 'base', None, 'syn'),
    # libre flanker (Arabic)
    ('libre', _cp(0x0627, 0x064A, 0x0641, 0x0020, 0x0633, 0x0627, 0x0646, 0x0020, 0x0644, 0x0648, 0x0631, 0x0627, 0x0646, 0x0020, 0x0644, 0x064A, 0x0628, 0x0631, 0x0020, 0x0627, 0x0646, 0x062A, 0x0646, 0x0633, 0x0020, 0x0039, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 90, 'flanker', 'intense', 'syn'),
    ('br540', 'Maison Francis Kurkdjian Baccarat Rouge 540 Eau de Parfum 70ml', 'EDP', 70, 'base', None, 'syn'),
    ('br540', 'MFK Baccarat Rouge 540 EDP 200ml', 'EDP', 200, 'size', None, 'syn'),
    ('br540', 'Baccarat Rouge 540 Extrait de Parfum 70ml', 'Extrait', 70, 'conc', None, 'syn'),
    ('br540', 'Maison Francis Kurkdjian Baccarat Rouge 540 Hair Mist 70ml', None, 70, 'body', None, 'syn'),
    ('br540', 'Baccarat Rouge 540 Scented Body Oil 70ml', None, 70, 'body', None, 'syn'),
    ('br540', 'Baccarat Rouge 540 EDP 35ml Refill', 'EDP', 35, 'refill', None, 'syn'),
    ('br540', 'Baccarat Rouge 540 EDP 70ml Tester', 'EDP', 70, 'tester', None, 'syn'),
    ('br540', 'Baccarat Rouge 540 Travel Spray 3 x 11ml', 'EDP', 11, 'mini', None, 'syn'),
    ('br540', 'Cloud Rouge 540 Inspired by Baccarat Rouge EDP 100ml', 'EDP', 100, 'dupe', None, 'syn'),
    # br540 base (Arabic)
    ('br540', _cp(0x0628, 0x0627, 0x0643, 0x0627, 0x0631, 0x0627, 0x062A, 0x0020, 0x0631, 0x0648, 0x062C, 0x0020, 0x0035, 0x0034, 0x0030, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0037, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 70, 'base', None, 'syn'),
    # br540 dupe (Arabic)
    ('br540', _cp(0x0639, 0x0637, 0x0631, 0x0020, 0x0628, 0x062F, 0x064A, 0x0644, 0x0020, 0x0628, 0x0627, 0x0643, 0x0627, 0x0631, 0x0627, 0x062A, 0x0020, 0x0631, 0x0648, 0x062C, 0x0020, 0x0035, 0x0034, 0x0030, 0x0020, 0x0644, 0x0644, 0x062C, 0x0646, 0x0633, 0x064A, 0x0646, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'dupe', None, 'syn'),
    ('aventus', 'Creed Aventus Eau de Parfum 100ml', 'EDP', 100, 'base', None, 'syn'),
    ('aventus', 'Creed Aventus 50ml', 'EDP', 50, 'size', None, 'syn'),
    ('aventus', 'Creed Aventus for Her EDP 75ml', 'EDP', 75, 'twin', None, 'syn'),
    ('aventus', 'Creed Aventus Cologne 100ml', 'EDC', 100, 'flanker', 'cologne', 'syn'),
    ('aventus', 'Creed Aventus Absolu 100ml', 'EDP', 100, 'flanker', 'absolu', 'syn'),
    ('aventus', 'Creed Aventus 100ml Tester', 'EDP', 100, 'tester', None, 'syn'),
    ('aventus', 'Creed Aventus 10ml Atomiser Travel Size', 'EDP', 10, 'mini', None, 'syn'),
    ('aventus', 'Creed Aventus Gift Set 100ml + 10ml', 'EDP', 100, 'gift', None, 'syn'),
    ('aventus', 'Creed Aventus Deodorant Stick 75ml', None, 75, 'body', None, 'syn'),
    # aventus base (Arabic)
    ('aventus', _cp(0x0643, 0x0631, 0x064A, 0x062F, 0x0020, 0x0627, 0x0641, 0x0646, 0x062A, 0x0648, 0x0633, 0x0020, 0x0644, 0x0644, 0x0631, 0x062C, 0x0627, 0x0644, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'base', None, 'syn'),
    # aventus twin (Arabic)
    ('aventus', _cp(0x0643, 0x0631, 0x064A, 0x062F, 0x0020, 0x0627, 0x0641, 0x0646, 0x062A, 0x0648, 0x0633, 0x0020, 0x0644, 0x0644, 0x0646, 0x0633, 0x0627, 0x0621, 0x0020, 0x0037, 0x0035, 0x0020, 0x0645, 0x0644), 'EDP', 75, 'twin', None, 'syn'),
    ('khamrah', 'Lattafa Khamrah EDP 100ml', 'EDP', 100, 'base', None, 'syn'),
    ('khamrah', 'Lattafa Khamrah Eau de Parfum 100ml Unisex', 'EDP', 100, 'base', None, 'syn'),
    ('khamrah', 'Lattafa Khamrah Qahwa EDP 100ml', 'EDP', 100, 'flanker', 'qahwa', 'syn'),
    ('khamrah', 'Lattafa Khamrah Dukhan EDP 100ml', 'EDP', 100, 'flanker', 'dukhan', 'syn'),
    ('khamrah', 'Lattafa Khamrah Deodorant 250ml', None, 250, 'body', None, 'syn'),
    ('khamrah', 'Lattafa Khamrah 100ml Tester', 'EDP', 100, 'tester', None, 'syn'),
    ('khamrah', 'Lattafa Khamrah Gift Set EDP 100ml + Deodorant', 'EDP', 100, 'gift', None, 'syn'),
    # khamrah base (Arabic)
    ('khamrah', _cp(0x0644, 0x0637, 0x0627, 0x0641, 0x0629, 0x0020, 0x062E, 0x0645, 0x0631, 0x0629, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'base', None, 'syn'),
    # khamrah flanker (Arabic)
    ('khamrah', _cp(0x0639, 0x0637, 0x0631, 0x0020, 0x062E, 0x0645, 0x0631, 0x0629, 0x0020, 0x0642, 0x0647, 0x0648, 0x0629, 0x0020, 0x0644, 0x0637, 0x0627, 0x0641, 0x0629, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'flanker', 'qahwa', 'syn'),
    ('hawas', 'Rasasi Hawas for Him EDP 100ml', 'EDP', 100, 'base', None, 'syn'),
    ('hawas', 'Rasasi Hawas Eau de Parfum for Men 100ml', 'EDP', 100, 'base', None, 'syn'),
    ('hawas', 'Rasasi Hawas for Her EDP 100ml', 'EDP', 100, 'twin', None, 'syn'),
    ('hawas', 'Rasasi Hawas Ice for Him EDP 100ml', 'EDP', 100, 'flanker', 'ice', 'syn'),
    ('hawas', 'Rasasi Hawas Elixir 100ml', 'Elixir', 100, 'conc', None, 'syn'),
    ('hawas', 'Rasasi Hawas Deodorant Spray 200ml', None, 200, 'body', None, 'syn'),
    ('hawas', 'Rasasi Hawas Tester 100ml', 'EDP', 100, 'tester', None, 'syn'),
    # hawas base (Arabic)
    ('hawas', _cp(0x0631, 0x0635, 0x0627, 0x0635, 0x064A, 0x0020, 0x062D, 0x0648, 0x0627, 0x0633, 0x0020, 0x0644, 0x0644, 0x0631, 0x062C, 0x0627, 0x0644, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'base', None, 'syn'),
    # hawas twin (Arabic)
    ('hawas', _cp(0x0631, 0x0635, 0x0627, 0x0635, 0x064A, 0x0020, 0x062D, 0x0648, 0x0627, 0x0633, 0x0020, 0x0644, 0x0644, 0x0646, 0x0633, 0x0627, 0x0621, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'twin', None, 'syn'),
    # sauvage gift (Arabic)
    ('sauvage', _cp(0x0637, 0x0642, 0x0645, 0x0020, 0x0647, 0x062F, 0x0627, 0x064A, 0x0627, 0x0020, 0x062F, 0x064A, 0x0648, 0x0631, 0x0020, 0x0633, 0x0648, 0x0641, 0x0627, 0x062C, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644, 0x0020, 0x0645, 0x0639, 0x0020, 0x062C, 0x0644, 0x0020, 0x0627, 0x0633, 0x062A, 0x062D, 0x0645, 0x0627, 0x0645), 'EDP', 100, 'gift', None, 'syn'),
    # libre body (Arabic)
    ('libre', _cp(0x0645, 0x0639, 0x0637, 0x0631, 0x0020, 0x0634, 0x0639, 0x0631, 0x0020, 0x0644, 0x064A, 0x0628, 0x0631, 0x0020, 0x0645, 0x0646, 0x0020, 0x0627, 0x064A, 0x0641, 0x0020, 0x0633, 0x0627, 0x0646, 0x0020, 0x0644, 0x0648, 0x0631, 0x0627, 0x0646, 0x0020, 0x0033, 0x0030, 0x0020, 0x0645, 0x0644), None, 30, 'body', None, 'syn'),
    # bleu tester (Arabic)
    ('bleu', _cp(0x062A, 0x0633, 0x062A, 0x0631, 0x0020, 0x0628, 0x0644, 0x0648, 0x0020, 0x062F, 0x064A, 0x0020, 0x0634, 0x0627, 0x0646, 0x064A, 0x0644, 0x0020, 0x0627, 0x0648, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'tester', None, 'syn'),
    # aventus mini (Arabic)
    ('aventus', _cp(0x0643, 0x0631, 0x064A, 0x062F, 0x0020, 0x0627, 0x0641, 0x0646, 0x062A, 0x0648, 0x0633, 0x0020, 0x0031, 0x0030, 0x0020, 0x0645, 0x0644, 0x0020, 0x062D, 0x062C, 0x0645, 0x0020, 0x0627, 0x0644, 0x0633, 0x0641, 0x0631), 'EDP', 10, 'mini', None, 'syn'),
    # khamrah body (Arabic)
    ('khamrah', _cp(0x0645, 0x0632, 0x064A, 0x0644, 0x0020, 0x0639, 0x0631, 0x0642, 0x0020, 0x0644, 0x0637, 0x0627, 0x0641, 0x0629, 0x0020, 0x062E, 0x0645, 0x0631, 0x0629, 0x0020, 0x0032, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), None, 200, 'body', None, 'syn'),
    # hawas flanker (Arabic)
    ('hawas', _cp(0x0631, 0x0635, 0x0627, 0x0635, 0x064A, 0x0020, 0x062D, 0x0648, 0x0627, 0x0633, 0x0020, 0x0627, 0x064A, 0x0633, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'flanker', 'ice', 'syn'),
    # br540 conc (Arabic)
    ('br540', _cp(0x0628, 0x0627, 0x0643, 0x0627, 0x0631, 0x0627, 0x062A, 0x0020, 0x0631, 0x0648, 0x062C, 0x0020, 0x0035, 0x0034, 0x0030, 0x0020, 0x0627, 0x0643, 0x0633, 0x062A, 0x0631, 0x064A, 0x062A, 0x0020, 0x062F, 0x0648, 0x0020, 0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646, 0x0020, 0x0037, 0x0030, 0x0020, 0x0645, 0x0644), 'Extrait', 70, 'conc', None, 'syn'),
    # y dupe (Arabic)
    ('y', _cp(0x0639, 0x0637, 0x0631, 0x0020, 0x0645, 0x0633, 0x062A, 0x0648, 0x062D, 0x0649, 0x0020, 0x0645, 0x0646, 0x0020, 0x0648, 0x0627, 0x064A, 0x0020, 0x0627, 0x064A, 0x0641, 0x0020, 0x0633, 0x0627, 0x0646, 0x0020, 0x0644, 0x0648, 0x0631, 0x0627, 0x0646, 0x0020, 0x0031, 0x0030, 0x0030, 0x0020, 0x0645, 0x0644), 'EDP', 100, 'dupe', None, 'syn'),
)
R4_AMOUNT = {'sauvage': 55.0, 'bleu': 60.0, 'y': 45.0, 'libre': 50.0, 'br540': 120.0, 'aventus': 140.0, 'khamrah': 12.0, 'hawas': 15.0}  # R4 corpus.py AMOUNT

# The product the owner means per line: (qid, line, typed text, resolved full_name, conc, size).
# typed = what the owner types (ENABLE_PRODUCT_RESOLVER OFF: searched and judged as typed);
# resolved = resolve_lexicon(typed, context=True) + apply_resolution + _shopping_cache_key
# at the base (pinned by test_pin_resolved_queries). R4's own query strings are the
# resolved shapes here (R4 QUERIES), except y_T / hawas_T / sauvage_T, which R4 used typed.
QUERIES = (
    ("sauvage_R", "sauvage", "Dior Sauvage EDP", "Dior Sauvage EDP", "EDP", None),
    ("sauvage_R100", "sauvage", "Dior Sauvage EDP 100ml", "Dior Sauvage EDP 100ml", "EDP", 100),
    ("sauvage_T", "sauvage", "Dior Sauvage 100 ML Edp", "Dior Sauvage EDP 100ml", "EDP", 100),
    ("bleu_R", "bleu", "Bleu de Chanel EDP", "Chanel Bleu de Chanel EDP", "EDP", None),
    ("bleu_R100", "bleu", "Bleu de Chanel EDP 100ml", "Chanel Bleu de Chanel EDP 100ml", "EDP", 100),
    ("y_T", "y", "YSL Y EDP", "Yves Saint Laurent Y EDP", "EDP", None),
    ("libre_R", "libre", "YSL Libre EDP", "Yves Saint Laurent Libre EDP", "EDP", None),
    ("br540_R", "br540", "Baccarat Rouge 540 EDP", MFK_Q, "EDP", None),
    ("aventus_R", "aventus", "Creed Aventus", "Creed Aventus EDP", "EDP", None),
    ("khamrah_R", "khamrah", "Lattafa Khamrah", "Lattafa Khamrah EDP", "EDP", None),
    ("hawas_T", "hawas", "Rasasi Hawas EDP", "Rasasi Hawas EDP", "EDP", None),
)
LINE_NAME = {
    "sauvage": "Sauvage", "bleu": "Bleu de Chanel", "y": "Y", "libre": "Libre",
    "br540": "Baccarat Rouge 540", "aventus": "Aventus", "khamrah": "Khamrah", "hawas": "Hawas",
    "layton": "Layton", "lveb": "La Vie Est Belle", "adgp": "Acqua di Gio Profumo",
    "swy": "Stronger With You", "eros": "Eros", "tygar": "Tygar", "homme": "Homme",
}
# A plausible BHD amount per line (only the floor guards read it); R4's eight, plus the
# probe lines (synthetic, same order of magnitude).
AMOUNT = {
    "sauvage": 55.0, "bleu": 60.0, "y": 45.0, "libre": 50.0, "br540": 120.0,
    "aventus": 140.0, "khamrah": 12.0, "hawas": 15.0,
    "layton": 80.0, "lveb": 50.0, "adgp": 45.0, "swy": 40.0, "eros": 35.0, "tygar": 95.0,
    "homme": 45.0,
}
PDP = "https://shop.example.bh/products/item-1"

# ---------------------------------------------------------------- the RED probe rows
# (rid, line, query, title, base_axis, q_conc, q_size, t_conc, t_size, cls); base_axis is the
# failing descriptor_verdict axis at the base (flag OFF), measured by the RED author.
ACCEPT_ROWS = (
    # the 7 brand-spelling rows of R4 lost_why.txt (latin selection:identity_subset)
    ("lw_sauvage_R_houseless", "sauvage", "Dior Sauvage EDP", "Sauvage EDP 100ml", "identity_subset", "EDP", None, "EDP", 100, "base"),
    ("lw_sauvage_R100_houseless", "sauvage", "Dior Sauvage EDP 100ml", "Sauvage EDP 100ml", "identity_subset", "EDP", 100, "EDP", 100, "base"),
    ("lw_sauvage_T_houseless", "sauvage", "Dior Sauvage 100 ML Edp", "Sauvage EDP 100ml", "identity_subset", "EDP", 100, "EDP", 100, "base"),
    ("lw_y_ysl_60_for_men", "y", "Yves Saint Laurent Y EDP", "YSL Y EDP 60ml for Men", "identity_subset", "EDP", None, "EDP", 60, "size"),
    ("lw_libre_ysl_50", "libre", "Yves Saint Laurent Libre EDP", "YSL Libre EDP 50ml", "identity_subset", "EDP", None, "EDP", 50, "size"),
    ("lw_libre_ysl_women_3oz", "libre", "Yves Saint Laurent Libre EDP", "YSL Libre Eau de Parfum for Women 3 oz", "identity_subset", "EDP", None, "EDP", 90, "base"),
    ("lw_br540_mfk_200", "br540", MFK_Q, "MFK Baccarat Rouge 540 EDP 200ml", "identity_subset", "EDP", None, "EDP", 200, "size"),
    # the concentration default and the variant-add row
    ("default_aventus_50", "aventus", "Creed Aventus EDP", "Creed Aventus 50ml", "candidate_missing_query_axis", "EDP", None, "EDP", 50, "size"),
    ("fold_christian_dior_60", "sauvage", "Dior Sauvage EDP", "Christian Dior Sauvage EDP 60ml", "variant_add", "EDP", None, "EDP", 60, "size"),
    # the four brandform.txt rows of spec 2 (under their resolved queries)
    ("bf_ysl_libre_90", "libre", "Yves Saint Laurent Libre EDP", "YSL Libre EDP 90ml", "identity_subset", "EDP", None, "EDP", 90, "base"),
    ("bf_br540_houseless_70", "br540", MFK_Q, "Baccarat Rouge 540 Eau de Parfum 70ml", "identity_subset", "EDP", None, "EDP", 70, "base"),
    ("bf_aventus_100", "aventus", "Creed Aventus EDP", "Creed Aventus 100ml", "candidate_missing_query_axis", "EDP", None, "EDP", 100, "base"),
    ("bf_khamrah_100", "khamrah", "Lattafa Khamrah EDP", "Lattafa Khamrah 100ml", "candidate_missing_query_axis", "EDP", None, "EDP", 100, "base"),
    # M1bR-9 additions
    ("saint_laurent_libre_90", "libre", "Yves Saint Laurent Libre EDP", "Saint Laurent Libre EDP 90ml", "identity_subset", "EDP", None, "EDP", 90, "base"),
    ("mfk_br540_70", "br540", MFK_Q, "MFK Baccarat Rouge 540 EDP 70ml", "identity_subset", "EDP", None, "EDP", 70, "base"),
    ("francis_kurkdjian_br540_70", "br540", MFK_Q, "Francis Kurkdjian Baccarat Rouge 540 EDP 70ml", "identity_subset", "EDP", None, "EDP", 70, "base"),
    # RED additions: a houseless title of every other distinctive seeded line (M1bR-5 b)
    ("hl_aventus", "aventus", "Creed Aventus EDP", "Aventus Eau de Parfum 100ml", "identity_subset", "EDP", None, "EDP", 100, "base"),
    ("hl_khamrah", "khamrah", "Lattafa Khamrah EDP", "Khamrah Eau de Parfum 100ml", "identity_subset", "EDP", None, "EDP", 100, "base"),
    ("hl_layton", "layton", "Parfums de Marly Layton EDP", "Layton Eau de Parfum 125ml", "identity_subset", "EDP", None, "EDP", 125, "size"),
    ("hl_la_vie_est_belle", "lveb", "Lancome La Vie Est Belle EDP", "La Vie Est Belle Eau de Parfum 100ml", "identity_subset", "EDP", None, "EDP", 100, "base"),
    ("hl_acqua_di_gio_profumo", "adgp", "Giorgio Armani Acqua di Gio Profumo", "Acqua di Gio Profumo 75ml", "identity_subset", None, None, None, 75, "base"),
    ("hl_stronger_with_you", "swy", "Emporio Armani Stronger With You EDT", "Stronger With You Eau de Toilette 100ml", "identity_subset", "EDT", None, "EDT", 100, "base"),
)
GUARD_ROWS = (
    # spec 2 GUARD list: a multi-concentration line still fails closed
    ("sauvage_edt_under_edp", "sauvage", "Dior Sauvage EDP", "Dior Sauvage Edt M 100Ml", "concentration", "EDP", None, "EDT", 100, "conc"),
    ("sauvage_noconc_multi", "sauvage", "Dior Sauvage EDP", "Dior Sauvage 100ml", "candidate_missing_query_axis", "EDP", None, "EDT", 100, "base"),
    ("sauvage_noconc_houseless_multi", "sauvage", "Dior Sauvage EDP", "SAUVAGE 100ML", "candidate_missing_query_axis", "EDP", None, "EDT", 100, "base"),
    # the twins and flankers with no concentration (M1bR-6 c, d)
    ("hawas_for_her_noconc", "hawas", "Rasasi Hawas EDP", "Rasasi Hawas for Her 100ml", "candidate_missing_query_axis", "EDP", None, "EDP", 100, "twin"),
    ("aventus_for_her_noconc", "aventus", "Creed Aventus EDP", "Creed Aventus for Her 75ml", "candidate_missing_query_axis", "EDP", None, "EDP", 75, "twin"),
    ("aventus_cologne", "aventus", "Creed Aventus EDP", "Creed Aventus Cologne 100ml", "candidate_missing_query_axis", "EDP", None, "EDC", 100, "flanker"),
    ("aventus_absolu", "aventus", "Creed Aventus EDP", "Creed Aventus Absolu 100ml", "candidate_missing_query_axis", "EDP", None, "EDP", 100, "flanker"),
    ("khamrah_qahwa_noconc", "khamrah", "Lattafa Khamrah EDP", "Lattafa Khamrah Qahwa 100ml", "candidate_missing_query_axis", "EDP", None, "EDP", 100, "flanker"),
    ("hawas_ice_noconc", "hawas", "Rasasi Hawas EDP", "Rasasi Hawas Ice 100ml", "candidate_missing_query_axis", "EDP", None, "EDP", 100, "flanker"),
    ("aventus_women_noconc", "aventus", "Creed Aventus EDP", "Creed Aventus Women 75ml", "candidate_missing_query_axis", "EDP", None, "EDP", 75, "twin"),
    ("hawas_women_noconc", "hawas", "Rasasi Hawas EDP", "Rasasi Hawas Women 100ml", "candidate_missing_query_axis", "EDP", None, "EDP", 100, "twin"),
    ("aventus_her_pronoun_noconc", "aventus", "Creed Aventus EDP", "Creed Aventus Her 75ml", "candidate_missing_query_axis", "EDP", None, "EDP", 75, "twin"),
    ("aventus_ladies_pronoun_noconc", "aventus", "Creed Aventus EDP", "Creed Aventus Ladies 75ml", "candidate_missing_query_axis", "EDP", None, "EDP", 75, "twin"),
    ("aventus_for_her_both_flanker", "aventus", "Creed Aventus for Her EDP", "Creed Aventus for Her 75ml", "candidate_missing_query_axis", "EDP", None, "EDP", 75, "base"),
    ("hawas_for_men_query_states_none", "hawas", "Rasasi Hawas EDP", "Rasasi Hawas for Men 100ml", "candidate_missing_query_axis", "EDP", None, "EDP", 100, "base"),
    ("default_needs_house_in_query", "hawas", "Hawas EDP", "Hawas 100ml", "candidate_missing_query_axis", "EDP", None, "EDP", 100, "base"),
    # dupe, mini, travel, tester, gift set, refill and body rows (M1bR-6 e, M1bR-5)
    ("dupe_inspired_sauvage", "sauvage", "Dior Sauvage EDP", "Inspired by Sauvage EDP 100ml Men Perfume", "identity_subset", "EDP", None, "EDP", 100, "dupe"),
    ("dupe_cloud_rouge", "br540", MFK_Q, "Cloud Rouge 540 Inspired by Baccarat Rouge EDP 100ml", "identity_subset", "EDP", None, "EDP", 100, "dupe"),
    ("dupe_aventus_inspired_houseless", "aventus", "Creed Aventus EDP", "Aventus Inspired EDP 100ml", "identity_subset", "EDP", None, "EDP", 100, "dupe"),
    ("dupe_sauvage_type_houseless", "sauvage", "Dior Sauvage EDP", "Sauvage Type EDP 100ml", "identity_subset", "EDP", None, "EDP", 100, "dupe"),
    ("dupe_sauvage_oil_houseless", "sauvage", "Dior Sauvage EDP", "Sauvage Perfume Oil 100ml", "form", "EDP", None, None, 100, "dupe"),
    ("gift_sauvage_houseless", "sauvage", "Dior Sauvage EDP", "Sauvage EDP 100ml Gift Set", "form", "EDP", None, "EDP", 100, "gift"),
    ("mini_aventus_atomiser", "aventus", "Creed Aventus EDP", "Creed Aventus 10ml Atomiser Travel Size", "candidate_missing_query_axis", "EDP", None, "EDP", 10, "mini"),
    ("mini_br540_travel", "br540", MFK_Q, "Baccarat Rouge 540 Travel Spray 3 x 11ml", "candidate_missing_query_axis", "EDP", None, "EDP", 11, "mini"),
    ("gift_aventus", "aventus", "Creed Aventus EDP", "Creed Aventus Gift Set 100ml + 10ml", "form", "EDP", None, "EDP", 100, "gift"),
    ("refill_br540", "br540", MFK_Q, "Baccarat Rouge 540 EDP 35ml Refill", "form", "EDP", None, "EDP", 35, "refill"),
    ("body_khamrah_deodorant", "khamrah", "Lattafa Khamrah EDP", "Lattafa Khamrah Deodorant 250ml", "form", "EDP", None, None, 250, "body"),
    ("body_br540_oil", "br540", MFK_Q, "Baccarat Rouge 540 Scented Body Oil 70ml", "form", "EDP", None, None, 70, "body"),
    ("tester_aventus", "aventus", "Creed Aventus EDP", "Creed Aventus 100ml Tester", "candidate_missing_query_axis", "EDP", None, "EDP", 100, "tester"),
    ("tester_khamrah", "khamrah", "Lattafa Khamrah EDP", "Lattafa Khamrah 100ml Tester", "candidate_missing_query_axis", "EDP", None, "EDP", 100, "tester"),
    ("tester_br540_houseless", "br540", MFK_Q, "Baccarat Rouge 540 EDP 70ml Tester", "identity_subset", "EDP", None, "EDP", 70, "tester"),
    # minis and travel sprays whose only extra words are form noise (travel, miniature,
    # spray), with no size typed: the corpus row R4 #58 under the resolved Libre query, and
    # the same class through the fold and through the houseless rule (spec 2 GUARD list:
    # "the dupe, mini, travel ... rows of the corpus")
    ("mini_libre_corpus_resolved", "libre", "Yves Saint Laurent Libre EDP", "YSL Libre EDP 7.5ml Miniature", "identity_subset", "EDP", None, "EDP", 7, "mini"),
    ("mini_br540_mfk_travel", "br540", MFK_Q, "MFK Baccarat Rouge 540 EDP 35ml Travel Spray", "identity_subset", "EDP", None, "EDP", 35, "mini"),
    ("mini_sauvage_christian_miniature", "sauvage", "Dior Sauvage EDP", "Christian Dior Sauvage EDP 10ml Miniature", "variant_add", "EDP", None, "EDP", 10, "mini"),
    ("mini_sauvage_houseless_travel", "sauvage", "Dior Sauvage EDP", "Sauvage EDP 10ml Travel Spray", "identity_subset", "EDP", None, "EDP", 10, "mini"),
    ("mini_aventus_houseless_travel", "aventus", "Creed Aventus EDP", "Aventus EDP 10ml Travel Spray", "identity_subset", "EDP", None, "EDP", 10, "mini"),
    # M1bR-6: the size branch does not change (the two Sauvage rows are a stated limit)
    ("size_sauvage_R100", "sauvage", "Dior Sauvage EDP 100ml", "DIOR Sauvage Eau de Parfum Spray", "candidate_missing_query_axis", "EDP", 100, "EDP", 100, "base"),
    ("size_sauvage_T", "sauvage", "Dior Sauvage 100 ML Edp", "DIOR Sauvage Eau de Parfum Spray", "candidate_missing_query_axis", "EDP", 100, "EDP", 100, "base"),
    ("size_aventus_no_size", "aventus", "Creed Aventus EDP 100ml", "Creed Aventus Eau de Parfum", "candidate_missing_query_axis", "EDP", 100, "EDP", 100, "base"),
    ("size_aventus_bare", "aventus", "Creed Aventus EDP 100ml", "Creed Aventus", "candidate_missing_query_axis", "EDP", 100, "EDP", 100, "base"),
    # M1bR-4 probes: the house-only guard
    ("y_lhomme", "y", "Yves Saint Laurent Y EDP", "YSL L'Homme EDP 100ml", "identity_subset", "EDP", None, "EDP", 100, "other"),
    ("y_house_only_title", "y", "Yves Saint Laurent Y EDP", "YSL EDP 100ml", "identity_subset", "EDP", None, "EDP", 100, "other"),
    ("homme_house_only_query", "homme", "Dior Homme EDP", "Christian Dior Homme EDP 100ml", "variant_add", "EDP", None, "EDP", 100, "base"),
    ("homme_intense_house_only_query", "homme", "Dior Homme EDP", "Dior Homme Intense EDP 100ml", "variant_add", "EDP", None, "EDP", 100, "flanker"),
    # M1bR-5 probes: Eau Sauvage, another house, partial house words, non-distinctive lines
    ("eau_sauvage_houseless", "sauvage", "Dior Sauvage EDP", "Eau Sauvage EDP 100ml", "identity_subset", "EDP", None, "EDP", 100, "other"),
    ("eau_sauvage_house_edt", "sauvage", "Dior Sauvage EDP", "Dior Eau Sauvage Eau de Toilette 100ml", "concentration", "EDP", None, "EDT", 100, "other"),
    ("eau_sauvage_parfum_houseless", "sauvage", "Dior Sauvage EDP", "Eau Sauvage Parfum 100ml", "concentration", "EDP", None, "Parfum", 100, "other"),
    ("eau_sauvage_house_edp", "sauvage", "Dior Sauvage EDP", "Dior Eau Sauvage EDP 100ml", "variant_add", "EDP", None, "EDP", 100, "other"),
    ("other_house_armaf_sauvage", "sauvage", "Dior Sauvage EDP", "Armaf Sauvage EDP 100ml", "identity_subset", "EDP", None, "EDP", 100, "dupe"),
    ("mfk_partial_member_title", "br540", MFK_Q, "Francis Baccarat Rouge 540 EDP 70ml", "identity_subset", "EDP", None, "EDP", 70, "base"),
    # M1bR-4 TRIGGER: a group the title alone names is not folded (the house stays an extra
    # token and the variant-add step rejects it as today)
    ("title_only_group_ysl", "libre", "Libre EDP", "YSL Libre EDP 90ml", "variant_add", "EDP", None, "EDP", 90, "base"),
    ("title_only_group_dior", "sauvage", "Sauvage EDP", "Christian Dior Sauvage EDP 100ml", "variant_add", "EDP", None, "EDP", 100, "base"),
    ("houseless_libre_not_distinctive", "libre", "Yves Saint Laurent Libre EDP", "Libre Eau de Parfum 90ml", "identity_subset", "EDP", None, "EDP", 90, "base"),
    ("houseless_y_not_distinctive", "y", "Yves Saint Laurent Y EDP", "Y Eau de Parfum 100ml", "identity_subset", "EDP", None, "EDP", 100, "base"),
    ("houseless_eros_not_distinctive", "eros", "Versace Eros EDT", "Eros Eau de Toilette 100ml", "identity_subset", "EDT", None, "EDT", 100, "base"),
    ("houseless_tygar_not_distinctive", "tygar", "Bvlgari Tygar EDP", "Tygar Eau de Parfum 125ml", "identity_subset", "EDP", None, "EDP", 125, "base"),
    ("houseless_hawas_not_distinctive", "hawas", "Rasasi Hawas EDP", "Hawas Eau de Parfum 100ml", "identity_subset", "EDP", None, "EDP", 100, "base"),
)
# Non-fragrance pairs that carry alias-group words (M1bR-3): the verdict with the flag ON is
# the base verdict (category, query, title, base _selection_match), measured at the base.
NON_FRAGRANCE_ROWS = (
    ("fashion", "Emporio Armani Logo T-Shirt", "Giorgio Armani Logo T-Shirt", False),
    ("fashion", "Christian Dior Saddle Bag", "Dior Saddle Bag", False),
    ("fashion", "Dior Saddle Bag", "Christian Dior Saddle Bag", False),
    ("fashion", "Dolce Gabbana Logo T-Shirt", "D&G Logo T-Shirt", False),
    ("fashion", "Calvin Klein Slim Fit Jeans", "CK Slim Fit Jeans", False),
    ("fashion", "Calvin Klein Eternity Watch", "CK Calvin Klein Eternity Watch Black", True),
    ("other", "Montblanc Meisterstuck Classique Pen", "Mont Blanc Meisterstuck Classique Pen", False),
    ("electronics", "Emporio Armani Smartwatch ART5", "Giorgio Armani Smartwatch ART5", False),
    ("makeup", "Giorgio Armani Luminous Silk Foundation", "Armani Luminous Silk Foundation", False),
    ("skincare", "Lancome Advanced Genifique Serum", "Lancome Paris Advanced Genifique Serum", False),
)
# The "other" chip re-infers fragrances before extraction (M1bR-3): the fold applies there.
OTHER_REINFERRED_ROWS = (
    ("other_dior_christian", "Dior Sauvage EDP", "Christian Dior Sauvage EDP 60ml"),
    ("other_montblanc_explorer", "Montblanc Explorer EDP", "Mont Blanc Explorer EDP 100ml"),
)
SINGLE_CONCENTRATION_LINES = frozenset({"Aventus", "Layton", "Khamrah", "Hawas"})


def _truth(q_conc, q_size, t_conc, t_size, cls):
    """R4 run_matrix.truth_price."""
    if cls not in ("base", "size"):
        return False
    if t_conc != q_conc:
        return False
    if q_size is not None and t_size != q_size:
        return False
    return True


# ---------------------------------------------------------------- flag reader (RED)


def test_red_reader_contract(monkeypatch):
    """M1bR-2: price_service.match_fold_enabled(), the house idiom, read per call."""
    _clean(monkeypatch)
    reader = _reader()
    assert reader() is False
    for value in ON_SPELLINGS:
        monkeypatch.setenv(FLAG, value)
        assert reader() is True, value
    for value in OFF_SPELLINGS:
        if value is None:
            monkeypatch.delenv(FLAG, raising=False)
        else:
            monkeypatch.setenv(FLAG, value)
        assert reader() is False, value


def test_red_reader_per_call(monkeypatch):
    """MB10: the flag is read per call; one process sees OFF, ON, OFF, ON."""
    query, title = "Dior Sauvage EDP", "Christian Dior Sauvage EDP 60ml"
    for value, expected in ((None, False), ("true", True), ("false", False), (" On ", True)):
        _clean(monkeypatch, **{FLAG: value})
        assert _sel(query, title) is expected, (value, expected)


def test_red_extra_alias_table():
    """M1bR-4: the private extra group read only by the fold; no ysl entry (the base ysl
    group already holds saint and laurent: test_pin_ysl_group_covers_saint_laurent)."""
    groups = getattr(ps, EXTRA_TABLE, None)
    assert groups is not None, "price_service.%s is missing" % EXTRA_TABLE
    assert [frozenset(g) for g in groups] == [
        frozenset({"mfk", "maison francis kurkdjian", "francis kurkdjian"})
    ]
    for rel in (
        "app/services/image_relevance.py",
        "app/services/product_resolver.py",
        "app/services/spec_spine_service.py",
        "app/services/zyte_service.py",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert EXTRA_TABLE not in text, rel


# ---------------------------------------------------------------- frozen tables (PIN)

BASE_ALIAS_GROUPS = (
    frozenset({"ysl", "yves", "saint", "laurent"}),
    frozenset({"dg", "d&g", "dolce", "gabbana"}),
    frozenset({"jpg", "jean", "paul", "gaultier"}),
    frozenset({"ck", "calvin", "klein"}),
    frozenset({"ch", "carolina", "herrera"}),
    frozenset({"mj", "marc", "jacobs"}),
    frozenset({"tf", "tom", "ford"}),
    frozenset({"vr", "v&r", "viktor", "rolf"}),
    frozenset({"dior", "christian"}),
    frozenset({"versace", "gianni"}),
    frozenset({"armani", "giorgio", "emporio"}),
    frozenset({"lancome", "paris"}),
    frozenset({"montblanc", "mont", "blanc"}),
)
BASE_FRAGRANCE_PADDING = (
    "and", "atomiser", "atomizer", "authentic", "brand", "femme", "femmes", "for",
    "fragrance", "fragrances", "full", "gents", "genuine", "gift", "her", "him", "homme",
    "hommes", "ladies", "man", "men", "mens", "natural", "new", "original", "perfume",
    "perfumes", "pour", "scent", "scented", "size", "spray", "sprays", "the", "unisex",
    "vapo", "vaporisateur", "vaporizer", "with", "woman", "women", "womens",
)
BASE_GENDER_STRIP = (
    "damen", "donna", "femme", "femmes", "herren", "homme", "hommes", "man", "men", "mens",
    "pour", "uomo", "woman", "women", "womens",
)
PADDING_WORDS = ("pour", "homme", "femme", "vaporisateur", "vapo", "natural")


def test_pin_brand_alias_groups_frozen():
    """M1bR-4 / MB11: the shared _BRAND_ALIAS_GROUPS stay byte-identical."""
    assert tuple(ps._BRAND_ALIAS_GROUPS) == BASE_ALIAS_GROUPS


def test_pin_ysl_group_covers_saint_laurent():
    """M1bR-4: saint and laurent are members of the base ysl group, so no extra entry."""
    ysl = [g for g in ps._BRAND_ALIAS_GROUPS if "ysl" in g]
    assert len(ysl) == 1 and {"saint", "laurent", "yves"} <= ysl[0]


def test_pin_padding_words_already_stripped(monkeypatch):
    """M1bR-8: the six words are stripped at the base; both tables stay byte-identical."""
    _clean(monkeypatch)
    assert tuple(sorted(ps._FRAGRANCE_PADDING_TOKENS)) == BASE_FRAGRANCE_PADDING
    assert tuple(sorted(ps._GENDER_IDENTITY_STRIP)) == BASE_GENDER_STRIP
    for word in PADDING_WORDS:
        assert word in ps._FRAGRANCE_PADDING_TOKENS or word in ps._GENDER_IDENTITY_STRIP, word
        core = ps._identity_tokens_ps("Dior Sauvage " + word, "", CAT)
        assert core - ps._category_padding(CAT) == {"dior", "sauvage"}, word
    title = "Dior Sauvage Pour Homme Vaporisateur Natural Vapo Femme"
    core = ps._identity_tokens_ps(title, "", CAT)
    assert core == {"dior", "sauvage", "natural", "vapo", "vaporisateur"}
    assert core - ps._category_padding(CAT) == {"dior", "sauvage"}


def test_pin_descriptor_memo_key_and_no_verdict_memo():
    """M1bR-2: the descriptor memo key does not change and no memo sits above the verdict
    functions (the fold and the default run in the verdict step)."""
    wrapped = getattr(ps._extract_variant_descriptor_cached, "__wrapped__", None)
    assert wrapped is not None
    assert list(inspect.signature(wrapped).parameters) == [
        "text", "category", "brand", "_gate_on", "_axes_on",
    ]
    for name in (
        "descriptor_verdict", "_descriptor_selection_verdict", "_descriptor_axis_mismatch",
        "_vd_candidate_missing_query_axis", "_selection_match", "is_exact_match",
        "_backstop_identity_ok", "extract_variant_descriptor",
    ):
        fn = getattr(ps, name)
        assert not hasattr(fn, "cache_info"), name
        assert not hasattr(fn, "__wrapped__"), name


# ---------------------------------------------------------------- ACCEPT rows (RED)


@pytest.mark.parametrize("row", ACCEPT_ROWS, ids=[r[0] for r in ACCEPT_ROWS])
def test_accept(monkeypatch, row):
    """M1bR-9: rejected with the flag OFF (base axis named), accepted with it ON.
    Reads _selection_match and descriptor_verdict (SELECTION)."""
    rid, line, query, title, base_axis = row[:5]
    _clean(monkeypatch)
    assert _sel(query, title) is False, rid
    assert _verdict(query, title).axis == base_axis, rid
    _on(monkeypatch)
    assert _sel(query, title) is True, "%s: %s | %s" % (rid, query, title)
    assert _verdict(query, title).match is True, rid


@pytest.mark.parametrize("row", OTHER_REINFERRED_ROWS, ids=[r[0] for r in OTHER_REINFERRED_ROWS])
def test_accept_other_chip_reinferred(monkeypatch, row):
    """M1bR-3: the scope is the category AFTER the "other" re-inference."""
    rid, query, title = row
    _clean(monkeypatch)
    assert _sel(query, title, "other") is False, rid
    _on(monkeypatch)
    assert _sel(query, title, "other") is True, rid


# ---------------------------------------------------------------- GUARD rows


@pytest.mark.parametrize("row", GUARD_ROWS, ids=[r[0] for r in GUARD_ROWS])
def test_guard(monkeypatch, row):
    """M1bR-9: rejected with the flag OFF and with it ON (the walk repeats it per mix)."""
    rid, line, query, title, base_axis = row[:5]
    _clean(monkeypatch)
    assert _sel(query, title) is False, rid
    assert _verdict(query, title).axis == base_axis, rid
    _on(monkeypatch)
    assert _sel(query, title) is False, "%s: %s | %s" % (rid, query, title)


def test_guard_every_arabic_title(monkeypatch):
    """M1bR-9: every Arabic corpus title stays rejected under its line's queries, both shapes."""
    arabic = [r for r in ROWS if _is_arabic(r[1])]
    assert len(arabic) == 27
    for flag in (None, "true"):
        _clean(monkeypatch, **{FLAG: flag})
        for qid, line, typed, resolved, _c, _s in QUERIES:
            for row in arabic:
                if row[0] != line:
                    continue
                for query in (typed, resolved):
                    assert _sel(query, row[1]) is False, (flag, qid, query)


# ---------------------------------------------------------------- scope pins (PIN, flag ON)


@pytest.mark.parametrize("row", NON_FRAGRANCE_ROWS, ids=["%s-%d" % (r[0], i) for i, r in enumerate(NON_FRAGRANCE_ROWS)])
def test_pin_non_fragrance_unchanged(monkeypatch, row):
    """M1bR-3 / MB9: every other category is byte-identical with the flag ON."""
    category, query, title, base = row
    for flags in ({}, {VDA: "true", LMG: "true", DG2: "true", PNL: "true"}):
        _on(monkeypatch, **flags)
        assert _sel(query, title, category) is base, (category, query, title, flags)
        _clean(monkeypatch, **flags)
        assert _sel(query, title, category) is base, (category, query, title, flags)


def test_pin_exact_mode_takes_no_default(monkeypatch):
    """M1bR-3 / MB8: the concentration default is SELECTION only; EXACT and BACKSTOP keep
    the base verdict with the flag ON."""
    rows = (
        ("Creed Aventus EDP", "Creed Aventus 50ml", False, True),
        ("Creed Aventus EDP", "Creed Aventus 100ml", False, True),
        ("Lattafa Khamrah EDP", "Lattafa Khamrah 100ml", False, True),
        ("Dior Sauvage EDP", "Sauvage EDP 100ml", False, True),
        ("Dior Sauvage EDP", "Christian Dior Sauvage EDP 60ml", False, True),
        ("Yves Saint Laurent Libre EDP", "YSL Libre EDP 90ml", False, True),
    )
    for flag in (None, "true"):
        _clean(monkeypatch, **{FLAG: flag})
        for query, title, exact, backstop in rows:
            assert bool(ps.is_exact_match(query, title, CAT)) is exact, (flag, title)
            assert bool(ps._backstop_identity_ok(query, title, CAT)) is backstop, (flag, title)
            q = ps.extract_variant_descriptor(query, CAT, "")
            c = ps.extract_variant_descriptor(title, CAT, "")
            assert ps.descriptor_verdict(q, c, CAT, ps.DESCRIPTOR_MODE_EXACT).match is exact
            assert ps.descriptor_verdict(q, c, CAT, ps.DESCRIPTOR_MODE_BACKSTOP).match is backstop


# ---------------------------------------------------------------- the accessor (RED)


def _file_lines():
    return json.loads(LINES_FILE.read_text(encoding="ascii"))["lines"]


FIELDS = ("house", "line", "house_aliases", "aliases", "concentrations", "single_concentration", "flankers")


def test_red_accessor_contract(monkeypatch):
    """M1bR-7: one public read-only function; immutable records of the validated lines."""
    _clean(monkeypatch)
    pr._reset_resolver_state()
    records = _accessor()()
    assert isinstance(records, tuple)
    items = _file_lines()
    assert len(records) == len(items) == 14
    for record, item in zip(records, items):
        assert dataclasses.is_dataclass(record) or hasattr(record, "_replace")
        for field in FIELDS:
            assert hasattr(record, field), field
        assert record.house == item["house"] and record.line == item["line"]
        for field in ("house_aliases", "aliases", "concentrations", "flankers"):
            value = getattr(record, field)
            assert isinstance(value, tuple), field
            assert value == tuple(item[field]), (item["line"], field)
        assert record.single_concentration is bool(item.get("single_concentration", False))
        with pytest.raises((AttributeError, TypeError, dataclasses.FrozenInstanceError)):
            setattr(record, "line", "x")
        hash(record)
    singles = {r.line for r in records if r.single_concentration}
    assert singles == SINGLE_CONCENTRATION_LINES
    assert _accessor()() == records


def test_red_accessor_no_file_read_per_call(monkeypatch):
    """M1bR-7: no file read per call once the lines are cached."""
    _clean(monkeypatch)
    pr._reset_resolver_state()
    accessor = _accessor()
    first = accessor()
    reads = []
    real_read_bytes = pathlib.Path.read_bytes
    real_read_text = pathlib.Path.read_text
    real_open = builtins.open

    def _rb(self, *a, **k):
        reads.append(str(self))
        return real_read_bytes(self, *a, **k)

    def _rt(self, *a, **k):
        reads.append(str(self))
        return real_read_text(self, *a, **k)

    def _op(file, *a, **k):
        reads.append(str(file))
        return real_open(file, *a, **k)

    monkeypatch.setattr(pathlib.Path, "read_bytes", _rb)
    monkeypatch.setattr(pathlib.Path, "read_text", _rt)
    monkeypatch.setattr(builtins, "open", _op)
    for _ in range(3):
        assert accessor() == first
    monkeypatch.undo()
    assert [p for p in reads if "fragrance_lines" in p] == []


def test_red_accessor_independent_of_resolver_flag(monkeypatch):
    """M1bR-7: the accessor works whatever ENABLE_PRODUCT_RESOLVER is."""
    _clean(monkeypatch)
    pr._reset_resolver_state()
    baseline = _accessor()()
    assert len(baseline) == 14
    for value in ("true", "false", None):
        _clean(monkeypatch, **{RESOLVER_FLAG: value})
        assert _accessor()() == baseline, value


def test_red_accessor_calls_no_model_no_network_no_spend(monkeypatch):
    """M1bR-7: never the model, the network or the spend admit."""
    _clean(monkeypatch)
    pr._reset_resolver_state()
    calls = []

    def _boom(*a, **k):
        calls.append(1)
        raise AssertionError("the accessor reached a model, spend or network seam")

    monkeypatch.setattr(pr._llm_router, "decide", _boom)
    monkeypatch.setattr(pr._llm_router, "route", _boom)
    monkeypatch.setattr(pr._llm_breaker, "guarded_llm_create", _boom)
    monkeypatch.setattr(socket.socket, "connect", _boom)
    records = _accessor()()
    assert len(records) == 14 and calls == []


@pytest.mark.parametrize("bad", ("missing", "not_json", "not_ascii", "bad_field"))
def test_red_accessor_empty_when_lines_fail(monkeypatch, tmp_path, bad):
    """M1bR-7: () when the lines file fails to load or validate; then the houseless rule and
    the default do nothing, and the fold still works."""
    _clean(monkeypatch)
    target = tmp_path / "fragrance_lines.json"
    if bad == "not_json":
        target.write_text("{not json", encoding="ascii")
    elif bad == "not_ascii":
        target.write_bytes(LINES_FILE.read_bytes().replace(b'"Aventus"', b'"Aventus\xc3\xa9"'))
    elif bad == "bad_field":
        data = json.loads(LINES_FILE.read_text(encoding="ascii"))
        data["lines"][2]["single_concentration"] = "yes"
        target.write_text(json.dumps(data), encoding="ascii")
    monkeypatch.setattr(pr, "LINES_PATH", target)
    pr._reset_resolver_state()
    try:
        assert _accessor()() == ()
        _on(monkeypatch)
        assert _sel("Creed Aventus EDP", "Creed Aventus 50ml") is False
        assert _sel("Dior Sauvage EDP", "Sauvage EDP 100ml") is False
        assert _sel("Dior Sauvage EDP", "Christian Dior Sauvage EDP 60ml") is True
        assert _sel("Yves Saint Laurent Libre EDP", "YSL Libre EDP 90ml") is True
    finally:
        monkeypatch.undo()
        pr._reset_resolver_state()


def test_red_single_source_default_follows_accessor(monkeypatch):
    """MB12 / M1bR-7: the default reads the line through the accessor (no copied list):
    patch the accessor and the verdict follows, both ways."""
    _on(monkeypatch)
    pr._reset_resolver_state()
    real = _accessor()()
    by_line = {r.line: r for r in real}
    assert _sel("Creed Aventus EDP", "Creed Aventus 50ml") is True
    patched = tuple(_with(r, single_concentration=False) if r.line == "Aventus" else r for r in real)
    monkeypatch.setattr(pr, ACCESSOR, lambda: patched)
    assert _sel("Creed Aventus EDP", "Creed Aventus 50ml") is False
    smw = _with(by_line["Aventus"], line="Silver Mountain Water", aliases=("silver mountain water",), flankers=())
    query, title = "Creed Silver Mountain Water EDP", "Creed Silver Mountain Water 100ml"
    monkeypatch.setattr(pr, ACCESSOR, lambda: real)
    assert _sel(query, title) is False
    monkeypatch.setattr(pr, ACCESSOR, lambda: real + (smw,))
    assert _sel(query, title) is True


def test_red_single_source_houseless_follows_accessor(monkeypatch):
    """MB12 / M1bR-7: the houseless rule reads the line through the accessor."""
    _on(monkeypatch)
    pr._reset_resolver_state()
    real = _accessor()()
    assert _sel("Dior Sauvage EDP", "Sauvage EDP 100ml") is True
    monkeypatch.setattr(pr, ACCESSOR, lambda: tuple(r for r in real if r.line != "Sauvage"))
    assert _sel("Dior Sauvage EDP", "Sauvage EDP 100ml") is False
    monkeypatch.setattr(pr, ACCESSOR, lambda: ())
    assert _sel("Dior Sauvage EDP", "Sauvage EDP 100ml") is False
    assert _sel("Dior Sauvage EDP", "Christian Dior Sauvage EDP 60ml") is True


# ---------------------------------------------------------------- the resolved query shapes (PIN)


def test_pin_resolved_queries(monkeypatch):
    """M1bR-10: the resolved shape is what the lexicon arm and apply_resolution produce for
    the typed text (no model), keyed by _shopping_cache_key."""
    from app.services import structured_comparison_service as scs

    _clean(monkeypatch)
    pr._reset_resolver_state()
    for qid, line, typed, resolved, conc, size in QUERIES:
        side = pr.resolve_lexicon(typed, context=True)
        assert side.resolved, qid
        products = [
            {"brand": "", "name": typed, "variant": None, "search_query": typed, "category": "other"},
            {"brand": "", "name": "x", "variant": None, "search_query": "x", "category": "other"},
        ]
        resolution = pr.Resolution((side, pr.Side()), pr.OUTCOME_PARTIAL, None, 0)
        pr.apply_resolution(products, resolution)
        p = products[0]
        assert scs._shopping_cache_key(p["brand"], p["name"], p["variant"]) == resolved, qid


# ---------------------------------------------------------------- the walk (M1bR-10)

CHECKS = (
    "numbers_match", "shopping_listing_matches", "_selection_match", "shopping_chain",
    "is_price_showable", "should_cache_price", "reconcile_pair_sizes", "end_to_end",
    "is_exact_match", "_backstop_identity_ok",
)
IDENTICAL_CHECKS = (
    "numbers_match", "shopping_listing_matches", "is_price_showable", "reconcile_pair_sizes",
    "is_exact_match", "_backstop_identity_ok",
)
MONOTONE_CHECKS = ("_selection_match", "shopping_chain", "should_cache_price", "end_to_end")
SHAPES = ("typed", "resolved")
MIXES = tuple(
    (fold, pnl, vda, lmg, dg2, shape)
    for fold in (0, 1)
    for pnl in (0, 1)
    for vda in (0, 1)
    for lmg in (0, 1)
    for dg2 in (0, 1)
    for shape in SHAPES
)


def _mix_id(mix):
    return "fold%d_pnl%d_vda%d_lmg%d_dg2%d_%s" % mix


def _golden_key(mix):
    return "pnl%d_vda%d_lmg%d_dg2%d_%s" % mix[1:]


def _mix_flags(mix):
    fold, pnl, vda, lmg, dg2, shape = mix
    index = MIXES.index(mix)
    flags = {
        FLAG: (ON_SPELLINGS[index % len(ON_SPELLINGS)] if fold
               else OFF_SPELLINGS[index % len(OFF_SPELLINGS)]),
        PNL: "true" if pnl else None,
        VDA: "true" if vda else None,
        LMG: "true" if lmg else None,
        DG2: "true" if dg2 else None,
    }
    return flags


def _pairs(shape):
    """(pair id, query, line, title, right, query size, kind) for one query shape."""
    out = []
    for qid, line, typed, resolved, qconc, qsize in QUERIES:
        query = typed if shape == "typed" else resolved
        for i, row in enumerate(ROWS):
            if row[0] != line:
                continue
            kind = "arabic" if _is_arabic(row[1]) else "corpus"
            out.append(("c:%s:%d" % (qid, i), query, line, row[1],
                        _truth(qconc, qsize, row[2], row[3], row[4]), qsize, kind))
    for kind, rows in (("accept", ACCEPT_ROWS), ("guard", GUARD_ROWS)):
        for rid, line, query, title, _axis, qconc, qsize, tconc, tsize, cls in rows:
            out.append(("p:" + rid, query, line, title, _truth(qconc, qsize, tconc, tsize, cls), qsize, kind))
    return out


def _price(line, title):
    return {"amount": AMOUNT[line], "currency": "BHD", "source_method": "local_bhd",
            "title": title, "url": PDP, "retailer": "shop.example.bh"}


def _pair_size_ok(query, line, title, qsize):
    """R4 run_matrix.chk_pair_size: the real reconcile_pair_sizes with a partner."""
    partner = "Creed Aventus EDP" if line != "aventus" else "Dior Sauvage EDP"
    sz = " %dml" % qsize if qsize else ""
    p0 = {"full_name": query, "name": LINE_NAME[line], "price": _price(line, title)}
    p1 = {"full_name": partner + sz, "name": partner,
          "price": {"amount": 50.0, "currency": "BHD", "source_method": "local_bhd",
                    "title": partner + " " + (str(qsize) if qsize else "100") + "ml", "url": PDP}}
    ps.reconcile_pair_sizes([p0, p1], user_query=query + " vs " + partner + sz, candidates_by_name={})
    amount = p0["price"].get("amount")
    return isinstance(amount, (int, float)) and amount > 0


def _vectors(shape):
    pairs = _pairs(shape)
    vec = {name: [] for name in CHECKS}
    for _pid, query, line, title, _right, qsize, _kind in pairs:
        numbers = bool(ps.numbers_match(query, title))
        listing = bool(ps.shopping_listing_matches(query, title))
        select = bool(ps._selection_match(query, title, CAT))
        chain = bool(listing and select and ps._brand_evidence_ok(query, title, candidate_brand="", category=CAT))
        showable = bool(ps.is_price_showable(query, _price(line, title), CAT, enforce_correctness=True))
        cache = bool(ps.should_cache_price(query, _price(line, title), CAT))
        pair = bool(_pair_size_ok(query, line, title, qsize))
        vec["numbers_match"].append(numbers)
        vec["shopping_listing_matches"].append(listing)
        vec["_selection_match"].append(select)
        vec["shopping_chain"].append(chain)
        vec["is_price_showable"].append(showable)
        vec["should_cache_price"].append(cache)
        vec["reconcile_pair_sizes"].append(pair)
        vec["end_to_end"].append(bool(chain and showable and pair))
        vec["is_exact_match"].append(bool(ps.is_exact_match(query, title, CAT)))
        vec["_backstop_identity_ok"].append(bool(ps._backstop_identity_ok(query, title, CAT)))
    return pairs, vec


def _pack(bits):
    out = bytearray((len(bits) + 7) // 8)
    for i, bit in enumerate(bits):
        if bit:
            out[i // 8] |= 0x80 >> (i % 8)
    return base64.b64encode(bytes(out)).decode("ascii")


def _unpack(text, n):
    raw = base64.b64decode(text.encode("ascii"))
    return [bool(raw[i // 8] & (0x80 >> (i % 8))) for i in range(n)]


def _label(pairs, i):
    pid, query, _line, title, right, _qs, kind = pairs[i]
    return "%s | %s | %s | right=%s kind=%s" % (pid, query, title.encode("ascii", "backslashreplace").decode("ascii"), right, kind)


@pytest.mark.parametrize("mix", MIXES, ids=[_mix_id(m) for m in MIXES])
def test_walk_mix(monkeypatch, mix):
    """M1bR-10, one row per mix. fold OFF: every check equals the base GOLDEN and the accessor
    is never called; fold ON: THE RULE (accepted-wrong ON is a subset of OFF, per check),
    EXACT / BACKSTOP / chokepoint / untouched checks identical, no GUARD probe and no Arabic
    title changes, and no fold-OFF accept lost (a RED addition)."""
    fold, shape = mix[0], mix[5]
    _clean(monkeypatch, **_mix_flags(mix))
    calls = []
    real = getattr(pr, ACCESSOR, None)
    if callable(real):
        def _counting():
            calls.append(1)
            return real()
        monkeypatch.setattr(pr, ACCESSOR, _counting)
    pairs, vec = _vectors(shape)
    golden = GOLDEN[_golden_key(mix)]
    n = len(pairs)
    assert golden["n"] == n
    base = {name: _unpack(golden[name], n) for name in CHECKS}
    if not fold:
        for name in CHECKS:
            diff = [_label(pairs, i) for i in range(n) if vec[name][i] != base[name][i]]
            assert diff == [], "%s flag-OFF drift in %s: %s" % (_mix_id(mix), name, diff[:6])
        assert calls == [], "the accessor was read with %s OFF" % FLAG
        return
    problems = []
    for name in CHECKS:
        on, off = vec[name], base[name]
        new_aw = [i for i in range(n) if on[i] and not off[i] and not pairs[i][4]]
        if new_aw:
            problems.append("NEW accepted-wrong in %s: %s" % (name, [_label(pairs, i) for i in new_aw][:6]))
        if name in IDENTICAL_CHECKS:
            changed = [i for i in range(n) if on[i] != off[i]]
            if changed:
                problems.append("%s changed with the flag ON: %s" % (name, [_label(pairs, i) for i in changed][:6]))
        guard = [i for i in range(n) if pairs[i][6] == "guard" and on[i] and not off[i]]
        if guard:
            problems.append("GUARD probe accepted in %s: %s" % (name, [_label(pairs, i) for i in guard][:6]))
        arabic = [i for i in range(n) if pairs[i][6] == "arabic" and on[i] != off[i]]
        if arabic:
            problems.append("Arabic title changed in %s: %s" % (name, [_label(pairs, i) for i in arabic][:6]))
        if name in MONOTONE_CHECKS:
            lost = [i for i in range(n) if off[i] and not on[i]]
            if lost:
                problems.append("fold-OFF accept lost in %s: %s" % (name, [_label(pairs, i) for i in lost][:6]))
    assert problems == [], "%s: %s" % (_mix_id(mix), problems)


# ---------------------------------------------------------------- GOLDEN (recorded at the base d0b5a761)
# Per fold-OFF mix (ENABLE_PRICE_NOT_LOST, ENABLE_VARIANT_DESCRIPTOR_AXES,
# ENABLE_LISTING_MATCH_GUARD, ENABLE_DATA_GUARDS_V2, query shape): n pairs and, per check, the
# accept bits in _pairs() order, packed MSB first and base64-encoded.
GOLDEN = {
    'pnl0_vda0_lmg0_dg20_resolved': {
        "n": 248,
        'numbers_match': '////////////////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda0_lmg0_dg20_typed': {
        "n": 248,
        'numbers_match': '///////wIAb/////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wAIAA/+D/4G+H/x/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda0_lmg0_dg21_resolved': {
        "n": 248,
        'numbers_match': '////////////////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda0_lmg0_dg21_typed': {
        "n": 248,
        'numbers_match': '///////wIAb/////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wAIAA/+D/4G+H/x/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda0_lmg1_dg20_resolved': {
        "n": 248,
        'numbers_match': '////////////////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda0_lmg1_dg20_typed': {
        "n": 248,
        'numbers_match': '///////wIAb/////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wAIAA/+D/4G+H/x/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda0_lmg1_dg21_resolved': {
        "n": 248,
        'numbers_match': '////////////////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda0_lmg1_dg21_typed': {
        "n": 248,
        'numbers_match': '///////wIAb/////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wAIAA/+D/4G+H/x/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda1_lmg0_dg20_resolved': {
        "n": 248,
        'numbers_match': '////////////////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/4f9/r///++//64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda1_lmg0_dg20_typed': {
        "n": 248,
        'numbers_match': '///////wIAb/////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wAIAA/+D/4G+H/x/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/4f9/r///++//64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda1_lmg0_dg21_resolved': {
        "n": 248,
        'numbers_match': '////////////////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/4f9/r///++//64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda1_lmg0_dg21_typed': {
        "n": 248,
        'numbers_match': '///////wIAb/////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wAIAA/+D/4G+H/x/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/4f9/r///++//64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda1_lmg1_dg20_resolved': {
        "n": 248,
        'numbers_match': '////////////////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/of9/r///+60/64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda1_lmg1_dg20_typed': {
        "n": 248,
        'numbers_match': '///////wIAb/////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wAIAA/+D/4G+H/x/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/of9/r///+60/64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda1_lmg1_dg21_resolved': {
        "n": 248,
        'numbers_match': '////////////////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/of9/r///+60/64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABABgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl0_vda1_lmg1_dg21_typed': {
        "n": 248,
        'numbers_match': '///////wIAb/////////////////7/////////f//w==',
        'shopping_listing_matches': '5/8D3/wAIAA/+D/4G+H/x/h/x/H8bf+fv/4v//Z74A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/of9/r///+60/64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABhBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda0_lmg0_dg20_resolved': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda0_lmg0_dg20_typed': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4G+H/x/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda0_lmg0_dg21_resolved': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda0_lmg0_dg21_typed': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4G+H/x/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda0_lmg1_dg20_resolved': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgGAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda0_lmg1_dg20_typed': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4G+H/x/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgGAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda0_lmg1_dg21_resolved': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgGAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda0_lmg1_dg21_typed': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4G+H/x/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u8L+6QP7pA/8v/Af8D/Ovu/8f9/7///+///64R/z/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgGAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda1_lmg0_dg20_resolved': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/4f9/r///++//64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda1_lmg0_dg20_typed': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4G+H/x/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/4f9/r///++//64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda1_lmg0_dg21_resolved': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/4f9/r///++//64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABQBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda1_lmg0_dg21_typed': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4G+H/x/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/4f9/r///++//64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABxBgHAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgHAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda1_lmg1_dg20_resolved': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/of9+r///+yw/64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgGAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda1_lmg1_dg20_typed': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4G+H/x/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/of9+r///+yw/64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgGAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda1_lmg1_dg21_resolved': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4NMNJx/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/of9+r///+yw/64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAIAIABABABgGAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAfOP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAIAAAAABABgGAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAIAIABABABAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
    'pnl1_vda1_lmg1_dg21_typed': {
        "n": 248,
        'numbers_match': '/////////////////////////////////////////w==',
        'shopping_listing_matches': '5/8D3/wPf/A/+D/4G+H/x/h/x/H8ff+fv/4v//574A==',
        '_selection_match': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'shopping_chain': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'is_price_showable': 'u4L+6AP7oA/8v/Af8D+Ovu/of9+r///+yw/64R/T/w==',
        'should_cache_price': 'goQACAAAIAA8ADAAEAGAQABhBgGAAAAAAAAAAAAAAA==',
        'reconcile_pair_sizes': '/lL////////zX///7XyIOAROP7/38gxr70f4GB//LQ==',
        'end_to_end': 'ggAACAAAIAAwADAAAACAAABABgGAAAAAAAAAAAAAAA==',
        'is_exact_match': 'gIQAAAAAAAA8ADAAAAEAQABgBAAAAAAAAAAAAAAAAA==',
        '_backstop_identity_ok': 'u//+6UP7pQ/8//Bf8P/P/v/////////+///////z/w==',
    },
}
