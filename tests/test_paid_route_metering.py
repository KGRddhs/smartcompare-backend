"""W2-1 (SESSION 65) RED tests -- paid-route metering, the `/url/compare`
unpack, history + category.

Findings: MB-RECONCILE-01, MB-RECONCILE-07, MB-NETWORK-CONTRACT-14,
PO-VERDICT-TRUTH-01, LS-RATELIMIT-KEY-02 (= CR-SECURITY-06).
Flag: ``ENABLE_PAID_ROUTE_METERING`` (default OFF; OFF must be byte-identical).

Written BEFORE the implementation. Every red node fails on an ASSERTION about
behaviour measured through an EXISTING runtime path (a status code, a body key,
a call count recorded by a stub that is installed with ``raising=False`` so it
works both before and after the wiring exists) -- never on an ImportError or an
AttributeError for a symbol that does not exist yet.

--------------------------------------------------------------------------
WHAT IS WRONG TODAY (all four measured on this tree at 4c872968, see below)
--------------------------------------------------------------------------

(a) ``POST /api/v1/image/identify`` runs a paid GPT-4o Vision call AND a full
    comparison for an AUTHENTICATED user with NO tier check at all. The M13-03
    anon gate at ``image_routes.py:89`` is a different, default-OFF,
    fingerprint-keyed path that explicitly no-ops when ``user`` is truthy.
    Nothing on this route ever calls ``consume_comparison_credit``.

(b) ``POST/GET /api/v1/url/compare`` 500s on EVERY successful extraction:
    ``url_extraction_service.compare_from_urls`` at ``:583`` does NOT unpack the
    2-tuple that ``extraction_service.generate_comparison`` returns (`:2543`
    ``return parsed, usage`` / `:2547` the except-branch twin), and then calls
    ``.get()`` on it at ``:591``. VERIFIED EMPIRICALLY -- see
    ``.qa-w2/W2-1-UNPACK-EVIDENCE.md``. The route is also unmetered, drops
    history (no ``save_comparison_and_track_cohort(input_type='url')``) and
    drops the category chip (``_resolve_pair_category(products, None, ...)``
    is hardcoded ``None`` at ``:576``).

(c) ``GET /api/v1/text/prices/{product}`` is unauthenticated and uncounted, and
    its ``@limiter.limit("20/minute")`` is a NO-OP against any caller who varies
    the path parameter: ``Limiter`` in ``app/middleware/rate_limiter.py:125``
    never passes ``key_style``, and slowapi's default is ``"url"``
    (``slowapi/extension.py:147`` / ``:565``), so the limit scope is
    ``request["path"]`` -- the product string itself. MEASURED: 25 DISTINCT
    product strings produce ZERO 429s and 25 real ``get_regional_prices``
    resolutions; 25 requests for the SAME string produce 5.

(d) With the flag OFF every one of the above must stay exactly as it is today.

--------------------------------------------------------------------------
THE SIX NON-DELIVERY EXITS OF ``POST /api/v1/image/identify``
--------------------------------------------------------------------------

Enumerated by reading ``app/api/image_routes.py`` end to end. The gate belongs
AFTER image validation and BEFORE the Vision call (``:135``), mirroring
``text_routes.py:193``; the five 400s at ``:106 :108 :116 :118 :124`` are
therefore PRE-gate (nothing consumed, nothing to refund) and the anon 429 at
``:94`` cannot coexist with an authenticated user. That leaves exactly six
exits that must each refund the one credit the gate reserved:

  1. ``:138``  HTTPException 500 -- ``identify_products`` raised.
  2. ``:144``  200 ``action="error"`` -- vision returned ``{"error": ...}``.
  3. ``:176``  200 ``action="need_second_product"`` -- L4 moderation blocked.
  4. ``:201``  200 ``action="error"`` -- zero products identified.
  5. ``:211``  200 ``action="need_second_product"`` -- ONE product identified.
  6. ``:300``  200 ``action="comparison_failed"`` -- ``compare_from_text`` raised.

and exactly one DELIVERY exit, ``:276`` (200 ``action="comparison"``), which
must consume once and refund never.

The double-charge trap: exit 5 is the one a user hits routinely (one bottle in
frame), and exits 2/4 are the ordinary "bad photo" outcomes. A refund that is
missing there burns a free credit for no product; a refund that fires TWICE
(e.g. once inline and once again in a ``finally``) silently grants credits. The
``UsageLedger`` below records every call in a list, so a double refund is
detectable as ``len(refunds) == 2``, not merely as "a refund happened".

--------------------------------------------------------------------------
CONTRACT UNDER ``ENABLE_PAID_ROUTE_METERING`` (default OFF, read per call)
--------------------------------------------------------------------------

* ``/image/identify`` and ``/url/compare`` (POST + GET) mirror
  ``text_routes.text_compare``: ``consume_comparison_credit`` at the gate,
  429 with ``code == "USAGE_LIMIT"`` on refusal, ``refund_comparison_credit``
  on every non-delivery exit, exactly once.
* ``/url/compare`` additionally threads ``selected_category`` into
  ``_resolve_pair_category`` and fires
  ``save_comparison_and_track_cohort(input_type="url")`` on success.
* ``/text/prices/{product}`` gets a limit whose bucket does NOT vary with the
  path parameter, and stops serving a paid price resolution to an anonymous
  caller (see ``test_prices_anonymous_paid_search_is_not_free`` for why this
  node deliberately accepts either the admin-gate or the metering design).
* Flag OFF: status codes, body shapes and consume/refund counts are exactly
  today's. NOTE the deliberate exception: the ``compare_from_urls`` unpack is a
  pure defect fix (same class as M13-10 / M13-44) and is NOT gated, so the
  flag-OFF pins for that route pin the metering COUNTS, never its status code.

Every test uses a DISTINCT user id and a DISTINCT product string so no ledger,
counter or slowapi bucket is ever shared between nodes.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import image_routes, text_routes, url_routes
from app.api.auth_routes import get_optional_user
from app.main import app
from app.services import (
    content_safety_service,
    extraction_service,
    feedback_service,
    structured_comparison_service,
    url_extraction_service,
    usage_service,
)

FLAG = "ENABLE_PAID_ROUTE_METERING"

# Smallest byte string that image_routes._detect_mime_type calls a JPEG.
JPEG = b"\xff\xd8" + b"\x00" * 64

# The shape extraction_service.generate_comparison ACTUALLY returns
# (`:2543` return parsed, usage). Used wherever a test needs the happy path
# rather than the real function's offline except-branch.
REAL_GENERATE_COMPARISON_RETURN = (
    {
        "winner_index": 1,
        "recommendation": "The second one, for the price.",
        "key_differences": ["price", "size"],
    },
    {"prompt_tokens": 11, "completion_tokens": 22},
)


# ---------------------------------------------------------------------------
# ledger
# ---------------------------------------------------------------------------
class UsageLedger:
    """Counting stand-in for consume_/refund_comparison_credit.

    Both members are PLAIN functions that append to a list and then return an
    already-built coroutine. Recording at CALL time (not at await time) is
    deliberate: the production refund site is
    ``fire_and_forget(refund_comparison_credit(uid), label=...)``, which builds
    the coroutine synchronously and schedules it as a task that may never be
    scheduled before TestClient returns. Recording on call makes the count
    deterministic; recording on await would make this suite flaky.
    """

    def __init__(self, allowed: bool = True, reason: str | None = None,
                 tier: str = "free") -> None:
        self.consumes: list[str] = []
        self.refunds: list[str] = []
        self._allowed = allowed
        self._reason = reason
        self._tier = tier

    def consume(self, user_id, access_token="", *_a, **_kw):
        self.consumes.append(user_id)
        if self._allowed:
            payload = {
                "allowed": True,
                "reason": None,
                "tier": self._tier,
                "consumed": True,
                "consumed_keys": {"daily": f"usage:daily:{user_id}",
                                  "monthly": f"usage:monthly:{user_id}"},
                "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
            }
        else:
            payload = {
                "allowed": False,
                "reason": self._reason,
                "tier": self._tier,
                "consumed": False,
                "remaining": {"daily": 0, "monthly": 0, "lifetime_free": 0},
            }

        async def _result():
            return payload

        return _result()

    def refund(self, user_id, consumed_keys=None, *_a, **_kw):
        self.refunds.append(user_id)

        async def _result():
            return None

        return _result()


def _install_ledger(monkeypatch, ledger: UsageLedger, *modules) -> None:
    """Point every binding the implementation could plausibly use at the ledger.

    ``raising=False`` throughout: today ``image_routes`` / ``url_routes`` do not
    import these names at all, so the patch must be able to CREATE the
    attribute. After the wiring lands the module-level ``from ... import`` name
    is the binding that matters; the ``usage_service`` patch covers a
    ``usage_service.consume_comparison_credit(...)`` call style.
    """
    targets = (usage_service,) + modules
    for mod in targets:
        monkeypatch.setattr(mod, "consume_comparison_credit", ledger.consume,
                            raising=False)
        monkeypatch.setattr(mod, "refund_comparison_credit", ledger.refund,
                            raising=False)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def authed(request):
    """Override get_optional_user with a user id unique to the running node."""
    user = {
        "id": f"w2-1-{request.node.name}"[:120],
        "email": "w2-1@example.test",
        "access_token": "w2-1-token",
    }
    app.dependency_overrides[get_optional_user] = lambda: user
    try:
        yield user
    finally:
        app.dependency_overrides.pop(get_optional_user, None)


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    return True


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    return True


# ---------------------------------------------------------------------------
# camera harness
# ---------------------------------------------------------------------------
class _FakeSafety:
    def __init__(self, allowed: bool) -> None:
        self._allowed = allowed

    async def moderate_vision_output(self, _extracted):
        if self._allowed:
            return content_safety_service.SafetyResult(allowed=True)
        return content_safety_service.SafetyResult(
            allowed=False, reason="violence", blocklist_match="probe"
        )


def _stub_camera(monkeypatch, *, vision=None, vision_raises=False,
                 moderation_allowed=True, compare_raises=False,
                 history=None):
    """Stub every leaf of /image/identify. Returns nothing; the caller drives
    which exit is taken via the keyword arguments."""

    async def _identify(_images):
        if vision_raises:
            raise RuntimeError("w2-1 probe: vision unavailable")
        return vision

    monkeypatch.setattr(image_routes, "identify_products", _identify)
    monkeypatch.setattr(
        content_safety_service, "get_content_safety_service",
        lambda: _FakeSafety(moderation_allowed),
    )

    async def _blocked(**_kw):
        return None

    from app.services import audit_service
    monkeypatch.setattr(audit_service, "log_content_blocked",
                        lambda **_kw: _blocked())

    class _Service:
        async def compare_from_text(self, *_a, **_kw):
            if compare_raises:
                raise RuntimeError("w2-1 probe: comparison unavailable")
            return {
                "success": True,
                "products": [{"brand": "A", "name": "one"},
                             {"brand": "B", "name": "two"}],
                "metadata": {"total_cost": 0.01},
            }

    monkeypatch.setattr(image_routes, "StructuredComparisonService", _Service)

    def _log_search(**_kw):
        async def _r():
            return None
        return _r()

    monkeypatch.setattr(image_routes, "log_search", _log_search)

    def _save(**kw):
        if history is not None:
            history.append(kw.get("input_type"))

        async def _r():
            return None
        return _r()

    monkeypatch.setattr(image_routes, "save_comparison_and_track_cohort", _save)


def _vision(n: int):
    return {
        "products": [{"brand": f"B{i}", "name": f"N{i}"} for i in range(n)],
        "cost": 0.003,
    }


def _post_identify(client, n_images: int = 2):
    files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(n_images)]
    return client.post("/api/v1/image/identify", files=files)


# ---------------------------------------------------------------------------
# url/compare harness
# ---------------------------------------------------------------------------
def _stub_url_leaves(monkeypatch, *, extract_ok=True, category_spy=None,
                     real_generate=False, history=None):
    async def _extract(url):
        if not extract_ok:
            return {"success": False, "error": "w2-1 probe: extraction refused"}
        tag = url.rsplit("/", 1)[-1]
        return {
            "success": True,
            "product": {
                "brand": "Probe",
                "name": tag,
                "category": "electronics",
                "search_query": f"Probe {tag}",
                "price": {"amount": 1.0, "currency": "BHD"},
            },
        }

    monkeypatch.setattr(url_extraction_service, "extract_from_url", _extract)

    async def _allow(_url):
        return True

    monkeypatch.setattr(url_routes, "_validate_url_offloop_or_sync", _allow)

    if category_spy is not None:
        async def _resolve(products, selected_category, parser_path=False):
            category_spy.append(selected_category)
            return "electronics", False, None

        monkeypatch.setattr(structured_comparison_service,
                            "_resolve_pair_category", _resolve)

    if real_generate:
        # Drive the REAL generate_comparison offline: get_client raises, so the
        # `:2545` except rung returns its genuine 2-tuple at `:2547`.
        def _boom():
            raise RuntimeError("w2-1 probe: no OpenAI client offline")

        monkeypatch.setattr(extraction_service, "get_client", _boom)
    else:
        async def _generate(*_a, **_kw):
            return REAL_GENERATE_COMPARISON_RETURN

        monkeypatch.setattr(extraction_service, "generate_comparison", _generate)

    def _save(**kw):
        if history is not None:
            history.append(kw.get("input_type"))

        async def _r():
            return None
        return _r()

    monkeypatch.setattr(feedback_service, "save_comparison_and_track_cohort",
                        _save, raising=False)
    monkeypatch.setattr(url_routes, "save_comparison_and_track_cohort",
                        _save, raising=False)


def _post_compare(client, body=None):
    payload = {"url1": "https://example.test/alpha",
               "url2": "https://example.test/beta"}
    if body:
        payload.update(body)
    return client.post("/api/v1/url/compare", json=payload)


# ===========================================================================
# (a) CAMERA -- POST /api/v1/image/identify
# ===========================================================================
def test_camera_at_lifetime_cap_returns_429_usage_limit(
    monkeypatch, client, authed, flag_on
):
    """RED: an authenticated user who is OUT of credits still gets a paid Vision
    call and a full comparison. Flag ON must refuse with the same envelope
    text_routes.py:195-203 uses, having consumed exactly once at the gate."""
    ledger = UsageLedger(allowed=False, reason="daily_limit")
    _install_ledger(monkeypatch, ledger, image_routes)
    _stub_camera(monkeypatch, vision=_vision(2))

    resp = _post_identify(client)

    assert resp.status_code == 429, (
        "flag ON: /image/identify must refuse a capped authenticated user with "
        f"429 USAGE_LIMIT, got {resp.status_code} body={resp.text[:200]}"
    )
    detail = resp.json().get("detail", {})
    assert detail.get("code") == "USAGE_LIMIT", (
        f"429 envelope must mirror text_routes, got {detail!r}"
    )
    assert ledger.consumes == [authed["id"]], (
        f"expected exactly one consume at the gate, got {ledger.consumes!r}"
    )
    assert ledger.refunds == [], (
        f"a refused gate consumed nothing, so it must refund nothing, "
        f"got {ledger.refunds!r}"
    )


CAMERA_NON_DELIVERY_EXITS = [
    # id,                    kwargs for _stub_camera,                 status
    ("vision_raised_500", dict(vision_raises=True), 500),
    ("vision_parse_error", dict(vision={"error": "bad json", "cost": 0.003}), 200),
    ("moderation_blocked", dict(vision=_vision(2), moderation_allowed=False), 200),
    ("zero_products", dict(vision=_vision(0)), 200),
    ("one_product", dict(vision=_vision(1)), 200),
    ("comparison_raised", dict(vision=_vision(2), compare_raises=True), 200),
]


@pytest.mark.parametrize(
    "exit_id,stub_kwargs,expected_status",
    CAMERA_NON_DELIVERY_EXITS,
    ids=[row[0] for row in CAMERA_NON_DELIVERY_EXITS],
)
def test_camera_non_delivery_exit_consumes_once_and_refunds_once(
    monkeypatch, client, authed, flag_on, exit_id, stub_kwargs, expected_status
):
    """RED: each of the six non-delivery exits mapped in the module docstring
    must reserve exactly ONE credit at the gate and give exactly ONE back.

    ``refunds`` is a list, so a second refund on the same request shows up as
    length 2 -- the double-charge trap is detected, not merely 'a refund
    happened'. The status assertion pins that adding the gate does not move the
    exit's existing wire surface."""
    ledger = UsageLedger()
    _install_ledger(monkeypatch, ledger, image_routes)
    _stub_camera(monkeypatch, **stub_kwargs)

    resp = _post_identify(client)

    assert resp.status_code == expected_status, (
        f"exit {exit_id}: status must stay {expected_status}, "
        f"got {resp.status_code} body={resp.text[:200]}"
    )
    assert ledger.consumes == [authed["id"]], (
        f"exit {exit_id}: expected exactly one consume at the gate, "
        f"got {ledger.consumes!r}"
    )
    assert ledger.refunds == [authed["id"]], (
        f"exit {exit_id}: expected exactly one refund on this non-delivery "
        f"exit, got {ledger.refunds!r}"
    )


