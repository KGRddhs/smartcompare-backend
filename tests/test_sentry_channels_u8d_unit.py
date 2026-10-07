"""U8d (S72, issue #311): the IN-PROCESS half -- direct calls of the Sentry
hooks, the AST pins over app/, and the option pins taken from the kwargs the
real ``init_sentry()`` passes to ``sentry_sdk.init`` (recorded, never run).

SPEC SET (later wins): docs/investigations/2026-10-05-session-72-state/specs/
U8D_SENTRY_CHANNELS_SPEC.md, U8D_SENTRY_CHANNELS_REVIEW.md (corrections 1-14),
FABLE_RULINGS_U8D.md (SR1-SR14). The child-process half is
tests/test_sentry_channels_u8d.py.

No Sentry client is ever installed in this process: hooks are plain functions,
and ``init_sentry()`` runs against a monkeypatched ``sentry_sdk.init`` that
only records its kwargs. Every hook is resolved THROUGH THE MODULE AT CALL TIME
(``_ss()``), never bound at collection (spec edge case 12: test_observability
and test_retro_w1_1 reload ``sentry_service``). Every sentinel is built at run
time by concatenation or as a hash digest; no credential-shaped literal is in
this file.

RULE -> NODES -> MUTANTS (spec M1-M15, review M16-M21, SR3, SR4, SR8):

| rule | nodes (this file) | kills |
|---|---|---|
| R1 | red_r1_value_blanked_type_kept, red_r1_notes_blanked, red_r1_chain_blanked_http_kept ; pin_r1_http_exception_detail_kept[*], pin_r1_503_dropped_first | M1 ; M2 (pin + U8c red2) |
| R2 sources | red_r2_sys_exc_info, red_r2_log_record_exc_info, red_r2_hint_exc_info, red_r2_params[*], red_r2_chain_cause, red_r2_safe_exc_form, red_r2_exc_summary_text_form | M3 (all), M4 (red_r2_sys_exc_info) |
| R2 crumb half | red_r2_breadcrumb_message, red_r2_breadcrumb_ordering | M5 |
| R2 ordering (review 6) | red_r2_ordering_hex_and_email, red_r2_breadcrumb_ordering | M16 |
| R2 edge cases | pin_edge1_short_text_not_replaced (M6), red_edge1_four_chars_replaced, red_edge2_text_inside_template, pin_edge3_broken_str_repr_never_raises (M15), pin_edge4_cyclic_chain_bounded, pin_clean_templates_unchanged[*] | M6, M15 |
| R3 belt | red_r3_belt_request_data_filtered[*] ; pin_r3_hooks_share_request_region | M8 |
| R4' | red_r4p_query_string[*], red_r4p_url_form, red_r4p_transaction_hook ; pin_r4p_r21_contract[*], pin_edge10_bytes_query_string | M9 (product_a_amp), M18 (amp_hash, product_a_amp) |
| R5 | red_r5_span_user_path, red_r5_span_query_values, red_r5_crumb[*] ; pin_r5_openai_token_counts_survive | M10, M11, M20 ; M17 |
| R6 | red_r6_capability_token[*] | M12 |
| R7 / R3 option / R12 / SR8 options | red_options_init_kwargs[*] ; pin_options_init_kwargs_kept | M7, M13, M-SR4, M-SR8 |
| R8 seven lines | red_r8_in_except_lines_no_user_content[*] (4), red_r8_outside_except_error_lines_type_only[*] (2 modules, 3 statements) ; pin_r8_no_other_outside_except_error_line ; red_r8_fetch_page_logs_host_only | M14 (l2_7), M21 (structured_comparison_service) |
| R10 | red_r10_header_filtered[*] ; pin_r10_allowlist_and_redacted_names[*] | M19 |
| R11 (SR3) | red_sr3_exc_summary_scrub_input_capped, red_sr3_r2_helper_scrub_input_capped ; pin_sr3_exc_summary_unchanged_up_to_cap[*] | M-SR3 (cap removed) |
| review 8 | pin_http_exception_5xx_details_are_literal | a computed 5xx detail |
| harness | pin_sentinels_survive_scrub_string, pin_hooks_resolved_at_call_time | a broken harness |

RED nodes fail at base 845ece15 because the sentinel (or the raw text) is in
the hook's output, or because an option / statement shape is absent. PIN nodes
pass at base and must pass after GREEN.
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import importlib
import json
import logging
import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = REPO_ROOT / "app"
CAP = 16384

# ---------------------------------------------------------------- sentinels
SENT = "quill" + "beacon"
EMAIL = "harbor.owl" + "@" + "fjord" + ".example"
EMAIL_PCT = EMAIL.replace("@", "%40")
HOST = "glacierproj" + ".supabase" + ".example"
QWORD = "zephyr" + "quokka"
QWORD2 = "wombat" + "saffron"
QWORD3 = "ibis" + "cobalt"
TOK = "tok" + "quasar" + "lumen" + "77"
SHTOK = "Shr" + "Pelican" + "Tundra" + "Kx9_ab"
IP = "203.0.113" + "." + "77"
NOTE = "puffin" + "meadow"
FP = hashlib.sha256(("otter" + "device").encode("utf-8")).hexdigest()
HEX32 = hashlib.md5(("u8d" + "-hex-run").encode("utf-8")).hexdigest()
PLAIN = [SENT, EMAIL, HOST, QWORD, QWORD2, QWORD3, TOK, SHTOK, IP, NOTE]
# Review correction 6: a 32-hex run and an email, longer than 200 characters.
ORDERING_TEXT = "upstream rejected key " + HEX32 + " after " + "retry " * 40 + "for " + EMAIL


def _ss():
    """sentry_service, resolved at CALL time (spec edge case 12)."""
    return importlib.import_module("app.services.sentry_service")


def _ls():
    return importlib.import_module("app.services.log_scrub")


_NAMES = {SENT: "SENT", EMAIL: "EMAIL", EMAIL_PCT: "EMAIL_PCT", HOST: "HOST", QWORD: "QWORD", QWORD2: "QWORD2",
          QWORD3: "QWORD3", TOK: "TOK", SHTOK: "SHTOK", IP: "IP", NOTE: "NOTE", FP: "FP", HEX32: "HEX32"}


def _dump(obj) -> str:
    return json.dumps(obj, default=repr)


def _san(obj) -> str:
    """Assertion-message form: every sentinel replaced by its <NAME>."""
    text = obj if isinstance(obj, str) else _dump(obj)
    for value, name in sorted(_NAMES.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(re.escape(value), "<" + name + ">", text, flags=re.IGNORECASE)
    return text


def _found(obj, needles) -> list:
    """The NAMES of the sentinels present in obj (never the values)."""
    text = _dump(obj).lower()
    return [_NAMES.get(n, "?") for n in needles if n.lower() in text]


def _logevent(text: str, params=None) -> dict:
    le = {"message": text, "formatted": text}
    if params is not None:
        le["params"] = params
    return {"logentry": le, "logger": "app.services.cache_service", "level": "error"}


def _exc_info_of(exc):
    try:
        raise exc
    except BaseException:  # noqa: BLE001
        return sys.exc_info()


# ======================================================================= R1

class TestR1ExceptionValues:

    def test_u8d_red_r1_value_blanked_type_kept(self):
        """R1: value '' ; type, module, mechanism, stacktrace kept. Base: the
        raw text (not pattern-shaped) survives _scrub_string."""
        frames = [{"filename": "app/services/cache_service.py", "function": "delete_cached", "lineno": 679}]
        ev = {"exception": {"values": [{
            "type": "RuntimeError", "module": "builtins", "value": "boom " + SENT + " " + EMAIL,
            "mechanism": {"type": "logging", "handled": True}, "stacktrace": {"frames": frames},
        }]}}
        v = _ss()._before_send(ev, {})["exception"]["values"][0]
        assert _found(v, [SENT, EMAIL]) == [], f"[R1] sentinel(s) kept in the exception value: {_found(v, [SENT, EMAIL])}"
        assert v["value"] == ""
        assert (v["type"], v["module"], v["mechanism"], v["stacktrace"]["frames"]) == (
            "RuntimeError", "builtins", {"type": "logging", "handled": True}, frames)

    def test_u8d_red_r1_notes_blanked(self):
        """R1: __notes__ the SDK appends to the value go with it."""
        ev = {"exception": {"values": [{"type": "ValueError", "value": "bad\nnote " + SENT}]}}
        v = _ss()._before_send(ev, {})["exception"]["values"][0]
        assert _found(v, [SENT]) == [], "[R1] a __notes__ sentinel survived"
        assert v["value"] == ""

    def test_u8d_red_r1_chain_blanked_http_kept(self):
        """R1 + Q3 (chains kept): every non-HTTPException value of the chain is
        '', the HTTPException literal detail stays."""
        detail = "{'code': 'SHARE_TOKEN_FAILED', 'error': 'Failed to create share link'}"
        ev = {"exception": {"values": [
            {"type": "APIError", "value": "dup " + SENT},
            {"type": "ShareTokenError", "value": "share_token write failed: Key (share_token)=(" + SHTOK + ")"},
            {"type": "HTTPException", "value": detail},
        ]}}
        vals = _ss()._before_send(ev, {})["exception"]["values"]
        assert _found(vals, [SENT, SHTOK]) == [], f"[R1] chain text kept: {_found(vals, [SENT, SHTOK])}"
        assert [(v["type"], v["value"]) for v in vals] == [
            ("APIError", ""), ("ShareTokenError", ""), ("HTTPException", detail)]

    @pytest.mark.parametrize(
        "detail",
        ["Account deletion failed", "{'code': 'INTERNAL_ERROR', 'error': 'Failed to register push token'}"],
        ids=["str_detail", "dict_detail"],
    )
    def test_u8d_pin_r1_http_exception_detail_kept(self, detail):
        """R1 exemption (spec edge case 8, M2): our own literal detail is kept."""
        ev = {"exception": {"values": [{"type": "HTTPException", "value": detail}]}}
        assert _ss()._before_send(ev, {})["exception"]["values"][0]["value"] == detail

    def test_u8d_pin_r1_503_dropped_first(self):
        """Spec edge case 9: a 503 is still dropped first."""
        ev = {"contexts": {"response": {"status_code": 503}},
              "exception": {"values": [{"type": "RuntimeError", "value": "x " + SENT}]}}
        assert _ss()._before_send(ev, {}) is None


# ======================================================================= R2

class TestR2HandledText:

    def test_u8d_red_r2_sys_exc_info(self):
        """R2 source 1: sys.exc_info() (the f-string sites without exc_info,
        e.g. cache_service.delete_cached; M4)."""
        try:
            raise ConnectionError("Error 111 connecting to %s:6379. %s" % (HOST, SENT))
        except ConnectionError as e:
            out = _ss()._before_send(_logevent(f"Cache delete error: {e}"), {})
        le = out["logentry"]
        assert _found(le, [HOST, SENT]) == [], f"[R2 sys.exc_info] raw text kept: {_san(le)}"
        assert (le["message"], le["formatted"]) == ("Cache delete error: <ConnectionError>",) * 2

    def test_u8d_red_r2_log_record_exc_info(self):
        """R2 source 2: hint['log_record'].exc_info, called OUTSIDE the except."""
        ei = _exc_info_of(RuntimeError("parse boom %s %s" % (SENT, EMAIL)))
        rec = logging.LogRecord("app.services.structured_comparison_service", logging.ERROR, __file__, 1,
                                "Comparison error: %s", None, ei)
        out = _ss()._before_send(_logevent(f"Comparison error: {ei[1]}"), {"log_record": rec})
        le = out["logentry"]
        assert _found(le, [SENT, EMAIL]) == [], f"[R2 log_record] raw text kept: {_san(le)}"
        assert le["formatted"] == "Comparison error: <RuntimeError>"

    def test_u8d_red_r2_hint_exc_info(self):
        """R2 source 3: hint['exc_info'], called OUTSIDE the except."""
        ei = _exc_info_of(RuntimeError("wrap " + SENT))
        out = _ss()._before_send(_logevent(f"Unhandled RuntimeError: {ei[1]}"), {"exc_info": ei})
        le = out["logentry"]
        assert _found(le, [SENT]) == [], f"[R2 hint exc_info] raw text kept: {_san(le)}"
        assert le["formatted"] == "Unhandled RuntimeError: <RuntimeError>"

    @pytest.mark.parametrize("form", ["str_param", "exception_object_param"])
    def test_u8d_red_r2_params(self, form):
        """R2: every string in logentry.params and every non-string param
        rendered with repr first (record.args is a tuple)."""
        try:
            raise RuntimeError("svc boom " + SENT)
        except RuntimeError as e:
            params = (str(e),) if form == "str_param" else (e,)
            out = _ss()._before_send(_logevent(f"Comparison error: {e}", params=params), {})
        got = out["logentry"]["params"]
        assert _found(got, [SENT]) == [], f"[R2 params {form}] raw text kept: {_san(repr(list(got)))}"
        assert list(got) == ["<RuntimeError>"], got

    def test_u8d_red_r2_chain_cause(self):
        """R2: a text built from a DIFFERENT exception in the chain (the share
        case: ShareTokenError embeds str(APIError), __cause__ = the APIError);
        longest form first."""
        from postgrest.exceptions import APIError

        class ShareTokenError(Exception):
            pass

        api = APIError({"message": "dup " + SENT, "code": "23505", "hint": None,
                        "details": "Key (share_token)=(" + SHTOK + ") already exists."})
        try:
            try:
                raise api
            except APIError as inner:
                raise ShareTokenError("share_token write failed: %s" % inner) from inner
        except ShareTokenError as exc:
            out = _ss()._before_send(_logevent(f"Share token creation failed: {exc}"), {})
        le = out["logentry"]
        assert _found(le, [SENT, SHTOK]) == [], f"[R2 chain] raw text kept: {_san(le)}"
        assert le["formatted"] == "Share token creation failed: <ShareTokenError>"

    def test_u8d_red_r2_safe_exc_form(self):
        """R2 handled forms include log_scrub.safe_exc(x) (the R-W18 drop lines)."""
        try:
            raise RuntimeError("fetch failed https://shop.invalid/" + QWORD + "?token=" + TOK)
        except RuntimeError as e:
            text = "[ADAPTER DROP] fanout:woo:shop.invalid: ERROR RuntimeError " + _ls().safe_exc(e)
            out = _ss()._before_send(_logevent(text), {})
        le = out["logentry"]
        assert _found(le, [QWORD, TOK]) == [], f"[R2 safe_exc form] text kept: {_san(le)}"
        assert le["formatted"] == "[ADAPTER DROP] fanout:woo:shop.invalid: ERROR RuntimeError <RuntimeError>"

    def test_u8d_red_r2_exc_summary_text_form(self):
        """R2 handled forms include the text part of log_scrub.exc_summary(x)."""
        try:
            raise RuntimeError("upstream said " + QWORD + " for " + EMAIL)
        except RuntimeError as e:
            out = _ss()._before_send(_logevent("Search error: " + _ls().exc_summary(e)), {})
        le = out["logentry"]
        assert _found(le, [QWORD, EMAIL]) == [], f"[R2 exc_summary form] text kept: {_san(le)}"
        assert "<RuntimeError>" in le["formatted"], _san(le["formatted"])

    def test_u8d_red_r2_ordering_hex_and_email(self):
        """Review correction 6 (M16): R2 runs BEFORE the pattern walk, so a text
        with a 32-hex run and an email becomes <RuntimeError>. Base:
        'Cache delete error: upstream rejected key [TOKEN_REDACTED] ... for <EMAIL>'.
        The text is longer than exc_summary's 200-character cut, so its text
        form cannot stand in for the full text after a pattern pass (M16)."""
        try:
            raise RuntimeError(ORDERING_TEXT)
        except RuntimeError as e:
            out = _ss()._before_send(_logevent(f"Cache delete error: {e}"), {})
        le = out["logentry"]
        assert _found(le, [EMAIL]) == [], f"[R2 ordering] email kept: {_san(le)}"
        assert le["formatted"] == "Cache delete error: <RuntimeError>"

    def test_u8d_red_r2_breadcrumb_message(self):
        """R2 crumb half (M5): before_breadcrumb replaces the handled text
        (it runs inside the except arm, sys.exc_info() is set)."""
        from postgrest.exceptions import APIError
        try:
            raise APIError({"message": "m " + SENT, "code": "23505", "hint": None,
                            "details": "Key (email)=(" + EMAIL + ") exists"})
        except APIError as e:
            rec = logging.LogRecord("app.api.auth_routes", logging.ERROR, __file__, 1, "x", None, None)
            crumb = {"type": "log", "category": "app.api.auth_routes", "level": "error",
                     "message": f"push token update failed for user-u8d: {e}"}
            out = _ss()._strip_tokens_from_breadcrumb(crumb, {"log_record": rec})
        assert _found(out, [SENT, EMAIL]) == [], f"[R2 crumb] raw text kept: {_san(out)}"
        assert out["message"] == "push token update failed for user-u8d: <APIError>"

    def test_u8d_red_r2_breadcrumb_ordering(self):
        """Review correction 6 for the crumb hook: replacement before _scrub_string."""
        try:
            raise RuntimeError(ORDERING_TEXT)
        except RuntimeError as e:
            crumb = {"type": "log", "category": "app.services.cache_service", "level": "error",
                     "message": f"Cache delete error: {e}"}
            out = _ss()._strip_tokens_from_breadcrumb(crumb, {})
        assert _found(out, [EMAIL]) == [], f"[R2 crumb ordering] email kept: {_san(out)}"
        assert out["message"] == "Cache delete error: <RuntimeError>"

    # ---------------------------------------------------- edge cases (spec 7)

    def test_u8d_pin_edge1_short_text_not_replaced(self):
        """Edge 1 (M6): a handled text shorter than 4 characters is never
        replaced, so a template letter is never rewritten."""
        try:
            raise RuntimeError("x")
        except RuntimeError as e:
            out = _ss()._before_send(_logevent(f"box x failed: {e}"), {})
        assert out["logentry"]["formatted"] == "box x failed: x"

    def test_u8d_red_edge1_four_chars_replaced(self):
        """Edge 1, the boundary: KeyError('id') -> "'id'" is 4 characters and IS
        replaced. Base: unchanged."""
        try:
            {}["id"]
        except KeyError as e:
            out = _ss()._before_send(_logevent(f"missing {e}"), {})
        assert out["logentry"]["formatted"] == "missing <KeyError>"

    def test_u8d_red_edge2_text_inside_template(self):
        """Edge 2: a text that also occurs in the template's constant part is
        replaced everywhere (pinned so a GREEN cannot anchor to the tail
        without a ruling). Base: unchanged."""
        try:
            raise RuntimeError("failed")
        except RuntimeError as e:
            out = _ss()._before_send(_logevent(f"op failed: {e}"), {})
        assert out["logentry"]["formatted"] == "op <RuntimeError>: <RuntimeError>"

    @pytest.mark.parametrize("hook", ["before_send", "before_breadcrumb"])
    def test_u8d_pin_edge3_broken_str_repr_never_raises(self, hook):
        """Edge 3 (M15): a handled exception whose __str__ and __repr__ raise is
        skipped; the hook never raises and the event / crumb still ships."""

        class Broken(Exception):
            def __str__(self):
                raise ValueError("no str")

            def __repr__(self):
                raise ValueError("no repr")

        try:
            raise Broken()
        except Broken:
            if hook == "before_send":
                out = _ss()._before_send(_logevent("constant broken line"), {})
                assert out is not None and out["logentry"]["formatted"] == "constant broken line"
            else:
                out = _ss()._strip_tokens_from_breadcrumb({"message": "constant broken line", "level": "error"}, {})
                assert out is not None and out["message"] == "constant broken line"

    def test_u8d_pin_edge4_cyclic_chain_bounded(self):
        """Edge 4: a cyclic __context__ chain is walked with a bound."""
        a, b = RuntimeError("alpha side"), RuntimeError("beta side")
        a.__context__, b.__context__ = b, a
        try:
            raise a
        except RuntimeError:
            sys.exc_info()[1].__context__ = b  # keep the cycle after the raise
            out = _ss()._before_send(_logevent("cycle constant line"), {})
        assert out is not None and out["logentry"]["formatted"] == "cycle constant line"

    @pytest.mark.parametrize(
        "line",
        ["Auth error in login: ConnectError", "Account deletion failed for user user-u8d: RuntimeError"],
        ids=["auth_type_only", "u8c_route_line"],
    )
    def test_u8d_pin_clean_templates_unchanged(self, line):
        """R2 never rewrites a clean type-only template (the exception text is
        not in it)."""
        try:
            raise RuntimeError("upstream connect failed")
        except RuntimeError:
            out = _ss()._before_send(_logevent(line), {})
        assert out["logentry"]["formatted"] == line


# ======================================================================= R3

class TestR3RequestBody:

    @pytest.mark.parametrize("hook", ["_before_send", "_before_send_transaction"])
    def test_u8d_red_r3_belt_request_data_filtered(self, hook):
        """R3 belt (M8): any request.data present becomes '[Filtered]' in BOTH
        hooks. Base: the dict is key-scrubbed only (query/email survive)."""
        ev = {"request": {"method": "POST", "data": {"query": QWORD, "email": EMAIL, "password": "x"}}}
        out = getattr(_ss(), hook)(ev, {})
        assert _found(out["request"], [QWORD, EMAIL]) == [], f"[R3 belt {hook}] body kept: {_san(out['request'])}"
        assert out["request"]["data"] == "[Filtered]"

    def test_u8d_pin_r3_hooks_share_request_region(self):
        """W1-1b: the two hooks scrub the request region identically."""
        def mk():
            return {"request": {"url": "http://testserver/api/v1/text/compare?q=" + QWORD + "&nocache=true",
                                "query_string": "q=" + QWORD + "&nocache=true",
                                "headers": {"authorization": "Bearer abc", "host": "testserver"},
                                "data": {"query": QWORD}}}
        ss = _ss()
        assert ss._before_send(mk(), {})["request"] == ss._before_send_transaction(mk(), {})["request"]


# ======================================================================= R4'

R4P_RED = [
    ("amp_hash", "q=" + QWORD + "&+" + QWORD2 + "+Gabbana+#" + QWORD3 + "&nocache=true",
     [QWORD, QWORD2, QWORD3], ["q=[QUERY_REDACTED]", "nocache=true"]),
    ("product_a_amp", "product_a=" + QWORD + "+&+" + QWORD2 + "&product_b=" + QWORD3 + "beta&region=bahrain",
     [QWORD, QWORD2, QWORD3], ["product_a=[QUERY_REDACTED]", "product_b=[QUERY_REDACTED]", "region=bahrain"]),
    ("unknown_key", "ref=" + SENT + "&limit=20", [SENT], ["limit=20"]),
    ("off_grammar_bookkeeping", "sort=" + SENT + "&offset=0", [SENT], ["offset=0"]),
    ("product_b", "product_b=" + QWORD, [QWORD], ["product_b=[QUERY_REDACTED]"]),
    ("url", "url=https://shop.invalid/p/" + QWORD, [QWORD], ["url=[QUERY_REDACTED]"]),
    ("url1", "url1=https://shop.invalid/p/" + QWORD + "?ref=" + SENT, [QWORD, SENT], ["url1=[QUERY_REDACTED]"]),
    ("url2", "url2=https://shop.invalid/q/" + QWORD, [QWORD], ["url2=[QUERY_REDACTED]"]),
    ("credential_in_unknown_key", "token=" + HEX32 + "&nocache=false", [HEX32], ["nocache=false"]),
]


class TestR4PrimeQueryStrings:

    @pytest.mark.parametrize("name,raw,needles,kept", R4P_RED, ids=[r[0] for r in R4P_RED])
    def test_u8d_red_r4p_query_string(self, name, raw, needles, kept):
        """R4' (review correction 1, SR7): on the DECODED query string, PII keys
        are redacted, decoded '&'/'#' remnants, unknown keys and off-grammar
        bookkeeping values are dropped, grammatical bookkeeping is kept."""
        out = _ss()._before_send({"request": {"query_string": raw}}, {})["request"]["query_string"]
        assert _found(out, needles) == [], f"[R4' {name}] user content kept: {_found(out, needles)}"
        assert all(k in out for k in kept), (name, kept)

    def test_u8d_red_r4p_url_form(self):
        """R4' on request.url's query part (``_scrub_query_string``)."""
        url = "http://testserver/api/v1/text/compare?q=" + QWORD + "&+" + QWORD2 + "+Gabbana+#" + QWORD3 + "&nocache=true"
        out = _ss()._before_send({"request": {"url": url}}, {})["request"]["url"]
        assert _found(out, [QWORD, QWORD2, QWORD3]) == [], f"[R4' url] user content kept: {_found(out, [QWORD, QWORD2, QWORD3])}"
        assert "nocache=true" in out

    def test_u8d_red_r4p_transaction_hook(self):
        """R4' applies to transactions through the shared request region."""
        raw = "product_a=" + QWORD + "+&+" + QWORD2 + "&region=bahrain"
        out = _ss()._before_send_transaction({"request": {"query_string": raw}}, {})["request"]["query_string"]
        assert _found(out, [QWORD, QWORD2]) == [], f"[R4' transaction] user content kept: {_san(out)}"
        assert "region=bahrain" in out

    @pytest.mark.parametrize(
        "field,raw,expected",
        [
            ("url", "https://example.com/api/v1/text/compare?nocache=true",
             "https://example.com/api/v1/text/compare?nocache=true"),
            ("url", "https://example.com/api/v1/comparisons?limit=20&offset=0&sort=desc",
             "https://example.com/api/v1/comparisons?limit=20&offset=0&sort=desc"),
            ("url", "https://example.com/search?q=" + SENT + "&limit=10",
             "https://example.com/search?q=[QUERY_REDACTED]&limit=10"),
            ("query_string", "q=" + SENT + "&limit=20", "q=[QUERY_REDACTED]&limit=20"),
            ("query_string", "nocache=true&region=bahrain", "nocache=true&region=bahrain"),
        ],
        ids=["nocache", "pagination", "multi_param", "raw_qs", "region"],
    )
    def test_u8d_pin_r4p_r21_contract(self, field, raw, expected):
        """The pinned Bundle D R21 contract: bookkeeping readable, PII
        [QUERY_REDACTED], byte-exact."""
        assert _ss()._before_send({"request": {field: raw}}, {})["request"][field] == expected

    def test_u8d_pin_edge10_bytes_query_string(self):
        """Edge 10: a bytes query_string is decoded and kept for bookkeeping."""
        out = _ss()._before_send({"request": {"query_string": b"nocache=true&limit=20"}}, {})
        assert out["request"]["query_string"] == "nocache=true&limit=20"


