"""D09 FEED-WALKER: the catalogue feeds of the registry's fragrance feed hosts.

ENABLE_FEED_WALKER (read per call, the FIRST statement of ``main``):
unset / false / garbage -> OFF (one INFO line, exit 0, nothing read);
true / 1 / yes / on -> DRY RUN (fetches under the named agent, counts per host,
writes nothing); apply -> kb_products / kb_variants (insert-ignore) and
kb_offers (one observation per feed page; a re-observation updates the
KB_OFFER_UPSERT_SET columns only).

Readers: Shopify ``/products.json`` and the WooCommerce Store API; every other
feed mechanism is reported ``no_reader`` (D09b). Every URL is built on the
persisted robots record's origin and passes the per-URL gate (ToS required)
before and on every hop. Shopify feeds are currency-blind: the row's registry
currency labels them with the rung ``expected_missing``, and a per-handle probe
of ``/products/<handle>.json`` that disagrees skips the host with no row.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from scripts import kb_seed_common as common

logger = logging.getLogger("cron_feed_walker")

FLAG = "ENABLE_FEED_WALKER"
PREFIX = "[FEED_WALKER]"
FEED_MECHANISMS = ("shopify", "woo_store_json", "magento_graphql", "salla_api", "algolia", "rest_json", "occ_rest")
READERS = ("shopify", "woo_store_json")
SHOPIFY_PAGE = 250
WOO_PAGE = 100
SAMPLE_PER_HOST = 5
RANK_TOP = 500
FEED_TIMEOUT = 20.0
ML_MIN, ML_MAX = 1, 5000
SKU_MAX = 128


def feed_walker_mode() -> str:
    return common.run_mode(FLAG)


def max_pages() -> int:
    return common.int_knob("FEED_WALKER_MAX_PAGES", 40, 1, 200)


def currency_probes() -> int:
    return common.int_knob("FEED_WALKER_CURRENCY_PROBES", 3, 0, 10)


def _fragrance_entry(entry: Dict[str, Any]) -> bool:
    cats = entry.get("categories")
    return not cats or (isinstance(cats, list) and "fragrances" in cats)


def _feed_entry(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for e in common.registry_entries(row):
        if e.get("mechanism") in FEED_MECHANISMS and _fragrance_entry(e):
            return e
    return None


def select_hosts(rows: List[Any]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """The live, undenied rows with a fragrance feed entry, in walk order (tier
    bahrain first, then priority_rank, then host)."""
    from app.services import deny_hosts as dh

    picked = []
    for row in rows or []:
        if not isinstance(row, dict) or row.get("status") != "live" or row.get("deny"):
            continue
        host = row.get("host")
        if not isinstance(host, str) or dh.is_denied_host(host):
            continue
        entry = _feed_entry(row)
        if entry is None:
            continue
        rank = entry.get("priority_rank") if isinstance(entry.get("priority_rank"), int) else 100
        picked.append(((0 if entry.get("tier") == "bahrain" else 1, rank, host), row, entry))
    picked.sort(key=lambda t: t[0])
    return [(row, entry) for _, row, entry in picked]


def _json(body: str) -> Any:
    try:
        return json.loads(body)
    except Exception:  # noqa: BLE001 - an unreadable body is a bad feed
        return None


def _end_reason(res: Any) -> Optional[str]:
    """None for a usable 2xx, else the reason that ends the host's walk."""
    from app.services import robots_registry as rr

    if res.gate is not None:
        return res.gate
    if res.refused is not None:
        return "ssrf" if res.refused in ("initial", "hop") else str(res.refused)
    if res.status in (429, 503):
        return "throttled"
    if res.status is not None and rr._challenge(res.status, res.headers, res.body):
        return "challenge"
    if not common.ok_status(res.status):
        return "bad_feed"
    return None


def _ml(value: Any) -> Optional[int]:
    return value if isinstance(value, int) and ML_MIN <= value <= ML_MAX else None