def test_camera_success_consumes_once_and_never_refunds(
    monkeypatch, client, authed, flag_on
):
    """RED: the delivery exit (image_routes.py:276) is the one path that keeps
    the credit. One consume, zero refunds, and the body is unchanged."""
    ledger = UsageLedger()
    _install_ledger(monkeypatch, ledger, image_routes)
    _stub_camera(monkeypatch, vision=_vision(2))

    resp = _post_identify(client)

    assert resp.status_code == 200, resp.text[:200]
    assert resp.json().get("action") == "comparison", resp.text[:200]
    assert ledger.consumes == [authed["id"]], (
        f"expected exactly one consume at the gate, got {ledger.consumes!r}"
    )
    assert ledger.refunds == [], (
        f"a delivered comparison must never refund, got {ledger.refunds!r}"
    )


# ===========================================================================
# (b) URL COMPARE -- POST/GET /api/v1/url/compare
# ===========================================================================
def test_url_compare_post_returns_success_on_extracted_pair(
    monkeypatch, client, flag_off
):
    """RED (the unpack, MB-RECONCILE-01): with both leaves resolving, the route
    500s because compare_from_urls (:583) never unpacks generate_comparison's
    2-tuple and then calls .get() on it at :591.

    This node drives the REAL generate_comparison -- only ``get_client`` is
    stubbed, so the genuine `:2547` return path executes -- and it runs with the
    metering flag OFF on purpose: the unpack is an UNFLAGGED defect fix, so a
    flag-OFF deployment must serve a real comparison too."""
    _stub_url_leaves(monkeypatch, real_generate=True)

    resp = _post_compare(client)

    assert resp.status_code == 200, (
        "POST /url/compare must deliver a comparison when both URLs extract; "
        f"got {resp.status_code} body={resp.text[:200]}"
    )
    body = resp.json()
    assert body.get("success") is True, f"body={body!r}"
    assert isinstance(body.get("comparison"), dict), (
        "`comparison` must be the parsed verdict dict, not the (parsed, usage) "
        f"tuple; got {type(body.get('comparison')).__name__}"
    )
    assert "winner_index" in body, f"body keys={sorted(body)!r}"