# ======================================================================= R5

class TestR5Outbound:

    def test_u8d_red_r5_span_user_path(self):
        """R5 + review 4 (M20, M10): a non-infra http.client span keeps scheme +
        host only; its http.query values are filtered."""
        span = {"op": "http.client",
                "description": "GET https://shop.invalid/products/" + QWORD + "-perfume?ref=" + SENT,
                "data": {"url": "https://shop.invalid/products/" + QWORD + "-perfume", "http.query": "ref=" + SENT,
                         "http.method": "GET"}}
        out = _ss()._before_send_transaction({"spans": [span]}, {})["spans"][0]
        assert _found(out, [QWORD, SENT]) == [], f"[R5 span path] user URL kept: {_found(out, [QWORD, SENT])}"
        assert "shop.invalid" in out["description"], _san(out["description"])

    def test_u8d_red_r5_span_query_values(self):
        """R5 (M10): outbound http.query values are filtered on spans (a
        PostgREST filter, a provider token in the query)."""
        spans = [
            {"op": "http.client", "description": "GET https://api.scrape.example/",
             "data": {"url": "https://api.scrape.example/", "http.method": "GET",
                      "http.query": "token=" + TOK + "&url=https%3A%2F%2Fshop.example%2Fp%3Fx%3D" + SENT}},
            {"op": "http.client", "description": "GET https://" + HOST + "/rest/v1/users",
             "data": {"url": "https://" + HOST + "/rest/v1/users", "http.method": "GET",
                      "http.query": "select=id&email=eq." + EMAIL_PCT}},
        ]
        out = _ss()._before_send_transaction({"spans": spans}, {})["spans"]
        assert _found(out, [TOK, SENT, EMAIL_PCT]) == [], f"[R5 span query] values kept: {_found(out, [TOK, SENT, EMAIL_PCT])}"

    @pytest.mark.parametrize("hook", ["before_breadcrumb", "before_send_walk"])
    @pytest.mark.parametrize("shape", ["query_values", "user_path"])
    def test_u8d_red_r5_crumb(self, hook, shape):
        """R5 for http breadcrumbs (M11, M20): http.query values filtered and a
        non-infra url keeps scheme + host, in before_breadcrumb AND in
        _before_send's breadcrumb walk."""
        if shape == "query_values":
            data = {"url": "https://api.scrape.example/", "http.method": "GET", "http.query": "token=" + TOK}
            needles = [TOK]
        else:
            data = {"url": "https://shop.invalid/products/" + QWORD + "-perfume", "http.method": "GET",
                    "http.query": ""}
            needles = [QWORD]
        crumb = {"type": "http", "category": "httplib", "data": data}
        ss = _ss()
        if hook == "before_breadcrumb":
            out = ss._strip_tokens_from_breadcrumb(crumb, {})
        else:
            out = ss._before_send({"breadcrumbs": {"values": [crumb]}}, {})["breadcrumbs"]["values"][0]
        assert _found(out, needles) == [], f"[R5 crumb {shape} {hook}] kept: {_san(out)}"

    def test_u8d_pin_r5_openai_token_counts_survive(self):
        """Review correction 5 (M17): R5 touches only http spans' http.query,
        url and description; an OpenAI span's integer token counts survive."""
        data = {"gen_ai.usage.input_tokens": 12, "gen_ai.usage.output_tokens": 34,
                "gen_ai.usage.total_tokens": 46, "gen_ai.request.max_tokens": 600,
                "gen_ai.request.model": "gpt-4o-mini"}
        span = {"op": "gen_ai.chat", "description": "chat gpt-4o-mini", "data": dict(data)}
        out = _ss()._before_send_transaction({"spans": [span]}, {})["spans"][0]
        assert out["data"] == data


