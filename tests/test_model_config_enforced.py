"""W4-11 (PO-PROMPTS-03, rulings R7 / C7 / C13) -- every OpenAI chat call routes its
sampling and token kwargs through model_config.

W1-3 (#147) moved 14 of the 15 chat-completion sites behind
``api_budget_service.guarded_llm_create``; only ``image_service.extract_image_via_gpt``
still calls ``client.chat.completions.create`` directly. A pin that matches only
``*.completions.create`` therefore sees 1 site and passes while 11 raw sites remain,
so M1 matches BOTH callees and asserts the site count. The two excluded wrapper
pass-throughs are ``api_budget_service.guarded_llm_create``'s own
``client.chat.completions.create(**kwargs)`` calls (flag-OFF and flag-ON branches):
17 raw matches - 2 = 15 sites (C13).

RED = fails at the base HEAD for the stated reason; PIN = green at base and must stay.
Zero network (autouse socket/DNS + curl_cffi guard); every node clears the
OPENAI_MODEL_* ids and the breaker flag (flag OFF = a bare create).
"""
import ast
import ipaddress
import os
import pathlib
import socket

import pytest

import app.services.extraction_service as es  # noqa: E402  (R13: module-top import)
import app.services.image_service as imgsvc  # noqa: E402
import app.services.openai_service as osvc  # noqa: E402
import app.services.url_extraction_service as urlsvc  # noqa: E402
import app.services.verdict_critique_service as vcs  # noqa: E402
from tests.w4_11_prompt_digest_recorder import BENIGN_HTML, BENIGN_ORGANIC, fake_client  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
JSON = {"type": "json_object"}