def test_url_compare_get_returns_success_on_extracted_pair(
    monkeypatch, client, flag_off
):
    """RED: same defect on the GET twin (url_routes.py:184)."""
    _stub_url_leaves(monkeypatch, real_generate=True)

    resp = client.get(
        "/api/v1/url/compare",
        params={"url1": "https://example.test/alpha",
                "url2": "https://example.test/beta"},
    )

    assert resp.status_code == 200, (
        "GET /url/compare must deliver a comparison when both URLs extract; "
        f"got {resp.status_code} body={resp.text[:200]}"
    )
    assert resp.json().get("success") is True, resp.text[:200]


def test_url_compare_at_cap_returns_429_usage_limit(
    monkeypatch, client, authed, flag_on
):
    """RED: /url/compare has NO user dependency at all today, so an
    out-of-credits user gets two paid extractions plus a verdict call for
    free. Flag ON must gate it exactly like text_routes."""
    ledger = UsageLedger(allowed=False, reason="monthly_limit")
    _install_ledger(monkeypatch, ledger, url_routes)
    _stub_url_leaves(monkeypatch)

    resp = _post_compare(client)

    # Consume first: today the route has no gate AT ALL, so it falls through
    # into the unpack 500 and a status-first assertion would report the wrong
    # defect. This ordering makes the red reason name the missing gate.
    assert ledger.consumes == [authed["id"]], (
        "flag ON: /url/compare must consume exactly one credit at the gate, "
        f"got {ledger.consumes!r}"
    )
    assert resp.status_code == 429, (
        "flag ON: /url/compare must refuse a capped user with 429 USAGE_LIMIT; "
        f"got {resp.status_code} body={resp.text[:200]}"
    )
    assert resp.json().get("detail", {}).get("code") == "USAGE_LIMIT", resp.text[:200]
    assert ledger.refunds == [], (
        f"a refused gate must not refund, got {ledger.refunds!r}"
    )