# ======================================================================= R6

class TestR6PathTokens:

    @pytest.mark.parametrize(
        "hook,where,value,expected_tail",
        [
            ("_before_send", "url", "http://testserver/api/v1/share/" + SHTOK, "/api/v1/share/[token]"),
            ("_before_send", "url", "http://testserver/api/v1/referrals/invite/" + SHTOK + "/quiz",
             "/api/v1/referrals/invite/[token]/quiz"),
            ("_before_send_transaction", "url", "http://testserver/api/v1/share/" + SHTOK, "/api/v1/share/[token]"),
            ("_before_send_transaction", "url", "http://testserver/api/v1/referrals/invite/" + SHTOK,
             "/api/v1/referrals/invite/[token]"),
            ("_before_send", "extra_path", "/api/v1/share/" + SHTOK, "/api/v1/share/[token]"),
        ],
        ids=["event_share", "event_invite_quiz", "txn_share", "txn_invite", "event_extra_path"],
    )
    def test_u8d_red_r6_capability_token(self, hook, where, value, expected_tail):
        """R6 (M12): the segment after /api/v1/share/ and /api/v1/referrals/invite/
        becomes [token] (request.url, both hooks; extra.path on events)."""
        ev = {"extra": {"path": value}} if where == "extra_path" else {"request": {"url": value}}
        out = getattr(_ss(), hook)(ev, {})
        got = out["extra"]["path"] if where == "extra_path" else out["request"]["url"]
        assert SHTOK not in got, f"[R6 {hook} {where}] token kept"
        assert got.endswith(expected_tail), _san(got)


