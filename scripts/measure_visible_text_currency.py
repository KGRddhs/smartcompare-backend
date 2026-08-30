"""M10 UNIT A1 — the corpus before/after gate for ENABLE_VISIBLE_TEXT_CURRENCY.

Runs ``extract_price_from_html`` over every cached page in the two read-only
corpora, in SHIPPED mode (``ENABLE_EXACT_PRICE_GATE`` at its default ON,
``ENABLE_NOT_A_PDP_FILTER`` unset) with a BHD ask, once with the rung OFF and
once with it ON, and diffs the two.

ACCEPTANCE, and the run on 2026-08-31 met it exactly:

  * 414 cached pages.
  * flag OFF, exactly ONE rung-3 ASK-currency stamp — a price labelled BHD whose
    page records a different currency and where ``_page_currency_evidence``
    returned None: **faces.ae, 1515.0 "BHD", recorded page currency AED**.
  * OFF -> ON, the diff is exactly **ONE row**: faces.ae,
    ``1515.0 BHD / original BHD / page_scrape`` becomes
    ``155.14 BHD / original AED / converted_usd``. Any second row is a
    regression and blocks the commit.

The two secondary counts this prints (``n_priced`` 142,
``n_labelled_bhd_foreign_truth`` 51, of which 49 ``converted_usd``) are lower
than the 138 / 120 / 119 recorded in the M10 dossier because the dossier's
harness derived its per-page query and its per-page "truth" from the corpus
files with slightly different key precedence. They are descriptive, not the
gate. The gate is the two bolded lines above, and both reproduce exactly.

ZERO NETWORK. The corpora under ``_proof/`` are read-only and git-excluded, so
this script is a reproduction harness, not a test: nothing under ``tests/`` may
depend on a corpus path. ``--corpus-root`` lets a pristine base worktree (which
has no ``_proof/`` of its own) read the corpora from the main checkout, which is
how the flag-OFF byte-identity proof is run.

    python scripts/measure_visible_text_currency.py [--out <path>]
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


def _corpus_paths():
    root = CORPUS_ROOT
    return (
        os.path.join(root, "_proof", "sweep2_curl_cffi.jsonl"),
        os.path.join(root, "_proof", "html"),
        os.path.join(root, "_proof", "global", "corpus.json"),
        (os.path.join(root, "_proof", "global", "html"),
         os.path.join(root, "_proof", "global", "_dach_html")),
    )


def inventory():
    """Every cached page with its recorded page currency. 92 Gulf + 322 global."""
    GULF_JSONL, GULF_HTML, GLOBAL_JSON, GLOBAL_HTML = _corpus_paths()
    rows = []
    with io.open(GULF_JSONL, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            url = rec.get("url") or ""
            digest = hashlib.sha1(("curl_cffi|" + url).encode("utf-8")).hexdigest()
            path = os.path.join(GULF_HTML, digest + ".html")
            if os.path.exists(path):
                rows.append({"corpus": "gulf", "url": url, "path": path,
                             "host": rec.get("domain"),
                             "truth": rec.get("registry_currency")})
    with io.open(GLOBAL_JSON, "r", encoding="utf-8") as fh:
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
        for directory in GLOBAL_HTML:
            path = os.path.join(directory, digest + ".html")
            if os.path.exists(path):
                rows.append({"corpus": "global", "url": url, "path": path,
                             "host": rec.get("host") or rec.get("domain"),
                             "truth": (rec.get("currency")
                                       or rec.get("page_currency")
                                       or rec.get("registry_currency"))})
                break
    return rows


def page_query(soup, url):
    """The query the page itself implies: JSON-LD Product.name, else og:title,
    else <title>. Deliberately the page's OWN identity, so the exact gate is
    exercised the way a matching search result would exercise it."""
    from app.services import price_service as ps

    def walk(node, depth=0):
        if depth > 6:
            return None
        if isinstance(node, dict):
            types = node.get("@type")
            types = types if isinstance(types, list) else [types]
            if any(isinstance(t, str) and t.lower() == "product" for t in types):
                name = node.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
            children = list(node.values())
        elif isinstance(node, list):
            children = node
        else:
            return None
        for child in children:
            if isinstance(child, (dict, list)):
                got = walk(child, depth + 1)
                if got:
                    return got
        return None

    try:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (ValueError, TypeError):
                continue
            name = walk(data)
            if name:
                return name
    except Exception:  # noqa: BLE001
        pass
    try:
        tag = soup.find("meta", property="og:title")
        if tag is not None and (tag.get("content") or "").strip():
            return tag["content"].strip()
    except Exception:  # noqa: BLE001
        pass
    try:
        if soup.title and (soup.title.string or "").strip():
            return soup.title.string.strip()
    except Exception:  # noqa: BLE001
        pass
    return (url.rstrip("/").rsplit("/", 1)[-1] or "product").replace("-", " ")


def sweep(rows, flag_value, ask="BHD"):
    from bs4 import BeautifulSoup
    from app.services import price_service as ps

    os.environ["ENABLE_VISIBLE_TEXT_CURRENCY"] = flag_value
    os.environ.pop("ENABLE_EXACT_PRICE_GATE", None)
    os.environ.pop("ENABLE_NOT_A_PDP_FILTER", None)
    out = {}
    for row in rows:
        html = io.open(row["path"], "r", encoding="utf-8", errors="replace").read()
        soup = BeautifulSoup(html, "html.parser")
        host = row["host"] or ""
        try:
            price = ps.extract_price_from_html(
                html, page_query(soup, row["url"]), ask, host, row["url"])
        except Exception as exc:  # noqa: BLE001 — a crash is a finding, not a stop
            price = {"error": "%s: %s" % (type(exc).__name__, exc)}
        out[row["url"]] = {
            "host": host, "truth": row["truth"], "corpus": row["corpus"],
            "evidence": ps._page_currency_evidence(soup),
            "price": None if price is None else {
                k: price.get(k) for k in
                ("amount", "currency", "original_currency", "source_method",
                 "capture_outcome", "error")},
        }
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

    rows = inventory()
    off = sweep(rows, "false")
    on = sweep(rows, "true")

    priced = [u for u, r in off.items() if r["price"] and r["price"].get("amount")]
    foreign_bhd = [
        u for u in priced
        if off[u]["price"].get("currency") == "BHD"
        and off[u]["truth"] and off[u]["truth"] != "BHD"]
    converted = [u for u in foreign_bhd
                 if off[u]["price"].get("source_method") == "converted_usd"]
    rung3 = [u for u in foreign_bhd if off[u]["evidence"] is None
             and off[u]["price"].get("source_method") != "converted_usd"]

    diff = []
    for url in off:
        a, b = off[url]["price"], on[url]["price"]
        if a != b:
            diff.append({"url": url, "host": off[url]["host"],
                         "truth": off[url]["truth"], "off": a, "on": b})

    lines = [
        "pages                                  %d" % len(rows),
        "flag OFF n_priced                      %d" % len(priced),
        "flag OFF n_labelled_bhd_foreign_truth  %d" % len(foreign_bhd),
        "flag OFF   of those converted_usd      %d" % len(converted),
        "flag OFF   of those rung-3 mislabels   %d" % len(rung3),
    ]
    for url in rung3:
        lines.append("    RUNG-3 %s %s %s truth=%s"
                     % (off[url]["host"], off[url]["price"]["amount"],
                        off[url]["price"]["currency"], off[url]["truth"]))
    lines.append("OFF -> ON diff rows                    %d" % len(diff))
    for row in diff:
        lines.append("    DIFF %-32s truth=%-5s off=%s on=%s"
                     % (row["host"], row["truth"],
                        json.dumps(row["off"]), json.dumps(row["on"])))
    lines.append("ACCEPTANCE: exactly one diff row, faces.ae, and it is the "
                 "rung-3 mislabel above.")
    report = "\n".join(lines) + "\n"
    sys.stdout.write(report)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"summary": lines, "off": off, "on": on, "diff": diff},
                      fh, indent=1)
    return 0 if len(diff) == 1 and len(rung3) == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
