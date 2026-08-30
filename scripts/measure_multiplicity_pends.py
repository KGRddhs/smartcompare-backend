"""M10 UNIT A3 — the corpus DRIFT GATE for the multiplicity population.

Runs ``extract_jsonld_price`` over every cached page in the two read-only
corpora with ``pending_out`` supplied, and counts how many pages the JSON-LD
shape ladder PRICES versus how many it PENDS on multiplicity. The policy pinned
in ``price_service._MULTIPLICITY_POLICY`` and
``tests/test_multiplicity_discriminator_policy.py`` is adjudicated against that
population; if the population moves, the policy needs re-adjudicating, and this
is what makes the move visible.

WHAT IT ASSERTS, and the run on 2026-08-31 met it exactly:

    pages swept                        414
    pages the ladder PRICED            219
    pages that PENDED on multiplicity   40

MODE: ``ENABLE_EXACT_PRICE_GATE=false`` (extraction isolated from the exact
gate — the mode CLAUDE.md documents for measuring extraction) and
``ENABLE_JSONLD_SHAPE_LADDER`` at its shipped default ON. With the ladder OFF
the adjudicator never runs and every count here is structurally zero, so the
sweep would measure nothing.

ON THE QUERY, AND WHY THE PRICED COUNT IS 216 AND NOT 220. Every page is swept
with a query derived FROM THE PAGE ITSELF, because the corpora record no user
query: the Gulf rows carry the sweep's own ``derived_query``; the global rows
get the first JSON-LD ``Product``/``ProductGroup`` name, else ``og:title``,
else ``<title>``. That derivation is deliberately simple and documented rather
than clever, and it differs on a handful of global pages from the ad-hoc
derivation used during the unit's design (which scored 220 priced on the same
bytes). The PEND count is 40 under BOTH derivations, which is the number this
gate exists for; the priced count is derivation-sensitive and is pinned only to
make an accidental change to it visible. The INVARIANT is that this script, run
twice against the same corpora, returns the same three numbers. A change means
an extractor moved the population.

The brand is passed as the query itself, which is what makes the JSON-LD branch
reachable at all: an EMPTY ``brand`` drops every Product at the brand gate and
manufactures a fake all-zero cohort (a documented measurement trap).

ZERO NETWORK. The corpora under ``_proof/`` are read-only and git-excluded, so
this is a reproduction harness, not a test — nothing under ``tests/`` may
depend on a corpus path. ``--corpus-root`` lets a pristine base worktree read
the corpora from the main checkout.

    python scripts/measure_multiplicity_pends.py [--out <path>] \
        [--corpus-root <repo>]
"""
import argparse
import hashlib
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

CORPUS_ROOT = REPO

#: The 2026-08-31 baseline. Any drift blocks the commit and is a signal to
#: re-adjudicate the policy, not to edit these numbers.
EXPECTED_PAGES = 414
EXPECTED_PRICED = 219
EXPECTED_PENDS = 40


def _read(path):
    return io.open(path, "r", encoding="utf-8", errors="replace").read()


