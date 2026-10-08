"""U3c (session 74) -- store=False on every OpenAI chat-completion dispatch.

Every chat completion is sent with store=False, so none becomes a stored
completion (dashboard Logs); the organisation data-sharing setting (OA2) is
separate and unaffected (OA3). This file makes no retention-period claim.

The ONE chokepoint is api_budget_service.guarded_llm_create; the pin is
unconditional (no flag), covers both breaker branches and overrides any caller
value (ruling R1). An extra_body carrying "store" is forced to False at runtime
(ruling R2: the pinned SDK merges extra_body OVER the body). The two direct
dispatches in scripts/ carry store=False too (ruling R5).

Hermetic: fake clients and an in-process mock transport only. Pure ASCII.
"""
import ast
import asyncio
import json
import types
from pathlib import Path

import pytest

from app.services import api_budget_service as abs_mod

REPO = Path(abs_mod.__file__).resolve().parents[2]
APP = REPO / "app"
SCRIPTS = REPO / "scripts"
CHOKEPOINT_FILE = APP / "services" / "api_budget_service.py"

# T02 attribute rule (ruling F2, narrowed by ruling X6). An OpenAI SDK surface in app/
# outside guarded_llm_create that could dispatch without the pin is: .create / .parse /
# .stream on an SDK object (chat.completions, responses, batches, with_raw_response,
# with_streaming_response); any chain through chat.completions, with_raw_response or
# with_streaming_response (a bound-method alias, getattr(...), functools.partial(...));
# a REST path string EQUAL to an SDK endpoint; getattr(..., <a GETATTR_NAMES string>).
DISPATCH_METHODS = frozenset({"create", "parse", "stream"})
SDK_OBJECTS = frozenset({"responses", "batches", "with_raw_response", "with_streaming_response"})
SDK_WRAPPERS = frozenset({"with_raw_response", "with_streaming_response"})
REST_PATHS = frozenset({"/chat/completions", "/responses", "/batches"})
GETATTR_NAMES = frozenset({
    "create", "parse", "stream", "chat", "completions", "responses", "batches",
    "with_raw_response", "with_streaming_response",
})
# The review probe shapes (U3c review NOTES/t02_bypass_probe.out): the rule must
# flag every one of them.
BYPASS_SHAPES = {
    "plain": "await client.chat.completions.create(model='m', messages=[])",
    "with_options": "await client.with_options(timeout=5).chat.completions.create(model='m')",
    "alias_bound_method": "create = client.chat.completions.create\nawait create(model='m')",
    "getattr_create": "await getattr(client.chat.completions, 'create')(model='m')",
    "partial": "import functools\nf = functools.partial(client.chat.completions.create, model='m')\nawait f()",
    "responses_parse": "await client.responses.parse(model='m', input='x')",
    "responses_raw": "await client.responses.with_raw_response.create(model='m', input='x')",
    "low_level_post": "await client.post('/chat/completions', body={'model': 'm'}, cast_to=object)",
    "batches_create": (
        "await client.batches.create(input_file_id='f', endpoint='/v1/chat/completions', "
        "completion_window='24h')"
    ),
    "beta_chat_parse": "await client.beta.chat.completions.parse(model='m', messages=[])",
}
# Ruling X6: shapes the narrowed rule must NOT flag (the engineering adversary's false
# positives: a fastapi.responses attribute, a non-SDK .completions / .chat / .beta
# attribute, a route path under /batches/).
LEGIT_SHAPES = {
    "fastapi_responses_attr": "import fastapi\nr = fastapi.responses.JSONResponse({})",
    "survey_completions_attr": "rate = survey.completions / max(1, survey.starts)",
    "chat_feature_attr": "enabled = settings.chat",
    "beta_flag_attr": "if user.beta:\n    pass",
    "route_batches_id": "@router.get('/batches/{bid}')\nasync def get_batch(bid):\n    return bid",
}
# Ruling R2 + F12 + X5: literal keywords no guarded_llm_create call site may pass
# (store / extra_body / extra_query would fight the chokepoint or bypass the body; the
# rest would send an account identifier, privacy.html:244).
DENIED_CALL_SITE_KWARGS = (
    "store", "extra_body", "extra_query", "user", "safety_identifier", "metadata",
    "prompt_cache_key", "extra_headers",
)
# Ruling X5: the only ** spreads a guarded_llm_create call site may carry = the static
# census at dfbda511 (15 sites): token_limit_kwargs(...) x15, sampling_kwargs(...) x15,
# _json_mode x1 (extraction_service.extract_price_from_training_data). Any other spread
# (a dict literal, another helper) could carry a denied keyword past the literal check.
ALLOWED_SPREAD_CALLS = frozenset({"token_limit_kwargs", "sampling_kwargs"})
ALLOWED_SPREAD_NAMES = frozenset({"_json_mode"})


