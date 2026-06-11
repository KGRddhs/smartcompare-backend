"""Bundle C § 1a A.3.1 — pros/cons fix via response_format=json_object.

Per qa-bundle-c D.1.3 follow-up (`docs/investigations/2026-05-17-
bundle-c-cold-cache-evidence.md`): all 6 cold-cache probes returned
`comparison.product_{0,1}_{pros,cons}` as None (keys ABSENT from the
parsed JSON). Suspects 3 + 4 ruled out by code inspection. Suspect 1
(model dropping keys under JSON schema pressure) most likely.

Smallest-blast fix per qa-bundle-c spec: add
`response_format={"type": "json_object"}` to the verdict
`chat.completions.create` calls. Forces OpenAI's structured-output
guarantee that the response is valid JSON honoring all declared keys.

NO speculative re-prompt fallback per spec § 1a — that path doubles
GPT cost for unconfirmed root cause. If response_format alone proves
insufficient (verified by Ahmed's post-deploy probe), the next escalation
is hard-pinning verdict to gpt-4o via model_router priority='critical'.
"""
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services import extraction_service


def _mock_chat_response(content: str = '{"winner_index": 0}'):
    """Build a fake openai SDK response object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = MagicMock(total_tokens=100, prompt_tokens=80, completion_tokens=20)
    return resp


@pytest.mark.asyncio
async def test_verdict_call_passes_response_format_json_object():
    """A.3.1: every verdict chat.completions.create call MUST include
    `response_format={"type": "json_object"}` so the model is contractually
    bound to emit complete JSON (preventing key-drop under prompt pressure)."""
    fake = _mock_chat_response(
        '{"winner_index": 0, "winner_declaration": "X", '
        '"product_0_pros": ["a"], "product_1_pros": ["b"], '
        '"product_0_cons": ["c"], "product_1_cons": ["d"]}'
    )
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake)

    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        await extraction_service.generate_comparison(
            product1={"name": "A", "brand": "X"},
            product2={"name": "B", "brand": "Y"},
            region="bahrain",
        )

    # Inspect every chat.completions.create call — all must pass
    # response_format={"type": "json_object"}.
    assert mock_client.chat.completions.create.called
    for call in mock_client.chat.completions.create.call_args_list:
        kwargs = call.kwargs
        assert "response_format" in kwargs, (
            "verdict call missing response_format — A.3.1 fix not applied"
        )
        assert kwargs["response_format"] == {"type": "json_object"}, (
            f"unexpected response_format value: {kwargs['response_format']!r}"
        )


@pytest.mark.asyncio
async def test_verdict_call_still_records_usage():
    """Regression guard: response_format addition must NOT break the
    existing model_router.record_usage telemetry."""
    fake = _mock_chat_response('{"winner_index": 0, "product_0_pros": ["x"]}')
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake)

    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        with patch(
            "app.services.model_router_service.model_router.record_usage",
            new_callable=AsyncMock,
        ) as mock_record:
            await extraction_service.generate_comparison(
                product1={"name": "A", "brand": "X"},
                product2={"name": "B", "brand": "Y"},
                region="bahrain",
            )

    # Usage must still be recorded (with the verdict model + token count)
    assert mock_record.called


@pytest.mark.asyncio
async def test_429_fallback_path_also_passes_response_format():
    """The 429-fallback path at line 1145 (re-call with gpt-4o-mini)
    must ALSO pass response_format — otherwise the fallback would
    revert to the broken behavior."""
    # First call raises 429; fallback succeeds with valid JSON.
    fake_fallback = _mock_chat_response('{"winner_index": 0, "product_0_pros": ["x"]}')
    mock_client = AsyncMock()

    call_count = {"n": 0}

    async def _create(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("429 rate limit exceeded")
        return fake_fallback

    mock_client.chat.completions.create = AsyncMock(side_effect=_create)

    # Force the 4o-priority path so the 429 → mini fallback triggers
    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        with patch(
            "app.services.model_router_service.model_router.get_model",
            new_callable=AsyncMock,
            return_value="gpt-4o",
        ):
            await extraction_service.generate_comparison(
                product1={"name": "A", "brand": "X"},
                product2={"name": "B", "brand": "Y"},
                region="bahrain",
            )

    assert call_count["n"] == 2, "expected primary call + fallback call"
    # Both calls must pass response_format
    for call in mock_client.chat.completions.create.call_args_list:
        kwargs = call.kwargs
        assert kwargs.get("response_format") == {"type": "json_object"}, (
            f"call {call} missing response_format — fallback regressed"
        )


# ---------------------------------------------------------------------------
# S2 (Decision D) — VERDICT call temperature=0
# ---------------------------------------------------------------------------
# I4 A/B evidence (docs/plans/2026-06-12-s2-shadow-results.md, temp0 arm)
# proved temperature=0 on the verdict call recovers the entire variance bucket
# of winner failures (18/18 on bias45) at zero cost/latency. This pins it to 0
# on BOTH the primary verdict call and the 429→mini fallback — VERDICT ONLY.


@pytest.mark.asyncio
async def test_verdict_call_temperature_zero():
    """Decision D: the primary verdict chat.completions.create call MUST use
    temperature=0 (deterministic verdict — kills the winner-variance bucket)."""
    fake = _mock_chat_response('{"winner_index": 0, "product_0_pros": ["x"]}')
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake)

    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        await extraction_service.generate_comparison(
            product1={"name": "A", "brand": "X"},
            product2={"name": "B", "brand": "Y"},
            region="bahrain",
        )

    assert mock_client.chat.completions.create.called
    for call in mock_client.chat.completions.create.call_args_list:
        assert call.kwargs.get("temperature") == 0, (
            f"verdict call temperature must be 0, got {call.kwargs.get('temperature')!r}"
        )


@pytest.mark.asyncio
async def test_429_fallback_verdict_temperature_zero():
    """The 429→gpt-4o-mini fallback verdict call must ALSO be temperature=0."""
    fake_fallback = _mock_chat_response('{"winner_index": 0, "product_0_pros": ["x"]}')
    mock_client = AsyncMock()
    call_count = {"n": 0}

    async def _create(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("429 rate limit exceeded")
        return fake_fallback

    mock_client.chat.completions.create = AsyncMock(side_effect=_create)
    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        with patch(
            "app.services.model_router_service.model_router.get_model",
            new_callable=AsyncMock,
            return_value="gpt-4o",
        ):
            await extraction_service.generate_comparison(
                product1={"name": "A", "brand": "X"},
                product2={"name": "B", "brand": "Y"},
                region="bahrain",
            )

    assert call_count["n"] == 2
    for call in mock_client.chat.completions.create.call_args_list:
        assert call.kwargs.get("temperature") == 0, (
            f"fallback verdict call temperature must be 0, got {call.kwargs.get('temperature')!r}"
        )


# ---------------------------------------------------------------------------
# S2 I2.5 (F5) — review_source_quotes is a DELIBERATE, LABELED verdict input
# ---------------------------------------------------------------------------


def _user_msg_of(mock_client):
    """Return the verdict user message from the (first) create call."""
    call = mock_client.chat.completions.create.call_args_list[0]
    for m in call.kwargs["messages"]:
        if m["role"] == "user":
            return m["content"]
    raise AssertionError("no user message in verdict call")


@pytest.mark.asyncio
async def test_review_source_quotes_present_when_consult_ran():
    """When the consult populated product.reviews.review_source_quotes (flag
    ON), the verdict user message carries a LABELED editorial-quotes block —
    not just buried in the json.dumps(product) blob."""
    fake = _mock_chat_response('{"winner_index": 0, "product_0_pros": ["x"]}')
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake)

    p1 = {"name": "A", "brand": "X", "reviews": {
        "review_source_quotes": [
            {"domain": "sayidaty.net", "text": "Held up beautifully through a humid Gulf afternoon."}
        ]
    }}
    p2 = {"name": "B", "brand": "Y"}

    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        await extraction_service.generate_comparison(product1=p1, product2=p2, region="bahrain")

    user_msg = _user_msg_of(mock_client)
    assert "Regional editorial review notes" in user_msg   # the deliberate label
    assert "sayidaty.net" in user_msg
    assert "humid Gulf afternoon" in user_msg


@pytest.mark.asyncio
async def test_review_source_quotes_absent_when_consult_off():
    """Flag OFF / consult missed (no review_source_quotes) → NO labeled block;
    the prompt is byte-identical to the no-consult path (zero change)."""
    fake = _mock_chat_response('{"winner_index": 0, "product_0_pros": ["x"]}')
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake)

    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        await extraction_service.generate_comparison(
            product1={"name": "A", "brand": "X"},
            product2={"name": "B", "brand": "Y"},
            region="bahrain",
        )

    user_msg = _user_msg_of(mock_client)
    assert "Regional editorial review notes" not in user_msg
