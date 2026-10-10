"""Review warm-up (runbook E step 2): fills the caches for the six curated review pairs.

Runs every pair twice, round-robin, the way the app asks (product_a/product_b, region
bahrain, no nocache, so the answers are cached), sleeping --pace seconds between compares
(default 10: at most 6 a minute under the 10-a-minute route limit), and grades each answer
with the canary's A1.8 rule (scripts/verify_after_credits.py). Since U13 anonymous compares
return 401, so run it as the admin caller (unmetered, no history row):

  railway run -s web -- <venv python> scripts/review_warmup.py --send-admin-key

The opt-in reads ADMIN_API_KEY and sends it as X-Admin-Key; the value is never printed.
Output: a pass table, the READY / NO PRICE / FAILED / COLD ONLY / PARTIAL lines and a last
line starting "RESULT:". Exit 0 all READY; 1 any FAILED, or no price amount in any compare;
3 no FAILED but some NO PRICE; 4 SETUP (a 401/403, the opt-in without ADMIN_API_KEY, a
--base carrying credentials); 5 CRASH. An exit code counts only when the last stdout line
starts with "RESULT:"; without one the run did not happen.
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

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import httpx  # noqa: E402

from scripts.verify_after_credits import (  # noqa: E402 - the one rule implementation (B11)
    DEFAULT_BASE,
    EXIT_CRASH,
    EXIT_FAIL,
    EXIT_NO_PRICE,
    EXIT_PASS,
    EXIT_SETUP,
    _harness_auth_headers,
    evaluate_compare,
)

PAIRS = [
    ("iPhone 15", "Samsung Galaxy S24"),
    ("Bose QuietComfort Ultra", "Sony WH-1000XM5"),
    ("Nivea Soft", "Cetaphil Moisturizing Cream"),
    ("HealthAid Vitamin D3", "NOW Foods Vitamin D-3"),
    ("L'Oreal Revitalift", "Olay Regenerist"),
    ("Tom Ford Tobacco Vanille", "Creed Aventus"),
]
DEFAULT_RUNS = 2
DEFAULT_PACE = 10.0
_sleep = time.sleep

COMPARE_PATH = "/api/v1/text/compare"
TABLE = "%-46s %3s %4s %-28s %6s %8s"
_OPT_IN_VALUES = ("1", "true", "yes", "on")
AUTH_HINT = ("setup: the compare routes need a caller since U13; run under railway run -s web "
             "with --send-admin-key (runbook A1.8)")


def _ascii(text) -> str:
    return text.encode("ascii", "backslashreplace").decode("ascii")


def _transport_reason(exc) -> str:
    """The class name only: str(exc) can quote a header value (h11) or the URL."""
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    return "transport_" + type(exc).__name__


def _health(client, base, timeout):
    """None when /health answers 200, else the failure reason."""
    try:
        response = client.get(base + "/health", timeout=timeout)
    except httpx.HTTPError as exc:
        return _transport_reason(exc)
    return None if response.status_code == 200 else "health_%d" % response.status_code


def _compare(client, base, pair, run, timeout) -> dict:
    """One app-shaped compare, graded by the A1.8 rule, as a report row."""
    product_a, product_b = pair
    started = time.monotonic()
    http = None
    try:
        response = client.get(base + COMPARE_PATH, timeout=timeout,
                              params={"product_a": product_a, "product_b": product_b,
                                      "region": "bahrain"})
        http = response.status_code
        try:
            body = response.json()
        except ValueError:
            body = None
        result = evaluate_compare(http, body)
    except httpx.HTTPError as exc:
        result = {"verdict": "FAIL", "reasons": [_transport_reason(exc)], "prices": "0/2",
                  "partial": False, "partial_stage": None}
    return {"pair": _ascii(product_a + " vs " + product_b), "run": run, "http": http,
            "verdict": result["verdict"], "reasons": result["reasons"],
            "prices": result["prices"], "elapsed_s": round(time.monotonic() - started, 1),
            "partial": result["partial"], "partial_stage": result["partial_stage"]}


def _table_row(row) -> str:
    verdict = row["verdict"] if row["verdict"] != "FAIL" else "FAIL:" + row["reasons"][0]
    http = "-" if row["http"] is None else str(row["http"])
    return TABLE % (row["pair"], row["run"], http, verdict, row["prices"],
                    "%.1fs" % row["elapsed_s"])


def _classify(doc, labels, per_pair):
    """Print the pair lists; return the RESULT line and exit code. A pair is FAILED if any
    run fails, else NO PRICE if any run has no price, else READY; COLD ONLY = the first run
    failed and every later run passed (B12); PARTIAL is reported, not gated (B13)."""
    ready, no_price, failed, cold, partial = [], [], [], [], []
    for label, rows in zip(labels, per_pair):
        verdicts = [row["verdict"] for row in rows]
        if "FAIL" in verdicts:
            failed.append(label)
            if len(verdicts) > 1 and verdicts[0] == "FAIL" and set(verdicts[1:]) == {"PASS"}:
                cold.append(label)
        elif "NO_PRICE" in verdicts:
            no_price.append(label)
        else:
            ready.append(label)
        if any(row["partial"] for row in rows):
            partial.append(label)
    print("READY (%d): %s" % (len(ready), " | ".join(ready)))
    print("NO PRICE (%d): %s" % (len(no_price), " | ".join(no_price)))
    print("FAILED (%d): %s" % (len(failed), " | ".join(failed)))
    print("COLD ONLY (%d): %s" % (len(cold), " | ".join(cold)))
    print("PARTIAL: %s" % (" | ".join(partial) or "none"))
    doc.update({"ready": ready, "no_price": no_price, "failed": failed})
    counts = "ready=%d no_price=%d failed=%d" % (len(ready), len(no_price), len(failed))
    priced = any(row["prices"] != "0/2" for row in doc["rows"])
    if failed:
        return "RESULT: FAIL " + counts, EXIT_FAIL
    if not priced:
        return "RESULT: FAIL no_price_in_run " + counts, EXIT_FAIL
    if no_price:
        return "RESULT: FAIL " + counts, EXIT_NO_PRICE
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
    parser = argparse.ArgumentParser(description="Review warm-up (runbook E step 2).")
    parser.add_argument("--base", default=DEFAULT_BASE, help="API base URL (default: production)")
    parser.add_argument("--pairs", nargs="*", metavar="PAIR",
                        help='"A vs B" pairs, split on the first " vs " (default: the six '
                             "review pairs)")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS,
                        help="runs over all pairs (default 2)")
    parser.add_argument("--pace", type=float, default=DEFAULT_PACE,
                        help="seconds between compares (default 10)")
    parser.add_argument("--timeout", type=float, default=150.0,
                        help="per-request timeout in seconds (default 150)")
    parser.add_argument("--report", metavar="PATH", help="also write a JSON report to PATH")
    parser.add_argument("--send-admin-key", action="store_true",
                        help="send X-Admin-Key from the environment (as HARNESS_SEND_ADMIN_KEY=1)")
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    if not (args.pace >= 0 and math.isfinite(args.pace)):
        parser.error("--pace must be a finite number of seconds >= 0")
    if args.pairs == []:
        parser.error('--pairs needs at least one "A vs B" entry')
    if args.pairs and any(" vs " not in pair for pair in args.pairs):
        parser.error('each --pairs entry must read "A vs B"')
    return args


def _run(argv) -> int:
    args = _parse_args(argv)
    base = args.base
    pairs = [tuple(pair.split(" vs ", 1)) for pair in args.pairs] if args.pairs else list(PAIRS)
    doc = {"script": "review_warmup.py", "rule": "A1.8-v1", "base": base, "auth": "none",
           "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "rows": [], "ready": [], "no_price": [], "failed": []}
    if "@" in base:
        doc["base"] = None
        print("setup: the --base URL must not carry credentials")
        return _finish(args.report, doc, "RESULT: FAIL setup=base_userinfo", EXIT_SETUP)
    opted_in = args.send_admin_key or (
        os.getenv("HARNESS_SEND_ADMIN_KEY", "").strip().lower() in _OPT_IN_VALUES)
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
    per_pair = [[] for _pair in pairs]
    client = httpx.Client(timeout=150, headers=auth) if auth else httpx.Client(timeout=150)
    with client:
        failure = _health(client, base, args.timeout)
        if failure:
            print("health: FAIL " + failure)
            return _finish(args.report, doc, "RESULT: FAIL " + failure, EXIT_FAIL)
        print(TABLE % ("pair", "run", "http", "verdict", "prices", "elapsed"))
        plan = [(run, index) for run in range(1, args.runs + 1) for index in range(len(pairs))]
        for count, (run, index) in enumerate(plan):
            if count:
                _sleep(args.pace)
            row = _compare(client, base, pairs[index], run, args.timeout)
            doc["rows"].append(row)
            per_pair[index].append(row)
            print(_table_row(row))
            if row["http"] in (401, 403):
                print(AUTH_HINT)
                return _finish(args.report, doc, "RESULT: FAIL setup=auth_%d" % row["http"],
                               EXIT_SETUP)
    labels = [_ascii(a + " vs " + b) for a, b in pairs]
    result, code = _classify(doc, labels, per_pair)
    return _finish(args.report, doc, result, code)


def main(argv=None) -> int:
    """Run the warm-up. Any unexpected error ends as "RESULT: FAIL error=<ClassName>",
    exit 5: never its text and never a traceback (an exception can carry a header value)."""
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
