"""BE-HARNESS -- the A1.8 canary truth rule and the signed-in review warm-up. RED file.

Spec set (authoritative, the later wins): s74-state/specs/BE_HARNESS_SPEC.md (sections
2-4 and 6), BE_HARNESS_REVIEW.md (F1-F18) and FABLE_RULINGS_BE_HARNESS.md (B1-B16,
binding). Node ids BHnn follow spec section 6; nodes added or changed by a ruling name
the ruling in their docstring.

Scripts under test, each loaded BY PATH under a private module name (never imported by
its real name): scripts/verify_after_credits.py (the promoted canary) and
scripts/review_warmup.py (new). A missing script is a node FAILURE
("RED: scripts/<name> is absent"), never a collection error.

Driver (the U13 convention, tests/test_s71_u13_harness_auth.py:65-97): main() is called
with sys.argv patched and the module-level `httpx` name replaced by a shim whose Client
forces an httpx.MockTransport (zero network) and records its constructor kwargs. A
SystemExit is caught as rc; any other escaping exception is recorded as
"raised <ClassName>" (never its text). An autouse fixture deletes
HARNESS_SEND_ADMIN_KEY and ADMIN_API_KEY before every node (nine test modules set
ADMIN_API_KEY at import); nodes that need them set them. The admin sentinel is built
at runtime by concatenation (no credential shape). Non-ASCII test data is built with
chr(); this file is pure ASCII.

Exit contract (B3): 0 PASS, 1 FAIL, 3 NO_PRICE, 4 SETUP, 5 CRASH; an rc counts only
when the last stdout line starts with "RESULT:".

Fixtures canary1..canary5 are DERIVED from the five session-74 canary logs (scratchpad
canary/canary{1..5}_*.log, the old script's output): the logged fields (http, success,
the per-product price objects, winner, the stream frame count and its success:true
terminal) are copied; the fields the old script never logged (pros/cons, spec rows,
comparison, metadata) are filled HEALTHY so only the logged fields decide (spec
section 2, B5). Their expected exits (1, 1, 1, 3, 1) are derived, not measured.

RED at base 3b24d182: no scripts/verify_after_credits.py and no scripts/review_warmup.py,
so every node fails with the "absent" message (RED-A). Against the OLD session-69
canary copied to scripts/verify_after_credits.py (RED-B) each docstring says "old:".
"""
from __future__ import annotations

import ast
import copy
import importlib.util
import inspect
import json
import re
import sys
import time
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CANARY = REPO_ROOT / "scripts" / "verify_after_credits.py"
WARMUP = REPO_ROOT / "scripts" / "review_warmup.py"

OPT_IN = "HARNESS_SEND_ADMIN_KEY"
ADMIN_ENV = "ADMIN_API_KEY"
SENTINEL = "be" + "harness-" + "sentinel-" + "x7"
BASE_URL = "http://beh.test"
HEALTH = "/health"
COMPARE = "/api/v1/text/compare"
STREAM = "/api/v1/text/compare/stream"
# canary/run_canary.sh drops every output line matching this (grep -v -i -E).
WRAPPER_FILTER = re.compile(r"api[_-]?key|token|secret|password", re.IGNORECASE)

DEFAULT_BASE = "https://web-production-58776.up.railway.app"
LOG_PAIRS = [
    "iPhone 15 vs Galaxy S24",
    "Dior Sauvage EDP 100ml vs Bleu de Chanel EDP 100ml",
    "Optimum Nutrition Gold Standard Whey vs Dymatize ISO100",
]
PAIRS2 = ("Product A vs Product B", "Product C vs Product D")
PROBE = ("iPhone 15", "Samsung Galaxy S24")
PROBE_PARAMS = {"product_a": PROBE[0], "product_b": PROBE[1], "region": "bahrain", "nocache": "true"}
WARMUP_PAIRS = [
    ("iPhone 15", "Samsung Galaxy S24"),
    ("Bose QuietComfort Ultra", "Sony WH-1000XM5"),
    ("Nivea Soft", "Cetaphil Moisturizing Cream"),
    ("HealthAid Vitamin D3", "NOW Foods Vitamin D-3"),
    ("L'Oreal Revitalift", "Olay Regenerist"),
    ("Tom Ford Tobacco Vanille", "Creed Aventus"),
]
WARMUP_LABELS = [a + " vs " + b for a, b in WARMUP_PAIRS]
EXIT = {"EXIT_PASS": 0, "EXIT_FAIL": 1, "EXIT_NO_PRICE": 3, "EXIT_SETUP": 4, "EXIT_CRASH": 5}
NON_ASCII_A = "Oud " + chr(0x645) + chr(0x64A)
NON_ASCII_LABEL = NON_ASCII_A + " vs Musk B"
# response_builder.py:625 _SPEC_NA_TOKENS = {"n/a", "na", "none", "unknown", "-", ""} (B1)
NA_VARIANTS = ["N/A", "n/a", "NA", "None", "NONE", "Unknown", " unknown ", "-", ""]
TRANSPORT = ["ConnectError", "LocalProtocolError", "ReadTimeout"]
WANT_REASON = {"ConnectError": "transport_ConnectError",
               "LocalProtocolError": "transport_LocalProtocolError",
               "ReadTimeout": "timeout"}
REPORT_KEYS = {"script", "rule", "base", "auth", "started_utc", "rows", "result", "exit"}
COMPARE_ROW_KEYS = {"kind", "label", "http", "ms", "verdict", "reasons", "code", "prices",
                    "amounts", "winner", "spec_rows", "spec_rows_real", "pros", "cons",
                    "comparison_error", "partial", "partial_stage"}
STREAM_ROW_KEYS = {"kind", "label", "http", "ms", "verdict", "reasons", "events", "terminal",
                   "terminal_success"}
WARMUP_REPORT_KEYS = {"script", "rule", "base", "auth", "started_utc", "rows", "ready",
                      "no_price", "failed", "result", "exit"}
WARMUP_ROW_KEYS = {"pair", "run", "http", "verdict", "reasons", "prices", "elapsed_s",
                   "partial", "partial_stage"}
TABLE_ROW_RE = re.compile(r"\b[0-2]/2\b.*\b\d+\.\ds\b")


@pytest.fixture(autouse=True)
def _clean_harness_env(monkeypatch):
    """Every node starts with both variables deleted; nodes set what they need."""
    _env(monkeypatch)


def _env(mp, *, opt_in=None, key=None):
    """Set or delete every variable the scripts read (never inherit them)."""
    for name, value in ((OPT_IN, opt_in), (ADMIN_ENV, key)):
        if value is None:
            mp.delenv(name, raising=False)
        else:
            mp.setenv(name, value)


def _load(path, private):
    if not path.is_file():
        pytest.fail("RED: scripts/%s is absent" % path.name)
    spec = importlib.util.spec_from_file_location("_beh_private_" + private, path)
    assert spec is not None and spec.loader is not None, "cannot load %s" % path
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _canary_fn(name):
    mod = _load(CANARY, "canary")
    fn = getattr(mod, name, None)
    if not callable(fn):
        pytest.fail("RED: verify_after_credits.%s is absent" % name)
    return fn


class _HttpxShim:
    """Stands in for a loaded script's module-level `httpx` name: the overridden
    attributes are recorders, everything else is the real httpx."""

    def __init__(self, **overrides):
        self._overrides = overrides

    def __getattr__(self, name):
        if name in self._overrides:
            return self._overrides[name]
        return getattr(httpx, name)


# ===========================================================================
# Wire-shape builders (spec section 1; response_builder.py:1892-2219)
# ===========================================================================
_DEFAULT = object()
_OMIT = object()
NAMES = ("Product A", "Product B")


def _pending():
    """make_pending_price (price_service.py:1928-1941): no retailer key."""
    return {"amount": None, "currency": "BHD", "unavailable": True, "reason": "pending_genuine"}


def _priced(amount, retailer, **extra):
    price = {"amount": amount, "currency": "BHD", "retailer": retailer, "url": None,
             "in_stock": True, "source_method": "local_bhd", "confidence": 0.9}
    price.update(extra)
    return price


def _row(field, p0, p1, winner=None):
    return {"field": field, "p0_value": p0, "p1_value": p1, "winner": winner}


# 3 rows, 2 real (the battery row is a placeholder).
ROWS_HEALTHY = [_row("display", "6.1 in", "6.2 in", 1), _row("ram", "6 GB", "8 GB", 1),
                _row("battery", "N/A", "N/A")]
# F1 case A (probe_rows2.log): _clean_specs stamps every null as "N/A".
ROWS_ALL_NA = [_row("display", "N/A", "N/A"), _row("ram", "N/A", "N/A"),
               _row("battery", "N/A", "N/A")]
# F1 case D (probe_rows2.log): a raw early-buffer partial ships identity/error rows.
ROWS_IDENTITY = [_row("brand", "Apple", "Samsung"), _row("model", "iPhone 15", "Galaxy S24"),
                 _row("error", "specs extraction failed", "specs extraction failed"),
                 _row("ram_source", "snippet", "snippet")]
ROWS_META = [_row("_search_snippets", "a", "b"), _row("variant", "128GB", "256GB"),
             _row("category", "phone", "phone"), _row("name", "iPhone 15", "Galaxy S24"),
             _row("brand_source", "llm", "llm")]
ROWS_ONE_SIDED = [_row("display", "6.1 in", "N/A"), _row("ram", "unknown", "8 GB"),
                  _row("weight", "-", "167 g")]
ROWS_BLANK = [_row("display", " ", "6.2 in"), _row("ram", None, "8 GB"), _row("cpu", "A16", "")]


def _body(prices=_DEFAULT, *, names=NAMES, winner=_DEFAULT, rows=_DEFAULT, pros=_DEFAULT,
          cons=_DEFAULT, comparison=_DEFAULT, partial=False, partial_stage=None):
    """A build_comparison_response-shaped 200 body: overview.winner/products with
    price, pros, cons; specs {products, specs_comparison.rows}; the legacy products
    alias with the product-level retailer mirror; comparison; metadata."""
    if prices is _DEFAULT:
        prices = (_priced(249.99, "bahrain.sharafdg.com"), _priced(279.0, "xcite.com"))
    if winner is _DEFAULT:
        winner = names[0]
    if rows is _DEFAULT:
        rows = ROWS_HEALTHY
    if pros is _DEFAULT:
        pros = (["Brighter display", "Longer support"], ["More RAM", "Faster charging"])
    if cons is _DEFAULT:
        cons = (["Slower charging"], ["Shorter support"])
    if comparison is _DEFAULT:
        comparison = {"winner_index": 0, "verdict": names[0] + " is the better buy",
                      "confidence": 0.8}
    ov_products, legacy = [], []
    for i in (0, 1):
        price = copy.deepcopy(prices[i])
        retailer = price.get("retailer") if isinstance(price, dict) else None
        amount = price.get("amount") if isinstance(price, dict) else None
        ov_products.append({
            "name": names[i], "price": price, "pros": list(pros[i]), "cons": list(cons[i]),
            "pros_cons": {"pros": list(pros[i])[:4], "cons": list(cons[i])[:4],
                          "is_winner": i == 0}})
        legacy.append({"name": names[i], "price": copy.deepcopy(price), "pros": list(pros[i]),
                       "cons": list(cons[i]), "retailer": retailer, "best_price": amount})
    body = {
        "success": True,
        "query": names[0] + " vs " + names[1],
        "category": "electronics",
        "category_switched": False,
        "overview": {
            "winner": {"product_index": 0, "name": winner, "declaration": "derived fixture",
                       "reason": "derived fixture", "key_tradeoff": "price", "margin": "clear"},
            "products": ov_products},
        "specs": {"products": [{"name": n, "specs": {}} for n in names],
                  "specs_comparison": {"rows": copy.deepcopy(rows)}},
        "products": legacy,
        "metadata": {"partial": partial},
    }
    if partial_stage is not None:
        body["metadata"]["partial_stage"] = partial_stage
    if comparison is not _OMIT:
        body["comparison"] = copy.deepcopy(comparison)
    return body


def _degraded():
    """BH01 / spec section 2: comparison.error, rows [], empty pros/cons, both pending."""
    return _body((_pending(), _pending()), rows=[], pros=([], []), cons=([], []),
                 comparison={"winner_index": 0, "error": "verdict generation unavailable"})


def _no_pros_cons():
    return _body(pros=([], []), cons=([], []))


INCOMPLETE = "Comparison data was incomplete " + chr(0x2014) + " choose different products."


def _envelope(code, error=INCOMPLETE):
    """error_handler.py:113-137."""
    return {"success": False, "error": error, "code": code, "request_id": "req-beh-01"}


AUTH_401 = {"success": False, "error": "Sign in to continue.", "code": "AUTH_REQUIRED",
            "request_id": "req-beh-401"}
AUTH_403 = {"success": False, "error": "Invalid admin key", "code": "HTTP_403",
            "request_id": "req-beh-403"}
STREAM_TIMEOUT = {"success": False, "code": "STREAM_TIMEOUT",
                  "error": "The comparison took too long."}
ERROR_EVENT = {"success": False, "code": "LLM_UNAVAILABLE",
               "error": "The AI service is unavailable."}


def _progress():
    """Ten non-terminal frames (text_routes.py:1032-1055): with settle_complete and
    complete, 12 frames = the 24 event/data lines of canaries 1/3/4/5."""
    return [("status", {"stage": "search", "message": "Finding products"}),
            ("status", {"stage": "extract", "message": "Reading specs"}),
            ("specs", {"products": [{"name": NAMES[0]}, {"name": NAMES[1]}]}),
            ("prices", {"prices": [None, None]}),
            ("reviews", {"reviews": []}),
            ("first_paint", {"overview": {}}),
            ("scores", {"scores": [0.8, 0.7]}),
            ("verdict", {"winner_index": 0}),
            ("settle_update", {"field": "price"}),
            ("confidence_upgrade", {"confidence": 0.9})]


def _stream(terminal=_DEFAULT, *, settle=_DEFAULT, progress=True):
    """settle_complete then complete with the SAME payload
    (structured_comparison_service.py:5100-5101) unless `settle` differs."""
    payload = _body() if terminal is _DEFAULT else terminal
    first = payload if settle is _DEFAULT else settle
    frames = _progress() if progress else []
    return frames + [("settle_complete", first), ("complete", payload)]