def test_url_compare_failure_exit_refunds_once(
    monkeypatch, client, authed, flag_on
):
    """RED: when extraction cannot produce two products the route raises 400
    (url_routes.py:164). The credit reserved at the gate must come back exactly
    once -- never zero (a failed compare burns a free credit) and never twice
    (silent credit grant)."""
    ledger = UsageLedger()
    _install_ledger(monkeypatch, ledger, url_routes)
    _stub_url_leaves(monkeypatch, extract_ok=False)

    resp = _post_compare(client)

    assert resp.status_code == 400, resp.text[:200]
    assert ledger.consumes == [authed["id"]], (
        f"expected exactly one consume at the gate, got {ledger.consumes!r}"
    )
    assert ledger.refunds == [authed["id"]], (
        f"expected exactly one refund on the <2-products exit, "
        f"got {ledger.refunds!r}"
    )


def test_url_compare_threads_selected_category(monkeypatch, client, flag_on):
    """RED (MB-RECONCILE-07): url_extraction_service.py:576 hardcodes the chip
    to ``None``, so a URL comparison can never honour a user category. The spy
    records what _resolve_pair_category was actually handed."""
    seen: list = []
    _stub_url_leaves(monkeypatch, category_spy=seen)

    _post_compare(client, {"selected_category": "fragrances"})

    assert seen, "_resolve_pair_category was never reached"
    assert seen[0] == "fragrances", (
        "the selected_category chip must reach _resolve_pair_category; it is "
        f"hardcoded None at url_extraction_service.py:576 -- saw {seen[0]!r}"
    )