def _jsonld_product_name(html):
    """First JSON-LD Product/ProductGroup ``name``, at any nesting depth."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    found = []

    def walk(node):
        if found:
            return
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        raw = node.get("@type")
        types = raw if isinstance(raw, list) else [raw]
        if any(t in ("Product", "ProductGroup") for t in types
               if isinstance(t, str)):
            name = node.get("name")
            if isinstance(name, str) and name.strip():
                found.append(name.strip())
                return
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            walk(json.loads(script.string or script.get_text() or ""))
        except (ValueError, TypeError):
            continue
        if found:
            break
    if found:
        return found[0]
    meta = soup.find("meta", property="og:title")
    if meta and (meta.get("content") or "").strip():
        return meta["content"].strip()
    return soup.title.get_text().strip() if soup.title else ""


def inventory():
    """Every cached page with the query and currency to sweep it with."""
    root = CORPUS_ROOT
    rows = []

    gulf_jsonl = os.path.join(root, "_proof", "sweep2_curl_cffi.jsonl")
    gulf_html = os.path.join(root, "_proof", "html")
    with io.open(gulf_jsonl, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            url = rec.get("url") or ""
            digest = hashlib.sha1(
                ("curl_cffi|" + url).encode("utf-8")).hexdigest()
            path = os.path.join(gulf_html, digest + ".html")
            if os.path.exists(path):
                rows.append({
                    "corpus": "gulf", "url": url, "path": path,
                    "host": rec.get("domain"),
                    "query": rec.get("derived_query") or "",
                    "currency": rec.get("page_currency")
                                or rec.get("registry_currency") or "USD",
                })

    global_json = os.path.join(root, "_proof", "global", "corpus.json")
    global_dirs = (os.path.join(root, "_proof", "global", "html"),
                   os.path.join(root, "_proof", "global", "_dach_html"))
    with io.open(global_json, "r", encoding="utf-8") as fh:
        blob = json.load(fh)
    records = blob if isinstance(blob, list) else (
        blob.get("pages") or blob.get("rows") or [])
    for rec in records:
        if not isinstance(rec, dict):
            continue
        url = rec.get("url") or ""
        if not url:
            continue
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
        for directory in global_dirs:
            path = os.path.join(directory, digest + ".html")
            if os.path.exists(path):
                rows.append({
                    "corpus": "global", "url": url, "path": path,
                    "host": rec.get("host") or rec.get("domain"),
                    "query": None,  # derived from the bytes below
                    "currency": rec.get("currency_code") or "USD",
                })
                break
    return rows


def sweep(rows):
    from app.services.price_service import extract_jsonld_price

    out = []
    for index, row in enumerate(rows):
        html = _read(row["path"])
        query = row["query"]
        if query is None:
            query = _jsonld_product_name(html)
        pending = []
        got = extract_jsonld_price(
            html, query, row["currency"], query,
            category="fragrances", pending_out=pending,
        )
        pended = sorted({c["amount"] for c in pending[0]}) if pending else []
        out.append({
            "i": index, "corpus": row["corpus"], "host": row["host"],
            "url": row["url"], "query": query, "currency": row["currency"],
            "amount": None if got is None else got.get("amount"),
            "pended": pended,
        })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None,
                        help="write the full per-page JSON here")
    parser.add_argument("--corpus-root", default=None,
                        help="repo holding _proof/ (default: this checkout)")
    args = parser.parse_args()

    global CORPUS_ROOT
    if args.corpus_root:
        CORPUS_ROOT = args.corpus_root

    os.environ["ENABLE_EXACT_PRICE_GATE"] = "false"
    os.environ.pop("ENABLE_JSONLD_SHAPE_LADDER", None)

    rows = inventory()
    records = sweep(rows)

    pages = len(records)
    priced = sum(1 for r in records if r["amount"] is not None)
    pends = sum(1 for r in records if r["pended"])
    by_host = {}
    for record in records:
        if record["pended"]:
            by_host.setdefault(record["host"], []).append(record["pended"])

    summary = {
        "pages": pages, "priced": priced, "pends": pends,
        "expected": {"pages": EXPECTED_PAGES, "priced": EXPECTED_PRICED,
                     "pends": EXPECTED_PENDS},
        "pend_hosts": dict(sorted(by_host.items())),
    }
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"summary": summary, "pages": records},
                                indent=1, ensure_ascii=False))

    ok = (pages == EXPECTED_PAGES and priced == EXPECTED_PRICED
          and pends == EXPECTED_PENDS)
    sys.stdout.write(
        "pages=%d priced=%d pends=%d -> %s\n"
        % (pages, priced, pends, "OK" if ok else "DRIFT")
    )
    if not ok:
        sys.stdout.write(
            "DRIFT: expected pages=%d priced=%d pends=%d. The multiplicity "
            "population moved; re-adjudicate the policy in "
            "price_service._MULTIPLICITY_POLICY before updating these "
            "numbers.\n"
            % (EXPECTED_PAGES, EXPECTED_PRICED, EXPECTED_PENDS)
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
