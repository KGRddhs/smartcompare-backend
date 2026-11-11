"""S81-16c WDQS-EXEMPTION RED rows (spec S81-G9 unit S81-16c section 5 as amended by
RULINGS_S81_G9 R-G9-4: the rule-set comparison is ORDER-INSENSITIVE, a reorder of
the two rules is exempt; no Retry-After and no body hint = wait the 120 s cap once;
a hint ABOVE the cap = give up with a logged retries count).

  R1-R8 (+ R1b, R5b, R7b)  fail at base on an AssertionError only
  P1-P6                    green at base, run with the full configuration
                           (ENABLE_KB_BRANDS + KB_BRANDS_MAX set, the Rig recorders)

Hermetic: the S16 harness (Rig / _merchant / _records / _mod / _attr /
_brand_bindings) by import of the module object tests.test_s81_s16_kb_seed (its
rows are not collected twice); app.main FIRST (the dotenv hazard); missing
symbols through s16._attr (AssertionError); the robots bodies are built here;
synthetic hosts; no network (the Rig fetch fake only).
"""
import hashlib
import logging
from pathlib import Path

import pytest

from tests import test_s81_s16_kb_seed as s16

ROOT = Path(__file__).resolve().parents[1]
RULING_DATE = "2026-11-07"
RULING_DOC = "docs/policies/2026-11-07-wdqs-robots-exemption.md"
ROBOTS_EVAL_LF_SHA = "bb584acb0539e67b53e8bc6e18a8e9280259ee5194be85a38b2648b64aff3cc2"
SEED_COMMON_LF_SHA = "afc8288eccf8e20b3fb591f878c13decc5879268c4df817113679f6a337c0893"
COMMENT = ("# synthetic query service robots comment" + "." * 10)[:43] + "\n"
PAIR = "User-agent: *\nDisallow: /sparql\nDisallow: /bigdata\n"
LIVE_ROBOTS = COMMENT + PAIR
LIVE_REORDERED = COMMENT + "User-agent: *\nDisallow: /bigdata\nDisallow: /sparql\n"
ONE_RULE = "User-agent: *\nDisallow: /sparql\n"
ALLOWED = "User-agent: *\nAllow: /\n"
RETRY_BODY = "Too many requests; retry in 120 seconds"
UNIT_ENV = ("ENABLE_KB_BRANDS", "ENABLE_KB_SEED", "KB_BRANDS_MAX", "ENABLE_LLM_SPEND_BREAKER",
            "ANTHROPIC_API_KEY") + s16.KNOBS


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in UNIT_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://" + "kbseed-test" + ".invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc" + "-" + "x" * 10)
    yield


def _named_group():
    from app.services import robots_eval as reval

    return "\nUser-agent: " + reval.NAMED_AGENT + "\nDisallow: /sparql\nDisallow: /bigdata\n"


def _brands():
    return s16._mod("seed_kb_brands_wikidata")


def _go(monkeypatch, tmp_path, caplog, responses, mode="true", client=True):
    common = s16._mod("kb_seed_common")
    brands = _brands()
    rig = s16.Rig(monkeypatch, common, merchants=[s16._merchant("store-a.example.com")])
    rig.fetch_responses = list(responses)
    monkeypatch.setenv("KB_BRANDS_MAX", "300")
    s16._set(monkeypatch, "ENABLE_KB_BRANDS", mode)
    caplog.set_level(logging.INFO)
    rep = tmp_path / "brands.json"
    rc = s16._attr(brands, "main")(["--report", str(rep)], client=rig.client if client else None)
    infos = [r.getMessage() for r in s16._records(caplog) if r.levelno == logging.INFO]
    return rc, rig, rep, infos


def _bindings():
    return (200, {}, s16._brand_bindings())


def _refused(rc, rig, rep):
    assert rc == 0
    assert len(rig.fetches) == 1, [f["url"] for f in rig.fetches]
    assert rig.client.writes() == []
    assert not rep.exists()


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

def test_r1_live_body_exempt_two_fetches(monkeypatch, tmp_path, caplog):
    assert len(LIVE_ROBOTS.encode("ascii")) == 95
    rc, rig, rep, infos = _go(monkeypatch, tmp_path, caplog, [(200, {}, LIVE_ROBOTS), _bindings()])
    assert rc == 0
    assert len(rig.fetches) == 2, [f["url"] for f in rig.fetches]
    assert rig.fetches[0]["url"] == "https://query.wikidata.org/robots.txt"
    assert rig.fetches[1]["url"] == _brands().sparql_url()
    assert rep.exists() and s16._report(rep)["hosts"]
    doc = s16._attr(_brands(), "WDQS_RULING_DOC")
    assert doc == RULING_DOC
    hits = [m for m in infos if "robots exemption applied ruling=" + RULING_DATE in m and RULING_DOC in m]
    assert len(hits) == 1, infos
    assert rig.client.writes() == []