def _sse(frames):
    """The wire frame `event: <type>\\ndata: <json>\\n\\n` (text_routes.py:1215)."""
    chunks = []
    for event, data in frames:
        chunks.append("event: " + event + "\ndata: " + json.dumps(data) + "\n\n")
    return "".join(chunks).encode("ascii")


def _lines(frames, *, comments=False):
    """What httpx iter_lines() yields for the frames ("" separators kept, MEASURED in
    probe_mock_semantics.log); with comments, ": ping" lines between blocks."""
    lines = _sse(frames).decode("ascii").splitlines()
    if not comments:
        return lines
    out = [": ping"]
    for line in lines:
        out.append(line)
        if line == "":
            out.append(": ping")
    return out


# ===========================================================================
# MockTransport server + driver
# ===========================================================================
def _kind(request):
    path = request.url.path
    if path == HEALTH:
        return "health"
    if path == STREAM:
        return "stream"
    if path == COMPARE:
        return "q" if "q" in request.url.params else "pair"
    return "other"


class _Server:
    """Answers every request (routes: kind -> callable(request, index)) and records
    kind, path, params, lower-cased headers and the per-request read timeout."""

    def __init__(self, routes, events):
        self.routes = dict(routes)
        self.seen = []
        self.counts = {}
        self.events = events

    def __call__(self, request):
        kind = _kind(request)
        index = self.counts.get(kind, 0)
        self.counts[kind] = index + 1
        timeout = request.extensions.get("timeout") or {}
        self.seen.append({"kind": kind, "path": request.url.path,
                          "params": dict(request.url.params),
                          "headers": {k.lower(): v for k, v in request.headers.items()},
                          "read_timeout": timeout.get("read")})
        self.events.append(("req", kind))
        route = self.routes.get(kind)
        if route is None:
            return httpx.Response(599, json={"success": False, "error": "beh: unrouted",
                                             "code": "BEH_UNROUTED"})
        return route(request, index)

    def of(self, *kinds):
        return [s for s in self.seen if s["kind"] in kinds]

    def compares(self):
        """B9: exact path, so the stream is never counted as a compare."""
        return [s for s in self.seen if s["path"] == COMPARE]


def _json(status, body):
    def route(request, index):
        return httpx.Response(status, json=copy.deepcopy(body))
    return route


def _events(frames, status=200):
    payload = _sse(frames)

    def route(request, index):
        return httpx.Response(status, content=payload,
                              headers={"content-type": "text/event-stream"})
    return route


def _by_q(table):
    def route(request, index):
        status, body = table[request.url.params["q"]]
        return httpx.Response(status, json=copy.deepcopy(body))
    return route


def _by_pair(plan, default=None):
    """plan: product_a -> [(status, body) per run] (the last repeats); others default."""
    counts = {}

    def route(request, index):
        a = request.url.params.get("product_a")
        n = counts.get(a, 0)
        counts[a] = n + 1
        answers = plan.get(a) or [default or (200, _body())]
        status, body = answers[min(n, len(answers) - 1)]
        return httpx.Response(status, json=copy.deepcopy(body))
    return route


def _raise(exc_name, request):
    if exc_name == "ConnectError":
        raise httpx.ConnectError("refused " + SENTINEL, request=request)
    if exc_name == "LocalProtocolError":
        # the h11 shape (h11/_headers.py:166): the raw header value inside the text
        raise httpx.LocalProtocolError("Illegal header value " + repr(SENTINEL + " "),
                                       request=request)
    if exc_name == "ReadTimeout":
        raise httpx.ReadTimeout("read timed out " + SENTINEL, request=request)
    raise RuntimeError("unexpected " + SENTINEL)


def _raise_first(exc_name, rest):
    def route(request, index):
        if index == 0:
            _raise(exc_name, request)
        return rest(request, index)
    return route


def _routes(**over):
    routes = {"health": _json(200, {"status": "healthy", "message": "MYEZ API is running"}),
              "q": _json(200, _body()), "pair": _json(200, _body()),
              "stream": _events(_stream())}
    routes.update(over)
    return routes


class _Run:
    def __init__(self, rc, out, err, server, built, sleeps, events):
        self.rc, self.out, self.err = rc, out, err
        self.server, self.built, self.sleeps, self.events = server, built, sleeps, events

    @property
    def lines(self):
        return [ln for ln in self.out.splitlines() if ln.strip()]

    @property
    def last(self):
        lines = self.lines
        return lines[-1] if lines else ""

    def rows(self, *kinds):
        found = []
        for line in self.lines:
            text = line.strip()
            if not text.startswith("{"):
                continue
            try:
                obj = json.loads(text)
            except ValueError:
                continue
            if isinstance(obj, dict) and (not kinds or obj.get("kind") in kinds):
                found.append(obj)
        return found

    def reasons(self):
        found = []
        for row in self.rows():
            value = row.get("reasons")
            if isinstance(value, (list, tuple)):
                found.extend(value)
        return found


def _drive(mp, capsys, script, argv, routes, *, opt_in=None, key=None, client_error=None):
    _env(mp, opt_in=opt_in, key=key)
    path, private = (CANARY, "canary") if script == "canary" else (WARMUP, "warmup")
    mod = _load(path, private)
    assert hasattr(mod, "httpx"), "%s has no module-level httpx name" % path.name
    events, built, sleeps = [], [], []
    server = _Server(routes, events)
    real_client = httpx.Client

    def _client(*args, **kwargs):
        built.append(dict(kwargs))
        if client_error is not None:
            raise client_error
        kw = dict(kwargs)
        kw["transport"] = httpx.MockTransport(server)
        return real_client(*args, **kw)

    mp.setattr(mod, "httpx", _HttpxShim(Client=_client))
    if script == "warmup":
        assert hasattr(mod, "_sleep"), "review_warmup._sleep is absent (spec section 4)"

        def _rec_sleep(seconds):
            sleeps.append(seconds)
            events.append(("sleep", seconds))
        mp.setattr(mod, "_sleep", _rec_sleep)
    mp.setattr(sys, "argv", [path.name] + list(argv))
    capsys.readouterr()
    try:
        rc = mod.main()
    except SystemExit as exc:
        rc = exc.code
    except Exception as exc:  # noqa: BLE001 - recorded by class name only, never its text
        rc = "raised " + type(exc).__name__
    out, err = capsys.readouterr()
    return _Run(rc, out, err, server, built, sleeps, events)


def _cargs(*extra, pairs=PAIRS2):
    return ["--base", BASE_URL, "--pairs", *pairs, *extra]


def _assert_rc(run, want):
    assert run.rc == want, "rc %r, want %r (last stdout line %s)" % (run.rc, want, ascii(run.last))
    assert run.last.startswith("RESULT:"), (
        "B3: the last stdout line %s does not start with RESULT:" % ascii(run.last))


def _assert_no_sentinel(run, report=None):
    assert run.out.count(SENTINEL) == 0, "the sentinel reached stdout"
    assert run.err.count(SENTINEL) == 0, "the sentinel reached stderr"
    assert run.err.count("Traceback") == 0, "a traceback reached stderr"
    if report is not None and report.exists():
        assert report.read_bytes().count(SENTINEL.encode("ascii")) == 0, (
            "the sentinel reached the report")


def _non_ascii(text):
    return sum(1 for ch in text if ord(ch) > 127)


def _line(run, prefix):
    found = [ln for ln in run.lines if ln.startswith(prefix)]
    assert len(found) == 1, "%d stdout lines start with %r" % (len(found), prefix)
    return found[0]


def _assert_class(report, name, labels):
    """report[name] is a count or a list of labels (spec section 4 leaves the type open)."""
    value = report.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, list, tuple)):
        pytest.fail("warm-up report[%r] is %r: want a count or a list" % (name, value))
    if isinstance(value, int):
        assert value == len(labels), (name, value, labels)
    else:
        got = sorted(" vs ".join(v) if isinstance(v, (list, tuple)) else v for v in value)
        assert got == sorted(labels), (name, got)


# ===========================================================================
# BH01-BH09  canary: the A1.8 rule through main()
# ===========================================================================
def test_BH01_degraded_200_on_every_compare_fails(monkeypatch, capsys):
    """BH01: comparison.error + rows [] + empty pros/cons + both prices pending on every
    compare (q pairs and the probe), healthy stream -> rc 1; a compare row carries
    comparison_error. Old: rc 0 / RESULT: PASS (spec section 2, MEASURED)."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(),
                 _routes(q=_json(200, _degraded()), pair=_json(200, _degraded())))
    _assert_rc(run, 1)
    flagged = [r for r in run.rows("compare", "probe")
               if r.get("comparison_error") and "comparison_error" in (r.get("reasons") or [])]
    assert flagged, "no compare row reports comparison_error: %r" % (
        [r.get("reasons") for r in run.rows()],)


STREAM_RC1 = {
    "BH02_terminal_complete_success_false": lambda: _progress()[:2] + [
        ("settle_complete", STREAM_TIMEOUT), ("complete", STREAM_TIMEOUT)],
    "BH03_terminal_error_event": lambda: _progress()[:2] + [("error", ERROR_EVENT)],
    "BH04_status_frames_only": lambda: _progress()[:2],
    "BH04b_success_terminal_without_pros_cons": lambda: _stream(_no_pros_cons()),
    "BH04c_first_terminal_success_false_last_true": lambda: _stream(settle=STREAM_TIMEOUT),
    "BH04c_first_terminal_payload_degraded_last_healthy": lambda: _stream(
        settle=_no_pros_cons()),
    "BH04d_error_frame_before_success_terminal": lambda: [
        ("status", {"stage": "search"}), ("error", ERROR_EVENT)] + _stream(progress=False),
}


@pytest.mark.parametrize("case", list(STREAM_RC1))
def test_BH02_to_BH04d_stream_rule_fails_the_run(monkeypatch, capsys, case):
    """BH02-BH04 (spec) and BH04b/BH04c/BH04d (B2: every terminal success:true, no error
    frame anywhere, the FIRST terminal's payload held to evaluate_compare): healthy
    compares + that stream -> rc 1 and the stream row is FAIL. Old: rc 0 (events > 0)."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(),
                 _routes(stream=_events(STREAM_RC1[case]())))
    _assert_rc(run, 1)
    stream_rows = run.rows("stream")
    assert len(stream_rows) == 1 and stream_rows[0].get("verdict") == "FAIL", stream_rows


def test_BH05_all_healthy_passes(monkeypatch, capsys):
    """BH05 GUARD: healthy priced compares + a success stream -> rc 0, last line
    "RESULT: PASS". Old: PASS (green in RED-B)."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(), _routes())
    _assert_rc(run, 0)
    assert run.last == "RESULT: PASS", ascii(run.last)


IPHONE = ("iPhone 15", "Galaxy S24")
DIOR = ("Sauvage", "Bleu de Chanel")
WHEY = ("Gold Standard Whey", "ISO100")
C4_IPHONE_PRICE = {
    "amount": 249.99, "currency": "BHD", "retailer": "bahrain.sharafdg.com",
    "url": ("https://bahrain.sharafdg.com/product/"
            "apple-iphone-15-128gb-black-with-facetime-middle-east-version/"),
    "in_stock": True, "estimated": False, "source_method": "local_bhd",
    "title": "Apple iPhone 15 (128GB) - Black Middle East Version with FaceTime",
    "confidence": 0.9}
C4_DIOR_PRICE = {
    "amount": 29.26, "currency": "BHD", "retailer": "Whatnot", "url": None, "in_stock": True,
    "source_method": "converted_usd", "confidence": 1.0, "title": "Sauvage by Dior 100ml EDP",
    "concentration": "EDP", "size": "100ml"}


def _canary_fixture(run_id):
    """DERIVED from scratchpad canary/<run_id>_*.log: the q rows as logged (http, the two
    price objects, winner), the probe = that run's iPhone row, the stream = 12 frames
    (canary2: 4 frames) ending success:true with the iPhone row's payload (canary2's
    iPhone was a 400: its stream payload is the both-pending iPhone body)."""
    pend = (_pending(), _pending())
    insufficient = (400, _envelope("INSUFFICIENT_DATA"))
    iphone_pending = (200, _body(pend, names=IPHONE, winner="iPhone 15"))
    whey_short = (200, _body(pend, names=WHEY, winner="Gold Standard Whey"))
    whey_long = (200, _body(pend, names=WHEY, winner="Optimum Nutrition Gold Standard Whey"))
    if run_id in ("canary1", "canary3"):
        q = [iphone_pending, insufficient, whey_short if run_id == "canary1" else whey_long]
        payload = iphone_pending[1]
    elif run_id == "canary2":
        q = [insufficient, insufficient, whey_short]
        payload = iphone_pending[1]
    elif run_id == "canary4":
        q = [(200, _body((C4_IPHONE_PRICE, _pending()), names=IPHONE, winner="iPhone 15")),
             (200, _body((C4_DIOR_PRICE, _pending()), names=DIOR, winner="Dior Sauvage")),
             whey_long]
        payload = q[0][1]
    else:  # canary5: all six prices pending_genuine (after U3c), old script rc 0
        q = [iphone_pending,
             (200, _body(pend, names=DIOR, winner="Chanel Bleu de Chanel")),
             whey_short]
        payload = iphone_pending[1]
    if run_id == "canary2":
        frames = _progress()[:2] + [("settle_complete", payload), ("complete", payload)]
    else:
        frames = _stream(payload)
    return {"q": dict(zip(LOG_PAIRS, q)), "probe": q[0], "frames": frames}


@pytest.mark.parametrize("run_id,want", [("canary1", 1), ("canary2", 1), ("canary3", 1),
                                         ("canary4", 3), ("canary5", 1)])
def test_BH06_canary_log_fixtures(monkeypatch, capsys, run_id, want):
    """BH06 (spec section 2 table + B4 canary5; DERIVED expected exits): 1, 1, 1, 3, 1.
    canary5 is all-pending -> R11 no_price_in_run -> 1 (B4). Old: 1, 1, 1, 0, 0 (so
    canary4 and canary5 are RED-B discriminators, canary1-3 stay green)."""
    fx = _canary_fixture(run_id)
    run = _drive(monkeypatch, capsys, "canary", _cargs(pairs=LOG_PAIRS),
                 _routes(q=_by_q(fx["q"]), pair=_json(*fx["probe"]),
                         stream=_events(fx["frames"])))
    _assert_rc(run, want)
    if run_id == "canary4":
        assert run.last == "RESULT: FAIL fail=0 no_price=1", ascii(run.last)


@pytest.mark.parametrize("where,want", [("nowhere", 1), ("stream_first_terminal_only", 3),
                                        ("probe_only", 3)])
def test_BH06b_run_rule_R11_no_price_in_run(monkeypatch, capsys, where, want):
    """B4 R11: no positive amount in the run (q pairs + probe + the stream's FIRST
    terminal) -> rc 1; one amount anywhere in the run makes it exit 3. Old: rc 0."""
    pend = _body((_pending(), _pending()))
    one = _body((_priced(249.99, "bahrain.sharafdg.com"), _pending()))
    routes = _routes(q=_json(200, pend), pair=_json(200, one if where == "probe_only" else pend),
                     stream=_events(_stream(one if where == "stream_first_terminal_only"
                                            else pend)))
    run = _drive(monkeypatch, capsys, "canary", _cargs(), routes)
    _assert_rc(run, want)


def test_BH07_probe_and_stream_are_app_shaped(monkeypatch, capsys):
    """BH07 (B9 exact path): health, the q pairs (q, nocache=true, region=bahrain), then
    exactly ONE product_a/product_b compare {iPhone 15, Samsung Galaxy S24, bahrain,
    nocache=true} with no q, then ONE stream with the same params. Old: no probe."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(pairs=LOG_PAIRS), _routes())
    assert [s["params"] for s in run.server.of("q")] == [
        {"q": p, "nocache": "true", "region": "bahrain"} for p in LOG_PAIRS]
    assert [s["params"] for s in run.server.of("pair")] == [PROBE_PARAMS], (
        "no app-shaped probe compare was requested")
    assert len(run.server.compares()) == len(LOG_PAIRS) + 1
    assert [s["params"] for s in run.server.of("stream")] == [PROBE_PARAMS]
    assert [s["kind"] for s in run.server.seen] == (
        ["health"] + ["q"] * len(LOG_PAIRS) + ["pair", "stream"])


