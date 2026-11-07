"""D17c COVERAGE-EMPTY-HOSTS RED rows (spec S81-G9 unit D17c section 5 as amended by
RULINGS_S81_G9 R-G9-2 / R-G9-3) + the D17d process-exit PIN rows.

  R1-R4 (+ R4b)  fail at base on an AssertionError only
  P1-P5          green at base (P4 / P5: each cron main in its own -I process
                 exits with no thread left besides MainThread)

R-G9-2: 0 hosts = a counted skip with NO pipeline call and one INFO; a failed hosts
read counts in not_built with the label pipeline_refused for the SDK signature;
EVERY failed family counts in not_built with one constants-only WARNING (R4b).

Hermetic: app.main FIRST; the D17 harness by import of the module object
(tests.test_s81_d17_coverage); the REAL upstash_redis.Redis on an httpx
MockTransport recorder (no socket); synthetic hosts; pure ASCII, LF.
"""
import json
import logging
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from tests import test_s81_d17_coverage as d17

ROOT = Path(__file__).resolve().parents[1]
STAMP = "kbh:20261101:"
ERR_BODY = {"error": "ERR synthetic"}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in (d17.FLAG, "KB_COVERAGE_MAX_HOSTS", "ENABLE_LIVE_ROBOTS_HEALTH_FLUSH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(d17._common(), "_now", lambda: d17.NOW)
    monkeypatch.setenv("KB_COVERAGE_MAX_HOSTS", "500")
    yield


def _sdk(status, payload, rest_encoding="base64"):
    import httpx
    from upstash_redis import Redis

    posts = []

    def handler(request):
        body = json.loads(request.content)
        posts.append({"url": str(request.url), "json": body})
        return httpx.Response(status, json=payload(body))

    redis = Redis(url="https://fake-upstash.invalid", token="synthetic" + "-word", rest_retries=0,
                  rest_encoding=rest_encoding)
    redis._http._client = httpx.Client(transport=httpx.MockTransport(handler))
    return redis, posts


def _tables(merchants):
    t = d17._tables()
    t["kb_merchants"] = list(merchants)
    return t


def _warnings(caplog):
    return [r for r in caplog.records if r.levelno == logging.WARNING
            and r.getMessage().startswith("[KB_COVERAGE]")]


def _totals(lines):
    found = [ln for ln in lines if ln.startswith("[KB_COVERAGE] totals")]
    assert len(found) == 1 and d17.TOTALS_LINE.match(found[0]), found
    return found[0]


def _go(monkeypatch, caplog, merchants, redis, raise_on=()):
    """Run main DRY; any raise out of main is reported as an AssertionError."""
    try:
        return d17._run(monkeypatch, caplog, "true", tables=_tables(merchants), redis=redis, raise_on=raise_on)
    except AssertionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise AssertionError("main raised %s" % type(exc).__name__)


class _RaisingPipe(d17._Pipe):
    def exec(self):
        self.redis.calls.append(("pipeline.exec", len(self.keys)))
        raise RuntimeError("d17c probe: exec failed")


class _RaisingRedis(d17._Redis):
    def pipeline(self):
        self.calls.append(("pipeline",))
        return _RaisingPipe(self)


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

def test_r1_zero_hosts_no_pipeline_sdk(monkeypatch, caplog):
    redis, posts = _sdk(400, lambda body: ERR_BODY)
    rc, _c, _r, lines = _go(monkeypatch, caplog, [d17._merchant(d17.HOST_C, "candidate")], redis)
    assert rc == 0
    assert posts == [], posts
    assert lines.count("[KB_COVERAGE] family=hosts skipped hosts=0") == 1, lines
    assert _warnings(caplog) == [], [r.getMessage() for r in _warnings(caplog)]
    totals = _totals(lines)
    assert " not_built=0 " in totals and totals.endswith("redis=0"), totals


def test_r2_zero_hosts_no_pipeline_fake(monkeypatch, caplog):
    rds = d17._Redis(d17._hashes())
    rc, _c, _r, lines = _go(monkeypatch, caplog, [], rds)
    assert rc == 0
    assert ("pipeline",) not in rds.calls, rds.calls
    assert not [c for c in rds.calls if c[0].startswith("pipeline")], rds.calls
    assert lines.count("[KB_COVERAGE] family=hosts skipped hosts=0") == 1, lines


@pytest.mark.parametrize("hosts", [1, 2])
def test_r3_400_counts_the_family(monkeypatch, caplog, hosts):
    redis, posts = _sdk(400, lambda body: ERR_BODY)
    merchants = [d17._merchant("h%03d.example.com" % i, "live") for i in range(hosts)]
    rc, _c, _r, lines = _go(monkeypatch, caplog, merchants, redis)
    assert rc == 0
    assert len(posts) == 1, posts
    warns = [r.getMessage() for r in _warnings(caplog)]
    assert warns == ["[KB_COVERAGE] family=hosts read failed (pipeline_refused)"], warns
    totals = _totals(lines)
    assert " not_built=1 " in totals and totals.endswith("redis=0"), totals
    assert not [ln for ln in lines if "metric=host." in ln], lines
    assert not [r for r in caplog.records if r.exc_info], "a traceback was logged"


def test_r4_exec_raise_counts_the_family(monkeypatch, caplog):
    rds = _RaisingRedis(d17._hashes())
    rc, _c, _r, lines = _go(monkeypatch, caplog, [d17._merchant(d17.HOST_A, "live")], rds)
    assert rc == 0
    warns = [r.getMessage() for r in _warnings(caplog)]
    assert warns == ["[KB_COVERAGE] family=hosts read failed (RuntimeError)"], warns
    totals = _totals(lines)
    assert " not_built=1 " in totals, totals


def test_r4b_failed_non_hosts_family_counts(monkeypatch, caplog):
    """R-G9-2: EVERY failed family counts in not_built (one constants-only WARNING)."""
    rds = d17._Redis(d17._hashes())
    merchants = [d17._merchant(d17.HOST_A, "live"), d17._merchant(d17.HOST_B, "blocked")]
    rc, _c, _r, lines = _go(monkeypatch, caplog, merchants, rds, raise_on={"kb_reviews"})
    assert rc == 0
    warns = [r.getMessage() for r in _warnings(caplog)]
    assert warns == ["[KB_COVERAGE] family=reviews read failed (RuntimeError)"], warns
    assert not [r for r in caplog.records if r.exc_info], "a traceback was logged"
    totals = _totals(lines)
    assert " not_built=1 " in totals and totals.endswith("redis=1"), totals


# ---------------------------------------------------------------------------
# PIN rows (green at base)
# ---------------------------------------------------------------------------

def test_p1_one_host_body_shape(monkeypatch, caplog):
    redis, posts = _sdk(200, lambda body: [{"result": []} for _ in body])
    rc, _c, _r, lines = _go(monkeypatch, caplog, [d17._merchant(d17.HOST_A, "live")], redis)
    assert rc == 0
    assert len(posts) == 1, posts
    assert posts[0]["url"].endswith("/pipeline"), posts[0]["url"]
    assert posts[0]["json"] == [["HGETALL", STAMP + d17.HOST_A]], posts[0]["json"]
    assert not [ln for ln in lines if "metric=host." in ln], lines
    assert _totals(lines).endswith("redis=1")
    assert _warnings(caplog) == []


def test_p2_410_hosts_one_pipeline(monkeypatch, caplog):
    hosts = ["h%03d.example.com" % i for i in range(410)]

    def answer(body):
        out = [{"result": []} for _ in body]
        out[0] = {"result": ["curl:robots_skip", "3", "curl:fetch", "5"]}
        return out

    redis, posts = _sdk(200, answer, rest_encoding=None)
    merchants = [d17._merchant(h, "live") for h in reversed(hosts)]
    rc, _c, _r, lines = _go(monkeypatch, caplog, merchants, redis)
    assert rc == 0
    assert len(posts) == 1, len(posts)
    assert posts[0]["json"] == [["HGETALL", STAMP + h] for h in sorted(hosts)]
    got = d17._metrics(lines)
    value, n = got["host.robots_skip:h000.example.com"]
    assert Decimal(value) == 3 and n == 8, (value, n)
    assert _totals(lines).endswith("redis=1")


def test_p3_report_and_totals_shape(monkeypatch, caplog, tmp_path):
    rep = tmp_path / "cov.md"
    rc, _c, _r, lines = d17._run(monkeypatch, caplog, "true", argv=["--report", str(rep)])
    assert rc == 0
    _totals(lines)
    assert "| metric | value | n |" in rep.read_text(encoding="ascii").splitlines()


_DRIVER = r'''
import json, os, sys, threading
sys.path.insert(0, sys.argv[1])
which = sys.argv[2]

class Chain:
    def __getattr__(self, name):
        if name == "execute":
            return lambda *a, **k: type("R", (), {"data": []})()
        return lambda *a, **k: self

class Client:
    def table(self, name):
        return Chain()

if which == "coverage":
    import httpx
    from upstash_redis import Redis
    import scripts.cron_kb_coverage as m
    os.environ["ENABLE_KB_COVERAGE_ROLLUP"] = "true"
    r = Redis(url="https://fake-upstash.invalid", token="synthetic" + "-word", rest_retries=0)
    r._http._client = httpx.Client(transport=httpx.MockTransport(
        lambda req: httpx.Response(400, json={"error": "ERR x"})))
    rc = m.main([], client=Client(), redis=r)
else:
    import scripts.cron_kb_enrich as m
    os.environ["ENABLE_KB_ENRICH_WORKER"] = "true"
    rc = m.main([], client=Client(), redis=None)
alive = sorted(t.name for t in threading.enumerate() if t is not threading.main_thread())
print("rc=%s" % rc)
print("threads=%s" % json.dumps(alive))
'''


def _exit_probe(which):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("UPSTASH", "SUPABASE", "ENABLE_"))}
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([sys.executable, "-I", "-c", _DRIVER, str(ROOT), which], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=60)
    out = proc.stdout.strip().splitlines()
    assert proc.returncode == 0, (proc.returncode, proc.stderr[-2000:])
    assert out[-2:] == ["rc=0", "threads=[]"], (out[-5:], proc.stderr[-2000:])


def test_p4_coverage_process_exits():
    _exit_probe("coverage")


def test_p5_enrich_process_exits():
    _exit_probe("enrich")
