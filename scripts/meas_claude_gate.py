"""S81-07 MEAS-CLAUDE-GATE: the Claude go / no-go measurement harness (a scripts/ leaf; nothing under
app/ imports it).

Contract: .qa-s80/S81-07_UNIT_SPEC.md + .qa-s80/S81-07_SPEC_AMENDMENTS.md (one contract, its GATE section
last), RULINGS_S81_07 (R-S07-13..34), GATE_S81_07 (GC-1..GC-19), the brief (R-S07-1..12); pinned by
tests/test_s81_s07_meas_harness.py.

WHO RUNS IT: the ops lane only, with the owner's TEST credential in the ONE variable named by ENV_VAR_NAME,
set for that one process. Agents run the tests and --dry-run only (no socket, no credential read).
Stages (sub-commands): text, moderation, vision, web_search, report; each with its own cap, spend ledger
and report under --out (a folder OUTSIDE the repo). Every refusal is ONE stderr line naming variable NAMES
only; the credential value never reaches argv, a log line, a report, a ledger row or an exception text.
Imports at module top are stdlib only; app modules are imported only after the start checks.

THE RUN COMMAND (RULINGS_FIX1_S81_07 F-2; the ONE canonical template, names and placeholders only, never a
value: <WORKTREE> the unit worktree, <KEYFILE> the owner's key file, <PY> the .venv-qaren interpreter, <OUT> one
absolute folder outside the repo, <NAME> each further refused name the refusal line lists). The credential
assignment is a SHELL PREFIX ASSIGNMENT placed BEFORE the command word env; written after env it would be an
argument of env and stay in the process list for the whole run:
    cd <WORKTREE> && MEAS_ANTHROPIC_TEST_KEY="$(cat <KEYFILE>)" env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY -u <NAME> <PY> -m scripts.meas_claude_gate <stage> --out <OUT>
The dry run carries NO assignment at all:
    cd <WORKTREE> && env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY -u <NAME> <PY> -m scripts.meas_claude_gate <stage> --dry-run --out <OUT>
"""
import asyncio
import hashlib
import importlib
import ipaddress
import json
import logging
import math
import os
import re
import socket
import subprocess
import sys
import time
import types
import warnings
from pathlib import Path

ENV_VAR_NAME = "MEAS_ANTHROPIC_TEST_KEY"
REFUSED_ENV_PREFIXES = ("ANTHROPIC_",)
# GC-5: the suite's ANTHROPIC_* names are covered by the prefix rule; this tuple holds every other name of
# the test suite's CREDENTIALS_UNSET and CREDENTIAL_PLACEHOLDERS lists (copied as literals, never imported).
REFUSED_ENV_NAMES = (
    "SENTRY_DSN", "UPSTASH_REDIS_URL", "UPSTASH_REDIS_TOKEN", "OPENAI_API_KEY_PRIVATE", "OPENAI_BASE_URL",
    "SERPER_API_KEY", "SERPER_API_KEYS", "FIRECRAWL_API_KEY", "SCRAPEDO_API_TOKEN", "BRIGHTDATA_API_KEY",
    "BRIGHTDATA_ZONE", "ZYTE_API_KEY", "ADMIN_API_KEY", "NASSER_GUEST_TOKEN", "TARGET_BASE_URL",
    "APPLE_SIWA_PRIVATE_KEY", "DEVICE_KEY" + "_PEPPER", "AUTH_THROTTLE_PEPPER",
    "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY", "YOUTUBE_API_KEY",
)
# The S81-05 pepper name is joined at import: the S81-05 P01 pin (a scripts/ walker) allows that name, as one
# contiguous literal, only in the two S81-05 modules.
OPENAI_IMPORT_PLACEHOLDER = "meas-import-placeholder"
UNIT_CEILING_USD = 15.0
STAGE_DEFAULTS = {
    "text": {"max_usd": 4.0, "max_calls": 700, "max_minutes": 90},
    "moderation": {"max_usd": 2.0, "max_calls": 250, "max_minutes": 20},
    "vision": {"max_usd": 5.0, "max_calls": 450, "max_minutes": 60},
    "web_search": {"max_usd": 3.0, "max_calls": 100, "max_minutes": 20},
}
CONSECUTIVE_TRANSIENT_STOP = 3
RATE_LIMIT_RETRIES = 3
RETRY_AFTER_DEFAULT_S = 5
RETRY_AFTER_MAX_S = 60
CALL_TIMEOUT_S = 25.0
ROUND_SPACING_S = 30.0
WEB_SEARCH_RESULT_TOKENS_BOUND = 60000
WEB_SEARCH_TOOL_TYPES = ("web_search_20250305", "web_search_20260318")
REPS_MAX = 2
LOCK_NAME = ".meas_lock"
UNBILLED_STATUSES = (400, 401, 403, 404, 413, 422, 429)
STOP_REASONS = ("budget", "unit_ceiling", "max_calls", "max_minutes", "transient", "rate_limit", "auth",
                "host_refused")
GO_THRESHOLDS = {
    "TEXT": {"json_valid_pooled_min": 0.98, "json_valid_site_min": 0.90, "schema_accept_min": 1.0,
             "refusals_a4_max": 1, "refusals_a4_arabic_max": 0, "max_tokens_pooled_max": 0.02,
             "max_tokens_site_max_hits": 2,
             "p95_s": {"classify": 4.0, "specs": 4.0, "reviews": 5.0, "price": 7.5, "image_tier3": 2.5},
             "timeouts_max": 0},
    "VERDICT": {"json_valid_pooled_min": 0.98, "a6_mismatch_max": 0.10, "a6_agreement_min": 0.90,
                "a6_refusals_max": 1, "a1_refusals_max": 0, "timeouts_max": 0},
    "SONNET_ESCALATION": {"accepted_min": 20, "json_valid_min": 0.95},
    "CRITIC": None,
    "MODERATION": {"false_positives_max": 0, "recall_min": 0.90, "fail_closed_max": 1, "p95_s": 3.0},
    "VISION": {"haiku_minus_sonnet_min": -0.05, "haiku_hit_min": 0.80, "p99_s": 20.0},
    "WEB_SEARCH": None,
}
RESULTS_KEYS = ("base_sha", "billing_assumption", "crash", "env_var_name", "flags_applied", "flags_case",
                "flags_removed", "n_run", "n_total", "not_runnable", "out_dir", "price_table_as_of",
                "proxy_env_ignored", "redactions", "settings", "spent_usd", "stage", "stop_reason",
                "unit_spent_usd")
LEDGER_INTENT_KEYS = ("call_id", "attempt", "state", "worst_usd", "kind", "stage", "setting", "site", "ts")
LEDGER_DONE_KEYS = ("call_id", "attempt", "state", "stage", "setting", "site", "case_id", "rep", "model", "kind",
                    "ok", "usd", "worst_usd", "input_tokens", "output_tokens", "cache_read_tokens",
                    "cache_write_tokens", "web_search_requests", "stop_reason", "error_class", "status",
                    "latency_ms", "ttft_ms", "ts")
# F-4 (b): one line per A1 round whose tail legs were SENT in that process (a replayed round writes none);
# span_ms is null and censored true when a tail leg timed out (+infinity, R-S07-19). Never booked.
LEDGER_TAIL_KEYS = ("state", "stage", "setting", "round", "span_ms", "censored", "ts")
A1_ROUND_ORDER = ("classify", "parse", ("specs", "specs", "price", "price", "image_tier3", "image_tier3"),
                  ("reviews", "reviews"), "verdict", "price_training", "specs_targeted", "specs_synthesized",
                  "disambiguate", "url_extract")
ALLOWED_HOST = "api.anthropic.com"
REPORT_NAME_LINE = "Credential variable (name only): " + ENV_VAR_NAME
EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_CRASH = 3
EXIT_UNIT_CEILING = 4
EXIT_AUTH = 5
EXIT_STOPPED = 6
EXIT_INTERRUPTED = 130

BILLING_ASSUMPTION = "4xx rejected requests are not billed"
A6_SENTENCE = ("A6 measures adherence to the deterministic scores_summary carried by the prompt (the production "
               "WINNER_INDEX_MISMATCH rule), not verdict quality against owner gold.")
FOLDER_SENTENCE = "The unit ceiling is per output folder; the workspace spend limit is the only cross-folder backstop."
TEXT_SETTINGS = ("A0_capabilities", "A1_sites", "A2_ttft", "A3_sonnet_between_tools", "A4_refusal_names",
                 "A5_count_tokens",  # own line: the secret scanner reads a word after a keyword as a value
                 "A6_verdict_eval")
NON_TRANSIENT = ("BadRequestError", "AuthenticationError", "PermissionDeniedError", "NotFoundError",
                 "RequestTooLargeError", "UnprocessableEntityError", "ConflictError", "AnthropicShapeError")
TRANSIENT = ("InternalServerError", "OverloadedError", "APIConnectionError", "APITimeoutError",
             "ServiceUnavailableError", "DeadlineExceededError", "_StreamCut")
REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "s81_s07"
_WS = " \t\r\n\x0b\x0c"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_FENCE = re.compile(r"^\s*```[A-Za-z]*\s*(.*?)\s*```\s*$", re.S)
_P95_SITES = ("classify", "specs", "reviews", "price", "image_tier3")
VERDICTS = ("GO", "NO-GO", "NOT RUN")


# ---------------------------------------------------------------------------
# seams
# ---------------------------------------------------------------------------
def _client_factory(**kw):
    return importlib.import_module("anthropic").AsyncAnthropic(**kw)


def _read_key():
    return os.environ.get(ENV_VAR_NAME)


async def _sleep(seconds):
    await asyncio.sleep(seconds)


def _monotonic():
    return time.monotonic()


def _fsync(fd):
    os.fsync(fd)


def _import_app_modules():
    for name in ("app.services.llm_router", "app.services.model_config", "app.services.llm_pricing",
                 "app.services.llm_spend_breaker", "app.services.extraction_service",
                 "app.services.openai_service", "app.services.image_service",
                 "app.services.url_extraction_service", "app.services.scoring_service",
                 "app.services.text_sanitize", "app.utils.prompt_sanitizer"):
        importlib.import_module(name)


def _git_head():
    """GC-11: the checkout's HEAD sha, or None on any failure (never fatal)."""
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), capture_output=True, text=True,
                              timeout=5)
        if proc.returncode != 0:
            return None
        value = (proc.stdout or "").strip()
        return value if _HEX40.match(value) else None
    except Exception:  # noqa: BLE001 - OSError, TimeoutExpired, anything: no sha
        return None


def _noop_load_dotenv(*a, **k):
    return False


def _install_dotenv_guard():
    import dotenv
    import dotenv.main
    dotenv.load_dotenv = _noop_load_dotenv
    dotenv.main.load_dotenv = _noop_load_dotenv


# ---------------------------------------------------------------------------
# pure pieces
# ---------------------------------------------------------------------------
class StageStop(BaseException):
    def __init__(self, reason, exit_code):
        super().__init__(reason)
        self.reason = reason
        self.exit_code = exit_code

    def __str__(self):
        return self.reason


def _stop(reason):
    code = EXIT_AUTH if reason == "auth" else (EXIT_UNIT_CEILING if reason == "unit_ceiling" else EXIT_STOPPED)
    return StageStop(reason, code)


