"""Session 69 U1 (audit finding PRD-BP-02): the OpenAI client initialisation
must never write any part of OPENAI_API_KEY to the logs.

Before this unit ``extraction_service.get_client`` logged the key's last ten
characters at INFO ("...key ending in: ...<suffix>"), which lands in Railway's
log stream and in any transcript that quotes it. The log line may say whether a
key is configured; it may not carry any substring of the key.
"""
import logging
from contextlib import suppress

import pytest

# Deliberately NOT shaped like a real key (the pre-commit credential scan
# rejects sk-... strings): the test only needs a long unique value.
SENTINEL_KEY = "QAREN-TEST-SENTINEL-S69-HYGIENE-0123456789-abcdefghijklmnopqrstuvwxyz"


def _substrings(value: str, n: int = 6):
    return {value[i:i + n] for i in range(len(value) - n + 1)}


@pytest.fixture
def fresh_extraction_client(monkeypatch):
    from app.services import extraction_service as es
    monkeypatch.setenv("OPENAI_API_KEY", SENTINEL_KEY)
    monkeypatch.setattr(es, "_client", None)
    yield es
    monkeypatch.setattr(es, "_client", None)


def test_get_client_log_carries_no_key_material(fresh_extraction_client, caplog):
    es = fresh_extraction_client
    with caplog.at_level(logging.DEBUG):
        es.get_client()
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert text, "the client construction must still log one line"
    assert SENTINEL_KEY[-10:] not in text, "the key suffix reached the log"
    leaked = [s for s in _substrings(SENTINEL_KEY) if s in text]
    assert not leaked, f"key material reached the log: {leaked[:3]}"


def test_get_client_log_states_presence_only(fresh_extraction_client, caplog):
    es = fresh_extraction_client
    with caplog.at_level(logging.INFO):
        es.get_client()
    msgs = [r.getMessage() for r in caplog.records if "OpenAI client" in r.getMessage()]
    assert msgs, "no OpenAI client initialisation line was logged"
    assert any("configured" in m for m in msgs), msgs


def test_get_client_log_names_missing_key(monkeypatch, caplog):
    from app.services import extraction_service as es
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(es, "_client", None)
    with caplog.at_level(logging.INFO), suppress(Exception):
        # openai 3.x raises OpenAIError("Missing credentials") from the
        # constructor when no key is set — unchanged behaviour; the log line
        # is written before the constructor runs.
        es.get_client()
    monkeypatch.setattr(es, "_client", None)
    msgs = [r.getMessage() for r in caplog.records if "OpenAI client" in r.getMessage()]
    assert msgs and any("missing" in m for m in msgs), msgs