def test_url_compare_saves_history_with_input_type_url(
    monkeypatch, client, authed, flag_on
):
    """RED (MB-NETWORK-CONTRACT-14): a successful URL comparison writes no
    history row, so it never appears in the History tab. Mirror the text path:
    fire-and-forget save_comparison_and_track_cohort(input_type='url').

    Note this node is red for TWO reasons today -- the call is not wired, and
    the success path is unreachable anyway because of the unpack 500."""
    history: list = []
    ledger = UsageLedger()
    _install_ledger(monkeypatch, ledger, url_routes)
    _stub_url_leaves(monkeypatch, history=history)

    resp = _post_compare(client)

    assert history == ["url"], (
        "expected exactly one save_comparison_and_track_cohort(input_type='url') "
        f"on the success path, got {history!r} "
        f"(route returned {resp.status_code})"
    )
    assert resp.status_code == 200, (
        f"the history write must ride a delivered comparison; "
        f"got {resp.status_code} body={resp.text[:200]}"
    )


# ===========================================================================
# (c) GET /api/v1/text/prices/{product}
# ===========================================================================
def _stub_prices(monkeypatch, calls=None):
    async def _prices(brand, name, variant, search_query):
        if calls is not None:
            calls.append(search_query)
        return {"prices": {"bahrain": {"amount": 1.0, "currency": "BHD"}},
                "cheapest_region": "bahrain"}

    monkeypatch.setattr(text_routes, "get_regional_prices", _prices)


