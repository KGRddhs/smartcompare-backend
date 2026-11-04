"""S81-16 brand hosts from Wikidata: DRY-ONLY by ruling R-G2-3.

The same flag and mode as seed_kb_batch (ENABLE_KB_SEED, read per call, the
FIRST statement of ``main``). In DRY and APPLY alike it reads the query
service's robots.txt once, then makes ONE SPARQL GET (both through the polite
named-agent fetcher, SSRF-checked on every hop), derives the official-site
hosts and writes the host list to --report only. It writes NOTHING to the KB in
any mode: a brands table needs its own migration (S81-16b), so APPLY behaves as
DRY and its mode line says so.
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

FLAG = "ENABLE_KB_SEED"
PREFIX = "[KB_BRANDS]"
ROBOTS_URL = "https://query.wikidata.org/robots.txt"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
# P1056 product or material produced = Q131746 perfume; P856 official website
# (offline-unverified ids: the dry-run binding count is the check, S16 L7).
SPARQL = ("SELECT DISTINCT ?brand ?site WHERE { ?brand wdt:P1056 wd:Q131746 . "
          "?brand wdt:P856 ?site . } LIMIT 2000")
MAX_BRAND_HOSTS = 300


def sparql_url() -> str:
    return SPARQL_ENDPOINT + "?format=json&query=" + quote(SPARQL, safe="")


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


async def _run(args: argparse.Namespace, client: Any) -> int:
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
    common.write_report(args.report, {"hosts": hosts, "counts": counts})
    common.log_counts(PREFIX, counts)
    return 0


def main(argv: Optional[List[str]] = None, client: Any = None) -> int:
    mode = common.run_mode(FLAG)
    if mode == common.MODE_OFF:
        logger.info("%s mode=off ENABLE_KB_SEED not set; skipping run", PREFIX)
        return 0
    args = _parse_args(argv)
    mode = common.cli_mode(mode, args.dry_run)
    logger.info("%s mode=%s (writes nothing in any mode; apply behaves as dry)", PREFIX, mode)
    client = common.resolve_client(client, PREFIX)
    if client is None:
        return 0
    return asyncio.run(_run(args, client))


run = main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main(sys.argv[1:]))
