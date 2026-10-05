"""Sentry integration -- error monitoring and performance tracing."""
import os
import re
import sys
import copy
import logging
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

# Patterns to scrub from Sentry events.
# M4 (audit 2026-05-22): widened the generic hex pattern from {40,} to {32,}
# so 32-char lowercase Serper API keys (e.g., 1d3cf422...) get caught.
# Also added key-name scrubbing below so any value living in a dict key
# matching api_key / token / secret gets redacted regardless of format —
# defense-in-depth against future provider keys (Scrape.do, Upstash REST,
# etc.) that don't match any specific pattern here.
_SENSITIVE_PATTERNS = [
    (re.compile(r'eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+'), '[JWT_REDACTED]'),
    (re.compile(r'sk-proj-[A-Za-z0-9_-]+'), '[OPENAI_KEY_REDACTED]'),
    (re.compile(r'fc-[a-f0-9]{20,}'), '[FIRECRAWL_KEY_REDACTED]'),
    (re.compile(r'[a-f0-9]{32,}'), '[TOKEN_REDACTED]'),  # Generic long hex tokens (Serper 32+, SHA-256 64, etc.)
    (re.compile(r'Bearer\s+[A-Za-z0-9_.-]+'), 'Bearer [REDACTED]'),
]

# Bundle D Task 1.B.6 (R21) — query-string scrubbing for free-text user input.
# Targets the five param names that carry user-typed content in this API:
#   q, query, email, search, text
# Captures everything from `&<name>=` (or `?<name>=`) up to the next `&` or
# end-of-URL, replacing the value with [QUERY_REDACTED]. Preserves bookkeeping
# params (?nocache=, ?limit=, ?offset=, etc.) by NOT matching their names.
# `?token=` is already covered by the `_scrub_dict` key-name denylist below,
# but the wholesale `[a-f0-9]{32,}` token pattern also catches hex tokens that
# leak into URLs.
#
# U8d R4' (review correction 1, SR7): the SDK URL-DECODES the query string
# before before_send, so a user value holding an encoded `&` or `#` ("Dolce &
# Gabbana") splits into parts the old `[^&#]*` value pattern never reached. A
# query string is now REBUILT part by part: a PII key keeps its name with the
# value [QUERY_REDACTED]; a bookkeeping key is kept verbatim only when its
# value fully matches that key's grammar; every other part (a decoded remnant
# of a user value, an unknown key, an off-grammar value) is DROPPED, so a new
# user-content parameter fails closed instead of leaking.
_QUERY_STRING_PII_PARAMS = (
    "q", "query", "email", "search", "text", "product_a", "product_b", "url", "url1", "url2",
)
_QUERY_STRING_BOOKKEEPING_GRAMMAR = {
    "nocache": re.compile(r"(?i:true|false|1|0)"),
    "limit": re.compile(r"[0-9]{1,9}"),
    "offset": re.compile(r"[0-9]{1,9}"),
    "sort": re.compile(r"(?i:asc|desc)"),
    # The six GCC_REGIONS keys (extraction_service); any other word is dropped.
    "region": re.compile(r"(?:bahrain|saudi_arabia|uae|kuwait|qatar|oman)"),
    "lang": re.compile(r"[a-z]{2}(?:[-_][A-Za-z]{2})?"),
}
# Only for a string with no `?` (a URL never carries its query there); the
# Bundle D R21 value pattern, kept for that shape.
_QUERY_STRING_SCRUB_PATTERN = re.compile(
    r"(?<=[?&])(" + "|".join(_QUERY_STRING_PII_PARAMS) + r")=[^&#]*",
    re.IGNORECASE,
)


def _scrub_query_part(qs: str) -> str:
    """R4': rebuild a decoded query string (no leading `?`) from its kept
    parts, then run the secret patterns over the result."""
    kept = []
    for part in qs.split("&"):
        key, sep, value = part.partition("=")
        if not sep:
            continue
        if key.lower() in _QUERY_STRING_PII_PARAMS:
            kept.append(key + "=[QUERY_REDACTED]")
            continue
        grammar = _QUERY_STRING_BOOKKEEPING_GRAMMAR.get(key)
        if grammar is not None and grammar.fullmatch(value):
            kept.append(part)
    return _scrub_string("&".join(kept))