def test_prices_distinct_products_share_one_rate_limit_bucket(
    monkeypatch, client, flag_on
):
    """RED (LS-RATELIMIT-KEY-02 = CR-SECURITY-06): the 20/minute decorator on
    text_routes.py:760 buckets on ``request["path"]`` because
    ``Limiter(...)`` at rate_limiter.py:125 leaves slowapi's ``key_style``
    at its ``"url"`` default. Varying the path parameter therefore buys an
    unlimited number of free price resolutions from one IP.

    MEASURED at 4c872968: 25 distinct strings -> 0 x 429 and 25 backend calls;
    25 requests for the SAME string -> 5 x 429. The fix is a route-keyed limit
    (an explicit ``scope=``, or ``key_style="endpoint"``)."""
    calls: list = []
    _stub_prices(monkeypatch, calls)

    statuses = [
        client.get(f"/api/v1/text/prices/w2-1-distinct-{i}").status_code
        for i in range(25)
    ]

    assert 429 in statuses, (
        "25 DISTINCT product strings must still hit the route's rate limit; "
        f"got statuses={statuses!r} and {len(calls)} paid price resolutions"
    )


def test_prices_anonymous_paid_search_is_not_free(monkeypatch, client, flag_on):
    """RED: an anonymous caller gets a full, paid, uncounted price resolution.

    DESIGN-AGNOSTIC ON PURPOSE. There are ZERO callers of this endpoint in
    SmartCompareApp/ (grep for 'text/prices' / '/prices' finds only the
    docstring, CLAUDE.md's Serper-rotation liveness probe and
    tests/test_rate_limiting_complete.py), and its sibling measurement route
    GET /text/price-kpi is ALREADY ``Depends(verify_admin_key)``. The
    recommended close is therefore the admin gate (401/403); the metering
    design (optional-user + consume -> 429 USAGE_LIMIT) is the alternative.
    This node accepts EITHER and only refuses the status quo, so it stays green
    whichever the implementer picks."""
    _stub_prices(monkeypatch)

    resp = client.get("/api/v1/text/prices/w2-1-anon-probe")

    assert resp.status_code in (401, 403, 429), (
        "flag ON: an anonymous caller must not receive a free paid price "
        "resolution -- expected 401/403 (admin gate) or 429 (metered); "
        f"got {resp.status_code} body={resp.text[:200]}"
    )