def test_BH07b_probe_flag_sets_the_pair(monkeypatch, capsys):
    """BH07b (spec section 3 CLI): --probe A B drives both the probe and the stream.
    Old: argparse rejects --probe."""
    run = _drive(monkeypatch, capsys, "canary", _cargs("--probe", "Pixel 9", "iPhone 16"),
                 _routes())
    want = {"product_a": "Pixel 9", "product_b": "iPhone 16", "region": "bahrain",
            "nocache": "true"}
    assert [s["params"] for s in run.server.of("pair")] == [want], (
        "no --probe compare was requested (rc %r)" % (run.rc,))
    assert [s["params"] for s in run.server.of("stream")] == [want]
    _assert_rc(run, 0)


def test_BH08_degraded_probe_fails_the_run(monkeypatch, capsys):
    """BH08: healthy q pairs, a degraded probe -> rc 1, the probe row FAIL. Old: rc 0."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(), _routes(pair=_json(200, _degraded())))
    _assert_rc(run, 1)
    probes = run.rows("probe")
    assert len(probes) == 1 and probes[0].get("verdict") == "FAIL", probes


@pytest.mark.parametrize("rows_id", ["rows_empty", "rows_all_na", "rows_identity_error_source"])
def test_BH09_spec_table_without_a_real_row_fails(monkeypatch, capsys, rows_id):
    """BH09 + B1 (real-shape fixtures, B9): a q pair whose specs dict has both keys but
    rows [] / all-"N/A" rows / identity+error+_source rows only -> rc 1, that row
    carries no_spec_rows and spec_rows_real 0. Old: rc 0 (len of the specs dict)."""
    rows = {"rows_empty": [], "rows_all_na": ROWS_ALL_NA,
            "rows_identity_error_source": ROWS_IDENTITY}[rows_id]
    table = {PAIRS2[0]: (200, _body(rows=rows)), PAIRS2[1]: (200, _body())}
    run = _drive(monkeypatch, capsys, "canary", _cargs(), _routes(q=_by_q(table)))
    _assert_rc(run, 1)
    bad = [r for r in run.rows("compare") if r.get("label") == PAIRS2[0]]
    assert len(bad) == 1 and "no_spec_rows" in (bad[0].get("reasons") or []), bad
    assert bad[0].get("spec_rows") == len(rows) and bad[0].get("spec_rows_real") == 0, bad


# ===========================================================================
# BH10-BH19  canary: auth, setup exits, transport errors, report, ASCII
# ===========================================================================
def test_BH10_not_opted_in_sends_no_admin_header(monkeypatch, capsys):
    """BH10 (key set, opt-in unset): httpx.Client(timeout=150) only, no request carries
    x-admin-key. Old: green."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(), _routes(), key=SENTINEL)
    assert run.server.seen, run.rc
    assert all("x-admin-key" not in s["headers"] for s in run.server.seen)
    assert run.built == [{"timeout": 150}], run.built


def test_BH11_env_opt_in_sends_the_key_on_every_request(monkeypatch, capsys):
    """BH11: HARNESS_SEND_ADMIN_KEY=1 -> health, compares and stream all carry the key;
    the key never reaches stdout or stderr. Old: green."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(), _routes(), opt_in="1", key=SENTINEL)
    assert {"health", "q", "stream"} <= {s["kind"] for s in run.server.seen}, run.rc
    assert all(s["headers"].get("x-admin-key") == SENTINEL for s in run.server.seen)
    _assert_no_sentinel(run)


def test_BH12_send_admin_key_flag_opts_in(monkeypatch, capsys):
    """BH12: --send-admin-key with the env opt-in unset -> the client carries the header
    and every request sends it. Old: argparse rejects the flag (rc 2, no request)."""
    run = _drive(monkeypatch, capsys, "canary", _cargs("--send-admin-key"), _routes(),
                 key=SENTINEL)
    assert run.server.seen, "no request was made (rc %r)" % (run.rc,)
    assert all(s["headers"].get("x-admin-key") == SENTINEL for s in run.server.seen)
    assert run.built == [{"timeout": 150, "headers": {"X-Admin-Key": SENTINEL}}], (
        sorted(run.built[0]) if run.built else run.built)
    _assert_rc(run, 0)


@pytest.mark.parametrize("mode", ["env_key_deleted", "env_key_empty", "flag_key_deleted"])
def test_BH13_opted_in_without_the_variable_is_setup_exit_4(monkeypatch, capsys, mode):
    """BH13 (B3 exit 4): opted in with ADMIN_API_KEY deleted or empty -> rc 4, NO request,
    stdout names the variable (name only) and ends "RESULT: FAIL
    setup=admin_variable_missing" (a line the wrapper filter keeps). Old: runs anonymous."""
    argv = _cargs("--send-admin-key") if mode == "flag_key_deleted" else _cargs()
    run = _drive(monkeypatch, capsys, "canary", argv, _routes(),
                 opt_in=None if mode == "flag_key_deleted" else "1",
                 key="" if mode == "env_key_empty" else None)
    _assert_rc(run, 4)
    assert run.server.seen == [], [s["kind"] for s in run.server.seen]
    assert "ADMIN_API_KEY" in run.out
    assert run.last == "RESULT: FAIL setup=admin_variable_missing", ascii(run.last)
    assert not WRAPPER_FILTER.search(run.last)


def test_BH14_401_on_the_first_compare_stops_with_setup_exit_4(monkeypatch, capsys):
    """BH14 (B3, B9 exact path): AUTH_REQUIRED 401 on the first compare -> rc 4 after
    exactly ONE compare request, no stream, the --send-admin-key hint, last line
    "RESULT: FAIL setup=auth_401". Old: runs on, rc 1."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(), _routes(q=_json(401, AUTH_401)))
    _assert_rc(run, 4)
    assert len(run.server.compares()) == 1, [s["params"] for s in run.server.compares()]
    assert run.server.of("stream") == []
    assert "--send-admin-key" in run.out
    assert run.last == "RESULT: FAIL setup=auth_401", ascii(run.last)


def test_BH14b_401_on_the_stream_is_setup_exit_4(monkeypatch, capsys):
    """BH14b (spec section 3: 401 on any compare/stream): healthy compares, 401 stream ->
    rc 4, "RESULT: FAIL setup=auth_401". Old: rc 1."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(),
                 _routes(stream=_json(401, AUTH_401)))
    _assert_rc(run, 4)
    assert run.last == "RESULT: FAIL setup=auth_401", ascii(run.last)


def test_BH15_403_on_the_first_compare_stops_with_setup_exit_4(monkeypatch, capsys):
    """BH15: a wrong key's 403 on the first compare -> rc 4, one compare, the hint,
    "RESULT: FAIL setup=auth_403"; the key never printed. Old: runs on, rc 1."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(), _routes(q=_json(403, AUTH_403)),
                 opt_in="1", key=SENTINEL)
    _assert_rc(run, 4)
    assert len(run.server.compares()) == 1
    assert "--send-admin-key" in run.out
    assert run.last == "RESULT: FAIL setup=auth_403", ascii(run.last)
    _assert_no_sentinel(run)


@pytest.mark.parametrize("exc_name", TRANSPORT)
def test_BH16_transport_error_is_a_row_and_never_leaks(monkeypatch, capsys, exc_name):
    """BH16 + B7: opted in; the first compare raises <exc>("... " + sentinel) -> rc 1, a
    row reason transport_<Class> (ReadTimeout: timeout), the run goes on, and the
    sentinel is absent from stdout and stderr (no traceback). Old: the error escapes."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(),
                 _routes(q=_raise_first(exc_name, _json(200, _body()))),
                 opt_in="1", key=SENTINEL)
    _assert_rc(run, 1)
    assert WANT_REASON[exc_name] in run.reasons(), run.reasons()
    assert len(run.server.of("stream")) == 1
    _assert_no_sentinel(run)


@pytest.mark.parametrize("exc_name", TRANSPORT)
def test_BH16r_transport_error_never_reaches_the_report(monkeypatch, capsys, tmp_path,
                                                        exc_name):
    """BH16r (B7: stdout, stderr AND the report): as BH16 with --report. Old: argparse."""
    report = tmp_path / "canary.json"
    run = _drive(monkeypatch, capsys, "canary", _cargs("--report", str(report)),
                 _routes(q=_raise_first(exc_name, _json(200, _body()))),
                 opt_in="1", key=SENTINEL)
    _assert_rc(run, 1)
    assert report.is_file(), "no report written"
    _assert_no_sentinel(run, report)


def test_BH16c_client_construction_failure_is_a_crash_exit_5(monkeypatch, capsys):
    """B7: the Client constructor raises UnicodeEncodeError carrying the sentinel (a
    non-ASCII key, httpx/_models.py:82) -> rc 5, last line
    "RESULT: FAIL error=UnicodeEncodeError", no request, no traceback, no sentinel.
    Old: the error escapes main()."""
    exc = UnicodeEncodeError("ascii", "k" + SENTINEL, 0, 1, "bad header " + SENTINEL)
    run = _drive(monkeypatch, capsys, "canary", _cargs(), _routes(), opt_in="1", key=SENTINEL,
                 client_error=exc)
    _assert_rc(run, 5)
    assert run.last == "RESULT: FAIL error=UnicodeEncodeError", ascii(run.last)
    assert run.server.seen == []
    _assert_no_sentinel(run)


def test_BH16x_unexpected_exception_never_leaks(monkeypatch, capsys):
    """B7: a non-httpx exception carrying the sentinel on the first compare -> a RESULT:
    FAIL line (rc 1 or 5), no traceback, no sentinel. Old: escapes main()."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(),
                 _routes(q=_raise_first("RuntimeError", _json(200, _body()))),
                 opt_in="1", key=SENTINEL)
    assert run.rc in (1, 5), run.rc
    assert run.last.startswith("RESULT: FAIL"), ascii(run.last)
    _assert_no_sentinel(run)


def test_BH17_read_timeout_is_reason_timeout_and_the_run_continues(monkeypatch, capsys):
    """BH17: ReadTimeout on the 2nd of 3 q pairs -> that row's reason is timeout; the 3rd
    pair, the probe and the stream are still requested; rc 1. Old: escapes."""
    pairs = ("P1 vs Q1", "P2 vs Q2", "P3 vs Q3")

    def q_route(request, index):
        if index == 1:
            raise httpx.ReadTimeout("read timed out", request=request)
        return httpx.Response(200, json=_body())
    run = _drive(monkeypatch, capsys, "canary", _cargs(pairs=pairs), _routes(q=q_route))
    _assert_rc(run, 1)
    timed = [r.get("label") for r in run.rows("compare") if "timeout" in (r.get("reasons") or [])]
    assert timed == [pairs[1]], timed
    assert (len(run.server.of("q")), len(run.server.of("pair")),
            len(run.server.of("stream"))) == (3, 1, 1)


@pytest.mark.parametrize("state", ["opted_in", "not_opted_in"])
def test_BH18_report_file(monkeypatch, capsys, tmp_path, state):
    """BH18: --report <new dirs>/canary.json -> parent dirs created; ASCII, LF; keys
    script/rule/base/auth/started_utc/rows/result/exit; rule A1.8-v1; auth admin|none;
    rows = 1 + len(pairs) + 2; exit == rc; no sentinel. Old: argparse."""
    report = tmp_path / "nested" / "dir" / "canary.json"
    run = _drive(monkeypatch, capsys, "canary", _cargs("--report", str(report)), _routes(),
                 opt_in="1" if state == "opted_in" else None, key=SENTINEL)
    _assert_rc(run, 0)
    assert report.is_file(), "no report written"
    raw = report.read_bytes()
    assert sum(1 for b in raw if b > 127) == 0 and raw.count(b"\r") == 0
    assert raw.count(SENTINEL.encode("ascii")) == 0
    data = json.loads(raw.decode("ascii"))
    assert REPORT_KEYS <= set(data), sorted(REPORT_KEYS - set(data))
    assert data["rule"] == "A1.8-v1"
    assert data["auth"] == ("admin" if state == "opted_in" else "none")
    assert data["base"] == BASE_URL
    assert data["exit"] == 0
    assert len(data["rows"]) == 1 + len(PAIRS2) + 2


def test_BH19_stdout_and_report_are_ascii(monkeypatch, capsys, tmp_path):
    """BH19: a --pairs label with chr(0x645) chr(0x64a) -> every stdout character and
    every report byte < 128. Old: ensure_ascii=False on stdout."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(pairs=(NON_ASCII_LABEL,)), _routes())
    assert run.out.strip(), "no stdout (rc %r)" % (run.rc,)
    assert _non_ascii(run.out) == 0, "%d non-ASCII characters on stdout" % _non_ascii(run.out)
    report = tmp_path / "r.json"
    run = _drive(monkeypatch, capsys, "canary",
                 _cargs("--report", str(report), pairs=(NON_ASCII_LABEL,)), _routes())
    assert report.is_file(), "no report written (rc %r)" % (run.rc,)
    raw = report.read_bytes()
    assert sum(1 for b in raw if b > 127) == 0, "non-ASCII bytes in the report"
    assert _non_ascii(run.out) == 0


