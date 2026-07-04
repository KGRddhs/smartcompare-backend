"""Wave D — unit-test the usable_exact_genuine KPI metric on synthetic response
bodies (the COLD/WARMED eval RUN against the truth set is the deferred Phase-2 step).
"""
import importlib

er = importlib.import_module("scripts.eval_runner")


def _body(p0, p1):
    return {"overview": {"products": [{"price": p0}, {"price": p1}]}}


# A genuine, in-stock, valid-PDP price for the EXACT truth product. Real cascade prices
# carry a resolved title — the KPI independently validates it against TRUTH (coverage
# review E: truth is MANDATORY; without it the metric is fail-closed, not auto-usable).
GENUINE = {"amount": 80.0, "currency": "BHD", "source_method": "woo_store_api",
           "in_stock": True, "title": "Dior Sauvage Eau de Toilette 100ml",
           "url": "https://theperfumesclub.com/products/sauvage-edt-100ml"}
TRUTH = {"id": "kpi-001", "query": "Dior Sauvage EDT 100ml", "category": "fragrances",
         "expected": {"brand": "Dior"}}


def test_usable_when_genuine_instock_valid_pdp():
    assert er.usable_exact_genuine_for_product(_body(GENUINE, GENUINE), 0, TRUTH) is True


def test_not_usable_without_truth_fail_closed():
    # coverage review E — without a truth entry the identity is UNVERIFIED, so the metric
    # is FAIL-CLOSED (never auto-counts a price as usable).
    assert er.usable_exact_genuine_for_product(_body(GENUINE, GENUINE), 0) is False


def test_not_usable_when_pended():
    pend = {"amount": None, "currency": "BHD", "unavailable": True, "reason": "pending_genuine"}
    assert er.usable_exact_genuine_for_product(_body(pend, GENUINE), 0, TRUTH) is False


def test_not_usable_when_converted_usd():
    conv = {**GENUINE, "source_method": "converted_usd"}
    assert er.usable_exact_genuine_for_product(_body(conv, GENUINE), 0, TRUTH) is False


def test_not_usable_when_estimated():
    est = {**GENUINE, "source_method": "estimated"}
    assert er.usable_exact_genuine_for_product(_body(est, GENUINE), 0, TRUTH) is False


def test_not_usable_when_out_of_stock():
    oos = {**GENUINE, "in_stock": False}
    assert er.usable_exact_genuine_for_product(_body(oos, GENUINE), 0, TRUTH) is False


def test_not_usable_when_listing_url():
    listing = {**GENUINE, "url": "https://www.noon.com/bahrain-en/search?q=dior+sauvage"}
    assert er.usable_exact_genuine_for_product(_body(listing, GENUINE), 0, TRUTH) is False


def test_not_usable_when_no_url_present():
    # B3 FIX — a genuine local_bhd with NO url is NOT usable_exact_genuine: with no
    # PDP we can't confirm the price is current + exact (the prior assertion that a
    # missing url is "benign" codified the B5 fail-open leak).
    no_url = {"amount": 13.3, "currency": "BHD", "source_method": "local_bhd",
              "in_stock": True, "title": "Dior Sauvage Eau de Toilette 100ml"}
    assert er.usable_exact_genuine_for_product(_body(no_url, GENUINE), 0, TRUTH) is False


def test_usable_when_stock_unknown():
    # HONESTY FIX (wf_236e28bd) — UNKNOWN stock (in_stock missing/None, common when a
    # JSON-LD PDP omits `availability`) now COUNTS as usable: the display path SHOWS
    # such a genuine, exact, valid-PDP price, so the KPI must not UNDER-count it.
    # Only a CONFIRMED in_stock=False is rejected (see test_not_usable_when_out_of_stock).
    unknown = {"amount": 13.3, "currency": "BHD", "source_method": "local_bhd",
               "title": "Dior Sauvage Eau de Toilette 100ml",
               "url": "https://sharafdg.com/p/x"}
    assert er.usable_exact_genuine_for_product(_body(unknown, GENUINE), 0, TRUTH) is True


def test_kpi_rejects_wrong_identity_with_truth_entry():
    # B3 FIX — with a truth entry, a genuine/in-stock/valid-PDP price for the WRONG
    # product is NOT usable (independent identity validation, not 'shown==exact').
    truth = {"id": "kpi-frag-001", "query": "YSL Black Opium EDP 90ml",
             "category": "fragrances", "expected": {"brand": "Yves Saint Laurent"}}
    wrong = {"amount": 30.0, "currency": "BHD", "source_method": "local_bhd",
             "in_stock": True, "title": "YSL Libre EDP 90ml",
             "url": "https://sharafdg.com/p/libre"}
    assert er.usable_exact_genuine_for_product(_body(wrong, GENUINE), 0, truth) is False
    right = {**wrong, "title": "YSL Black Opium Eau de Parfum 90ml"}
    assert er.usable_exact_genuine_for_product(_body(right, GENUINE), 0, truth) is True


def test_count_usable_exact_genuine():
    pend = {"amount": None, "unavailable": True}
    assert er.count_usable_exact_genuine(_body(GENUINE, pend), [TRUTH, TRUTH]) == (1, 2)
    assert er.count_usable_exact_genuine(_body(GENUINE, GENUINE), [TRUTH, TRUTH]) == (2, 2)


def test_kpi_structured_storage_axis_enforced():
    # coverage review E — a query that OMITS storage but whose truth.expected pins it must
    # fail a wrong-storage title (independent structured validation, not just truth.query).
    truth = {"id": "e", "query": "iPhone 15", "category": "electronics",
             "expected": {"brand": "Apple", "storage_gb": 256}}
    wrong = {"amount": 50, "source_method": "woo_store_api", "in_stock": True,
             "title": "Apple iPhone 15 128GB", "url": "https://x.com/p/1"}
    right = {**wrong, "title": "Apple iPhone 15 256GB"}
    assert er.usable_exact_genuine_for_product(_body(wrong, GENUINE), 0, truth) is False
    assert er.usable_exact_genuine_for_product(_body(right, GENUINE), 0, truth) is True


def test_kpi_run_mode_wired_aggregates_per_category():
    # coverage review E — the KPI run-mode is WIRED (was dead code): it loads the truth set,
    # POSTs each query, and aggregates per category. A transport that echoes the query as the
    # exact product title makes every entry usable -> per-category share 1.0.
    import asyncio
    import httpx

    def handler(request):
        q = dict(request.url.params).get("q", "")
        body = {"overview": {"products": [{"price": {
            "amount": 30.0, "currency": "BHD", "source_method": "woo_store_api",
            "in_stock": True, "title": q, "url": "https://store.bh/p/x"}}]}}
        return httpx.Response(200, json=body)

    out = asyncio.run(er.run_usable_exact_genuine_kpi(
        base_url="http://test", read_cache=False,
        transport=httpx.MockTransport(handler)))
    assert out["kpi"] == "usable_exact_genuine"
    assert out["overall"]["requested"] == 18  # the truth set size
    assert out["overall"]["share"] == 1.0
    assert set(out["per_category"]) == {"electronics", "fragrances", "fashion"}


def test_count_guard_rejected():
    gr = {"amount": None, "unavailable": True, "reason": "pending_genuine", "guard_rejected": "out_of_stock"}
    pend_plain = {"amount": None, "unavailable": True, "reason": "pending_genuine"}
    assert er.count_guard_rejected(_body(gr, pend_plain)) == 1
    assert er.count_guard_rejected(_body(gr, gr)) == 2
    assert er.count_guard_rejected(_body(GENUINE, pend_plain)) == 0