def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    elif isinstance(node, ast.Call):
        parts.append(_dotted(node.func) + "()")
    return ".".join(reversed(parts))


def _is_dispatch(call):
    return _dotted(call.func).endswith("chat.completions.create")


def _func(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError("function %s not found" % name)


def _chokepoint():
    return _func(ast.parse(CHOKEPOINT_FILE.read_text(encoding="utf-8")), "guarded_llm_create")


def _body(fn):
    """Top-level statements of fn without its docstring."""
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    return body


def _is_store_false_assign(stmt, name="kwargs"):
    """<name>["store"] = False, as one plain assignment statement."""
    if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
        return False
    t = stmt.targets[0]
    return (
        isinstance(t, ast.Subscript)
        and isinstance(t.value, ast.Name) and t.value.id == name
        and isinstance(t.slice, ast.Constant) and t.slice.value == "store"
        and isinstance(stmt.value, ast.Constant) and stmt.value.value is False
    )


def _contains_dispatch(stmt):
    return any(isinstance(n, ast.Call) and _is_dispatch(n) for n in ast.walk(stmt))


def _first_dispatch_index(body):
    return next(i for i, s in enumerate(body) if _contains_dispatch(s))


def _store_writes(fn, name="kwargs"):
    return [
        n for n in ast.walk(fn)
        if isinstance(n, ast.Subscript) and isinstance(n.ctx, (ast.Store, ast.Del))
        and isinstance(n.value, ast.Name) and n.value.id == name
        and isinstance(n.slice, ast.Constant) and n.slice.value == "store"
    ]


def _root_name(node):
    """The Name at the root of a Subscript/Attribute chain, else None."""
    while isinstance(node, (ast.Subscript, ast.Attribute)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _first_key(node):
    """For kwargs[...][...] chains: the key of the subscript applied to the Name."""
    key = None
    while isinstance(node, (ast.Subscript, ast.Attribute)):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            key = node.slice.value if isinstance(node.slice, ast.Constant) else "<dynamic>"
        node = node.value
    return key


def _py_files(root):
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _docstring_ids(tree):
    ids = set()
    for n in ast.walk(tree):
        if (isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)):
            ids.add(id(n.body[0].value))
    return ids


def _is_chat_completions(node):
    return (isinstance(node, ast.Attribute) and node.attr == "completions"
            and isinstance(node.value, ast.Attribute) and node.value.attr == "chat")


def _is_sdk_object(node):
    return _is_chat_completions(node) or (isinstance(node, ast.Attribute) and node.attr in SDK_OBJECTS)


def _sdk_surface_hits(tree, allowed_ids=frozenset()):
    """Ruling F2 attribute rule, narrowed by X6: every OpenAI SDK dispatch surface in tree
    outside allowed_ids."""
    hits = []
    docstrings = _docstring_ids(tree)
    for n in ast.walk(tree):
        if id(n) in allowed_ids:
            continue
        line = getattr(n, "lineno", 0)
        if isinstance(n, ast.Attribute) and n.attr in DISPATCH_METHODS and _is_sdk_object(n.value):
            hits.append("line %d .%s on an SDK object" % (line, n.attr))
        elif _is_chat_completions(n) or (isinstance(n, ast.Attribute) and n.attr in SDK_WRAPPERS):
            hits.append("line %d chain through .%s" % (line, n.attr))
        elif (isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
              and n.value in REST_PATHS):
            hits.append("line %d REST path %r" % (line, n.value))
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr"
              and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant)
              and n.args[1].value in GETATTR_NAMES):
            hits.append("line %d getattr(..., %r)" % (line, n.args[1].value))
    return hits


