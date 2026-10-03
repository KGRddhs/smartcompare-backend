"""Session 70 OAI_OBS item 3 -- empty-message Sentry issues.

Sentry (org qaren-rr, project python-fastapi, read 2026-09-30) holds
PYTHON-FASTAPI-N ``"Search error: "`` (11 events) and PYTHON-FASTAPI-14
``"Serper shopping call error (gl=us): "`` (4 events) with an EMPTY tail: the
sites log ``logger.error(f"...{e}")`` and ``str(e)`` is ``''`` for an httpx
transport timeout / connect error (measured on the pinned httpx 0.28.1 /
httpcore 1.0.9) and for a no-arg ``TimeoutError()``.

Requirements pinned here (OAI_OBS_SPEC.md R3.1-R3.4 + review corrections C1,
C3 + orchestrator rulings OQ3, OR6, OR9):
  R3.1 a leaf ``app/services/log_scrub.py`` owns the R-W18 scrubber as
       ``safe_exc``; ``structured_comparison_service._safe_exc`` IS that
       function (the retro pins in tests/test_retro_w1_8.py stay green).
  R3.2 ``exc_summary(exc)`` = the exception TYPE plus the scrubbed text
       (sentry key shapes, URL userinfo/query/fragment, one line, <= 200 chars,
       scrubbed BEFORE the cut), never raising.
  R3.3 / C1 / OQ3 the EIGHT CHANGE sites (five serper + extract_specs +
       extract_price + extract_price_from_training_data) log a CONSTANT
       %-template with the old prefix and ``exc_summary(e)`` as the argument;
       every return value stays byte-identical (``"error": str(e)`` included).
  R3.4 ``record.msg`` is the template and holds no exception text.
  OR6  the three LLM sites are driven by mocking ``guarded_llm_create`` (the
       SDK is never constructed into a real call).
  OR9  no ``exc_info`` and no stack on the eight records.

BASE = 4bd5a09f (OR14; app/ and tests/ are byte-identical to 94c097cd).
RED at BASE: the exc_summary / safe_exc / leaf tests (the module is absent) and
test_site_logs_name_the_type + test_site_log_scrubs_exception_text for all
eight sites (the message is the bare prefix / the raw text).
PIN (green at BASE): test_site_return_value_unchanged (C3: split out so it
executes at base), test_site_log_carries_no_exc_info (OR9) and
test_safe_exc_outputs_unchanged.

C3: nothing this unit creates is imported at module top; ``log_scrub`` /
``exc_summary`` / ``safe_exc`` are imported inside the test bodies.
This file is ASCII-only: the two Unicode line separators the R-W18 regex
handles are built with chr().
"""
import ast
import asyncio
import logging
import pathlib
import re
from unittest.mock import MagicMock

import httpx
import pytest

import app.services.extraction_service as es
import app.services.serper_service as ss
import app.services.structured_comparison_service as scs

_REPO = pathlib.Path(__file__).resolve().parents[1]
_ZERO_USAGE = {"prompt_tokens": 0, "completion_tokens": 0}
_LS = chr(0x2028)  # LINE SEPARATOR
_PS = chr(0x2029)  # PARAGRAPH SEPARATOR


class _BrokenStr(Exception):
    def __str__(self):  # noqa: D401
        raise RuntimeError("broken __str__")


class _NonStrStr(Exception):
    def __str__(self):
        return 42  # type: ignore[return-value]  -- str() raises TypeError


# ===========================================================================
# R3.2 -- exc_summary
# ===========================================================================

