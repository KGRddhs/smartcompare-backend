"""M10 UNIT A2 — the corpus before/after gate for ENABLE_WALL_SIGNATURE_ANCHOR.

Runs ``classify_capture(html, None, http_status)`` over every cached page in the
two read-only corpora, once with the anchor flag OFF and once with it ON, and
diffs the WALLED sets. No other flag is read on this path, so nothing else needs
pinning.

ACCEPTANCE, and the run on 2026-08-31 met it exactly:

  * 414 cached pages, of which 37 are named WALLED by HTTP STATUS alone.
  * flag OFF: walled = 44  (37 status-driven + 7 signature-driven).
  * flag ON : walled = 40  (37 status-driven + 3 signature-driven).
  * DROPPED = exactly the four measured FALSE POSITIVES:
        om.swissarabian.com  200  (``access denied`` in a JS comment)
        www.macys.com        404  (``access denied`` in a JS comment)
        www.walmart.com      200  x2 (``perimeterx`` in a CSP host allowlist)
  * ADDED = EMPTY. This is the no-false-negative bar and it is the reason the
    unit is a diff and not an assertion.
  * The three signature-driven walls retained under the flag are exactly
    www.boots.com (``_Incapsula_``), www.sallybeauty.com (``px-captcha``) and
    www.dillards.com (anchored ``<TITLE>Access Denied</TITLE>``).

Any other movement, in either direction, blocks the commit.

ZERO NETWORK. The corpora under ``_proof/`` are read-only and git-excluded, so
this is a reproduction harness, not a test: nothing under ``tests/`` may depend
on a corpus path. ``--corpus-root`` lets a pristine base worktree (which has no
``_proof/`` of its own) read the corpora from the main checkout.

    python scripts/measure_wall_anchoring.py [--out <path>] [--corpus-root <repo>]
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

#: The four pages the unit exists to stop mislabelling.
EXPECTED_DROPPED = {
    ("om.swissarabian.com",
     "https://om.swissarabian.com/products/musk-07-edp-body-lotion-gift-set"),
    ("www.macys.com",
     "https://www.macys.com/shop/product/dior-sauvage-eau-de-toilette-spray?ID=1147845"),
    ("www.walmart.com",
     "https://www.walmart.com/ip/Ysl-Mon-Paris-3-Oz-Edp-Sp-For-Women/137848167"),
    ("www.walmart.com",
     "https://www.walmart.com/ip/Versace-Bright-Crystal-Absolu-Eau-De-Parfum-for-Women-3-oz/47002984"),
}

#: The signature-driven walls that MUST survive the narrowing.
EXPECTED_TRUE_WALLS = {"www.boots.com", "www.sallybeauty.com", "www.dillards.com"}


def inventory():
    """Every cached page with its recorded HTTP status. 92 Gulf + 322 global."""
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
            digest = hashlib.sha1(("curl_cffi|" + url).encode("utf-8")).hexdigest()
            path = os.path.join(gulf_html, digest + ".html")
            if os.path.exists(path):
                rows.append({"corpus": "gulf", "url": url, "path": path,
                             "host": rec.get("domain"),
                             "status": rec.get("status"),
                             "blocked": rec.get("structurally_blocked")})
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
                rows.append({"corpus": "global", "url": url, "path": path,
                             "host": rec.get("host") or rec.get("domain"),
                             "status": rec.get("http_status"),
                             "blocked": rec.get("blocked")})
                break
    return rows


def sweep(rows, flag_value):
    from app.services import price_service as ps

    os.environ["ENABLE_WALL_SIGNATURE_ANCHOR"] = flag_value
    out = []
    for index, row in enumerate(rows):
        html = io.open(row["path"], "r", encoding="utf-8", errors="replace").read()
        status = row["status"]
        status_wall = (isinstance(status, int) and not isinstance(status, bool)
                       and status in ps._WALL_HTTP_STATUS)
        out.append({
            "i": index, "host": row["host"], "url": row["url"],
            "status": status, "bytes": len(html), "blocked": row["blocked"],
            "outcome": ps.classify_capture(html, None, status),
            "status_wall": status_wall,
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

    rows = inventory()
    off = sweep(rows, "false")
    on = sweep(rows, "true")

    def walled(records):
        return {r["i"] for r in records if r["outcome"] == "walled"}

    off_walled, on_walled = walled(off), walled(on)
    dropped = sorted(off_walled - on_walled)
    added = sorted(on_walled - off_walled)
    status_walls = sum(1 for r in off if r["status_wall"])
    sig_on = [r for r in on if r["outcome"] == "walled" and not r["status_wall"]]

    lines = [
        "pages                                  %d" % len(rows),
        "status-driven walls (both modes)       %d" % status_walls,
        "flag OFF walled                        %d" % len(off_walled),
        "flag ON  walled                        %d" % len(on_walled),
        "DROPPED (OFF walled, ON not)           %d" % len(dropped),
    ]
    for i in dropped:
        lines.append("    DROPPED %-24s status=%-5s -> %s"
                     % (off[i]["host"], off[i]["status"], on[i]["outcome"]))
    lines.append("ADDED   (ON walled, OFF not)           %d" % len(added))
    for i in added:
        lines.append("    ADDED   %-24s status=%-5s (was %s)"
                     % (on[i]["host"], on[i]["status"], off[i]["outcome"]))
    lines.append("signature-driven walls retained ON     %d" % len(sig_on))
    for r in sig_on:
        lines.append("    KEPT    %-24s status=%-5s bytes=%d"
                     % (r["host"], r["status"], r["bytes"]))

    got_dropped = {(off[i]["host"], off[i]["url"]) for i in dropped}
    got_kept = {r["host"] for r in sig_on}
    ok = (not added
          and got_dropped == EXPECTED_DROPPED
          and got_kept == EXPECTED_TRUE_WALLS)
    lines.append("ACCEPTANCE: ADDED empty, DROPPED is exactly the four measured "
                 "false positives, and the retained signature walls are exactly "
                 "boots/sallybeauty/dillards -> %s" % ("PASS" if ok else "FAIL"))

    report = "\n".join(lines) + "\n"
    sys.stdout.write(report)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"summary": lines, "off": off, "on": on,
                       "dropped": dropped, "added": added}, fh, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