# ====================================================================== R10

R10_HEADERS = {
    "x-device-fingerprint": FP,
    "cf-connecting-ip": IP,
    "true-client-ip": IP,
    "x-envoy-external-address": IP,
    "forwarded": "for=" + IP,
    "x-custom-note": NOTE,
}


class TestR10Headers:

    @pytest.mark.parametrize("hook", ["_before_send", "_before_send_transaction"])
    @pytest.mark.parametrize("header", sorted(R10_HEADERS))
    def test_u8d_red_r10_header_filtered(self, header, hook):
        """R10 (M19): a header outside the allowlist ships '[Filtered]'."""
        ev = {"request": {"headers": {"host": "testserver", header: R10_HEADERS[header]}}}
        got = getattr(_ss(), hook)(ev, {})["request"]["headers"][header]
        assert R10_HEADERS[header] not in got, f"[R10 {header} {hook}] value kept"
        assert got == "[Filtered]", _san(got)

    @pytest.mark.parametrize("hook", ["_before_send", "_before_send_transaction"])
    def test_u8d_pin_r10_allowlist_and_redacted_names(self, hook):
        """The allowlisted headers stay readable; the existing [REDACTED] names
        stay [REDACTED]."""
        keep = {"host": "testserver", "user-agent": "MYEZ-u8d/1.0", "accept": "*/*",
                "accept-encoding": "gzip", "accept-language": "ar", "content-type": "application/json",
                "content-length": "12", "connection": "keep-alive", "x-request-id": "rid-u8d"}
        redacted = {"authorization": "Bearer abc", "x-admin-key": "k-u8d", "cookie": "c=1",
                    "x-qaren-synthetic": "s-u8d"}
        out = getattr(_ss(), hook)({"request": {"headers": {**keep, **redacted}}}, {})["request"]["headers"]
        assert {k: out[k] for k in keep} == keep
        assert {k: out[k] for k in redacted} == {k: "[REDACTED]" for k in redacted}


# ================================================================= options

def _recorded_init_kwargs(monkeypatch) -> dict:
    """Run the REAL init_sentry() against a recording sentry_sdk.init (no SDK
    client is installed in this process)."""
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    calls = []
    monkeypatch.setattr(sentry_sdk, "init", lambda *a, **kw: calls.append(kw))
    monkeypatch.setattr(LoggingIntegration, "capture_sentry_logs", LoggingIntegration.capture_sentry_logs)
    monkeypatch.setenv("SENTRY_DSN", "https://public" + "@" + "o0.ingest.example.invalid/1")
    _ss().init_sentry()
    assert len(calls) == 1, calls
    return calls[0]


def _integration(kw: dict, name: str):
    found = [i for i in (kw.get("integrations") or []) if type(i).__name__ == name]
    return found[0] if found else None


class TestOptions:

    @pytest.mark.parametrize(
        "option", ["max_request_body_size", "logging_integration_levels", "openai_include_prompts",
                   "trace_propagation_targets"])
    def test_u8d_red_options_init_kwargs(self, monkeypatch, option):
        """R3 option (M7), R7 = ERROR (M13), SR8 include_prompts (M-SR8), R12
        (M-SR4): the kwargs init_sentry passes. Base: absent."""
        kw = _recorded_init_kwargs(monkeypatch)
        if option == "max_request_body_size":
            assert kw.get("max_request_body_size") == "never", kw.get("max_request_body_size")
        elif option == "logging_integration_levels":
            li = _integration(kw, "LoggingIntegration")
            assert li is not None, "no explicit LoggingIntegration in init_sentry's integrations"
            assert (li._breadcrumb_handler.level, li._handler.level) == (logging.ERROR, logging.ERROR)
        elif option == "openai_include_prompts":
            oi = _integration(kw, "OpenAIIntegration")
            assert oi is not None, "no explicit OpenAIIntegration in init_sentry's integrations"
            assert oi.include_prompts is False
        else:
            assert "trace_propagation_targets" in kw and list(kw["trace_propagation_targets"]) == [], (
                kw.get("trace_propagation_targets", "<absent>"))

    def test_u8d_pin_options_init_kwargs_kept(self, monkeypatch):
        """R9: the existing options stay (no PII default, no frame locals, the
        sample rate, the three hooks, 503 excluded from failed requests)."""
        kw = _recorded_init_kwargs(monkeypatch)
        ss = _ss()
        assert (kw["send_default_pii"], kw["include_local_variables"], kw["traces_sample_rate"]) == (False, False, 0.1)
        assert (kw["before_send"].__name__, kw["before_send_transaction"].__name__, kw["before_breadcrumb"].__name__) == (
            ss._before_send.__name__, ss._before_send_transaction.__name__, ss._strip_tokens_from_breadcrumb.__name__)
        for name in ("FastApiIntegration", "StarletteIntegration"):
            integ = _integration(kw, name)
            assert integ is not None, name
            codes = set(integ.failed_request_status_codes)
            assert 503 not in codes and {500, 502, 504} <= codes, (name, sorted(codes)[:5])