def _scrub_query_string(url: str) -> str:
    """Rebuild the query part of a URL with R4' (`?q=`, `?product_a=`, ...
    redacted, bookkeeping like `?nocache=true` or `?limit=20` kept, anything
    else dropped). Existing `?token=` handling also lives in `_scrub_dict`
    (key-name denylist) and the wholesale hex pattern.
    """
    if not url or not isinstance(url, str):
        return url
    if "?" not in url:
        if "=" not in url:
            # Neither a full URL with query string NOR a raw query_string field —
            # nothing to scrub.
            return url
        return _QUERY_STRING_SCRUB_PATTERN.sub(r"\1=[QUERY_REDACTED]", url)
    base, _, query = url.partition("?")
    query = _scrub_query_part(query)
    return base + "?" + query if query else base


def _scrub_raw_query_string(qs: str) -> str:
    """Scrub a RAW query-string fragment (no leading `?`).

    Bundle D R21 follow-up (Frontend cross-QA `c12a7c6` review): modern
    sentry-python populates `event.request.query_string` separately from
    `event.request.url` — a string like `q=foo&search=bar` with no `?`
    prefix. U8d R4': the same part-by-part rebuild as the query part of a URL.
    """
    if not qs:
        return qs
    # Bytes from some sentry-sdk versions — decode defensively.
    if isinstance(qs, (bytes, bytearray)):
        try:
            qs = qs.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            return qs
    if not isinstance(qs, str):
        return qs
    return _scrub_query_part(qs)

# Key-name denylist (case-insensitive substring match). When _scrub_dict
# encounters a string value under a key matching one of these, the whole
# value is replaced — regardless of whether the value itself matches a
# pattern above. Catches provider-specific tokens whose shape we don't
# explicitly pattern-match (e.g., Scrape.do, Upstash REST token, future).
_SENSITIVE_KEY_FRAGMENTS = ("api_key", "apikey", "token", "secret", "password")


def _scrub_string(value: str) -> str:
    """Remove sensitive patterns from a string."""
    for pattern, replacement in _SENSITIVE_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def _key_is_sensitive(key: str) -> bool:
    """True when a dict key name suggests its value is a secret."""
    lowered = key.lower()
    return any(frag in lowered for frag in _SENSITIVE_KEY_FRAGMENTS)


def _scrub_dict(data: dict) -> dict:
    """Recursively scrub sensitive values from a dict.

    M4 fix: if the key name suggests a secret (api_key / token / secret /
    password), redact the value wholesale even when the string content
    doesn't match a specific pattern.
    """
    scrubbed = {}
    for key, value in data.items():
        if isinstance(key, str) and _key_is_sensitive(key) and value is not None:
            scrubbed[key] = "[REDACTED]"
        elif isinstance(value, str):
            scrubbed[key] = _scrub_string(value)
        elif isinstance(value, dict):
            scrubbed[key] = _scrub_dict(value)
        elif isinstance(value, (list, tuple)):
            # TUPLES matter, not just lists (Fable review, W1-1): the logging
            # integration assigns `event['logentry']['params'] = record.args`,
            # and `record.args` is a TUPLE (measured). Without this branch a
            # `logger.warning('token=%s', tok)` shipped `tok` verbatim even
            # after the logentry walk added by this unit. Normalising to a
            # list is safe: the event is JSON-serialised downstream, where a
            # tuple and a list are the same array, and nothing reads it back.
            scrubbed[key] = [_scrub_dict(v) if isinstance(v, dict) else (_scrub_string(v) if isinstance(v, str) else v) for v in value]
        else:
            scrubbed[key] = value
    return scrubbed