# ===========================================================================
# (d) FLAG-OFF PINS -- green today AND after the implementation
# ===========================================================================
def test_flag_off_camera_success_is_unmetered_and_unchanged(
    monkeypatch, client, authed, flag_off
):
    """PIN: with the flag unset the camera route neither consumes nor refunds,
    and its delivery body is exactly today's."""
    ledger = UsageLedger()
    _install_ledger(monkeypatch, ledger, image_routes)
    _stub_camera(monkeypatch, vision=_vision(2))

    resp = _post_identify(client)

    assert resp.status_code == 200, resp.text[:200]
    body = resp.json()
    assert body.get("action") == "comparison"
    assert body.get("success") is True
    assert body["metadata"]["input_method"] == "camera"
    assert ledger.consumes == [] and ledger.refunds == [], (
        f"flag OFF must be byte-identical: consumes={ledger.consumes!r} "
        f"refunds={ledger.refunds!r}"
    )


def test_flag_off_camera_one_product_exit_is_unmetered_and_unchanged(
    monkeypatch, client, authed, flag_off
):
    """PIN: the routine one-bottle-in-frame exit (image_routes.py:211)."""
    ledger = UsageLedger()
    _install_ledger(monkeypatch, ledger, image_routes)
    _stub_camera(monkeypatch, vision=_vision(1))

    resp = _post_identify(client)

    assert resp.status_code == 200, resp.text[:200]
    body = resp.json()
    assert body.get("action") == "need_second_product"
    assert body.get("success") is True
    assert len(body.get("products", [])) == 1
    assert ledger.consumes == [] and ledger.refunds == [], (
        f"flag OFF must be byte-identical: consumes={ledger.consumes!r} "
        f"refunds={ledger.refunds!r}"
    )