# ===========================================================================
# BH20-BH22  the rule functions
# ===========================================================================
def _b_specs_missing():
    body = _body()
    del body["specs"]
    return body


def _b_winner(name):
    body = _body()
    body["overview"]["winner"]["name"] = name
    return body


def _b_no_winner():
    body = _body()
    del body["overview"]["winner"]
    return body


def _b_products(n):
    body = _body()
    products = body["overview"]["products"]
    body["overview"]["products"] = products[:1] if n == 1 else products + [copy.deepcopy(products[0])]
    return body


def _b_legacy_retailer(where):
    """Product 1 pending; a retailer appears only on the legacy alias (R9 reads it)."""
    body = _body((_priced(249.99, "bahrain.sharafdg.com"), _pending()))
    if where == "product":
        body["products"][1]["retailer"] = "Lulu Hypermarket"
    else:
        body["products"][1]["price"]["retailer"] = "Lulu Hypermarket"
    return body


def _bad_amount(amount):
    return _body((_priced(amount, "Whatnot"), _priced(279.0, "xcite.com")))


RULE_CASES = [
    ("perfect", 200, lambda: _body(), "PASS", None),
    ("comparison_error_truthy", 200, lambda: _body(
        comparison={"winner_index": 0, "error": "verdict generation unavailable"}),
     "FAIL", "comparison_error"),
    ("comparison_error_empty_string", 200, lambda: _body(
        comparison={"winner_index": 0, "verdict": "A", "error": ""}), "PASS", None),
    ("comparison_error_none", 200, lambda: _body(
        comparison={"winner_index": 0, "verdict": "A", "error": None}), "PASS", None),
    ("comparison_missing", 200, lambda: _body(comparison=_OMIT), "FAIL", "comparison_missing"),
    ("comparison_not_a_dict", 200, lambda: _body(comparison="A wins"), "FAIL",
     "comparison_missing"),
    ("rows_empty_two_key_specs", 200, lambda: _body(rows=[]), "FAIL", "no_spec_rows"),
    ("rows_all_na_B1", 200, lambda: _body(rows=ROWS_ALL_NA), "FAIL", "no_spec_rows"),
    ("rows_identity_error_source_B1", 200, lambda: _body(rows=ROWS_IDENTITY), "FAIL",
     "no_spec_rows"),
    ("rows_meta_fields_B1", 200, lambda: _body(rows=ROWS_META), "FAIL", "no_spec_rows"),
    ("rows_one_sided_placeholder_B1", 200, lambda: _body(rows=ROWS_ONE_SIDED), "FAIL",
     "no_spec_rows"),
    ("rows_blank_or_null_values_B1", 200, lambda: _body(rows=ROWS_BLANK), "FAIL",
     "no_spec_rows"),
    ("rows_one_real_among_placeholders_B1", 200, lambda: _body(
        rows=ROWS_ALL_NA + ROWS_IDENTITY + [_row("weight", "171 g", "167 g", 1)]), "PASS", None),
    ("specs_missing", 200, _b_specs_missing, "FAIL", "no_spec_rows"),
    ("pros_empty_on_product_1", 200, lambda: _body(pros=(["Bright"], [])), "FAIL", "no_pros"),
    ("cons_blank_on_product_0", 200, lambda: _body(cons=([" "], ["Short support"])), "FAIL",
     "no_cons"),
    ("both_pending_soft", 200, lambda: _body((_pending(), _pending())), "NO_PRICE",
     "no_price_amount"),
    ("one_amount_passes", 200, lambda: _body(
        (_priced(249.99, "bahrain.sharafdg.com"), _pending())), "PASS", None),
    ("retailer_amount_none", 200, lambda: _bad_amount(None), "FAIL", "retailer_without_amount"),
    ("retailer_amount_zero", 200, lambda: _bad_amount(0), "FAIL", "retailer_without_amount"),
    ("retailer_amount_true", 200, lambda: _bad_amount(True), "FAIL", "retailer_without_amount"),
    ("retailer_amount_string", 200, lambda: _bad_amount("249.99"), "FAIL",
     "retailer_without_amount"),
    ("retailer_amount_negative", 200, lambda: _bad_amount(-5.0), "FAIL",
     "retailer_without_amount"),
    ("retailer_amount_nan", 200, lambda: _bad_amount(float("nan")), "FAIL",
     "retailer_without_amount"),
    ("retailer_amount_inf", 200, lambda: _bad_amount(float("inf")), "FAIL",
     "retailer_without_amount"),
    ("legacy_product_retailer_null_amount", 200, lambda: _b_legacy_retailer("product"), "FAIL",
     "retailer_without_amount"),
    ("legacy_price_retailer_null_amount", 200, lambda: _b_legacy_retailer("price"), "FAIL",
     "retailer_without_amount"),
    ("amount_marked_unavailable_B6", 200, lambda: _body((
        {"amount": 5.0, "currency": "BHD", "unavailable": True, "reason": "pending_genuine"},
        _pending())), "NO_PRICE", "no_price_amount"),
    ("amount_estimated_B6", 200, lambda: _body((
        {"amount": 5.0, "currency": "BHD", "source_method": "estimated", "estimated": True,
         "confidence": 0.3}, _pending())), "NO_PRICE", "no_price_amount"),
    ("amount_unavailable_with_retailer_B6", 200, lambda: _body((
        _priced(5.0, "Whatnot", unavailable=True), _pending())), "FAIL",
     "retailer_without_amount"),
    ("amount_estimated_with_retailer_B6", 200, lambda: _body((
        _priced(5.0, "Whatnot", source_method="estimated", estimated=True), _pending())),
     "FAIL", "retailer_without_amount"),
    ("price_none_B6", 200, lambda: _body((None, _pending())), "NO_PRICE", "no_price_amount"),
    ("price_string_B6", 200, lambda: _body(("12.5 BHD", _pending())), "NO_PRICE",
     "no_price_amount"),
    ("content_unavailable_200", 200, lambda: _envelope(
        "CONTENT_UNAVAILABLE", "No product content was found."), "FAIL", "not_success"),
    ("http_400_envelope", 400, lambda: _envelope("INSUFFICIENT_DATA"), "FAIL", "http_400"),
    ("http_503", 503, lambda: _envelope("LLM_UNAVAILABLE", "The AI service is unavailable."),
     "FAIL", "http_503"),
    ("winner_name_empty", 200, lambda: _b_winner(""), "FAIL", "no_winner"),
    ("winner_name_blank", 200, lambda: _b_winner("   "), "FAIL", "no_winner"),
    ("winner_missing", 200, _b_no_winner, "FAIL", "no_winner"),
    ("products_one", 200, lambda: _b_products(1), "FAIL", "products_shape"),
    ("products_three", 200, lambda: _b_products(3), "FAIL", "products_shape"),
    ("non_json_text", 200, lambda: "<html>Bad gateway</html>", "FAIL", "non_json"),
    ("non_json_none", 200, lambda: None, "FAIL", "non_json"),
    ("non_json_list", 200, lambda: [1, 2], "FAIL", "non_json"),
    ("both_pending_and_no_pros_hard_dominates", 200, lambda: _body(
        (_pending(), _pending()), pros=([], ["Cheaper"])), "FAIL", "no_pros"),
    ("u13_h10_degraded_B10", 200, lambda: {
        "success": True, "products": [], "overview": {"winner": {"name": "u13"}}}, "FAIL",
     "products_shape"),
    ("empty_object_B10", 200, lambda: {}, "FAIL", "not_success"),
]


@pytest.mark.parametrize("case", RULE_CASES, ids=[c[0] for c in RULE_CASES])
def test_BH20_evaluate_compare_table(case):
    """BH20 (+B1 real rows, +B6 amounts, +B10 robustness): evaluate_compare(status, body)
    -> {verdict, reasons, ...}; FAIL on any hard reason, NO_PRICE iff no_price_amount is
    the only reason, PASS iff none. Old: evaluate_compare absent."""
    name, status, factory, verdict, reason = case
    evaluate = _canary_fn("evaluate_compare")
    res = evaluate(status, factory())
    assert isinstance(res, dict), type(res)
    reasons = list(res.get("reasons") or [])
    assert res.get("verdict") == verdict, "%s: verdict %r, reasons %r" % (
        name, res.get("verdict"), reasons)
    if reason is None:
        assert reasons == [], reasons
    else:
        assert reason in reasons, reasons
    if verdict == "NO_PRICE":
        assert reasons == ["no_price_amount"], reasons
    if name == "http_400_envelope":
        assert res.get("code") == "INSUFFICIENT_DATA", res


@pytest.mark.parametrize("token", NA_VARIANTS, ids=["tok%d" % i for i in range(len(NA_VARIANTS))])
def test_BH20b_every_na_token_is_a_placeholder(token):
    """B1: _SPEC_NA_TOKENS (response_builder.py:625), stripped and case-folded: a table
    whose only row is <token>|<token> has no real row -> no_spec_rows."""
    evaluate = _canary_fn("evaluate_compare")
    res = evaluate(200, _body(rows=[_row("display", token, token)]))
    assert res.get("verdict") == "FAIL" and "no_spec_rows" in (res.get("reasons") or []), res


STREAM_RULE_CASES = [
    ("settle_and_complete_success_pass", 200, lambda: _lines(_stream()), "PASS", None),
    ("comment_lines_ignored", 200, lambda: _lines(_stream(), comments=True), "PASS", None),
    ("complete_success_false_S4", 200, lambda: _lines(_progress()[:2] + [
        ("settle_complete", STREAM_TIMEOUT), ("complete", STREAM_TIMEOUT)]), "FAIL",
     "stream_terminal_not_success"),
    ("error_event_last_S3", 200, lambda: _lines(_progress()[:2] + [("error", ERROR_EVENT)]),
     "FAIL", "stream_error_event"),
    ("no_terminal_S2", 200, lambda: _lines(_progress()), "FAIL", "stream_no_terminal"),
    ("http_401_S1", 401, lambda: [], "FAIL", "http_401"),
    ("error_frame_before_success_terminal_B2", 200, lambda: _lines(
        [("status", {"stage": "search"}), ("error", ERROR_EVENT)] + _stream(progress=False)),
     "FAIL", "stream_error_event"),
    ("first_terminal_not_success_last_success_B2", 200, lambda: _lines(
        _stream(settle=STREAM_TIMEOUT)), "FAIL", "stream_terminal_not_success"),
    ("first_terminal_payload_degraded_last_healthy_B2", 200, lambda: _lines(
        _stream(settle=_no_pros_cons())), "FAIL", "stream_no_pros"),
    ("success_terminal_without_pros_cons_BH04b", 200, lambda: _lines(
        _stream(_no_pros_cons())), "FAIL", "stream_no_pros"),
    ("success_terminal_all_na_rows_B2", 200, lambda: _lines(
        _stream(_body(rows=ROWS_ALL_NA))), "FAIL", "stream_no_spec_rows"),
    ("success_terminal_both_pending_soft_B2", 200, lambda: _lines(
        _stream(_body((_pending(), _pending())))), "NO_PRICE", "stream_no_price_amount"),
    ("u13_h10_complete_data_empty_B10", 200, lambda: ["event: complete", "data: {}", ""],
     "FAIL", "stream_terminal_not_success"),
]


@pytest.mark.parametrize("case", STREAM_RULE_CASES, ids=[c[0] for c in STREAM_RULE_CASES])
def test_BH21_evaluate_stream_table(case):
    """BH21 + B2: evaluate_stream(status, lines): S1 http_<n>; S2 stream_no_terminal; S3
    stream_error_event (an error frame ANYWHERE); S4 stream_terminal_not_success (EVERY
    terminal); S5 evaluate_compare(200, FIRST terminal data) with a stream_ prefix,
    NO_PRICE soft. Lines starting ':' are ignored. Old: evaluate_stream absent."""
    name, status, factory, verdict, reason = case
    evaluate = _canary_fn("evaluate_stream")
    res = evaluate(status, factory())
    assert isinstance(res, dict), type(res)
    reasons = list(res.get("reasons") or [])
    assert res.get("verdict") == verdict, "%s: verdict %r, reasons %r" % (
        name, res.get("verdict"), reasons)
    if reason is None:
        assert reasons == [], reasons
    else:
        assert reason in reasons, reasons