# U8d R10 (review correction 3): every request header outside this allowlist
# ships "[Filtered]" -- the device fingerprint, client-IP headers the SDK does
# not filter (cf-connecting-ip, true-client-ip, forwarded, ...) and anything
# custom. The [REDACTED] names below keep their marker.
_REQUEST_HEADER_ALLOWLIST = frozenset({
    "host", "user-agent", "accept", "accept-encoding", "accept-language",
    "content-type", "content-length", "connection", "x-request-id",
})

# U8d R6: the capability token in a share / referral-invite path.
_CAPABILITY_PATH_RE = re.compile(r"(/api/v1/(?:share|referrals/invite)/)[^/?#]+")
# U8d R6 (FIX A5): GET /api/v1/text/prices/{product} carries the product query
# in its PATH -- the only free-text path parameter in app/api -- so the whole
# rest of the path is replaced (a decoded '#', '?' or '/' may be product text).
_FREE_TEXT_PATH_RE = re.compile(r"(/api/v1/text/prices/).+", re.DOTALL)

# U8d R5 (review correction 4): an outbound URL keeps scheme + host only; the
# path stays for these infrastructure hosts (triage). init_sentry adds the
# SUPABASE_URL and UPSTASH_REDIS_URL hosts once.
_INFRA_HOSTS_FIXED = ("api.openai.com", "google.serper.dev")
_INFRA_HOSTS = frozenset(_INFRA_HOSTS_FIXED)

# U8d R2: the handled-exception texts a log template may carry.
_HANDLED_TEXT_MIN_CHARS = 4
_HANDLED_CHAIN_MAX = 10
# SR3 (R11): no pattern scrub ever sees more than this much of one exception's
# text; a longer text is matched by its str / repr forms through plain string
# operations only.
_HANDLED_TEXT_SCRUB_CAP = 16384


def _fail_safe(rule, *args) -> None:
    """Run one U8d rule. An error inside it leaves the event to the scrub that
    ran before U8d; a scrub rule never raises and never drops an event."""
    try:
        rule(*args)
    except Exception:  # noqa: BLE001
        pass


def _scrub_capability_path(value):
    if isinstance(value, str):
        value = _CAPABILITY_PATH_RE.sub(r"\1[token]", value)
        return _FREE_TEXT_PATH_RE.sub(r"\1[product]", value)
    return value


def _exception_chain(exc) -> list:
    """exc, then its __cause__ (else __context__), at most 10 links, cycle-safe."""
    chain = []
    while isinstance(exc, BaseException) and len(chain) < _HANDLED_CHAIN_MAX:
        if any(exc is seen for seen in chain):
            break
        chain.append(exc)
        exc = exc.__cause__ if exc.__cause__ is not None else exc.__context__
    return chain


def _handled_text_forms(exc) -> list:
    """str(exc), repr(exc), safe_exc(exc) and the text part of exc_summary(exc).
    A broken __str__ / __repr__ is skipped, never raised."""
    forms = []
    try:
        forms.append(repr(exc))
    except Exception:  # noqa: BLE001
        pass
    try:
        text = str(exc)
    except Exception:  # noqa: BLE001
        return forms
    forms.append(text)
    try:
        # Lazy: log_scrub imports this module at its top.
        from app.services import log_scrub

        # safe_exc(exc), derived from at most 16,384 characters (SR3).
        forms.append(log_scrub._scrub_text(text[:_HANDLED_TEXT_SCRUB_CAP]))
        # exc_summary cuts its own input at 16,384 characters (SR3).
        forms.append(log_scrub.exc_summary(exc).partition(": ")[2])
    except Exception:  # noqa: BLE001
        pass
    return forms


