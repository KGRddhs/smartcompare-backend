"""Flag-OFF byte-identity harness — corpus-file-driven, ZERO network.

WHAT THIS IS. The reproducible gate a verify agent runs to prove a branch's
flag-OFF behaviour is byte-identical to base: run
``price_service.extract_price_from_html`` over a cached HTML corpus with every
branch-added flag forced OFF, in BOTH exact-gate modes and BOTH currency legs,
canonicalise the results, and print one stable overall SHA-256. Run it at BASE
and at HEAD; the two digests must be equal.

WHY IT LIVES IN THE REPO (M11 backlog item 2, recorded M10 verify finding).
The previous incarnation lived only in a session scratchpad (``g1_harness.py``)
and the M10 verify run fed a FIXED single query to every corpus page — so
586/588 pages hashed the literal ``None`` extraction and the gate had near-zero
discrimination: it would have signed off almost any regression. This port
derives a PER-PAGE query from the page itself (manifest ``derived_query`` /
``name`` -> manifest ``brand`` + the page ``<title>`` tokens -> the URL slug
tokens), so the identity gates actually match, extractors actually run, and
two different extractions hash differently. A degenerate query set (every page
handed the same query) is now a hard error (exit 2), not a silent pass.

USAGE
    # The standard _proof layout (Gulf sweep jsonl + global corpus.json),
    # resolved against --proof-root (default: <repo>/_proof):
    python scripts/verify_flag_byte_identity.py \
        --proof-root C:/Users/.../sc-scraper-proof/_proof \
        --flags ENABLE_SALE_PRICE_FIRST,ENABLE_JSONLD_FIRST \
        --out gate_head.json

    # Any explicit corpus manifest (JSONL rows or JSON {"rows": [...]}):
    python scripts/verify_flag_byte_identity.py \
        --corpus my_corpus.jsonl --html-dir my_html_dir --out gate.json

    # Then diff the printed "OVERALL SHA256" between base and head runs.

MANIFEST CONTRACT (per row): ``url`` is required. The HTML body is resolved,
in order: an explicit ``path``/``html_path`` field; ``<html-dir>/<sha1(
'curl_cffi|'+url)>.html`` (the Gulf sweep convention); ``<html-dir>/<sha1(
url)>.html`` (the global corpus convention). Optional fields used when
present: ``derived_query``/``name`` (the query), ``brand``, ``domain``/
``host``, ``page_currency``/``currency_code``/``registry_currency``. Rows
whose HTML file is missing are skipped and counted in ``skipped_no_html``.

GUARANTEES: no network (local file reads + a pure extraction call only); the
flags named by ``--flags`` are forced OFF in the environment before the app
import AND per call; output records are sorted and JSON-canonicalised
(sort_keys, ensure_ascii), so a rerun over the same corpus and code prints the
same digest.
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# Make `python scripts/verify_flag_byte_identity.py` work from anywhere:
# the app package lives at the repo root, one level above this file.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Both exact-gate modes are always exercised: the gate changes which candidates
# survive, so identity-gated regressions hide in whichever mode you skip.
GATE_MODES = ("false", "true")

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

# Query length cap — mirrors the g1 harness; long enough for brand + title.
_MAX_QUERY_CHARS = 120
_MAX_TITLE_TOKENS = 12


def _page_title(html_text: str) -> str:
    """First ``<title>`` text, unescaped, tags stripped, whitespace collapsed."""
    m = _TITLE_RE.search(html_text or "")
    if not m:
        return ""
    text = html_lib.unescape(_TAG_RE.sub(" ", m.group(1)))
    return _WS_RE.sub(" ", text).strip()


def _slug_tokens(url: str) -> str:
    slug = (url or "").split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
    return _WS_RE.sub(" ", slug.replace("-", " ").replace("_", " ")).strip()


def derive_page_query(record: Dict[str, Any], html_text: str) -> str:
    """A PER-PAGE query so the extractor's identity gates actually engage.

    Priority: the manifest's own ``derived_query``/``name`` (hand-derived,
    known-good) -> ``brand`` + the page ``<title>`` tokens -> ``brand`` + the
    URL slug tokens. Never a fixed constant — the degenerate single-query
    corpus is exactly the failure this function exists to prevent."""
    for key in ("derived_query", "name", "query"):
        val = (record.get(key) or "").strip()
        if val:
            return val[:_MAX_QUERY_CHARS]
    brand = (record.get("brand") or "").strip()
    title = _page_title(html_text)
    if title:
        # Site-name suffixes ("Product | Store") add noise tokens that the
        # word-overlap matchers tolerate; keep the leading segment's tokens.
        head = re.split(r"[|\u2013\u2014]", title)[0].strip() or title
        tokens = head.split()[:_MAX_TITLE_TOKENS]
        q = (brand + " " + " ".join(tokens)).strip()
        if q:
            return q[:_MAX_QUERY_CHARS]
    q = (brand + " " + _slug_tokens(record.get("url") or "")).strip()
    return q[:_MAX_QUERY_CHARS]


def _record_currency(record: Dict[str, Any]) -> str:
    for key in ("page_currency", "currency_code", "registry_currency", "currency"):
        cur = (record.get(key) or "").strip().upper()
        if len(cur) == 3 and cur.isalpha() and cur != "N/A":
            return cur
    return "USD"


def _resolve_html_path(
    record: Dict[str, Any], html_dirs: List[str],
) -> Optional[str]:
    for key in ("path", "html_path"):
        p = record.get(key)
        if p and os.path.exists(p):
            return p
    url = record.get("url") or ""
    if not url:
        return None
    for html_dir in html_dirs:
        for digest in (
            hashlib.sha1(("curl_cffi|" + url).encode()).hexdigest(),  # Gulf sweep
            hashlib.sha1(url.encode()).hexdigest(),  # global corpus
        ):
            p = os.path.join(html_dir, digest + ".html")
            if os.path.exists(p):
                return p
    return None


def load_manifest(
    manifest_path: str,
    html_dir: Any = None,
    corpus_name: str = "corpus",
) -> Tuple[List[Dict[str, Any]], int]:
    """Manifest rows (JSONL, or JSON with a ``rows`` list / a bare list) ->
    normalised harness records. Returns (records, skipped_no_html)."""
    with open(manifest_path, encoding="utf-8") as fh:
        text = fh.read()
    rows: List[Dict[str, Any]]
    try:
        # One JSON document: {"rows": [...]} or a bare list.
        doc = json.loads(text)
        rows = doc.get("rows", []) if isinstance(doc, dict) else doc
    except json.JSONDecodeError:
        # JSONL: one row object per line.
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]

    if html_dir is None:
        html_dirs: List[str] = []
    elif isinstance(html_dir, str):
        html_dirs = [html_dir]
    else:
        html_dirs = list(html_dir)

    records: List[Dict[str, Any]] = []
    skipped = 0
    for row in rows:
        if not isinstance(row, dict) or not row.get("url"):
            continue
        path = _resolve_html_path(row, html_dirs)
        if path is None:
            skipped += 1
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            html_text = fh.read()
        records.append({
            "corpus": corpus_name,
            "url": row["url"],
            "domain": row.get("domain") or row.get("host") or "",
            "page_currency": _record_currency(row),
            "query": derive_page_query(row, html_text),
            "path": path,
        })
    return records, skipped


def load_proof_layout(proof_root: str) -> Tuple[List[Dict[str, Any]], int]:
    """The standard ``_proof`` layout: ``sweep2_curl_cffi.jsonl`` + ``html/``
    (Gulf) and ``global/corpus.json`` + ``global/html`` (+ ``_dach_html``)."""
    records: List[Dict[str, Any]] = []
    skipped = 0
    gulf_manifest = os.path.join(proof_root, "sweep2_curl_cffi.jsonl")
    if os.path.exists(gulf_manifest):
        recs, sk = load_manifest(
            gulf_manifest, os.path.join(proof_root, "html"), corpus_name="gulf",
        )
        records.extend(recs)
        skipped += sk
    global_manifest = os.path.join(proof_root, "global", "corpus.json")
    if os.path.exists(global_manifest):
        recs, sk = load_manifest(
            global_manifest,
            [
                os.path.join(proof_root, "global", "html"),
                os.path.join(proof_root, "global", "_dach_html"),
            ],
            corpus_name="global",
        )
        records.extend(recs)
        skipped += sk
    return records, skipped


def canonical(value: Any) -> Any:
    """JSON-canonical form of an extraction result (repr for the un-JSON-able)."""
    try:
        return json.loads(json.dumps(
            value, sort_keys=True, ensure_ascii=True, default=repr,
        ))
    except Exception:  # noqa: BLE001 — a hash input must always materialise
        return repr(value)


def run_harness(
    records: List[Dict[str, Any]],
    flags: List[str],
    skipped_no_html: int = 0,
) -> Tuple[Dict[str, Any], str]:
    """Run the extraction sweep; return (payload, overall_sha256).

    Every flag in ``flags`` is forced ``"false"`` for the duration (previous
    environment values are restored afterwards), and the exact-price gate is
    swept over both modes. Each page runs TWO currency legs — its own page
    currency and the BHD ask — because currency-relabel regressions only show
    on the leg where ask and page disagree."""
    from app.services.price_service import extract_price_from_html

    pinned = list(flags) + ["ENABLE_EXACT_PRICE_GATE"]
    saved = {name: os.environ.get(name) for name in pinned}
    payload: Dict[str, Any] = {
        "n_records": len(records),
        "skipped_no_html": skipped_no_html,
        "flags_forced_off": sorted(flags),
        "results": [],
    }
    try:
        for name in flags:
            os.environ[name] = "false"
        for gate in GATE_MODES:
            os.environ["ENABLE_EXACT_PRICE_GATE"] = gate
            for rec in records:
                with open(rec["path"], encoding="utf-8", errors="replace") as fh:
                    html_text = fh.read()
                # Two legs unconditionally (stable call count): the page's own
                # currency and the BHD ask. When they coincide the legs agree
                # by construction; when they differ, the bhd leg is where
                # currency-relabel regressions surface.
                for leg, cur in (("page", rec["page_currency"]), ("bhd", "BHD")):
                    try:
                        res = extract_price_from_html(
                            html_text, rec["query"], cur, rec["domain"], rec["url"],
                        )
                        val = canonical(res)
                        err = None
                    except Exception as e:  # noqa: BLE001 — record, keep sweeping
                        val = None
                        err = "%s: %s" % (type(e).__name__, e)
                    payload["results"].append({
                        "corpus": rec["corpus"],
                        "url": rec["url"],
                        "query": rec["query"],
                        "gate": gate,
                        "leg": leg,
                        "currency": cur,
                        "result": val,
                        "error": err,
                    })
    finally:
        for name, old in saved.items():
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old

    payload["results"].sort(key=lambda r: (r["corpus"], r["url"], r["gate"], r["leg"]))
    payload["distinct_queries"] = len({r["query"] for r in records})
    payload["non_none_extractions"] = sum(
        1 for r in payload["results"] if r["result"] is not None
    )
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=1)
    return payload, hashlib.sha256(blob.encode("utf-8")).hexdigest()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", action="append", default=[],
                        help="manifest path (JSONL rows or JSON {'rows': [...]}); repeatable")
    parser.add_argument("--html-dir", default=None,
                        help="directory of cached HTML bodies for --corpus rows")
    parser.add_argument("--proof-root", default=None,
                        help="root of the standard _proof layout (default: <repo>/_proof "
                             "when no --corpus is given)")
    parser.add_argument("--flags", default="",
                        help="comma-separated flags to force OFF for the sweep")
    parser.add_argument("--limit", type=int, default=0,
                        help="smoke mode: only the first N records (manifest "
                             "order, deterministic); 0 = all")
    parser.add_argument("--out", default=None, help="write the full payload JSON here")
    args = parser.parse_args(argv)

    flags = [f.strip() for f in args.flags.split(",") if f.strip()]
    # Pin the environment BEFORE the app import so even an import-time flag
    # read (none exist today, by repo convention) cannot leak ON state.
    for name in flags:
        os.environ[name] = "false"

    records: List[Dict[str, Any]] = []
    skipped = 0
    if args.corpus:
        for path in args.corpus:
            recs, sk = load_manifest(path, args.html_dir,
                                     corpus_name=os.path.basename(path))
            records.extend(recs)
            skipped += sk
    else:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        proof_root = args.proof_root or os.path.join(repo_root, "_proof")
        if not os.path.isdir(proof_root):
            print("ERROR: no --corpus given and %s does not exist" % proof_root)
            return 1
        records, skipped = load_proof_layout(proof_root)

    if not records:
        print("ERROR: corpus resolved to zero records (skipped_no_html=%d)" % skipped)
        return 1
    if args.limit and args.limit > 0:
        records = records[:args.limit]
    queries = {r["query"] for r in records}
    if len(records) > 1 and len(queries) == 1:
        print("ERROR: DEGENERATE QUERY SET — every page got the same query %r; "
              "the gate would hash near-constant output (the M10 586/588-None "
              "failure). Fix the manifest/derivation." % next(iter(queries)))
        return 2

    payload, digest = run_harness(records, flags, skipped_no_html=skipped)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=1))
    print("RECORDS n=%d skipped_no_html=%d distinct_queries=%d non_none=%d calls=%d"
          % (len(records), skipped, payload["distinct_queries"],
             payload["non_none_extractions"], len(payload["results"])))
    print("OVERALL SHA256 " + digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