# ===================================================================== R11

class _RecordingPattern:
    """Proxy for a compiled regex that records the length of every input."""

    def __init__(self, real, lens):
        self._real, self._lens = real, lens

    def sub(self, repl, string, *a, **k):
        self._lens.append(len(string))
        return self._real.sub(repl, string, *a, **k)

    def __getattr__(self, name):
        return getattr(self._real, name)


def _record_scrubs(monkeypatch) -> list:
    lens = []
    ss, ls = _ss(), _ls()
    real_ss, real_ls = ss._scrub_string, ls._scrub_string

    def rec_ss(value):
        lens.append(len(value))
        return real_ss(value)

    def rec_ls(value):
        lens.append(len(value))
        return real_ls(value)

    monkeypatch.setattr(ss, "_scrub_string", rec_ss)
    monkeypatch.setattr(ls, "_scrub_string", rec_ls)
    monkeypatch.setattr(ls, "_SAFE_EXC_URL_RE", _RecordingPattern(ls._SAFE_EXC_URL_RE, lens))
    return lens


BIG_TEXT_LEN = 400000


class TestR11Cap:

    def test_u8d_red_sr3_exc_summary_scrub_input_capped(self, monkeypatch):
        """SR3 (M-SR3): exc_summary cuts its input to the first 16,384
        characters BEFORE both scrubs (structural; no wall clock). Base: both
        scrubs receive all 400,000+ characters."""
        lens = _record_scrubs(monkeypatch)
        _ls().exc_summary(RuntimeError(SENT + " " + "a" * BIG_TEXT_LEN))
        assert lens, "exc_summary called no pattern scrub"
        assert max(lens) <= CAP, f"[SR3 exc_summary] a pattern scrub received {max(lens)} characters (cap {CAP})"

    def test_u8d_red_sr3_r2_helper_scrub_input_capped(self, monkeypatch):
        """SR3 for the R2 helper path: with a 400,000-character handled text no
        pattern scrub (sentry_service._scrub_string, log_scrub._scrub_string,
        the R-W18 URL regex) receives more than 16,384 characters; the long
        text is still replaced (plain str.replace). Base: _scrub_dict passes
        the whole logentry text to _scrub_string."""
        lens = _record_scrubs(monkeypatch)
        try:
            raise RuntimeError(SENT + " " + "a" * BIG_TEXT_LEN)
        except RuntimeError as e:
            out = _ss()._before_send(_logevent(f"big op failed: {e}"), {})
        assert lens == [] or max(lens) <= CAP, f"[SR3 R2 helper] a pattern scrub received {max(lens)} characters (cap {CAP})"
        assert out["logentry"]["formatted"] == "big op failed: <RuntimeError>"


def _exc_summary_reference(exc: BaseException) -> str:
    """The base (845ece15) exc_summary algorithm, rebuilt from log_scrub's own
    helpers, uncapped: for a text of at most 16,384 characters the SR3 cap is
    a no-op, so the real function must equal this."""
    ls = _ls()
    name = ls._SAFE_EXC_LINEBREAK_RE.sub(" ", type(exc).__name__)
    text = str(exc)
    text = ls._SAFE_EXC_URL_RE.sub(ls._safe_exc_url, text)
    text = ls._scrub_string(text)
    text = ls._SAFE_EXC_LINEBREAK_RE.sub(" ", text).lstrip()
    text = text[:ls._SAFE_EXC_MAX_CHARS]
    if not text.strip():
        return name
    return f"{name}: {text}"