def _handled_texts(hint) -> list:
    """R2: (text, "<TypeName>") for every exception currently handled --
    the chains of sys.exc_info(), hint["log_record"].exc_info and
    hint["exc_info"] -- each text at least 4 characters, longest first."""
    roots = [sys.exc_info()[1]]
    if isinstance(hint, dict):
        record_exc_info = getattr(hint.get("log_record"), "exc_info", None)
        for exc_info in (record_exc_info, hint.get("exc_info")):
            if isinstance(exc_info, tuple) and len(exc_info) > 1:
                roots.append(exc_info[1])
    seen = []
    pairs = {}
    for root in roots:
        for exc in _exception_chain(root):
            if any(exc is s for s in seen):
                continue
            seen.append(exc)
            placeholder = "<" + type(exc).__name__ + ">"
            for text in _handled_text_forms(exc):
                if isinstance(text, str) and len(text) >= _HANDLED_TEXT_MIN_CHARS:
                    pairs.setdefault(text, placeholder)
    return sorted(pairs.items(), key=lambda pair: -len(pair[0]))


def _redact_handled(value, texts):
    """Replace each occurrence of a handled text in value by its "<TypeName>"
    (plain string operations, longest text first; a placeholder already put in
    is never rewritten by a later, shorter text)."""
    if not texts or not isinstance(value, str):
        return value
    segments = [(value, False)]
    for text, placeholder in texts:
        rebuilt = []
        for segment, done in segments:
            if done or text not in segment:
                rebuilt.append((segment, done))
                continue
            for i, piece in enumerate(segment.split(text)):
                if i:
                    rebuilt.append((placeholder, True))
                if piece:
                    rebuilt.append((piece, False))
        segments = rebuilt
    return "".join(segment for segment, _ in segments)


def _redact_handled_param(param, texts):
    """A logentry param: a non-string, non-scalar param is rendered with repr
    first, so an exception object passed as a %-argument is matched too."""
    if param is None or isinstance(param, (bool, int, float)):
        return param
    if not isinstance(param, str):
        try:
            param = repr(param)
        except Exception:  # noqa: BLE001 -- left to the SDK's own safe repr
            return param
    return _redact_handled(param, texts)


def _outbound_url(url):
    """R5: scheme + host of an outbound URL (+ the path for an infra host);
    never userinfo, query or fragment. Unparseable -> "[Filtered]"."""
    if not isinstance(url, str) or not url:
        return url
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return "[Filtered]"
    if not parts.scheme or not host:
        return "[Filtered]"
    origin = parts.scheme + "://" + parts.netloc.rpartition("@")[2]
    return origin + parts.path if host in _INFRA_HOSTS else origin


def _outbound_description(description):
    """R5: an http span description "METHOD URL" keeps METHOD + _outbound_url."""
    if not isinstance(description, str):
        return description
    method, sep, target = description.partition(" ")
    if sep and "://" in target:
        return method + " " + _outbound_url(target)
    return description.split("?", 1)[0]


def _scrub_outbound_http_data(data) -> None:
    """R5 on an http span's / http breadcrumb's data: http.query keeps its keys
    with every value "[Filtered]", a fragment is "[Filtered]", url per
    _outbound_url. Nothing else in data is touched (review correction 5)."""
    if not isinstance(data, dict):
        return
    query = data.get("http.query")
    if isinstance(query, str) and query:
        data["http.query"] = "&".join(
            part.partition("=")[0] + "=[Filtered]" if "=" in part else "[Filtered]"
            for part in query.split("&")
        )
    if data.get("http.fragment"):
        data["http.fragment"] = "[Filtered]"
    if "url" in data:
        data["url"] = _outbound_url(data["url"])


def _is_http_breadcrumb(crumb) -> bool:
    return crumb.get("type") == "http" or crumb.get("category") == "httplib"


def _blank_exception_values(event) -> None:
    """R1: every exception value loses its text (type, module, mechanism and
    stacktrace stay), except an HTTPException, whose value is our own detail."""
    exception = event.get("exception")
    if not isinstance(exception, dict):
        return
    for exc in exception.get("values") or []:
        if isinstance(exc, dict) and "value" in exc and exc.get("type") != "HTTPException":
            exc["value"] = ""


