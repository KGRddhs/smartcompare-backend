"""Pins the eval's genuine-BH source-method set EQUAL to the backend's.

S3.1 follow-on: the eval (scripts/eval_runner.py GENUINE_BH_SOURCE_METHODS) had
drifted from the backend (app/services/price_service.py _GENUINE_BH_SOURCE_METHODS)
— it was missing `page_scrape_jsonld` (the method alhajis/ounass genuine BHD
prices stamp), `firecrawl_brand_domain`, and `official_brand`. Effect: those
genuine prices counted toward `priced` but no bucket, silently UNDER-reporting
the genuine-BH-share KPI. This static parity test prevents future drift in
either direction.
"""
from app.services.price_service import _GENUINE_BH_SOURCE_METHODS as BACKEND_SET
from scripts.eval_runner import GENUINE_BH_SOURCE_METHODS as EVAL_SET


def test_eval_genuine_set_equals_backend_set():
    assert EVAL_SET == BACKEND_SET, (
        "eval genuine-source set drifted from backend.\n"
        f"  only in eval:    {sorted(EVAL_SET - BACKEND_SET)}\n"
        f"  only in backend: {sorted(BACKEND_SET - EVAL_SET)}"
    )


def test_page_scrape_jsonld_is_credited_genuine():
    # the big one — alhajis/ounass genuine BHD prices stamp this method
    assert "page_scrape_jsonld" in EVAL_SET
