"""S81-24 gate rows (RULINGS_FIX1_S81_24 F1-3; the correctness minors m1-m3).

- G24-GR1 the HMAC key is pepper.strip(): a padded pepper keys like the bare
  one (kills M58': the strip dropped from the key only).
- G24-GR2 an unknown endpoint allows and writes NO key (kills A17: the
  `endpoint not in ENDPOINTS` guard removed).
- G24-GR3 the hop-probe presence booleans are `is not None`: an EMPTY header
  value counts as present (kills A15: the booleans by truthiness).

Each row is green at the fix HEAD and RED on a sha-verified byte-copy mutant.
Hermetic: no network, no .env, synthetic values built at run time.
"""
import asyncio
import hashlib
import hmac
import importlib
import logging
import re

import pytest

MOD = "app.services.auth_throttle"
RID_MOD = "app.middleware.request_id"
FLAG = "ENABLE_AUTH_THROTTLE_V2"
HOP_FLAG = "ENABLE_HOP_PROBE_LOG"
PEPPER_ENV_NAME = "AUTH_THROTTLE_" + "PEPPER"
UVICORN_ENV_NAME = "FORWARDED_ALLOW_IPS"
PEPPER_VALUE = "s24-gate-" + "r" * 8
E1 = "gate-a" + "@" + "example.com"
HOP_RE = re.compile(
    r"\[HOP_PROBE\] xff_entries=(\d+) xff_leftmost_is_peer=(true|false) "
    r"xff_rightmost_is_peer=(true|false) xff_leftmost_public=(true|false) "
    r"x_real_ip_present=(true|false) x_real_ip_is_peer=(true|false) "
    r"x_real_ip_public=(true|false) forwarded_present=(true|false) "
    r"cf_present=(true|false) peer_public=(true|false) "
    r"uvicorn_forwarded_allow_ips_set=(true|false)"
)


class RecFake:
    """upstash-redis shaped recorder: any command call is recorded."""

    def __init__(self):
        self.calls = []

    def eval(self, script, keys=None, args=None):
        self.calls.append(("eval", tuple(keys or ())))
        return [1, 0, 1]

    def __getattr__(self, name):
        def _cmd(*a, **k):
            self.calls.append((name, a))
            return None
        return _cmd


RecFake.__module__ = "upstash_redis.s24gate"


class Cap(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (the DOTENV GUARD rule: import first, then setenv)
    for name in (FLAG, HOP_FLAG, PEPPER_ENV_NAME, UVICORN_ENV_NAME):
        monkeypatch.delenv(name, raising=False)
    m = importlib.import_module(MOD)
    m._reset_pepper_warning()
    m._reset_skip_memo()
    from app.middleware.rate_limiter import limiter
    limiter.reset()
    yield
    m._reset_pepper_warning()
    m._reset_skip_memo()
    limiter.reset()


@pytest.fixture
def cap():
    lg = logging.getLogger("app")
    c = Cap()
    old = lg.level
    lg.addHandler(c)
    lg.setLevel(logging.INFO)
    yield c
    lg.removeHandler(c)
    lg.setLevel(old)


def _expected(pepper_text, ident):
    return hmac.new(pepper_text.encode("utf-8"), ident.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


@pytest.mark.parametrize("pad", [" %s ", "\t%s\n", "  %s"])
def test_g24_gr1_hmac_key_is_stripped_pepper(monkeypatch, pad):
    at = importlib.import_module(MOD)
    monkeypatch.setenv(PEPPER_ENV_NAME, PEPPER_VALUE)
    bare = at.digest(E1)
    monkeypatch.setenv(PEPPER_ENV_NAME, pad % PEPPER_VALUE)
    padded = at.digest(E1)
    assert bare == _expected(PEPPER_VALUE, E1)
    assert padded == bare


@pytest.mark.parametrize("endpoint", ["bogus", "Login", "login ", "", "update_password"])
def test_g24_gr2_unknown_endpoint_allows_and_writes_no_key(monkeypatch, cap, endpoint):
    at = importlib.import_module(MOD)
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(PEPPER_ENV_NAME, PEPPER_VALUE)
    fake = RecFake()
    from app.services import cache_service
    monkeypatch.setattr(cache_service, "redis_client", fake)
    assert asyncio.run(at.gate(endpoint, E1)) is None
    assert fake.calls == []
    assert [r.getMessage() for r in cap.records if r.getMessage().startswith("[AUTH_THROTTLE]")] == []
    assert asyncio.run(at.gate("register", E1)) is None
    assert len(fake.calls) == 1 and fake.calls[0][0] == "eval"


def test_g24_gr3_empty_header_counts_as_present(monkeypatch, cap):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setenv(HOP_FLAG, "true")
    c = TestClient(app, client=("100.64.0.1", 50000))
    r = c.get("/health", headers={"X-Real-IP": "", "Forwarded": "", "CF-Connecting-IP": ""})
    assert r.status_code == 200
    lines = [x.getMessage() for x in cap.records if x.getMessage().startswith("[HOP_PROBE]")]
    assert len(lines) == 1, lines
    m = HOP_RE.fullmatch(lines[0])
    assert m, lines[0]
    g = m.groups()
    assert g[4] == "true", "x_real_ip_present"
    assert g[7] == "true", "forwarded_present"
    assert g[8] == "true", "cf_present"
    assert g[5] == "false" and g[6] == "false"
    recs = [x for x in cap.records if x.getMessage().startswith("[HOP_PROBE]")]
    assert recs[0].name == RID_MOD