def test_r1b_reordered_live_body_exempt(monkeypatch, tmp_path, caplog):
    """R-G9-4: a benign reorder of the two rules is NOT a refusal."""
    rc, rig, rep, infos = _go(monkeypatch, tmp_path, caplog, [(200, {}, LIVE_REORDERED), _bindings()])
    assert rc == 0
    assert len(rig.fetches) == 2, [f["url"] for f in rig.fetches]
    assert rep.exists()
    assert len([m for m in infos if "robots exemption applied ruling=" + RULING_DATE in m]) == 1, infos


@pytest.mark.parametrize("extra", ["Disallow: /\n", "Disallow:\n", "Allow: /x\n"], ids=["slash", "empty", "allow"])
def test_r2_slash_and_extra_rules_refuse(monkeypatch, tmp_path, caplog, extra):
    rc, rig, rep, infos = _go(monkeypatch, tmp_path, caplog, [(200, {}, LIVE_ROBOTS + extra), _bindings()])
    _refused(rc, rig, rep)
    assert any(m.endswith("check=rule_set") for m in infos), infos


def test_r3_qarenbot_group_refuses(monkeypatch, tmp_path, caplog):
    rc, rig, rep, infos = _go(monkeypatch, tmp_path, caplog, [(200, {}, LIVE_ROBOTS + _named_group()), _bindings()])
    _refused(rc, rig, rep)
    assert any(m.endswith("check=named_group") for m in infos), infos


def test_r4_helper_url_and_rules():
    brands = _brands()
    check = s16._attr(brands, "wdqs_exemption_check")
    url = brands.sparql_url()
    assert check(LIVE_ROBOTS, url) is None
    assert check(LIVE_ROBOTS, "https://www.wikidata.org/w/api.php?action=query") == "url"
    assert check(LIVE_ROBOTS, "https://query.wikidata.org/bigdata/namespace/wdq/sparql") == "url"
    assert check(LIVE_ROBOTS, "http://query.wikidata.org/sparql") == "url"
    assert check(LIVE_REORDERED, url) is None
    assert check(ONE_RULE, url) == "rule_set"
    assert check(LIVE_ROBOTS + "Disallow: /\n", url) == "rule_set"
    assert check(LIVE_ROBOTS + _named_group(), url) == "named_group"


def test_r5_429_then_200_one_retry(monkeypatch, tmp_path, caplog):
    rc, rig, rep, infos = _go(monkeypatch, tmp_path, caplog,
                              [(200, {}, ALLOWED), (429, {}, RETRY_BODY), _bindings()])
    assert rc == 0
    assert len(rig.fetches) == 3, [f["url"] for f in rig.fetches]
    assert rig.fetches[1]["url"] == rig.fetches[2]["url"] == _brands().sparql_url()
    assert rig.sleeps == [2.0, 120.0, 2.0], rig.sleeps
    assert rep.exists()
    assert len([m for m in infos if "one retry after 120s" in m]) == 1, infos


def test_r5b_429_no_hint_waits_the_cap(monkeypatch, tmp_path, caplog):
    """R-G9-4 / Q-16c-2: no Retry-After and no body hint = wait the 120 s cap ONCE."""
    rc, rig, rep, _infos = _go(monkeypatch, tmp_path, caplog,
                               [(200, {}, ALLOWED), (429, {}, "Too many requests"), _bindings()])
    assert rc == 0
    assert len(rig.fetches) == 3, [f["url"] for f in rig.fetches]
    assert rig.sleeps == [2.0, 120.0, 2.0], rig.sleeps
    assert rep.exists()


def test_r6_429_twice_gives_up(monkeypatch, tmp_path, caplog):
    rc, rig, rep, infos = _go(monkeypatch, tmp_path, caplog,
                              [(200, {}, ALLOWED), (429, {}, RETRY_BODY), (429, {}, RETRY_BODY), _bindings()])
    assert rc == 0
    assert len(rig.fetches) == 3, [f["url"] for f in rig.fetches]
    assert rig.client.writes() == [] and not rep.exists()
    assert len([m for m in infos if "query failed status=429 retries=1" in m]) == 1, infos


@pytest.mark.parametrize("status,headers,body,wait", [
    (503, {"Retry-After": "30"}, "busy", 30.0),
    (429, {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}, "slow down; retry in 45 seconds", 45.0),
], ids=["header30", "date_body45"])
def test_r7_retry_after_header_and_body(monkeypatch, tmp_path, caplog, status, headers, body, wait):
    rc, rig, rep, _infos = _go(monkeypatch, tmp_path, caplog,
                               [(200, {}, ALLOWED), (status, headers, body), _bindings()])
    assert rc == 0
    assert len(rig.fetches) == 3, [f["url"] for f in rig.fetches]
    assert rig.sleeps[1] == wait, rig.sleeps
    assert rep.exists()


