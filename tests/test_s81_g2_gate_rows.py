"""S81-G2 KB-SEED: the GREEN-owned gate rows (RULINGS_FIX1_S81_G2).

  test_g2_gr1_*   F1-1 (a)-(d): a results read that raises mid-stream with the
                  breaker ON and a held ticket settles the ticket with None
                  (the bound stays held), writes NO llm_spend_ledger row, still
                  writes the rows parsed so far, never deletes the batch, exits
                  0 and logs ONE WARNING carrying the type name and the batch id.
  test_g2_gr2_*   F1-1: the same partial read with the reserve failed open (no
                  ticket): no record call, no ledger row.
  test_g2_gr3_*   F1-1 (b): the later --resume of that batch with a complete
                  read makes no reserve / create / settle / record call and
                  writes exactly ONE ledger row for the batch (the partial run
                  wrote none), then the rows and the delete.
  test_g2_gr4_*   F1-4 (R-G2-11): a Woo product without a usable ``brands``
                  field is skipped ``no_brand`` (the per-host line and the
                  --report carry no_brand=1) and no kb row is written.
  test_g2_gr5_*   F1-5 (GC-4): a D11 host whose persisted robots record
                  disallows "/" for one of the two agents is skipped with
                  reason ``robots`` BEFORE any request (no robots.txt read).

Hermetic: the three RED files' harnesses are reused by import (module objects
only, so none of their rows is collected here twice); synthetic hosts only;
every key-like sentinel is built at run time; no flag is set outside a row's
own monkeypatch.
"""
import logging

import pytest

from tests import test_s81_d09_feed_walker as d09
from tests import test_s81_d11_pdp_discovery as d11
from tests import test_s81_s16_kb_seed as s16

BATCH_ID = "msgbatch_" + "t" * 8
UNIT_ENV = ("ENABLE_KB_SEED", "ENABLE_LLM_SPEND_BREAKER", "ANTHROPIC_API_KEY", "ENABLE_FEED_WALKER",
            "FEED_WALKER_MAX_PAGES", "FEED_WALKER_CURRENCY_PROBES", "ENABLE_DATA_GUARDS_V2",
            "ENABLE_PDP_DISCOVERY", "ENABLE_CC_CDX", "KB_CC_INDEX", "PDP_DISCOVERY_MAX_HOSTS",
            "PDP_DISCOVERY_MAX_JUICES", "PDP_DISCOVERY_MAX_CHILDREN", "ENABLE_SITEMAP_PDP_MARKERS_V2",
            "ENABLE_SITEMAP_MATCH_V2") + s16.KNOBS


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in UNIT_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://" + "g2rows-test" + ".invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc" + "-" + "w" * 10)
    yield


# ---------------------------------------------------------------------------
# F1-1: the spend contract on a partial results read (scripts/seed_kb_batch.py)
# ---------------------------------------------------------------------------

N_JUICES = 4
READ_BEFORE_RAISE = 3


def _partial_run(monkeypatch, tmp_path, caplog, ticket):
    common = s16._mod("kb_seed_common")
    seed = s16._mod("seed_kb_batch")
    corpus = s16._std_corpus(tmp_path, n=N_JUICES)
    rig = s16.Rig(monkeypatch, common, seed=seed, merchants=[s16._merchant("store-a.example.com")],
                  results=s16._answer_all(), results_raise_after=READ_BEFORE_RAISE)
    monkeypatch.setenv("ENABLE_LLM_SPEND_BREAKER", "true")
    monkeypatch.setenv("KB_SEED_MAX_USD", "10")
    monkeypatch.setattr(seed, "request_bound", lambda requests, model: 5.0)
    s16._patch_breaker(monkeypatch, rig, ticket=ticket)
    s16._dry(monkeypatch, "apply")
    caplog.set_level(logging.INFO)
    rc = s16._run_seed(seed, ["--corpus", str(corpus)])
    return common, seed, corpus, rig, rc


def _spec_pids(rig):
    return {r["product_id"] for t, _, rows, _ in rig.client.writes() if t == "kb_specs" for r in rows}


def _ledger_rows(rig):
    return [rows for t, kind, rows, _ in rig.client.writes() if t == "llm_spend_ledger" and kind == "insert"]


def _partial_common_asserts(rig, rc, caplog):
    names = rig.names()
    assert rc == 0
    assert "db:llm_spend_ledger:insert" not in names, "a partial results read wrote an llm_spend_ledger row"
    assert _ledger_rows(rig) == []
    assert len(_spec_pids(rig)) == READ_BEFORE_RAISE, "the rows parsed before the raise were not written"
    assert "delete" not in names, "the batch was deleted after a partial results read"
    warns = [r.getMessage() for r in s16._records(caplog) if r.levelno == logging.WARNING]
    assert len(warns) == 1, warns
    assert "RuntimeError" in warns[0] and BATCH_ID in warns[0]