def _is_loopback_host(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    host = str(host)
    if host in ("localhost", "testserver", "testclient", "test", ""):
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts: list = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_gai = socket.getaddrinfo

    def _addr_ok(address) -> bool:
        if isinstance(address, (str, bytes)):
            return True
        if isinstance(address, tuple) and address:
            return _is_loopback_host(address[0])
        return False

    def guarded_connect(self, address):
        if not _addr_ok(address):
            attempts.append(("connect", repr(address)))
            raise OSError(f"W4-11 zero-network guard: connect {address!r}")
        return real_connect(self, address)

    def guarded_connect_ex(self, address):
        if not _addr_ok(address):
            attempts.append(("connect_ex", repr(address)))
            raise OSError(f"W4-11 zero-network guard: connect_ex {address!r}")
        return real_connect_ex(self, address)

    def guarded_gai(host, *args, **kwargs):
        if not _is_loopback_host(host):
            attempts.append(("getaddrinfo", repr(host)))
            raise socket.gaierror(f"W4-11 zero-network guard: {host!r}")
        return real_gai(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_gai)
    try:
        import curl_cffi.requests as _cc

        def _no_curl(*a, **kw):
            attempts.append(("curl_cffi.requests.get", repr(a[:1])))
            raise OSError("W4-11 zero-network guard: curl_cffi.requests.get")
        monkeypatch.setattr(_cc, "get", _no_curl)
    except ImportError:  # pragma: no cover - curl_cffi is pinned in CI
        pass
    yield attempts
    assert not attempts, f"test attempted network access: {attempts!r}"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in list(os.environ):
        if k.startswith("OPENAI_MODEL_"):
            monkeypatch.delenv(k, raising=False)
    for k in ("ENABLE_LLM_PREFLIGHT_BREAKER", "ENABLE_PRICE_FALLBACK_MAY_DECLINE",
              "ENABLE_VERDICT_PROMPT_TRUTH", "ENABLE_SPECS_NO_FABRICATION",
              "ENABLE_PRICE_PARSE_OFFLOAD"):
        monkeypatch.delenv(k, raising=False)
    yield


# ---------------------------------------------------------------------------
# M1 -- the AST pin
# ---------------------------------------------------------------------------
def _is_wrapper_passthrough(path, node):
    return (path.name == "api_budget_service.py" and not node.args
            and len(node.keywords) == 1 and node.keywords[0].arg is None)


def _chat_sites():
    sites = []
    for path in sorted((ROOT / "app").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = ast.unparse(node.func)
            if not (callee.endswith("completions.create") or callee.endswith("guarded_llm_create")):
                continue
            if _is_wrapper_passthrough(path, node):
                continue
            sites.append((f"{path.relative_to(ROOT).as_posix()}:{node.lineno}", callee, node))
    return sites


def test_no_call_site_passes_raw_sampling_kwargs():
    """M1 RED: AST over app/**/*.py, callee ending `completions.create` OR `guarded_llm_create`
    (minus the wrapper's two `**kwargs` pass-throughs): >= 15 sites (so a matcher that stops
    matching cannot pass vacuously) and NO literal `temperature=` / `max_tokens=` keyword.
    Base: 15 sites, 12 raw temperature, 6 raw max_tokens."""
    sites = _chat_sites()
    assert len(sites) >= 15, f"only {len(sites)} chat-completion sites matched (matcher narrowed?)"
    raw = [(where, kw.arg) for where, _c, node in sites for kw in node.keywords
           if kw.arg in ("temperature", "max_tokens")]
    assert not raw, f"{len(raw)} literal sampling/token kwargs bypass model_config: {raw}"


def test_image_tier3_dispatches_through_the_breaker_chokepoint(monkeypatch):
    """M5 RED (ruling R7): extract_image_via_gpt is the one chat call that bypasses the W1-3
    chokepoint; it must dispatch through api_budget_service.guarded_llm_create (byte-identical
    with the breaker flag OFF), and no app module may call `completions.create` directly
    outside the wrapper. Base: image_service.py:173 is a direct create."""
    import asyncio

    from app.services import api_budget_service

    direct = [where for where, callee, _n in _chat_sites() if callee.endswith("completions.create")]
    assert not direct, f"direct chat.completions.create outside the breaker wrapper: {direct}"
    seen = []
    real = api_budget_service.guarded_llm_create

    async def _spy(client, **kwargs):
        seen.append(kwargs.get("model"))
        return await real(client, **kwargs)

    monkeypatch.setattr(api_budget_service, "guarded_llm_create", _spy)
    calls = []
    monkeypatch.setattr(imgsvc, "get_client", lambda *a, **k: fake_client(calls, '{"image_url": null}'))
    asyncio.run(imgsvc.extract_image_via_gpt("Apple iPhone 17", BENIGN_ORGANIC))
    assert calls, "extract_image_via_gpt made no OpenAI call"
    assert seen, "extract_image_via_gpt did not dispatch through guarded_llm_create"


# ---------------------------------------------------------------------------
# M2 / M3 -- the twelve routed sites, captured through fake clients
# ---------------------------------------------------------------------------
async def _call(monkeypatch, site):
    calls = []

    def _client(content):
        return lambda *a, **k: fake_client(calls, content)

    if site == "classify_category_llm":
        monkeypatch.setattr(es, "get_client", _client("electronics"))
        await es.classify_category_llm(["Apple iPhone 17"])
    elif site == "parse_product_query":
        monkeypatch.setattr(es, "get_client", _client('{"products": []}'))
        await es.parse_product_query("iPhone 17 vs Galaxy S25")
    elif site == "extract_specs":
        monkeypatch.setattr(es, "get_client", _client("{}"))
        await es.extract_specs("Apple", "iPhone 17", "256GB", "electronics", "[snippet_1] battery 3500 mAh")
    elif site == "extract_price":
        monkeypatch.setattr(es, "get_client", _client("{}"))
        await es.extract_price("Apple", "iPhone 17", None, "bahrain", "[snippet_1] 312.500 BHD")
    elif site == "extract_price_from_training_data":
        monkeypatch.setattr(es, "get_client", _client('{"amount": 300, "original_currency": "USD"}'))
        await es.extract_price_from_training_data("Apple", "iPhone 17", None, "bahrain")
    elif site == "extract_reviews":
        monkeypatch.setattr(es, "get_client", _client("{}"))
        await es.extract_reviews("Apple", "iPhone 17", None, "[snippet_1] great phone")
    elif site == "extract_specs_targeted":
        monkeypatch.setattr(osvc, "get_client", _client('{"battery": "5000 mAh"}'))
        await osvc.extract_specs_targeted(brand="Apple", name="iPhone 17", variant=None,
                                          category="electronics", fields=["battery"], context="snip")
    elif site == "extract_specs_synthesized":
        monkeypatch.setattr(osvc, "get_client", _client('{"battery": "5000 mAh"}'))
        await osvc.extract_specs_synthesized(brand="Apple", name="iPhone 17", variant=None,
                                             category="electronics", fields=["battery"], model=None)
    elif site == "disambiguate_variant_line":
        monkeypatch.setattr(osvc, "get_client", _client('{"distinct_product": false, "confidence": "high"}'))
        await osvc.disambiguate_variant_line("fragrances", "Dior Sauvage EDP", "Dior Sauvage EDP Men", "gender")
    elif site == "extract_image_via_gpt":
        monkeypatch.setattr(imgsvc, "get_client", _client('{"image_url": null}'))
        await imgsvc.extract_image_via_gpt("Apple iPhone 17", BENIGN_ORGANIC)
    elif site == "extract_with_ai":
        monkeypatch.setattr(urlsvc, "get_client", _client('{"name": "iPhone 17"}'))
        await urlsvc.extract_with_ai("https://www.example-retailer.com/p/iphone-17", BENIGN_HTML,
                                     {"key": "generic", "name": "Example"})
    elif site == "critique_verdict":
        monkeypatch.setattr(vcs, "get_client", _client("{}"))
        await vcs.critique_verdict(comparison={"winner_index": 0, "winner_reason": "Longer battery life"},
                                   product_names=["Apple iPhone 17", "Samsung Galaxy S25"])
    else:  # pragma: no cover
        raise AssertionError(site)
    assert calls, f"{site} made no OpenAI call"
    return {k: v for k, v in calls[0].items() if k != "messages"}


# The shipped values (all OPENAI_MODEL_* unset), measured at the base HEAD (spec 0.6 + C7).
SHIPPED = {
    "classify_category_llm": {"model": "gpt-4o-mini", "max_tokens": 10, "temperature": 0.0},
    "parse_product_query": {"model": "gpt-4o-mini", "max_tokens": 500, "temperature": 0.1},
    "extract_specs": {"model": "gpt-4o-mini", "max_tokens": 1000, "temperature": 0.1},
    "extract_price": {"model": "gpt-4o-mini", "max_tokens": 300, "temperature": 0.1},
    "extract_price_from_training_data": {"model": "gpt-4o-mini", "max_tokens": 200, "temperature": 0.2},
    "extract_reviews": {"model": "gpt-4o-mini", "max_tokens": 600, "temperature": 0.2},
    "extract_specs_targeted": {"model": "gpt-4o-mini", "max_tokens": 200, "temperature": 0.1, "response_format": JSON},
    "extract_specs_synthesized": {"model": "gpt-4o", "max_tokens": 300, "temperature": 0.1, "response_format": JSON},
    "disambiguate_variant_line": {"model": "gpt-4o-mini", "max_tokens": 60, "temperature": 0, "response_format": JSON},
    "extract_image_via_gpt": {"model": "gpt-4o-mini", "max_tokens": 120, "temperature": 0.1},
    "extract_with_ai": {"model": "gpt-4o-mini", "max_tokens": 800, "temperature": 0.1},
    "critique_verdict": {"model": "gpt-4o-mini", "max_tokens": 150, "temperature": 0.0, "response_format": JSON},
}
SITES = sorted(SHIPPED)


@pytest.mark.asyncio
@pytest.mark.parametrize("site", SITES)
async def test_gpt5_ids_emit_no_rejected_kwargs(monkeypatch, site):
    """M2 RED (C7: all twelve routed sites): with GPT-5-family ids configured, no call sends
    `temperature` (a non-default temperature is a 400 on GPT-5) or `max_tokens` (GPT-5 needs
    `max_completion_tokens`). Base: every site still sends a literal temperature."""
    monkeypatch.setenv("OPENAI_MODEL_STANDARD", "gpt-5-mini")
    monkeypatch.setenv("OPENAI_MODEL_VERDICT", "gpt-5")
    monkeypatch.setenv("OPENAI_MODEL_CRITIC", "gpt-5-mini")
    kw = await _call(monkeypatch, site)
    assert "temperature" not in kw, f"{site} sends temperature={kw.get('temperature')!r} to {kw.get('model')}"
    assert "max_tokens" not in kw, f"{site} sends max_tokens={kw.get('max_tokens')!r} to {kw.get('model')}"


@pytest.mark.asyncio
@pytest.mark.parametrize("site", SITES)
async def test_shipped_ids_kwargs_unchanged(monkeypatch, site):
    """M3 PIN (C7): with every OPENAI_MODEL_* unset each of the twelve sites sends exactly the
    kwargs it sends today (routing through sampling_kwargs/token_limit_kwargs is
    byte-identical on the ids that resolve today)."""
    kw = await _call(monkeypatch, site)
    assert kw == SHIPPED[site]


def test_resolved_models_unchanged():
    """M4 PIN: resolved_models() with every OPENAI_MODEL_* unset."""
    from app.services.model_config import resolved_models

    assert resolved_models() == {"critic": "gpt-4o-mini", "moderation": "omni-moderation-latest",
                                 "standard": "gpt-4o-mini", "verdict": "gpt-4o", "vision": "gpt-4o-mini"}
