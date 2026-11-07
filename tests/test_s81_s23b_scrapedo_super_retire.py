"""S81-23b SCRAPEDO-SUPER-RETIRE RED rows (spec S81-G9 unit S81-23b section 5;
RULINGS_S81_G9 R-G9-6: EK2 / EK3 are GREEN's; R2 pins the legacy name read 0
times; R5 the AST census over app/ + scripts/).

  R1-R5  fail at base on an AssertionError only
  P1-P4  green at base, with the full configuration (a run-time token,
         SCRAPEDO_GEOCODE where stated, the httpx recorder on both render
         functions, the routing registry pinned to the literal rows)

Hermetic: the S23 helpers by import of the module object
(tests.test_s81_s23_bypass_retire; its rows are not collected twice); httpx is
patched at app.services.scrapedo_service.httpx.AsyncClient; no network; pure
ASCII, LF.
"""
import ast
import importlib
import os
from pathlib import Path

import pytest

from tests import test_s81_s23_bypass_retire as s23

ROOT = Path(__file__).resolve().parents[1]
NEW_FLAG = "ENABLE_SCRAPEDO_SUPER"
LEGACY = "SCRAPEDO_SUPER"
GEO = "SCRAPEDO_GEOCODE"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in (NEW_FLAG, LEGACY, GEO, "ENABLE_MERCHANT_REGISTRY_DB", "ENABLE_DATA_GUARDS_V2",
                 "ENABLE_LONGEST_HOST_MATCH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SCRAPEDO_API_TOKEN", s23._token())
    sd = _sd()
    sd.reset_super_flags_cache()
    sr = importlib.import_module("app.services.source_router")
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", list(sr._LITERAL_ROWS))
    monkeypatch.setattr(sr, "_ROUTABLE_MEMO", None, raising=False)
    yield
    sd.reset_super_flags_cache()


def _sd():
    return importlib.import_module("app.services.scrapedo_service")


def _reader():
    fn = getattr(_sd(), "scrapedo_super_enabled", None)
    assert callable(fn), "scrapedo_service.scrapedo_super_enabled is missing"
    return fn


class _RecEnviron:
    def __init__(self, names):
        self._names = names

    def get(self, name, default=None):
        self._names.append(name)
        return os.environ.get(name, default)

    def __getitem__(self, name):
        self._names.append(name)
        return os.environ[name]

    def __contains__(self, name):
        self._names.append(name)
        return name in os.environ

    def __getattr__(self, name):
        return getattr(os.environ, name)


class _RecOs:
    """A recording stand-in for the scrapedo_service module's ``os``."""

    def __init__(self):
        self.names = []
        self.environ = _RecEnviron(self.names)

    def getenv(self, name, default=None):
        self.names.append(name)
        return os.environ.get(name, default)

    def __getattr__(self, name):
        return getattr(os, name)


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("legacy", ["true", "TRUE"])
def test_r1_legacy_alone_is_off(monkeypatch, legacy):
    sd = _sd()
    monkeypatch.setenv(LEGACY, legacy)
    assert _reader()() is False
    assert sd._super_params() == {}
    assert sd._super_enabled() is False


def test_r2_legacy_name_never_read(monkeypatch):
    sd = _sd()
    rec = _RecOs()
    monkeypatch.setattr(sd, "os", rec)
    monkeypatch.setenv(LEGACY, "true")
    monkeypatch.setenv(GEO, "ae")
    sd._super_params()
    sd._super_enabled()
    s23._render_params(monkeypatch)
    importlib.import_module("app.services.source_router").get_sources_for_category("makeup")
    assert NEW_FLAG in rec.names, rec.names
    assert rec.names.count(LEGACY) == 0, rec.names


def test_r3_legacy_alone_routes_no_super_row(monkeypatch):
    monkeypatch.setenv(LEGACY, "true")
    monkeypatch.setenv(GEO, "ae")
    for cat in ("makeup", "skincare", "fragrances"):
        assert s23.SEPHORA not in s23._routed_bahrain(cat), cat
    for cat in s23.CATEGORIES:
        assert s23._routed_bahrain(cat) == s23.P2_ROUTED["off"][cat], cat


def test_r4_legacy_alone_render_params_plain(monkeypatch):
    monkeypatch.setenv(LEGACY, "true")
    monkeypatch.setenv(GEO, "ae")
    assert s23._render_params(monkeypatch) == [s23._base_params(False)] * 2


def test_r5_no_code_names_the_legacy():
    hits = []
    for top in ("app", "scripts"):
        for path in sorted((ROOT / top).rglob("*.py")):
            tree = ast.parse(path.read_bytes().decode("utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and node.value == LEGACY:
                    hits.append("%s:%d" % (path.relative_to(ROOT).as_posix(), node.lineno))
    assert hits == [], hits


# ---------------------------------------------------------------------------
# PIN rows (green at base)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("new", ["true", "1", "yes", " ON "], ids=["true", "1", "yes", "ON_padded"])
def test_p1_new_name_truthy_on(monkeypatch, new):
    monkeypatch.setenv(NEW_FLAG, new)
    monkeypatch.setenv(GEO, "ae")
    assert _reader()() is True
    assert s23._render_params(monkeypatch) == [s23._base_params(True)] * 2
    for cat in ("makeup", "skincare", "fragrances"):
        assert s23.SEPHORA in s23._routed_bahrain(cat), cat


@pytest.mark.parametrize("new", [None, "false", "0", ""], ids=["unset", "false", "0", "empty"])
def test_p2_production_state_off_identity(monkeypatch, new):
    if new is not None:
        monkeypatch.setenv(NEW_FLAG, new)
    monkeypatch.setenv(GEO, "ae")
    assert _reader()() is False
    assert s23._render_params(monkeypatch) == [s23._base_params(False)] * 2
    for cat in s23.CATEGORIES:
        assert s23._routed_bahrain(cat) == s23.P2_ROUTED["off"][cat], cat


def test_p3_new_false_kills_regardless(monkeypatch):
    sd = _sd()
    monkeypatch.setenv(NEW_FLAG, "false")
    monkeypatch.setenv(LEGACY, "true")
    monkeypatch.setenv(GEO, "ae")
    assert _reader()() is False and sd._super_params() == {} and sd._super_enabled() is False
    assert s23._render_params(monkeypatch) == [s23._base_params(False)] * 2


def test_p4_reset_hook_and_geocode(monkeypatch):
    sd = _sd()
    assert sd.reset_super_flags_cache() is None
    monkeypatch.setenv(NEW_FLAG, "true")
    monkeypatch.delenv(GEO, raising=False)
    assert sd._super_params() == {"super": "true", "geoCode": "bh"}
    assert s23._render_params(monkeypatch) == [s23._base_params(True, "bh")] * 2