def _innermost_function(tree):
    """id(node) -> innermost enclosing FunctionDef/AsyncFunctionDef (None at module level)."""
    owner = {}

    def visit(node, fn):
        for child in ast.iter_child_nodes(node):
            inner = child if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
            owner[id(child)] = fn
            visit(child, inner)

    visit(tree, None)
    return owner


# --------------------------------------------------------------------------
# static pins
# --------------------------------------------------------------------------
def test_u3c_01_chokepoint_assigns_store_false_before_every_dispatch():
    """RED at main: guarded_llm_create forwards **kwargs unchanged (ruling R1)."""
    fn = _chokepoint()
    dispatches = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and _is_dispatch(n)]
    assert len(dispatches) == 2, "harness: expected the flag-OFF and flag-ON dispatch, saw %d" % len(dispatches)
    body = _body(fn)
    first_is_pin = bool(body) and _is_store_false_assign(body[0])
    assert first_is_pin, (
        "guarded_llm_create must assign kwargs['store'] = False as its FIRST statement, "
        "before the flag check (so both breaker branches carry it); first statement is: %s"
        % (ast.unparse(body[0]).splitlines()[0] if body else "<none>")
    )
    assert _first_dispatch_index(body) > 0, "the store assignment must precede the first dispatching statement"
    writes = _store_writes(fn)
    assert len(writes) == 1, "exactly one write to kwargs['store'] (no later re-assignment or del), saw %d" % len(writes)


def test_u3c_01b_chokepoint_cannot_strip_or_widen_the_dispatch_kwargs():
    """GUARD (green at main; ruling F3): inside guarded_llm_create no kwargs.<method>()
    call except .get, no rebinding/del of the name kwargs, writes into kwargs only in the
    privacy prologue (top-level statements before the first dispatch) and only to 'store'
    or 'extra_body', and each dispatch is exactly create(**kwargs). Kills a conditional
    kwargs.pop('store') and an extra keyword on one dispatch (review mutants mC, mA)."""
    fn = _chokepoint()
    assert fn.args.kwarg is not None and fn.args.kwarg.arg == "kwargs", "harness: signature (client, **kwargs)"
    body = _body(fn)
    first = _first_dispatch_index(body)
    prologue = {id(n) for s in body[:first] for n in ast.walk(s)}
    bad = []
    for n in ast.walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "kwargs"
                and n.func.attr != "get"):
            bad.append("line %d kwargs.%s()" % (n.lineno, n.func.attr))
        if isinstance(n, ast.Name) and n.id == "kwargs" and isinstance(n.ctx, (ast.Store, ast.Del)):
            bad.append("line %d rebinds or deletes kwargs" % n.lineno)
        if (isinstance(n, (ast.Subscript, ast.Attribute)) and isinstance(n.ctx, (ast.Store, ast.Del))
                and _root_name(n) == "kwargs"):
            if id(n) not in prologue:
                bad.append("line %d writes into kwargs after the privacy prologue" % n.lineno)
            elif _first_key(n) not in ("store", "extra_body"):
                bad.append("line %d writes kwargs[%r] in the prologue" % (n.lineno, _first_key(n)))
        if isinstance(n, ast.Call) and _is_dispatch(n):
            shape_ok = (
                not n.args and len(n.keywords) == 1 and n.keywords[0].arg is None
                and isinstance(n.keywords[0].value, ast.Name) and n.keywords[0].value.id == "kwargs"
            )
            if not shape_ok:
                bad.append("line %d dispatch is not exactly create(**kwargs): %s" % (n.lineno, ast.unparse(n)))
    assert bad == [], bad