def test_exc_summary_shapes():
    """RED at base (app.services.log_scrub is absent)."""
    from app.services.log_scrub import exc_summary

    # empty text -> the type name alone (the Sentry bug)
    assert exc_summary(httpx.ReadTimeout("")) == "ReadTimeout"
    assert exc_summary(httpx.ConnectTimeout("")) == "ConnectTimeout"
    assert exc_summary(TimeoutError()) == "TimeoutError"
    assert exc_summary(asyncio.TimeoutError()) == "TimeoutError"
    assert exc_summary(asyncio.CancelledError()) == "CancelledError"
    # whitespace-only text counts as empty
    assert exc_summary(ValueError("   ")) == "ValueError"
    assert exc_summary(ValueError("\n")) == "ValueError"
    # non-empty text -> "Type: text"
    assert exc_summary(ValueError("bad")) == "ValueError: bad"
    # OR6: the SDK's own typed errors are non-empty
    req = httpx.Request("POST", "https://api.openai.test/v1/chat/completions")
    import openai
    assert exc_summary(openai.APITimeoutError(request=req)) == "APITimeoutError: Request timed out."
    # line breaks collapse to one line
    assert exc_summary(ValueError("a\nb")) == "ValueError: a b"
    assert "\n" not in exc_summary(ValueError("a\r\n\r\nb"))
    assert "\r" not in exc_summary(ValueError("a\r\n\r\nb"))
    assert exc_summary(ValueError("a" + _LS + "b" + _PS + "c")) == "ValueError: a b c"
    # truncation: at most 200 characters of text after "Name: "
    long_out = exc_summary(ValueError("x" * 5000))
    assert long_out.startswith("ValueError: ")
    assert 0 < len(long_out) - len("ValueError: ") <= 200, len(long_out)
    # a broken __str__ never raises
    assert exc_summary(_BrokenStr()) == "<unprintable _BrokenStr>"
    assert exc_summary(_NonStrStr()) == "<unprintable _NonStrStr>"


def test_exc_summary_strips_credentials_and_query():
    """RED at base (module absent). The summary never carries URL userinfo, a
    query string, a fragment or a sentry-scrubbed key shape."""
    from app.services.log_scrub import exc_summary

    out = exc_summary(RuntimeError("x https://user:hunter2@h.test/p?q=SECRET#frag y"))
    assert "hunter2" not in out and "SECRET" not in out and "frag" not in out, out
    assert out == "RuntimeError: x https://h.test/p y", out

    assert exc_summary(RuntimeError("Bearer abc.def.ghi")) == "RuntimeError: Bearer [REDACTED]"

    hex40 = "0123456789abcdef0123456789abcdef01234567"
    assert len(hex40) == 40
    out = exc_summary(RuntimeError(f"token {hex40} end"))
    assert hex40 not in out and "[TOKEN_REDACTED]" in out, out

    # a real raise_for_status message over a credentialed URL (multi-line)
    req = httpx.Request("POST", "https://google.serper.test/search?apiKey=SECRETKEY&q=x")
    resp = httpx.Response(429, request=req)
    with pytest.raises(httpx.HTTPStatusError) as ei:
        resp.raise_for_status()
    out = exc_summary(ei.value)
    assert out.startswith("HTTPStatusError: Client error '429"), out
    assert "SECRETKEY" not in out and "apiKey" not in out, out
    assert "\n" not in out


def test_exc_summary_scrubs_before_truncating():
    """RED at base (module absent). R3.2 order: scrub the FULL text, then cut,
    so a truncation can never land inside a credential."""
    from app.services.log_scrub import exc_summary

    hex40 = "abcdefabcdefabcdefabcdefabcdefabcdefabcd"
    out = exc_summary(RuntimeError("y" * 180 + " " + hex40))
    assert "[TOKEN_REDACTED]" in out, out
    assert "abcdefabcd" not in out, "a cut before the scrub leaked a token prefix"

    out = exc_summary(RuntimeError("y" * 185 + " https://user:pw12345678@h.test/p"))
    assert "pw1234" not in out and "user:" not in out, out


# ===========================================================================
# R3.1 -- the leaf module and the safe_exc re-export
# ===========================================================================

def test_safe_exc_reexport_is_identical():
    """RED at base (module absent): scs._safe_exc IS log_scrub.safe_exc, so the
    four scs call sites and ``scs._safe_exc`` in tests resolve unchanged."""
    import app.services.log_scrub as log_scrub

    assert scs._safe_exc is log_scrub.safe_exc


