"""M13-34 pins — adapter inner timeouts are clamped under the per-source wrap, and
the shared to_thread pool is explicitly sized.

Failure scenario: eleven divergent hardcoded adapter ceilings; four exceeded
`structured_comparison_service._ADAPTER_TIMEOUT` (10s), so the per-source
`_timeout_none` wrap returned None at 10s while the thread stayed parked in
curl.perform(); Bright Data's 20s even exceeded the 15s price race, so the Serper-
depletion fallback could only return after the race had cancelled. All to_thread
sites also shared CPython's unbounded default executor.
"""
import asyncio
import os

import pytest

from app.services import adapter_timeouts
from app.services.adapter_timeouts import adapter_timeout, adapter_inner_ceiling
import app.services.structured_comparison_service as scs

# The modules in scs._new_adapter_specs, mapped to their inner-timeout constant.
_ADAPTER_TIMEOUT_CONSTANTS = {
    "woocommerce_service": ("app.services.woocommerce_service", "_WOO_TIMEOUT"),
    "salla_service": ("app.services.salla_service", "_HTTP_TIMEOUT"),
    "occ_service": ("app.services.occ_service", "_TIMEOUT"),
    "magento_graphql_service": ("app.services.magento_graphql_service", "_HTTP_TIMEOUT"),
    "unbxd_service": ("app.services.unbxd_service", "_HTTP_TIMEOUT"),
    "rest_json_service": ("app.services.rest_json_service", "_REQUEST_TIMEOUT"),
    "noon_service": ("app.services.noon_service", "_HTTP_TIMEOUT"),
    # shopify_gcc adapter -> fetch_shopify_price -> _fetch_shopify_catalog uses
    # price_service.PAGE_SCRAPE_TIMEOUT.
    "price_service_shopify": ("app.services.price_service", "PAGE_SCRAPE_TIMEOUT"),
}


def _load_const(modpath, name):
    import importlib
    mod = importlib.import_module(modpath)
    return getattr(mod, name)


@pytest.mark.parametrize("module,ref", list(_ADAPTER_TIMEOUT_CONSTANTS.items()))
def test_adapter_inner_timeout_under_wrap(module, ref):
    modpath, const = ref
    inner = float(_load_const(modpath, const))
    assert inner <= scs._ADAPTER_TIMEOUT - 1, (
        f"{module}.{const}={inner} exceeds _ADAPTER_TIMEOUT-1 "
        f"(={scs._ADAPTER_TIMEOUT - 1}); it will park a thread past the wrap"
    )


def test_brightdata_timeout_under_price_race():
    from app.services import brightdata_service
    assert brightdata_service._TIMEOUT < scs._PRICE_RACE_TIMEOUT, (
        f"brightdata _TIMEOUT={brightdata_service._TIMEOUT} must be under the "
        f"{scs._PRICE_RACE_TIMEOUT}s race or the fallback can never return in time"
    )


def test_clamp_mirror_matches_scs_wrap():
    """The mirrored wrap constant must equal scs._ADAPTER_TIMEOUT so the clamp
    can never silently drift from the real per-source wrap."""
    assert adapter_timeouts._ADAPTER_WRAP_TIMEOUT == scs._ADAPTER_TIMEOUT


def test_clamp_is_min_of_default_and_ceiling(monkeypatch):
    ceiling = adapter_inner_ceiling()
    assert adapter_timeout(100.0) == ceiling          # clamps a large default
    assert adapter_timeout(2.0) == 2.0                # leaves a small default alone
    assert ceiling <= scs._ADAPTER_TIMEOUT - 1


def test_ceiling_tracks_price_race_env(monkeypatch):
    # A shrunk race pulls the ceiling down with it.
    monkeypatch.setenv("PRICE_RACE_TIMEOUT", "5.0")
    assert adapter_inner_ceiling() == pytest.approx(4.0)
    monkeypatch.delenv("PRICE_RACE_TIMEOUT", raising=False)


def test_default_executor_is_explicitly_sized():
    from app.utils.executor import install_default_executor, default_executor_size
    loop = asyncio.new_event_loop()
    try:
        ex = install_default_executor(loop)
        assert ex is loop._default_executor
        assert ex._max_workers == default_executor_size()
        # Named for stack-dump readability.
        ex.submit(lambda: None).result(timeout=5)
        any_named = any(
            t.name.startswith("qaren-worker") for t in ex._threads
        )
        assert any_named
    finally:
        ex.shutdown(wait=True)
        loop.close()


def test_executor_size_env_override(monkeypatch):
    from app.utils import executor
    monkeypatch.setenv("ADAPTER_EXECUTOR_MAX_WORKERS", "7")
    assert executor.default_executor_size() == 7
    monkeypatch.delenv("ADAPTER_EXECUTOR_MAX_WORKERS", raising=False)
    assert executor.default_executor_size() == executor._DEFAULT_MAX_WORKERS
