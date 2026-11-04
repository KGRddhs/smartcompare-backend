"""S81-16 brand hosts and S81-16b brand rows from Wikidata, under ENABLE_KB_BRANDS.

The script has its OWN flag since S81-16b: ENABLE_KB_BRANDS, read per call as
the FIRST statement of ``main`` (unset / blank / false / 0 / no / off / dry ->
OFF; true / 1 / yes / on -> DRY; the exact word apply -> WRITE; --dry-run
downgrades APPLY to DRY) and the knob KB_BRANDS_MAX (300, clamped 1..5000).
ENABLE_KB_SEED never runs this script. In DRY and APPLY alike it reads the
query service's robots.txt once, then makes ONE SPARQL GET (both through the
polite named-agent fetcher, SSRF-checked on every hop), derives the new
official-site hosts and the brand rows (en, else mul, and ar labels; human
items excluded) and writes both, with the counts, to --report. Only APPLY
writes, and only public.kb_brands (migration 052) through KbWriter.brands:
insert-ignore on qid, then one update of the label and host columns of each
'wikidata' row the insert did not return. It never writes kb_merchants and
never deletes. Wikidata structured data is CC0.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlsplit

from scripts import kb_seed_common as common

logger = logging.getLogger("seed_kb_brands_wikidata")

FLAG = "ENABLE_KB_BRANDS"
MAX_KNOB = "KB_BRANDS_MAX"
PREFIX = "[KB_BRANDS]"
ROBOTS_URL = "https://query.wikidata.org/robots.txt"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
SPARQL_LIMIT = 2000
# P1056 product or material produced = Q131746 perfume; P856 official website;
# P31 Q5 = instance of human (excluded: no person's name is imported). The ids
# are offline-unverified: the dry-run counts are the check (S16 L7). Labels are
# exact-language OPTIONALs (an unbound label is None, never the bare item id):
# en, else mul (the default-language label), and ar. Ordered by the NUMERIC
# qid so a truncation at the LIMIT is deterministic and agrees with the cap.
SPARQL = ("SELECT DISTINCT ?brand ?site ?label_en ?label_mul ?label_ar WHERE { "
          "?brand wdt:P1056 wd:Q131746 . ?brand wdt:P856 ?site . "
          "FILTER NOT EXISTS { ?brand wdt:P31 wd:Q5 . } "
          'OPTIONAL { ?brand rdfs:label ?label_en . FILTER(LANG(?label_en) = "en") } '
          'OPTIONAL { ?brand rdfs:label ?label_mul . FILTER(LANG(?label_mul) = "mul") } '
          'OPTIONAL { ?brand rdfs:label ?label_ar . FILTER(LANG(?label_ar) = "ar") } '
          '} ORDER BY xsd:integer(STRAFTER(STR(?brand), "/entity/Q")) ?site LIMIT %d' % SPARQL_LIMIT)
MAX_BRAND_HOSTS = 300
#: The report fields of one brand row (the report never carries source / updated_at).
REPORT_BRAND_KEYS = ("qid", "label_en", "label_ar", "official_host")


def sparql_url() -> str:
    return SPARQL_ENDPOINT + "?format=json&query=" + quote(SPARQL, safe="")


def brands_max() -> int:
    """KB_BRANDS_MAX, read per call: 300 by default, clamped to 1..5000."""
    return common.int_knob(MAX_KNOB, 300, 1, 5000)


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="seed_kb_brands_wikidata")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--report", default=None)
    return p.parse_args(argv if argv is not None else [])


def _site_host(binding: Any) -> Optional[str]:
    site = ((binding or {}).get("site") or {}).get("value") if isinstance(binding, dict) else None
    return site if isinstance(site, str) and site else None


def derive_hosts(bindings: Any, existing: set, counts: Dict[str, int]) -> List[str]:
    """The new official-site hosts, sorted, at most MAX_BRAND_HOSTS: a host the
    S81-14 host rules refuse (an IP literal included), a denied host or one
    already in kb_merchants is excluded and counted."""
    from app.services import deny_hosts as dh

    kb = common.kb_leaf()
    host_re = re.compile(kb.KB_HOST_REGEX)
    top_re = re.compile(kb.KB_HOST_TOP_LABEL_REGEX)
    out: set = set()
    for b in bindings if isinstance(bindings, list) else []:
        common.bump(counts, "bindings")
        site = _site_host(b)
        if site is None:
            continue
        common.bump(counts, "with_site")
        try:
            host = dh.normalize_host(urlsplit(site).hostname or "")
        except ValueError:
            host = ""
        if not host or not host_re.match(host) or not top_re.match(host):
            common.bump(counts, "invalid")
            continue
        if dh.is_denied_host(host):
            common.bump(counts, "denied")
            continue
        if host in existing:
            common.bump(counts, "existing")
            continue
        out.add(host)
    hosts = sorted(out)
    if len(hosts) > MAX_BRAND_HOSTS:
        counts["over_cap"] = len(hosts) - MAX_BRAND_HOSTS
        hosts = hosts[:MAX_BRAND_HOSTS]
    counts["new"] = len(hosts)
    return hosts


def _binding_value(binding: Any, key: str) -> Optional[str]:
    value = ((binding or {}).get(key) or {}).get("value") if isinstance(binding, dict) else None
    return value if isinstance(value, str) else None


def qid_of(binding: Any) -> Optional[str]:
    """The last path segment of the brand IRI (a bare id stays as it is);
    whether it is a valid qid is the builder's call."""
    value = _binding_value(binding, "brand")
    if not value:
        return None
    return value.rsplit("/", 1)[-1] or None


