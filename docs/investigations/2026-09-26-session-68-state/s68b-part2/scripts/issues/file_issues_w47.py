"""Files the W4-7 follow-up issues (run AFTER the W4-7 PR merges). python issues/file_issues_w47.py [--dry] [PRNUM]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pr_rest import api, REPO  # noqa: E402

PR = next((a for a in sys.argv[1:] if a.isdigit()), "the W4-7 PR")
CTX = f"Follow-up of PR #{PR} (W4-7 fact-check honesty: `ENABLE_RELIABILITY_UNCHECKED_ABSENCE` coupled to renorm, `ENABLE_CONFIDENCE_SINGLE_COMPUTATION`, `ENABLE_FACTCHECK_SHOPPING_KEY`; all default OFF, read per call)."

ISSUES = [
    ("W4-7e: the price-path parked-price key drift (_price_fallback_on_miss / _parked_price / _price_candidates) - a parked price is recovered for one identity shape and lost for three", f"""
{CTX}

**What is wrong (ruling R6, measured by the W4-7 red).** The price path parks a candidate under one key spelling and looks it up under another: `_price_fallback_on_miss` / `_parked_price` / `_price_candidates` disagree with the size-aware `_get_price` key on variant-bearing and brand-repeating identities, so a parked price is recovered for ONE of the four measured identity shapes and silently lost for the other three (the compare then falls to a later tier or an estimate). W4-7 Part C fixed the same class for the four FACT-CHECK readers by routing them through `_shopping_cache_key`; the PRICE path was out of its scope by ruling (price_service untouched, R9/R10).

**Ask.** Its own flagged unit: route the three price-path readers/writers through the shared `_shopping_cache_key` (or a price_service twin of it) under a default-OFF flag; flag OFF byte-identical over the 414-page corpus gate AND the 167-record scoring equality gate; pin the four identity shapes in both states; measure the recovered-price delta on the corpus and state it.
"""),
    ("W4-7f: persist the identity-matched listing count beside the cached price so a price-cache hit carries a truthful count under ENABLE_CONFIDENCE_SINGLE_COMPUTATION", f"""
{CTX}

**Stated limit (rulings R25/R31a).** Under Part B the price confidence leg's source count is the identity-matched listing count computed over the shopping pool returned THIS request. On a price-cache hit no pool is returned, so the count is UNKNOWN and the leg falls back to today's evidence (the flag-OFF leg). After warm-up most compares are cache hits, so Part B's improvement is invisible on them.

**Ask.** Persist the identity-matched count beside the cached price on both cache layers (L1 Redis 24 h / L2 `product_prices`) when Part B is ON, and read it back on a hit so the leg carries the count the price was computed with; flag OFF byte-identical cache payloads (pinned); include the product-0 scoping of `confidence_details.price.sources_count` on mixed pairs (`_product_shopping_count(product0)` in `compute_confidence` - beside a strong pill it reads 0 and the "Checked across N retail sources." line is absent). Canary: the hit-bucket leg distribution converges on the miss bucket.
"""),
    ("W4-7g: a search-status signal from price_service/serper_service (searched-and-empty vs failed / timed out / no key / budget out) so a real empty search can carry a truthful listing count of 0", f"""
{CTX}

**Stated limit (ruling R31a).** `_do_serper_shopping` returns `{{}}` on any non-200, on Serper's own timeout and on a network error, and `search_product_prices` then returns `{{'shopping': [], 'shopping_region': 'us_fallback'}}` - byte-identical to a REAL empty 200; with no key or the #60 budget exhausted it returns `{{'shopping': [], 'error': ...}}` with no call. Because the orchestrator cannot tell the cases apart, W4-7 treats EVERY empty pool as unknown (the leg keeps today's evidence). A real "searched and found nothing" therefore never carries an honest 0.

**Ask.** A private, additive status key on the search return (`_search_status: ok | empty | failed | timeout | no_key | budget_out`), written by `serper_service` / `price_service` under its own default-OFF flag (flag OFF byte-identical - the corpus byte-identity gate applies), consumed by the Part B stash so `ok`+empty stashes 0 and every failure class stays unknown; pin each class through the real `search_product_prices` with only the transport seams patched (the W4-7 test file already drives it that way for the failure classes).
"""),
    ("Client: 'Checked across 1 retail sources.' has no plural form (confidence detail copy)", f"""
{CTX}

The results screen renders the price-confidence detail as "Checked across N retail sources." from `confidence_details.price.sources_count` with no singular form, so a count of 1 reads "1 retail sources". Under Part B a count of 1 becomes reachable (a one-row identity-matched pool - pinned). Mobile lane: add the plural key (en/ar) through i18next plurals with the `intl-pluralrules` guard, and pin 0 / 1 / 2 / 3 / 11 in both languages; the referenced-key fence must stay green.
"""),
    ("tests: the pre-existing renorm-ON failure of test_scoring_service.py::test_all_missing_data", f"""
Recorded by PR #{PR} (W4-7) while adjudicating its CI-order set: with `ENABLE_MISSING_DIM_RENORM=true` exported, `tests/test_scoring_service.py::test_all_missing_data` fails at BASE (`15e1fb89`) as well - a pre-existing pin of the legacy `MISSING_SCORE=50` sum that the renorm flag changes by design (#101). CI runs with the flag unset, so it never sees it. Ask: make the pin flag-aware (delenv in the node, or a renorm-ON twin with the renormalised expectation) so the file is green in both states; no scoring change.
"""),
    ("response_builder: a non-dict raw price crashes build_comparison_response when the price-pending chokepoint is degraded (pre-existing)", f"""
Recorded by PR #{PR} (W4-7, rulings R12/R30a, measured by its adversaries): with the price-pending chokepoint healthy a non-dict `price` value (99.0, 'BHD 99', 0) is normalised to `{{amount: None, unavailable: True, reason: pending_genuine}}` and every reader copes; with the chokepoint DEGRADED (`exchange_rate_service.get_region_currency` raising) a non-dict raw price reaches `response_builder.build_comparison_response`, which raises at `p.get("price", {{}}).get("source_method")` - at base and in every flag state. A doubly degraded path, but a 500 for the user. Ask: normalise a non-dict price to the pending shape at the top of the builder (idempotent with the chokepoint), pin the degraded path in both flag states, no result change on the healthy path (the 167-record equality gate).
"""),
]


def main():
    dry = "--dry" in sys.argv
    for title, body in ISSUES:
        body = body.strip() + "\n"
        if dry:
            print("DRY", title[:90], len(body)); continue
        st, res = api("POST", f"/repos/{REPO}/issues", {"title": title, "body": body})
        if st != 201:
            print(f"FAILED status={st} {title[:60]} {str(res)[:200]}"); continue
        print(f"created #{res['number']} {res['html_url']}")


if __name__ == "__main__":
    main()
