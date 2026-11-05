"""D22 NIGHTLY-LEARNING RED rows (spec S81-G5 section 5, as amended by
RULINGS_S81_G5 R-G5-1..R-G5-16): the nightly DB-only learning job
``scripts/cron_learning.py`` (flag ENABLE_LEARNING_JOB, the G2 mode idiom through
``kb_seed_common.run_mode``: unset / garbage OFF, the house truthy set DRY, the
exact word ``apply`` WRITE; ``--dry-run`` downgrades) and its service config
``railway.learning.json``; the retirement of the rotation cron (E2 / E3).

Every RED row fails at base on an AssertionError only: the module is reached
through ``_mod()`` (find_spec + an assertion), never imported at module top.
Every PIN row is green at base and runs with the FULL configuration (the flag,
the five knobs and the service-role names set to synthetic values) where it
reads a flag or knob.

The fake Supabase client is the D17 recorder form (tests/test_s81_d17_coverage.py)
with filter EVALUATION (gte / lt / in_ applied, order sorting, range slicing) and
column PROJECTION (an ``alias:json->>path`` item is served from the seeded
``alias`` key), seeded through the injected ``client`` argument of ``main``.

Hygiene: pure ASCII, LF; bounded runner only; netguard on (no socket: the
client is an in-memory fake); synthetic names and ids only, every id, device
key, email shape or phone shape built at run time.
"""
from __future__ import annotations

import ast
import copy
import importlib
import importlib.util
import itertools
import json
import logging
import math
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THIS = Path(__file__).resolve()
MOD = "scripts.cron_learning"
FLAG = "ENABLE_LEARNING_JOB"
KNOBS = (
    "LEARNING_WINDOW_DAYS", "LEARNING_MIN_CASES", "LEARNING_MIN_DEVICES",
    "LEARNING_MAX_ROWS", "LEARNING_EXEMPLARS_PER_CATEGORY",
)
SCRIPT = ROOT / "scripts" / "cron_learning.py"
CONFIG = ROOT / "railway.learning.json"
ROTATION_NAME = "cron_few_shot_" + "rotation"
ROTATION = ROOT / "scripts" / (ROTATION_NAME + ".py")

NOW = datetime(2026, 11, 5, 3, 0, tzinfo=timezone.utc)
DAY = date(2026, 11, 4)
WIN_START = "2026-10-29T00:00:00+00:00"
WIN_END = "2026-11-05T00:00:00+00:00"
T_IN = "2026-11-02T10:00:00+00:00"
T_LATE = "2026-11-04T06:00:00+00:00"
T_BEFORE = "2026-10-28T23:59:59+00:00"

# the 2.2 constants (literals here, read from the spec, never from the module)
T_FEEDBACK = "comparison_feedback"
T_COMPARISONS = "comparisons"
T_EVENTS = "user_events"
T_SEARCH = "search_logs"
T_CRITIQUES = "verdict_critiques"
T_GAPS = "kb_gaps"
T_KBFB = "kb_feedback"
T_SPECS = "kb_specs"
T_COVERAGE = "kb_coverage_daily"
READ_TABLES = (T_FEEDBACK, T_COMPARISONS, T_EVENTS, T_SEARCH, T_CRITIQUES, T_GAPS, T_KBFB, T_SPECS)
WINDOWED = {T_FEEDBACK: "created_at", T_CRITIQUES: "created_at", T_EVENTS: "created_at",
            T_SEARCH: "created_at", T_GAPS: "last_seen", T_KBFB: "created_at"}
FEEDBACK_COLUMNS = "id,user_id,comparison_id,useful,winner_correct,price_correct,specs_correct,created_at"
COMPARISON_COLUMNS = ("id,user_id,product_names,category:full_response->>category_used,"
                      "wi:full_response->>winner_index,"
                      "m0:full_response->overview->products->0->price->>source_method,"
                      "m1:full_response->overview->products->1->price->>source_method,"
                      "a0:full_response->overview->products->0->price->>amount,"
                      "a1:full_response->overview->products->1->price->>amount,"
                      "c0:full_response->overview->products->0->price->>currency,"
                      "c1:full_response->overview->products->1->price->>currency,"
                      "cwi:full_response->comparison->>winner_index,"
                      "wr:full_response->comparison->>winner_reason,"
                      "kt:full_response->comparison->>key_tradeoff,"
                      "vc:full_response->comparison->value_context")
EVENT_COLUMNS = "id,user_id,event_type,comparison_id,created_at"
SEARCH_COLUMNS = "id,user_id,success,is_synthetic,created_at"
CRITIQUE_COLUMNS = "id,comparison_id,bias_score,missing_citation_score,created_at"
GAP_COLUMNS = "id,field,state,demand_count,last_seen"
KB_FEEDBACK_COLUMNS = "id,compare_request_id,product_id,field,verdict,device_key,created_at"
SPEC_COLUMNS = "product_id,field,source_url,cited"
SELECTS = {T_FEEDBACK: FEEDBACK_COLUMNS, T_COMPARISONS: COMPARISON_COLUMNS, T_EVENTS: EVENT_COLUMNS,
           T_SEARCH: SEARCH_COLUMNS, T_CRITIQUES: CRITIQUE_COLUMNS, T_GAPS: GAP_COLUMNS,
           T_KBFB: KB_FEEDBACK_COLUMNS, T_SPECS: SPEC_COLUMNS}
BUCKETS = ("identity_wrong", "price_wrong", "spec_missing", "spec_wrong", "verdict_unsupported", "verdict_wrong")
CATEGORIES = ("electronics", "grocery", "supplements", "makeup", "skincare", "haircare", "fragrances",
              "fashion", "other")
D05_FIELDS = ("identity", "image", "price", "size", "concentration", "specs", "rating", "review_count")
SOURCE_METHODS = ("local_bhd", "converted_usd", "page_scrape", "page_scrape_rendered", "firecrawl",
                  "scrapedo_rendered", "estimated")
SOURCES_EXTRA = ("mixed", "unknown", "specs", "verdict", "critic", "kb", "kb_gap")
ACTIONS = ("recheck_source", "drop_source_for_field", "needs_operator", "no_action")
ABANDON_EVENTS = ("result_abandon", "compare_cancelled", "scan_failed")
CONFIRM_EVENTS = ("save", "share_completed", "screenshot")
GAP_OPEN_STATES = ("open", "queued", "needs_operator")

EXPECTED_CONSTANTS = {
    "PREFIX": "[LEARNING]",
    "FLAG": FLAG,
    "REPORT_SCHEMA": "learning-report/1",
    "KB_COVERAGE_TABLE": T_COVERAGE,
    "KB_FEEDBACK_TABLE": T_KBFB,
    "COMPARISON_FEEDBACK_TABLE": T_FEEDBACK,
    "COMPARISONS_TABLE": T_COMPARISONS,
    "USER_EVENTS_TABLE": T_EVENTS,
    "SEARCH_LOGS_TABLE": T_SEARCH,
    "VERDICT_CRITIQUES_TABLE": T_CRITIQUES,
    "READ_TABLES": READ_TABLES,
    "FEEDBACK_COLUMNS": FEEDBACK_COLUMNS,
    "COMPARISON_COLUMNS": COMPARISON_COLUMNS,
    "EVENT_COLUMNS": EVENT_COLUMNS,
    "SEARCH_COLUMNS": SEARCH_COLUMNS,
    "CRITIQUE_COLUMNS": CRITIQUE_COLUMNS,
    "GAP_COLUMNS": GAP_COLUMNS,
    "KB_FEEDBACK_COLUMNS": KB_FEEDBACK_COLUMNS,
    "SPEC_COLUMNS": SPEC_COLUMNS,
    "BUCKETS": BUCKETS,
    "CATEGORIES": CATEGORIES,
    "D05_FIELDS": D05_FIELDS,
    "SOURCE_METHODS": SOURCE_METHODS,
    "SOURCES_EXTRA": SOURCES_EXTRA,
    "ACTIONS": ACTIONS,
    "ABANDON_EVENTS": ABANDON_EVENTS,
    "CONFIRM_EVENTS": CONFIRM_EVENTS,
    "GAP_OPEN_STATES": GAP_OPEN_STATES,
    "HINT_PREFIX": "pdp_",
    "CRITIQUE_THRESHOLD": 7,
    "MISSING_TABLE_CODES": ("42P01", "PGRST205"),
    "IN_CHUNK": 100,
}

OFF_VALUES = [None, "", "false", " FALSE ", "0", "off", "no", "garbage", "dry"]
DRY_VALUES = ["true", " TRUE ", "1", "yes", "On"]
APPLY_VALUES = ["apply", " APPLY "]

OFF_LINE = "[LEARNING] mode=off ENABLE_LEARNING_JOB not set; skipping run"
_TYPE = r"\([A-Za-z_][A-Za-z0-9_]*\)"
TEMPLATES = [
    re.compile(r"^\[LEARNING\] mode=off ENABLE_LEARNING_JOB not set; skipping run$"),
    re.compile(r"^\[LEARNING\] bad --day; skipping run$"),
    re.compile(r"^\[LEARNING\] no service-role client " + _TYPE + "$"),
    re.compile(r"^\[LEARNING\] mode=(dry|apply) day=\d{4}-\d{2}-\d{2} window_days=\d+$"),
    re.compile(r"^\[LEARNING\] table=[a-z_]+ status=(ok|absent|error|capped) rows=\d+$"),
    re.compile(r"^\[LEARNING\] table=[a-z_]+ read failed " + _TYPE + "$"),
    re.compile(r"^\[LEARNING\] cluster bucket=[a-z_]+ category=[a-z]+ source=[a-z_]+ "
               r"field=[a-z][a-z0-9_]* cases=\d+ actors=\d+ systematic=[01]$"),
    re.compile(r"^\[LEARNING\] proposal bucket=[a-z_]+ category=[a-z]+ source=[a-z_]+ field=[a-z][a-z0-9_]* "
               r"action=(recheck_source|drop_source_for_field|needs_operator|no_action) grounding=\d+$"),
    re.compile(r"^\[LEARNING\] exemplar_set category=[a-z]+ version=\d{4}-\d{2}-\d{2}\.[a-z2-7]{16} count=\d+$"),
    re.compile(r"^\[LEARNING\] exemplar category=[a-z]+ version=\S+ names=.+ \|\| .+$"),
    re.compile(r"^\[LEARNING\] eval_case category=[a-z]+ winner=[01] prices=[01] names=.+ \|\| .+$"),
    re.compile(r"^\[LEARNING\] metric=[a-z][a-z0-9_.:-]* value=\S+ n=\d+$"),
    re.compile(r"^\[LEARNING\] report write failed " + _TYPE + "$"),
    re.compile(r"^\[LEARNING\] upsert failed " + _TYPE + "$"),
    re.compile(r"^\[LEARNING\] totals rows=\d+ not_built=\d+ clusters=\d+ systematic=\d+ mode=(dry|apply)$"),
]
TOTALS_LINE = TEMPLATES[-1]
METRIC_LINE = re.compile(r"^\[LEARNING\] metric=(\S+) value=(\S+) n=(\d+)$")
HEADER_LINE = TEMPLATES[3]