def _event_breadcrumbs(event) -> list:
    breadcrumbs = event.get("breadcrumbs")
    if not isinstance(breadcrumbs, dict):
        return []
    return [crumb for crumb in breadcrumbs.get("values") or [] if isinstance(crumb, dict)]


def _redact_event_texts(event, hint) -> None:
    """R2 on an event: logentry message / formatted / params and breadcrumb
    messages."""
    texts = _handled_texts(hint)
    if not texts:
        return
    logentry = event.get("logentry")
    if isinstance(logentry, dict):
        for key in ("message", "formatted"):
            if isinstance(logentry.get(key), str):
                logentry[key] = _redact_handled(logentry[key], texts)
        params = logentry.get("params")
        if isinstance(params, dict):
            logentry["params"] = {k: _redact_handled_param(v, texts) for k, v in params.items()}
        elif isinstance(params, (list, tuple)):
            logentry["params"] = [_redact_handled_param(p, texts) for p in params]
    for crumb in _event_breadcrumbs(event):
        if isinstance(crumb.get("message"), str):
            crumb["message"] = _redact_handled(crumb["message"], texts)


def _scrub_breadcrumb_path(crumb) -> None:
    """R6 on a breadcrumb's data.path (FIX A9: the logging integration copies a
    record's extras into its breadcrumb's data, and ErrorHandlerMiddleware's
    ERROR line passes extra path=request.url.path)."""
    data = crumb.get("data")
    if isinstance(data, dict) and "path" in data:
        data["path"] = _scrub_capability_path(data["path"])


def _scrub_event_outbound_and_paths(event) -> None:
    """R5 on an event's http breadcrumbs, R6 on extra.path and crumb data.path."""
    for crumb in _event_breadcrumbs(event):
        _scrub_breadcrumb_path(crumb)
        if _is_http_breadcrumb(crumb):
            _scrub_outbound_http_data(crumb.get("data"))
    extra = event.get("extra")
    if isinstance(extra, dict) and "path" in extra:
        extra["path"] = _scrub_capability_path(extra["path"])


def _scrub_outbound_spans(event) -> None:
    """R5 on a transaction's http spans (description, url, http.query)."""
    for span in event.get("spans") or []:
        if isinstance(span, dict) and str(span.get("op") or "").startswith("http"):
            _scrub_outbound_http_data(span.get("data"))
            if "description" in span:
                span["description"] = _outbound_description(span["description"])


def _redact_breadcrumb(breadcrumb, hint) -> None:
    """R5 on an http breadcrumb and R2 on a breadcrumb message (before_breadcrumb
    runs inside the except arm the log line was written in)."""
    if _is_http_breadcrumb(breadcrumb):
        _scrub_outbound_http_data(breadcrumb.get("data"))
    if isinstance(breadcrumb.get("message"), str):
        breadcrumb["message"] = _redact_handled(breadcrumb["message"], _handled_texts(hint))


