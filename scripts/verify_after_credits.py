"""A1.8 canary: proves the funded OpenAI key yields real comparisons (runbook A1 step 8).

Read-only against production; spends five uncached compares: the three q-form pairs, the
app-shaped product_a/product_b probe and one stream of the probe pair. Since U13 every
anonymous compare returns 401, so run it with the web service's environment and opt in:

  railway run -s web -- <venv python> scripts/verify_after_credits.py --send-admin-key
  railway run -s web -- env HARNESS_SEND_ADMIN_KEY=1 <venv python> scripts/verify_after_credits.py

The opt-in reads ADMIN_API_KEY and sends it as X-Admin-Key; the value is never printed.
Output: one JSON line per check (health, each pair, the probe, the stream), then a last
line starting "RESULT:". Exit 0 PASS; 1 FAIL (a hard reason anywhere, or no price amount
anywhere in the run); 3 NO_PRICE (nothing failed, some compare carries no price amount);
4 SETUP (a 401/403, the opt-in without ADMIN_API_KEY, a --base carrying credentials);
5 CRASH. An exit code counts only when the last stdout line starts with "RESULT:"; without
one the run did not happen (2 = an argparse usage error or a missing file).
Never run it with DEBUG logging for httpx/httpcore: that trace quotes a malformed header value.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

DEFAULT_BASE = "https://web-production-58776.up.railway.app"
DEFAULT_PAIRS = [
    "iPhone 15 vs Galaxy S24",
    "Dior Sauvage EDP 100ml vs Bleu de Chanel EDP 100ml",
    "Optimum Nutrition Gold Standard Whey vs Dymatize ISO100",
]
DEFAULT_PROBE = ("iPhone 15", "Samsung Galaxy S24")

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_NO_PRICE = 3
EXIT_SETUP = 4
EXIT_CRASH = 5

RULE = "A1.8-v1"
COMPARE_PATH = "/api/v1/text/compare"
STREAM_PATH = "/api/v1/text/compare/stream"
TERMINAL_EVENTS = ("settle_complete", "complete")
SOFT_REASON = "no_price_amount"
# Copied verbatim from app/services/response_builder.py:625 (_SPEC_NA_TOKENS, main 3b24d182).
_SPEC_NA_TOKENS = {"n/a", "na", "none", "unknown", "-", ""}
# Fields that name the product or carry pipeline bookkeeping, never a compared spec (B1).
_NON_SPEC_FIELDS = {"brand", "model", "variant", "category", "error", "name"}
_OPT_IN_VALUES = ("1", "true", "yes", "on")
AUTH_HINT = ("setup: the compare routes need a caller since U13; run under railway run -s web "
             "with --send-admin-key (runbook A1.8)")


def _env_opt_in() -> bool:
    return os.getenv("HARNESS_SEND_ADMIN_KEY", "").strip().lower() in _OPT_IN_VALUES


def _harness_auth_headers(opt_in: bool = False) -> dict:
    """{"X-Admin-Key": ADMIN_API_KEY} when opted in (the argument, or HARNESS_SEND_ADMIN_KEY
    in 1/true/yes/on) and the variable is non-empty, else {}. Never print the value."""
    key = os.getenv("ADMIN_API_KEY", "")
    if (opt_in or _env_opt_in()) and key:
        return {"X-Admin-Key": key}
    return {}


# ---------------------------------------------------------------------------
# The A1.8 rule
# ---------------------------------------------------------------------------
def _text(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _amount(price):
    """The positive amount of a showable wire price object, else None (R9, R10, B6)."""
    if not isinstance(price, dict):
        return None
    if price.get("unavailable") is True or price.get("source_method") == "estimated":
        return None
    amount = price.get("amount")
    if isinstance(amount, (int, float)) and not isinstance(amount, bool):
        if math.isfinite(amount) and amount > 0:
            return amount
    return None


def _real_spec_row(row) -> bool:
    """B1: a compared field with a real value on BOTH products (no placeholder, no identity)."""
    if not isinstance(row, dict) or not isinstance(row.get("field"), str):
        return False
    field = row["field"]
    if field in _NON_SPEC_FIELDS or field.endswith("_source") or field.startswith("_"):
        return False
    for key in ("p0_value", "p1_value"):
        # a missing value reads "None" -> "none", a placeholder token like "N/A" or blank
        if str(row.get(key)).strip().lower() in _SPEC_NA_TOKENS:
            return False
    return True


def _verdict(reasons, soft) -> str:
    if any(reason != soft for reason in reasons):
        return "FAIL"
    return "NO_PRICE" if reasons else "PASS"


def _blank_compare() -> dict:
    return {"verdict": "FAIL", "reasons": [], "code": None, "prices": "0/2",
            "amounts": [None, None], "winner": None, "spec_rows": 0, "spec_rows_real": 0,
            "pros": [0, 0], "cons": [0, 0], "comparison_error": False, "partial": False,
            "partial_stage": None}


def _product_reasons(products, legacy, out) -> list:
    """R8-R10 over the two overview products; fills pros, cons, amounts and prices."""
    reasons = []
    for i, product in enumerate(products):
        out["pros"][i] = sum(1 for item in _list(product.get("pros")) if _text(item))
        out["cons"][i] = sum(1 for item in _list(product.get("cons")) if _text(item))
    if 0 in out["pros"]:
        reasons.append("no_pros")
    if 0 in out["cons"]:
        reasons.append("no_cons")
    unpriced_retailer = False
    for i, product in enumerate(products):
        price = product.get("price")
        out["amounts"][i] = _amount(price)
        alias = _dict(legacy[i]) if i < len(legacy) else {}
        retailer = (_text(_dict(price).get("retailer"))
                    or _text(_dict(alias.get("price")).get("retailer"))
                    or _text(alias.get("retailer")))
        if retailer and out["amounts"][i] is None:
            unpriced_retailer = True
    if unpriced_retailer:
        reasons.append("retailer_without_amount")
    priced = sum(1 for amount in out["amounts"] if amount is not None)
    out["prices"] = "%d/2" % priced
    if priced == 0:
        reasons.append(SOFT_REASON)
    return reasons


def evaluate_compare(http_status, body) -> dict:
    """The A1.8 rule (R1-R10) over one compare response: {verdict, reasons, ...fields}.
    FAIL on any hard reason, NO_PRICE when no_price_amount is the only reason, else PASS."""
    out = _blank_compare()
    if isinstance(body, dict) and isinstance(body.get("code"), str):
        out["code"] = body["code"]
    if http_status != 200:
        out["reasons"] = ["http_%s" % http_status]
        return out
    if not isinstance(body, dict):
        out["reasons"] = ["non_json"]
        return out
    reasons = []
    if body.get("success") is not True:
        reasons.append("not_success")
    comparison = body.get("comparison")
    if not isinstance(comparison, dict):
        reasons.append("comparison_missing")
    elif comparison.get("error"):
        reasons.append("comparison_error")
        out["comparison_error"] = True
    overview = _dict(body.get("overview"))
    winner = _dict(overview.get("winner")).get("name")
    if _text(winner):
        out["winner"] = winner
    else:
        reasons.append("no_winner")
    products = overview.get("products")
    shaped = (isinstance(products, list) and len(products) == 2
              and all(isinstance(product, dict) for product in products))
    if not shaped:
        reasons.append("products_shape")
    rows = _list(_dict(_dict(body.get("specs")).get("specs_comparison")).get("rows"))
    out["spec_rows"] = len(rows)
    out["spec_rows_real"] = sum(1 for row in rows if _real_spec_row(row))
    if out["spec_rows_real"] == 0:
        reasons.append("no_spec_rows")
    if shaped:
        reasons.extend(_product_reasons(products, _list(body.get("products")), out))
    metadata = _dict(body.get("metadata"))
    out["partial"] = metadata.get("partial") is True
    out["partial_stage"] = metadata.get("partial_stage")
    out["reasons"] = reasons
    out["verdict"] = _verdict(reasons, SOFT_REASON)
    return out


def _sse_frames(lines) -> list:
    """[(event, data)] from SSE lines: a blank line ends a frame; every other line (a ':'
    comment, an id: or retry: field) is ignored. One data line per frame (text_routes.py)."""
    frames, event, data, started = [], None, None, False
    for line in list(lines) + [""]:
        if line == "":
            if started:
                frames.append((event, data))
            event, data, started = None, None, False
        elif line.startswith("event:"):
            event, started = line[len("event:"):].strip(), True
        elif line.startswith("data:"):
            started = True
            try:
                data = json.loads(line[len("data:"):].strip())
            except ValueError:
                data = None
    return frames


def _blank_stream() -> dict:
    return {"verdict": "FAIL", "reasons": [], "events": 0, "terminal": None,
            "terminal_success": None, "amounts": [None, None]}


def evaluate_stream(http_status, lines) -> dict:
    """S1-S5 over one SSE response (B2): a terminal frame exists, no error frame anywhere,
    EVERY terminal carries success:true, and the FIRST terminal's payload passes
    evaluate_compare (its reasons prefixed stream_, stream_no_price_amount soft)."""
    out = _blank_stream()
    if http_status != 200:
        out["reasons"] = ["http_%s" % http_status]
        return out
    frames = _sse_frames(lines)
    terminals = [(event, data) for event, data in frames if event in TERMINAL_EVENTS]
    reasons = []
    if not terminals:
        reasons.append("stream_no_terminal")
    if any(event == "error" for event, _data in frames):
        reasons.append("stream_error_event")
    if terminals:
        ok = [_dict(data).get("success") is True for _event, data in terminals]
        out["terminal"] = terminals[-1][0]
        out["terminal_success"] = all(ok)
        if not all(ok):
            reasons.append("stream_terminal_not_success")
        first = evaluate_compare(200, terminals[0][1])
        reasons.extend("stream_" + reason for reason in first["reasons"])
        out["amounts"] = first["amounts"]
    out["events"] = len(frames)
    out["reasons"] = reasons
    out["verdict"] = _verdict(reasons, "stream_" + SOFT_REASON)
    return out


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------
def _transport_reason(exc) -> str:
    """The class name only: str(exc) can quote a header value (h11) or the URL."""
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    return "transport_" + type(exc).__name__


def _json_or_none(response):
    try:
        return response.json()
    except ValueError:
        return None


def _health(client, base, timeout) -> dict:
    started = time.monotonic()
    row = {"kind": "health", "label": "/health", "http": None, "reasons": []}
    try:
        response = client.get(base + "/health", timeout=timeout)
        row["http"] = response.status_code
        if response.status_code != 200:
            row["reasons"] = ["health_%d" % response.status_code]
    except httpx.HTTPError as exc:
        row["reasons"] = [_transport_reason(exc)]
    row["ms"] = int((time.monotonic() - started) * 1000)
    row["verdict"] = "FAIL" if row["reasons"] else "PASS"
    return row


def _check(client, base, kind, label, params, timeout) -> dict:
    """One compare (kind compare|probe) or the stream, as an output row."""
    started = time.monotonic()
    row = {"kind": kind, "label": label, "http": None}
    try:
        if kind == "stream":
            with client.stream("GET", base + STREAM_PATH, params=params,
                               timeout=timeout) as response:
                lines = list(response.iter_lines()) if response.status_code == 200 else []
            row["http"] = response.status_code
            result = evaluate_stream(response.status_code, lines)
        else:
            response = client.get(base + COMPARE_PATH, params=params, timeout=timeout)
            row["http"] = response.status_code
            result = evaluate_compare(response.status_code, _json_or_none(response))
    except httpx.HTTPError as exc:
        result = _blank_stream() if kind == "stream" else _blank_compare()
        result["reasons"] = [_transport_reason(exc)]
    row["ms"] = int((time.monotonic() - started) * 1000)
    row.update(result)
    return row


def _emit(row) -> None:
    print(json.dumps(row, ensure_ascii=True, sort_keys=True))


def _summary(rows):
    """The RESULT line and exit code; R11: no price amount anywhere in the run fails it (B4)."""
    fails = sum(1 for row in rows if row["verdict"] == "FAIL")
    no_price = sum(1 for row in rows if row["verdict"] == "NO_PRICE")
    priced = any(amount is not None for row in rows for amount in row.get("amounts", ()))
    if fails:
        return "RESULT: FAIL fail=%d no_price=%d" % (fails, no_price), EXIT_FAIL
    if no_price and not priced:
        return "RESULT: FAIL no_price_in_run fail=0 no_price=%d" % no_price, EXIT_FAIL
    if no_price:
        return "RESULT: FAIL fail=0 no_price=%d" % no_price, EXIT_NO_PRICE
    return "RESULT: PASS", EXIT_PASS


def _finish(path, doc, result, code) -> int:
    """Write the optional report, then print the RESULT line (the last stdout line)."""
    if path:
        doc.update({"result": result, "exit": code})
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="ascii", newline="\n") as handle:
            handle.write(json.dumps(doc, ensure_ascii=True, sort_keys=True) + "\n")
    print(result)
    return code


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="A1.8 canary (runbook A1 step 8).")
    parser.add_argument("--base", default=DEFAULT_BASE, help="API base URL (default: production)")
    parser.add_argument("--pairs", nargs="*", default=list(DEFAULT_PAIRS), metavar="PAIR",
                        help='q-form pairs, each "A vs B" (default: the three canary pairs)')
    parser.add_argument("--probe", nargs=2, default=list(DEFAULT_PROBE), metavar=("A", "B"),
                        help="the app-shaped product_a/product_b pair for the probe and the stream")
    parser.add_argument("--timeout", type=float, default=150.0,
                        help="per-request timeout in seconds (default 150)")
    parser.add_argument("--report", metavar="PATH", help="also write a JSON report to PATH")
    parser.add_argument("--send-admin-key", action="store_true",
                        help="send X-Admin-Key from the environment (as HARNESS_SEND_ADMIN_KEY=1)")
    args = parser.parse_args(argv)
    if args.pairs == []:
        parser.error('--pairs needs at least one "A vs B" entry')
    return args


def _run(argv) -> int:
    args = _parse_args(argv)
    base = args.base
    doc = {"script": "verify_after_credits.py", "rule": RULE, "base": base, "auth": "none",
           "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "rows": []}
    if "@" in base:
        doc["base"] = None
        print("setup: the --base URL must not carry credentials")
        return _finish(args.report, doc, "RESULT: FAIL setup=base_userinfo", EXIT_SETUP)
    opted_in = args.send_admin_key or _env_opt_in()
    key = os.getenv("ADMIN_API_KEY", "")
    if opted_in and not key:
        print("setup: ADMIN_API_KEY is not set in this environment")
        return _finish(args.report, doc, "RESULT: FAIL setup=admin_variable_missing",
                       EXIT_SETUP)
    if opted_in and key != key.strip():  # H4: a pasted space/newline (h11 would quote it)
        print("setup: ADMIN_API_KEY carries leading or trailing whitespace, or is blank")
        return _finish(args.report, doc, "RESULT: FAIL setup=admin_variable_malformed",
                       EXIT_SETUP)
    auth = _harness_auth_headers(opt_in=args.send_admin_key)
    doc["auth"] = "admin" if auth else "none"
    rows = doc["rows"]
    product_a, product_b = args.probe
    probe = {"product_a": product_a, "product_b": product_b, "region": "bahrain",
             "nocache": "true"}
    checks = [("compare", pair, {"q": pair, "nocache": "true", "region": "bahrain"})
              for pair in args.pairs]
    checks.append(("probe", product_a + " vs " + product_b, probe))
    checks.append(("stream", product_a + " vs " + product_b, probe))
    client = httpx.Client(timeout=150, headers=auth) if auth else httpx.Client(timeout=150)
    with client:
        rows.append(_health(client, base, args.timeout))
        _emit(rows[-1])
        if rows[-1]["verdict"] == "PASS":
            for kind, label, params in checks:
                row = _check(client, base, kind, label, params, args.timeout)
                rows.append(row)
                _emit(row)
                if row["http"] in (401, 403):
                    print(AUTH_HINT)
                    return _finish(args.report, doc, "RESULT: FAIL setup=auth_%d" % row["http"],
                                   EXIT_SETUP)
    result, code = _summary(rows)
    return _finish(args.report, doc, result, code)


def main(argv=None) -> int:
    """Run the canary. Any unexpected error ends as "RESULT: FAIL error=<ClassName>", exit 5:
    never its text and never a traceback (an exception can carry a header value)."""
    try:
        sys.stdout.reconfigure(line_buffering=True)  # H2: a pipe is block-buffered; flush each row
    except Exception:  # noqa: BLE001 - best effort: a stream without reconfigure keeps working
        pass
    try:
        return _run(argv)
    except Exception as exc:  # noqa: BLE001 - the class name only (B7)
        print("RESULT: FAIL error=%s" % type(exc).__name__)
        return EXIT_CRASH


if __name__ == "__main__":
    sys.exit(main())