def test_u3c_01c_kwargs_is_read_only_through_get_subscript_or_dispatch():
    """GUARD (ruling X2): inside guarded_llm_create every Load of the name kwargs is (i) the
    receiver of kwargs.get(...), (ii) the root of a kwargs[...] subscript, or (iii) the
    **kwargs of a dispatch. A helper call or an alias receiving kwargs can strip or widen
    the dispatch kwargs out of sight of T01/T01b (engineering adversary mutants e03, e04)."""
    fn = _chokepoint()
    ok, kinds = set(), {"get": 0, "subscript": 0, "dispatch": 0}
    for n in ast.walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get"
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "kwargs"):
            ok.add(id(n.func.value))
            kinds["get"] += 1
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "kwargs":
            ok.add(id(n.value))
            kinds["subscript"] += 1
        if isinstance(n, ast.Call) and _is_dispatch(n):
            for k in n.keywords:
                if k.arg is None and isinstance(k.value, ast.Name) and k.value.id == "kwargs":
                    ok.add(id(k.value))
                    kinds["dispatch"] += 1
    assert kinds["get"] >= 1 and kinds["subscript"] >= 1 and kinds["dispatch"] == 2, (
        "harness: expected the store/scrub prologue and two create(**kwargs) dispatches, saw %s" % kinds)
    bad = [
        "line %d passes kwargs outside .get(...) / kwargs[...] / create(**kwargs)" % n.lineno
        for n in ast.walk(fn)
        if isinstance(n, ast.Name) and n.id == "kwargs" and isinstance(n.ctx, ast.Load) and id(n) not in ok
    ]
    assert bad == [], bad


def test_u3c_02_no_chat_dispatch_outside_the_chokepoint_under_app():
    """GUARD (green at main; rulings F2, X6): no OpenAI SDK dispatch surface in app/ outside
    guarded_llm_create (.create/.parse/.stream on chat.completions, responses, batches or a
    raw/streaming wrapper; any chain through chat.completions or a wrapper; a REST path
    string equal to an SDK endpoint; getattr(..., 'create')). Self-checks: all 10 review
    bypass shapes are flagged and none of the X6 false-positive shapes is."""
    for shape, src in BYPASS_SHAPES.items():
        assert _sdk_surface_hits(ast.parse(src)), "harness: the rule misses the %s shape" % shape
    for shape, src in LEGIT_SHAPES.items():
        assert _sdk_surface_hits(ast.parse(src)) == [], "harness: the rule flags the legit %s shape" % shape
    offenders = []
    for path in _py_files(APP):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        allowed = frozenset()
        if path == CHOKEPOINT_FILE:
            allowed = frozenset(id(n) for n in ast.walk(_func(tree, "guarded_llm_create")))
        offenders += ["%s %s" % (path.relative_to(REPO).as_posix(), h) for h in _sdk_surface_hits(tree, allowed)]
    assert offenders == [], "OpenAI SDK surface outside guarded_llm_create: %s" % offenders


def test_u3c_03_call_sites_pass_no_store_or_extra_body():
    """GUARD (green at main; rulings R2, F12, X5): the chokepoint is the single source of truth
    for store; extra_body={'store': True} would override it in the SDK
    (_base_client._merge_mappings) and extra_query would move it to the query string;
    user / safety_identifier / metadata / prompt_cache_key / extra_headers would send an
    account identifier. Every ** spread is one of the census helpers (X5), so a denied
    keyword cannot ride in through a dict literal or another helper."""
    sites, spreads, bad = 0, 0, []
    for path in _py_files(APP):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and _dotted(node.func).endswith("guarded_llm_create"):
                sites += 1
                where = "%s:%d" % (path.relative_to(REPO).as_posix(), node.lineno)
                for kw in node.keywords:
                    if kw.arg in DENIED_CALL_SITE_KWARGS:
                        bad.append("%s %s=" % (where, kw.arg))
                    elif kw.arg is None:
                        spreads += 1
                        v = kw.value
                        allowed = (
                            (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                             and v.func.id in ALLOWED_SPREAD_CALLS)
                            or (isinstance(v, ast.Name) and v.id in ALLOWED_SPREAD_NAMES)
                        )
                        if not allowed:
                            bad.append("%s **%s is not an allowlisted spread" % (where, ast.unparse(v)))
    assert sites >= 15, "harness: census floor is 15 call sites at dfbda511, saw %d" % sites
    assert spreads >= 31, "harness: census floor is 31 spreads at dfbda511 (15 + 15 + 1), saw %d" % spreads
    assert bad == [], bad