def _scrub_request_region(event) -> None:
    """Scrub ``event["request"]`` in place: secret headers, PII query strings,
    body and cookies.

    W1-1b: ONE helper shared by ``_before_send`` (error events) and
    ``_before_send_transaction`` (performance transactions) so the two hooks
    can never drift apart on what leaves the process in the request region.
    U8d adds R10 (header allowlist), R4' (query strings), R6 (capability path
    tokens) and R3's belt (no body) here, so both hooks get them.
    """
    if "request" in event:
        if "headers" in event["request"]:
            headers = event["request"]["headers"]
            if isinstance(headers, dict):
                for key in list(headers.keys()):
                    # W4-13 (ruling D4): X-Qaren-Synthetic carries SEARCH_LOG_SYNTHETIC_TOKEN.
                    if key.lower() in ("authorization", "x-admin-key", "cookie", "x-qaren-synthetic"):
                        headers[key] = "[REDACTED]"
                    elif key.lower() not in _REQUEST_HEADER_ALLOWLIST:
                        headers[key] = "[Filtered]"
        # Bundle D Task 1.B.6 (R21) — scrub PII query-string values from request URL
        if isinstance(event["request"].get("url"), str):
            event["request"]["url"] = _scrub_capability_path(_scrub_query_string(event["request"]["url"]))
        # Bundle D R21 follow-up (Frontend cross-QA review on c12a7c6):
        # modern sentry-python FastAPI/Starlette integrations populate
        # `request.query_string` separately as raw `key=val&key2=val2`
        # (no leading `?`), so route it through _scrub_raw_query_string (U8d
        # R4': the same part-by-part rebuild as the query part of a URL).
        raw_qs = event["request"].get("query_string")
        if raw_qs is not None:
            event["request"]["query_string"] = _scrub_raw_query_string(raw_qs)
        # CR-SECURITY-03: request body + cookies were never walked. A JWT in a
        # login body or a session cookie reached Sentry verbatim.
        for _req_key in ("data", "cookies"):
            _req_val = event["request"].get(_req_key)
            if isinstance(_req_val, dict):
                event["request"][_req_key] = _scrub_dict(_req_val)
            elif isinstance(_req_val, str):
                event["request"][_req_key] = _scrub_string(_req_val)
        # U8d R3: the belt to max_request_body_size="never" -- a body that
        # reached the event anyway never leaves the process.
        if "data" in event["request"]:
            event["request"]["data"] = "[Filtered]"


def _before_send_transaction(event, hint):
    """Scrub the request region of a performance TRANSACTION before sending.

    W1-1b: ``before_send`` is never called for transactions, and the SDK's own
    header filter does not list ``x-admin-key``, so every sampled transaction
    for an authenticated admin request shipped the operator's key verbatim in
    ``request.headers`` (measured on sentry-sdk 2.68.1). This applies exactly
    the request-region scrub ``_before_send`` applies and nothing else:
    the trace ids, spans and contexts are left alone (a rewritten trace_id
    orphans the trace), and the 503 drop is NOT applied -- that drop exists to
    keep deliberate 503s out of the ERROR stream, not the performance stream.
    U8d R5: outbound http spans lose their query values and user URL paths.
    """
    _fail_safe(_scrub_outbound_spans, event)
    _scrub_request_region(event)
    return event