@pytest.mark.parametrize("headers,body", [
    ({"Retry-After": "999"}, "busy"),
    ({}, "Too many requests; retry in 300 seconds"),
], ids=["header999", "body300"])
def test_r7b_hint_above_cap_gives_up(monkeypatch, tmp_path, caplog, headers, body):
    """R-G9-4 / Q-16c-3: a hint ABOVE the cap = GIVE UP (never wait beyond the cap)."""
    rc, rig, rep, infos = _go(monkeypatch, tmp_path, caplog,
                              [(200, {}, ALLOWED), (429, headers, body), _bindings()])
    assert rc == 0
    assert len(rig.fetches) == 2, [f["url"] for f in rig.fetches]
    assert rig.sleeps == [2.0], rig.sleeps
    assert rig.client.writes() == [] and not rep.exists()
    hits = [m for m in infos if "status=429" in m and "retries=0" in m]
    assert len(hits) == 1, infos
    assert "999" not in hits[0] and "300" not in hits[0] and "http" not in hits[0], hits


def test_r8_exemption_only_in_this_script():
    name = RULING_DOC.rsplit("/", 1)[1]
    hits = []
    for top in ("app", "scripts"):
        for path in sorted((ROOT / top).rglob("*.py")):
            text = path.read_bytes().replace(b"\r\n", b"\n").decode("utf-8", "replace")
            if name in text:
                hits.append(path.relative_to(ROOT).as_posix())
    assert hits == ["scripts/seed_kb_brands_wikidata.py"], hits

    def lf_sha(rel):
        return hashlib.sha256((ROOT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()

    assert lf_sha("app/services/robots_eval.py") == ROBOTS_EVAL_LF_SHA
    assert lf_sha("scripts/kb_seed_common.py") == SEED_COMMON_LF_SHA
    src = (ROOT / "scripts" / "seed_kb_brands_wikidata.py").read_bytes().decode("ascii")
    assert "QarenBot" not in src and "NAMED_AGENT" not in src


# ---------------------------------------------------------------------------
# PIN rows (green at base)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", ["403", "timeout", "disallow"])
def test_p1_r24_shapes_still_refuse(monkeypatch, tmp_path, caplog, case):
    first = {"403": (403, {}, "forbidden"), "timeout": TimeoutError("t"), "disallow": (200, {}, ONE_RULE)}[case]
    rc, rig, rep, infos = _go(monkeypatch, tmp_path, caplog, [first, _bindings()])
    _refused(rc, rig, rep)
    assert any("robots" in m for m in infos), infos


def test_p2_named_group_body_refuses(monkeypatch, tmp_path, caplog):
    """R-G9-4: P2 keeps ONLY the QarenBot-group body (a reorder is exempt now)."""
    rc, rig, rep, _infos = _go(monkeypatch, tmp_path, caplog,
                               [(200, {}, LIVE_ROBOTS + _named_group()), _bindings()])
    _refused(rc, rig, rep)


@pytest.mark.parametrize("first", [(403, {}, "forbidden"), (500, {}, "oops"), TimeoutError("t")],
                         ids=["403", "500", "timeout"])
def test_p3_unreadable_fail_closed(monkeypatch, tmp_path, caplog, first):
    rc, rig, rep, infos = _go(monkeypatch, tmp_path, caplog, [first, _bindings()])
    _refused(rc, rig, rep)
    assert any("robots unreadable" in m for m in infos), infos


def test_p4_allowed_body_byte_identical(monkeypatch, tmp_path, caplog):
    from app.services import robots_registry as rr

    rc, rig, rep, infos = _go(monkeypatch, tmp_path, caplog, [(200, {}, ALLOWED), _bindings()])
    assert rc == 0
    assert len(rig.fetches) == 2 and rig.sleeps == [2.0], (rig.fetches, rig.sleeps)
    for f in rig.fetches:
        assert f["headers"] == rr._REQUEST_HEADERS
        assert rr.QARENBOT_UA in f["headers"]["User-Agent"] and "contact:" in f["headers"]["User-Agent"]
        assert f["allow_redirects"] is False
    assert rep.exists() and rig.client.writes() == []
    assert not [m for m in infos if "exemption" in m or "retry" in m], infos


def test_p5_non_retry_failure_line(monkeypatch, tmp_path, caplog):
    rc, rig, rep, infos = _go(monkeypatch, tmp_path, caplog, [(200, {}, ALLOWED), (500, {}, "err"), _bindings()])
    assert rc == 0
    assert len(rig.fetches) == 2, [f["url"] for f in rig.fetches]
    assert rig.sleeps == [2.0], rig.sleeps
    assert [m for m in infos if "query failed" in m] == ["[KB_BRANDS] query failed status=500"], infos
    assert not rep.exists()


@pytest.mark.parametrize("value", [None, "", "false", "0", "off", "dry"], ids=lambda v: repr(v))
def test_p6_off_inert(monkeypatch, tmp_path, caplog, value):
    rc, rig, rep, _infos = _go(monkeypatch, tmp_path, caplog, [(200, {}, LIVE_ROBOTS), _bindings()],
                               mode=value, client=False)
    assert rc == 0
    assert rig.fetches == [] and rig.sleeps == [] and rig.client_factory_calls == []
    assert rig.client.writes() == [] and not rep.exists()