def test_log_scrub_is_a_cycle_free_leaf():
    """RED at base (file absent). R3.1: the leaf's only imports are ``re`` and
    ``from app.services.sentry_service import _scrub_string`` (sentry_service is
    stdlib-only at its top), so serper_service and extraction_service can import
    it at module top without the scs <-> extraction_service/serper_service
    cycle. A ``from __future__`` compiler directive is tolerated; nothing else."""
    path = _REPO / "app" / "services" / "log_scrub.py"
    assert path.is_file(), "app/services/log_scrub.py does not exist"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    sentry_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            if node.module == "app.services.sentry_service":
                sentry_names.update(alias.name for alias in node.names)
    assert imported <= {"re", "app.services.sentry_service", "__future__"}, imported
    assert "re" in imported
    assert "app.services.sentry_service" in imported
    assert sentry_names == {"_scrub_string"}, sentry_names


def test_change_modules_use_the_shared_exc_summary():
    """RED at base: serper_service and extraction_service import exc_summary
    from the leaf (R3.3 -- module top)."""
    import app.services.log_scrub as log_scrub

    assert getattr(ss, "exc_summary", None) is log_scrub.exc_summary
    assert getattr(es, "exc_summary", None) is log_scrub.exc_summary


# A verbatim copy of the base R-W18 scrubber
# (structured_comparison_service.py:300-341 at 4bd5a09f), used ONLY as the
# reference the moved function must keep matching (R3.1: output identical to
# base for every input). The two Unicode separators are appended with chr() so
# this file stays ASCII; the character class is the same as the source's.
_REF_URL_RE = re.compile(r"(?i)([a-z][a-z0-9+.\-]{0,15}://)(\S*)")
_REF_LINEBREAK_RE = re.compile(r"[\r\n\x0b\x0c\x1c-\x1e\x85" + _LS + _PS + "]+")
_REF_MAX_CHARS = 200


def _ref_url(m):
    scheme, rest = m.group(1), m.group(2)
    at = rest.rfind("@")
    if at != -1:
        if "?" in rest[:at] or "#" in rest[:at]:
            return scheme + "[redacted]"
        rest = rest[at + 1:]
    for sep in ("?", "#"):
        cut = rest.find(sep)
        if cut != -1:
            rest = rest[:cut]
    return scheme + rest


def _ref_safe_exc(exc):
    try:
        text = str(exc)
    except Exception:  # noqa: BLE001
        return f"<unprintable {type(exc).__name__}>"
    text = _REF_URL_RE.sub(_ref_url, text)
    text = _REF_LINEBREAK_RE.sub(" ", text)
    return text[:_REF_MAX_CHARS]


_SAFE_EXC_INPUTS = {
    "empty": ValueError(""),
    "noarg_timeout": TimeoutError(),
    "plain": RuntimeError("plain text"),
    "userinfo_query_fragment_two_urls": RuntimeError(
        "see https://user:pass@h.test/a/b?x=1#f and socks5://u:p@proxy.test:1080"),
    "at_inside_query": RuntimeError("q https://h.test/p?email=a@b&k=SECRET end"),
    "question_mark_inside_password": RuntimeError("pw https://user:pa?ss@h.test/p"),
    "line_breaks": RuntimeError("line1\nline2\r\nline3\x0bline4"),
    "unicode_line_separators": RuntimeError("a" + _LS + "b" + _PS + "c\x85d\x0be"),
    "over_200_chars": RuntimeError("z" * 600),
    "sentry_shapes_are_NOT_scrubbed_by_safe_exc": RuntimeError(
        "Bearer abc.def.ghi 0123456789abcdef0123456789abcdef"),
    "broken_str": _BrokenStr(),
}


@pytest.mark.parametrize("exc", list(_SAFE_EXC_INPUTS.values()), ids=list(_SAFE_EXC_INPUTS))
def test_safe_exc_outputs_unchanged(exc):
    """PIN: the (moved) scs._safe_exc output equals the base R-W18 scrubber's
    for every input -- it does NOT gain the sentry patterns exc_summary adds."""
    assert scs._safe_exc(exc) == _ref_safe_exc(exc)


# ===========================================================================
# R3.3 / R3.4 / C1 -- the eight CHANGE sites
# ===========================================================================

