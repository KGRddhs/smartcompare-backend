"""Bundle C § 1a — diagnostic logging hook for empty pros/cons.

Per design § 1a + plan A.2.1: when generate_comparison() returns a verdict
where product_0_pros and/or product_1_pros are empty, the raw GPT response
content must be logged so post-deploy probes can identify which suspect is
firing (verdict JSON dropping keys / model omitting / validate_verdict
stripping).

The hook is gated on DEBUG_STAGE_TIMINGS=true per the project measure-
before-optimize rule + CLAUDE.md env-var note (zero prod overhead with
flag off; cached at process init).
"""
import logging
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services import extraction_service


@pytest.mark.asyncio
async def test_logs_raw_response_when_product_0_pros_empty(caplog, monkeypatch):
    """When product_0_pros is empty, raw GPT response must be logged
    under the PROS_CONS_DIAGNOSTIC marker (flag ON)."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    # Reset the cached flag so the new env value is picked up.
    monkeypatch.setattr(extraction_service, "_PROS_CONS_DIAG_FLAG", None, raising=False)

    fake_content = (
        '{"winner_index": 0, "winner_declaration": "iPhone wins", '
        '"product_0_pros": [], "product_1_pros": ["Cheaper price"], '
        '"product_0_cons": ["Pricier"], "product_1_cons": []}'
    )
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = fake_content
    mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=80, completion_tokens=20)

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        with caplog.at_level(logging.WARNING, logger="app.services.extraction_service"):
            await extraction_service.generate_comparison(
                product1={"name": "iPhone 16", "brand": "Apple"},
                product2={"name": "Galaxy S25", "brand": "Samsung"},
                region="bahrain",
            )

    assert "PROS_CONS_DIAGNOSTIC" in caplog.text, (
        "Expected PROS_CONS_DIAGNOSTIC log marker when pros/cons empty"
    )
    # Raw response content must appear (truncated) so root cause can be diagnosed
    assert "product_0_pros" in caplog.text


@pytest.mark.asyncio
async def test_logs_raw_response_when_product_1_pros_empty(caplog, monkeypatch):
    """Mirror case: empty product_1_pros also fires the diagnostic."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    monkeypatch.setattr(extraction_service, "_PROS_CONS_DIAG_FLAG", None, raising=False)

    fake_content = (
        '{"winner_index": 0, "winner_declaration": "X", '
        '"product_0_pros": ["Better camera"], "product_1_pros": [], '
        '"product_0_cons": [], "product_1_cons": ["Slower chip"]}'
    )
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = fake_content
    mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=80, completion_tokens=20)

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        with caplog.at_level(logging.WARNING, logger="app.services.extraction_service"):
            await extraction_service.generate_comparison(
                product1={"name": "A", "brand": "X"},
                product2={"name": "B", "brand": "Y"},
                region="bahrain",
            )

    assert "PROS_CONS_DIAGNOSTIC" in caplog.text


@pytest.mark.asyncio
async def test_no_log_when_both_pros_populated(caplog, monkeypatch):
    """Happy path: both pros lists non-empty → no diagnostic noise."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    monkeypatch.setattr(extraction_service, "_PROS_CONS_DIAG_FLAG", None, raising=False)

    fake_content = (
        '{"winner_index": 0, "winner_declaration": "X", '
        '"product_0_pros": ["Better camera", "Longer battery"], '
        '"product_1_pros": ["Cheaper price"], '
        '"product_0_cons": ["Pricier"], "product_1_cons": ["Slower chip"]}'
    )
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = fake_content
    mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=80, completion_tokens=20)

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        with caplog.at_level(logging.WARNING, logger="app.services.extraction_service"):
            await extraction_service.generate_comparison(
                product1={"name": "A", "brand": "X"},
                product2={"name": "B", "brand": "Y"},
                region="bahrain",
            )

    assert "PROS_CONS_DIAGNOSTIC" not in caplog.text


@pytest.mark.asyncio
async def test_diagnostic_silent_when_flag_off(caplog, monkeypatch):
    """Per A.10.1 + measure-before-optimize: diagnostic MUST be flag-gated.
    With DEBUG_STAGE_TIMINGS off, no diagnostic log even when pros empty."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "false")
    monkeypatch.setattr(extraction_service, "_PROS_CONS_DIAG_FLAG", None, raising=False)

    fake_content = (
        '{"winner_index": 0, "winner_declaration": "X", '
        '"product_0_pros": [], "product_1_pros": [], '
        '"product_0_cons": [], "product_1_cons": []}'
    )
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = fake_content
    mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=80, completion_tokens=20)

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        with caplog.at_level(logging.WARNING, logger="app.services.extraction_service"):
            await extraction_service.generate_comparison(
                product1={"name": "A", "brand": "X"},
                product2={"name": "B", "brand": "Y"},
                region="bahrain",
            )

    assert "PROS_CONS_DIAGNOSTIC" not in caplog.text