def test_g2_gr1_partial_read_settles_none_with_ticket(monkeypatch, tmp_path, caplog):
    _, _, _, rig, rc = _partial_run(monkeypatch, tmp_path, caplog, ticket="t")
    reserve = [e for e in rig.events if e[0] == "reserve"]
    assert len(reserve) == 1 and reserve[0][2] == pytest.approx(5.0)
    settles = [e for e in rig.events if e[0] == "settle"]
    assert len(settles) == 1, "the held ticket was not settled exactly once"
    assert settles[0][1].bound_usd == pytest.approx(5.0)
    assert settles[0][2] is None, "the ticket was settled with a partial actual (the bound must stay held)"
    assert not [e for e in rig.events if e[0] == "record"]
    _partial_common_asserts(rig, rc, caplog)


def test_g2_gr2_partial_read_fail_open_records_nothing(monkeypatch, tmp_path, caplog):
    _, _, _, rig, rc = _partial_run(monkeypatch, tmp_path, caplog, ticket=None)
    assert len([e for e in rig.events if e[0] == "reserve"]) == 1
    assert not [e for e in rig.events if e[0] == "record"], "a failed-open reserve recorded a partial actual"
    assert not [e for e in rig.events if e[0] == "settle"]
    _partial_common_asserts(rig, rc, caplog)


def test_g2_gr3_resume_writes_the_one_ledger_row(monkeypatch, tmp_path, caplog):
    common, seed, corpus, rig, rc = _partial_run(monkeypatch, tmp_path, caplog, ticket="t")
    assert rc == 0
    created = list(rig.created)
    assert len(created) == 1 and len(created[0]) == N_JUICES
    rig2 = s16.Rig(monkeypatch, common, seed=seed, merchants=[s16._merchant("store-a.example.com")],
                   statuses=("ended",), results=lambda _r: s16._answer_all()(created[0]))
    s16._patch_breaker(monkeypatch, rig2)
    assert s16._run_seed(seed, ["--corpus", str(corpus), "--resume", BATCH_ID]) == 0
    got = [n for n in rig2.names() if n not in ("factory", "retrieve", "sleep")]
    assert not {"reserve", "create", "settle", "record"} & set(got)
    total = len(_ledger_rows(rig)) + len(_ledger_rows(rig2))
    assert total == 1, "the batch carries %d llm_spend_ledger rows across the partial run and the resume" % total
    (row,) = _ledger_rows(rig2)
    row = row[0] if isinstance(row, list) else row
    assert row.get("provider_batch_id") == BATCH_ID
    tail = got[got.index("results"):]
    assert tail == ["results", "db:llm_spend_ledger:insert", "db:kb_products:upsert", "db:kb_variants:upsert",
                    "db:kb_specs:upsert", "delete"]
    assert len(_spec_pids(rig2)) == N_JUICES


# ---------------------------------------------------------------------------
# F1-4: the Woo no_brand skip (scripts/cron_feed_walker.py::map_woo)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("brands", ["absent", "empty"])
def test_g2_gr4_woo_without_brand_is_skipped(monkeypatch, tmp_path, caplog, brands):
    common, fw = d09._mods()
    product = d09._woo_product()
    if brands == "absent":
        product.pop("brands")
    else:
        product["brands"] = []
    rig = d09.Rig(monkeypatch, common, merchants=[d09._merchant(d09.WOO, mechanism="woo_store_json")],
                  routes={"https://" + d09.WOO + "/wp-json/wc/store/products": d09._woo_page([product])})
    caplog.set_level(logging.INFO)
    rep = tmp_path / "r.json"
    assert d09._run(fw, "apply", monkeypatch, ["--report", str(rep)]) == 0
    assert rig.fetches, "the Woo feed was never read"
    h = d09._host_report(rep, d09.WOO)
    assert h["counts"].get("no_brand") == 1
    assert h["kept"] == 0
    for table in ("kb_products", "kb_variants", "kb_offers"):
        assert rig.client.rows(table) == [], "a Woo product without a brand wrote %s" % table
    lines = [r.getMessage() for r in caplog.records if r.name in d09.G2_LOGGERS
             and ("host=" + d09.WOO + " ") in r.getMessage()]
    assert len(lines) == 1 and " no_brand=1" in lines[0], lines


# ---------------------------------------------------------------------------
# F1-5: the D11 origin gate before the robots.txt read (scripts/cron_pdp_discovery.py)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("agent", ["qarenbot", "star"])
def test_g2_gr5_origin_gate_before_robots_read(monkeypatch, tmp_path, agent):
    common, pd = d11._mods()
    from app.services import robots_eval as re_

    origin = "https://" + d11.HOST
    named = re_.NAMED_AGENT
    if agent == "qarenbot":
        body = "User-agent: %s\nDisallow: /\n\nUser-agent: *\nAllow: /\n" % named
    else:
        body = "User-agent: %s\nAllow: /\n\nUser-agent: *\nDisallow: /\n" % named
    row = d11._merchant(d11.HOST, robots=d11._robots(origin, body))
    assert common.url_gate(row, origin + "/", d11.NOW) == "robots"
    rig = d11.Rig(monkeypatch, common, merchants=[row], routes=d11._std_routes())
    rep = tmp_path / "r.json"
    assert d11._run(pd, "true", monkeypatch, ["--report", str(rep)]) == 0
    assert rig.fetches == [], "a request was made for a host whose record disallows '/'"
    assert rig.validates == []
    h = d11._host_report(rep)
    assert h["reason"] == "robots"