def _before_send(event, hint):
    """Scrub sensitive data from Sentry events before sending.

    Also drops the DELIBERATE transient 503s (the genuine-bh-latency bundle's
    TIMEOUT graceful-timeout surface + FEATURE_DISABLED gated routes). The
    Starlette/FastAPI integration's default ``failed_request_status_codes``
    captures every 5xx, so changing the timeout surface from 400 -> 503 would
    otherwise flood Sentry with expected, user-facing-graceful responses and
    bury real 500s. We exclude 503 at the integration level too (init_sentry);
    this is the version-independent backstop. Timeout frequency stays visible
    via the ``[L2.7]`` hard-cap WARNING in Railway logs, and genuine crashes
    still surface as 500 (ErrorHandlerMiddleware ``capture_exception``).
    """
    # Drop deliberate transient 503s (TIMEOUT / FEATURE_DISABLED) — not bugs.
    try:
        _resp = (event.get("contexts") or {}).get("response") or {}
        if int(_resp.get("status_code")) == 503:
            return None
    except (TypeError, ValueError):
        pass
    # U8d (review correction 6): R1 and R2 run BEFORE every pattern pass below,
    # so a pattern replacement inside an exception text can never break R2's
    # exact match and leave the rest of the text behind.
    _fail_safe(_blank_exception_values, event)
    _fail_safe(_redact_event_texts, event, hint)
    _fail_safe(_scrub_event_outbound_and_paths, event)
    # Scrub exception values
    if "exception" in event:
        for exc in event["exception"].get("values", []):
            if "value" in exc and isinstance(exc["value"], str):
                exc["value"] = _scrub_string(exc["value"])
            # CR-SECURITY-03: stack-frame LOCALS. `include_local_variables=False`
            # in init_sentry is the primary fix (it stops the SDK collecting
            # these at all); this walk is the belt to that pair of braces, for
            # any event that reaches _before_send with frame vars already on it.
            frames = (exc.get("stacktrace") or {}).get("frames") or []
            for frame in frames:
                if isinstance(frame, dict) and isinstance(frame.get("vars"), dict):
                    frame["vars"] = _scrub_dict(frame["vars"])
    # Scrub breadcrumbs
    if "breadcrumbs" in event:
        for crumb in event["breadcrumbs"].get("values", []):
            if "data" in crumb and isinstance(crumb["data"], dict):
                crumb["data"] = _scrub_dict(crumb["data"])
            if "message" in crumb and isinstance(crumb["message"], str):
                crumb["message"] = _scrub_string(crumb["message"])
    # Scrub request headers + query-string
    _scrub_request_region(event)
    # CR-SECURITY-03: the remaining regions a secret can ride in. Scrub the
    # secret PATTERNS inside them with the existing helpers — do NOT blank the
    # regions. `contexts` in particular carries the runtime/OS/response metadata
    # that makes an event triageable, and the 503-drop branch above READS
    # contexts.response.status_code (it runs first, so the walk cannot disturb
    # it). _scrub_dict passes non-str values (ints, bools, None) through
    # untouched, so status_code stays an int and the structure stays nested.
    event_contexts_original = copy.deepcopy(event.get("contexts")) if isinstance(event.get("contexts"), dict) else None
    for _region in ("extra", "contexts", "logentry", "tags", "user"):
        _value = event.get(_region)
        if isinstance(_value, dict):
            event[_region] = _scrub_dict(_value)
    # Fable review (W1-1): PUT THE TRACE CORRELATION IDS BACK.
    # A Sentry `trace_id` is `uuid4().hex` — 32 lowercase hex characters — which
    # the pre-existing generic token pattern `[a-f0-9]{32,}` matches
    # unconditionally, so the walk above rewrote it to `[TOKEN_REDACTED]` on
    # EVERY error event (measured). Relay treats an invalid trace_id as a
    # normalization error and drops the trace context, which would orphan every
    # backend error from its transaction and from the mobile->backend
    # distributed trace — silently degrading the observability this campaign
    # relies on to read its own canaries, as a side effect of the OPTIONAL belt
    # half of a security fix.
    # Only these three fields are restored, and only from `contexts.trace`:
    # they are SDK-generated correlation ids, never user input. Everything else
    # under `contexts.trace` (notably `data`, which carries app-set span
    # attributes) stays scrubbed.
    _orig_trace = ((event_contexts_original or {}).get("trace") or {})
    _new_trace = ((event.get("contexts") or {}).get("trace") or {})
    if isinstance(_orig_trace, dict) and isinstance(_new_trace, dict):
        for _id_field in ("trace_id", "span_id", "parent_span_id"):
            if _id_field in _orig_trace:
                _new_trace[_id_field] = _orig_trace[_id_field]
    return event


def _strip_tokens_from_breadcrumb(breadcrumb, hint):
    """Redact tokens + PII query strings from Sentry breadcrumb URLs; U8d R2
    (handled exception text) and R5 (outbound http data) first, and R6 on
    data.path (its own fail-safe rule, so a failing R2 never skips it)."""
    _fail_safe(_scrub_breadcrumb_path, breadcrumb)
    _fail_safe(_redact_breadcrumb, breadcrumb, hint)
    if breadcrumb.get("data") and isinstance(breadcrumb["data"], dict):
        url = breadcrumb["data"].get("url", "")
        if url:
            # Bundle D R21: scrub PII query-string values BEFORE token-pattern
            # scrub so a URL like `?q=eyJabc...` doesn't get masked by the JWT
            # pattern but then leak the rest of the query value.
            url = _scrub_query_string(url)
            breadcrumb["data"]["url"] = _scrub_string(url)
    return breadcrumb