def _corpus() -> list:
    pad = "b" * (CAP - 64)
    return [
        ("empty", ""),
        ("blank", "   \n "),
        ("plain", "plain failure text"),
        ("url_userinfo", "fetch https://u:" + "pw" + "@" + HOST + "/p?token=" + TOK + "#frag tail"),
        ("linebreaks", "multi\nline\rtext" + chr(0x2028) + "end"),
        ("hex_and_email", "key " + HEX32 + " for " + EMAIL),
        ("bearer", "Bearer " + "z" * 40 + " rejected"),
        ("jwt_shaped", "tok " + "eyJ" + "a" * 24 + ".eyJ" + "b" * 24 + "." + "c" * 12),
        ("at_cap_tail_url", pad + " https://" + HOST + "/x?k=" + TOK),
        ("exactly_cap", ("ab" * (CAP // 2))),
        ("leading_ws_long", " " * 300 + "after spaces " + SENT),
    ]


class TestR11Pins:

    @pytest.mark.parametrize("name,text", _corpus(), ids=[c[0] for c in _corpus()])
    def test_u8d_pin_sr3_exc_summary_unchanged_up_to_cap(self, name, text):
        """SR3: for a text of at most 16,384 characters exc_summary's output is
        byte-identical to the base algorithm."""
        assert len(text) <= CAP, (name, len(text))
        exc = RuntimeError(text)
        assert _ls().exc_summary(exc) == _exc_summary_reference(exc)


# ====================================================================== R8 (AST)

_LOG_RECEIVERS = {"logger", "log", "_logger", "LOGGER", "_log", "logging"}
_ERROR_LEVELS = {"error", "exception", "critical"}
_ID_NAMES = {"user_id", "comparison_id", "key", "label"}
# Review correction 2 allowlist, by site: (file, extra names allowed there).
_SITE_NAMES = {
    "app/services/auth_service.py": {"context"},
    "app/services/llm_provider.py": {"_ENV"},
}
_SITE_CALLS = {"app/services/llm_provider.py": {"_redacted"}}


def _parents(tree):
    par = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            par[ch] = node
    return par


def _inside_except(node, par) -> bool:
    cur = node
    while cur in par:
        cur = par[cur]
        if isinstance(cur, ast.ExceptHandler):
            return True
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return False
    return False


def _is_error_log_call(node) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in _ERROR_LEVELS
            and isinstance(node.func.value, ast.Name) and node.func.value.id in _LOG_RECEIVERS)


def _arg_ok(node, rel) -> bool:
    """Constant, type(x).__name__, an allowlisted identifier, or a
    concatenation / f-string of those."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.JoinedStr):
        return all(_arg_ok(v.value if isinstance(v, ast.FormattedValue) else v, rel) for v in node.values)
    if isinstance(node, ast.BinOp):
        return _arg_ok(node.left, rel) and _arg_ok(node.right, rel)
    if isinstance(node, ast.Name):
        return node.id in _ID_NAMES or node.id in _SITE_NAMES.get(rel, set())
    if isinstance(node, ast.Attribute) and node.attr == "__name__":
        v = node.value
        return isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "type"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id in _SITE_CALLS.get(rel, set())
    return False


def _outside_except_error_calls() -> list:
    """(file, line, ok, template) for every ERROR-level log call outside an
    except arm in app/."""
    rows = []
    for p in sorted(APP_DIR.rglob("*.py")):
        rel = p.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(p.read_text(encoding="utf-8"))
        par = _parents(tree)
        for node in ast.walk(tree):
            if not _is_error_log_call(node) or _inside_except(node, par):
                continue
            ok = all(_arg_ok(a, rel) for a in node.args)
            rows.append((rel, node.lineno, ok, ast.unparse(node.args[0])[:80] if node.args else ""))
    return rows


def _outside_except_offenders() -> list:
    return [(rel, line, tpl) for rel, line, ok, tpl in _outside_except_error_calls() if not ok]


def _bare_name_refs(node, names) -> list:
    """Names in ``names`` referenced NOT under a Call (len(query), a hash of
    query, urlparse(url).hostname are fine; query, f'{query}' are not)."""
    out = []

    def walk(n, under_call):
        if isinstance(n, ast.Name) and n.id in names and not under_call:
            out.append(n.id)
        for ch in ast.iter_child_nodes(n):
            walk(ch, under_call or isinstance(n, ast.Call))
    walk(node, False)
    return out


def _template_text(call) -> str:
    if not call.args:
        return ""
    a0 = call.args[0]
    if isinstance(a0, ast.JoinedStr):
        return "".join(v.value for v in a0.values if isinstance(v, ast.Constant))
    if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
        return a0.value
    return ast.unparse(a0)


R8_IN_EXCEPT = [
    ("scs_l2_7_partial_build", "app/services/structured_comparison_service.py", "[L2.7] partial build failed", {"query"}),
    ("scs_stream_tail_deadline", "app/services/structured_comparison_service.py",
     "[stream] tail-deadline partial build failed", {"query"}),
    ("scs_stream_hard_cap", "app/services/structured_comparison_service.py",
     "[stream] partial build failed after hard-cap", {"query"}),
    ("url_extraction_fetch_failed", "app/services/url_extraction_service.py", "Failed to fetch", {"url", "current"}),
]


class TestR8SourceLines:

    @pytest.mark.parametrize("name,rel,prefix,names", R8_IN_EXCEPT, ids=[r[0] for r in R8_IN_EXCEPT])
    def test_u8d_red_r8_in_except_lines_no_user_content(self, name, rel, prefix, names):
        """R8 (M14): the four in-except ERROR lines log query_hash/length (or
        the URL host) instead of the user's query / URL. The statement is found
        by its template prefix (resolve by statement, not by line number)."""
        tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
        calls = [n for n in ast.walk(tree) if _is_error_log_call(n) and _template_text(n).startswith(prefix)]
        assert len(calls) == 1, f"[R8 {name}] expected one ERROR call with template prefix {prefix!r}, found {len(calls)}"
        refs = [r for a in calls[0].args for r in _bare_name_refs(a, names)]
        assert refs == [], f"[R8 {name}] {rel}:{calls[0].lineno} interpolates user content {refs}"

    @pytest.mark.parametrize(
        "module",
        ["app/services/structured_comparison_service.py", "app/api/image_routes.py"],
        ids=["structured_comparison_service", "image_routes"],
    )
    def test_u8d_red_r8_outside_except_error_lines_type_only(self, module):
        """Review correction 2 (M21): an ERROR-level call outside an except arm
        has only constant, type(x).__name__ or allowlisted-identifier
        arguments. Base: SCS 'Error fetching {key}: {phase1_results[i]}' and
        its phase-2 twin, image_routes 'Vision parse error: {...}'."""
        rows = [r for r in _outside_except_offenders() if r[0] == module]
        assert rows == [], f"[R8 outside-except] {rows}"

    def test_u8d_pin_r8_no_other_outside_except_error_line(self):
        """Every other module is already clean (positive control: the scan sees
        the allowlisted llm_provider and auth_service sites)."""
        calls = _outside_except_error_calls()
        seen_allowlisted = sorted({rel for rel, _, ok, _ in calls if ok and rel in _SITE_NAMES})
        assert seen_allowlisted == ["app/services/auth_service.py", "app/services/llm_provider.py"], seen_allowlisted
        rows = [r for r in _outside_except_offenders()
                if r[0] not in ("app/services/structured_comparison_service.py", "app/api/image_routes.py")]
        assert rows == [], rows

    def test_u8d_red_r8_fetch_page_logs_host_only(self, caplog):
        """R8 at url_extraction_service.fetch_page: the ERROR line names the
        URL's host, never its path or query (Railway text + Sentry)."""
        from app.services import url_extraction_service as ues

        class _Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, *a, **k):
                raise RuntimeError("constant fetch failure")

        url = "https://shop.invalid/products/" + QWORD + "-perfume?ref=" + SENT

        async def go():
            with patch("app.utils.url_validator._validate_url_offloop_or_sync", AsyncMock(return_value=True)), \
                 patch.object(ues.httpx, "AsyncClient", _Client):
                return await ues.fetch_page(url)

        with caplog.at_level(logging.ERROR, logger="app.services.url_extraction_service"):
            assert asyncio.run(go()) is None
        msgs = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
        assert msgs, "fetch_page logged no ERROR line"
        assert _found(msgs, [QWORD, SENT]) == [], f"[R8 fetch_page] user URL path/query logged: {_found(msgs, [QWORD, SENT])}"
        assert any("shop.invalid" in m for m in msgs), _san(msgs)


# ====================================================== review 8 (AST) + harness

def _is_http_exception_call(node) -> bool:
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    return (isinstance(f, ast.Name) and f.id == "HTTPException") or (
        isinstance(f, ast.Attribute) and f.attr == "HTTPException")


def _const_like(node) -> bool:
    return isinstance(node, ast.Constant) or (isinstance(node, ast.Name) and node.id.lstrip("_").isupper())


def _result_dict_access(node) -> bool:
    """result['error'] or result.get('error', <constant>)."""
    if isinstance(node, ast.Subscript):
        return isinstance(node.value, ast.Name) and isinstance(node.slice, ast.Constant)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
        return isinstance(node.func.value, ast.Name) and all(_const_like(a) for a in node.args)
    return False


def _detail_ok(node, func) -> bool:
    if _const_like(node) or _result_dict_access(node):
        return True
    if isinstance(node, ast.Dict):
        return all(_detail_ok(v, func) for v in node.values)
    if isinstance(node, ast.Name) and func is not None:
        # A local bound ONLY from a result-dict access or a constant
        # (text_routes._surface_comparison_failure: code / error_msg).
        binds = [a.value for a in ast.walk(func) if isinstance(a, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == node.id for t in a.targets)]
        return bool(binds) and all(_const_like(b) or _result_dict_access(b) for b in binds)
    return False


def _enclosing_function(node, par):
    cur = node
    while cur in par:
        cur = par[cur]
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
    return None


def test_u8d_pin_http_exception_5xx_details_are_literal():
    """Review correction 8: every HTTPException with a 5xx or a computed
    status has a literal, a constant name, a dict of literals or a result-dict
    detail -- never an f-string, str(...) or an exception name -- so R1's
    HTTPException exemption can never ship exception text."""
    rows, checked = [], 0
    for p in sorted(APP_DIR.rglob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        par = _parents(tree)
        for node in ast.walk(tree):
            if not _is_http_exception_call(node):
                continue
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            status = kw.get("status_code", node.args[0] if node.args else None)
            detail = kw.get("detail", node.args[1] if len(node.args) > 1 else None)
            if isinstance(status, ast.Constant) and isinstance(status.value, int) and status.value < 500:
                continue
            checked += 1
            if detail is not None and not _detail_ok(detail, _enclosing_function(node, par)):
                rows.append((p.relative_to(REPO_ROOT).as_posix(), node.lineno, ast.unparse(detail)[:80]))
    assert checked >= 6, f"the scan saw only {checked} 5xx / computed-status HTTPException sites"
    assert rows == [], rows


def test_u8d_pin_sentinels_survive_scrub_string():
    """Positive control (U8c PIN7 idiom): the plain sentinels are not
    pattern-shaped, so a clean result is never a scrubbed-away false negative."""
    ss = _ss()
    assert [s for s in PLAIN if ss._scrub_string(s) != s] == []


def test_u8d_pin_hooks_resolved_at_call_time():
    """Spec edge case 12: this file never binds a sentry_service / log_scrub
    name at import (two other test files reload sentry_service)."""
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    bound = [ast.unparse(n) for n in tree.body
             if isinstance(n, (ast.Import, ast.ImportFrom))
             and ("sentry_service" in ast.unparse(n) or "log_scrub" in ast.unparse(n))]
    assert bound == [], bound


def test_u8d_red_r8_fetch_page_http_status_error_logs_no_url(caplog):
    """UG2 (R8 at url_extraction_service.fetch_page): raise_for_status() raises
    an httpx.HTTPStatusError whose str() carries the FULL request URL (path and
    query), so the failure line names the URL host and the exception TYPE
    only. A stub 404 response on a URL with a path sentinel and a query
    sentinel goes through the REAL fetch_page failure log line: neither
    sentinel is in the log record (message, args, exc_info). Base: 'Failed to
    fetch URL <url>: <str(e)>' carries both."""
    import httpx
    from app.services import url_extraction_service as ues

    url = "https://shop.invalid/products/" + QWORD + "-perfume?ref=" + SENT

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, target, *a, **k):
            return httpx.Response(404, request=httpx.Request("GET", target), text="gone")

    async def go():
        with patch("app.utils.url_validator._validate_url_offloop_or_sync", AsyncMock(return_value=True)), \
             patch.object(ues.httpx, "AsyncClient", _Client):
            return await ues.fetch_page(url)

    with caplog.at_level(logging.ERROR, logger="app.services.url_extraction_service"):
        assert asyncio.run(go()) is None
    recs = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert recs, "fetch_page logged no ERROR line"
    blobs = [r.getMessage() + " " + repr(r.args) + " " + repr(r.exc_info) for r in recs]
    assert _found(blobs, [QWORD, SENT]) == [], (
        f"[R8 fetch_page HTTPStatusError] user URL path/query logged: {_found(blobs, [QWORD, SENT])}")
    msgs = [r.getMessage() for r in recs]
    assert any("shop.invalid" in m and "HTTPStatusError" in m for m in msgs), _san(msgs)


# ============================================================== FIX round
# Appended by the U8d FIX round (adversary findings B1-B4, B6-B8, A2, A3, A5,
# A9). Existing nodes above are unchanged. Every sentinel is built at run time.

class TestFixR2FormsChainFailSafe:

    def test_u8d_fix_r2_safe_exc_form_is_the_only_match(self):
        """B1 (mutant B05, the safe_exc form removed): a 32-hex run OUTSIDE the
        URL makes exc_summary's text differ from the logged safe_exc text and
        the query strip makes str/repr differ, so ONLY the safe_exc form can
        match the line."""
        try:
            raise RuntimeError("fetch failed key " + HEX32 + " at https://shop.invalid/" + QWORD + "?token=" + TOK)
        except RuntimeError as e:
            line = "[ADAPTER DROP] fanout:woo:shop.invalid: ERROR RuntimeError " + _ls().safe_exc(e)
            matching = [f for f in _ss()._handled_text_forms(e) if f in line]
            assert matching == [_ls().safe_exc(e)], "precondition: safe_exc is the only matching form"
            out = _ss()._before_send(_logevent(line), {})
        le = out["logentry"]
        assert _found(le, [QWORD, TOK, HEX32]) == [], f"[R2 safe_exc only] text kept: {_san(le)}"
        assert le["formatted"] == "[ADAPTER DROP] fanout:woo:shop.invalid: ERROR RuntimeError <RuntimeError>"

    def test_u8d_fix_r2_exc_summary_form_is_the_only_match(self):
        """B1 (mutant B06, the exc_summary form removed): exc_summary rewrites a
        32-hex run, so str/repr/safe_exc differ from the logged text and ONLY
        the exc_summary text form can match (the 8 ERROR sites that log
        exc_summary(e) as a %-param)."""
        try:
            raise RuntimeError("upstream said " + QWORD + " for " + EMAIL + " key " + HEX32)
        except RuntimeError as e:
            part = _ls().exc_summary(e).partition(": ")[2]
            line = "Search error: " + _ls().exc_summary(e)
            matching = [f for f in _ss()._handled_text_forms(e) if f in line]
            assert matching == [part], "precondition: the exc_summary text is the only matching form"
            out = _ss()._before_send(_logevent(line), {})
        le = out["logentry"]
        assert _found(le, [QWORD, EMAIL]) == [], f"[R2 exc_summary only] text kept: {_san(le)}"
        assert le["formatted"] == "Search error: RuntimeError: <RuntimeError>"

    def test_u8d_fix_r2_nested_except_outer_text_redacted(self):
        """B2 (mutants B02 chain cut to one link, B03 __cause__ only): a line
        that names the OUTER exception inside a nested except arm --
        sys.exc_info() is the inner one, whose __context__ is the outer --
        ships '<RuntimeError>' on the event and on the breadcrumb."""
        try:
            raise RuntimeError("outer failure " + SENT + " " + EMAIL)
        except RuntimeError as outer:
            try:
                raise KeyError("inner")
            except KeyError:
                line = f"rollback failed after {outer}"
                out = _ss()._before_send(_logevent(line), {})
                crumb = _ss()._strip_tokens_from_breadcrumb({"level": "error", "message": line}, {})
        assert _found(out["logentry"], [SENT, EMAIL]) == [], _san(out["logentry"])
        assert out["logentry"]["formatted"] == "rollback failed after <RuntimeError>"
        assert crumb["message"] == "rollback failed after <RuntimeError>", _san(crumb)

    def test_u8d_fix_failsafe_event_and_breadcrumb(self, monkeypatch):
        """B3 (mutants B23 / B24, the _fail_safe net removed): a U8d rule that
        raises never drops the event or the breadcrumb, and the pre-U8d scrub
        (the hex pattern, the query-string redaction) still runs."""
        ss = _ss()

        def boom(*a, **k):
            raise RuntimeError("rule failure")

        monkeypatch.setattr(ss, "_exception_chain", boom)
        try:
            raise ValueError("text " + HEX32)
        except ValueError:
            out = ss._before_send(_logevent("x " + HEX32), {})
            crumb = ss._strip_tokens_from_breadcrumb(
                {"level": "error", "message": "y", "data": {"url": "https://a.invalid/p?q=" + QWORD}}, {})
        assert out is not None and HEX32 not in _dump(out), _san(out)
        assert crumb is not None, "breadcrumb dropped"
        assert QWORD not in _dump(crumb), _san(crumb)

    def test_u8d_fix_failsafe_transaction(self, monkeypatch):
        """B3 (mutant B25): a raising R5 rule never drops the transaction; the
        request-region scrub still runs."""
        ss = _ss()

        def boom(*a, **k):
            raise RuntimeError("rule failure")

        monkeypatch.setattr(ss, "_outbound_description", boom)
        tx = {"type": "transaction",
              "spans": [{"op": "http.client", "description": "GET https://a.invalid/p", "data": {}}],
              "request": {"headers": {"authorization": "x"}, "query_string": "q=" + QWORD}}
        out = ss._before_send_transaction(tx, {})
        assert out is not None, "transaction dropped"
        assert out["request"]["headers"]["authorization"] == "[REDACTED]"
        assert QWORD not in _dump(out["request"]), _san(out["request"])


class TestFixRequestAndOutbound:

    @pytest.mark.parametrize("raw,kept", [
        ("limit=20" + QWORD + "&nocache=true", "nocache=true"),
        ("region=bahrain " + QWORD + "&offset=0", "offset=0"),
        ("nocache=true" + QWORD + "&sort=asc", "sort=asc"),
    ], ids=["limit_prefix", "region_prefix", "nocache_prefix"])
    def test_u8d_fix_r4p_grammar_is_anchored(self, raw, kept):
        """B6 (mutant B15, fullmatch -> match): a grammatical prefix followed by
        user text is dropped, not kept."""
        out = _ss()._before_send({"request": {"query_string": raw}}, {})["request"]["query_string"]
        assert QWORD not in out, _san(out)
        assert out == kept

    @pytest.mark.parametrize("typ", ["Exception", "ComparisonException", "HTTPExceptionWrapper",
                                     "StarletteHTTPException"])
    def test_u8d_fix_r1_only_the_exact_http_exception_type_is_exempt(self, typ):
        """B7 (mutant B37, a broadened exemption): only the exact type name
        'HTTPException' keeps its value."""
        ev = {"exception": {"values": [{"type": typ, "value": "text " + SENT},
                                       {"type": "HTTPException", "value": "Detail"}]}}
        vals = _ss()._before_send(ev, {})["exception"]["values"]
        assert (vals[0]["value"], vals[1]["value"]) == ("", "Detail"), _san(vals)

    @pytest.mark.parametrize("hook", ["_before_send", "_before_send_transaction"])
    def test_u8d_fix_r3_string_body_filtered(self, hook):
        """B8 (mutant B13, the belt for dict bodies only): a STRING body never
        leaves either hook."""
        ev = {"request": {"method": "POST", "data": "query=" + QWORD + "&email=" + EMAIL}}
        out = getattr(_ss(), hook)(ev, {})
        assert _found(out["request"], [QWORD, EMAIL]) == [], _san(out["request"])
        assert out["request"]["data"] == "[Filtered]"

    def test_u8d_fix_r5_keyless_outbound_query_part_filtered(self):
        """B8 (mutant B17): a key-less part of an outbound http.query is
        '[Filtered]' too."""
        tx = {"spans": [{"op": "http.client", "description": "GET https://a.invalid/p",
                         "data": {"url": "https://a.invalid/p", "http.query": TOK + "&k=v"}}]}
        out = _ss()._before_send_transaction(tx, {})["spans"][0]["data"]
        assert TOK not in _dump(out), _san(out)
        assert out["http.query"] == "[Filtered]&k=[Filtered]", _san(out)

    @pytest.mark.parametrize("hook", ["before_breadcrumb", "before_send_walk", "transaction_span"])
    def test_u8d_fix_r5_http_fragment_filtered(self, hook):
        """A2 (mutant MA1, the http.fragment rule removed): a Link-mode URL
        fragment never leaves on an http breadcrumb or an http span."""
        data = {"url": "https://shop.invalid/p", "http.method": "GET", "http.fragment": QWORD + "-" + SENT}
        ss = _ss()
        if hook == "transaction_span":
            span = {"op": "http.client", "description": "GET https://shop.invalid/p", "data": data}
            out = ss._before_send_transaction({"spans": [span]}, {})["spans"][0]
        else:
            crumb = {"type": "http", "category": "httplib", "data": data}
            if hook == "before_breadcrumb":
                out = ss._strip_tokens_from_breadcrumb(crumb, {})
            else:
                out = ss._before_send({"breadcrumbs": {"values": [crumb]}}, {})["breadcrumbs"]["values"][0]
        assert _found(out, [QWORD, SENT]) == [], f"[R5 fragment {hook}] kept: {_san(out)}"
        assert out["data"]["http.fragment"] == "[Filtered]"

    @pytest.mark.parametrize("hook", ["_before_send", "_before_send_transaction"])
    def test_u8d_fix_r4p_region_outside_the_gcc_enum_dropped(self, hook):
        """A3: region is bookkeeping only for the six GCC region keys; any other
        word (user text from a non-app caller) is dropped. Before the fix the
        grammar [a-z_]{2,24} kept it."""
        raw = "region=" + QWORD + "&nocache=true"
        out = getattr(_ss(), hook)({"request": {"query_string": raw}}, {})["request"]["query_string"]
        assert QWORD not in out, f"[R4' region {hook}] word kept: {_san(out)}"
        assert out == "nocache=true"

    def test_u8d_fix_r4p_region_grammar_keeps_every_gcc_region(self):
        """A3 pin: every GCC_REGIONS key (extraction_service) stays readable,
        so a region added there without the grammar goes red here."""
        from app.services.extraction_service import GCC_REGIONS

        ss = _ss()
        for key in sorted(GCC_REGIONS):
            raw = "region=" + key + "&limit=20"
            assert ss._before_send({"request": {"query_string": raw}}, {})["request"]["query_string"] == raw, key


PRICES_PATH = "/api/v1/text/prices/"


class TestFixPathRules:

    @pytest.mark.parametrize(
        "hook,where,value",
        [
            ("_before_send_transaction", "url", "http://testserver" + PRICES_PATH + QWORD + " " + QWORD2),
            ("_before_send", "url", "http://testserver" + PRICES_PATH + QWORD + " " + QWORD2),
            ("_before_send", "url", "http://testserver" + PRICES_PATH + QWORD + "?" + QWORD2),
            ("_before_send", "extra_path", PRICES_PATH + QWORD + " " + QWORD2),
            ("_before_send", "extra_path", PRICES_PATH + QWORD + "#" + QWORD2),
            ("_before_send", "extra_path", PRICES_PATH + QWORD + "/" + QWORD2),
        ],
        ids=["txn_url", "event_url", "event_url_decoded_qmark", "event_extra_path", "extra_path_decoded_hash",
             "extra_path_decoded_slash"],
    )
    def test_u8d_fix_r6_prices_path_product_replaced(self, hook, where, value):
        """A5: GET /api/v1/text/prices/{product} carries the product query in its
        PATH (the only free-text path parameter in app/api), so the segment
        after the prefix becomes [product] in request.url (both hooks) and
        extra.path -- the whole rest of the path, since a decoded '#', '?' or
        '/' may be part of the product text."""
        ev = {"extra": {"path": value}} if where == "extra_path" else {"request": {"url": value}}
        out = getattr(_ss(), hook)(ev, {})
        got = out["extra"]["path"] if where == "extra_path" else out["request"]["url"]
        assert _found(got, [QWORD, QWORD2]) == [], f"[R6 prices {hook} {where}] product kept: {_san(got)}"
        assert got.endswith(PRICES_PATH + "[product]"), _san(got)

    @pytest.mark.parametrize("hook", ["before_breadcrumb", "before_send_walk"])
    @pytest.mark.parametrize("path,needles,tail", [
        ("/api/v1/share/" + SHTOK, [SHTOK], "/api/v1/share/[token]"),
        ("/api/v1/referrals/invite/" + SHTOK + "/quiz", [SHTOK], "/api/v1/referrals/invite/[token]/quiz"),
        (PRICES_PATH + QWORD + " " + QWORD2, [QWORD, QWORD2], PRICES_PATH + "[product]"),
    ], ids=["share", "invite_quiz", "prices"])
    def test_u8d_fix_r6_breadcrumb_data_path(self, hook, path, needles, tail):
        """A9: the ErrorHandlerMiddleware ERROR line passes extra={..., 'path':
        request.url.path}; the logging integration copies record extras into
        the breadcrumb's data, so data.path gets the R6 rule in
        before_breadcrumb AND in _before_send's breadcrumb walk."""
        crumb = {"type": "default", "category": "app.middleware.error_handler", "level": "error",
                 "message": "Unhandled RuntimeError: <RuntimeError>",
                 "data": {"request_id": "rid-u8d", "method": "GET", "path": path}}
        ss = _ss()
        if hook == "before_breadcrumb":
            out = ss._strip_tokens_from_breadcrumb(crumb, {})
        else:
            out = ss._before_send({"breadcrumbs": {"values": [crumb]}}, {})["breadcrumbs"]["values"][0]
        assert _found(out, needles) == [], f"[R6 crumb data.path {hook}] kept: {_san(out)}"
        assert out["data"]["path"] == tail, _san(out["data"])
        assert (out["data"]["request_id"], out["data"]["method"]) == ("rid-u8d", "GET")

    def test_u8d_fix_r6_other_paths_unchanged(self):
        """A5/A9 pin: a path with no capability token and no free text keeps
        its bytes (the prices rule is anchored on its prefix)."""
        ss = _ss()
        for path in ("/api/v1/text/compare", "/api/v1/text/price-kpi", "/api/v1/comparisons/" + "0" * 8,
                     "/api/v1/text/prices"):
            assert ss._before_send({"extra": {"path": path}}, {})["extra"]["path"] == path, path


class TestFixOpenAIIntegrationIsolated:

    @pytest.mark.parametrize("failure", ["import_error", "did_not_enable"])
    def test_u8d_fix_openai_integration_failure_keeps_sentry(self, monkeypatch, failure):
        """B4: the explicit OpenAIIntegration import sits in its own try, so an
        openai integration that cannot load (sentry_sdk raises DidNotEnable
        when openai is missing) never disables Sentry: init still runs with
        the explicit LoggingIntegration and without OpenAIIntegration (which
        then cannot send prompts either). Before the fix the import was inside
        init_sentry's single try, and sentry_sdk.init was never called."""
        import types

        from sentry_sdk.integrations import DidNotEnable

        name = "sentry_sdk.integrations.openai"
        if failure == "import_error":
            monkeypatch.setitem(sys.modules, name, None)
        else:
            class _Broken(types.ModuleType):
                def __getattr__(self, attr):
                    if attr.startswith("__"):
                        raise AttributeError(attr)
                    raise DidNotEnable("openai not installed (u8d fix test)")

            monkeypatch.setitem(sys.modules, name, _Broken(name))
        kw = _recorded_init_kwargs(monkeypatch)
        assert _integration(kw, "OpenAIIntegration") is None
        li = _integration(kw, "LoggingIntegration")
        assert li is not None and (li._breadcrumb_handler.level, li._handler.level) == (logging.ERROR, logging.ERROR)
        assert kw.get("max_request_body_size") == "never" and list(kw.get("trace_propagation_targets")) == []


# ============================================== fix round 2 (ruling UF3, A10)

def test_u8d_red_uf3_r8_query_lines_log_length_only():
    """Ruling UF3: an unsalted sha256[:12] of a query is dictionary-reversible
    for popular pairs, and the three R8 query lines of
    structured_comparison_service are ERROR events that reach Sentry. Each
    logs ``length=%d`` only: its template names no hash and none of its
    arguments touches ``hashlib``. Each statement is found by its template
    prefix (UG4). RED on the fix-round-1 tree (``query_hash=%s`` +
    ``hashlib.sha256(query...)``); mutant M-UF3 restores the hash on one line."""
    rel = "app/services/structured_comparison_service.py"
    tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
    rows = [r for r in R8_IN_EXCEPT if r[1] == rel]
    assert len(rows) == 3, rows
    problems = []
    for name, _rel, prefix, _names in rows:
        calls = [n for n in ast.walk(tree) if _is_error_log_call(n) and _template_text(n).startswith(prefix)]
        if len(calls) != 1:
            problems.append((name, "statements", len(calls)))
            continue
        call = calls[0]
        template = _template_text(call)
        if re.search(r"(?i)hash|digest|sha\d|md5", template) or "length=%d" not in template:
            problems.append((name, "template", template))
        refs = [n.lineno for a in [*call.args, *(k.value for k in call.keywords)] for n in ast.walk(a)
                if isinstance(n, ast.Name) and n.id == "hashlib"]
        if refs:
            problems.append((name, "hashlib in arguments", refs))
    assert problems == [], f"[UF3] the R8 query lines must log length=%d only: {problems}"


# ============================================== fix round 3 (finding F1, ruling UF3)

def _enclosing_except_name(node, par):
    """The name the nearest enclosing ``except ... as <name>`` arm binds; None
    when that arm binds no name or the node sits in no except arm."""
    cur = node
    while cur in par:
        cur = par[cur]
        if isinstance(cur, ast.ExceptHandler):
            return cur.name
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return None
    return None


def _is_len_of_query(node) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len"
            and len(node.args) == 1 and not node.keywords
            and isinstance(node.args[0], ast.Name) and node.args[0].id == "query")


