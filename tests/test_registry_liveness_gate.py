"""I5.11 live gate — registry rows must HEAD-resolve (control-calibrated)."""
import pytest

pytestmark = pytest.mark.live_unit


def test_registry_rows_all_live():
    from scripts.verify_source_registry import main
    rc = main()
    if rc == 3:
        pytest.skip("environment network-blocked (controls failed)")
    assert rc == 0, "dead registry rows found - fix or delete per Decision F"