def test_BH22_harness_auth_headers_env_parity_and_opt_in_argument(monkeypatch):
    """BH22: _harness_auth_headers() keeps the env-only contract (U13 H07; opt-in values
    1/true/yes/on, case and space insensitive) and _harness_auth_headers(opt_in=True)
    sends the key with the env opt-in unset. Old: no opt_in parameter."""
    mod = _load(CANARY, "canary")
    helper = getattr(mod, "_harness_auth_headers", None)
    assert callable(helper), "_harness_auth_headers is absent"
    for value in ("1", "true", " TRUE ", "Yes", "on"):
        _env(monkeypatch, opt_in=value, key=SENTINEL)
        assert helper() == {"X-Admin-Key": SENTINEL}, ascii(value)
    for value in (None, "", "0", "false", "off", "no"):
        _env(monkeypatch, opt_in=value, key=SENTINEL)
        assert helper() == {}, ascii(value)
    _env(monkeypatch, opt_in=None, key=SENTINEL)
    try:
        got = helper(opt_in=True)
    except TypeError:
        got = TypeError
    if got is TypeError:
        pytest.fail("RED: _harness_auth_headers(opt_in) unsupported")
    assert got == {"X-Admin-Key": SENTINEL}
    assert helper(opt_in=False) == {}


# ===========================================================================
# BH23-BH29  canary: module API, row fields, health, U13 input, timeouts, partial
# ===========================================================================
def test_BH23_canary_module_api_and_hygiene():
    """Spec section 3 API + B3 constants: EXIT_PASS 0, EXIT_FAIL 1, EXIT_NO_PRICE 3,
    EXIT_SETUP 4, EXIT_CRASH 5; DEFAULT_BASE / DEFAULT_PAIRS unchanged; DEFAULT_PROBE;
    main(argv=None); module-level `import httpx`, never `from httpx import`; no logging
    setup (F7); pure ASCII; the docstring keeps the railway-run invocation.
    Old: EXIT_* absent."""
    mod = _load(CANARY, "canary")
    for name, value in EXIT.items():
        got = getattr(mod, name, None)
        assert got == value and not isinstance(got, bool), "%s = %r (want %r, B3)" % (
            name, got, value)
    assert mod.DEFAULT_BASE == DEFAULT_BASE
    assert list(mod.DEFAULT_PAIRS) == LOG_PAIRS
    assert tuple(getattr(mod, "DEFAULT_PROBE", ())) == PROBE
    for name in ("evaluate_compare", "evaluate_stream", "_harness_auth_headers", "main"):
        assert callable(getattr(mod, name, None)), name
    assert "argv" in inspect.signature(mod.main).parameters
    assert "railway run -s web" in (mod.__doc__ or "")
    src = CANARY.read_bytes()
    assert sum(1 for b in src if b > 127) == 0, "scripts/verify_after_credits.py is not ASCII"
    tree = ast.parse(src.decode("ascii"))
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                and (n.module or "").split(".")[0] == "httpx"]
    assert any(isinstance(n, ast.Import) and any(a.name == "httpx" and a.asname is None
                                                 for a in n.names) for n in tree.body)
    assert src.count(b"basicConfig") == 0


def test_BH24_rows_carry_the_section_3_fields(monkeypatch, capsys):
    """Spec section 3 output + B1 (spec_rows / spec_rows_real) + B8 (pros/cons per side)
    + B13 (partial, partial_stage): one JSON row per check in the order health, pairs,
    probe, stream; no line the wrapper filter would drop. Old: no `kind` field."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(), _routes())
    _assert_rc(run, 0)
    assert [r.get("kind") for r in run.rows()] == ["health", "compare", "compare", "probe",
                                                   "stream"]
    assert [r.get("label") for r in run.rows("compare")] == list(PAIRS2)
    for row in run.rows("compare", "probe"):
        assert COMPARE_ROW_KEYS <= set(row), sorted(COMPARE_ROW_KEYS - set(row))
        assert (row["http"], row["verdict"], row["prices"]) == (200, "PASS", "2/2"), row
        assert (list(row["pros"]), list(row["cons"])) == ([2, 2], [1, 1]), row
        assert (row["spec_rows"], row["spec_rows_real"]) == (3, 2), row
    stream = run.rows("stream")[0]
    assert STREAM_ROW_KEYS <= set(stream), sorted(STREAM_ROW_KEYS - set(stream))
    assert stream["terminal_success"] is True and stream["verdict"] == "PASS", stream
    assert [ln for ln in run.lines if WRAPPER_FILTER.search(ln)] == []


@pytest.mark.parametrize("mode", ["http_503", "ConnectError"])
def test_BH25_health_failure_stops_before_any_compare(monkeypatch, capsys, mode):
    """Spec section 3: /health non-200 or a transport error -> a FAIL row, rc 1, no
    compare and no stream. Old: compares anyway (503) / the error escapes."""
    if mode == "http_503":
        health = _json(503, {"status": "unhealthy"})
    else:
        health = _raise_first("ConnectError", _json(200, {"status": "healthy"}))
    run = _drive(monkeypatch, capsys, "canary", _cargs(), _routes(health=health))
    _assert_rc(run, 1)
    assert run.server.of("q", "pair", "stream") == [], [s["kind"] for s in run.server.seen]
    if mode == "http_503":
        assert "health_503" in run.reasons(), run.reasons()
    _assert_no_sentinel(run)


@pytest.mark.parametrize("state", ["opted_in", "not_opted_in"])
def test_BH26_u13_h10_degraded_input_returns_rc_1(monkeypatch, capsys, state):
    """B10: U13 H10's handler (every JSON answer {"success": true, "products": [],
    "overview": {"winner": {"name": "u13"}}}, the stream "event: complete / data: {}")
    -> main() returns rc 1 with a RESULT line and never raises; the client kwargs stay
    the U13 pin. Old: rc 0."""
    h10 = {"success": True, "products": [], "overview": {"winner": {"name": "u13"}}}

    def stream_route(request, index):
        return httpx.Response(200, text="event: complete\ndata: {}\n\n",
                              headers={"content-type": "text/event-stream"})
    routes = {"health": _json(200, h10), "q": _json(200, h10), "pair": _json(200, h10),
              "stream": stream_route}
    opted = state == "opted_in"
    run = _drive(monkeypatch, capsys, "canary", ["--base", BASE_URL, "--pairs", "a vs b"],
                 routes, opt_in="1" if opted else None, key=SENTINEL)
    _assert_rc(run, 1)
    want = {"timeout": 150, "headers": {"X-Admin-Key": SENTINEL}} if opted else {"timeout": 150}
    assert run.built == [want], [sorted(b) for b in run.built]


def test_BH27_timeout_flag_is_per_request_and_the_client_stays_pinned(monkeypatch, capsys):
    """Spec section 3 + B10: --timeout 42 is passed on EVERY request (health, compares,
    stream) as timeout=; the one Client is still httpx.Client(timeout=150).
    Old: argparse rejects --timeout."""
    run = _drive(monkeypatch, capsys, "canary", _cargs("--timeout", "42"), _routes())
    assert run.server.seen, "no request was made (rc %r)" % (run.rc,)
    assert {s["read_timeout"] for s in run.server.seen} == {42.0}
    assert run.built == [{"timeout": 150}], run.built
    _assert_rc(run, 0)


def test_BH28_partial_is_reported_not_gated(monkeypatch, capsys):
    """B13 (A4): a q pair with metadata.partial true and partial_stage "verdict" stays
    PASS (rc 0); its row reports partial true and partial_stage "verdict"; a non-partial
    row reports partial false. Old: no such row fields."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(),
                 _routes(q=_json(200, _body(partial=True, partial_stage="verdict"))))
    _assert_rc(run, 0)
    rows = run.rows("compare")
    assert len(rows) == 2, "want 2 compare rows (kind=compare), got %d" % len(rows)
    assert all(r.get("partial") is True and r.get("partial_stage") == "verdict"
               for r in rows), rows
    probes = run.rows("probe")
    assert len(probes) == 1 and not probes[0].get("partial"), probes


def test_BH29_no_report_file_without_the_flag(monkeypatch, capsys, tmp_path):
    """A7 GUARD: without --report no file is written (cwd = an empty tmp dir).
    Old: green."""
    monkeypatch.chdir(tmp_path)
    run = _drive(monkeypatch, capsys, "canary", _cargs(), _routes())
    assert run.server.seen, run.rc
    assert sorted(p.name for p in tmp_path.iterdir()) == []


# ===========================================================================
# BH30-BH41  scripts/review_warmup.py
# ===========================================================================
W_PASS = (200, _body())
W_NOPRICE = (200, _body((_pending(), _pending())))
W_FAIL400 = (400, _envelope("INSUFFICIENT_DATA"))


def _wargs(*extra):
    return ["--base", BASE_URL, *extra]


def test_BH30_warmup_call_plan(monkeypatch, capsys):
    """BH30 (B9 exact path): /health, then 12 compare GETs: run 1 over the six pairs in
    order, then run 2; params exactly {product_a, product_b, region=bahrain}: no
    nocache, no q; no stream. Old: script absent."""
    run = _drive(monkeypatch, capsys, "warmup", _wargs(), _routes())
    assert [s["path"] for s in run.server.seen] == [HEALTH] + [COMPARE] * 12, (
        [s["path"] for s in run.server.seen])
    want = [{"product_a": a, "product_b": b, "region": "bahrain"}
            for _run in range(2) for a, b in WARMUP_PAIRS]
    assert [s["params"] for s in run.server.compares()] == want
    _assert_rc(run, 0)


@pytest.mark.parametrize("extra,pace", [((), 10.0), (("--pace", "3"), 3.0)])
def test_BH31_warmup_sleeps_between_compares_only(monkeypatch, capsys, extra, pace):
    """BH31: _sleep(pace) 11 times for 12 compares (default 10.0, --pace 3 -> 3.0):
    between consecutive compares, none after health, none after the last."""
    run = _drive(monkeypatch, capsys, "warmup", _wargs(*extra), _routes())
    assert run.sleeps == [pace] * 11, run.sleeps
    flat = [e[1] if e[0] == "req" else "sleep" for e in run.events]
    assert flat == ["health", "pair"] + ["sleep", "pair"] * 11, flat


def test_BH32_warmup_table_and_report(monkeypatch, capsys, tmp_path):
    """BH32: a header line with the columns pair run http verdict prices elapsed, 12 row
    lines; the report (parent dirs created; ASCII) carries the section-4 keys and 12
    rows with pair/run/http/verdict/reasons/prices/elapsed_s/partial (+partial_stage,
    B13); exit 0, auth none."""
    report = tmp_path / "out" / "warmup.json"
    run = _drive(monkeypatch, capsys, "warmup", _wargs("--report", str(report)), _routes())
    _assert_rc(run, 0)
    cols = ("pair", "run", "http", "verdict", "prices", "elapsed")
    headers = [ln for ln in run.lines if all(c in ln.lower().split() for c in cols)]
    assert len(headers) == 1, run.lines[:3]
    assert len([ln for ln in run.lines if TABLE_ROW_RE.search(ln)]) == 12
    raw = report.read_bytes()
    assert sum(1 for b in raw if b > 127) == 0
    data = json.loads(raw.decode("ascii"))
    assert WARMUP_REPORT_KEYS <= set(data), sorted(WARMUP_REPORT_KEYS - set(data))
    assert len(data["rows"]) == 12
    for row in data["rows"]:
        assert WARMUP_ROW_KEYS <= set(row), sorted(WARMUP_ROW_KEYS - set(row))
    assert (data["exit"], data["auth"], data["base"]) == (0, "none", BASE_URL)
    assert run.last == "RESULT: PASS", ascii(run.last)


def test_BH33_warmup_classifies_pairs(monkeypatch, capsys, tmp_path):
    """BH33: pair 1 PASS/PASS, pair 2 NO_PRICE/PASS, pair 3 PASS/FAIL, rest PASS -> READY
    (4) without pair 2, NO PRICE (1) = pair 2, FAILED (1) = pair 3; the FAIL row reads
    FAIL:http_400; report ready/no_price/failed exact; rc 1,
    "RESULT: FAIL ready=4 no_price=1 failed=1"."""
    plan = {WARMUP_PAIRS[0][0]: [W_PASS, W_PASS], WARMUP_PAIRS[1][0]: [W_NOPRICE, W_PASS],
            WARMUP_PAIRS[2][0]: [W_PASS, W_FAIL400]}
    report = tmp_path / "w.json"
    run = _drive(monkeypatch, capsys, "warmup", _wargs("--report", str(report)),
                 _routes(pair=_by_pair(plan)))
    _assert_rc(run, 1)
    ready, no_price, failed = (_line(run, "READY ("), _line(run, "NO PRICE ("),
                               _line(run, "FAILED ("))
    assert ready.startswith("READY (4):") and no_price.startswith("NO PRICE (1):")
    assert failed.startswith("FAILED (1):")
    assert WARMUP_LABELS[1] in no_price and WARMUP_LABELS[1] not in ready
    assert WARMUP_LABELS[2] in failed and WARMUP_LABELS[2] not in ready
    assert all(WARMUP_LABELS[i] in ready for i in (0, 3, 4, 5))
    assert any(WARMUP_LABELS[2] in ln and "FAIL:http_400" in ln
               for ln in run.lines if TABLE_ROW_RE.search(ln))
    data = json.loads(report.read_bytes().decode("ascii"))
    _assert_class(data, "ready", [WARMUP_LABELS[i] for i in (0, 3, 4, 5)])
    _assert_class(data, "no_price", [WARMUP_LABELS[1]])
    _assert_class(data, "failed", [WARMUP_LABELS[2]])
    assert run.last == "RESULT: FAIL ready=4 no_price=1 failed=1", ascii(run.last)


def _w_plan_no_price_tail():
    return {a: [W_NOPRICE, W_NOPRICE] for a, _b in WARMUP_PAIRS[3:]}


W_EXIT_CASES = {
    "all_pass_0": (lambda: _routes(), 0, "RESULT: PASS", None),
    "ready_and_no_price_3": (lambda: _routes(pair=_by_pair(_w_plan_no_price_tail())), 3,
                             "RESULT: FAIL ready=3 no_price=3 failed=0", None),
    "all_no_price_R11_1": (lambda: _routes(pair=_json(*W_NOPRICE)), 1, None, None),
    "health_503_1": (lambda: _routes(health=_json(503, {"status": "unhealthy"})), 1, None, 0),
    "first_compare_401_4": (lambda: _routes(pair=_json(401, AUTH_401)), 4,
                            "RESULT: FAIL setup=auth_401", 1),
    "first_compare_403_4": (lambda: _routes(pair=_json(403, AUTH_403)), 4,
                            "RESULT: FAIL setup=auth_403", 1),
}