_SERPER = "app.services.serper_service"
_EXTRACT = "app.services.extraction_service"

# id: (logger, old prefix, constant template, empty-text exception factory,
#      expected record.args head before the summary, base return value)
_SITES = {
    "search_web": (_SERPER, "Search error: ", "Search error: %s",
                   lambda: httpx.ReadTimeout(""), (),
                   {"organic": [], "error": ""}),
    "shopping": (_SERPER, "Serper shopping call error (gl=us): ",
                 "Serper shopping call error (gl=%s): %s",
                 lambda: httpx.ConnectTimeout(""), ("us",), {}),
    "price_organic": (_SERPER, "Price organic search error: ",
                      "Price organic search error: %s",
                      lambda: httpx.ReadTimeout(""), (),
                      {"organic": [], "error": ""}),
    "videos": (_SERPER, "Video search error: ", "Video search error: %s",
               lambda: httpx.ReadTimeout(""), (), {"videos": [], "error": ""}),
    "news": (_SERPER, "News search error: ", "News search error: %s",
             lambda: httpx.ConnectTimeout(""), (), {"news": [], "error": ""}),
    "extract_specs": (_EXTRACT, "Specs extraction error: ", "Specs extraction error: %s",
                      lambda: TimeoutError(), (),
                      ({"brand": "B", "model": "N", "error": ""}, _ZERO_USAGE)),
    "extract_price": (_EXTRACT, "Price extraction error: ", "Price extraction error: %s",
                      lambda: TimeoutError(), (),
                      ({"amount": None, "currency": "BHD", "error": ""}, _ZERO_USAGE)),
    "extract_price_fallback": (_EXTRACT, "Price fallback error: ", "Price fallback error: %s",
                               lambda: TimeoutError(), (),
                               ({"amount": None, "currency": "BHD", "error": ""}, _ZERO_USAGE)),
}


@pytest.fixture(autouse=True)
def _site_env(monkeypatch):
    monkeypatch.delenv("ENABLE_PRICE_FALLBACK_MAY_DECLINE", raising=False)
    monkeypatch.delenv("ENABLE_LLM_PREFLIGHT_BREAKER", raising=False)
    monkeypatch.delenv("ENABLE_SERPER_BREAKER", raising=False)
    monkeypatch.delenv("ENABLE_BRIGHTDATA_FALLBACK", raising=False)
    yield


async def _drive(site, monkeypatch, exc):
    """Run the REAL site function with its transport / LLM call raising
    ``exc``. No network: ``_serper_post`` / ``guarded_llm_create`` are the
    first I/O and both are replaced (an ``httpx.AsyncClient`` opens no
    connection on construction); Bright Data is disabled; the LLM client is a
    MagicMock that is never dispatched (OR6)."""
    if site in ("search_web", "shopping", "price_organic", "videos", "news"):
        import app.services.brightdata_service as bds

        monkeypatch.setattr(ss, "_active_serper_key", lambda *a, **k: "test-serper-key")
        monkeypatch.setattr(ss, "_serper_budget_ok", lambda *a, **k: True)
        monkeypatch.setattr(bds, "_brightdata_enabled", lambda *a, **k: False)

        async def _boom_post(client, path, payload):
            raise exc

        monkeypatch.setattr(ss, "_serper_post", _boom_post)
        if site == "search_web":
            return await ss.search_web("iPhone 16")
        if site == "shopping":
            return await ss._do_serper_shopping("iPhone 16", "us")
        if site == "price_organic":
            return await ss.search_price_organic("iPhone 16", "bh")
        if site == "videos":
            return await ss.search_videos("iPhone 16 review")
        return await ss.search_news("iPhone 16")

    async def _boom_llm(client, **kwargs):
        raise exc

    monkeypatch.setattr(es._llm_breaker, "guarded_llm_create", _boom_llm)
    monkeypatch.setattr(es, "get_client", lambda: MagicMock())
    if site == "extract_specs":
        return await es.extract_specs("B", "N", None, "other", "ctx")
    if site == "extract_price":
        return await es.extract_price("B", "N", None, "bahrain", "ctx")
    return await es.extract_price_from_training_data("B", "N", None, "bahrain")


