"""U3b (session 75) -- the per-user AI-sharing branch is gone from the backend.

Decision D3 = C (2026-10-08, rulings OA2/OA3): the organisation shares the
compare inputs and outputs with OpenAI and there is NO per-user AI-sharing
control. The dead routing (select_client_for_user, the OPENAI_API_KEY_PRIVATE
arm of get_client, the use_shared_project parameter) is deleted from
app/services/openai_service.py; get_client() takes no argument and memoises
ONE AsyncOpenAI under a dict cache (test_m18's contract). The preference field
ai_sharing_enabled stays accepted and stored by app/api/auth_routes.py for older
app bundles and is read by nothing else (inert).

Spec: scratchpad/specs/U3B_CONSENT_V2_SPEC.md section 3 (B1-B4), rulings
FABLE_RULINGS_U3B.md. B1/B2/B4 are red at main 4c0f3c99; B3 is a pin.
Post-adversary rulings UY3/UY4 (FABLE_RULINGS_U3B_POST_ADVERSARY.md): B5 pins
the OpenAPI texts of the preference-toggles route (no opt-out / PDPL claim);
B3 also pins the constructor kwargs (no api_key, so the SDK reads
OPENAI_API_KEY itself; the retry knob; the timeout).

Hermetic: source walks over app/, a spy class in place of AsyncOpenAI and a
fresh app.openapi() build (the cached schema is restored). No network; the only
environment touch is B3 setting the non-secret OPENAI_MAX_RETRIES knob through
monkeypatch. Pure ASCII, LF.
"""
import inspect
import re
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "app"

# The three names of the deleted branch (spec T-D grep fence).
REMOVED_TOKENS = (b"select_client_for_user", b"OPENAI_API_KEY_PRIVATE", b"use_shared_project")
INERT_FIELD = b"ai_sharing_enabled"
# The ONE app/ file allowed to name the inert field (the route that stores and
# echoes it for older bundles; spec T-E).
INERT_READERS = {"app/api/auth_routes.py"}
# UY3: the public /docs text of the preference-toggles route must not claim an
# opt-out (D3 = C has no per-user control).
OPT_OUT_CLAIM = re.compile(r"opt.?out|PDPL", re.IGNORECASE)
TOGGLES_PATH = "/api/v1/auth/preference-toggles"


def _app_py_files():
    files = []
    for path in sorted(APP.rglob("*.py")):
        if path.is_file():
            files.append(path)
    assert files, "no .py under app/ -- wrong repo root"
    return files


def _rel(path):
    return path.relative_to(REPO).as_posix()


def test_b1_no_app_file_names_the_deleted_sharing_branch():
    """B1 grep fence: select_client_for_user / OPENAI_API_KEY_PRIVATE /
    use_shared_project appear in no .py under app/."""
    hits = []
    for path in _app_py_files():
        data = path.read_bytes()
        for token in REMOVED_TOKENS:
            if token in data:
                hits.append((_rel(path), token.decode("ascii")))
    assert hits == [], "the deleted AI-sharing branch is still named in app/: %r" % (hits,)


def test_b2a_openai_service_has_no_select_client_for_user():
    """B2 import fence (a): the routing function is gone."""
    from app.services import openai_service

    assert not hasattr(openai_service, "select_client_for_user"), (
        "openai_service still defines select_client_for_user (D3 = C: no per-user routing)"
    )


def test_b2b_get_client_takes_no_parameter():
    """B2 import fence (b): get_client() has an empty signature -- a parameter
    that selects nothing would be a lie."""
    from app.services import openai_service

    params = inspect.signature(openai_service.get_client).parameters
    assert dict(params) == {}, "get_client still takes parameters: %r" % (list(params),)


def test_b3_get_client_memoises_one_client_under_a_dict_cache(monkeypatch):
    """B3 pin (green at main): two get_client() calls construct AsyncOpenAI once
    and return the same object; _client_cache stays a dict (test_m18 saves,
    clears and updates it as a dict). UY4: the one construction passes no
    api_key (the SDK reads OPENAI_API_KEY itself, so no second key can come
    back under any spelling), the OPENAI_MAX_RETRIES knob (set to 4 here, so
    a hard-coded count other than 4 cannot pass B3; test_m18 pins the launch
    value 1) and the 120 s / 30 s connect timeout."""
    import app.services.openai_service as osvc

    built = []
    seen_kwargs = []

    class _Spy:
        def __init__(self, *a, **kw):
            built.append(self)
            seen_kwargs.append(dict(kw))

    monkeypatch.setenv("OPENAI_MAX_RETRIES", "4")
    monkeypatch.setattr(osvc, "AsyncOpenAI", _Spy)
    monkeypatch.setattr(osvc, "_client_cache", {}, raising=False)

    first = osvc.get_client()
    second = osvc.get_client()

    assert first is second, "get_client() must return the memoised client"
    assert len(built) == 1, "AsyncOpenAI constructed %d times, expected once" % len(built)
    assert isinstance(osvc._client_cache, dict), type(osvc._client_cache)
    assert first in osvc._client_cache.values()

    kw = seen_kwargs[0]
    assert "api_key" not in kw, (
        "get_client() passes an api_key (a second key arm is back): %r" % (sorted(kw),)
    )
    assert osvc.openai_max_retries() == 4, "the OPENAI_MAX_RETRIES knob did not resolve"
    assert kw.get("max_retries") == osvc.openai_max_retries(), (
        "max_retries %r is not the OPENAI_MAX_RETRIES knob" % (kw.get("max_retries"),)
    )
    assert kw.get("timeout") == httpx.Timeout(120.0, connect=30.0), (
        "timeout %r is not httpx.Timeout(120.0, connect=30.0)" % (kw.get("timeout"),)
    )


def test_b4_only_the_route_names_the_inert_preference_field():
    """B4 inert-reader fence: the set of app/ files naming ai_sharing_enabled is
    exactly the route that stores and echoes it for older bundles."""
    readers = set()
    for path in _app_py_files():
        if INERT_FIELD in path.read_bytes():
            readers.add(_rel(path))
    assert readers == INERT_READERS, (
        "ai_sharing_enabled is read outside the route: %r" % (sorted(readers - INERT_READERS),)
    )


def test_b5_openapi_preference_toggles_texts_claim_no_opt_out():
    """B5 (UY3): a FRESH app.openapi() build (the cached schema is saved,
    cleared and restored, as test_s71_u13's _openapi_snapshot does): neither
    components.schemas.PreferenceTogglesBody.description nor the PUT
    /api/v1/auth/preference-toggles operation description matches
    /opt.?out|PDPL/i."""
    from app.main import app

    saved = app.openapi_schema
    app.openapi_schema = None
    try:
        schema = app.openapi()
    finally:
        app.openapi_schema = saved

    body_doc = schema["components"]["schemas"]["PreferenceTogglesBody"].get("description", "")
    route_doc = schema["paths"][TOGGLES_PATH]["put"].get("description", "")
    assert body_doc and route_doc, "the OpenAPI texts went missing: %r / %r" % (body_doc, route_doc)
    hits = [
        (where, match.group(0))
        for where, text in (("PreferenceTogglesBody", body_doc), ("PUT " + TOGGLES_PATH, route_doc))
        for match in OPT_OUT_CLAIM.finditer(text)
    ]
    assert hits == [], "the OpenAPI text still claims an AI-sharing opt-out: %r" % (hits,)