def _conc(pid: str) -> Optional[str]:
    conc = pid.split("|")[3]
    return None if conc == "-" else conc


class HostWalk:
    def __init__(self, row: Dict[str, Any], entry: Dict[str, Any]) -> None:
        self.row = row
        self.entry = entry
        self.host = row["host"]
        self.reason = "ok"
        self.pages = 0
        self.products = 0
        self.kept = 0
        self.counts: Dict[str, int] = {}
        self.product_rows: Dict[str, Dict[str, Any]] = {}
        self.variant_rows: Dict[str, Dict[str, Any]] = {}
        self.offer_rows: List[Dict[str, Any]] = []
        self.samples: List[Dict[str, Any]] = []
        self.pids: set = set()
        self.notes: List[str] = []

    def bump(self, key: str) -> None:
        common.bump(self.counts, key)

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)

    def drop_rows(self) -> None:
        self.product_rows.clear()
        self.variant_rows.clear()
        self.offer_rows.clear()

    def sample(self, title: str, brand: Any) -> None:
        if len(self.samples) < SAMPLE_PER_HOST:
            self.samples.append({"title": title, "brand": brand})


def _guards(walk: HostWalk, title: str, surface: str) -> bool:
    """A fragrance signal on the surface, then no counterfeit, no accessory."""
    from app.services import price_service as ps
    from scripts import seed_spec_spine as ssp

    if not ssp._has_fragrance_signal(surface):
        walk.bump("non_fragrance")
        return False
    if ps.is_counterfeit_listing(title):
        walk.bump("counterfeit")
        return False
    if ps.is_accessory_for_category(title, "fragrances"):
        walk.bump("accessory")
        return False
    return True


def _product(walk: HostWalk, brand: Any, title: str, gtins: List[Optional[str]], observed: Any) -> Optional[str]:
    """The juice id through the S81-14 identity helper; never a guessed brand."""
    kb = common.kb_leaf()
    if not isinstance(brand, str) or not brand.strip():
        walk.bump("no_brand")
        return None
    pid = kb.kb_product_id(brand.strip(), title)
    if pid is None:
        walk.bump("no_identity")
        return None
    row = kb.build_product_row(id=pid, brand=brand.strip(), name=title, concentration=_conc(pid),
                               identity_confidence="high" if any(gtins) else "medium", updated_at=observed)
    if row is None:
        walk.bump("refused_by_builder")
        return None
    walk.product_rows.setdefault(pid, row)
    walk.pids.add(pid)
    return pid


def _variant(walk: HostWalk, pid: str, ml: Any, gtin: Optional[str], sku: Any, observed: Any) -> Optional[str]:
    kb = common.kb_leaf()
    conc = _conc(pid)
    ml = _ml(ml)
    vid = kb.kb_variant_key(pid, conc, ml)
    if vid is None:
        walk.bump("no_variant")
        return None
    sku = sku if isinstance(sku, str) and 1 <= len(sku) <= SKU_MAX else None
    row = kb.build_variant_row(id=vid, product_id=pid, concentration=conc, size_ml=ml, gtin=gtin, sku=sku,
                               updated_at=observed)
    if row is None:
        walk.bump("refused_by_builder")
        return None
    walk.variant_rows.setdefault(vid, row)
    return vid


def _offers(walk: HostWalk, vid: str, ml: Any, amount: Any, list_amount: Any, currency: str, rung: str,
            url: Optional[str], in_stock: Any, observed: Any) -> None:
    """One offer row, or the sale / list pair when a higher list price is known
    (both stamped with the page's ONE observation time)."""
    kb = common.kb_leaf()
    if url is None:
        walk.bump("off_host")
        return
    ml = _ml(ml)
    if (isinstance(list_amount, (int, float)) and isinstance(amount, (int, float))
            and list_amount > amount):
        pairs = [("sale", amount), ("list", list_amount)]
    else:
        pairs = [("unknown", amount)]
    for kind, value in pairs:
        row = kb.build_offer_row(variant_id=vid, merchant_id=walk.host, market=walk.row.get("country"),
                                 amount=value, observed_currency=currency, evidence_rung=rung,
                                 canonical_url=url, captured_at=observed, size_ml=ml, list_vs_sale=kind,
                                 in_stock=in_stock if isinstance(in_stock, bool) else None)
        if row is None:
            walk.bump("refused_by_builder")
            continue
        walk.offer_rows.append(row)