@pytest.mark.parametrize("case", list(W_EXIT_CASES))
def test_BH34_warmup_exit_codes(monkeypatch, capsys, case):
    """BH34 (+B3 setup 4, +B4 R11 over the 12 compares): all READY 0; READY + NO PRICE
    3; NO PRICE everywhere (no amount in the run) 1; health failure 1 with no compare;
    401/403 on the first compare 4 after exactly one compare."""
    routes, want, last, compares = W_EXIT_CASES[case]
    run = _drive(monkeypatch, capsys, "warmup", _wargs(), routes())
    _assert_rc(run, want)
    if last is not None:
        assert run.last == last, ascii(run.last)
    if compares is not None:
        assert len(run.server.compares()) == compares, len(run.server.compares())
    if want == 4:
        assert "--send-admin-key" in run.out


@pytest.mark.parametrize("mode", ["not_opted_in", "env_opt_in", "flag_opt_in",
                                  "opted_in_key_missing"])
def test_BH35_warmup_auth_parity(monkeypatch, capsys, mode):
    """BH35 (parity with BH10-BH13): no opt-in -> Client(timeout=150), no header; env or
    --send-admin-key -> Client(timeout=150, headers=...) and every request carries it;
    opted in without ADMIN_API_KEY -> rc 4, no request, setup=admin_variable_missing."""
    argv = _wargs("--send-admin-key") if mode == "flag_opt_in" else _wargs()
    run = _drive(monkeypatch, capsys, "warmup", argv, _routes(),
                 opt_in="1" if mode in ("env_opt_in", "opted_in_key_missing") else None,
                 key=None if mode == "opted_in_key_missing" else SENTINEL)
    if mode == "opted_in_key_missing":
        _assert_rc(run, 4)
        assert run.server.seen == []
        assert "ADMIN_API_KEY" in run.out
        assert run.last == "RESULT: FAIL setup=admin_variable_missing", ascii(run.last)
        return
    _assert_rc(run, 0)
    assert len(run.server.seen) == 13
    if mode == "not_opted_in":
        assert run.built == [{"timeout": 150}], run.built
        assert all("x-admin-key" not in s["headers"] for s in run.server.seen)
    else:
        assert run.built == [{"timeout": 150, "headers": {"X-Admin-Key": SENTINEL}}], (
            [sorted(b) for b in run.built])
        assert all(s["headers"].get("x-admin-key") == SENTINEL for s in run.server.seen)
    _assert_no_sentinel(run)


@pytest.mark.parametrize("exc_name", TRANSPORT)
def test_BH36_warmup_transport_errors_never_leak(monkeypatch, capsys, tmp_path, exc_name):
    """BH36 + B7: opted in; the first compare raises <exc> carrying the sentinel -> that
    pair FAILED (rc 1) with reason transport_<Class> / timeout in the report, all 12
    compares still made, the sentinel absent from stdout, stderr and the report."""
    report = tmp_path / "w.json"
    run = _drive(monkeypatch, capsys, "warmup", _wargs("--report", str(report)),
                 _routes(pair=_raise_first(exc_name, _json(200, _body()))),
                 opt_in="1", key=SENTINEL)
    _assert_rc(run, 1)
    assert len(run.server.compares()) == 12
    assert report.is_file(), "no report written"
    _assert_no_sentinel(run, report)
    data = json.loads(report.read_bytes().decode("ascii"))
    assert any(WANT_REASON[exc_name] in (r.get("reasons") or []) for r in data["rows"]), (
        [r.get("reasons") for r in data["rows"]])


def test_BH36c_warmup_client_construction_failure_is_a_crash_exit_5(monkeypatch, capsys):
    """B7: the Client constructor raises UnicodeEncodeError carrying the sentinel -> rc 5,
    "RESULT: FAIL error=UnicodeEncodeError", no request, no traceback, no sentinel."""
    exc = UnicodeEncodeError("ascii", "k" + SENTINEL, 0, 1, "bad header " + SENTINEL)
    run = _drive(monkeypatch, capsys, "warmup", _wargs(), _routes(), opt_in="1", key=SENTINEL,
                 client_error=exc)
    _assert_rc(run, 5)
    assert run.last == "RESULT: FAIL error=UnicodeEncodeError", ascii(run.last)
    assert run.server.seen == []
    _assert_no_sentinel(run)


def test_BH37_warmup_output_and_report_are_ascii(monkeypatch, capsys, tmp_path):
    """BH37: a --pairs label with chr(0x645) chr(0x64a) is sent as is, and every stdout
    character and report byte is < 128 (ASCII backslashreplace)."""
    report = tmp_path / "w.json"
    run = _drive(monkeypatch, capsys, "warmup",
                 _wargs("--runs", "1", "--pairs", NON_ASCII_LABEL, "--report", str(report)),
                 _routes())
    assert [s["params"].get("product_a") for s in run.server.compares()] == [NON_ASCII_A]
    assert _non_ascii(run.out) == 0, "%d non-ASCII characters on stdout" % _non_ascii(run.out)
    assert sum(1 for b in report.read_bytes() if b > 127) == 0, "non-ASCII bytes in the report"


def test_BH38_single_run_single_pair(monkeypatch, capsys):
    """BH38: --runs 1 --pairs "A vs B vs C" -> exactly 1 compare, split on the FIRST
    " vs " (product_a A, product_b "B vs C"), 0 sleeps; --timeout 7 rides on every
    request while the Client stays timeout=150."""
    run = _drive(monkeypatch, capsys, "warmup",
                 _wargs("--runs", "1", "--pairs", "A vs B vs C", "--timeout", "7"), _routes())
    assert [s["params"] for s in run.server.compares()] == [
        {"product_a": "A", "product_b": "B vs C", "region": "bahrain"}]
    assert run.sleeps == []
    assert {s["read_timeout"] for s in run.server.seen} == {7.0}
    assert run.built == [{"timeout": 150}], run.built
    _assert_rc(run, 0)


def test_BH39_warmup_imports_only_pure_names_from_the_canary():
    """B11: review_warmup imports from scripts.verify_after_credits only DEFAULT_BASE,
    EXIT_* constants, evaluate_compare and _harness_auth_headers (one rule
    implementation; it defines no rule of its own); its own module-level `import httpx`;
    PAIRS / DEFAULT_RUNS / DEFAULT_PACE / _sleep as spec section 4."""
    if not WARMUP.is_file():
        pytest.fail("RED: scripts/review_warmup.py is absent")
    src = WARMUP.read_bytes()
    assert sum(1 for b in src if b > 127) == 0, "scripts/review_warmup.py is not ASCII"
    tree = ast.parse(src.decode("ascii"))
    froms = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
             and "verify_after_credits" in (n.module or "")]
    plain = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
             if "verify_after_credits" in a.name]
    assert froms, "review_warmup does not import from scripts.verify_after_credits"
    assert {n.module for n in froms} == {"scripts.verify_after_credits"}
    assert plain == []
    names = {a.name for n in froms for a in n.names}
    allowed = {"DEFAULT_BASE", "evaluate_compare", "_harness_auth_headers"}
    extra = sorted(n for n in names if n not in allowed and not n.startswith("EXIT_"))
    assert extra == [], "B11: review_warmup also imports %s" % extra
    assert {"evaluate_compare", "_harness_auth_headers"} <= names
    defs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert not ({"evaluate_compare", "evaluate_stream", "_harness_auth_headers"} & defs)
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                and (n.module or "").split(".")[0] == "httpx"]
    assert any(isinstance(n, ast.Import) and any(a.name == "httpx" and a.asname is None
                                                 for a in n.names) for n in tree.body)
    mod = _load(WARMUP, "warmup")
    assert getattr(mod.evaluate_compare, "__module__", None) == "scripts.verify_after_credits"
    for name, value in EXIT.items():
        if hasattr(mod, name):
            assert getattr(mod, name) == value, name
    assert [tuple(p) for p in mod.PAIRS] == WARMUP_PAIRS
    assert mod.DEFAULT_RUNS == 2 and mod.DEFAULT_PACE == 10.0
    assert mod._sleep is time.sleep


def test_BH40_warmup_cold_only_list(monkeypatch, capsys):
    """B12: pair 1 FAIL then PASS (cold only), pair 2 PASS then FAIL -> both FAILED
    ("any FAIL -> FAILED" stays), and the COLD ONLY (1) line names pair 1 only."""
    plan = {WARMUP_PAIRS[0][0]: [W_FAIL400, W_PASS], WARMUP_PAIRS[1][0]: [W_PASS, W_FAIL400]}
    run = _drive(monkeypatch, capsys, "warmup", _wargs(), _routes(pair=_by_pair(plan)))
    _assert_rc(run, 1)
    cold = _line(run, "COLD ONLY (")
    assert cold.startswith("COLD ONLY (1):"), ascii(cold)
    assert WARMUP_LABELS[0] in cold and WARMUP_LABELS[1] not in cold
    failed = _line(run, "FAILED (")
    assert failed.startswith("FAILED (2):") and WARMUP_LABELS[0] in failed
    assert WARMUP_LABELS[1] in failed


def test_BH41_warmup_partial_reported_not_gated(monkeypatch, capsys, tmp_path):
    """B13: pair 6 run 1 is a partial (partial_stage "gather") but otherwise passes ->
    it stays READY (rc 0); the PARTIAL: line names it and no other pair; its report row
    carries partial true and partial_stage "gather"."""
    plan = {WARMUP_PAIRS[5][0]: [(200, _body(partial=True, partial_stage="gather")), W_PASS]}
    report = tmp_path / "w.json"
    run = _drive(monkeypatch, capsys, "warmup", _wargs("--report", str(report)),
                 _routes(pair=_by_pair(plan)))
    _assert_rc(run, 0)
    partial = _line(run, "PARTIAL:")
    assert WARMUP_LABELS[5] in partial
    assert all(WARMUP_LABELS[i] not in partial for i in range(5))
    assert WARMUP_LABELS[5] in _line(run, "READY (")
    rows = [r for r in json.loads(report.read_bytes().decode("ascii"))["rows"] if r.get("partial")]
    assert len(rows) == 1 and rows[0].get("partial_stage") == "gather", rows


# ===========================================================================
# Fix round (FABLE_RULINGS_BE_HARNESS.md "Post-adversary rulings 20:10", H2-H5, H8):
# every node below is NEW and appended; no node above changed. Each docstring names
# the mutant shape (adv-eng E08/E15/E18/E22/E23, green Y28) or the GREEN bytes it is
# red on.
# ===========================================================================
SCRIPTS = {"canary": CANARY, "warmup": WARMUP}


def test_BH21b_stream_success_first_failure_last_is_not_success():
    """H5 (ENG-1, mutant E08): settle_complete success:true then complete success:false
    -> FAIL stream_terminal_not_success and terminal_success false (B2: S4 holds EVERY
    terminal, not only the first). Red on E08 (terminals[:1])."""
    evaluate = _canary_fn("evaluate_stream")
    res = evaluate(200, _lines(_stream(STREAM_TIMEOUT, settle=_body())))
    assert res.get("verdict") == "FAIL", res
    assert "stream_terminal_not_success" in (res.get("reasons") or []), res
    assert res.get("terminal_success") is False, res


