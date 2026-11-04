"""D11 PDP-DISCOVERY: the robots-declared sitemaps (and, behind a sub-flag, the
Common Crawl CDX index) of the registry's JSON-LD fragrance hosts -> queued
kb_gaps discovery hints for RANKED juices only.

ENABLE_PDP_DISCOVERY (read per call, the FIRST statement of ``main``):
unset / false / garbage -> OFF (one INFO line, exit 0, nothing read);
true / 1 / yes / on -> DRY RUN (reads robots.txt and the declared sitemaps under
the named agent, counts per host, writes nothing); apply -> one queued kb_gaps
row per (juice, host) match (field ``pdp_<sha256(host)[:16]>``, demand_count 0,
the canonical PDP URL as the hint; a re-discovery updates last_seen only).
ENABLE_CC_CDX (house boolean) + a valid KB_CC_INDEX: the CDX leg, inert
otherwise; it follows the parent's mode.

No Redis write: the sitemap channel's own collector is driven with this run's
named-agent fetch and a robots cache pre-seeded from the body read here.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlsplit

from scripts import kb_seed_common as common

logger = logging.getLogger("cron_pdp_discovery")

FLAG = "ENABLE_PDP_DISCOVERY"
CDX_FLAG = "ENABLE_CC_CDX"
PREFIX = "[PDP_DISCOVERY]"
CC_INDEX_RE = re.compile(r"^CC-MAIN-[0-9]{4}-[0-9]{2}$")
CDX_HOST = "https://index.commoncrawl.org/"
CDX_PAGES = 3
MAX_DECLARED = 5
OFFER_PAGE = 1000
PRODUCT_CHUNK = 100
HINT_MAX = 256
REPORT_URLS = 50


def pdp_discovery_mode() -> str:
    return common.run_mode(FLAG)


def cc_cdx_enabled() -> bool:
    return common.house_flag(CDX_FLAG)


def cc_index() -> Optional[str]:
    """KB_CC_INDEX when it names a crawl (CC-MAIN-YYYY-WW), else None."""
    raw = os.getenv("KB_CC_INDEX")
    if not isinstance(raw, str) or not CC_INDEX_RE.match(raw.strip()):
        return None
    return raw.strip()


def cdx_active() -> bool:
    return cc_cdx_enabled() and cc_index() is not None


def max_hosts() -> int:
    return common.int_knob("PDP_DISCOVERY_MAX_HOSTS", 100, 1, 500)


def max_juices() -> int:
    return common.int_knob("PDP_DISCOVERY_MAX_JUICES", 2000, 1, 20000)


def max_children() -> int:
    return common.int_knob("PDP_DISCOVERY_MAX_CHILDREN", 32, 1, 200)


def _fragrance_entry(entry: Dict[str, Any]) -> bool:
    cats = entry.get("categories")
    return not cats or (isinstance(cats, list) and "fragrances" in cats)


def _jsonld_entry(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The row's first catalog entry with NO platform mechanism (a JSON-LD
    host), not render-only, carrying fragrances; None otherwise."""
    for e in common.registry_entries(row):
        if (e.get("origin") == "catalog" and (e.get("mechanism") or "") == ""
                and not e.get("is_render_only") and _fragrance_entry(e)):
            return e
    return None


def select_hosts(rows: List[Any]) -> List[Dict[str, Any]]:
    """Live undenied rows with a JSON-LD fragrance entry, in run order: tier
    bahrain first, then priority_rank, then host."""
    from app.services import deny_hosts as dh

    picked = []
    for row in rows or []:
        if not isinstance(row, dict) or row.get("status") != "live" or row.get("deny"):
            continue
        host = row.get("host")
        if not isinstance(host, str) or dh.is_denied_host(host):
            continue
        entry = _jsonld_entry(row)
        if entry is None:
            continue
        rank = entry.get("priority_rank") if isinstance(entry.get("priority_rank"), int) else 100
        picked.append(((0 if entry.get("tier") == "bahrain" else 1, rank, host), row))
    picked.sort(key=lambda t: t[0])
    return [row for _, row in picked]


def gap_field(host: str) -> str:
    return "pdp_" + hashlib.sha256(host.encode("utf-8")).hexdigest()[:16]