def map_shopify(walk: HostWalk, origin: str, product: Any, currency: str, observed: Any) -> None:
    from app.services import price_service as ps

    kb = common.kb_leaf()
    if not isinstance(product, dict):
        return
    walk.products += 1
    title = product.get("title") if isinstance(product.get("title"), str) else ""
    tags = product.get("tags")
    tags = " ".join(tags) if isinstance(tags, list) else (tags if isinstance(tags, str) else "")
    ptype = product.get("product_type") if isinstance(product.get("product_type"), str) else ""
    if not _guards(walk, title, " ".join((title, ptype, tags))):
        return
    variants = [v for v in (product.get("variants") or []) if isinstance(v, dict)]
    gtins = [str(v.get("barcode")) if kb.gtin_check_digit_ok(str(v.get("barcode") or "")) else None
             for v in variants]
    pid = _product(walk, product.get("vendor"), title, gtins, observed)
    if pid is None:
        return
    walk.kept += 1
    walk.sample(title, product.get("vendor"))
    handle = product.get("handle") if isinstance(product.get("handle"), str) else ""
    url = kb.canonical_offer_url(origin + "/products/" + handle) if handle else None
    for v, gtin in zip(variants, gtins, strict=True):
        vtitle = v.get("title") if isinstance(v.get("title"), str) else ""
        ml = ps.extract_size_ml_any(title + " " + vtitle)
        vid = _variant(walk, pid, ml, gtin, v.get("sku"), observed)
        if vid is None:
            continue
        amount = ps.parse_money(v.get("price"), currency)
        compare = ps.parse_money(v.get("compare_at_price"), currency) if v.get("compare_at_price") else None
        if amount is None:
            walk.bump("no_price")
            continue
        # The feed is currency-blind: the registry currency labels it, never the rung platform_api.
        _offers(walk, vid, ml, amount, compare, currency, "expected_missing", url, v.get("available"), observed)


def _on_host(url: Optional[str], host: str) -> Optional[str]:
    """``url`` when its host is the merchant host or a subdomain of it."""
    if url is None:
        return None
    try:
        h = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return None
    return url if (h == host or h.endswith("." + host)) else None


def _woo_sale_list(prices: Dict[str, Any], amount: Any) -> Tuple[Any, Any]:
    """(amount, list amount): the sale / list pair when the minor-unit sale price
    is below the regular one, else (amount, None)."""
    from app.services import woocommerce_service as ws

    try:
        regular, sale = prices.get("regular_price"), prices.get("sale_price")
        if regular not in (None, "") and sale not in (None, "") and int(str(sale)) < int(str(regular)):
            return (ws._amount_from_prices(dict(prices, price=sale)),
                    ws._amount_from_prices(dict(prices, price=regular)))
    except (TypeError, ValueError):
        pass
    return amount, None