def test_BH04e_stream_success_first_failure_last_fails_the_run(monkeypatch, capsys):
    """H5 (E08) driver: healthy compares + a stream whose settle_complete is success:true
    and whose complete is success:false -> rc 1; the stream row is FAIL with
    stream_terminal_not_success and terminal_success false."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(),
                 _routes(stream=_events(_stream(STREAM_TIMEOUT, settle=_body()))))
    _assert_rc(run, 1)
    rows = run.rows("stream")
    assert len(rows) == 1 and rows[0].get("verdict") == "FAIL", rows
    assert "stream_terminal_not_success" in (rows[0].get("reasons") or []), rows
    assert rows[0].get("terminal_success") is False, rows


def test_BH40b_cold_only_excludes_fail_fail_and_fail_no_price(monkeypatch, capsys):
    """H5 (ENG-4, mutant E18): pair 1 FAIL/PASS, pair 2 FAIL/FAIL, pair 3 FAIL/NO_PRICE,
    rest PASS -> FAILED (3) names all three; COLD ONLY (1) names pair 1 ONLY (B12: the
    first run failed AND every later run passed). Red on E18 (any first-run FAIL)."""
    plan = {WARMUP_PAIRS[0][0]: [W_FAIL400, W_PASS], WARMUP_PAIRS[1][0]: [W_FAIL400, W_FAIL400],
            WARMUP_PAIRS[2][0]: [W_FAIL400, W_NOPRICE]}
    run = _drive(monkeypatch, capsys, "warmup", _wargs(), _routes(pair=_by_pair(plan)))
    _assert_rc(run, 1)
    cold = _line(run, "COLD ONLY (")
    assert cold.startswith("COLD ONLY (1):"), ascii(cold)
    assert WARMUP_LABELS[0] in cold, ascii(cold)
    assert all(WARMUP_LABELS[i] not in cold for i in (1, 2, 3, 4, 5)), ascii(cold)
    failed = _line(run, "FAILED (")
    assert failed.startswith("FAILED (3):"), ascii(failed)
    assert all(WARMUP_LABELS[i] in failed for i in (0, 1, 2)), ascii(failed)
    assert run.last == "RESULT: FAIL ready=3 no_price=0 failed=3", ascii(run.last)


def test_BH39b_warmup_never_binds_the_canary_module_object():
    """H5 (ENG-5, mutant E15): B11 pins the import SET, so the warm-up may not reach the
    canary module any other way: no `from scripts import ...`, no `import scripts[.x]`,
    no relative import, no importlib.import_module / __import__ call anywhere; and at
    runtime no module-typed attribute of the loaded warm-up belongs to the scripts
    package. Red on E15 (`from scripts import verify_after_credits as _vac`)."""
    if not WARMUP.is_file():
        pytest.fail("RED: scripts/review_warmup.py is absent")
    tree = ast.parse(WARMUP.read_bytes().decode("ascii"))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            if node.level or module == "scripts" or (
                    module != "scripts.verify_after_credits"
                    and any("verify_after_credits" in n or n == "scripts" for n in names)):
                bad.append("from %s%s import %s" % ("." * node.level, module, ", ".join(names)))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "scripts" or alias.name.startswith("scripts."):
                    bad.append("import " + alias.name)
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (
                func.attr if isinstance(func, ast.Attribute) else "")
            if name in ("__import__", "import_module"):
                bad.append("call " + name)
    assert bad == [], "B11 bypass: %s" % bad
    mod = _load(WARMUP, "warmup")
    bound = sorted(name for name, value in vars(mod).items()
                   if isinstance(value, type(sys))
                   and (getattr(value, "__name__", "") or "").split(".")[0] == "scripts")
    assert bound == [], "the warm-up binds a scripts module object: %s" % bound


def _b_success(value):
    body = _body()
    body["success"] = value
    return body


def _b_products_entry(index, value):
    body = _body()
    body["overview"]["products"][index] = value
    return body


BH20C_CASES = [
    ("success_int_1", lambda: _b_success(1), "not_success"),
    ("success_string_true", lambda: _b_success("true"), "not_success"),
    ("products_two_with_a_string", lambda: _b_products_entry(1, "Product B"), "products_shape"),
    ("products_two_with_none", lambda: _b_products_entry(0, None), "products_shape"),
    ("products_two_with_a_list", lambda: _b_products_entry(1, ["Product B"]), "products_shape"),
]


@pytest.mark.parametrize("case", BH20C_CASES, ids=[c[0] for c in BH20C_CASES])
def test_BH20c_evaluate_compare_identity_checks(case):
    """H5 (mutants E22, E23): R3 is `success is True` (an int 1 or the string "true" is
    not_success) and R6 needs TWO DICTS (a two-entry list holding a string, None or a
    list is products_shape); the function returns a FAIL dict and never raises."""
    name, factory, reason = case
    evaluate = _canary_fn("evaluate_compare")
    res = evaluate(200, factory())
    assert isinstance(res, dict), type(res)
    assert res.get("verdict") == "FAIL", (name, res)
    assert reason in (res.get("reasons") or []), (name, res)


@pytest.mark.parametrize("value", ["true", "yes", "on", " TRUE ", "Yes"])
@pytest.mark.parametrize("state", ["key_missing", "key_set"])
def test_BH35b_warmup_env_opt_in_values(monkeypatch, capsys, value, state):
    """H5 (GREEN Q4, mutant Y28): the warm-up's env opt-in accepts 1/true/yes/on, case and
    space insensitive (parity with the canary, BH22): with the key missing -> rc 4, no
    request, setup=admin_variable_missing; with the key set -> every request carries it.
    Red on Y28 (the warm-up accepting "1" only) in the key_missing cases."""
    run = _drive(monkeypatch, capsys, "warmup", _wargs(), _routes(), opt_in=value,
                 key=None if state == "key_missing" else SENTINEL)
    if state == "key_missing":
        _assert_rc(run, 4)
        assert run.server.seen == [], [s["kind"] for s in run.server.seen]
        assert run.last == "RESULT: FAIL setup=admin_variable_missing", ascii(run.last)
        return
    _assert_rc(run, 0)
    assert len(run.server.seen) == 13
    assert all(s["headers"].get("x-admin-key") == SENTINEL for s in run.server.seen)
    assert run.built == [{"timeout": 150, "headers": {"X-Admin-Key": SENTINEL}}], (
        [sorted(b) for b in run.built])
    _assert_no_sentinel(run)


def _main_first_statement(path):
    """The first statement of main() after its docstring (None when main is absent)."""
    tree = ast.parse(path.read_bytes().decode("ascii"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            body = list(node.body)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                body = body[1:]
            return body[0] if body else None
    return None


def _is_reconfigure_call(node):
    """`sys.stdout.reconfigure(line_buffering=True)` as an expression statement, exactly."""
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    call = node.value
    func = call.func
    target = (isinstance(func, ast.Attribute) and func.attr == "reconfigure"
              and isinstance(func.value, ast.Attribute) and func.value.attr == "stdout"
              and isinstance(func.value.value, ast.Name) and func.value.value.id == "sys")
    keywords = {k.arg: k.value for k in call.keywords}
    flag = keywords.get("line_buffering")
    return bool(target and not call.args and list(keywords) == ["line_buffering"]
                and isinstance(flag, ast.Constant) and flag.value is True)


@pytest.mark.parametrize("script", ["canary", "warmup"])
def test_BH42_main_reconfigures_stdout_line_buffered_first(script):
    """H2 (ENG-3): the FIRST statement of main() is sys.stdout.reconfigure(line_buffering=True),
    bare or as the first statement of a try that has a handler (a stdout without
    reconfigure must keep working). A pipe is block-buffered: rows already printed must
    survive a bound kill (adv-eng demo_buffering.py: 0 lines under the wrapper). Red on
    the GREEN bytes (main() starts with `try: return _run(argv)`)."""
    path = SCRIPTS[script]
    if not path.is_file():
        pytest.fail("RED: scripts/%s is absent" % path.name)
    first = _main_first_statement(path)
    assert first is not None, "main() is absent or empty"
    if isinstance(first, ast.Try):
        assert first.body and _is_reconfigure_call(first.body[0]), ast.dump(first.body[0])
        assert first.handlers, "the try around reconfigure has no handler"
    else:
        assert _is_reconfigure_call(first), ast.dump(first)


class _Stdout:
    """A text sink standing in for sys.stdout: records reconfigure calls and their order
    against the first non-blank write; built without `reconfigure` on request."""

    def __init__(self, with_reconfigure):
        self.chunks, self.calls, self.events = [], [], []
        if with_reconfigure:
            self.reconfigure = self._reconfigure

    def _reconfigure(self, **kwargs):
        self.calls.append(dict(kwargs))
        self.events.append("reconfigure")

    def write(self, text):
        if text.strip():
            self.events.append("write")
        self.chunks.append(text)
        return len(text)

    def flush(self):
        return None

    def getvalue(self):
        return "".join(self.chunks)


@pytest.mark.parametrize("with_reconfigure", [True, False], ids=["reconfigure", "no_reconfigure"])
@pytest.mark.parametrize("script", ["canary", "warmup"])
def test_BH42b_main_line_buffers_stdout_before_the_first_row(monkeypatch, script,
                                                             with_reconfigure):
    """H2 behaviour: main() calls stdout.reconfigure(line_buffering=True) exactly once,
    before the first row is written; a stdout WITHOUT reconfigure still completes the
    run with "RESULT: PASS" (fallback-safe). Red on the GREEN bytes (no call)."""
    mod = _load(SCRIPTS[script], script)
    server = _Server(_routes(), [])
    real_client = httpx.Client

    def _client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(server)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(mod, "httpx", _HttpxShim(Client=_client))
    if script == "warmup":
        monkeypatch.setattr(mod, "_sleep", lambda seconds: None)
    sink = _Stdout(with_reconfigure)
    monkeypatch.setattr(sys, "stdout", sink)
    argv = _cargs() if script == "canary" else _wargs("--runs", "1", "--pairs", "A vs B")
    rc = mod.main(argv)
    lines = [ln for ln in sink.getvalue().splitlines() if ln.strip()]
    assert rc == 0 and lines and lines[-1] == "RESULT: PASS", (rc, lines[-1:])
    assert server.seen, "no request was made"
    if with_reconfigure:
        assert sink.calls == [{"line_buffering": True}], sink.calls
        assert sink.events[:1] == ["reconfigure"], sink.events[:3]


@pytest.mark.parametrize("script", ["canary", "warmup"])
def test_BH43_empty_pairs_is_a_usage_error(monkeypatch, capsys, script):
    """H3 (ENG-8): `--pairs` with no value is an argparse usage error in BOTH scripts: exit
    2, a usage message on stderr naming --pairs, no RESULT line, no request. Red on the
    GREEN bytes (the canary runs probe + stream and exits 0; the warm-up runs the six
    default pairs and exits 0)."""
    run = _drive(monkeypatch, capsys, script, ["--base", BASE_URL, "--pairs"], _routes())
    assert run.rc == 2, "rc %r (last stdout line %s)" % (run.rc, ascii(run.last))
    assert run.server.seen == [], [s["kind"] for s in run.server.seen]
    assert "--pairs" in run.err and "usage:" in run.err, ascii(run.err[-300:])
    assert not any(ln.startswith("RESULT:") for ln in run.lines), run.lines[-1:]
    assert run.built == [], run.built


MALFORMED_KEYS = {"whitespace_only": "   ", "trailing_space": SENTINEL + " ",
                  "leading_space": " " + SENTINEL, "trailing_newline": SENTINEL + "\n"}


@pytest.mark.parametrize("shape", list(MALFORMED_KEYS))
@pytest.mark.parametrize("mode", ["flag", "env"])
@pytest.mark.parametrize("script", ["canary", "warmup"])
def test_BH44_malformed_admin_key_is_setup_exit_4(monkeypatch, capsys, tmp_path, script,
                                                  mode, shape):
    """H4 (CT-3): opted in (the flag or HARNESS_SEND_ADMIN_KEY=1) with an ADMIN_API_KEY
    that is blank after strip or differs from its strip (a pasted space or newline
    reaches h11 as an illegal header value whose text quotes the key) -> rc 4, NO
    request, no client, stdout names the variable (name only), the last line is
    "RESULT: FAIL setup=admin_variable_malformed" (kept by the wrapper filter), and the
    key is absent from stdout, stderr and the report. Red on the GREEN bytes (the padded
    key is sent as is)."""
    report = tmp_path / "r.json"
    make = _cargs if script == "canary" else _wargs
    flag = ("--send-admin-key",) if mode == "flag" else ()
    run = _drive(monkeypatch, capsys, script, make(*flag, "--report", str(report)), _routes(),
                 opt_in="1" if mode == "env" else None, key=MALFORMED_KEYS[shape])
    _assert_rc(run, 4)
    assert run.server.seen == [], [s["kind"] for s in run.server.seen]
    assert run.built == [], run.built
    assert run.last == "RESULT: FAIL setup=admin_variable_malformed", ascii(run.last)
    assert not WRAPPER_FILTER.search(run.last)
    assert "ADMIN_API_KEY" in run.out
    _assert_no_sentinel(run, report)


def test_BH23b_canary_docstring_carries_the_debug_logging_caveat():
    """H8: the canary docstring says, in one line, never to run it with DEBUG logging for
    httpx/httpcore (the httpcore.http11 DEBUG trace quotes a malformed header value:
    adv-canary-truth debug_log_probe.log). Red on the GREEN bytes."""
    mod = _load(CANARY, "canary")
    doc = mod.__doc__ or ""
    assert "DEBUG" in doc and "httpcore" in doc, doc[-300:]


# ===========================================================================
# BH45-BH52  FANOUT-STARVE (session 75, 2026-10-09): the canary `--form` plumbing of
# FS-R5 (T22) and the runbook A1 step 8 form rule (T23). Appended nodes, RED at main
# 4c0f3c99 (argparse rejects --form / --strict-q; no `form` row field; no q_fail /
# pair_fail on the RESULT line; no runbook sentence). Contract fixed here for GREEN
# where FS-R5 leaves a name open:
#   * `--form q|pair|both`: each curated pair runs as a `compare` row in the requested
#     form(s); a pair-form row sends {product_a, product_b, region, nocache} with the pair
#     text split on its FIRST " vs "; row labels read "<pair> [q]" / "<pair> [pair]";
#     every compare row carries `form` ("q" | "pair") on stdout and in the --report rows.
#   * The RESULT line ALWAYS ends " q_fail=<n> pair_fail=<n>" in pair and both mode, zeros
#     included (FG-2, as corrected by FY14); in q mode and without --form it is today's line
#     byte for byte (BH05's exact "RESULT: PASS" pin stays green; BH55 pins --form q).
#   * The exit is driven by the pair rows, the probe and the stream; q rows are reported
#     and drive the exit only under `--strict-q`.
#   * The DEFAULT of --form is deliberately NOT pinned here: FS-R5's default `both`
#     reddens BH07 / BH07b / BH18 / BH24 / BH28 (append-only protected) -- reported to the
#     orchestrator as a ruling question; every node below passes --form explicitly.
# ===========================================================================
FORM_PAIRS = ("Product A vs Product B", "Product C vs Product D")
PAIR_PARAMS = [{"product_a": "Product A", "product_b": "Product B", "region": "bahrain",
                "nocache": "true"},
               {"product_a": "Product C", "product_b": "Product D", "region": "bahrain",
                "nocache": "true"}]
Q_PARAMS = [{"q": p, "nocache": "true", "region": "bahrain"} for p in FORM_PAIRS]
RUNBOOK = (REPO_ROOT / "docs" / "investigations" / "2026-09-29-session-69-state"
           / "APP_STORE_LAUNCH_RUNBOOK.md")


def _params_sorted(rows):
    return sorted(json.dumps(p, sort_keys=True) for p in rows)


def test_BH45_form_both_runs_every_pair_in_both_forms(monkeypatch, capsys):
    """BH45 (FS-R5 plumbing, T22): --form both -> for each curated pair ONE q request and
    ONE product_a/product_b request (split on the first " vs "), then the probe and the
    stream once each; 2 x len(pairs) compare rows whose labels carry [q] / [pair] and
    whose `form` field matches; health first, probe and stream last; rc 0.
    RED at main: argparse rejects --form."""
    run = _drive(monkeypatch, capsys, "canary", _cargs("--form", "both", pairs=FORM_PAIRS),
                 _routes())
    _assert_rc(run, 0)
    assert [s["params"] for s in run.server.of("q")] == Q_PARAMS, run.server.of("q")
    pair_seen = [s["params"] for s in run.server.of("pair")]
    assert _params_sorted(pair_seen) == _params_sorted(PAIR_PARAMS + [PROBE_PARAMS]), pair_seen
    assert len(run.server.compares()) == 2 * len(FORM_PAIRS) + 1
    assert [s["params"] for s in run.server.of("stream")] == [PROBE_PARAMS]
    kinds = [r.get("kind") for r in run.rows()]
    assert kinds[0] == "health" and kinds[-2:] == ["probe", "stream"], kinds
    rows = run.rows("compare")
    assert len(rows) == 2 * len(FORM_PAIRS), rows
    want_labels = sorted([p + " [q]" for p in FORM_PAIRS] + [p + " [pair]" for p in FORM_PAIRS])
    assert sorted(r.get("label") for r in rows) == want_labels, rows
    for row in rows:
        assert row.get("form") in ("q", "pair"), row
        assert row["label"].endswith("[" + row["form"] + "]"), row
        assert (row["http"], row["verdict"], row["prices"]) == (200, "PASS", "2/2"), row


@pytest.mark.parametrize("form", ["q", "pair"])
def test_BH46_form_single_runs_only_that_form(monkeypatch, capsys, form):
    """BH46 (FS-R5, T22): --form q -> only q compare rows (the probe stays the single
    pair-form request); --form pair -> only pair-form compare rows and NO q request.
    RED at main: argparse rejects --form."""
    run = _drive(monkeypatch, capsys, "canary", _cargs("--form", form, pairs=FORM_PAIRS),
                 _routes())
    _assert_rc(run, 0)
    rows = run.rows("compare")
    assert len(rows) == len(FORM_PAIRS) and all(r.get("form") == form for r in rows), rows
    assert all(r.get("label", "").endswith("[" + form + "]") for r in rows), rows
    if form == "q":
        assert [s["params"] for s in run.server.of("q")] == Q_PARAMS
        assert [s["params"] for s in run.server.of("pair")] == [PROBE_PARAMS]
    else:
        assert run.server.of("q") == [], run.server.of("q")
        pair_seen = [s["params"] for s in run.server.of("pair")]
        assert _params_sorted(pair_seen) == _params_sorted(PAIR_PARAMS + [PROBE_PARAMS]), pair_seen


def test_BH47_report_rows_carry_the_form_field(monkeypatch, capsys, tmp_path):
    """BH47 (FS-R5, T22): --form both --report -> every compare row of the report carries
    `form` matching its label; the section-3 keys stay; rows = 1 + 2 x pairs + 2; the
    report stays ASCII/LF. RED at main: argparse rejects --form."""
    report = tmp_path / "canary.json"
    run = _drive(monkeypatch, capsys, "canary",
                 _cargs("--form", "both", "--report", str(report), pairs=FORM_PAIRS), _routes())
    _assert_rc(run, 0)
    assert report.is_file(), "no report written"
    raw = report.read_bytes()
    assert sum(1 for b in raw if b > 127) == 0 and raw.count(b"\r") == 0
    data = json.loads(raw.decode("ascii"))
    assert REPORT_KEYS <= set(data), sorted(REPORT_KEYS - set(data))
    compare_rows = [r for r in data["rows"] if r.get("kind") == "compare"]
    assert len(compare_rows) == 2 * len(FORM_PAIRS), compare_rows
    for row in compare_rows:
        assert COMPARE_ROW_KEYS <= set(row), sorted(COMPARE_ROW_KEYS - set(row))
        assert row.get("form") in ("q", "pair"), row
        assert row["label"].endswith("[" + row["form"] + "]"), row
    assert sorted(r["form"] for r in compare_rows) == (
        ["pair"] * len(FORM_PAIRS) + ["q"] * len(FORM_PAIRS))
    assert len(data["rows"]) == 1 + 2 * len(FORM_PAIRS) + 2, len(data["rows"])


def test_BH48_q_failures_are_reported_but_do_not_drive_the_exit(monkeypatch, capsys):
    """BH48 (FS-R5 exit semantics, T22): --form both with degraded q rows and a healthy
    pair / probe / stream -> rc 0; the q compare rows report verdict FAIL and the pair
    rows PASS; the RESULT line starts "RESULT: PASS" and carries q_fail=<pairs>
    pair_fail=0. RED at main: argparse rejects --form."""
    run = _drive(monkeypatch, capsys, "canary", _cargs("--form", "both", pairs=FORM_PAIRS),
                 _routes(q=_json(200, _degraded())))
    _assert_rc(run, 0)
    q_rows = [r for r in run.rows("compare") if r.get("form") == "q"]
    assert len(q_rows) == len(FORM_PAIRS) and all(r.get("verdict") == "FAIL" for r in q_rows), (
        q_rows)
    pair_rows = [r for r in run.rows("compare") if r.get("form") == "pair"]
    assert len(pair_rows) == len(FORM_PAIRS) and all(r.get("verdict") == "PASS" for r in pair_rows), (
        pair_rows)
    assert run.last.startswith("RESULT: PASS"), ascii(run.last)
    assert "q_fail=%d" % len(FORM_PAIRS) in run.last and "pair_fail=0" in run.last, ascii(run.last)


def test_BH49_strict_q_makes_q_failures_drive_the_exit(monkeypatch, capsys):
    """BH49 (FS-R5 --strict-q, T22): the BH48 run with --strict-q -> rc 1 and a
    "RESULT: FAIL ..." line carrying q_fail=<pairs> pair_fail=0.
    RED at main: argparse rejects --form / --strict-q."""
    run = _drive(monkeypatch, capsys, "canary",
                 _cargs("--form", "both", "--strict-q", pairs=FORM_PAIRS),
                 _routes(q=_json(200, _degraded())))
    _assert_rc(run, 1)
    assert run.last.startswith("RESULT: FAIL"), ascii(run.last)
    assert "q_fail=%d" % len(FORM_PAIRS) in run.last and "pair_fail=0" in run.last, ascii(run.last)


def test_BH50_pair_failures_drive_the_exit(monkeypatch, capsys):
    """BH50 (FS-R5 exit semantics, T22): --form both with the two curated pair-form rows
    degraded (the probe stays healthy through _by_pair) and healthy q rows -> rc 1, the
    pair rows FAIL, the probe PASS, and "RESULT: FAIL ..." carries pair_fail=<pairs>
    q_fail=0. RED at main: argparse rejects --form."""
    plan = {"Product A": [(200, _degraded())], "Product C": [(200, _degraded())]}
    run = _drive(monkeypatch, capsys, "canary", _cargs("--form", "both", pairs=FORM_PAIRS),
                 _routes(pair=_by_pair(plan)))
    _assert_rc(run, 1)
    pair_rows = [r for r in run.rows("compare") if r.get("form") == "pair"]
    assert len(pair_rows) == len(FORM_PAIRS) and all(r.get("verdict") == "FAIL" for r in pair_rows), (
        pair_rows)
    probes = run.rows("probe")
    assert len(probes) == 1 and probes[0].get("verdict") == "PASS", probes
    assert run.last.startswith("RESULT: FAIL"), ascii(run.last)
    assert "pair_fail=%d" % len(FORM_PAIRS) in run.last and "q_fail=0" in run.last, ascii(run.last)


def test_BH51_form_rejects_an_unknown_value(monkeypatch, capsys):
    """BH51 (FS-R5, T22): --form x is an argparse CHOICES error: rc 2, stderr names the
    invalid choice, no request, no client, no RESULT line. RED at main: argparse reports
    an unrecognized argument instead of an invalid choice."""
    run = _drive(monkeypatch, capsys, "canary", _cargs("--form", "x", pairs=FORM_PAIRS),
                 _routes())
    assert run.rc == 2, "rc %r (last stdout line %s)" % (run.rc, ascii(run.last))
    assert "invalid choice" in run.err and "--form" in run.err, ascii(run.err[-300:])
    assert run.server.seen == [] and run.built == [], (run.server.seen, run.built)
    assert not any(ln.startswith("RESULT:") for ln in run.lines), run.lines[-1:]


def test_BH52_runbook_a1_step_8_names_the_form_rule():
    """BH52 / T23 (FS-R5): the runbook's A1 step 8 block (from the line starting
    "8. Canary" to the next top-level step) names the `--form` rule and why: the app sends
    the product_a/product_b (pair) form, so the pair rows, the probe and the stream decide
    the exit while the q rows are reported. RED at main: the block has no --form sentence."""
    assert RUNBOOK.is_file(), "missing %s" % RUNBOOK
    lines = RUNBOOK.read_text(encoding="utf-8").splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith("8. Canary")), None)
    assert start is not None, "runbook A1 step 8 ('8. Canary') not found"
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^\d+\. ", lines[i])),
               len(lines))
    block = "\n".join(lines[start:end])
    assert "--form" in block, "A1 step 8 does not name the --form rule"
    lowered = block.lower()
    assert "product_a" in lowered, "A1 step 8 does not name the product_a/product_b form"
    assert re.search(r"pair[ -]form", lowered), "A1 step 8 does not say 'pair form'"
    assert re.search(r"\bapp\b[^.]{0,80}\b(sends|uses)\b", lowered), (
        "A1 step 8 does not say that the app sends the pair form")


# ===========================================================================
# BH53-BH54  FANOUT-STARVE GREEN additions (FG-1 / FG-2, 2026-10-09): the `--form`
# DEFAULT is today's run, and the both-mode RESULT line always carries the counts.
# ===========================================================================
def test_BH53_no_form_flag_is_todays_run(monkeypatch, capsys):
    """BH53 GUARD (FG-1): a run WITHOUT --form is today's run byte for byte: one q-form
    compare row per curated pair with the BARE pair text as its label and NO `form`
    field, no pair-form compare request (the probe is the only product_a/product_b
    request), the probe and the stream once each, "RESULT: PASS" exactly, rc 0.
    Green at main 4c0f3c99 and after D9 (the default is q-form, bare, unsuffixed)."""
    run = _drive(monkeypatch, capsys, "canary", _cargs(pairs=FORM_PAIRS), _routes())
    _assert_rc(run, 0)
    assert [s["params"] for s in run.server.of("q")] == Q_PARAMS, run.server.of("q")
    assert [s["params"] for s in run.server.of("pair")] == [PROBE_PARAMS], run.server.of("pair")
    assert len(run.server.compares()) == len(FORM_PAIRS) + 1
    rows = run.rows("compare")
    assert [r.get("label") for r in rows] == list(FORM_PAIRS), rows
    assert all("form" not in r for r in rows), rows
    kinds = [r.get("kind") for r in run.rows()]
    assert kinds == ["health", "compare", "compare", "probe", "stream"], kinds
    assert run.last == "RESULT: PASS", ascii(run.last)


def test_BH54_form_both_all_pass_result_line_carries_zero_counts(monkeypatch, capsys):
    """BH54 (FG-2): --form both on an all-healthy run -> rc 0 and the last stdout line is
    EXACTLY "RESULT: PASS q_fail=0 pair_fail=0": in pair and both mode the suffix is
    ALWAYS appended, zeros included, so a reader can tell the mode from the line.
    RED at the RED bytes (and at main): argparse rejects --form."""
    run = _drive(monkeypatch, capsys, "canary", _cargs("--form", "both", pairs=FORM_PAIRS),
                 _routes())
    _assert_rc(run, 0)
    assert run.last == "RESULT: PASS q_fail=0 pair_fail=0", ascii(run.last)


# ===========================================================================
# BH55-BH56  FANOUT-STARVE fix round (post-adversary rulings FY14 / FY23, 2026-10-09).
# ===========================================================================
def test_BH55_form_q_result_line_is_todays(monkeypatch, capsys):
    """BH55 (FY14, ENG-m3 / C12): in --form q the RESULT line is byte-identical to today --
    never a q_fail / pair_fail suffix (FG-2)."""
    run = _drive(monkeypatch, capsys, "canary", _cargs("--form", "q", pairs=FORM_PAIRS),
                 _routes())
    _assert_rc(run, 0)
    assert run.last == "RESULT: PASS", ascii(run.last)


@pytest.mark.parametrize("form", ["pair", "both"])
def test_BH56_setup_and_crash_lines_carry_the_counts_in_pair_and_both_mode(monkeypatch, capsys,
                                                                           form):
    """BH56 (FY23, runtime-truth m4): FG-2's "always" holds for the setup and crash lines too:
    in pair / both mode `RESULT: FAIL setup=...` and `RESULT: FAIL error=...` end
    " q_fail=<n> pair_fail=<n>" (zeros when no compare row ran); the exit codes are today's.
    RED on the GREEN bytes: the setup and crash lines carried no suffix."""
    run = _drive(monkeypatch, capsys, "canary", _cargs("--form", form, pairs=FORM_PAIRS),
                 _routes(), opt_in="1", key=None)
    _assert_rc(run, 4)
    assert run.server.seen == []
    assert run.last == "RESULT: FAIL setup=admin_variable_missing q_fail=0 pair_fail=0", (
        ascii(run.last))
    exc = RuntimeError("client construction failed")
    run = _drive(monkeypatch, capsys, "canary", _cargs("--form", form, pairs=FORM_PAIRS),
                 _routes(), client_error=exc)
    _assert_rc(run, 5)
    assert run.last == "RESULT: FAIL error=RuntimeError q_fail=0 pair_fail=0", ascii(run.last)
    run = _drive(monkeypatch, capsys, "canary", _cargs("--form", form, pairs=FORM_PAIRS),
                 _routes(q=_json(401, AUTH_401), pair=_json(401, AUTH_401)))
    _assert_rc(run, 4)
    assert re.match(r"^RESULT: FAIL setup=auth_401 q_fail=\d+ pair_fail=\d+$", run.last), (
        ascii(run.last))


def test_BH56_no_form_setup_and_crash_lines_are_todays(monkeypatch, capsys):
    """BH56 GUARD (FY23): without --form (and in q mode) the setup and crash lines stay
    today's bytes, no suffix."""
    for extra in ((), ("--form", "q")):
        run = _drive(monkeypatch, capsys, "canary", _cargs(*extra, pairs=FORM_PAIRS),
                     _routes(), opt_in="1", key=None)
        _assert_rc(run, 4)
        assert run.last == "RESULT: FAIL setup=admin_variable_missing", ascii(run.last)
        run = _drive(monkeypatch, capsys, "canary", _cargs(*extra, pairs=FORM_PAIRS),
                     _routes(), client_error=RuntimeError("boom"))
        _assert_rc(run, 5)
        assert run.last == "RESULT: FAIL error=RuntimeError", ascii(run.last)