class Budget:
    def __init__(self, stage_cap_usd, stage_spent_usd, unit_spent_usd):
        self.cap = float(stage_cap_usd)
        self.spent = float(stage_spent_usd)
        self.unit_spent = float(unit_spent_usd)
        self.reserved = 0.0

    def reserve(self, worst_usd):
        w = float(worst_usd)
        if self.spent + self.reserved + w > self.cap:
            return False
        if self.unit_spent + self.reserved + w > UNIT_CEILING_USD:
            return False
        self.reserved += w
        return True

    def settle(self, worst_usd, booked_usd):
        self.reserved -= float(worst_usd)
        if abs(self.reserved) < 1e-12:
            self.reserved = 0.0
        self.spent += float(booked_usd)
        self.unit_spent += float(booked_usd)


def worst_case_usd(request, web_search_max_uses=0):
    from app.services import llm_spend_breaker as sb
    model = request.get("model")
    msgs = []
    if request.get("system"):
        msgs.append({"role": "user", "content": request["system"]})
    msgs.extend(request.get("messages") or [])
    fmt = (request.get("output_config") or {}).get("format")
    uses = int(web_search_max_uses or 0)
    bound = sb.prompt_token_upper_bound(msgs, response_format=fmt, tools=request.get("tools"),
                                        provider="anthropic", model=model)
    bound += uses * WEB_SEARCH_RESULT_TOKENS_BOUND
    usd = sb.upper_bound_usd("anthropic", model, bound, request.get("max_tokens"), uses)
    if usd is None:
        usd = sb.conservative_bound_usd("anthropic", bound, request.get("max_tokens"), uses)
    return float(usd)


def booked_usd_for_exception(exc, worst_usd, sent):
    if not sent:
        return 0.0
    try:
        anthropic = importlib.import_module("anthropic")
        if isinstance(exc, anthropic.APIStatusError) and getattr(exc, "status_code", None) in UNBILLED_STATUSES:
            return 0.0
    except ImportError:
        pass
    return float(worst_usd)


def usd_from_usage(model, usage, worst_usd):
    from app.services import llm_pricing
    rec = llm_pricing.anthropic_usage_record(model, usage)
    cost = rec.get("cost_usd") if isinstance(rec, dict) else None
    if cost is None:
        return float(worst_usd)
    return float(cost)