def map_woo(walk: HostWalk, product: Any, row_cur: Optional[str], observed: Any) -> None:
    from app.services import price_service as ps
    from app.services import woocommerce_service as ws

    kb = common.kb_leaf()
    if not isinstance(product, dict):
        return
    walk.products += 1
    name = product.get("name") if isinstance(product.get("name"), str) else ""
    cats = " ".join(c.get("name", "") for c in (product.get("categories") or []) if isinstance(c, dict))
    if not _guards(walk, name, name + " " + cats):
        return
    prices = product.get("prices") if isinstance(product.get("prices"), dict) else {}
    if ws._woo_variable_spread(prices):
        walk.bump("variable_spread")
        return
    code = ps._resolve_iso_currency(prices.get("currency_code"))
    rung = "platform_api"
    if code is None:
        code, rung = row_cur, "expected_missing"
    if code is None:
        walk.bump("currency_unknown")
        return
    brands = product.get("brands")
    brand = (brands[0].get("name")
             if isinstance(brands, list) and brands and isinstance(brands[0], dict) else None)
    pid = _product(walk, brand, name, [], observed)
    if pid is None:
        return
    walk.kept += 1
    walk.sample(name, brand)
    ml = ps.extract_size_ml_any(name)
    vid = _variant(walk, pid, ml, None, product.get("sku"), observed)
    if vid is None:
        return
    # The Store API amounts are minor units (currency_minor_unit): the service's own reader divides.
    amount = ws._amount_from_prices(prices)
    if amount is None:
        walk.bump("no_price")
        return
    amount, list_amount = _woo_sale_list(prices, amount)
    permalink = product.get("permalink")
    url = _on_host(kb.canonical_offer_url(permalink) if isinstance(permalink, str) else None, walk.host)
    _offers(walk, vid, ml, amount, list_amount, code, rung, url, product.get("is_in_stock"), observed)


async def _probe_currency(walk: HostWalk, fetcher: Any, origin: str, handles: List[str], row_cur: str,
                          now: Any) -> bool:
    """False when a probed handle's self-declared price_currency disagrees with
    the registry currency (the host then ends with no row). A probe that cannot
    be read is noted ``currency_unprobed`` and the walk continues."""
    from app.services import price_service as ps

    for handle in handles[:currency_probes()]:
        res = await fetcher.get(origin + "/products/" + handle + ".json", walk.row, now, timeout=FEED_TIMEOUT)
        data = _json(res.body) if (res.gate is None and common.ok_status(res.status)) else None
        variants = ((data or {}).get("product") or {}).get("variants") if isinstance(data, dict) else None
        if not isinstance(variants, list):
            walk.note("currency_unprobed")
            continue
        for v in variants:
            code = ps._resolve_iso_currency(v.get("price_currency")) if isinstance(v, dict) else None
            if code is not None and code != row_cur:
                return False
    return True


def _feed_url(mech: str, origin: str, page: int) -> str:
    if mech == "shopify":
        return "%s/products.json?limit=%d&page=%d" % (origin, SHOPIFY_PAGE, page)
    return "%s/wp-json/wc/store/products?per_page=%d&page=%d" % (origin, WOO_PAGE, page)


async def walk_host(walk: HostWalk, fetcher: Any, now: Any) -> None:
    """The host-level gates (reader, ToS, a known currency, a robots record),
    then at most FEED_WALKER_MAX_PAGES pages on the record's origin."""
    mech = walk.entry.get("mechanism")
    if mech not in READERS:
        walk.reason = "no_reader"
        return
    tos = walk.row.get("tos")
    if not isinstance(tos, dict) or tos.get("verdict") != "allowed":
        walk.reason = "tos"
        return
    row_cur = common.row_currency(walk.row)
    if row_cur is None:
        walk.reason = "currency_unknown"
        return
    robots = walk.row.get("robots")
    origin = robots.get("origin") if isinstance(robots, dict) else None
    if not isinstance(origin, str) or not origin:
        walk.reason = "no_record"
        return
    page_size = SHOPIFY_PAGE if mech == "shopify" else WOO_PAGE
    probed = mech != "shopify"
    for page in range(1, max_pages() + 1):
        res = await fetcher.get(_feed_url(mech, origin, page), walk.row, now, timeout=FEED_TIMEOUT)
        reason = _end_reason(res)
        if reason is not None:
            walk.reason = reason
            return
        data = _json(res.body)
        items = data.get("products") if (mech == "shopify" and isinstance(data, dict)) else data
        if not isinstance(items, list):
            walk.reason = "bad_feed"
            return
        walk.pages += 1
        observed = common._now()
        if not probed:
            probed = True
            handles = [p.get("handle") for p in items if isinstance(p, dict) and isinstance(p.get("handle"), str)]
            if not await _probe_currency(walk, fetcher, origin, handles, row_cur, now):
                walk.reason = "currency_disagrees"
                walk.drop_rows()
                return
        for product in items:
            if mech == "shopify":
                map_shopify(walk, origin, product, row_cur, observed)
            else:
                map_woo(walk, product, row_cur, observed)
        if len(items) < page_size:
            return


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="cron_feed_walker")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--report", default=None)
    return p.parse_args(argv if argv is not None else [])