def _label(binding: Any, key: str) -> Optional[str]:
    """A label value stripped; an empty or missing label is None."""
    value = _binding_value(binding, key)
    if value is None:
        return None
    return value.strip() or None


def _brand_host(site: Optional[str]) -> Optional[str]:
    """The official-site host normalised as derive_hosts does; validity is the builder's."""
    from app.services import deny_hosts as dh

    if not site:
        return None
    try:
        host = dh.normalize_host(urlsplit(site).hostname or "")
    except ValueError:
        return None
    return host or None


def derive_brands(bindings: Any, counts: Dict[str, int], now: Any, cap: int) -> List[Dict[str, Any]]:
    """The kb_brands rows of one SPARQL answer, sorted by numeric qid, at most ``cap``.

    Counters (ints, absent at 0 except brand_rows): bad_qid per binding;
    with_label_en / with_label_ar = distinct qids carrying that exact label;
    label_en_from_mul, no_label_en, label_ar_dropped, brand_host_null per qid;
    over_cap_brands; sparql_limit_hit when the answer holds SPARQL_LIMIT rows."""
    kb = common.kb_leaf()
    rows_in = bindings if isinstance(bindings, list) else []
    if len(rows_in) == SPARQL_LIMIT:
        counts["sparql_limit_hit"] = 1
    groups: Dict[str, Dict[str, Any]] = {}
    for b in rows_in:
        qid = qid_of(b)
        if qid is None or not kb._sql_match(kb.KB_QID_REGEX, qid):
            common.bump(counts, "bad_qid")
            continue
        g = groups.setdefault(qid, {"en": None, "mul": None, "ar": None, "sites": []})
        for slot, var in (("en", "label_en"), ("mul", "label_mul"), ("ar", "label_ar")):
            if g[slot] is None:
                g[slot] = _label(b, var)
        site = _site_host(b)
        if site is not None:
            g["sites"].append(site)
    rows: List[Dict[str, Any]] = []
    for qid, g in groups.items():
        if g["en"] is not None:
            common.bump(counts, "with_label_en")
        if g["ar"] is not None:
            common.bump(counts, "with_label_ar")
        # en when present (a refused en label never falls back), else mul
        label_en = g["en"] if g["en"] is not None else g["mul"]
        if label_en is None or kb.build_brand_row(qid=qid, label_en=label_en, updated_at=now) is None:
            common.bump(counts, "no_label_en")
            continue
        if g["en"] is None:
            common.bump(counts, "label_en_from_mul")
        label_ar = g["ar"]
        if label_ar is not None and kb.build_brand_row(
                qid=qid, label_en=label_en, label_ar=label_ar, updated_at=now) is None:
            common.bump(counts, "label_ar_dropped")
            label_ar = None
        host = None
        for candidate in sorted({h for h in (_brand_host(s) for s in g["sites"]) if h}):
            if kb.build_brand_row(qid=qid, label_en=label_en, official_host=candidate,
                                  updated_at=now) is not None:
                host = candidate
                break
        if host is None:
            common.bump(counts, "brand_host_null")
        row = kb.build_brand_row(qid=qid, label_en=label_en, label_ar=label_ar,
                                 official_host=host, source="wikidata", updated_at=now)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda r: int(r["qid"][1:]))
    if len(rows) > cap:
        counts["over_cap_brands"] = len(rows) - cap
        rows = rows[:cap]
    counts["brand_rows"] = len(rows)
    return rows