def ranked_juices(client: Any) -> List[Tuple[str, str, str]]:
    """[(product id, brand, name)] of the juices with at least one offer, by
    distinct merchant count (desc), then id; at most PDP_DISCOVERY_MAX_JUICES."""
    merchants: Dict[str, set] = {}
    start = 0
    for _ in range(common.MAX_PAGES):
        resp = (client.table(common.KB_OFFERS_TABLE).select("variant_id,merchant_id").order("id")
                .range(start, start + OFFER_PAGE - 1).execute())
        data = getattr(resp, "data", None)
        if not isinstance(data, list):
            raise TypeError("kb_offers page is not a list")
        for r in data:
            if isinstance(r, dict) and isinstance(r.get("variant_id"), str) and r.get("merchant_id"):
                pid = r["variant_id"].rsplit("|", 1)[0]
                merchants.setdefault(pid, set()).add(r["merchant_id"])
        if len(data) < OFFER_PAGE:
            break
        start += OFFER_PAGE
    order = sorted(merchants, key=lambda p: (-len(merchants[p]), p))[:max_juices()]
    names: Dict[str, Tuple[str, str]] = {}
    for i in range(0, len(order), PRODUCT_CHUNK):
        chunk = order[i:i + PRODUCT_CHUNK]
        resp = client.table(common.KB_PRODUCTS_TABLE).select("id,brand,name").in_("id", chunk).execute()
        for r in getattr(resp, "data", None) or []:
            if isinstance(r, dict):
                names[r.get("id")] = (r.get("brand") or "", r.get("name") or "")
    return [(pid, names[pid][0], names[pid][1]) for pid in order if pid in names]


def _refuse_all(url: str) -> Any:
    """The collector's robots fetch: never used (the cache is pre-seeded), and
    refusing keeps a cache miss from fetching robots.txt a second time."""
    raise RuntimeError("robots fetch refused")


class HostRun:
    def __init__(self, row: Dict[str, Any]) -> None:
        self.row = row
        self.host = row.get("host")
        self.reason = "ok"
        self.sitemaps = 0
        self.fetched = 0
        self.pdp_urls = 0
        self.cdx_urls = 0
        self.matched = 0
        self.slugs: Dict[str, str] = {}


async def _cdx(run: HostRun, fetcher: Any, index: str, state: Dict[str, Any]) -> None:
    """At most CDX_PAGES pages of the host's captured HTML 200s. A non-2xx, a
    refused hop or an unreadable body stops the CDX leg for the whole run."""
    from app.services import sitemap_discovery_service as sds

    bare = sds._bare_host(run.host)
    for page in range(CDX_PAGES):
        if state.get("cdx_stopped"):
            return
        url = (CDX_HOST + index + "-index?url=" + quote(run.host + "/*", safe="") +
               "&output=json&fl=url,status,mime&filter=status:200&filter=mime:text/html&page=%d" % page)
        res = await fetcher.get(url, gate=False, timeout=30.0)
        if res.refused or not common.ok_status(res.status):
            state["cdx_stopped"] = True
            return
        lines = [ln for ln in (res.body or "").splitlines() if ln.strip()]
        if not lines:
            return
        try:
            for ln in lines:
                u = json.loads(ln).get("url")
                if isinstance(u, str) and sds._same_site(u, bare) and sds._is_pdp_url(u):
                    slug = sds._slug_from_pdp(u)
                    if slug:
                        run.slugs[slug] = u
                        run.cdx_urls += 1
        except Exception:  # noqa: BLE001 - a malformed body stops the leg for the run
            state["cdx_stopped"] = True
            return


async def discover_host(run: HostRun, fetcher: Any, now: Any, state: Dict[str, Any]) -> None:
    """The host's origin gate, its robots.txt, then at most MAX_DECLARED
    same-site, robots-allowed declared sitemaps through the channel's collector."""
    from app.services import robots_eval as re_
    from app.services import sitemap_discovery_service as sds

    robots = run.row.get("robots")
    origin = robots.get("origin") if isinstance(robots, dict) else None
    if not isinstance(origin, str) or not origin:
        run.reason = "no_record"
        return
    reason = common.url_gate(run.row, origin + "/", now)
    if reason is not None:
        run.reason = reason
        return
    res = await fetcher.get(origin + "/robots.txt", run.row, now, gate=False, timeout=20.0)
    if res.refused is None and common.ok_status(res.status):
        body: Optional[str] = res.body
    elif res.refused is None and res.status in (404, 410):
        run.reason = "no_sitemap"
        body = None
    else:
        run.reason = "robots_unreadable"
        return
    if body is not None:
        bare = sds._bare_host(origin)
        kept = [u for u in re_.sitemaps(body)
                if sds._same_site(u, bare) and common.url_gate(run.row, u, now) is None][:MAX_DECLARED]
        run.sitemaps = len(kept)
        netloc = (urlsplit(origin).netloc or "").lower()

        async def _fetch(url: str) -> Optional[str]:
            got = await fetcher.get(url, run.row, now, timeout=20.0)
            run.fetched += 1
            if got.gate is None and got.refused is None and common.ok_status(got.status):
                return got.body
            return None

        for index_url in kept:
            found = await sds._collect_slugs_for_index(run.host, index_url, fetch=_fetch,
                                                       max_children=max_children(), robots_fetch=_refuse_all,
                                                       robots_cache={netloc: body})
            run.slugs.update(found)
        run.pdp_urls = len(run.slugs)
    if cdx_active():
        await _cdx(run, fetcher, cc_index(), state)


