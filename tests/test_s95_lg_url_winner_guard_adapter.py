"""S95-LG URL-WINNER-GUARD: the GL-3 scorer-input adapter rows (G7, G8).

GATE_S95_LG GL-3 / GL-4 (the RED measured limit L-1): the deterministic scorer
reads ``rating`` and ``review_count`` at the TOP level of a product, while
``normalize_product_data`` nests them under ``reviews`` (``rating`` / ``count``),
so a link pair was scored on price and specs only. Under ENABLE_URL_WINNER_GUARD
ON, ``compare_from_urls`` hands the scorer PER-PRODUCT SHALLOW COPIES of the link
products with the two keys lifted from ``reviews`` (only where the top-level key
is absent or None and the nested value is present); the delivered ``products``
list and its dicts stay unchanged (no new key).

- G7 (RED at base and at the RED prototype bytes): an equal-price, equal-spec pair
  that differs only in its nested buyer rating. The real scorer on the RAW
  products does not pick index 1 (a PRECONDITION: the row needs the lift) and on
  hand-lifted copies it picks 1 (a PRECONDITION on the fixture). ON, the model
  picks 0: the verdict call receives score_winner_index 1 and the delivered
  winner_index is 1.
- G8 (a PIN): ON, no delivered product dict holds a top-level ``rating`` or
  ``review_count`` key and each delivered product equals a deep copy taken before
  the call.

Hermetic, the RED file's patch idiom: ``extract_from_url`` on the
url_extraction_service module, ``_resolve_pair_category`` on
structured_comparison_service and ``generate_comparison`` on extraction_service
(the call-time local imports of ``compare_from_urls`` read them there); the
S81-10b fragrance decision is skipped with ``fragrance_gate=None``. The REAL
scorer and the REAL reconcile. Synthetic product names and synthetic hosts only;
every flag is set or deleted only through monkeypatch.
"""
import asyncio
import copy

import pytest

from app.services import extraction_service as es
from app.services import llm_router
from app.services import scoring_service as ss
from app.services import structured_comparison_service as scs
from app.services import url_extraction_service as ues

FLAG = "ENABLE_URL_WINNER_GUARD"
V2_FLAG = "ENABLE_URL_MODE_V2"
PROSE_FLAG = "ENABLE_WINNER_PROSE_RECONCILE"

ROLE_FLAG_NAMES = tuple(sorted(
    set(getattr(llm_router, "ROLE_FLAGS", {}).values())
    | {getattr(llm_router, "ESCALATION_FLAG", "ENABLE_SONNET_ESCALATION"),
       getattr(llm_router, "PRE_V3_FLAG", "ENABLE_OPENAI_PRE_V3")}
))

URL_0 = "https://shop-c.example/p/synth-c-test-scent-three"
URL_1 = "https://shop-d.example/p/synth-d-test-scent-four"
NAME_0 = "SynthC Test Scent Three"
NAME_1 = "SynthD Test Scent Four"
RETAILER = {"name": "synthstore", "currency": "BHD", "key": "generic"}
CATEGORY = "fragrances"
LIFTED_KEYS = ("rating", "review_count")

# Equal price and equal specs: the pair differs ONLY in its buyer rating, which
# normalize_product_data nests under ``reviews`` (3.1 / 500 vs 4.8 / 500).
SPECS = {
    "scent_family": "woody", "notes_top": "bergamot", "notes_heart": "rose",
    "notes_base": "vanilla", "longevity": "8 hours", "sillage": "moderate",
    "season": "all-season", "occasion": "evening",
}
RAW_0 = {
    "title": NAME_0, "brand": "SynthC", "name": "Test Scent Three",
    "price": 40.0, "currency": "BHD", "category": CATEGORY, "variant": "100ml",
    "specs": dict(SPECS), "rating": 3.1, "review_count": 500, "in_stock": True,
}
RAW_1 = {
    "title": NAME_1, "brand": "SynthD", "name": "Test Scent Four",
    "price": 40.0, "currency": "BHD", "category": CATEGORY, "variant": "100ml",
    "specs": dict(SPECS), "rating": 4.8, "review_count": 500, "in_stock": True,
}

# The model's verdict: it names product 0 as the winner.
VERDICT_PICKS_0 = {
    "winner_index": 0,
    "winner_declaration": NAME_0,
    "winner_reason": NAME_0 + " is the better pick at the same price.",
    "key_tradeoff": NAME_1 + " has the stronger buyer rating.",
    "specs_comparison": {
        "product_0_advantages": ["Same price"],
        "product_1_advantages": ["Higher buyer rating"],
        "similar": ["Eau de parfum"],
    },
}
ZERO_USAGE = {"prompt_tokens": 0, "completion_tokens": 0}