def test_u3c_04_scripts_direct_dispatches_carry_store_false():
    """RED at main: scripts/seed_spec_spine.py and scripts/shadow_experiments.py dispatch
    directly with the same organisation key and send no store field. Ruling R5/F8: each
    dispatch passes store=False as a keyword, or its innermost function assigns
    <spread>['store'] = False as a top-level statement before the first dispatching
    statement (exactly one such write)."""
    bad, seen = [], 0
    for path in _py_files(SCRIPTS):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        owner = _innermost_function(tree)
        for c in [n for n in ast.walk(tree) if isinstance(n, ast.Call) and _is_dispatch(n)]:
            seen += 1
            where = "%s:%d" % (path.relative_to(REPO).as_posix(), c.lineno)
            kw_false = any(
                k.arg == "store" and isinstance(k.value, ast.Constant) and k.value.value is False
                for k in c.keywords
            )
            if kw_false:
                continue
            fn = owner.get(id(c))
            spreads = [k.value.id for k in c.keywords if k.arg is None and isinstance(k.value, ast.Name)]
            ok = False
            if fn is not None and spreads:
                body = _body(fn)
                pre = body[:_first_dispatch_index(body)]
                ok = any(
                    any(_is_store_false_assign(s, name) for s in pre) and len(_store_writes(fn, name)) == 1
                    for name in spreads
                )
            if not ok:
                bad.append(where)
    assert seen >= 2, "harness: expected the two script dispatches, saw %d" % seen
    assert bad == [], "script dispatch without a dominating store=False: %s" % bad


# --------------------------------------------------------------------------
# runtime pins (fake client)
# --------------------------------------------------------------------------
class _CapturingClient:
    def __init__(self):
        self.calls = []
        self.response = object()
        outer = self

        class _Completions:
            async def create(self, **kwargs):
                outer.calls.append(dict(kwargs))
                return outer.response

        self.chat = type("_Chat", (), {"completions": _Completions()})()


def _set_flag(monkeypatch, on):
    monkeypatch.setattr(abs_mod, "llm_preflight_breaker_enabled", lambda: on)
    if on:
        recorded = []
        monkeypatch.setattr(abs_mod, "_openai_dispatch_admission", lambda: (True, True, False))
        monkeypatch.setattr(abs_mod, "openai_record_success", lambda: recorded.append("success"))
        monkeypatch.setattr(abs_mod, "openai_record_failure", lambda: recorded.append("failure"))
        return recorded
    return None


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag_off", "flag_on"])
def test_u3c_05_dispatch_carries_store_false(monkeypatch, flag_on):
    """RED at main: the captured kwargs have no 'store' key."""
    recorded = _set_flag(monkeypatch, flag_on)
    client = _CapturingClient()
    out = asyncio.run(abs_mod.guarded_llm_create(
        client, model="gpt-4o-mini", messages=[{"role": "user", "content": "x"}], max_tokens=5))
    assert out is client.response
    assert len(client.calls) == 1
    sent = client.calls[0]
    assert "store" in sent and sent["store"] is False, sorted(sent)
    assert sent["model"] == "gpt-4o-mini" and sent["max_tokens"] == 5
    if flag_on:
        assert recorded == ["success"], recorded


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag_off", "flag_on"])
def test_u3c_06_caller_store_true_is_overridden(monkeypatch, flag_on):
    """RED at main: store=True is forwarded. Ruling R1: hard override, never honoured."""
    _set_flag(monkeypatch, flag_on)
    client = _CapturingClient()
    asyncio.run(abs_mod.guarded_llm_create(client, model="m", messages=[], store=True))
    assert client.calls[0]["store"] is False


def test_u3c_07_streaming_dispatch_carries_store_false(monkeypatch):
    """RED at main."""
    _set_flag(monkeypatch, False)
    client = _CapturingClient()
    asyncio.run(abs_mod.guarded_llm_create(client, model="m", messages=[], stream=True))
    assert client.calls[0]["stream"] is True and client.calls[0]["store"] is False


def _omit():
    import openai

    return openai.omit