def match_host(run: HostRun, juices: List[Tuple[str, str, str]]) -> List[Tuple[str, str]]:
    """[(product id, PDP url)] through the sitemap service's own token buckets
    and its fail-closed slug matcher (None, never a wrong URL)."""
    from app.services import price_service as ps
    from app.services import sitemap_discovery_service as sds

    buckets: Dict[str, Dict[str, str]] = {}
    for slug, url in run.slugs.items():
        for token in ps.normalize_words(slug):
            key = sds._sanitize_token_key(token)
            if not key:
                continue
            bucket = buckets.setdefault(key, {})
            if len(bucket) < sds._BUCKET_CAP:
                bucket[slug] = url
    out = []
    for pid, brand, name in juices:
        query = (brand + " " + name).strip()
        for key in sds._ordered_probe_tokens(query)[:sds._MAX_BUCKET_PROBES]:
            bucket = buckets.get(key)
            if not bucket:
                continue
            url = sds._match_sitemap_slug(dict(bucket), query)
            if url:
                out.append((pid, url))
                break
    return out


def gap_rows(run: HostRun, matches: List[Tuple[str, str]], observed: Any) -> Tuple[List[Dict[str, Any]], int]:
    """The builder's kb_gaps rows for the matches, and the refused-hint count."""
    kb = common.kb_leaf()
    rows: List[Dict[str, Any]] = []
    refused = 0
    for pid, url in matches:
        hint = kb.canonical_offer_url(url)
        row = None
        if hint is not None and len(hint) <= HINT_MAX:
            row = kb.build_gap_row(product_key=pid, field=gap_field(run.host), first_seen=observed,
                                   last_seen=observed, demand_count=0, state="queued", source_hint=hint)
        if row is None:
            refused += 1
            continue
        rows.append(row)
    return rows, refused


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="cron_pdp_discovery")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--report", default=None)
    return p.parse_args(argv if argv is not None else [])


async def _run(args: argparse.Namespace, mode: str, client: Any) -> int:
    try:
        rows = common.read_merchant_rows(client)
        juices = ranked_juices(client)
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s KB read failed (%s)", PREFIX, type(exc).__name__)
        return 0
    observed = common._now()
    fetcher = common.PoliteFetcher()
    writer = common.KbWriter(client)
    state: Dict[str, Any] = {}
    report: Dict[str, Any] = {"hosts": []}
    totals: Dict[str, int] = {}
    for row in select_hosts(rows)[:max_hosts()]:
        run = HostRun(row)
        try:
            await discover_host(run, fetcher, observed, state)
        except Exception as exc:  # noqa: BLE001 - one host never ends the run
            run.reason = "error_" + type(exc).__name__
        gaps, hint_refused = gap_rows(run, match_host(run, juices), observed)
        run.matched = len(gaps)
        if mode == common.MODE_APPLY and gaps:
            try:
                writer.gaps(gaps)
            except Exception as exc:  # noqa: BLE001
                logger.warning("%s host=%s write failed (%s)", PREFIX, run.host, type(exc).__name__)
        logger.info("%s host=%s reason=%s sitemaps=%d fetched=%d pdp_urls=%d cdx_urls=%d matched=%d", PREFIX,
                    run.host, run.reason, run.sitemaps, run.fetched, run.pdp_urls, run.cdx_urls, run.matched)
        common.bump(totals, run.reason)
        report["hosts"].append({"host": run.host, "reason": run.reason, "sitemaps": run.sitemaps,
                                "fetched": run.fetched, "pdp_urls": run.pdp_urls, "cdx_urls": run.cdx_urls,
                                "matched": run.matched, "hint_refused": hint_refused,
                                "urls": sorted(run.slugs.values())[:REPORT_URLS],
                                "gaps": [[g["product_key"], g["source_hint"]] for g in gaps]})
    totals["ranked_juices"] = len(juices)
    if state.get("cdx_stopped"):
        totals["cdx_stopped"] = 1
    common.log_counts(PREFIX, totals)
    common.write_report(args.report, report)
    return 0


def main(argv: Optional[List[str]] = None, client: Any = None) -> int:
    mode = pdp_discovery_mode()
    if mode == common.MODE_OFF:
        logger.info("%s mode=off ENABLE_PDP_DISCOVERY not set; skipping run", PREFIX)
        return 0
    args = _parse_args(argv)
    mode = common.cli_mode(mode, args.dry_run)
    logger.info("%s mode=%s cdx=%d", PREFIX, mode, int(cdx_active()))
    client = common.resolve_client(client, PREFIX)
    if client is None:
        return 0
    return asyncio.run(_run(args, mode, client))


run = main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main(sys.argv[1:]))