@pytest.fixture(autouse=True)
def _clean_flags(monkeypatch):
    for name in (FLAG, V2_FLAG, PROSE_FLAG) + ROLE_FLAG_NAMES:
        monkeypatch.delenv(name, raising=False)
    yield


def _written_back():
    """The two link products as compare_from_urls holds them before the verdict:
    the real normalize_product_data, then the category write-back."""
    products = [
        ues.normalize_product_data(copy.deepcopy(RAW_0), dict(RETAILER), URL_0),
        ues.normalize_product_data(copy.deepcopy(RAW_1), dict(RETAILER), URL_1),
    ]
    for product in products:
        product["category"] = CATEGORY
    return products


def _hand_lifted(products):
    """The test's own lift, independent of the unit's adapter: shallow copies with
    the top-level rating / review_count read from ``reviews``."""
    out = []
    for product in products:
        view = dict(product)
        view["rating"] = product["reviews"]["rating"]
        view["review_count"] = product["reviews"]["count"]
        out.append(view)
    return out


def _assert_preconditions():
    products = _written_back()
    for product in products:
        for key in LIFTED_KEYS:
            assert key not in product, (
                "PRECONDITION: normalize_product_data emitted a top-level %s" % key)
        assert product["reviews"]["count"] == 500, "PRECONDITION: the nested review count"
    raw = ss.ScoringService().compute_scores(copy.deepcopy(products))
    assert raw.get("winner_index") != 1, (
        "PRECONDITION: the real scorer on the RAW link products must NOT pick index 1 "
        "(got %r): the row must need the lift" % (raw.get("winner_index"),))
    lifted = ss.ScoringService().compute_scores(_hand_lifted(copy.deepcopy(products)))
    assert lifted.get("winner_index") == 1, (
        "PRECONDITION: the real scorer on hand-lifted copies must pick index 1 "
        "(got %r); re-pick the fixture" % (lifted.get("winner_index"),))


class _VerdictRecorder:
    """The generate_comparison double: records each call, returns (verdict, usage)."""

    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((copy.deepcopy(args), copy.deepcopy(kwargs)))
        return copy.deepcopy(self.verdict), dict(ZERO_USAGE)


def _install(monkeypatch, products):
    """Patch the three seams. The fake extraction hands out the given product dicts
    THEMSELVES, so an in-place write on them stays visible after the call."""
    by_url = {URL_0: products[0], URL_1: products[1]}

    async def _fake_extract(url, url_mode_v2=False):
        return {"success": True, "product": by_url[url]}

    async def _fake_resolve(*_args, **_kwargs):
        return CATEGORY, False, CATEGORY

    recorder = _VerdictRecorder(VERDICT_PICKS_0)
    monkeypatch.setattr(ues, "extract_from_url", _fake_extract)
    monkeypatch.setattr(scs, "_resolve_pair_category", _fake_resolve)
    monkeypatch.setattr(es, "generate_comparison", recorder)
    return recorder


def _run():
    return asyncio.run(ues.compare_from_urls(URL_0, URL_1, fragrance_gate=None))


def test_g7_on_the_scorer_reads_the_lifted_rating(monkeypatch):
    """G7 (GL-4, RED): ON; equal price and equal specs, the buyer rating nested
    under ``reviews`` (3.1 / 500 on product 0, 4.8 / 500 on product 1); the RAW
    products do not make the scorer pick index 1 (PRECONDITION) and the model
    picks 0 -> the verdict call receives score_winner_index 1 and the delivered
    winner_index is 1."""
    _assert_preconditions()
    monkeypatch.setenv(FLAG, "true")
    recorder = _install(monkeypatch, _written_back())
    out = _run()
    assert out.get("success") is True, sorted(out)
    assert len(recorder.calls) == 1, len(recorder.calls)
    _args, kwargs = recorder.calls[0]
    assert kwargs.get("score_winner_index") == 1, (
        "the verdict call's score_winner_index is %r, not the lifted scorer's 1"
        % (kwargs.get("score_winner_index"),))
    assert out.get("winner_index") == 1, (
        "the delivered winner_index is %r, not the lifted scorer's 1"
        % (out.get("winner_index"),))


def test_g8_on_the_delivered_products_stay_unlifted(monkeypatch):
    """G8 (GL-4, PIN): ON -> no delivered product dict holds a top-level ``rating``
    or ``review_count`` key, and each delivered product equals a deep copy taken
    before the call (the scorer's copies never leak into the delivered dicts)."""
    monkeypatch.setenv(FLAG, "true")
    products = _written_back()
    before = copy.deepcopy(products)
    _install(monkeypatch, products)
    out = _run()
    assert out.get("success") is True, sorted(out)
    delivered = out["products"]
    assert len(delivered) == 2, len(delivered)
    for index, product in enumerate(delivered):
        for key in LIFTED_KEYS:
            assert key not in product, (
                "delivered product %d holds a top-level %s" % (index, key))
        assert product == before[index], index
