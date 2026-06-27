"""Wave D — unit-test the usable_exact_genuine KPI metric on synthetic response
bodies (the COLD/WARMED eval RUN against the truth set is the deferred Phase-2 step).
"""
import importlib

er = importlib.import_module("scripts.eval_runner")


def _body(p0, p1):
    return {"overview": {"products": [{"price": p0}, {"price": p1}]}}


GENUINE = {"amount": 80.0, "currency": "BHD", "source_method": "woo_store_api",
           "in_stock": True, "url": "https://theperfumesclub.com/products/sauvage-edt-100ml"}


def test_usable_when_genuine_instock_valid_pdp():
    assert er.usable_exact_genuine_for_product(_body(GENUINE, GENUINE), 0) is True


def test_not_usable_when_pended():
    pend = {"amount": None, "currency": "BHD", "unavailable": True, "reason": "pending_genuine"}
    assert er.usable_exact_genuine_for_product(_body(pend, GENUINE), 0) is False


def test_not_usable_when_converted_usd():
    conv = {**GENUINE, "source_method": "converted_usd"}
    assert er.usable_exact_genuine_for_product(_body(conv, GENUINE), 0) is False


def test_not_usable_when_estimated():
    est = {**GENUINE, "source_method": "estimated"}
    assert er.usable_exact_genuine_for_product(_body(est, GENUINE), 0) is False


def test_not_usable_when_out_of_stock():
    oos = {**GENUINE, "in_stock": False}
    assert er.usable_exact_genuine_for_product(_body(oos, GENUINE), 0) is False


def test_not_usable_when_listing_url():
    listing = {**GENUINE, "url": "https://www.noon.com/bahrain-en/search?q=dior+sauvage"}
    assert er.usable_exact_genuine_for_product(_body(listing, GENUINE), 0) is False


def test_usable_when_genuine_no_url_present():
    # A genuine local_bhd with no url is still usable (missing url is benign).
    no_url = {"amount": 13.3, "currency": "BHD", "source_method": "local_bhd", "in_stock": True}
    assert er.usable_exact_genuine_for_product(_body(no_url, GENUINE), 0) is True


def test_count_usable_exact_genuine():
    pend = {"amount": None, "unavailable": True}
    assert er.count_usable_exact_genuine(_body(GENUINE, pend)) == (1, 2)
    assert er.count_usable_exact_genuine(_body(GENUINE, GENUINE)) == (2, 2)


def test_count_guard_rejected():
    gr = {"amount": None, "unavailable": True, "reason": "pending_genuine", "guard_rejected": "out_of_stock"}
    pend_plain = {"amount": None, "unavailable": True, "reason": "pending_genuine"}
    assert er.count_guard_rejected(_body(gr, pend_plain)) == 1
    assert er.count_guard_rejected(_body(gr, gr)) == 2
    assert er.count_guard_rejected(_body(GENUINE, pend_plain)) == 0