def _infra_hosts_from_env() -> frozenset:
    """R5: the infrastructure hosts whose outbound URL path stays readable --
    the fixed provider hosts plus the HOST NAMES of SUPABASE_URL and
    UPSTASH_REDIS_URL (never a URL, a path or a credential)."""
    hosts = set(_INFRA_HOSTS_FIXED)
    for name in ("SUPABASE_URL", "UPSTASH_REDIS_URL"):
        try:
            host = urlsplit(os.getenv(name, "")).hostname
        except ValueError:
            host = None
        if host:
            hosts.add(host)
    return frozenset(hosts)


def init_sentry():
    """Initialize Sentry SDK. No-op if SENTRY_DSN not set."""
    global _INFRA_HOSTS
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        logger.info("SENTRY_DSN not set -- Sentry disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        _INFRA_HOSTS = _infra_hosts_from_env()

        # Capture 5xx as failed requests EXCEPT 503 — in this app a 503 is only
        # ever returned deliberately (TIMEOUT graceful-timeout from the
        # genuine-bh-latency bundle + FEATURE_DISABLED gated routes), so it is an
        # expected transient, not a bug. Keeping it in Sentry floods the error
        # stream and buries real 500s. Real crashes surface as 500 and are kept.
        _captured_5xx = frozenset(range(500, 600)) - {503}
        integrations = [
            FastApiIntegration(
                transaction_style="endpoint",
                failed_request_status_codes=_captured_5xx,
            ),
            StarletteIntegration(
                transaction_style="endpoint",
                failed_request_status_codes=_captured_5xx,
            ),
            # U8d R7 (SR2, Q4): only ERROR log lines become breadcrumbs, so
            # no INFO / WARNING line (user queries, product names, URLs,
            # exception text) reaches an event. The event level stays the
            # SDK default, ERROR.
            LoggingIntegration(level=logging.ERROR),
        ]
        # U8d SR8: prompts and completions never leave the process, even if
        # send_default_pii is ever turned on. FIX B4: its own try -- sentry_sdk
        # raises DidNotEnable on this import when openai cannot load, and that
        # must not disable Sentry (an integration that cannot load cannot send
        # prompts either; the SDK's own auto-enable skips it the same way).
        try:
            from sentry_sdk.integrations.openai import OpenAIIntegration

            integrations.append(OpenAIIntegration(include_prompts=False))
        except Exception:  # noqa: BLE001
            pass
        sentry_sdk.init(
            dsn=dsn,
            integrations=integrations,
            traces_sample_rate=0.1,
            environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
            release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown"),
            send_default_pii=False,
            # CR-SECURITY-03 (the PRIMARY fix): the SDK default is True, so
            # every captured 5xx shipped the raising frame's locals. This
            # service holds the admin key, user JWTs, Supabase service keys and
            # provider API keys as ordinary locals across most modules, so a
            # scrub-by-name alternative has to be complete AND stay complete —
            # one new local named `api_key_v2` would re-open it silently. False
            # fails safe by construction. The exception value, the breadcrumbs,
            # the request metadata and the log message all survive, which is
            # what actually identifies a crash. Deliberate trade: stack traces
            # lose local variables, which costs debuggability.
            include_local_variables=False,
            # U8d R3: the SDK never reads a request body (the request-region
            # belt filters any body that arrives anyway).
            max_request_body_size="never",
            # U8d R12 (SR4): no sentry-trace / baggage header (public key,
            # transaction name, release) to any outbound host; the backend
            # calls no Sentry-instrumented service of ours.
            trace_propagation_targets=[],
            before_send=_before_send,
            # W1-1b: transactions never pass through before_send.
            before_send_transaction=_before_send_transaction,
            before_breadcrumb=_strip_tokens_from_breadcrumb,
        )
        logger.info("Sentry initialized successfully")
    except ImportError:
        logger.warning("sentry-sdk not installed -- Sentry disabled")
    except Exception as e:
        logger.warning(f"Sentry init failed: {e}")