def _write_brands(client: Any, rows: List[Dict[str, Any]], counts: Dict[str, int]) -> None:
    """APPLY only: KbWriter.brands; a failure is ONE WARNING with the type name
    (an owner precondition such as 052 not applied); the writer's own counters
    are ADDED to the counts in a finally, so batches already sent are reported."""
    writer = common.KbWriter(client)
    try:
        writer.brands(rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s kb_brands write failed (%s)", PREFIX, type(exc).__name__)
        counts["write_failed"] = 1
    finally:
        for key, value in sorted(writer.counts.items()):
            common.bump(counts, key, int(value))


async def _run(args: argparse.Namespace, client: Any, mode: str = common.MODE_DRY) -> int:
    from app.services import robots_eval as re_

    try:
        rows = common.read_merchant_rows(client)
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s kb_merchants read failed (%s)", PREFIX, type(exc).__name__)
        return 0
    existing = set(common.rows_by_host(rows))
    fetcher = common.PoliteFetcher()
    robots = await fetcher.get(ROBOTS_URL, gate=False, timeout=20.0)
    if common.ok_status(robots.status):
        body = robots.body
    elif robots.status in (404, 410):
        body = ""
    else:
        logger.info("%s robots unreadable; nothing read", PREFIX)
        return 0
    url = sparql_url()
    if not (re_.can_fetch(body, re_.QARENBOT_UA, url) and re_.can_fetch(body, "*", url)):
        logger.info("%s robots disallow the query endpoint; nothing read", PREFIX)
        return 0
    res = await fetcher.get(url, gate=False, timeout=60.0)
    if not common.ok_status(res.status):
        logger.info("%s query failed status=%d", PREFIX, int(res.status or 0))
        return 0
    try:
        bindings = json.loads(res.body)["results"]["bindings"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s query body unreadable (%s)", PREFIX, type(exc).__name__)
        return 0
    counts: Dict[str, int] = {}
    hosts = derive_hosts(bindings, existing, counts)
    brand_rows = derive_brands(bindings, counts, common._now(), brands_max())
    if mode == common.MODE_APPLY:
        _write_brands(client, brand_rows, counts)
    report_rows = [{k: r[k] for k in REPORT_BRAND_KEYS} for r in brand_rows]
    common.write_report(args.report, {"hosts": hosts, "brands": report_rows, "counts": counts})
    common.log_counts(PREFIX, counts)
    return 0


def main(argv: Optional[List[str]] = None, client: Any = None) -> int:
    mode = common.run_mode(FLAG)
    if mode == common.MODE_OFF:
        logger.info("%s mode=off ENABLE_KB_BRANDS not set; skipping run (ENABLE_KB_SEED does not run this script)",
                    PREFIX)
        return 0
    args = _parse_args(argv)
    mode = common.cli_mode(mode, args.dry_run)
    logger.info("%s mode=%s (apply writes kb_brands; dry writes nothing)", PREFIX, mode)
    client = common.resolve_client(client, PREFIX)
    if client is None:
        return 0
    return asyncio.run(_run(args, client, mode))


run = main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main(sys.argv[1:]))