def _write_host(writer: Any, walk: HostWalk) -> None:
    try:
        writer.products(list(walk.product_rows.values()))
        writer.variants(list(walk.variant_rows.values()))
        writer.offers(walk.offer_rows)
    except Exception as exc:  # noqa: BLE001 - one host's write never ends the run
        logger.warning("%s host=%s write failed (%s)", PREFIX, walk.host, type(exc).__name__)


async def _run(args: argparse.Namespace, mode: str, client: Any) -> int:
    try:
        rows = common.read_merchant_rows(client)
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s kb_merchants read failed (%s)", PREFIX, type(exc).__name__)
        return 0
    now = common._now()
    fetcher = common.PoliteFetcher(require_tos=True)
    writer = common.KbWriter(client)
    report: Dict[str, Any] = {"hosts": [], "ranking": []}
    carriers: Dict[str, set] = {}
    totals: Dict[str, int] = {}
    for row, entry in select_hosts(rows):
        walk = HostWalk(row, entry)
        try:
            await walk_host(walk, fetcher, now)
        except Exception as exc:  # noqa: BLE001 - one host never ends the run
            walk.reason = "error_" + type(exc).__name__
        ok = walk.reason == "ok"
        if mode == common.MODE_APPLY and ok:
            _write_host(writer, walk)
        for pid in walk.pids if ok else ():
            carriers.setdefault(pid, set()).add(walk.host)
        logger.info("%s host=%s reason=%s pages=%d products=%d kept=%d offers=%d no_brand=%d", PREFIX,
                    walk.host, walk.reason, walk.pages, walk.products, walk.kept, len(walk.offer_rows),
                    walk.counts.get("no_brand", 0))
        common.bump(totals, walk.reason)
        report["hosts"].append({"host": walk.host, "reason": walk.reason, "pages": walk.pages,
                                "products": walk.products, "kept": walk.kept, "offers": len(walk.offer_rows),
                                "counts": dict(walk.counts), "notes": list(walk.notes),
                                "samples": walk.samples[:SAMPLE_PER_HOST]})
    ranking = sorted(((len(h), pid) for pid, h in carriers.items()), key=lambda t: (-t[0], t[1]))
    report["ranking"] = [{"pid": pid, "merchants": n} for n, pid in ranking[:RANK_TOP]]
    totals["juices"] = len(ranking)
    totals["multi_merchant"] = sum(1 for n, _ in ranking if n > 1)
    common.log_counts(PREFIX, totals)
    common.write_report(args.report, report)
    return 0


def main(argv: Optional[List[str]] = None, client: Any = None) -> int:
    mode = feed_walker_mode()
    if mode == common.MODE_OFF:
        logger.info("%s mode=off ENABLE_FEED_WALKER not set; skipping run", PREFIX)
        return 0
    args = _parse_args(argv)
    mode = common.cli_mode(mode, args.dry_run)
    logger.info("%s mode=%s", PREFIX, mode)
    client = common.resolve_client(client, PREFIX)
    if client is None:
        return 0
    return asyncio.run(_run(args, mode, client))


run = main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main(sys.argv[1:]))
