"""Leaf helpers that make exception text safe for a log line (session 70, OAI_OBS item 3).

Two public helpers:

- ``safe_exc(exc)`` -- the R-W18 scrubber, moved here verbatim from
  ``structured_comparison_service`` (which re-exports it as ``_safe_exc``):
  URL userinfo, query string and fragment stripped, line breaks collapsed,
  truncated to 200 characters. Its output is unchanged for every input.
- ``exc_summary(exc)`` -- ``"<TypeName>: <scrubbed text>"``, or the bare
  ``<TypeName>`` when the text is empty. An httpx transport timeout or a
  no-arg ``TimeoutError()`` has an EMPTY ``str(e)``, so an f-string log line
  carried only its prefix (the empty-message Sentry issues). The text is
  scrubbed with the R-W18 URL scrub and then the Sentry key patterns
  (``sentry_service._scrub_string``), both over the FULL text, before the cut.

This module is a LEAF: its only imports are ``re`` and
``sentry_service._scrub_string`` (stdlib-only at its top), so
``serper_service`` and ``extraction_service`` import it at module top without
the ``structured_comparison_service`` import cycle.
"""
import re

from app.services.sentry_service import _scrub_string

# R-W18 (W1-8d) — bound + scrub exception text before it reaches an INFO drop
# line. LOCAL on purpose: sentry_service._scrub_query_string keeps `api_key=`
# and never strips URL userinfo (measured), so it cannot be reused here.
# Every `<scheme>://<token>` (http, https, socks5, ... — a proxy URL is the
# threat; the scheme quantifier is BOUNDED so a long letter run stays linear) is
# rewritten by _safe_exc_url: userinfo = everything up to the LAST '@' in the
# token, so a '@', '/' or ':' inside an unencoded password cannot leak its
# tail; the whole query string and fragment are dropped; host + path are kept.
# When the text before that '@' holds a '?' or '#', the '@' may sit in a query
# (`?email=a@b&k=SECRET`) or in a password (`user:pa?ss@host`) — the two cannot
# be told apart, so the whole token is replaced by `[redacted]`.
_SAFE_EXC_URL_RE = re.compile(r"(?i)([a-z][a-z0-9+.\-]{0,15}://)(\S*)")
_SAFE_EXC_LINEBREAK_RE = re.compile(r"[\r\n\x0b\x0c\x1c-\x1e\x85\u2028\u2029]+")
_SAFE_EXC_MAX_CHARS = 200


def _safe_exc_url(m: "re.Match[str]") -> str:
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


def _scrub_text(text: str) -> str:
    """The R-W18 text steps, in order: URL scrub, line-break collapse, then the
    200-character cut (always last, so a cut never lands inside a credential)."""
    text = _SAFE_EXC_URL_RE.sub(_safe_exc_url, text)
    text = _SAFE_EXC_LINEBREAK_RE.sub(" ", text)
    return text[:_SAFE_EXC_MAX_CHARS]


def safe_exc(exc: BaseException) -> str:
    """`str(exc)` made safe for a grep-stable INFO line: userinfo and the query
    string stripped from every http(s) URL, line breaks collapsed to one space,
    truncated to 200 chars. Scrubs the FULL text before truncating so a cut can
    never land inside a URL's credentials."""
    try:
        text = str(exc)
    except Exception:  # noqa: BLE001 — a broken __str__ must not break logging
        return f"<unprintable {type(exc).__name__}>"
    return _scrub_text(text)


def exc_summary(exc: BaseException) -> str:
    """The exception TYPE plus its scrubbed text, for a constant %-template log
    argument: ``"ReadTimeout"`` when ``str(exc)`` is empty or whitespace,
    otherwise ``"ValueError: bad"``.

    Scrub order: the R-W18 URL scrub (userinfo, query, fragment) and then the
    Sentry key shapes (``_scrub_string``: JWT, ``sk-proj-`` keys, ``fc-``
    keys, 32+ hex tokens, ``Bearer`` tokens), both on the FULL text; then the
    line-break collapse, leading whitespace dropped, and the 200-character
    cut LAST, so a cut can never land inside a credential. The URL scrub goes
    FIRST because a key-shape replacement can swallow the scheme of a URL
    glued to it (``Bearer https://u:p@h``, or a JWT / 32-hex run directly
    before ``https://``); the URL scrub would then no longer see
    ``scheme://`` and the userinfo would survive. Leading whitespace is
    dropped before the cut so it cannot use up the 200 characters. The type
    name is collapsed to one line as well. It only ever removes text that
    ``str(exc)`` already held, and never raises: a broken ``__str__`` yields
    ``"<unprintable TypeName>"``.
    """
    name = _SAFE_EXC_LINEBREAK_RE.sub(" ", type(exc).__name__)
    try:
        text = str(exc)
    except Exception:  # noqa: BLE001 — a broken __str__ must not break logging
        return f"<unprintable {name}>"
    text = _SAFE_EXC_URL_RE.sub(_safe_exc_url, text)
    text = _scrub_string(text)
    text = _SAFE_EXC_LINEBREAK_RE.sub(" ", text).lstrip()
    text = text[:_SAFE_EXC_MAX_CHARS]
    if not text.strip():
        return name
    return f"{name}: {text}"