ALWAYS_METRICS = tuple("learning.cases." + b for b in BUCKETS) + (
    "learning.clusters.total", "learning.clusters.systematic", "learning.proposals",
    "learning.exemplar_candidates", "learning.eval_candidates", "learning.actors",
    "learning.events.abandon", "learning.events.confirm", "learning.searches.failed",
    "learning.dropped.deidentify",
)
CONDITIONAL_METRICS = tuple("learning.skipped." + t for t in READ_TABLES) + tuple(
    "learning.capped." + t for t in READ_TABLES)

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
HEX64_RE = re.compile(r"[0-9a-fA-F]{64}")
EIGHT_DIGITS_RE = re.compile(r"[0-9]{8}")
AT_SIGN = "@"
PHONE_PREFIX = "+97" + "3"


# ---------------------------------------------------------------------------
# module access (AssertionError only at base)
# ---------------------------------------------------------------------------

def _present(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _mod():
    assert _present(MOD), "scripts/cron_learning.py does not exist (D22 not implemented)"
    return importlib.import_module(MOD)


def _attr(mod, name):
    assert hasattr(mod, name), "%s.%s is missing (D22 not implemented)" % (mod.__name__, name)
    return getattr(mod, name)


def _call(mod, argv, **kwargs):
    """main(argv, **kwargs); any raise (SystemExit included) surfaces as an AssertionError."""
    main = _attr(mod, "main")
    try:
        return main(argv, **kwargs)
    except SystemExit as exc:
        raise AssertionError("main exited through SystemExit(%r)" % (exc.code,)) from None
    except Exception as exc:  # noqa: BLE001 - a raise out of main is a row failure, never an error
        raise AssertionError("main raised %s" % type(exc).__name__) from None


def _common():
    import scripts.kb_seed_common as common
    return common


def _leaf():
    from app.services import kb_service
    return kb_service


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    _leaf()  # the dotenv guard: the leaf (and its imports) load before any env is set
    for name in (FLAG,) + KNOBS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(_common(), "_now", lambda: NOW)
    yield


def _svc_env_name():
    return "SUPABASE_SERVICE_" + "KE" + "Y"


def _full_config(monkeypatch):
    """B1: every knob and the service-role names set to synthetic in-range values."""
    monkeypatch.setenv("LEARNING_WINDOW_DAYS", "5")
    monkeypatch.setenv("LEARNING_MIN_CASES", "2")
    monkeypatch.setenv("LEARNING_MIN_DEVICES", "1")
    monkeypatch.setenv("LEARNING_MAX_ROWS", "700")
    monkeypatch.setenv("LEARNING_EXEMPLARS_PER_CATEGORY", "4")
    monkeypatch.setenv("SUPABASE_URL", "https://" + "db.example.invalid")
    monkeypatch.setenv(_svc_env_name(), "-".join(["synthetic", "service", "value"]))


def _set_flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


# ---------------------------------------------------------------------------
# synthetic ids (built at run time)
# ---------------------------------------------------------------------------

def _uuid(n, tag):
    return "%08x-%04x-4%03x-8%03x-%012x" % (0x5EED0000 + tag, n, n, n, n)


def _uid(n):
    return _uuid(n, 1)


def _cid(n):
    return _uuid(n, 2)


def _rid(n):
    return _uuid(n, 3)


def _dev(ch):
    return ch * 64


P_A, P_B, P_C, P_D = "acme-rose-edp", "birch-oud-edt", "cedar-musk-edp", "dune-amber-edp"
URL_A = "https://" + "store-a.example.com/p/acme-rose"
URL_A2 = "https://" + "store-a.example.com/p/acme-rose-alt"
URL_B = "https://" + "store-b.example.com/p/birch-oud"


def _email():
    return "x" + AT_SIGN + "example.invalid"


# ---------------------------------------------------------------------------
# the seeded world
# ---------------------------------------------------------------------------

def _cmp(n, user, category, names, m0, m1, wi="0", cwi="0", wr=None, kt="The runner-up projects further.",
         vc=None, prices=("12.5", "20.0", "BHD", "BHD")):
    a0, a1, c0, c1 = prices
    return {
        "id": _cid(n), "user_id": user, "product_names": list(names), "category": category,
        "wi": wi, "m0": m0, "m1": m1, "a0": a0, "a1": a1, "c0": c0, "c1": c1, "cwi": cwi,
        "wr": wr if wr is not None else "Wins on value for daily wear.", "kt": kt,
        "vc": vc if vc is not None else {"product_0": "Fair for the size.", "product_1": "Costs more per ml."},
        "query": "qsentinel-cmp-%d" % n, "full_response": {"note": "frsentinel-%d" % n},
    }


def _fb(n, user, cmp_n, created=T_IN, **fields):
    row = {"id": "row-cf-%03d" % n, "user_id": user, "comparison_id": _cid(cmp_n) if cmp_n else None,
           "useful": None, "winner_correct": None, "price_correct": None, "specs_correct": None,
           "created_at": created, "change_suggestion": "cssentinel-%d" % n, "mattered_most": "mmsentinel-%d" % n}
    row.update(fields)
    return row


def _world():
    u = {i: _uid(i) for i in range(1, 7)}
    dev_a, dev_b = _dev("a"), _dev("b")
    comparisons = [
        _cmp(1, u[1], "fragrances", ("Acme Rose EDP", "Birch Oud EDT"), "page_scrape", "page_scrape"),
        _cmp(2, u[2], "fragrances", ("Cedar Musk EDP", "Dune Amber EDP"), "page_scrape", "page_scrape",
             wi="1", cwi="1"),
        _cmp(3, u[1], "fragrances", ("Elm Vetiver EDT", "Fern Citrus EDT"), "page_scrape", "page_scrape"),
        _cmp(4, u[6], "fragrances", ("Gale Iris EDP", "Haze Vanilla EDP"), "estimated", "estimated"),
        _cmp(5, u[4], "electronics", ("Ion Phone Pro", "Jet Phone Max"), "local_bhd", "local_bhd"),
        _cmp(6, u[5], "Electronics ", ("Kilo Tablet", "Lima Tablet"), "converted_usd", "converted_usd"),
        _cmp(7, None, None, ("Mono Soap", "Nova Soap"), "page_scrape", None),
        _cmp(8, u[6], "fragrances", ("Opal Bloom EDP", "Pine Smoke EDT"), "page_scrape", "page_scrape",
             wr="Ask " + _email() + " for the decant."),
    ]
    feedback = [
        _fb(1, u[1], 1, T_LATE, price_correct="wrong"),
        _fb(2, u[1], 1, price_correct="wrong"),                 # duplicate of 1: one case
        _fb(3, u[2], 2, price_correct="wrong"),
        _fb(4, u[1], 3, price_correct="wrong"),
        _fb(5, None, 7, price_correct="wrong"),                  # anonymous, unknown category / source
        _fb(6, u[3], 1, specs_correct="wrong"),
        _fb(7, u[3], 2, specs_correct="wrong"),
        _fb(8, u[3], 3, specs_correct="wrong"),
        _fb(9, u[4], 5, winner_correct="wrong"),
        _fb(10, u[5], 6, winner_correct="wrong"),
        _fb(11, u[2], 1, useful=True, winner_correct="correct", price_correct="correct"),
        _fb(12, u[2], 2, useful=True, winner_correct="correct"),
        _fb(13, u[3], 3, useful=True, winner_correct="correct"),
        _fb(14, u[4], 4, useful=True, winner_correct="correct"),
        _fb(15, u[5], 5, useful=True, winner_correct="correct"),
        _fb(16, u[6], 8, useful=True, winner_correct="correct"),  # winner_reason carries an email shape
        _fb(17, u[1], 6, useful=False, winner_correct="correct"),
        _fb(18, u[1], 7, useful=True, winner_correct="unsure"),
        _fb(19, u[6], 4, WIN_END, price_correct="wrong"),        # out: the end edge is exclusive
        _fb(20, u[6], 4, T_BEFORE, price_correct="wrong"),       # out: before the start
        _fb(21, u[5], 5, WIN_START, specs_correct="wrong"),      # in: the start edge is inclusive
        _fb(22, u[4], 1, useful=True, winner_correct="correct", price_correct="correct"),  # duplicate pair
    ]
    critiques = [
        {"id": "row-vc-1", "comparison_id": _cid(1), "bias_score": 8, "missing_citation_score": 6, "created_at": T_IN},
        {"id": "row-vc-2", "comparison_id": _cid(2), "bias_score": 7, "missing_citation_score": 7, "created_at": T_IN},
        {"id": "row-vc-3", "comparison_id": _cid(3), "bias_score": None, "missing_citation_score": None,
         "created_at": T_IN},
        {"id": "row-vc-4", "comparison_id": _cid(4), "bias_score": 6, "missing_citation_score": None,
         "created_at": T_IN},
        {"id": "row-vc-5", "comparison_id": _cid(2), "bias_score": 1, "missing_citation_score": 1,
         "created_at": T_BEFORE},
    ]
    events = [
        {"id": "row-ue-1", "user_id": u[1], "event_type": "result_abandon", "comparison_id": _cid(1), "created_at": T_IN},
        {"id": "row-ue-2", "user_id": u[2], "event_type": "compare_cancelled", "comparison_id": None, "created_at": T_IN},
        {"id": "row-ue-3", "user_id": u[1], "event_type": "scan_failed", "comparison_id": None, "created_at": T_IN},
        {"id": "row-ue-4", "user_id": u[3], "event_type": "save", "comparison_id": _cid(2), "created_at": T_IN},
        {"id": "row-ue-5", "user_id": u[3], "event_type": "share_completed", "comparison_id": _cid(2),
         "created_at": T_IN},
        {"id": "row-ue-6", "user_id": None, "event_type": "screenshot", "comparison_id": _cid(3), "created_at": T_IN},
        {"id": "row-ue-7", "user_id": u[4], "event_type": "tab_switch", "comparison_id": None, "created_at": T_IN},
        {"id": "row-ue-8", "user_id": u[4], "event_type": "result_abandon", "comparison_id": None,
         "created_at": WIN_END},
    ]
    for i, ev in enumerate(events):
        ev["event_data"] = {"note": "edsentinel-%d" % i}
        ev["session_id"] = "sssentinel-%d" % i
    searches = [
        {"id": "row-sl-1", "user_id": u[1], "success": True, "is_synthetic": False, "created_at": T_IN},
        {"id": "row-sl-2", "user_id": u[2], "success": True, "is_synthetic": None, "created_at": T_IN},
        {"id": "row-sl-3", "user_id": u[1], "success": False, "is_synthetic": False, "created_at": T_IN},
        {"id": "row-sl-4", "user_id": None, "success": False, "is_synthetic": True, "created_at": T_IN},
        {"id": "row-sl-5", "user_id": u[3], "success": False, "is_synthetic": None, "created_at": T_IN},
        {"id": "row-sl-6", "user_id": u[3], "success": False, "is_synthetic": False, "created_at": T_BEFORE},
    ]
    for i, s in enumerate(searches):
        s["query"] = "qsentinel-sl-%d" % i
        s["error_message"] = "emsentinel-%d" % i
        s["products_found"] = ["pfsentinel-%d" % i]
    gaps = [
        {"id": "row-kg-1", "product_key": "pksentinel-1", "field": "price", "state": "open", "demand_count": 4,
         "last_seen": T_IN, "source_hint": "shsentinel-1"},
        {"id": "row-kg-2", "product_key": "pksentinel-2", "field": "pdp_x", "state": "open", "demand_count": 9,
         "last_seen": T_IN, "source_hint": "shsentinel-2"},
        {"id": "row-kg-3", "product_key": "pksentinel-3", "field": "season", "state": "closed", "demand_count": 5,
         "last_seen": T_IN, "source_hint": "shsentinel-3"},
        {"id": "row-kg-4", "product_key": "pksentinel-4", "field": "longevity", "state": "queued",
         "demand_count": 2, "last_seen": T_IN, "source_hint": "shsentinel-4"},
        {"id": "row-kg-5", "product_key": "pksentinel-5", "field": "sillage", "state": "open", "demand_count": 7,
         "last_seen": T_BEFORE, "source_hint": "shsentinel-5"},
    ]
    kbfb = [
        {"id": "row-kf-1", "compare_request_id": _rid(1), "product_id": P_A, "field": "concentration",
         "verdict": "wrong", "device_key": dev_a, "created_at": T_IN},
        {"id": "row-kf-2", "compare_request_id": _rid(2), "product_id": P_A, "field": "concentration",
         "verdict": "wrong", "device_key": dev_b, "created_at": T_IN},
        {"id": "row-kf-3", "compare_request_id": _rid(3), "product_id": P_B, "field": "concentration",
         "verdict": "wrong", "device_key": dev_a, "created_at": T_IN},
        {"id": "row-kf-4", "compare_request_id": _rid(4), "product_id": P_C, "field": "price",
         "verdict": "wrong", "device_key": dev_b, "created_at": T_IN},
        {"id": "row-kf-5", "compare_request_id": _rid(5), "product_id": P_A, "field": "longevity",
         "verdict": "correct", "device_key": dev_a, "created_at": T_IN},
        {"id": "row-kf-6", "compare_request_id": _rid(6), "product_id": P_B, "field": "concentration",
         "verdict": "wrong", "device_key": dev_b, "created_at": WIN_END},
    ]
    specs = [
        {"id": "row-ks-1", "product_id": P_A, "field": "concentration", "source_url": URL_A, "cited": True,
         "value": "vsentinel-1"},
        {"id": "row-ks-2", "product_id": P_A, "field": "concentration", "source_url": URL_A2, "cited": False,
         "value": "vsentinel-2"},
        {"id": "row-ks-3", "product_id": P_B, "field": "longevity", "source_url": URL_B, "cited": True,
         "value": "vsentinel-3"},
        {"id": "row-ks-4", "product_id": P_B, "field": "concentration",
         "source_url": "https://" + "store-b.example.com/p/" + _email(), "cited": True, "value": "vsentinel-4"},
        {"id": "row-ks-5", "product_id": P_C, "field": "concentration", "source_url": URL_B, "cited": True,
         "value": "vsentinel-5"},
    ]
    return {T_COMPARISONS: comparisons, T_FEEDBACK: feedback, T_CRITIQUES: critiques, T_EVENTS: events,
            T_SEARCH: searches, T_GAPS: gaps, T_KBFB: kbfb, T_SPECS: specs}


_SENTINEL_KEYS = ("id", "user_id", "comparison_id", "compare_request_id", "device_key", "query",
                  "change_suggestion", "mattered_most", "event_data", "error_message", "products_found",
                  "source_hint", "product_key", "session_id", "full_response", "value")


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _strings(v)


def _sentinels(world):
    out = set()
    for rows in world.values():
        for row in rows:
            for key in _SENTINEL_KEYS:
                if key in row:
                    out.update(s for s in _strings(row[key]) if s)
    return out


# ---------------------------------------------------------------------------
# the fake client (the D17 recorder form + evaluation + projection)
# ---------------------------------------------------------------------------

def _ts(value):
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value


def _cmp_key(value):
    v = _ts(value)
    if isinstance(v, datetime):
        return (0, v.timestamp(), "")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return (1, float(v), "")
    return (2, 0.0, str(v))


class _Resp:
    def __init__(self, data):
        self.data = data
        self.count = None


class _Query:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.op, self.payload, self.kwargs = None, None, {}
        self.filters, self.orders, self.columns = [], [], None
        self.lim, self.rng = None, None

    def select(self, columns="*", **kwargs):
        if self.op is None:
            self.op = "select"
        self.columns = columns
        return self

    def upsert(self, rows, **kwargs):
        self.op, self.payload, self.kwargs = "upsert", copy.deepcopy(rows), dict(kwargs)
        return self

    def insert(self, rows, **kwargs):
        self.op, self.payload, self.kwargs = "insert", copy.deepcopy(rows), dict(kwargs)
        return self

    def update(self, payload, **kwargs):
        self.op, self.payload, self.kwargs = "update", copy.deepcopy(payload), dict(kwargs)
        return self

    def delete(self, **kwargs):
        self.op, self.kwargs = "delete", dict(kwargs)
        return self

    def order(self, column, desc=False, **kwargs):
        self.orders.append((column, bool(desc)))
        return self

    def limit(self, n, **kwargs):
        self.lim = n
        return self

    def range(self, start, end, **kwargs):
        self.rng = (start, end)
        return self

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _filter(*args, **kwargs):
            self.filters.append((name, list(args)))
            return self
        return _filter

    def execute(self):
        return self.client._execute(self)


def _match(row, name, args):
    if len(args) < 2:
        return True
    col, val = args[0], args[1]
    have = row.get(col)
    if name == "eq":
        return str(have) == str(val) if not isinstance(val, bool) else have is val
    if name == "in_":
        return have in list(val)
    if name in ("gte", "gt", "lte", "lt"):
        if have is None:
            return False
        a, b = _cmp_key(have), _cmp_key(val)
        return {"gte": a >= b, "gt": a > b, "lte": a <= b, "lt": a < b}[name]
    return True


def _project(row, columns):
    if not columns or columns.strip() == "*":
        return copy.deepcopy(row)
    out = {}
    for item in columns.split(","):
        item = item.strip()
        key = item.split(":", 1)[0] if ":" in item else item
        out[key] = copy.deepcopy(row.get(key))
    return out


class _PgErr(Exception):
    def __init__(self, code):
        super().__init__("pg probe")
        self.code = code


class _Client:
    def __init__(self, tables, raise_on=None):
        self.tables = copy.deepcopy(tables)
        self.raise_on = dict(raise_on or {})
        self.ops = []
        self.table_calls = 0

    def table(self, name):
        self.table_calls += 1
        return _Query(self, name)

    def _execute(self, q):
        self.ops.append({"table": q.table, "op": q.op, "payload": q.payload, "kwargs": q.kwargs,
                         "filters": [(n, list(a)) for n, a in q.filters], "orders": list(q.orders),
                         "columns": q.columns, "rng": q.rng, "lim": q.lim})
        if q.table in self.raise_on:
            raise self.raise_on[q.table]()
        if q.op != "select":
            return _Resp([])
        rows = [r for r in self.tables.get(q.table, [])
                if all(_match(r, n, a) for n, a in q.filters)]
        for col, desc in reversed(q.orders):
            rows.sort(key=lambda r, c=col: _cmp_key(r.get(c)), reverse=desc)
        if q.rng is not None:
            rows = rows[q.rng[0]: q.rng[1] + 1]
        if q.lim is not None:
            rows = rows[: q.lim]
        return _Resp([_project(r, q.columns) for r in rows])

    def selects(self, table=None):
        return [o for o in self.ops if o["op"] == "select" and (table is None or o["table"] == table)]

    def writes(self):
        return [o for o in self.ops if o["op"] != "select"]


class _Recorder:
    """A client that records every attribute touch and must never be used (OFF rows)."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        self.calls.append(name)
        raise AssertionError("the client was touched with the flag OFF: %s" % name)


class _LeafSpy:
    """Wraps the real leaf: records build_coverage_row calls, delegates everything else."""

    def __init__(self, leaf):
        self._leaf = leaf
        self.calls = []
        self.outputs = []

    def build_coverage_row(self, *args, **kwargs):
        self.calls.append((args, dict(kwargs)))
        row = self._leaf.build_coverage_row(*args, **kwargs)
        self.outputs.append(row)
        return row

    def __getattr__(self, name):
        return getattr(self._leaf, name)


# ---------------------------------------------------------------------------
# run helper
# ---------------------------------------------------------------------------

_RUN_SEQ = itertools.count(1)


class _Run:
    def __init__(self, rc, fake, report, records, report_path, md_path):
        self.rc, self.fake, self._report, self.records = rc, fake, report, records
        self.report_path, self.md_path = report_path, md_path

    @property
    def report(self):
        assert self._report is not None, "the run wrote no --report file"
        return self._report

    def messages(self, logger_name="cron_learning"):
        return [r.getMessage() for r in self.records if logger_name is None or r.name == logger_name]

    def metrics_from_log(self):
        out = {}
        for msg in self.messages():
            m = METRIC_LINE.match(msg)
            if m:
                out[m.group(1)] = (m.group(2), int(m.group(3)))
        return out

    def metrics(self):
        out = {}
        for item in self.report["metrics"]:
            assert isinstance(item, list) and len(item) == 3, "a metric entry is not [name, value, n]: %r" % (item,)
            out[item[0]] = (item[1], item[2])
        return out

    def cluster(self, bucket, category, source, field):
        found = [c for c in self.report["clusters"]
                 if (c["bucket"], c["category"], c["source"], c["field"]) == (bucket, category, source, field)]
        assert len(found) == 1, "cluster %r not found once: %r" % ((bucket, category, source, field),
                                                                   self.report["clusters"])
        return found[0]


def _run(monkeypatch, tmp_path, caplog, flag, world=None, argv=(), env=None, raise_on=None, md=False,
         report=True):
    mod = _mod()
    _set_flag(monkeypatch, flag)
    for name, value in (env or {}).items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    fake = _Client(world if world is not None else _world(), raise_on)
    seq = next(_RUN_SEQ)
    rpath = tmp_path / ("report-%d.json" % seq)
    mpath = tmp_path / ("report-%d.md" % seq)
    args = []
    if report:
        args += ["--report", str(rpath)]
    if md:
        args += ["--report-md", str(mpath)]
    args += list(argv)
    caplog.set_level(logging.DEBUG)
    start = len(caplog.records)
    rc = _call(mod, args, client=fake)
    records = list(caplog.records[start:])
    rep = json.loads(rpath.read_text(encoding="ascii")) if rpath.exists() else None
    return _Run(rc, fake, rep, records, rpath, mpath)


def _buckets(run):
    return {b: (run.report["buckets"][b]["cases"], run.report["buckets"][b]["actors"]) for b in BUCKETS}


DEFAULT_BUCKETS = {
    "identity_wrong": (0, 0),
    "price_wrong": (5, 3),
    "spec_missing": (2, 0),
    "spec_wrong": (7, 4),
    "verdict_unsupported": (2, 2),
    "verdict_wrong": (2, 2),
}

CLUSTER_A = ("price_wrong", "fragrances", "page_scrape", "price")
CLUSTER_B = ("spec_wrong", "fragrances", "specs", "specs")
CLUSTER_C = ("verdict_wrong", "electronics", "verdict", "verdict")
CLUSTER_KB = ("spec_wrong", "fragrances", "kb", "concentration")
CLUSTER_ANON = ("price_wrong", "unknown", "unknown", "price")


# ===========================================================================
# RED rows
# ===========================================================================

def test_r1_module_and_seams(monkeypatch):
    mod = _mod()
    for name in ("main", "run", "learning_mode", "window_days", "min_cases", "min_devices", "max_rows",
                 "exemplars_per_category"):
        assert callable(_attr(mod, name)), "%s is not callable" % name
    assert _attr(mod, "run") is _attr(mod, "main")
    for name, value in EXPECTED_CONSTANTS.items():
        assert _attr(mod, name) == value, "%s = %r, expected %r" % (name, getattr(mod, name), value)
    assert mod.learning_mode() == "off"
    assert (mod.window_days(), mod.min_cases(), mod.min_devices(), mod.max_rows(),
            mod.exemplars_per_category()) == (7, 3, 2, 5000, 5)
    monkeypatch.setenv(FLAG, " Apply ")
    assert mod.learning_mode() == "apply"
    monkeypatch.setenv(FLAG, "YES")
    assert mod.learning_mode() == "dry"


@pytest.mark.parametrize("value", OFF_VALUES, ids=lambda v: "unset" if v is None else repr(v))
def test_r2_off_is_one_line_and_nothing_else(monkeypatch, tmp_path, caplog, value):
    mod = _mod()
    common = _common()
    _full_config(monkeypatch)
    _set_flag(monkeypatch, value)
    admin_calls, leaf_calls = [], []

    def _raising_admin():
        admin_calls.append(1)
        raise AssertionError("probe: the client must not be built with the flag OFF")

    def _leaf_spy():
        leaf_calls.append(1)
        return _leaf()

    monkeypatch.setattr(common, "_admin_client", _raising_admin)
    monkeypatch.setattr(common, "kb_leaf", _leaf_spy)
    caplog.set_level(logging.DEBUG)
    rec = _Recorder()
    rpath = tmp_path / "off-report.json"
    mpath = tmp_path / "off-report.md"
    for argv, client in (
        (["--report", str(rpath), "--report-md", str(mpath)], rec),
        (["--bogus", "--day", "not-a-day"], None),
        (None, None),
        (["--report", str(rpath)], None),
    ):
        start = len(caplog.records)
        rc = _call(mod, argv, client=client)
        records = caplog.records[start:]
        assert rc == 0
        assert [r.getMessage() for r in records] == [OFF_LINE], [r.getMessage() for r in records]
        assert records[0].levelno == logging.INFO
    assert admin_calls == [], "_admin_client was called with the flag OFF"
    assert leaf_calls == [], "kb_leaf was called with the flag OFF"
    assert rec.calls == [], "the injected client was touched with the flag OFF"
    assert not rpath.exists() and not mpath.exists(), "a report file was created with the flag OFF"


@pytest.mark.parametrize("value", DRY_VALUES)
def test_r3_dry_reads_and_never_writes(monkeypatch, tmp_path, caplog, value):
    run = _run(monkeypatch, tmp_path, caplog, value, md=True)
    assert run.rc == 0
    assert run.report_path.exists(), "the DRY run wrote no report"
    assert set(run.report) == {
        "schema", "day", "mode", "window_days", "window_start", "window_end", "thresholds", "judge_state",
        "actor_basis", "tables", "buckets", "clusters", "proposals", "exemplar_candidates",
        "eval_candidates", "context", "dropped_deidentify", "metrics"}, sorted(run.report)
    assert run.report["schema"] == "learning-report/1"
    assert run.report["mode"] == "dry"
    assert run.report["judge_state"] == "pending"
    assert run.fake.ops, "the DRY run read nothing"
    assert all(o["op"] == "select" for o in run.fake.ops), [o for o in run.fake.ops if o["op"] != "select"]
    assert run.fake.writes() == []
    logged = run.metrics_from_log()
    for name in ALWAYS_METRICS:
        assert name in logged, "metric line %s missing in DRY" % name
    assert any(HEADER_LINE.match(m) and " mode=dry " in m for m in run.messages())


@pytest.mark.parametrize("value", APPLY_VALUES)
def test_r4_apply_one_upsert_through_the_builder(monkeypatch, tmp_path, caplog, value):
    common = _common()
    spy = _LeafSpy(_leaf())
    monkeypatch.setattr(common, "kb_leaf", lambda: spy)
    run = _run(monkeypatch, tmp_path, caplog, value)
    assert run.rc == 0
    writes = run.fake.writes()
    assert len(writes) == 1, writes
    w = writes[0]
    assert (w["table"], w["op"]) == (T_COVERAGE, "upsert")
    assert w["kwargs"] == {"on_conflict": "day,metric"}
    assert spy.calls, "build_coverage_row was never called"
    for args, kwargs in spy.calls:
        assert args == (), "build_coverage_row called with positional args"
        assert set(kwargs) == {"day", "metric", "value", "n"}
        assert type(kwargs["day"]) is date and kwargs["day"] == DAY
    assert w["payload"] == [r for r in spy.outputs if r is not None]
    assert all(r["day"] == "2026-11-04" for r in w["payload"])
    assert run.report["mode"] == "apply"


def test_r5_cli_dry_run_downgrades_apply(monkeypatch, tmp_path, caplog):
    run = _run(monkeypatch, tmp_path, caplog, "apply", argv=["--dry-run"])
    assert run.rc == 0
    assert run.fake.writes() == []
    headers = [m for m in run.messages() if HEADER_LINE.match(m)]
    assert len(headers) == 1 and " mode=dry " in headers[0], headers
    assert run.report["mode"] == "dry"


def test_r6_read_discipline(monkeypatch, tmp_path, caplog):
    run = _run(monkeypatch, tmp_path, caplog, "true")
    seen = {o["table"] for o in run.fake.selects()}
    assert seen == set(READ_TABLES), sorted(seen)
    for op in run.fake.selects():
        table = op["table"]
        assert op["columns"] == SELECTS[table], "%s select %r" % (table, op["columns"])
        assert op["orders"] == [("id", False)], "%s orders %r" % (table, op["orders"])
        if table in WINDOWED:
            col = WINDOWED[table]
            gte = [a for n, a in op["filters"] if n == "gte"]
            lt = [a for n, a in op["filters"] if n == "lt"]
            assert gte == [[col, WIN_START]], "%s gte %r" % (table, gte)
            assert lt == [[col, WIN_END]], "%s lt %r" % (table, lt)
            assert not [n for n, a in op["filters"] if n in ("gt", "lte")]
        if table == T_EVENTS:
            ins = [a for n, a in op["filters"] if n == "in_"]
            assert len(ins) == 1 and ins[0][0] == "event_type", ins
            assert sorted(ins[0][1]) == sorted(ABANDON_EVENTS + CONFIRM_EVENTS)
        lowered = op["columns"].lower()
        for banned in ("query", "change_suggestion", "mattered_most", "event_data", "error_message",
                       "products_found"):
            assert banned not in lowered, "%s selects %s" % (table, banned)
        items = [i.strip() for i in op["columns"].split(",")]
        assert "full_response" not in items and not any(i.endswith(":full_response") for i in items)
    cmp_ids = set()
    for op in run.fake.selects(T_COMPARISONS):
        ins = [a for n, a in op["filters"] if n == "in_"]
        assert len(ins) == 1 and ins[0][0] == "id", ins
        assert list(ins[0][1]) == sorted(set(ins[0][1])), "the comparison ids are not de-duplicated and sorted"
        cmp_ids.update(ins[0][1])
    assert cmp_ids == {_cid(n) for n in range(1, 9)}
    spec_ids = set()
    for op in run.fake.selects(T_SPECS):
        ins = [a for n, a in op["filters"] if n == "in_"]
        assert len(ins) == 1 and ins[0][0] == "product_id", ins
        spec_ids.update(ins[0][1])
    assert spec_ids == {P_A, P_B}


def _many_feedback(n):
    return {T_FEEDBACK: [{"id": "row-cf-%05d" % i, "user_id": None, "comparison_id": None, "useful": None,
                          "winner_correct": None, "price_correct": None, "specs_correct": None,
                          "created_at": T_IN} for i in range(n)]}


def test_r7_paging_and_cap(monkeypatch, tmp_path, caplog):
    run = _run(monkeypatch, tmp_path, caplog, "true", world=_many_feedback(1200))
    ranges = [o["rng"] for o in run.fake.selects(T_FEEDBACK)]
    assert ranges == [(0, 499), (500, 999), (1000, 1499)], ranges
    assert all(o["orders"] == [("id", False)] for o in run.fake.selects(T_FEEDBACK))
    assert run.report["tables"][T_FEEDBACK] == {"rows": 1200, "status": "ok", "error": None}
    assert "learning.capped." + T_FEEDBACK not in run.metrics()

    run = _run(monkeypatch, tmp_path, caplog, "apply", world=_many_feedback(1200),
               env={"LEARNING_MAX_ROWS": "700"})
    ranges = [o["rng"] for o in run.fake.selects(T_FEEDBACK)]
    assert ranges == [(0, 499), (500, 699)], ranges
    assert run.report["tables"][T_FEEDBACK] == {"rows": 700, "status": "capped", "error": None}
    value, n = run.metrics()["learning.capped." + T_FEEDBACK]
    assert float(value) == 700 and n == 700
    assert run.metrics_from_log()["learning.capped." + T_FEEDBACK] == ("700", 700)
    assert "table=%s status=capped rows=700" % T_FEEDBACK in " ".join(run.messages())

    run = _run(monkeypatch, tmp_path, caplog, "true", world=_many_feedback(1200),
               env={"LEARNING_MAX_ROWS": "50"})
    ranges = [o["rng"] for o in run.fake.selects(T_FEEDBACK)]
    assert ranges == [(0, 99)], ranges
    assert run.report["tables"][T_FEEDBACK]["rows"] == 100
    assert run.report["thresholds"]["max_rows"] == 100


def test_r8_bucket_counts(monkeypatch, tmp_path, caplog):
    run = _run(monkeypatch, tmp_path, caplog, "true")
    assert _buckets(run) == DEFAULT_BUCKETS, _buckets(run)
    assert run.report["buckets"]["identity_wrong"]["inputs"] == [T_KBFB]
    assert run.report["actor_basis"] == {
        "comparison_feedback": "user_id (proxy for device)",
        "verdict_critiques": "comparisons.user_id (proxy)",
        "kb_feedback": "device_key",
        "kb_gaps": "none",
    }
    metrics = run.metrics()
    for b, (cases, actors) in DEFAULT_BUCKETS.items():
        value, n = metrics["learning.cases." + b]
        assert (float(value), n) == (cases, actors), (b, value, n)
    value, n = metrics["learning.actors"]
    assert (float(value), n) == (8, 8)
    # R-G5-5: a kb_feedback identity + wrong row is identity_wrong (source kb, actor the device)
    world = _world()
    world[T_KBFB].append({"id": "row-kf-7", "compare_request_id": _rid(7), "product_id": P_D,
                          "field": "identity", "verdict": "wrong", "device_key": _dev("c"), "created_at": T_IN})
    run = _run(monkeypatch, tmp_path, caplog, "true", world=world)
    assert _buckets(run)["identity_wrong"] == (1, 1)
    assert run.cluster("identity_wrong", "fragrances", "kb", "identity")["cases"] == 1


def test_r9_clusters_and_systematic_rule(monkeypatch, tmp_path, caplog):
    run = _run(monkeypatch, tmp_path, caplog, "true")
    a, b, c = run.cluster(*CLUSTER_A), run.cluster(*CLUSTER_B), run.cluster(*CLUSTER_C)
    assert (a["cases"], a["actors"], bool(a["systematic"])) == (3, 2, True)
    assert (b["cases"], b["actors"], bool(b["systematic"])) == (3, 1, False)
    assert (c["cases"], c["actors"], bool(c["systematic"])) == (2, 2, False)
    anon = run.cluster(*CLUSTER_ANON)
    assert (anon["cases"], anon["actors"], bool(anon["systematic"])) == (1, 0, False)
    kb = run.cluster(*CLUSTER_KB)
    assert (kb["cases"], kb["actors"], bool(kb["systematic"])) == (3, 2, True)
    assert run.cluster("spec_missing", "fragrances", "kb_gap", "price")["demand"] == 4
    assert run.cluster("spec_missing", "fragrances", "kb_gap", "longevity")["demand"] == 2
    keys = [(x["bucket"], x["category"], x["source"], x["field"]) for x in run.report["clusters"]]
    assert keys == sorted(keys), keys
    assert len(keys) == 10, keys
    assert sum(1 for x in run.report["clusters"] if x["systematic"]) == 2
    metrics = run.metrics()
    assert float(metrics["learning.clusters.total"][0]) == 10
    assert float(metrics["learning.clusters.systematic"][0]) == 2


def test_r10_knobs_move_the_rule(monkeypatch, tmp_path, caplog):
    mod = _mod()
    run = _run(monkeypatch, tmp_path, caplog, "true", env={"LEARNING_MIN_CASES": "2"})
    assert bool(run.cluster(*CLUSTER_C)["systematic"]) is True
    assert run.report["thresholds"]["min_cases"] == 2
    run = _run(monkeypatch, tmp_path, caplog, "true", env={"LEARNING_MIN_CASES": None,
                                                            "LEARNING_MIN_DEVICES": "1"})
    assert bool(run.cluster(*CLUSTER_B)["systematic"]) is True
    for bad in ("0", "-1", "inf", "nan", "x", ""):
        monkeypatch.setenv("LEARNING_MIN_CASES", bad)
        assert mod.min_cases() == 3, bad
    run = _run(monkeypatch, tmp_path, caplog, "true", env={"LEARNING_MIN_CASES": "nan",
                                                            "LEARNING_MIN_DEVICES": None})
    assert run.report["thresholds"]["min_cases"] == 3
    assert bool(run.cluster(*CLUSTER_C)["systematic"]) is False
    run = _run(monkeypatch, tmp_path, caplog, "true", env={"LEARNING_MIN_CASES": None,
                                                            "LEARNING_MIN_DEVICES": "99"})
    assert run.report["thresholds"]["min_devices"] == 10
    assert bool(run.cluster(*CLUSTER_A)["systematic"]) is False
    run = _run(monkeypatch, tmp_path, caplog, "true", env={"LEARNING_MIN_DEVICES": None,
                                                            "LEARNING_WINDOW_DAYS": "1"})
    assert run.report["window_days"] == 1
    assert run.report["window_start"] == "2026-11-04T00:00:00+00:00"
    assert run.report["window_end"] == WIN_END
    assert run.report["buckets"]["price_wrong"]["cases"] < DEFAULT_BUCKETS["price_wrong"][0]
    run = _run(monkeypatch, tmp_path, caplog, "true", env={"LEARNING_WINDOW_DAYS": "31"})
    assert run.report["window_days"] == 30
    assert run.report["window_start"] == "2026-10-06T00:00:00+00:00"


def test_r11_window_and_day(monkeypatch, tmp_path, caplog):
    run = _run(monkeypatch, tmp_path, caplog, "true")
    assert run.report["day"] == "2026-11-04"
    assert (run.report["window_start"], run.report["window_end"]) == (WIN_START, WIN_END)
    run = _run(monkeypatch, tmp_path, caplog, "apply", argv=["--day", "2026-10-30"])
    assert run.report["day"] == "2026-10-30"
    assert (run.report["window_start"], run.report["window_end"]) == (
        "2026-10-24T00:00:00+00:00", "2026-10-31T00:00:00+00:00")
    gte = [a for o in run.fake.selects(T_FEEDBACK) for n, a in o["filters"] if n == "gte"]
    assert gte and all(a[1] == "2026-10-24T00:00:00+00:00" for a in gte)
    upserts = [o for o in run.fake.writes() if o["op"] == "upsert"]
    assert upserts and all(r["day"] == "2026-10-30" for r in upserts[0]["payload"])
    # a bad --day: one WARNING, exit 0, no client built or touched (full configuration present)
    common = _common()
    _full_config(monkeypatch)
    admin_calls = []

    def _raising_admin():
        admin_calls.append(1)
        raise AssertionError("probe: no client for a bad --day")

    monkeypatch.setattr(common, "_admin_client", _raising_admin)
    for client in (None, _Recorder()):
        monkeypatch.setenv(FLAG, "true")
        caplog.set_level(logging.DEBUG)
        start = len(caplog.records)
        rc = _call(_mod(), ["--day", "2026-13-01"], client=client)
        records = caplog.records[start:]
        assert rc == 0
        warnings = [r for r in records if r.levelno == logging.WARNING]
        assert [r.getMessage() for r in warnings] == ["[LEARNING] bad --day; skipping run"]
        if client is not None:
            assert client.calls == []
    assert admin_calls == []


def _estimated_world():
    world = _world()
    u3, u4 = _uid(3), _uid(4)
    for n, names in ((30, ("Quartz Oud EDP", "Rain Musk EDP")), (31, ("Sage Amber EDP", "Teak Smoke EDP")),
                     (32, ("Umber Rose EDP", "Vale Iris EDP"))):
        world[T_COMPARISONS].append(_cmp(n, u3, "fragrances", names, "estimated", "estimated"))
    world[T_FEEDBACK] += [_fb(130, u3, 30, price_correct="wrong"), _fb(131, u4, 31, price_correct="wrong"),
                          _fb(132, u3, 32, price_correct="wrong")]
    return world


PROPOSAL_KEYS = {"bucket", "category", "source", "field", "cases", "distinct_actors", "judge_state",
                 "grounding", "proposed_action"}


def test_r12_proposals(monkeypatch, tmp_path, caplog):
    run = _run(monkeypatch, tmp_path, caplog, "apply", world=_estimated_world())
    props = run.report["proposals"]
    systematic = [c for c in run.report["clusters"] if c["systematic"]]
    assert len(props) == len(systematic) == 3, props
    by_key = {}
    for p in props:
        assert set(p) == PROPOSAL_KEYS, sorted(p)
        assert p["judge_state"] == "pending"
        by_key[(p["bucket"], p["category"], p["source"], p["field"])] = p
    assert by_key[CLUSTER_A]["proposed_action"] == "recheck_source"
    assert by_key[CLUSTER_A]["grounding"] == []
    assert (by_key[CLUSTER_A]["cases"], by_key[CLUSTER_A]["distinct_actors"]) == (3, 2)
    est = by_key[("price_wrong", "fragrances", "estimated", "price")]
    assert est["proposed_action"] == "drop_source_for_field"
    kb = by_key[CLUSTER_KB]
    assert kb["proposed_action"] == "recheck_source"
    assert kb["grounding"] == [{"product_id": P_A, "field": "concentration", "source_url": URL_A}]
    for w in run.fake.writes():
        assert w["table"] == T_COVERAGE, "a write outside kb_coverage_daily: %r" % (w["table"],)
    # every systematic cluster gets the 2.5 action (min 1 case / 1 actor)
    run = _run(monkeypatch, tmp_path, caplog, "true",
               env={"LEARNING_MIN_CASES": "1", "LEARNING_MIN_DEVICES": "1"})
    actions = {(p["bucket"], p["category"], p["source"], p["field"]): p["proposed_action"]
               for p in run.report["proposals"]}
    assert actions == {
        ("price_wrong", "fragrances", "kb", "price"): "needs_operator",
        CLUSTER_A: "recheck_source",
        ("spec_wrong", "electronics", "specs", "specs"): "needs_operator",
        CLUSTER_KB: "recheck_source",
        CLUSTER_B: "needs_operator",
        ("verdict_unsupported", "fragrances", "critic", "verdict"): "no_action",
        CLUSTER_C: "no_action",
    }, actions
    assert all(p["judge_state"] == "pending" for p in run.report["proposals"])


def _exemplar_world():
    world = _world()
    u2 = _uid(2)
    extra = ((40, ("Willow Rose EDP", "Xeno Oud EDT")), (41, ("Yarrow Musk EDP", "Zinnia Amber EDP")),
             (42, ("Briar Leaf EDT", "Clove Spice EDT")), (43, ("Dahlia Bloom EDP", "Ember Wood EDP")))
    for i, (n, names) in enumerate(extra):
        world[T_COMPARISONS].append(_cmp(n, u2, "fragrances", names, "page_scrape", "page_scrape"))
        world[T_FEEDBACK].append(_fb(140 + i, u2, n, useful=True, winner_correct="correct"))
    return world


EXEMPLAR_KEYS = {"product_names", "winner_index", "winner_reason", "key_tradeoff", "value_context"}
VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.[a-z2-7]{16}$")


def test_r13_exemplar_candidates(monkeypatch, tmp_path, caplog):
    run = _run(monkeypatch, tmp_path, caplog, "true")
    ex = run.report["exemplar_candidates"]
    assert set(ex) == {"fragrances", "electronics"}, sorted(ex)
    assert ex["fragrances"]["count"] == 4 and len(ex["fragrances"]["exemplars"]) == 4
    assert ex["electronics"]["count"] == 1
    names = [tuple(e["product_names"]) for e in ex["fragrances"]["exemplars"]]
    assert names == sorted(names)
    assert ("Opal Bloom EDP", "Pine Smoke EDT") not in names  # the email-shaped candidate is dropped
    first = ex["fragrances"]["exemplars"][0]
    assert set(first) == EXEMPLAR_KEYS, sorted(first)
    assert first == {"product_names": ["Acme Rose EDP", "Birch Oud EDT"], "winner_index": 0,
                     "winner_reason": "Wins on value for daily wear.",
                     "key_tradeoff": "The runner-up projects further.",
                     "value_context": {"product_0": "Fair for the size.", "product_1": "Costs more per ml."}}
    for cat in ex:
        assert VERSION_RE.match(ex[cat]["version"]), ex[cat]["version"]
        assert ex[cat]["version"].startswith("2026-11-04.")
    version = ex["fragrances"]["version"]
    again = _run(monkeypatch, tmp_path, caplog, "true")
    assert again.report["exemplar_candidates"]["fragrances"]["version"] == version
    world = _world()
    world[T_COMPARISONS][0]["wr"] = "Wins on longevity for the price."
    changed = _run(monkeypatch, tmp_path, caplog, "true", world=world)
    assert changed.report["exemplar_candidates"]["fragrances"]["version"] != version
    # the per-category cap (8 clean fragrance candidates)
    for knob, expected in ((None, 5), ("1", 3), ("4", 4), ("9", 5)):
        run = _run(monkeypatch, tmp_path, caplog, "true", world=_exemplar_world(),
                   env={"LEARNING_EXEMPLARS_PER_CATEGORY": knob})
        got = run.report["exemplar_candidates"]["fragrances"]
        assert (got["count"], len(got["exemplars"])) == (expected, expected), (knob, got["count"])
        assert run.report["thresholds"]["exemplars_per_category"] == expected
    value, n = run.metrics()["learning.exemplar_candidates"]
    assert (float(value), n) == (6, 2)


def test_r14_report_log_and_rows_are_deidentified(monkeypatch, tmp_path, caplog):
    world = _world()
    token = "Lot" + _uuid(77, 9) + "z"  # a uuid inside a longer token (R-G5-13): dropped, never echoed
    world[T_COMPARISONS].append(_cmp(12, _uid(2), "fragrances", ("Aaa " + token, "Abb Musk EDP"),
                                     "page_scrape", "page_scrape"))
    world[T_FEEDBACK].append(_fb(160, _uid(2), 12, useful=True, winner_correct="correct", price_correct="correct"))
    # phone / digit-run shapes in fields that must never be read or echoed (built at run time)
    world[T_SEARCH][0]["query"] = "call " + PHONE_PREFIX + "3" * 8
    world[T_FEEDBACK][0]["change_suggestion"] = "ring " + PHONE_PREFIX + "4" * 8
    sentinels = _sentinels(world)
    dry = _run(monkeypatch, tmp_path, caplog, "true", world=world, md=True)
    app = _run(monkeypatch, tmp_path, caplog, "apply", world=world, md=True)
    texts = []
    for run in (dry, app):
        assert run.report_path.exists() and run.md_path.exists()
        texts.append(("report", run.report_path.read_text(encoding="ascii")))
        texts.append(("md", run.md_path.read_text(encoding="ascii")))
        texts += [("log", r.getMessage()) for r in run.records]
    upserts = [w for w in app.fake.writes() if w["op"] == "upsert"]
    assert upserts, "the APPLY run sent no upsert"
    texts += [("row", json.dumps(r, sort_keys=True)) for r in upserts[0]["payload"]]
    for where, text in texts:
        for s in sentinels:
            assert s not in text, "a sentinel reached the %s: %r" % (where, s)
        assert token not in text, "the uuid-carrying name reached the %s" % where
        for rx in (UUID_RE, HEX64_RE, EIGHT_DIGITS_RE):
            assert not rx.search(text), "%s matches %s: %r" % (where, rx.pattern, text[:200])
        assert AT_SIGN not in text, "an @ reached the %s" % where
        assert PHONE_PREFIX not in text, "a phone prefix reached the %s" % where
    assert dry.report["dropped_deidentify"] >= 1
    value, n = dry.metrics()["learning.dropped.deidentify"]
    assert float(value) >= 1 and n >= 1


def test_r15_eval_candidates(monkeypatch, tmp_path, caplog):
    run = _run(monkeypatch, tmp_path, caplog, "true")
    none_prices = {"product_0": None, "product_1": None}

    def _e(cat, names, wi, prices=None):
        return {"category": cat, "product_names": list(names), "confirmed_winner_index": wi,
                "confirmed_prices": prices if prices is not None else none_prices}

    expected = [
        _e("electronics", ("Ion Phone Pro", "Jet Phone Max"), 0),
        _e("fragrances", ("Acme Rose EDP", "Birch Oud EDT"), 0,
           {"product_0": {"amount": 12.5, "currency": "BHD"}, "product_1": {"amount": 20.0, "currency": "BHD"}}),
        _e("fragrances", ("Cedar Musk EDP", "Dune Amber EDP"), 1),
        _e("fragrances", ("Elm Vetiver EDT", "Fern Citrus EDT"), 0),
        _e("fragrances", ("Gale Iris EDP", "Haze Vanilla EDP"), 0),
        _e("fragrances", ("Opal Bloom EDP", "Pine Smoke EDT"), 0),
    ]
    got = run.report["eval_candidates"]
    assert got == expected, got
    amount = got[1]["confirmed_prices"]["product_0"]["amount"]
    assert isinstance(amount, float)
    value, n = run.metrics()["learning.eval_candidates"]
    assert float(value) == 6


def test_r16_absent_kb_tables_are_counted_skips(monkeypatch, tmp_path, caplog):
    run = _run(monkeypatch, tmp_path, caplog, "apply",
               raise_on={T_GAPS: lambda: _PgErr("PGRST205"), T_KBFB: lambda: _PgErr("PGRST205")})
    assert run.rc == 0
    for t in (T_GAPS, T_KBFB):
        assert run.report["tables"][t]["status"] == "absent", run.report["tables"][t]
        value, n = run.metrics()["learning.skipped." + t]
        assert (float(value), n) == (1, 0)
    assert run.report["buckets"]["spec_missing"]["cases"] == 0
    assert run.report["buckets"]["identity_wrong"]["cases"] == 0
    assert "learning.cases.price_wrong" in run.metrics()
    assert run.report["tables"][T_FEEDBACK]["status"] == "ok"
    warnings = [r.getMessage() for r in run.records if r.levelno == logging.WARNING]
    assert any("table=%s read failed (_PgErr)" % T_GAPS in m for m in warnings), warnings
    upserts = [w for w in run.fake.writes() if w["op"] == "upsert"]
    assert len(upserts) == 1


def test_r17_one_table_error_isolated(monkeypatch, tmp_path, caplog):
    detail = "probe-detail-" + "zq"
    run = _run(monkeypatch, tmp_path, caplog, "true", raise_on={T_EVENTS: lambda: RuntimeError(detail)})
    assert run.rc == 0
    warnings = [r.getMessage() for r in run.records if r.levelno == logging.WARNING]
    assert warnings == ["[LEARNING] table=%s read failed (RuntimeError)" % T_EVENTS], warnings
    for r in run.records:
        assert detail not in r.getMessage()
    assert run.report["tables"][T_EVENTS] == {"rows": 0, "status": "error", "error": "RuntimeError"}
    value, n = run.metrics()["learning.skipped." + T_EVENTS]
    assert (float(value), n) == (1, 0)
    assert _buckets(run) == DEFAULT_BUCKETS
    assert run.report["tables"][T_SEARCH]["status"] == "ok"


@pytest.mark.parametrize("mode", ["raises", "none"])
def test_r18_client_failure_exits_one(monkeypatch, tmp_path, caplog, mode):
    mod = _mod()
    common = _common()
    _full_config(monkeypatch)
    monkeypatch.setenv(FLAG, "true")

    def _admin():
        if mode == "raises":
            raise RuntimeError("probe-no-client")
        return None

    monkeypatch.setattr(common, "_admin_client", _admin)
    caplog.set_level(logging.DEBUG)
    start = len(caplog.records)
    rpath = tmp_path / "r18.json"
    rc = _call(mod, ["--report", str(rpath)])
    records = caplog.records[start:]
    assert rc == 1
    errors = [r.getMessage() for r in records if r.levelno >= logging.ERROR]
    assert len(errors) == 1, errors
    assert TEMPLATES[2].match(errors[0]), errors
    if mode == "raises":
        assert errors[0] == "[LEARNING] no service-role client (RuntimeError)"
    assert "probe-no-client" not in " ".join(r.getMessage() for r in records)
    assert not rpath.exists(), "a report was written without a client"
    assert not [r for r in records if METRIC_LINE.match(r.getMessage())]


def test_r19_unwritable_report_keeps_the_log(monkeypatch, tmp_path, caplog):
    mod = _mod()
    monkeypatch.setenv(FLAG, "true")
    caplog.set_level(logging.DEBUG)
    start = len(caplog.records)
    target = tmp_path / "a-directory"
    target.mkdir()
    rc = _call(mod, ["--report", str(target)], client=_Client(_world()))
    records = caplog.records[start:]
    assert rc == 0
    warnings = [r.getMessage() for r in records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and TEMPLATES[12].match(warnings[0]), warnings
    metrics = [r.getMessage() for r in records if METRIC_LINE.match(r.getMessage())]
    assert len(metrics) >= len(ALWAYS_METRICS)


def test_r20_metric_names_closed_and_valid(monkeypatch, tmp_path, caplog):
    leaf_regex = re.compile(_leaf().KB_METRIC_REGEX)
    closed = set(ALWAYS_METRICS) | set(CONDITIONAL_METRICS)
    assert len(ALWAYS_METRICS) == 16 and len(CONDITIONAL_METRICS) == 16
    runs = [
        _run(monkeypatch, tmp_path, caplog, "true"),
        _run(monkeypatch, tmp_path, caplog, "true",
             raise_on={T_GAPS: lambda: _PgErr("42P01"), T_EVENTS: lambda: RuntimeError("x")}),
        _run(monkeypatch, tmp_path, caplog, "true", world=_many_feedback(150),
             env={"LEARNING_MAX_ROWS": "100"}),
    ]
    seen = set()
    for run in runs:
        metrics = run.metrics()
        logged = run.metrics_from_log()
        assert set(metrics) == set(logged), (sorted(metrics), sorted(logged))
        for name, (value, n) in metrics.items():
            assert name in closed, "metric %s is outside the closed list" % name
            assert leaf_regex.match(name), name
            assert not name.startswith(("kb.", "proxy.", "host.")), name
            assert isinstance(value, (int, float)) and not isinstance(value, bool), (name, value)
            assert math.isfinite(value), (name, value)
            assert isinstance(n, int) and not isinstance(n, bool) and n >= 0, (name, n)
        for name in ALWAYS_METRICS:
            assert name in metrics, "always-emitted metric %s missing" % name
        seen.update(metrics)
    assert "learning.skipped." + T_GAPS in seen and "learning.skipped." + T_EVENTS in seen
    assert "learning.capped." + T_FEEDBACK in seen
    assert "learning.skipped." + T_FEEDBACK not in runs[0].metrics()


def test_r21_apply_is_idempotent_per_day(monkeypatch, tmp_path, caplog):
    one = _run(monkeypatch, tmp_path, caplog, "apply")
    two = _run(monkeypatch, tmp_path, caplog, "apply")
    u1 = [w for w in one.fake.writes() if w["op"] == "upsert"]
    u2 = [w for w in two.fake.writes() if w["op"] == "upsert"]
    assert len(u1) == len(u2) == 1
    assert u1[0]["payload"] == u2[0]["payload"]
    assert u1[0]["kwargs"] == u2[0]["kwargs"] == {"on_conflict": "day,metric"}
    metrics = {r["metric"] for r in u1[0]["payload"]}
    assert len(metrics) == len(u1[0]["payload"]), "a (day, metric) pair appears twice in one upsert"


FORBIDDEN_IMPORTS = ("app.services.openai_service", "anthropic", "openai", "httpx", "requests", "curl_cffi",
                     "aiohttp", "urllib.request", "app.services.serper_service", "app.services.llm_router")


def _imported_names(node):
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    if isinstance(node, ast.ImportFrom):
        base = node.module or ""
        return [base] + ["%s.%s" % (base, a.name) if base else a.name for a in node.names]
    return []


def test_r22_db_only_no_llm_no_network():
    _mod()
    text = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(text)
    stdlib = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module == "scripts":
                assert [a.name for a in node.names] == ["kb_seed_common"], ast.dump(node)
                continue
            for name in ([a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]):
                if name == "scripts.kb_seed_common":
                    continue
                assert name.split(".")[0] in stdlib, "module-level import %s is not stdlib" % name
    for node in ast.walk(tree):
        for name in _imported_names(node):
            for bad in FORBIDDEN_IMPORTS:
                assert not (name == bad or name.startswith(bad + ".")), "imports %s" % name
    assert "kb_service" not in text


def test_r23_never_writes_data_dir(monkeypatch, tmp_path, caplog):
    _mod()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    outputs = set()
    for flag in ("true", "apply"):
        run = _run(monkeypatch, cwd, caplog, flag, md=True)
        outputs.update({run.report_path.resolve(), run.md_path.resolve()})
    made = {p.resolve() for p in cwd.rglob("*") if p.is_file()}
    assert made == outputs, sorted(str(p) for p in made - outputs)
    text = SCRIPT.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert not re.search(r"""["']data[/\\]""", text), "a data/ path literal in the script"
    assert not re.search(r"""[/\\]data["'/\\]""", text), "a data/ path literal in the script"
    assert not re.search(r"""/\s*["']data["']""", text), "a data path segment join in the script"


def test_r24_railway_config():
    _mod()
    assert CONFIG.exists(), "railway.learning.json is missing"
    raw = CONFIG.read_bytes()
    assert all(b < 128 for b in raw), "railway.learning.json is not ASCII"
    assert b"\r" not in raw.replace(b"\r\n", b"\n")
    assert json.loads(raw.decode("ascii")) == {
        "$schema": "https://railway.com/railway.schema.json",
        "build": {"watchPatterns": ["scripts/cron_learning.py", "scripts/kb_seed_common.py",
                                    "railway.learning.json"]},
        "deploy": {"startCommand": "python -m scripts.cron_learning", "restartPolicyType": "NEVER"},
    }


def _banned_needles():
    return ("request_context", "device_key_pepper", "x-ai-consent-version", "x-compare-request-id",
            "header_state", "legacy_hash", "device_lookup_keys", "Qaren" + "Bot", "NAMED_" + "AGENT",
            AT_SIGN + "gmail.com", "cleanup_expired_" + "ratings")


def test_r25_script_hygiene():
    _mod()
    raw = SCRIPT.read_bytes()
    assert all(b < 128 for b in raw), "scripts/cron_learning.py is not ASCII"
    assert b"\r" not in raw.replace(b"\r\n", b"\n")
    text = raw.decode("ascii")
    for needle in _banned_needles():
        assert needle not in text, "scripts/cron_learning.py names %s" % needle


def test_r26_rotation_cron_retired():
    assert not ROTATION.exists(), "scripts/%s.py still exists (E2)" % ROTATION_NAME
    offenders = []
    for top in ("app", "scripts", "tests"):
        for path in sorted((ROOT / top).rglob("*.py")):
            if "__pycache__" in path.parts or path.resolve() == THIS:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                names = _imported_names(node)
                if isinstance(node, ast.ImportFrom):
                    names = names + [a.name for a in node.names]
                if any(ROTATION_NAME in n for n in names):
                    offenders.append("%s:%d" % (path.relative_to(ROOT).as_posix(), node.lineno))
    assert offenders == [], "the retired rotation cron is still imported: %s" % offenders


def _critique_world(bias, missing):
    world = {T_COMPARISONS: [_cmp(1, _uid(1), "fragrances", ("Acme Rose EDP", "Birch Oud EDT"),
                                  "page_scrape", "page_scrape")],
             T_CRITIQUES: [{"id": "row-vc-1", "comparison_id": _cid(1), "bias_score": bias,
                            "missing_citation_score": missing, "created_at": T_IN}]}
    return world


def test_r27_verdict_unsupported_threshold(monkeypatch, tmp_path, caplog):
    for bias, missing, cases in ((8, 6, 1), (6, 8, 1), (7, 7, 0), (None, None, 0), (None, 6, 1), (6, None, 1),
                                 (7, None, 0), (None, 7, 0)):
        run = _run(monkeypatch, tmp_path, caplog, "true", world=_critique_world(bias, missing))
        got = run.report["buckets"]["verdict_unsupported"]
        assert (got["cases"], got["actors"]) == (cases, cases), (bias, missing, got)
    run = _run(monkeypatch, tmp_path, caplog, "true")
    assert run.report["buckets"]["verdict_unsupported"]["cases"] == 2
    assert run.cluster("verdict_unsupported", "fragrances", "critic", "verdict")["actors"] == 2


def test_r28_context_metrics(monkeypatch, tmp_path, caplog):
    run = _run(monkeypatch, tmp_path, caplog, "true")
    assert run.report["context"] == {"events_abandon": 3, "events_confirm": 3, "searches_failed": 2,
                                     "searches_total": 4}
    metrics = run.metrics()
    assert (float(metrics["learning.events.abandon"][0]), metrics["learning.events.abandon"][1]) == (3, 2)
    assert (float(metrics["learning.events.confirm"][0]), metrics["learning.events.confirm"][1]) == (3, 1)
    assert (float(metrics["learning.searches.failed"][0]), metrics["learning.searches.failed"][1]) == (2, 4)


def test_r29_log_templates(monkeypatch, tmp_path, caplog):
    for flag, kwargs in (("true", {"md": True}), ("apply", {}),
                         ("true", {"raise_on": {T_KBFB: lambda: _PgErr("PGRST205")}})):
        run = _run(monkeypatch, tmp_path, caplog, flag, **kwargs)
        mine = [r for r in run.records if r.name == "cron_learning" and r.levelno >= logging.INFO]
        assert mine, "no cron_learning record"
        for r in mine:
            msg = r.getMessage()
            assert any(t.match(msg) for t in TEMPLATES), "a log line outside the 2.6 templates: %r" % msg
        assert TOTALS_LINE.match(mine[-1].getMessage()), mine[-1].getMessage()
        assert sum(1 for r in mine if TOTALS_LINE.match(r.getMessage())) == 1
        tables = [r.getMessage() for r in mine if TEMPLATES[4].match(r.getMessage())]
        assert len(tables) == len(READ_TABLES), tables
        assert HEADER_LINE.match(mine[0].getMessage()), mine[0].getMessage()


# ===========================================================================
# PIN rows (green at base)
# ===========================================================================

def _exemplars(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for cat, block in data.items():
        if cat.startswith("_") or not isinstance(block, dict):
            continue
        out[cat] = list(block.get("exemplars") or [])
    return out


def test_p1_no_user_derived_exemplar_under_data():
    canonical = _exemplars(ROOT / "data" / "verdict_exemplars.json")
    assert canonical and all(v == [] for v in canonical.values()), "canonical exemplars are not empty"
    parked = _exemplars(ROOT / "data" / "verdict_exemplars.s3_parked.json")
    total = 0
    for cat, items in list(canonical.items()) + list(parked.items()):
        for e in items:
            total += 1
            prov = e.get("_provenance") or {}
            assert prov.get("synthetic") is True, (cat, prov)
            assert not UUID_RE.search(str(prov.get("source_pattern_id", ""))), (cat, prov)
    assert total == 26, total


def test_p2_run_mode_contract(monkeypatch):
    common = _common()
    _full_config(monkeypatch)
    for value, expected in ([(v, "off") for v in OFF_VALUES] + [(v, "dry") for v in DRY_VALUES]
                            + [(v, "apply") for v in APPLY_VALUES]):
        _set_flag(monkeypatch, value)
        assert common.run_mode(FLAG) == expected, (value, expected)
    assert common.cli_mode("apply", True) == "dry" and common.cli_mode("off", True) == "off"
    ranges = {"LEARNING_WINDOW_DAYS": (7, 1, 30), "LEARNING_MIN_CASES": (3, 1, 100),
              "LEARNING_MIN_DEVICES": (2, 1, 10), "LEARNING_MAX_ROWS": (5000, 100, 50000),
              "LEARNING_EXEMPLARS_PER_CATEGORY": (5, 3, 5)}
    for name, (default, low, high) in ranges.items():
        for bad in ("", "x", "inf", "nan", "-1", "0"):
            monkeypatch.setenv(name, bad)
            assert common.int_knob(name, default, low, high) == default, (name, bad)
        monkeypatch.setenv(name, str(high * 10))
        assert common.int_knob(name, default, low, high) == high
        monkeypatch.setenv(name, " %d " % low)
        assert common.int_knob(name, default, low, high) == low
    monkeypatch.setenv("LEARNING_EXEMPLARS_PER_CATEGORY", "1")
    assert common.int_knob("LEARNING_EXEMPLARS_PER_CATEGORY", 5, 3, 5) == 3


def test_p3_builder_accepts_the_learning_names():
    leaf = _leaf()
    for name in ALWAYS_METRICS + ("learning.skipped." + T_FEEDBACK, "learning.capped." + T_FEEDBACK):
        for value in (0, 1.5):
            row = leaf.build_coverage_row(day=DAY, metric=name, value=value, n=0)
            assert row is not None, (name, value)
            assert row["day"] == "2026-11-04" and row["metric"] == name


def test_p4_no_railway_service_runs_rotation_or_learning_twice():
    configs = sorted(ROOT.glob("railway*.json"))
    assert configs, "no railway*.json found"
    learning = 0
    for path in configs:
        data = json.loads(path.read_text(encoding="utf-8"))
        command = str(((data.get("deploy") or {}).get("startCommand")) or "")
        assert ROTATION_NAME not in command, "%s runs the rotation cron" % path.name
        if "cron_learning" in command:
            learning += 1
    assert learning <= 1, learning


def _module_assign(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return node.value
    raise AssertionError("%s not assigned in %s" % (name, path))


def test_p5_critique_threshold_mirror():
    path = ROOT / "app" / "services" / "verdict_critique_service.py"
    assert ast.literal_eval(_module_assign(path, "CRITIQUE_THRESHOLD")) == 7
    axes = ast.literal_eval(_module_assign(path, "CRITIQUE_AXES"))
    assert "bias_score" in axes and "missing_citation_score" in axes


def test_p6_field_and_event_vocabularies():
    assert ast.literal_eval(_module_assign(ROOT / "app" / "services" / "kb_ingest.py", "D05_FIELDS")) == D05_FIELDS
    valid = ast.literal_eval(_module_assign(ROOT / "app" / "api" / "feedback_routes.py", "VALID_EVENT_TYPES"))
    for ev in ABANDON_EVENTS + CONFIRM_EVENTS:
        assert ev in valid, ev
    cols = _leaf().KB_COLUMNS
    for table, wanted in ((T_GAPS, GAP_COLUMNS), (T_KBFB, KB_FEEDBACK_COLUMNS), (T_SPECS, SPEC_COLUMNS + ",id")):
        for col in wanted.split(","):
            assert col in cols[table], (table, col)
    assert _leaf().KB_CATEGORY == "fragrances"


def _function(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError("%s not found in %s" % (name, path))


def _record_keys(fn):
    keys = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "record":
            sl = node.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                keys.add(sl.value)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "record" for t in node.targets):
            if isinstance(node.value, ast.Dict):
                keys.update(k.value for k in node.value.keys if isinstance(k, ast.Constant))
    return keys


def test_p7_feedback_writer_columns():
    fb = _record_keys(_function(ROOT / "app" / "services" / "feedback_service.py", "save_feedback"))
    for key in ("winner_correct", "price_correct", "specs_correct", "user_id", "comparison_id"):
        assert key in fb, key
    cmp_keys = _record_keys(_function(ROOT / "app" / "services" / "database_service.py", "save_comparison"))
    assert "full_response" in cmp_keys
    assert "category_used" not in cmp_keys