_F1_UF3_ROWS = [r for r in R8_IN_EXCEPT if r[1] == "app/services/structured_comparison_service.py"]


@pytest.mark.parametrize("name,rel,prefix,names", _F1_UF3_ROWS, ids=[r[0] for r in _F1_UF3_ROWS])
def test_u8d_red_f1_uf3_query_reaches_the_line_only_through_len(name, rel, prefix, names):
    """Finding F1 (ruling UF3: nothing derived from the query but its length).
    On each of the three R8 query lines, walked with parent links over every
    argument and keyword of the logger call: every Name ``query`` is the ONLY
    argument of a ``len(...)`` call with no keywords; at least one
    ``len(query)`` is there (no vacuous pass after a rename); every other Name
    is the exception the enclosing ``except ... as <name>`` arm binds, passed
    as a bare positional argument (R2 replaces its text in Sentry). That
    closes what the UF3 node leaves open: a non-hashlib digest
    (``zlib.crc32(query.encode())``, mutant FA16), a raw-text wrapper
    (``str(query)``, FA19 = UG5's limit, closed on these lines), an alias of
    the query bound before the call, and a transformed exception text. The
    statement is found by its template prefix (UG4)."""
    assert len(_F1_UF3_ROWS) == 3, _F1_UF3_ROWS
    tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if _is_error_log_call(n) and _template_text(n).startswith(prefix)]
    assert len(calls) == 1, f"[F1 {name}] expected one ERROR call with template prefix {prefix!r}, found {len(calls)}"
    call = calls[0]
    par = _parents(tree)
    bound = _enclosing_except_name(call, par)
    problems, len_of_query = [], 0
    for root in [*call.args, *(k.value for k in call.keywords)]:
        for n in ast.walk(root):
            if _is_len_of_query(n):
                len_of_query += 1
            if not isinstance(n, ast.Name):
                continue
            parent = par.get(n)
            if n.id == "query":
                if not (_is_len_of_query(parent) and parent.args[0] is n):
                    problems.append(("query outside len(query)", n.lineno, ast.unparse(parent)[:80]))
            elif n.id == "len" and _is_len_of_query(parent) and parent.func is n:
                continue
            elif not (bound is not None and n.id == bound and parent is call and n in call.args):
                problems.append(("name", n.id, n.lineno, ast.unparse(parent)[:80]))
    if len_of_query < 1:
        problems.append(("no len(query) argument", call.lineno))
    assert problems == [], (
        f"[F1 {name}] {rel}:{call.lineno} logs more than the query's length: {problems}")