def _error_records(caplog, logger_name):
    return [r for r in caplog.records
            if r.name == logger_name and r.levelno >= logging.ERROR]


@pytest.mark.asyncio
@pytest.mark.parametrize("site", list(_SITES))
async def test_site_logs_name_the_type(monkeypatch, caplog, site):
    """RED at base (the message is the bare prefix). Exactly one ERROR record
    whose formatted message is ``<old prefix><TypeName>``, whose ``record.msg``
    is the CONSTANT template (no exception text, so one Sentry issue per
    template) and whose ``record.args`` carry the summary last."""
    logger_name, prefix, template, make_exc, args_head, _ = _SITES[site]
    exc = make_exc()
    type_name = type(exc).__name__
    caplog.set_level(logging.ERROR, logger=logger_name)
    await _drive(site, monkeypatch, exc)
    recs = _error_records(caplog, logger_name)
    assert len(recs) == 1, [r.getMessage() for r in recs]
    rec = recs[0]
    assert rec.getMessage() == f"{prefix}{type_name}", rec.getMessage()
    assert rec.msg == template, rec.msg
    assert type_name not in str(rec.msg)
    assert isinstance(rec.args, tuple), rec.args
    assert rec.args == (*args_head, type_name), rec.args


@pytest.mark.asyncio
@pytest.mark.parametrize("site", list(_SITES))
async def test_site_return_value_unchanged(monkeypatch, caplog, site):
    """PIN (C3: split out of the log test so it executes at base): the return
    value of every CHANGE site is byte-identical to base, including the
    ``"error": str(e)`` field (empty for these exceptions)."""
    _, _, _, make_exc, _, expected = _SITES[site]
    caplog.set_level(logging.ERROR)
    out = await _drive(site, monkeypatch, make_exc())
    assert out == expected, out


@pytest.mark.asyncio
@pytest.mark.parametrize("site", list(_SITES))
async def test_site_log_carries_no_exc_info(monkeypatch, caplog, site):
    """PIN (OR9; green at base, where the f-string sites pass no exc_info): the
    ONE ERROR record of every CHANGE site carries no exception info and no
    stack, so each %-template stays one Sentry issue."""
    logger_name, _, _, make_exc, _, _ = _SITES[site]
    caplog.set_level(logging.ERROR, logger=logger_name)
    await _drive(site, monkeypatch, make_exc())
    recs = _error_records(caplog, logger_name)
    assert len(recs) == 1, [r.getMessage() for r in recs]
    assert not recs[0].exc_info, recs[0].exc_info
    assert recs[0].stack_info is None, recs[0].stack_info


@pytest.mark.asyncio
@pytest.mark.parametrize("site", list(_SITES))
async def test_site_log_scrubs_exception_text(monkeypatch, caplog, site):
    """RED at base (the f-string logs the raw text, credentials and query
    included). A text-bearing exception is logged as ``Type: scrubbed text``;
    the RETURN value still carries ``str(e)`` exactly as at base."""
    logger_name, prefix, template, _, args_head, _ = _SITES[site]
    raw = "boom https://user:hunter2@h.test/p?q=SECRET#frag"
    caplog.set_level(logging.ERROR, logger=logger_name)
    out = await _drive(site, monkeypatch, RuntimeError(raw))
    recs = _error_records(caplog, logger_name)
    assert len(recs) == 1, [r.getMessage() for r in recs]
    rec = recs[0]
    assert rec.getMessage() == f"{prefix}RuntimeError: boom https://h.test/p", rec.getMessage()
    assert rec.msg == template
    assert rec.args == (*args_head, "RuntimeError: boom https://h.test/p"), rec.args
    assert "hunter2" not in rec.getMessage() and "SECRET" not in rec.getMessage()
    # return values keep str(e) byte-identical (the shopping site returns {})
    if site == "shopping":
        assert out == {}
    elif site in ("extract_specs", "extract_price", "extract_price_fallback"):
        assert out[0]["error"] == raw and out[1] == _ZERO_USAGE
    else:
        assert out["error"] == raw