def _dump(obj):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return dict(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return dict(vars(obj))


def stream_usage(events):
    usage = {}
    complete = False
    for ev in events:
        kind = getattr(ev, "type", None)
        if kind == "message_start":
            usage = _dump(getattr(getattr(ev, "message", None), "usage", None)) or {}
        elif kind == "message_delta":
            for k, v in (_dump(getattr(ev, "usage", None)) or {}).items():
                if v is not None:
                    usage[k] = v
        elif kind == "message_stop":
            complete = True
    return usage, complete


def percentile(samples, q):
    xs = sorted(float(x) for x in samples)
    if not xs:
        return None
    rank = int(math.ceil(q / 100.0 * len(xs)))
    rank = min(max(rank, 1), len(xs))
    return xs[rank - 1]


def ceil_half(x):
    if x is None or math.isinf(x):
        return math.inf
    return math.ceil(round(x * 2.0, 9)) / 2.0


def timeout_proposal(samples, q=99):
    p = percentile(samples, q)
    if p is None:
        return None
    return ceil_half(p * 1.25)


def _host_name(host):
    """F-3 (a): the host as a lower-case str; IDNA bytes are decoded as ASCII; None when they do not decode."""
    if isinstance(host, (bytes, bytearray)):
        try:
            return bytes(host).decode("ascii").strip().lower()
        except UnicodeDecodeError:
            return None
    return str(host or "").strip().lower()


def _is_loopback_name(h):
    """M-4 m5: loopback is the literal name localhost or a host that PARSES as a loopback IP address
    (127.0.0.0/8 or ::1); a name that merely starts with '127.' is any other host name."""
    if h is None:
        return False
    if h == "localhost":
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def host_allowed(host, port):
    h = _host_name(host)
    if h is None:
        return False
    if _is_loopback_name(h):
        return True
    try:
        p = int(port)
    except (TypeError, ValueError):
        return False
    return h == ALLOWED_HOST and p == 443


def refused_names_present(environ):
    return sorted(n for n in environ if n.startswith(REFUSED_ENV_PREFIXES) or n in REFUSED_ENV_NAMES)


def call_id_for(stage, setting, site, case_id, rep):
    raw = "%s|%s|%s|%s|%s" % (stage, setting, site, case_id, rep)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _unfence(text):
    if not isinstance(text, str):
        return None
    m = _FENCE.match(text)
    return m.group(1) if m else text


def _parse_json(text):
    """The parsed JSON of a response text after the Claude fence strip, or None."""
    t = _unfence(text)
    if t is None:
        return None
    try:
        return json.loads(t)
    except (TypeError, ValueError):
        return None


def _tokens(value):
    return re.findall(r"\w+", str(value or "").casefold())


def identity_hit(answer, expected_brand, expected_name):
    """GC-13 (V): True iff some product of the answer matches the expected brand AND name, token-wise and
    case-insensitively (spacing and punctuation do not count)."""
    obj = _parse_json(answer) if isinstance(answer, str) else answer
    if not isinstance(obj, dict) or not isinstance(obj.get("products"), list):
        return False
    want_b, want_n = _tokens(expected_brand), _tokens(expected_name)
    if not want_b or not want_n:
        return False
    for item in obj["products"]:
        if isinstance(item, dict) and _tokens(item.get("brand")) == want_b and _tokens(item.get("name")) == want_n:
            return True
    return False


def _r9(x):
    return round(float(x), 9)


def _ratio(num, den):
    return None if not den else _r9(float(num) / float(den))


_ROLE_STAGE = {"TEXT": "text", "VERDICT": "text", "SONNET_ESCALATION": "text", "MODERATION": "moderation",
               "VISION": "vision"}
_ROLE_NEEDS = {"TEXT": ("A1_sites", "A4_refusal_names"), "VERDICT": ("A1_sites", "A6_verdict_eval"),
               "SONNET_ESCALATION": ("A3_sonnet_between_tools",), "MODERATION": ("M1_parity",),
               "VISION": ("V2_haiku_vision_v2", "V3_sonnet_vision_v2")}


def _n(d, k):
    v = (d or {}).get(k)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


def evaluate_role(role, results):
    """GC-12: (verdict, failed_bars) for one role over {stage: results.json}; pure. A bar passes ON its value."""
    if role not in _ROLE_STAGE:
        return ("NOT RUN", [])
    st = (results or {}).get(_ROLE_STAGE[role])
    if not isinstance(st, dict) or st.get("not_runnable"):
        return ("NOT RUN", ["missing:" + _ROLE_STAGE[role]])
    s = st.get("settings") or {}
    missing = [name for name in _ROLE_NEEDS[role] if not isinstance(s.get(name), dict)]
    if missing:
        return ("NOT RUN", ["missing:" + name for name in missing])
    b = GO_THRESHOLDS[role]
    failed = []
    if role == "TEXT":
        sites = {k: v for k, v in (s["A1_sites"].get("sites") or {}).items() if k != "verdict"}
        pooled = _ratio(sum(_n(v, "json_valid") for v in sites.values()), sum(_n(v, "json_n") for v in sites.values()))
        if pooled is None or pooled < b["json_valid_pooled_min"]:
            failed.append("json_valid_pooled_min")
        if any(_n(v, "json_n") and _ratio(_n(v, "json_valid"), _n(v, "json_n")) < b["json_valid_site_min"]
               for v in sites.values()):
            failed.append("json_valid_site_min")
        if any(_n(v, "schema_n") and _ratio(_n(v, "schema_accepted"), _n(v, "schema_n")) < b["schema_accept_min"]
               for v in sites.values()):
            failed.append("schema_accept_min")
        a4 = s["A4_refusal_names"]
        if _n(a4, "refusals") > b["refusals_a4_max"]:
            failed.append("refusals_a4_max")
        if _n(a4, "refusals_arabic") > b["refusals_a4_arabic_max"]:
            failed.append("refusals_a4_arabic_max")
        hits = _ratio(sum(_n(v, "max_tokens_hits") for v in sites.values()), sum(_n(v, "n") for v in sites.values()))
        if hits is None or hits > b["max_tokens_pooled_max"]:
            failed.append("max_tokens_pooled_max")
        if any(_n(v, "max_tokens_hits") > b["max_tokens_site_max_hits"] for v in sites.values()):
            failed.append("max_tokens_site_max_hits")
        for site in _P95_SITES:
            p = (sites.get(site) or {}).get("p95_s")
            if p is None or p > b["p95_s"][site]:
                failed.append("p95_s." + site)
        if sum(_n(v, "timeouts") for v in sites.values()) > b["timeouts_max"]:
            failed.append("timeouts_max")
    elif role == "VERDICT":
        v = (s["A1_sites"].get("sites") or {}).get("verdict") or {}
        a6 = s["A6_verdict_eval"]
        pooled = _ratio(_n(v, "json_valid") + _n(a6, "json_valid"), _n(v, "json_n") + _n(a6, "json_n"))
        if pooled is None or pooled < b["json_valid_pooled_min"]:
            failed.append("json_valid_pooled_min")
        mism = _ratio(_n(a6, "mismatches"), _n(a6, "n_scored"))
        if mism is None or mism > b["a6_mismatch_max"]:
            failed.append("a6_mismatch_max")
        agree = a6.get("agreement")
        if not isinstance(agree, (int, float)) or _r9(agree) < b["a6_agreement_min"]:
            failed.append("a6_agreement_min")
        if _n(a6, "refusals") > b["a6_refusals_max"]:
            failed.append("a6_refusals_max")
        if _n(v, "refusals") > b["a1_refusals_max"]:
            failed.append("a1_refusals_max")
        if _n(v, "timeouts") + _n(a6, "timeouts") > b["timeouts_max"]:
            failed.append("timeouts_max")
    elif role == "SONNET_ESCALATION":
        a3 = s["A3_sonnet_between_tools"]
        if _n(a3, "accepted") < b["accepted_min"]:
            failed.append("accepted_min")
        jv = _ratio(_n(a3, "json_valid"), _n(a3, "json_n"))
        if jv is None or jv < b["json_valid_min"]:
            failed.append("json_valid_min")
    elif role == "MODERATION":
        m = s["M1_parity"]
        if _n(m, "false_positives") > b["false_positives_max"]:
            failed.append("false_positives_max")
        rec = _ratio(_n(m, "flagged_hits"), _n(m, "n_flagworthy_run"))
        if rec is None or rec < b["recall_min"]:
            failed.append("recall_min")
        if _n(m, "fail_closed") > b["fail_closed_max"]:
            failed.append("fail_closed_max")
        p = m.get("p95_s")
        if not isinstance(p, (int, float)) or p > b["p95_s"]:
            failed.append("p95_s")
    elif role == "VISION":
        h = s["V2_haiku_vision_v2"].get("hit_rate")
        so = s["V3_sonnet_vision_v2"].get("hit_rate")
        if not isinstance(h, (int, float)) or _r9(h) < b["haiku_hit_min"]:
            failed.append("haiku_hit_min")
        if not isinstance(h, (int, float)) or not isinstance(so, (int, float)) or \
                _r9(h - so) < b["haiku_minus_sonnet_min"]:
            failed.append("haiku_minus_sonnet_min")
        p = s["V2_haiku_vision_v2"].get("p99_s")
        if not isinstance(p, (int, float)) or p > b["p99_s"]:
            failed.append("p99_s")
    return ("NO-GO" if failed else "GO", failed)


def _ts():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class _Scrub:
    def __init__(self, value=None):
        self._v = value
        self.count = 0

    def __repr__(self):
        return "<scrub>"

    def s(self, text):
        if self._v and isinstance(text, str) and self._v in text:
            self.count += text.count(self._v)
            return text.replace(self._v, "[redacted]")
        return text

    def obj(self, o):
        if isinstance(o, str):
            return self.s(o)
        if isinstance(o, dict):
            return {self.s(k) if isinstance(k, str) else k: self.obj(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [self.obj(v) for v in o]
        return o


class _StreamCut(Exception):
    pass


class _RateLimited(Exception):
    def __init__(self, delay):
        super().__init__("rate_limited")
        self.delay = delay


def _u(usage, name):
    if usage is None:
        return 0
    v = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
    return int(v or 0)


def _searches(usage):
    stu = usage.get("server_tool_use") if isinstance(usage, dict) else getattr(usage, "server_tool_use", None)
    if stu is None:
        return 0
    v = stu.get("web_search_requests") if isinstance(stu, dict) else getattr(stu, "web_search_requests", None)
    return int(v or 0)


def _retry_after(exc):
    try:
        raw = exc.response.headers.get("retry-after")
        v = float(raw)
        if not math.isfinite(v):
            raise ValueError
    except Exception:  # noqa: BLE001
        v = float(RETRY_AFTER_DEFAULT_S)
    v = min(max(v, 1.0), float(RETRY_AFTER_MAX_S))
    return int(v) if v == int(v) else v


class _Assembled:
    def __init__(self, text, stop_reason, model):
        self.content = [{"type": "text", "text": text}]
        self.stop_reason = stop_reason
        self.model = model


class Dispatcher:
    def __init__(self, client, budget, ledger_path, *, stage, max_calls, deadline_monotonic):
        self.client = client
        self.budget = budget
        self.ledger_path = Path(ledger_path)
        self.stage = stage
        self.max_calls = max_calls
        self.deadline = deadline_monotonic
        self.sends = 0
        self.completed = {}
        self.attempts = {}
        self.records = []
        self.outcomes = []
        self.stop = None
        self.scrub = _Scrub(None)
        self.sent_ids = set()  # F-4 (a): the call_ids this process actually sent
        self.last = {}  # call_id -> its latest done line of this process

    def write_tail(self, setting, round_id, span_ms, censored, failed=False):
        """F-4 (b): the tail span of a round whose tail legs were sent in this process, into the ledger.
        M-4 m6: a censored round (a timed-out leg) and an excluded round (a leg that failed in any other way)
        carry no span; censored true marks the first, censored false with a null span the second."""
        self._write({"state": "tail", "stage": self.stage, "setting": setting, "round": round_id,
                     "span_ms": None if (censored or failed) else span_ms, "censored": bool(censored),
                     "ts": _ts()})

    def _write(self, obj):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(self.scrub.obj(obj), sort_keys=True)
        with open(self.ledger_path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line + "\n")
            fh.flush()
            _fsync(fh.fileno())

    def _halt(self, reason):
        s = _stop(reason)
        if reason != "rate_limit":
            self.stop = s
        raise s

    async def send(self, request, *, setting, site, case_id, rep, kind="create", stream=False):
        rec, _ = await self._send(request, setting=setting, site=site, case_id=case_id, rep=rep, kind=kind,
                                  stream=stream)
        return rec

    async def _send(self, request, *, setting, site, case_id, rep, kind="create", stream=False):
        cid = call_id_for(self.stage, setting, site, case_id, rep)
        if cid in self.completed:
            return self.completed[cid], self.resp_from_raw(cid)
        retries = 0
        while True:
            try:
                return await self._attempt(cid, request, setting, site, case_id, rep, kind, stream)
            except _RateLimited as rl:
                if retries >= RATE_LIMIT_RETRIES:
                    self._halt("rate_limit")
                retries += 1
                await _sleep(rl.delay)

    async def _attempt(self, cid, request, setting, site, case_id, rep, kind, stream):
        if self.stop is not None:
            raise _stop(self.stop.reason)
        if self.sends >= self.max_calls:
            self._halt("max_calls")
        if _monotonic() > self.deadline:
            self._halt("max_minutes")
        uses = 0
        for tool in request.get("tools") or []:
            uses += int(tool.get("max_uses") or 0)
        worst = 0.0 if kind in ("count_tokens", "models_retrieve") else worst_case_usd(request, uses)
        if not self.budget.reserve(worst):
            self._halt("budget")
        self.sends += 1
        idx = len(self.outcomes)
        self.outcomes.append(None)
        attempt = self.attempts.get(cid, 0) + 1
        self.attempts[cid] = attempt
        model = request.get("model")
        booked = 0.0
        sent = False
        rec = None
        try:
            self._write({"call_id": cid, "attempt": attempt, "state": "sent", "worst_usd": worst, "kind":
                         "stream" if stream else kind, "stage": self.stage, "setting": setting, "site": site,
                         "ts": _ts()})
            t0 = _monotonic()
            ttft = None
            usage = None
            resp = None
            sent = True
            self.sent_ids.add(cid)
            try:
                if kind == "count_tokens":
                    await self.client.messages.count_tokens(**request)
                elif kind == "models_retrieve":
                    await self.client.models.retrieve(model)
                elif stream:
                    s = await self.client.messages.create(**request, stream=True, timeout=CALL_TIMEOUT_S)
                    events = []
                    try:
                        async for ev in s:
                            if ttft is None and getattr(ev, "type", None) == "content_block_delta":
                                ttft = (_monotonic() - t0) * 1000.0
                            events.append(ev)
                    except Exception as exc:  # noqa: BLE001 - a cut or failed stream
                        raise _StreamCut() from exc
                    usage, complete = stream_usage(events)
                    if not complete:
                        raise _StreamCut()
                    text = "".join(getattr(getattr(e, "delta", None), "text", "") or "" for e in events
                                   if getattr(e, "type", None) == "content_block_delta")
                    stop_r = None
                    for e in events:
                        if getattr(e, "type", None) == "message_delta":
                            stop_r = getattr(getattr(e, "delta", None), "stop_reason", None)
                    resp = _Assembled(text, stop_r, model)
                else:
                    resp = await self.client.messages.create(**request, timeout=CALL_TIMEOUT_S)
                    usage = getattr(resp, "usage", None)
            except BaseException as exc:
                booked = booked_usd_for_exception(exc, worst, sent)
                rec = self._done(cid, attempt, setting, site, case_id, rep, model, kind, stream, False, booked,
                                 worst, None, None, type(exc).__name__, getattr(exc, "status_code", None),
                                 (_monotonic() - t0) * 1000.0, ttft)
                self._after_error(exc, idx)
                raise _Recorded(rec)
            if kind in ("count_tokens", "models_retrieve"):
                booked = 0.0
            else:
                booked = usd_from_usage(model, usage, worst)
            rec = self._done(cid, attempt, setting, site, case_id, rep, model, kind, stream, True, booked, worst,
                             usage, getattr(resp, "stop_reason", None), None, None, (_monotonic() - t0) * 1000.0,
                             ttft)
            self.outcomes[idx] = "ok"
            if resp is not None:
                self._raw(cid, resp, usage, model)
            self.completed[cid] = rec
            return rec, resp
        except _Recorded as r:
            return r.rec, None
        finally:
            self.budget.settle(worst, booked)

    def _after_error(self, exc, idx):
        name = type(exc).__name__
        status = getattr(exc, "status_code", None)
        if isinstance(exc, StageStop):
            self.outcomes[idx] = "other"
            self.stop = exc
            raise exc
        if not isinstance(exc, Exception):
            raise exc
        if status in (401, 403):
            self.outcomes[idx] = "other"
            self._halt("auth")
        if status == 429:
            self.outcomes[idx] = "other"
            raise _RateLimited(_retry_after(exc))
        if name in TRANSIENT or isinstance(exc, _StreamCut):
            self.outcomes[idx] = "transient"
            n = 0
            j = idx
            while j >= 0 and self.outcomes[j] == "transient":
                n += 1
                j -= 1
            if n >= CONSECUTIVE_TRANSIENT_STOP:
                self._halt("transient")
            return
        if name in NON_TRANSIENT:
            self.outcomes[idx] = "other"
            return
        raise exc

    def _done(self, cid, attempt, setting, site, case_id, rep, model, kind, stream, ok, usd, worst, usage,
              stop_reason, error_class, status, latency, ttft):
        rec = {"call_id": cid, "attempt": attempt, "state": "done", "stage": self.stage, "setting": setting,
               "site": site, "case_id": case_id, "rep": rep, "model": model, "kind": "stream" if stream else kind,
               "ok": ok, "usd": float(usd), "worst_usd": float(worst),
               "input_tokens": _u(usage, "input_tokens"), "output_tokens": _u(usage, "output_tokens"),
               "cache_read_tokens": _u(usage, "cache_read_input_tokens"),
               "cache_write_tokens": _u(usage, "cache_creation_input_tokens"),
               "web_search_requests": _searches(usage) if usage is not None else 0,
               "stop_reason": stop_reason, "error_class": error_class,
               "status": status if isinstance(status, int) else None,
               "latency_ms": None if latency is None else round(latency, 3),
               "ttft_ms": None if ttft is None else round(ttft, 3), "ts": _ts()}
        self._write(rec)
        if ok or error_class in NON_TRANSIENT:
            self.completed[cid] = rec
        self.records.append(rec)
        self.last[cid] = rec
        return rec

    def raw_path(self, cid):
        return self.ledger_path.parent / "raw" / (cid + ".json")

    def raw_data(self, cid):
        p = self.raw_path(cid)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def resp_from_raw(self, cid):
        """A completed call of an earlier run: its stored (scrubbed) response, or None."""
        data = self.raw_data(cid)
        if data is None:
            return None
        blocks = [types.SimpleNamespace(**b) for b in (data.get("content") or []) if isinstance(b, dict)]
        return types.SimpleNamespace(content=blocks, stop_reason=data.get("stop_reason"), model=data.get("model"),
                                     usage=data.get("usage"))

    def _raw(self, cid, resp, usage, model):
        content = [_dump(b) if not isinstance(b, dict) else dict(b) for b in (getattr(resp, "content", None) or [])]
        data = {"content": content, "stop_reason": getattr(resp, "stop_reason", None), "usage": _dump(usage),
                "model": getattr(resp, "model", None) or model}
        p = self.ledger_path.parent / "raw" / (cid + ".json")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.scrub.obj(data), sort_keys=True, default=str), encoding="utf-8",
                     newline="\n")


class _Recorded(Exception):
    def __init__(self, rec):
        super().__init__("recorded")
        self.rec = rec


# ---------------------------------------------------------------------------
# argv, refusals, ledger read-back
# ---------------------------------------------------------------------------
class _Refuse(Exception):
    def __init__(self, line, code=EXIT_REFUSED):
        super().__init__("refused")
        self.line = line
        self.code = code


def _parse(argv):
    if not argv or argv[0] not in ("text", "moderation", "vision", "web_search", "report"):
        raise _Refuse("refused: bad_argument names=stage")
    a = {"stage": argv[0], "dry_run": False}
    vals = ("--out", "--max-usd", "--max-calls", "--max-minutes", "--reps", "--set", "--owner-line",
            "--settings", "--flags-file")
    i = 1
    while i < len(argv):
        tok = argv[i]
        if tok == "--dry-run":
            a["dry_run"] = True
            i += 1
            continue
        if tok in vals and i + 1 < len(argv):
            a[tok] = argv[i + 1]
            i += 2
            continue
        raise _Refuse("refused: bad_argument names=%s" % (tok if tok.startswith("--") else "argv"))
    if "--out" not in a:
        raise _Refuse("refused: bad_argument names=--out")
    d = STAGE_DEFAULTS.get(a["stage"], {"max_usd": 0.0, "max_calls": 0, "max_minutes": 0})
    a["max_usd"] = _num(a, "--max-usd", d["max_usd"], float)
    a["max_calls"] = _num(a, "--max-calls", d["max_calls"], int)
    a["max_minutes"] = _num(a, "--max-minutes", d["max_minutes"], float)
    a["reps"] = _num(a, "--reps", REPS_MAX, int)
    return a


def _num(a, flag, default, kind):
    if flag not in a:
        return default
    raw = a[flag]
    try:
        v = kind(raw)
    except (TypeError, ValueError):
        raise _Refuse("refused: bad_argument names=%s" % flag)
    if isinstance(v, float) and not math.isfinite(v) or v <= 0:
        raise _Refuse("refused: bad_argument names=%s" % flag)
    if v > default:
        raise _Refuse("refused: above_default names=%s" % flag)
    return v


def _read_ledgers(out):
    unit = 0.0
    per_stage = {}
    for p in sorted(out.glob("*/spend.jsonl")):
        stage = p.parent.name
        st = per_stage.setdefault(stage, {"spent": 0.0, "completed": {}, "attempts": {}})
        intents = {}
        dones = set()
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                obj = None
            if not isinstance(obj, dict) or obj.get("state") not in ("sent", "done", "tail"):
                raise _Refuse("refused: ledger_corrupt file=%s line=%d" % (p, n))
            keys = {"sent": LEDGER_INTENT_KEYS, "done": LEDGER_DONE_KEYS, "tail": LEDGER_TAIL_KEYS}[obj["state"]]
            if not set(keys) <= set(obj):
                raise _Refuse("refused: ledger_corrupt file=%s line=%d" % (p, n))
            if obj["state"] == "tail":
                v = obj["span_ms"]
                if v is not None and (not isinstance(v, (int, float)) or isinstance(v, bool)
                                      or not math.isfinite(v) or v < 0):
                    raise _Refuse("refused: ledger_corrupt file=%s line=%d" % (p, n))
                continue
            for k in ("usd", "worst_usd"):
                if k in obj:
                    v = obj[k]
                    if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0:
                        raise _Refuse("refused: ledger_corrupt file=%s line=%d" % (p, n))
            key = (obj["call_id"], obj["attempt"])
            st["attempts"][obj["call_id"]] = max(st["attempts"].get(obj["call_id"], 0), int(obj["attempt"]))
            if obj["state"] == "sent":
                intents[key] = float(obj["worst_usd"])
            else:
                dones.add(key)
                st["spent"] += float(obj["usd"])
                if obj["ok"] or obj.get("error_class") in NON_TRANSIENT:
                    st["completed"][obj["call_id"]] = obj
        for key, w in intents.items():
            if key not in dones:
                st["spent"] += w
        unit += st["spent"]
    return unit, per_stage


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    state = {"restore": []}
    try:
        return _main(argv, state)
    except _Refuse as r:
        sys.stderr.write("meas_claude_gate: %s\n" % r.line)
        return r.code
    except StageStop as s:
        # a stop raised outside a stage run (e.g. a refused host during the app imports): the reason code only
        _finish_partial(state, interrupted=False, reason=s.reason)
        sys.stderr.write("meas_claude_gate: stopped reason=%s\n" % s.reason)
        return s.exit_code
    except KeyboardInterrupt:
        _finish_partial(state, interrupted=True)
        return EXIT_INTERRUPTED
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the last-resort arm (type only)
        _write_crash(state, type(exc).__name__)
        sys.stderr.write("meas_claude_gate: crashed class=%s\n" % type(exc).__name__)
        return EXIT_CRASH
    finally:
        for fn in reversed(state["restore"]):
            try:
                fn()
            except Exception:  # noqa: BLE001
                pass


def _main(argv, state):
    a = _parse(argv)
    stage = a["stage"]
    out = Path(a["--out"]).resolve()
    root = Path(REPO_ROOT).resolve()
    if out == root or root in out.parents:
        raise _Refuse("refused: out_inside_repo")
    names = refused_names_present(os.environ)
    if names:
        raise _Refuse("refused: refused_env names=" + ",".join(names))
    not_runnable = None
    if stage == "vision" and not a.get("--set"):
        not_runnable = "no_photo_set"
    if stage == "web_search" and not a.get("--owner-line"):
        not_runnable = "no_owner_line"
    live = not a["dry_run"] and stage != "report" and not_runnable is None
    value = None
    raw = _read_key() if live else None
    # GC-10 + F-7 (a): the credential leaves the environment at start in EVERY mode (the dry run, report and
    # a NOT RUNNABLE stage included), right after the live read, before any child process; never restored
    os.environ.pop(ENV_VAR_NAME, None)
    if live:
        value = (raw or "").strip(_WS)
        raw = None
        if not value:
            raise _Refuse("refused: credential_missing names=" + ENV_VAR_NAME)
        if any(ord(c) < 0x21 or ord(c) > 0x7E for c in value):
            raise _Refuse("refused: credential_malformed names=" + ENV_VAR_NAME)
    out.mkdir(parents=True, exist_ok=True)
    lock = out / LOCK_NAME
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise _Refuse("refused: lock_present path=%s (remove it by hand only after confirming that no run is "
                      "live)" % lock)
    os.close(fd)
    state["restore"].append(lambda: lock.unlink())
    unit_spent, per_stage = _read_ledgers(out)
    if stage != "report" and not_runnable is None and unit_spent + a["max_usd"] > UNIT_CEILING_USD:
        raise _Refuse("refused: unit_ceiling", EXIT_UNIT_CEILING)
    for n in ("anthropic", "httpx2", "httpx", "httpcore"):
        logging.getLogger(n).setLevel(logging.WARNING)
    removed = {}
    for name in list(os.environ):
        if name.startswith("ENABLE_"):
            removed[name] = os.environ.pop(name)
    applied = {}

    def _restore_flags():
        for nm in applied:
            os.environ.pop(nm, None)
        os.environ.update(removed)
    state["restore"].append(_restore_flags)
    if a.get("--flags-file"):
        ff = Path(a["--flags-file"])
        for n, line in enumerate(ff.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            m = re.match(r"^(ENABLE_[A-Z0-9_]+)=(true|false)$", line.strip())
            if not m:
                raise _Refuse("refused: flags_file file=%s line=%d" % (ff, n))
            applied[m.group(1)] = m.group(2)
        os.environ.update(applied)
    ctx = _Ctx(a, out, stage, unit_spent, per_stage.get(stage, {"spent": 0.0, "completed": {}, "attempts": {}}))
    ctx.flags_removed = sorted(removed)
    ctx.flags_applied = applied
    ctx.not_runnable = not_runnable
    ctx.scrub = _Scrub(value)
    state["ctx"] = ctx
    # GC-8: the network guard runs in every mode (live: the one host + loopback; otherwise loopback only)
    _install_host_guard(ctx, state, live)
    if stage == "report":
        # F-4 (d): the report reads the CURRENT knob values from the router, so it imports the app modules
        # under the same guards as every other stage (dotenv guard, placeholder, the post-import re-scan)
        _install_guard_and_import(state)
        names = [n for n in refused_names_present(os.environ)
                 if not (n == "OPENAI_API_KEY" and os.environ.get(n) == OPENAI_IMPORT_PLACEHOLDER)]
        if names:
            raise _Refuse("refused: refused_env names=" + ",".join(names))
        _write_top_report(ctx)
        return EXIT_OK
    if not_runnable:
        ctx.write_results(None)
        return EXIT_OK
    _install_guard_and_import(state)
    names = [n for n in refused_names_present(os.environ)
             if not (n == "OPENAI_API_KEY" and os.environ.get(n) == OPENAI_IMPORT_PLACEHOLDER)]
    if names:
        raise _Refuse("refused: refused_env names=" + ",".join(names))
    ctx.base_sha = _git_head()
    client = None
    if live:
        httpx2 = importlib.import_module("httpx2")
        router = importlib.import_module("app.services.llm_router")
        ctx.proxy_env_ignored = sorted(n for n in os.environ
                                       if n.upper() in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"))
        http_client = httpx2.AsyncClient(trust_env=False, follow_redirects=False,
                                         timeout=httpx2.Timeout(CALL_TIMEOUT_S, connect=5.0),
                                         event_hooks={"request": [_make_request_guard(ctx)]})
        client = _client_factory(api_key=value, base_url=router.ANTHROPIC_BASE_URL, max_retries=0,
                                 timeout=CALL_TIMEOUT_S, http_client=http_client)
    value = None
    return ctx.run(client)


def _make_request_guard(ctx):
    """GC-9: the harness client's request hook (async, measured by P13): only https://ALLOWED_HOST:443."""
    async def _request_guard(request):
        url = request.url
        if url.scheme != "https" or url.host != ALLOWED_HOST or url.port not in (None, 443):
            ctx.hosts_refused.append(str(url.host))
            raise _stop("host_refused")
    return _request_guard


def _install_guard_and_import(state):
    import dotenv
    import dotenv.main
    a, b = dotenv.load_dotenv, dotenv.main.load_dotenv

    def _r():
        dotenv.load_dotenv = a
        dotenv.main.load_dotenv = b
    state["restore"].append(_r)
    had = "OPENAI_API_KEY" in os.environ
    state["restore"].append(lambda: None if had else os.environ.pop("OPENAI_API_KEY", None))
    # GC-14: the app's loggers and warnings are silenced for the rest of the run (restored in finally), so
    # a builder's capture error never reaches stderr; the one-line refusal / crash contract holds.
    prev_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    state["restore"].append(lambda: logging.disable(prev_disable))
    wcm = warnings.catch_warnings()
    wcm.__enter__()
    warnings.simplefilter("ignore")
    state["restore"].append(lambda: wcm.__exit__(None, None, None))
    _install_dotenv_guard()
    os.environ["OPENAI_API_KEY"] = OPENAI_IMPORT_PLACEHOLDER
    _import_app_modules()


def _loopback(host):
    return _is_loopback_name(_host_name(host))


def _port_443(port):
    try:
        return int(port) == 443
    except (TypeError, ValueError):
        return False


def _install_host_guard(ctx, state, live):
    """R-S07-26 (a) + GC-8: process-wide wrappers; live allows host_allowed, every other mode loopback only."""
    real_gai = socket.getaddrinfo
    real_conn = socket.socket.connect
    real_conn_ex = socket.socket.connect_ex
    real_cc = socket.create_connection
    # F-3 (b): the addresses the guarded resolver returned for ALLOWED_HOST in this process (live mode only)
    resolved = set()

    def allowed(host, port):
        return host_allowed(host, port) if live else _loopback(host)

    def connect_allowed(host, port):
        if _loopback(host):
            return True
        return live and _host_name(host) in resolved and _port_443(port)

    def refuse(host):
        name = _host_name(host)
        ctx.hosts_refused.append(name if name is not None else "<undecodable>")
        raise _stop("host_refused")

    def gai(host, port, *a, **k):
        if not allowed(host, port):
            refuse(host)
        res = real_gai(host, port, *a, **k)
        if live and _host_name(host) == ALLOWED_HOST:
            for row in res or []:
                try:
                    resolved.add(str(row[4][0]).strip().lower())
                except (IndexError, TypeError):
                    pass
        return res

    def _addr(addr):
        if isinstance(addr, tuple) and len(addr) >= 2:
            return addr[0], addr[1]
        return "localhost", None  # an AF_UNIX path: loopback-equivalent

    def conn(self, addr):
        h, p = _addr(addr)
        if not connect_allowed(h, p):
            refuse(h)
        return real_conn(self, addr)

    def conn_ex(self, addr):
        h, p = _addr(addr)
        if not connect_allowed(h, p):
            refuse(h)
        return real_conn_ex(self, addr)

    def cc(address, *a, **k):
        # create_connection resolves through the guarded getaddrinfo and connects through the wrapper above
        h, p = _addr(address)
        if not (allowed(h, p) or connect_allowed(h, p)):
            refuse(h)
        return real_cc(address, *a, **k)

    socket.getaddrinfo = gai
    socket.socket.connect = conn
    socket.socket.connect_ex = conn_ex
    socket.create_connection = cc

    def _r():
        socket.getaddrinfo = real_gai
        socket.socket.connect = real_conn
        socket.socket.connect_ex = real_conn_ex
        socket.create_connection = real_cc
    state["restore"].append(_r)


def _finish_partial(state, interrupted, reason=None):
    ctx = state.get("ctx")
    if ctx is not None:
        ctx.partial = True
        if reason and not ctx.stop_reason:
            ctx.stop_reason = reason
        try:
            ctx.write_results(None)
        except Exception:  # noqa: BLE001 - the partial write is best effort
            pass


def _write_crash(state, name):
    ctx = state.get("ctx")
    if ctx is not None:
        try:
            ctx.partial = True
            ctx.write_results(name)
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# the stage context
# ---------------------------------------------------------------------------
class _Ctx:
    def __init__(self, a, out, stage, unit_spent, stage_state):
        self.a = a
        self.out = out
        self.stage = stage
        self.dir = out / stage
        self.unit_spent_start = unit_spent
        self.stage_state = stage_state
        self.flags_removed = []
        self.flags_applied = {}
        self.not_runnable = None
        self.proxy_env_ignored = []
        self.hosts_refused = []
        self.scrub = _Scrub(None)
        self.dispatcher = None
        self.settings = {}
        self.stop_reason = None
        self.partial = False
        self.extra = {}
        self.n_run = None
        self.n_total = None
        self.plan = None
        self.base_sha = None
        self.case_lang = {}
        self.case_sensitive = {}
        self.gold = {}
        self.vision_expected = {}
        self.mod_expected = {}
        self._texts = {}

    # --- plan and run -----------------------------------------------------
    def run(self, client):
        dry = self.a["dry_run"]
        if dry:
            try:
                plan = asyncio.run(self.build_plan())
            except StageStop as s:  # GC-8: a refused host during the plan: no plan, exit by the reason
                self.stop_reason = s.reason
                self.partial = True
                self.write_results(None)
                return s.exit_code
            self.write_plan(plan)
            return EXIT_OK
        budget = Budget(self.a["max_usd"], self.stage_state["spent"], self.unit_spent_start)
        d = Dispatcher(client, budget, self.dir / "spend.jsonl", stage=self.stage, max_calls=self.a["max_calls"],
                       deadline_monotonic=_monotonic() + 60.0 * self.a["max_minutes"])
        d.completed = dict(self.stage_state["completed"])
        d.attempts = dict(self.stage_state["attempts"])
        d.scrub = self.scrub
        self.dispatcher = d
        code = EXIT_OK
        try:
            code = asyncio.run(self._run_live(d))
        except StageStop as s:
            self.stop_reason = s.reason
            self.partial = True
            code = s.exit_code
        except KeyboardInterrupt:
            self.partial = True
            raise
        except BaseException as exc:
            self.partial = True
            self.write_results(type(exc).__name__)
            raise
        self.write_results(None)
        return code

    async def _run_live(self, d):
        plan = await self.build_plan()
        for setting, items in plan:
            self.settings.setdefault(setting, {"stop_reason": None})
            try:
                await self.run_setting(d, setting, items)
            except StageStop as s:
                self.settings[setting]["stop_reason"] = s.reason
                if s.reason == "rate_limit":
                    continue
                raise
        return EXIT_OK

    def selected(self, names):
        sel = self.a.get("--settings")
        if not sel:
            return list(names)
        want = [x.strip() for x in sel.split(",") if x.strip()]
        return [n for n in names if n in want]

    async def build_plan(self):
        if self.stage == "text":
            return await _plan_text(self)
        if self.stage == "moderation":
            return await _plan_moderation(self)
        if self.stage == "vision":
            return await _plan_vision(self)
        return await _plan_web(self)

    def write_plan(self, plan):
        settings = {}
        total_calls = 0
        total = 0.0
        for setting, items in plan:
            calls = 0
            worst = 0.0
            for it in _flatten(items):
                calls += 1
                if it["kind"] not in ("count_tokens", "models_retrieve"):
                    worst += worst_case_usd(it["request"], it.get("uses", 0))
            settings[setting] = {"calls": calls, "worst_usd": round(worst, 6)}
            total_calls += calls
            total += worst
        self.dir.mkdir(parents=True, exist_ok=True)
        data = {"stage": self.stage, "settings": settings, "total_calls": total_calls,
                "total_worst_usd": round(total, 6), "max_usd": self.a["max_usd"]}
        (self.dir / "plan.json").write_text(json.dumps(data, sort_keys=True, indent=1), encoding="utf-8",
                                            newline="\n")

    async def run_setting(self, d, setting, items):
        if self.stage == "moderation":
            return await _run_moderation(self, d, setting, items)
        if setting == "A1_sites":
            return await _run_a1(self, d, setting, items)
        for it in items:
            await d._send(it["request"], setting=setting, site=it["site"], case_id=it["case_id"], rep=it["rep"],
                          kind=it["kind"], stream=it.get("stream", False))

    # --- outputs ----------------------------------------------------------
    def _pool(self):
        """The latest record per call of this run + the completed calls of earlier runs not re-sent."""
        d = self.dispatcher
        this = d.records if d else []
        latest = {}
        for r in this:
            latest[r["call_id"]] = r
        prior = [r for cid, r in (self.stage_state.get("completed") or {}).items() if cid not in latest]
        return this, prior + list(latest.values())

    def _text(self, rec):
        cid = rec["call_id"]
        if cid not in self._texts:
            data = self.dispatcher.raw_data(cid) if self.dispatcher else None
            blocks = (data or {}).get("content") or []
            self._texts[cid] = ("".join(b.get("text") or "" for b in blocks
                                        if isinstance(b, dict) and b.get("type") == "text") if data else None)
        return self._texts[cid]

    def _citations(self, rec):
        data = self.dispatcher.raw_data(rec["call_id"]) if self.dispatcher else None
        return sum(len(b.get("citations") or []) for b in ((data or {}).get("content") or [])
                   if isinstance(b, dict) and b.get("type") == "text")

    def summarize(self):
        out = {}
        this, pool = self._pool()
        for setting, meta in self.settings.items():
            rs = [r for r in this if r["setting"] == setting]
            ps = [r for r in pool if r["setting"] == setting]
            lat = _latencies_s(ps)
            n_cens = sum(1 for x in lat if math.isinf(x))
            entry = {"calls": len(rs), "ok": sum(1 for r in rs if r["ok"]),
                     "usd": round(sum(r["usd"] for r in rs), 6), "stop_reason": meta.get("stop_reason"),
                     "timeout_rate": (n_cens / len(ps)) if ps else 0.0, "n_censored": n_cens,
                     "p50_s": _fin(percentile(lat, 50)), "p95_s": _fin(percentile(lat, 95)),
                     "p99_s": _fin(percentile(lat, 99)),
                     "error_classes": _count(r["error_class"] for r in ps if r["error_class"]),
                     "site_latency_ms": _group(ps)}
            entry.update(self._metrics(setting, ps, meta))
            entry.update({k: v for k, v in meta.items() if k != "stop_reason"})
            entry["hosts_refused"] = list(self.hosts_refused)
            out[setting] = entry
        return out

    def _metrics(self, setting, ps, meta):
        """GC-12 / GC-13: the per-setting figures evaluate_role and the report read."""
        router = sys.modules.get("app.services.llm_router")
        sites_table = getattr(router, "SITES", {}) if router else {}
        if setting == "A1_sites":
            sites = {}
            for site in sorted({r["site"] for r in ps}):
                rs = [r for r in ps if r["site"] == site]
                spec = sites_table.get(site)
                expects_json = bool(getattr(spec, "expects_json", False))
                has_schema = spec is not None and spec.output_schema is not None
                lat = _latencies_s(rs)
                sites[site] = {
                    "n": len(rs),
                    "json_n": len(rs) if expects_json else 0,
                    "json_valid": sum(1 for r in rs if expects_json and r["ok"]
                                      and _parse_json(self._text(r)) is not None),
                    "schema_n": len(rs) if has_schema else 0,
                    "schema_accepted": sum(1 for r in rs if has_schema and r.get("status") != 400),
                    "max_tokens_hits": sum(1 for r in rs if r.get("stop_reason") == "max_tokens"),
                    "refusals": sum(1 for r in rs if r.get("stop_reason") == "refusal"),
                    "timeouts": sum(1 for r in rs if r.get("error_class") == "APITimeoutError"),
                    "p95_s": percentile(lat, 95), "p99_s": percentile(lat, 99)}
            out = {"sites": sites}
            out.update(self._a1_ledger_figures(setting))
            return out
        if setting == "A2_ttft":
            ttft = [r["ttft_ms"] / 1000.0 for r in ps if r.get("ttft_ms") is not None]
            return {"ttft_p50_s": percentile(ttft, 50), "ttft_p95_s": percentile(ttft, 95)}
        if setting == "A3_sonnet_between_tools":
            return {"n": len(ps), "accepted": sum(1 for r in ps if r["ok"]), "json_n": len(ps),
                    "json_valid": sum(1 for r in ps if r["ok"] and _parse_json(self._text(r)) is not None)}
        if setting == "A4_refusal_names":
            ar = [r for r in ps if self.case_lang.get(r["case_id"]) == "ar"]
            sens = [r for r in ps if self.case_sensitive.get(r["case_id"])]
            return {"n": len(ps), "refusals": sum(1 for r in ps if r.get("stop_reason") == "refusal"),
                    "n_arabic": len(ar), "refusals_arabic": sum(1 for r in ar if r.get("stop_reason") == "refusal"),
                    "n_sensitive": len(sens),
                    "refusals_sensitive": sum(1 for r in sens if r.get("stop_reason") == "refusal")}
        if setting == "A6_verdict_eval":
            winners = {}
            mism = scored = valid = 0
            for r in ps:
                obj = _parse_json(self._text(r)) if r["ok"] else None
                if obj is not None:
                    valid += 1
                wi = obj.get("winner_index") if isinstance(obj, dict) else None
                if isinstance(wi, bool) or wi not in (0, 1):
                    continue
                scored += 1
                winners[(r["case_id"], r["rep"])] = wi
                gold = self.gold.get(r["case_id"])
                if gold is not None and int(wi) != int(gold):
                    mism += 1
            pairs = [(winners[(c, 0)], winners[(c, 1)]) for (c, rep) in winners if rep == 0 and (c, 1) in winners]
            agreement = (sum(1 for a, b in pairs if a == b) / float(len(pairs))) if pairs else None
            return {"n": len(ps), "json_n": len(ps), "json_valid": valid, "mismatches": mism, "n_scored": scored,
                    "agreement": agreement, "refusals": sum(1 for r in ps if r.get("stop_reason") == "refusal"),
                    "timeouts": sum(1 for r in ps if r.get("error_class") == "APITimeoutError")}
        if setting == "M1_parity":
            fp = hits = benign = worthy = closed = 0
            for row in meta.get("cases") or []:
                if row["outcome"] == "not_run":
                    continue
                expected = self.mod_expected.get(row["id"])
                if row["outcome"] in ("unavailable", "malformed", "refusal"):
                    closed += 1
                if expected is False:
                    benign += 1
                    fp += 1 if row["outcome"] == "flagged" else 0
                elif expected is True:
                    worthy += 1
                    hits += 1 if row["outcome"] == "flagged" else 0
            return {"false_positives": fp, "n_benign_run": benign, "flagged_hits": hits, "n_flagworthy_run": worthy,
                    "fail_closed": closed, "p95_s": percentile(_latencies_s(ps), 95)}
        if setting.startswith("V"):
            hits = scored = 0
            for r in ps:
                exp = self.vision_expected.get(r["case_id"])
                if not r["ok"] or exp is None:
                    continue
                scored += 1
                hits += 1 if identity_hit(self._text(r), exp[0], exp[1]) else 0
            return {"hits": hits, "n_scored": scored, "hit_rate": (hits / float(scored)) if scored else None}
        if setting.startswith("W"):
            outcomes = [{"case_id": r["case_id"], "accepted": bool(r["ok"]), "error_class": r.get("error_class"),
                         "status": r.get("status"), "web_search_requests": int(r.get("web_search_requests") or 0),
                         "citations": self._citations(r) if r["ok"] else 0} for r in ps]
            return {"outcomes": outcomes, "accepted": sum(1 for o in outcomes if o["accepted"]),
                    "web_search_requests": sum(o["web_search_requests"] for o in outcomes),
                    "citations": sum(o["citations"] for o in outcomes)}
        return {}

    def _ledger_lines(self):
        """Every parsable line of this stage's ledger (every run of the folder); best effort."""
        p = self.dir / "spend.jsonl"
        out = []
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, ValueError):
            return out
        for line in text.splitlines():
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
        return out

    def _a1_ledger_figures(self, setting):
        """F-4 (b) the tail spans and F-5 (a) / (c) the cost per synthetic compare and the cache_read share,
        all from the LEDGER (every run of the folder), never from process memory."""
        lines = self._ledger_lines()
        tails = {}
        for x in lines:
            if x.get("state") == "tail" and x.get("setting") == setting:
                if x.get("censored"):
                    tails[x.get("round")] = math.inf
                elif x.get("span_ms") is None:
                    tails[x.get("round")] = None  # M-4 m6: a failed tail leg excludes the round
                else:
                    tails[x.get("round")] = float(x["span_ms"])
        spans = [tails[k] for k in sorted(tails) if tails[k] is not None]
        n_failed = sum(1 for k in tails if tails[k] is None)
        done = [x for x in lines if x.get("state") == "done" and x.get("setting") == setting]
        round_of = {}
        per_round = {}
        completed = {}
        for x in done:
            rid = str(x.get("case_id") or "").split(":")[0]
            round_of[x["call_id"]] = rid
            per_round[rid] = per_round.get(rid, 0.0) + float(x.get("usd") or 0.0)
            if x.get("ok") or x.get("error_class") in NON_TRANSIENT:
                completed.setdefault(rid, set()).add(x["call_id"])
        dones = {(x["call_id"], x.get("attempt")) for x in done}
        for x in lines:
            if x.get("state") == "sent" and x.get("setting") == setting and                     (x.get("call_id"), x.get("attempt")) not in dones and x.get("call_id") in round_of:
                rid = round_of[x["call_id"]]
                per_round[rid] = per_round.get(rid, 0.0) + float(x.get("worst_usd") or 0.0)
        n_calls = sum(len(i) if isinstance(i, tuple) else 1 for i in A1_ROUND_ORDER)
        costs = [per_round[rid] for rid in sorted(per_round) if len(completed.get(rid, ())) >= n_calls]
        p50, p95 = percentile(costs, 50), percentile(costs, 95)
        cost = {"n": len(costs), "p50_usd": None if p50 is None else round(p50, 9),
                "p95_usd": None if p95 is None else round(p95, 9)}
        tok = {}
        for x in done:
            t = tok.setdefault(x["site"], [0, 0])
            t[0] += int(x.get("cache_read_tokens") or 0)
            t[1] += int(x.get("input_tokens") or 0) + int(x.get("cache_write_tokens") or 0) +                 int(x.get("cache_read_tokens") or 0)
        share = {"pooled": _ratio(sum(v[0] for v in tok.values()), sum(v[1] for v in tok.values())),
                 "sites": {k: _ratio(v[0], v[1]) for k, v in sorted(tok.items())}}
        return {"tail_span_ms": spans, "tail_n_censored": sum(1 for x in spans if math.isinf(x)),
                "tail_n_failed": n_failed,
                "cost_per_compare": cost, "cache_read_share": share}

    def write_results(self, crash):
        self.dir.mkdir(parents=True, exist_ok=True)
        d = self.dispatcher
        spent = d.budget.spent if d else self.stage_state["spent"]
        unit = d.budget.unit_spent if d else self.unit_spent_start
        try:
            lp = importlib.import_module("app.services.llm_pricing") if "app.services.llm_pricing" in sys.modules \
                else None
        except Exception:  # noqa: BLE001
            lp = None
        res = {"base_sha": self.base_sha, "billing_assumption": BILLING_ASSUMPTION, "crash": crash,
               "env_var_name": ENV_VAR_NAME, "flags_applied": dict(self.flags_applied),
               "flags_case": "flags_file" if self.a.get("--flags-file") else "code_defaults",
               "flags_removed": list(self.flags_removed), "n_run": self.n_run, "n_total": self.n_total,
               "not_runnable": [self.not_runnable] if self.not_runnable else [], "out_dir": str(self.out),
               "price_table_as_of": getattr(lp, "ANTHROPIC_PRICE_TABLE_AS_OF", None) if lp else None,
               "proxy_env_ignored": list(self.proxy_env_ignored), "redactions": 0,
               "settings": self.summarize(), "spent_usd": round(spent, 6), "stage": self.stage,
               "stop_reason": self.stop_reason, "unit_spent_usd": round(unit, 6)}
        report = self.render_stage_report(res)
        res = self.scrub.obj(res)
        report = self.scrub.s(report)
        res["redactions"] = self.scrub.count
        (self.dir / "results.json").write_text(json.dumps(res, sort_keys=True, indent=1, default=str),
                                               encoding="utf-8", newline="\n")
        (self.dir / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")

    def render_stage_report(self, res):
        lines = ["# MEAS-CLAUDE-GATE stage report: %s" % self.stage, ""]
        if self.partial or self.stop_reason:
            lines.append("PARTIAL: stopped (%s)" % (self.stop_reason or "interrupted"))
        lines.append(REPORT_NAME_LINE)
        lines.append("Output folder: %s" % self.out)
        lines.append(FOLDER_SENTENCE)
        lines.append("Flags case: %s" % res["flags_case"])
        for k, v in sorted(self.flags_applied.items()):
            lines.append("- %s=%s" % (k, v))
        if self.not_runnable == "no_photo_set":
            lines += ["", "NOT RUNNABLE: the owner supplies --set <dir> holding 100 owner-taken packaging photos "
                      "(about 30 with Arabic labels) and a manifest.json of [{file, label_lang, expected_brand, "
                      "expected_name}]; no faces, no people, no personal data."]
        if self.not_runnable == "no_owner_line":
            lines += ["", "NOT RUNNABLE: the owner's dated line enabling web search is required (--owner-line)."]
        if res.get("n_total") is not None:
            lines.append("cases run: %s / %s" % (res["n_run"], res["n_total"]))
        lines += ["", "| setting | calls | ok | usd | stop |", "|---|---|---|---|---|"]
        for name, s in sorted(res["settings"].items()):
            lines.append("| %s | %s | %s | %s | %s |" % (name, s["calls"], s["ok"], s["usd"], s["stop_reason"]))
        return "\n".join(lines) + "\n"


def _fin(x):
    if x is None or math.isinf(x):
        return None
    return x


def _latencies_s(recs):
    """R-S07-19: latencies in seconds; a timeout is a sample at +infinity."""
    out = []
    for r in recs:
        if r.get("error_class") == "APITimeoutError":
            out.append(math.inf)
        elif r.get("latency_ms") is not None:
            out.append(float(r["latency_ms"]) / 1000.0)
    return out


def _count(xs):
    out = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out


def _group(rs):
    out = {}
    for r in rs:
        out.setdefault(r["site"], []).append(None if r.get("error_class") == "APITimeoutError" else r["latency_ms"])
    return out


def _flatten(items):
    for it in items:
        if isinstance(it, list):
            for x in _flatten(it):
                yield x
        else:
            yield it


def _fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# capture seam
# ---------------------------------------------------------------------------
class _Captured(Exception):
    pass


async def _capture(site, call):
    router = importlib.import_module("app.services.llm_router")
    mods = [importlib.import_module("app.services." + m) for m in
            ("extraction_service", "openai_service", "image_service", "url_extraction_service")]
    got = {}
    saved_route = router.route
    saved = []

    async def rec(s, dispatch, client, **kwargs):
        got.setdefault(s, kwargs)
        raise _Captured()

    router.route = rec
    for m in mods:
        for attr in ("get_client", "get_openai_client", "_get_client"):
            if hasattr(m, attr):
                saved.append((m, attr, getattr(m, attr)))
                setattr(m, attr, lambda *a, **k: object())
    try:
        try:
            await call()
        except Exception:  # noqa: BLE001 - the capture raises; a builder may wrap it
            pass
    finally:
        router.route = saved_route
        for m, attr, v in saved:
            setattr(m, attr, v)
    if site not in got:
        raise RuntimeError("builder_did_not_dispatch")
    return router.to_claude_request(site, got[site])


def _ctx_block(snips):
    return "<SEARCH_RESULTS>\n" + "\n".join("[snippet_%d] %s" % (i, s) for i, s in enumerate(snips)) + \
        "\n</SEARCH_RESULTS>"


def _full(p):
    return "%s %s" % (p.get("brand"), p.get("name"))


async def _a1_round(r, cp):
    es = importlib.import_module("app.services.extraction_service")
    osvc = importlib.import_module("app.services.openai_service")
    isvc = importlib.import_module("app.services.image_service")
    us = importlib.import_module("app.services.url_extraction_service")
    pa, pb = cp["product_a"], cp["product_b"]
    ca, cb = _ctx_block(cp["snippets_a"]), _ctx_block(cp["snippets_b"])
    ss = "%s: 72/100; %s: 75/100" % (_full(pa), _full(pb))

    def it(site, case, call):
        return {"site": site, "case_id": "r%02d:%s" % (r, case), "rep": 0, "kind": "create", "call": call}

    def per(p, c, tag):
        return [it("specs", tag, lambda: es.extract_specs(p["brand"], p["name"], p["variant"], "fragrances", c,
                                                          None, None))]

    spec = [
        it("classify", "x", lambda: es.classify_category_llm([_full(pa), _full(pb)])),
        it("parse", "x", lambda: es.parse_product_query("%s vs %s" % (_full(pa), _full(pb)))),
        per(pa, ca, "a") + per(pb, cb, "b")
        + [it("price", "a", lambda: es.extract_price(pa["brand"], pa["name"], pa["variant"], "bahrain", ca)),
           it("price", "b", lambda: es.extract_price(pb["brand"], pb["name"], pb["variant"], "bahrain", cb)),
           it("image_tier3", "a", lambda: isvc.extract_image_via_gpt(_full(pa), [
               {"title": _full(pa), "link": "https://example.com/a", "snippet": cp["snippets_a"][0]}])),
           it("image_tier3", "b", lambda: isvc.extract_image_via_gpt(_full(pb), [
               {"title": _full(pb), "link": "https://example.com/b", "snippet": cp["snippets_b"][0]}]))],
        [it("reviews", "a", lambda: es.extract_reviews(pa["brand"], pa["name"], pa["variant"], ca, "fragrances")),
         it("reviews", "b", lambda: es.extract_reviews(pb["brand"], pb["name"], pb["variant"], cb, "fragrances"))],
        # S81-07c (V5): request parity with production, which passes the scorer's winner index:
        # here the higher of the two synthetic scores above (75 > 72), product b = index 1.
        it("verdict", "x", lambda: es.generate_comparison(pa, pb, "bahrain", None, None, ss, "fragrances",
                                                          score_winner_index=1)),
        it("price_training", "x", lambda: es.extract_price_from_training_data(pa["brand"], pa["name"],
                                                                              pa["variant"], "bahrain")),
        it("specs_targeted", "x", lambda: osvc.extract_specs_targeted(pa["brand"], pa["name"], pa["variant"],
                                                                      "fragrances", ["top_notes"], ca)),
        it("specs_synthesized", "x", lambda: osvc.extract_specs_synthesized(pa["brand"], pa["name"],
                                                                            pa["variant"], "fragrances",
                                                                            ["top_notes"])),
        it("disambiguate", "x", lambda: osvc.disambiguate_variant_line("fragrances", _full(pa),
                                                                       _full(pa) + " Elixir 60ml",
                                                                       "concentration")),
        it("url_extract", "x", lambda: us.extract_with_ai("https://example.com/p/%d" % r,
                                                          "<html><h1>%s</h1><p>45 BHD</p></html>" % _full(pa),
                                                          "example", False)),
    ]
    out = []
    for item in spec:
        if isinstance(item, list):
            group = []
            for x in item:
                x["request"] = await _capture(x["site"], x.pop("call"))
                group.append(x)
            out.append(group)
        else:
            item["request"] = await _capture(item["site"], item.pop("call"))
            out.append(item)
    return out


async def _plan_text(ctx):
    router = importlib.import_module("app.services.llm_router")
    mc = importlib.import_module("app.services.model_config")
    es = importlib.import_module("app.services.extraction_service")
    pairs = _fixture("compare_pairs.json")
    plan = []
    sel = ctx.selected(TEXT_SETTINGS)
    rounds = None
    if any(s in sel for s in ("A1_sites", "A2_ttft", "A3_sonnet_between_tools", "A5_count_tokens")):
        rounds = [await _a1_round(r, pairs[r]) for r in range(20)]

    def verdict_of(rnd):
        return [x for x in rnd if isinstance(x, dict) and x["site"] == "verdict"][0]

    for s in sel:
        if s == "A0_capabilities":
            ids = []
            for role in ("text", "vision", "verdict", "critic", "moderation"):
                m = mc.anthropic_model(role)
                if m not in ids:
                    ids.append(m)
            esc = mc.anthropic_escalation_model()
            if esc not in ids:
                ids.append(esc)
            plan.append((s, [{"site": "models", "case_id": m, "rep": 0, "kind": "models_retrieve",
                              "request": {"model": m}} for m in ids]))
        elif s == "A1_sites":
            plan.append((s, rounds))
        elif s == "A2_ttft":
            items = []
            for r, rnd in enumerate(rounds):
                v = verdict_of(rnd)
                sp = rnd[2][0]
                items.append(dict(v, case_id="t%02d" % r, stream=True))
                items.append(dict(sp, case_id="t%02d" % r, stream=True))
            plan.append((s, items))
        elif s == "A3_sonnet_between_tools":
            plan.append((s, [dict(verdict_of(rnd), case_id="s%02d" % r,
                                  request=router._escalation_request(verdict_of(rnd)["request"]))
                             for r, rnd in enumerate(rounds)]))
        elif s == "A4_refusal_names":
            names = _fixture("fragrance_names.json")
            items = []
            for i in range(100):
                a, b = names[i], names[(i + 1) % 100]
                req = await _capture("parse", lambda a=a, b=b: es.parse_product_query("%s vs %s" % (
                    a["name"], b["name"])))
                lang = "ar" if "ar" in (a["lang"], b["lang"]) else "en"
                ctx.case_lang["n%03d" % i] = lang
                # F-5 (d): the sensitive-looking subset = a case whose either name's fixture group is 'sensitive'
                ctx.case_sensitive["n%03d" % i] = "sensitive" in (a.get("group"), b.get("group"))
                items.append({"site": "parse", "case_id": "n%03d" % i, "rep": 0, "kind": "create",
                              "request": req, "lang": lang})
            plan.append((s, items))
        elif s == "A5_count_tokens":
            items = []
            for r, rnd in enumerate(rounds):
                req = {k: v for k, v in verdict_of(rnd)["request"].items() if k != "max_tokens"}
                items.append({"site": "verdict", "case_id": "k%02d" % r, "rep": 0, "kind": "count_tokens",
                              "request": req})
            plan.append((s, items))
        elif s == "A6_verdict_eval":
            gold = _fixture("verdict_gold.json")
            items = []
            for case in gold:
                ctx.gold[case["case_id"]] = case["gold_winner_index"]
            for rep in range(ctx.a["reps"]):
                for case in gold:
                    # S81-07c (V5): the case's scorer winner (the gold field), as production passes it.
                    req = await _capture("verdict", lambda c=case: es.generate_comparison(
                        c["product_a"], c["product_b"], "bahrain", None, None, c["scores_summary"], "fragrances",
                        score_winner_index=c["gold_winner_index"]))
                    items.append({"site": "verdict", "case_id": case["case_id"], "rep": rep, "kind": "create",
                                  "request": req, "gold": case["gold_winner_index"]})
            plan.append((s, items))
    return plan


async def _run_a1(ctx, d, setting, rounds):
    for r, rnd in enumerate(rounds):
        if r > 0:
            await _sleep(ROUND_SPACING_S)
        p2 = None
        tail_ids = []
        for item in rnd:
            if isinstance(item, list):
                if item[0]["site"] == "reviews":
                    p2 = _monotonic()
                    tail_ids = [call_id_for(d.stage, setting, x["site"], x["case_id"], 0) for x in item]
                # GC-6: sends already made are awaited to their done line (never cancelled); a stop is sticky
                # in the dispatcher, so a task that had not sent yet raises it before reserving.
                res = await asyncio.gather(*[d.send(x["request"], setting=setting, site=x["site"],
                                                    case_id=x["case_id"], rep=0) for x in item],
                                           return_exceptions=True)
                crash = [x for x in res if isinstance(x, BaseException) and not isinstance(x, StageStop)]
                if crash:
                    raise crash[0]
                stops = [x for x in res if isinstance(x, StageStop)]
                if stops:
                    raise stops[0]
            else:
                await d.send(item["request"], setting=setting, site=item["site"], case_id=item["case_id"], rep=0)
                if item["site"] == "verdict" and p2 is not None:
                    span = round((_monotonic() - p2) * 1000.0, 3)
                    ids = tail_ids + [call_id_for(d.stage, setting, "verdict", item["case_id"], 0)]
                    # F-4 (a): only a round whose tail legs were all SENT in this process has a span
                    if all(c in d.sent_ids for c in ids):
                        legs = [d.last.get(c) or {} for c in ids]
                        censored = any(x.get("error_class") == "APITimeoutError" for x in legs)
                        # M-4 m6: a span only when the three tail legs all SUCCEEDED; a timed-out leg censors
                        # (it wins over another failure: fail-closed); any other failed leg excludes the round
                        failed = not censored and not all(x.get("ok") is True for x in legs)
                        d.write_tail(setting, item["case_id"].split(":")[0], span, censored, failed)


async def _plan_moderation(ctx):
    router = importlib.import_module("app.services.llm_router")
    path = Path(ctx.a["--set"]) if ctx.a.get("--set") else FIXTURES / "moderation_parity.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    ctx.cases = cases
    ctx.mod_expected = {c["id"]: c.get("expected_flagged") for c in cases}
    if not ctx.selected(("M1_parity",)):
        return []
    if not ctx.a["dry_run"]:
        return [("M1_parity", cases)]
    items = []
    saved = (router.guarded_anthropic_create, router.consume_escalation)
    for case in cases:
        state = {"used": False}

        async def fake(**kw):
            req = {"model": kw["model"], "messages": kw["messages"], "max_tokens": kw["max_tokens"],
                   "thinking": kw["thinking"], "output_config": kw["output_config"]}
            if kw.get("system"):
                req["system"] = kw["system"]
            items.append({"site": "moderation", "case_id": case["id"], "rep": len(items), "kind": "create",
                          "request": req})
            return router.ClaudeChatResult('{"flagged": false, "category": "none", "uncertain": true}', "stop",
                                           {}, kw["model"], "end_turn")

        def once(st=state):
            if st["used"]:
                return False
            st["used"] = True
            return True
        router.guarded_anthropic_create = fake
        router.consume_escalation = once
        try:
            await router.moderate_with_claude(case["text"])
        finally:
            router.guarded_anthropic_create, router.consume_escalation = saved
    return [("M1_parity", items)]


async def _run_moderation(ctx, d, setting, cases):
    router = importlib.import_module("app.services.llm_router")
    meta = ctx.settings[setting]
    rows = meta.setdefault("cases", [])
    ctx.n_total = len(cases)
    ctx.n_run = 0
    saved = (router.guarded_anthropic_create, router.consume_escalation)

    class _DispatchFailed(Exception):
        pass

    try:
        for i, case in enumerate(cases):
            state = {"used": False}

            async def fake(**kw):
                req = {"model": kw["model"], "messages": kw["messages"], "max_tokens": kw["max_tokens"],
                       "thinking": kw["thinking"], "output_config": kw["output_config"]}
                if kw.get("system"):
                    req["system"] = kw["system"]
                rep = 1 if kw.get("lane") == router.LANE_ESCALATION else 0
                rec, resp = await d._send(req, setting=setting, site="moderation", case_id=case["id"], rep=rep)
                if resp is None:
                    raise _DispatchFailed()
                if getattr(resp, "stop_reason", None) == "refusal":
                    raise router.AnthropicRefusalError()
                return router.ClaudeChatResult.from_message(resp, kw["model"], {})

            def once(st=state):
                if st["used"]:
                    return False
                st["used"] = True
                return True
            router.guarded_anthropic_create = fake
            router.consume_escalation = once
            try:
                allowed, reason = await router.moderate_with_claude(case["text"])
            except StageStop:
                for c in cases[i:]:
                    rows.append({"id": c["id"], "outcome": "not_run", "reason": None})
                raise
            ctx.n_run += 1
            if allowed:
                rows.append({"id": case["id"], "outcome": "allowed", "reason": None})
            elif reason in ("refusal", "unavailable", "malformed"):
                rows.append({"id": case["id"], "outcome": reason, "reason": reason})
            else:
                rows.append({"id": case["id"], "outcome": "flagged", "reason": reason})
    finally:
        router.guarded_anthropic_create, router.consume_escalation = saved


async def _plan_vision(ctx):
    router = importlib.import_module("app.services.llm_router")
    osvc = importlib.import_module("app.services.openai_service")
    d = Path(ctx.a["--set"])
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    v1, v2, v3 = [], [], []
    for row in manifest:
        ctx.vision_expected[row["file"]] = (row.get("expected_brand"), row.get("expected_name"))
        data = (d / row["file"]).read_bytes()
        mime = "image/png" if row["file"].lower().endswith(".png") else "image/jpeg"
        imgs = [{"bytes": data, "mime_type": mime}]
        r1 = await _capture("vision_v1", lambda: osvc.identify_products(imgs))
        r2 = await _capture("vision_v2", lambda: osvc._identify_products_v2(imgs))
        base = {"case_id": row["file"], "rep": 0, "kind": "create"}
        v1.append(dict(base, site="vision_v1", request=r1))
        v2.append(dict(base, site="vision_v2", request=r2))
        v3.append(dict(base, site="vision_v2", request=router._escalation_request(r2)))
    plan = [("V1_haiku_vision_v1", v1), ("V2_haiku_vision_v2", v2), ("V3_sonnet_vision_v2", v3)]
    keep = ctx.selected([name for name, _ in plan])
    return [(name, items) for name, items in plan if name in keep]


async def _plan_web(ctx):
    pairs = _fixture("compare_pairs.json")
    domains = _fixture("web_search_domains.json")
    es = importlib.import_module("app.services.extraction_service")
    pa = pairs[0]["product_a"]
    base = await _capture("price", lambda: es.extract_price(pa["brand"], pa["name"], pa["variant"], "bahrain",
                                                            _ctx_block(pairs[0]["snippets_a"])))
    schema = {"type": "object", "additionalProperties": False, "required": ["price", "currency", "source_url"],
              "properties": {"price": {"type": ["number", "null"]}, "currency": {"type": ["string", "null"]},
                             "source_url": {"type": ["string", "null"]}}}
    plan = []
    for t in WEB_SEARCH_TOOL_TYPES:
        tail = t.rsplit("_", 1)[1]
        tool = {"type": t, "name": "web_search", "max_uses": 1, "allowed_domains": list(domains)}
        one = dict(base, tools=[tool])
        fmt = dict(one, output_config=dict(base["output_config"], format={"type": "json_schema", "schema": schema}))
        plan.append(("W%d_one_turn_%s" % (len(plan) + 1, tail),
                     [{"site": "price", "case_id": "w%02d" % i, "rep": 0, "kind": "create", "request": one,
                       "uses": 1} for i in range(20)]))
        plan.append(("W%d_with_format_%s" % (len(plan) + 1, tail),
                     [{"site": "price", "case_id": "w%02d" % i, "rep": 0, "kind": "create", "request": fmt,
                       "uses": 1} for i in range(20)]))
    keep = ctx.selected([name for name, _ in plan])
    return [(name, items) for name, items in plan if name in keep]


# ---------------------------------------------------------------------------
# the top-level report
# ---------------------------------------------------------------------------
def _write_top_report(ctx):
    res = {}
    for st in ("text", "moderation", "vision", "web_search"):
        p = ctx.out / st / "results.json"
        if p.exists():
            res[st] = json.loads(p.read_text(encoding="utf-8"))
    lines = ["# MEAS-CLAUDE-GATE go / no-go", "", REPORT_NAME_LINE, "Output folder: %s" % ctx.out, FOLDER_SENTENCE,
             "Billing assumption (the only one): %s." % BILLING_ASSUMPTION,
             "The bars are PROPOSED pass bars (RULINGS_S81_07 R-S07-31); every raw figure is printed below, so a "
             "changed bar needs no second run.", "",
             "| role | verdict | failed bars | bars |", "|---|---|---|---|"]
    for role, bar in GO_THRESHOLDS.items():
        verdict, failed = evaluate_role(role, res)
        lines.append("| %s | %s | %s | %s |" % (role, verdict, ", ".join(failed) if failed else "-",
                                               json.dumps(bar, sort_keys=True) if bar else "none (not a flip bar)"))
    for st in ("text", "moderation", "vision", "web_search"):
        if st not in res:
            lines.append("- stage %s: NOT RUN (no results.json)" % st)
            continue
        r = res[st]
        lines.append("- stage %s: spent %s USD, stop %s, not runnable %s" % (
            st, r.get("spent_usd"), r.get("stop_reason"), r.get("not_runnable") or "no"))
    lines += ["", A6_SENTENCE,
              "Percentiles are nearest-rank with a timeout counted as +infinity; with n = 20, p99 = max (n = 20).",
              "", "## Raw figures", ""]
    for st in ("text", "moderation", "vision", "web_search"):
        for name, s in sorted(((res.get(st) or {}).get("settings") or {}).items()):
            keep = {k: v for k, v in s.items() if k not in ("site_latency_ms", "outcomes", "cases")}
            lines.append("- %s / %s: %s" % (st, name, json.dumps(keep, sort_keys=True, default=str)))
    a1 = (res.get("text") or {}).get("settings", {}).get("A1_sites", {})
    lines += ["", "## Reported figures (not bars)", ""]
    lines += _figure_lines(res)
    lines += ["", "## Timeout knob proposals (a knob changes only by the owner's dated line)", ""]
    cls = [x / 1000.0 if x is not None else math.inf for x in (a1.get("site_latency_ms") or {}).get("classify") or []]
    tail = [float(x) / 1000.0 for x in a1.get("tail_span_ms") or []]
    v2 = (res.get("vision") or {}).get("settings", {}).get("V2_haiku_vision_v2", {})
    vlat = [x / 1000.0 if x is not None else math.inf for x in (v2.get("site_latency_ms") or {}).get("vision_v2") or []]
    cp = timeout_proposal(cls) if cls else None
    vp = timeout_proposal(vlat) if vlat else None
    tp = timeout_proposal(tail, 95) if tail else None
    knobs = _current_knobs()
    lines.append("- ANTHROPIC_CLASSIFY_LLM_TIMEOUT: current %s, proposed %s (p99 x 1.25, n = %d, censored %d); %s"
                 % (knobs["classify"], _prop(cp), len(cls), sum(1 for x in cls if math.isinf(x)), KNOB_VALUE_LABEL))
    lines.append("- ANTHROPIC_VISION_TIMEOUT_SECONDS: current %s, proposed %s (p99 of vision_v2 x 1.25, n = %d, "
                 "censored %d); %s" % (knobs["vision"], _prop(vp), len(vlat), sum(1 for x in vlat if math.isinf(x)),
                                      KNOB_VALUE_LABEL))
    lines.append("- ANTHROPIC_TAIL_RESERVE_SECONDS: current %s, proposed %s (p95 of tail_span x 1.25, n = %d, "
                 "censored %d, rounds excluded for a failed tail leg %d; LLM legs only: no search, no scoring); %s"
                 % (knobs["tail"], _prop(tp), len(tail), sum(1 for x in tail if math.isinf(x)),
                    int(a1.get("tail_n_failed") or 0), KNOB_VALUE_LABEL))
    (ctx.out / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# M-4 m3: in a real run every ANTHROPIC_* name refuses the start, so the values read from the router are the
# code defaults; the report says so at the end of each knob line (R87 / R82 pin the line heads).
KNOB_VALUE_LABEL = ("current = the code default (a production override is not visible to this run: every "
                    "ANTHROPIC_* name refuses the start)")


def _current_knobs():
    """F-4 (d): the current knob values, read from the router the run imported (never literals of this script).
    classify_timeout returns its Claude-branch knob only when the text role decides anthropic, so the read
    asks it on that branch."""
    router = importlib.import_module("app.services.llm_router")
    saved = router.decide
    router.decide = lambda role: "anthropic"
    try:
        classify = router.classify_timeout(None)
    finally:
        router.decide = saved
    return {"classify": classify, "vision": router.vision_timeout(), "tail": router.tail_reserve_seconds_for_request()}


def _fmt_usd(x):
    return "NOT MEASURED" if x is None else "%.6f" % x


def _figure_lines(res):
    """F-5 and F-7 (e): the ruled figures, each reported, not a bar."""
    st = (res.get("text") or {}).get("settings") or {}
    a1 = st.get("A1_sites") or {}
    cost = a1.get("cost_per_compare") or {}
    p50, p95 = cost.get("p50_usd"), cost.get("p95_usd")
    out = ["- Cost per synthetic compare (an A1 round: the booked usd of its calls from the ledger, nearest-rank "
           "over the rounds that completed every call): p50 %s USD, p95 %s USD (n = %d)"
           % (_fmt_usd(p50), _fmt_usd(p95), int(cost.get("n") or 0))]
    sb = importlib.import_module("app.services.llm_spend_breaker")
    cap = sb.DEFAULT_CAPS_USD[sb.LANE_LIVE]

    def per_day(c):
        return "NOT MEASURED" if not c else "%d" % math.floor(cap / c)
    out.append("- Compares per day under the breaker's live-lane cap (code default, not the production value; "
               "recompute with the live value): cap %s USD; floor(cap / p95) = %s, floor(cap / p50) = %s"
               % (cap, per_day(p95), per_day(p50)))
    share = a1.get("cache_read_share") or {}
    sites = ", ".join("%s %s" % (k, v) for k, v in sorted((share.get("sites") or {}).items()))
    out.append("- cache_read share (cache-read input tokens / all input tokens: uncached + cache creation + "
               "cache read; A1 sites, from the ledger): pooled %s; %s" % (share.get("pooled"), sites or "none"))
    a4 = st.get("A4_refusal_names") or {}
    out.append("- A4 refusals (the bars are R-S07-23; the sensitive subset is reported, not a bar): all n = %s, "
               "refusals = %s; Arabic-script names n = %s, refusals = %s; sensitive-looking names n = %s, "
               "refusals = %s" % (a4.get("n"), a4.get("refusals"), a4.get("n_arabic"), a4.get("refusals_arabic"),
                                  a4.get("n_sensitive"), a4.get("refusals_sensitive")))
    out.append("- VISION hit rate = hits / n_scored: successful calls only (a failed call is not scored).")
    out.append("- A6 mismatch rate = mismatches / n_scored: successful calls whose winner_index parsed only.")
    return out


def _prop(x):
    if x is None:
        return "NOT MEASURED"
    if math.isinf(x):
        return "NOT PROPOSABLE (censored)"
    return "%.1f" % x


if __name__ == "__main__":
    sys.exit(main())