# Rulings R2, X3, X4: extra_body shapes whose "store" entry must arrive as False in the
# captured kwargs and on the wire, the rest of extra_body kept. A Mapping that is not a
# dict (MappingProxyType) is scrubbed into a plain dict; a None entry would be SENT as
# null, and an Omit entry makes the SDK merge drop the body's store key altogether
# (_base_client._merge_mappings removes Omit values), so both become False too.
EXTRA_BODY_SHAPES = {
    "dict_true": lambda: {"store": True, "u3c_keep": 1},
    "mappingproxy_true": lambda: types.MappingProxyType({"store": True, "u3c_keep": 1}),
    "dict_none": lambda: {"store": None, "u3c_keep": 1},
    "dict_omit": lambda: {"store": _omit(), "u3c_keep": 1},
}


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag_off", "flag_on"])
@pytest.mark.parametrize("shape", list(EXTRA_BODY_SHAPES))
def test_u3c_18_extra_body_store_is_forced_false(monkeypatch, shape, flag_on):
    """RED at main: extra_body={'store': True} reaches the client unchanged. Ruling R2: the
    entry is set to False inside the chokepoint; the rest of extra_body is kept. X3: a
    MappingProxyType arrives as a plain dict; X4: a None or Omit entry arrives as False."""
    _set_flag(monkeypatch, flag_on)
    client = _CapturingClient()
    asyncio.run(abs_mod.guarded_llm_create(
        client, model="m", messages=[], extra_body=EXTRA_BODY_SHAPES[shape]()))
    sent = client.calls[0]
    eb = sent.get("extra_body")
    assert type(eb) is dict and eb == {"store": False, "u3c_keep": 1} and eb["store"] is False, (
        type(eb).__name__, eb)
    assert sent.get("store", "ABSENT") is False, sent.get("store", "ABSENT")


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag_off", "flag_on"])
def test_u3c_22_caller_extra_body_is_not_mutated(monkeypatch, flag_on):
    """GUARD (ruling X8): the scrub builds a NEW dict; the caller's extra_body still carries
    store True afterwards (kills an in-place eb['store'] = False, green mutant g07)."""
    _set_flag(monkeypatch, flag_on)
    client = _CapturingClient()
    caller_eb = {"store": True, "u3c_keep": 1}
    asyncio.run(abs_mod.guarded_llm_create(client, model="m", messages=[], extra_body=caller_eb))
    assert caller_eb == {"store": True, "u3c_keep": 1} and caller_eb["store"] is True, caller_eb
    sent_eb = client.calls[0]["extra_body"]
    assert sent_eb is not caller_eb and sent_eb == {"store": False, "u3c_keep": 1}, sent_eb


# --------------------------------------------------------------------------
# end-to-end through the pinned SDK (openai==3.3.1): the request BODY
# --------------------------------------------------------------------------
def _sdk_bodies(monkeypatch, flag_on, **extra):
    import httpx2
    import openai

    _set_flag(monkeypatch, flag_on)
    bodies = []
    canned = {
        "id": "c", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }

    def handler(request):
        bodies.append(json.loads(request.content.decode("utf-8")))
        return httpx2.Response(200, json=canned)

    async def run():
        client = openai.AsyncOpenAI(
            api_key="test-key", base_url="https://u3c.invalid/v1", max_retries=0,
            http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
        )
        return await abs_mod.guarded_llm_create(
            client, model="m", messages=[{"role": "user", "content": "x"}], **extra)

    resp = asyncio.run(run())
    assert resp.choices[0].message.content == "ok"
    assert len(bodies) == 1, bodies
    return bodies[0]


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag_off", "flag_on"])
def test_u3c_09_pinned_sdk_puts_store_false_in_the_request_body(monkeypatch, flag_on):
    """RED at main: the body has no 'store' key, so the request is not sent with
    store=False and may become a stored completion (dashboard Logs)."""
    body = _sdk_bodies(monkeypatch, flag_on)
    assert body.get("store", "ABSENT") is False, body


@pytest.mark.parametrize("flag_on", [False, True], ids=["flag_off", "flag_on"])
@pytest.mark.parametrize("shape", list(EXTRA_BODY_SHAPES))
def test_u3c_19_pinned_sdk_body_store_false_despite_extra_body(monkeypatch, shape, flag_on):
    """RED at main: the pinned SDK merges extra_body OVER the body, so
    extra_body={'store': True} puts store=true on the wire. Ruling R2; X3 (a
    MappingProxyType), X4 (a None entry is sent as null, an Omit entry deletes the key)."""
    body = _sdk_bodies(monkeypatch, flag_on, extra_body=EXTRA_BODY_SHAPES[shape]())
    assert body.get("store", "ABSENT") is False, body
    assert body.get("u3c_keep") == 1, body