def test_flag_off_camera_at_cap_still_delivers_comparison(
    monkeypatch, client, authed, flag_off
):
    """PIN: flag OFF must not consult the gate at all -- a ledger that would
    REFUSE is never asked, and the comparison is delivered exactly as today."""
    ledger = UsageLedger(allowed=False, reason="daily_limit")
    _install_ledger(monkeypatch, ledger, image_routes)
    _stub_camera(monkeypatch, vision=_vision(2))

    resp = _post_identify(client)

    assert resp.status_code == 200, resp.text[:200]
    assert resp.json().get("action") == "comparison"
    assert ledger.consumes == [], (
        f"flag OFF must never reach the gate, got {ledger.consumes!r}"
    )


def test_flag_off_url_compare_is_unmetered(monkeypatch, client, authed, flag_off):
    """PIN: flag OFF, /url/compare consumes nothing, refunds nothing and writes
    no history row.

    Its STATUS is deliberately NOT pinned here: the compare_from_urls unpack is
    an UNFLAGGED defect fix, so this route legitimately moves 500 -> 200 with
    the flag OFF. That transition is pinned by
    test_url_compare_post_returns_success_on_extracted_pair instead."""
    history: list = []
    ledger = UsageLedger()
    _install_ledger(monkeypatch, ledger, url_routes)
    _stub_url_leaves(monkeypatch, history=history)

    _post_compare(client)

    assert ledger.consumes == [] and ledger.refunds == [], (
        f"flag OFF must not meter /url/compare: consumes={ledger.consumes!r} "
        f"refunds={ledger.refunds!r}"
    )
    assert history == [], (
        f"flag OFF must not write a history row, got {history!r}"
    )


def test_flag_off_prices_anonymous_200_and_unmetered(monkeypatch, client, flag_off):
    """PIN: flag OFF, the prices endpoint keeps serving anonymous callers with
    today's body shape and no metering."""
    ledger = UsageLedger()
    _install_ledger(monkeypatch, ledger, text_routes)
    _stub_prices(monkeypatch)

    resp = client.get("/api/v1/text/prices/w2-1-flagoff-probe")

    assert resp.status_code == 200, resp.text[:200]
    body = resp.json()
    assert body["product"] == "w2-1-flagoff-probe"
    assert set(body) >= {"product", "variant", "search_query", "prices",
                         "cheapest_region"}
    assert ledger.consumes == [] and ledger.refunds == [], (
        f"flag OFF must not meter /text/prices: consumes={ledger.consumes!r} "
        f"refunds={ledger.refunds!r}"
    )
