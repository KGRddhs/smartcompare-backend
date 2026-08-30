"""UNIT M9 F2 — harden the M5 Magento GraphQL Shape-C url_key adapter against
the failure classes UNIT E3 measured (same flag, ENABLE_MAGENTO_GQL_ADAPTER,
still default OFF).

E3 (scratchpad m8/E3, 12 hosts, one Bahrain residential IP, robots-checked,
>=2.5s/host throttle) put the real hit-rate at 6/12 = 50% and showed the misses
are STRUCTURED, not random:

  (a) NO ENDPOINT despite platform=magento — flaconi.de + breuninger.com answer
      a 2MB / 663KB HTML SPA page with HTTP 404, douglas.at answers a generic
      framework 404 in application/json, dm.de answers 405 with an EMPTY
      Content-Type and 0 bytes. So a response is trustworthy only when it is
      BOTH a JSON content-type AND a data.products envelope; douglas proves
      neither half suffices alone.
  (b) SCHEMA DIVERGENCE — parfum-zentrum.de answers HTTP 400 with five GraphQL
      validation errors (custom ProductPublic / ProductPublicCollection types,
      no url_key filter). A 400 is a schema miss: log it, decline, and never
      re-issue the same query at the same host.
  (c) url_key derivation is per-host fragile — strip .html, but REJECT a
      wholly-numeric last segment (douglas /de/p/<numeric-id>) and a route-marker
      tail (breuninger /<id>/p/) as not-a-url_key, WITHOUT over-rejecting a
      legitimate slug that merely ends in digits (beautysuccess.fr). And
      total_count 0 is a MAPPING miss - the channel is alive, the key is
      unmapped - which must log distinctly from a dead channel.
  (d) GCC — en-kwt.ajmal.com returned AED on a Kuwait subdomain because no
      store-view header was sent and the DEFAULT store answered. Send the
      store-view header where a correct value is known, and RECONCILE the
      returned currency against the registry currency; a mismatch PENDs
      (returns None) instead of shipping a correctly-labelled wrong number.

Every fixture under tests/fixtures/magento_gql_e3/ is a verbatim E3 record
(status + Content-Type + bytes + latency + body); provenance in its SOURCES.json.
NO network: the single ``_raw_post_json`` transport seam is monkeypatched.
"""
import asyncio
import json
import logging
import os

import pytest

import app.services.magento_graphql_service as mg
import app.services.price_service as ps
from app.services.exchange_rate_service import FALLBACK_RATES

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "magento_gql_e3")
FIX_B3 = os.path.join(os.path.dirname(__file__), "fixtures", "magento_gql_b3")
LOGGER_NAME = "app.services.magento_graphql_service"


def _rec(name):
    """One verbatim E3 probe record."""
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


def _run(coro):
    return asyncio.run(coro)


def _body(rec):
    """The record's body as the raw response TEXT the transport would hand back."""
    if "body_json" in rec:
        return json.dumps(rec["body_json"])
    return rec.get("body_text_head", "")


# --- the six E3 working hosts, keyed by fixture -----------------------------
HITS = {
    "arenal": ("arenal_com_200_json_hit_eur.json", "Gentleman Society Ambree",
               51.45, "EUR"),
    "druni": ("druni_es_200_json_hit_eur.json", "Cofre One Million", 72.95, "EUR"),
    "beautysuccess": ("beautysuccess_fr_200_json_hit_eur.json",
                      "Grey flannel Eau de Toilette Vaporisateur 120ml", 59.5, "EUR"),
    "parfumcenter": ("parfumcenter_nl_200_json_hit_eur.json",
                     "Lattafa Yara Moi 100ml eau de parfum spray", 27.95, "EUR"),
    "klinq": ("klinq_com_200_json_hit_bhd.json", "Miss Dior EDP", 48.13, "BHD"),
    "ajmal": ("ajmal_kwt_200_json_aed_default_store_leak.json", "Violet Musc",
              105.000001, "AED"),
}

# --- the six E3 failure classes ---------------------------------------------
MISSES = {
    "flaconi_404_html": ("flaconi_de_404_html_spa_catchall.json", "no_endpoint"),
    "breuninger_404_html": ("breuninger_com_404_html_oups.json", "no_endpoint"),
    "douglas_404_json": ("douglas_at_404_json_framework.json", "no_endpoint"),
    "dm_405_empty": ("dm_de_405_empty_no_ctype.json", "no_endpoint"),
    "notino_403_waf": ("notino_de_403_html_cloudflare.json", "walled"),
    "parfum_zentrum_400": ("parfum_zentrum_de_400_json_schema_divergence.json",
                           "schema_miss"),
}


@pytest.fixture(autouse=True)
def _pagescrape_on(monkeypatch):
    monkeypatch.setattr(mg, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)


def _bypass_plausibility(monkeypatch):
    """Isolate the adapter from the ORTHOGONAL downstream plausibility filter —
    the fragrance floor legitimately drops a genuine-but-low converted price
    (51.45 EUR -> 21.09 BHD reads decant-low to it). Same bypass the M5 pins use;
    every other gate (strict match, content safety) still runs."""
    monkeypatch.setattr(mg, "is_price_showable", lambda *a, **k: True)


def _patch_transport(monkeypatch, record):
    """Monkeypatch the ONE network seam of the hardened Shape-C path with a
    verbatim E3 record. Records every (url, url_key, headers) call so the tests
    can pin BOTH the no-retry contract and the store-view header."""
    calls = []

    async def fake_raw_post(url, body, headers):
        calls.append((url, json.loads(body).get("variables", {}).get("urlKey"),
                      dict(headers)))
        if record is None:
            return None  # transport failure
        return {"status": record["status"],
                "ctype": record.get("content_type", ""),
                "text": _body(record)}

    monkeypatch.setattr(mg, "_raw_post_json", fake_raw_post)
    return calls


# ===========================================================================
# (a) + (b)  the response-trust ladder
# ===========================================================================

@pytest.mark.parametrize("key", sorted(MISSES))
def test_e3_failure_classes_are_classified_and_declined(key):
    """Each measured miss lands in its own outcome — a 400 is a SCHEMA MISS, a
    403 is WALLED, and 404/405 are NO ENDPOINT. None of them is ``ok``."""
    fname, expected = MISSES[key]
    rec = _rec(fname)
    body = rec.get("body_json")
    outcome = mg._classify_gql_response(rec["status"], rec.get("content_type", ""), body)
    assert outcome == expected, f"{key}: {outcome!r} != {expected!r}"
    assert outcome != mg._GQL_OK


@pytest.mark.parametrize("key", sorted(HITS))
def test_e3_working_hosts_classify_ok(key):
    fname = HITS[key][0]
    rec = _rec(fname)
    assert mg._classify_gql_response(
        rec["status"], rec["content_type"], rec["body_json"]) == mg._GQL_OK


def test_json_content_type_alone_is_not_enough_douglas():
    """douglas.at answers application/json — the SHAPE gate is what rejects it.
    Fed at status 200 (its recorded status is 404, which the status rung would
    catch first) to isolate the second half of the gate."""
    rec = _rec("douglas_at_404_json_framework.json")
    assert mg._is_gql_json_ctype(rec["content_type"]) is True
    assert mg._has_products_shape(rec["body_json"]) is False
    assert mg._classify_gql_response(200, rec["content_type"],
                                     rec["body_json"]) == mg._GQL_BAD_SHAPE


def test_html_body_at_200_is_rejected_by_the_content_type_gate():
    """The Content-Type rung, isolated. flaconi's recorded Content-Type and body
    are verbatim; the 200 is NOT — E3 recorded it at 404 — so this exercises the
    rung that would catch an SPA catch-all that answered 200 instead."""
    rec = _rec("flaconi_de_404_html_spa_catchall.json")
    assert mg._classify_gql_response(
        200, rec["content_type"], None) == mg._GQL_NOT_JSON


@pytest.mark.parametrize("ctype,ok", [
    ("application/json", True),
    ("application/json; charset=utf-8", True),          # douglas.at
    ("application/graphql-response+json", True),
    ("text/html; charset=UTF-8", False),                # flaconi / notino
    ("text/html;charset=UTF-8", False),                 # breuninger — NO space
    ("", False),                                        # dm.de — empty header
    (None, False),
    ("text/plain", False),
])
def test_content_type_gate(ctype, ok):
    assert mg._is_gql_json_ctype(ctype) is ok


def test_total_count_zero_is_a_mapping_miss_not_a_dead_channel():
    """A live endpoint that simply does not carry this url_key must be a DISTINCT
    outcome from a dead/absent one. Body from the B4-measured empty control."""
    with open(os.path.join(FIX_B3, "no_match_empty_control.json"), encoding="utf-8") as fh:
        empty = json.load(fh)
    outcome = mg._classify_gql_response(200, "application/json", empty)
    assert outcome == mg._GQL_MAPPING_MISS
    assert outcome not in (mg._GQL_OK, mg._GQL_NO_ENDPOINT, mg._GQL_BAD_SHAPE)


def test_transport_failure_is_its_own_outcome(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _patch_transport(monkeypatch, None)
    payload, outcome = _run(mg._post_graphql_typed(
        "https://www.arenal.com/graphql", mg._SHAPE_C_URLKEY_QUERY,
        {"urlKey": "x"}, {}))
    assert payload is None
    assert outcome == mg._GQL_TRANSPORT


# ===========================================================================
# (c)  url_key derivation
# ===========================================================================

def test_numeric_id_last_segment_is_not_a_url_key():
    """douglas.at PDP paths are /de/p/<numeric-id> — the last segment is a
    product id. E3 probed exactly this id."""
    assert mg._url_key_from_url_strict("https://www.douglas.at/de/p/3001037119") == ""


def test_route_marker_tail_is_not_a_url_key():
    """breuninger.com PDP paths are /de/marken/<brand>/<slug>/<id>/p/ — the last
    segment is the route marker 'p' and the one before it is a numeric id."""
    assert mg._url_key_from_url_strict(
        "https://www.breuninger.com/de/marken/xerjoff/alto-astral/1234567/p/") == ""


def test_numeric_rejection_does_not_over_reject_a_slug_with_a_numeric_tail():
    """beautysuccess.fr's REAL url_key ends in digits and is a full hit — the
    numeric-id rejection must fire on a WHOLLY numeric segment only."""
    key = _rec("beautysuccess_fr_200_json_hit_eur.json")["url_key_probed"]
    assert key.endswith("0911867205")
    assert mg._url_key_from_url_strict(
        "https://www.beautysuccess.fr/" + key) == key


@pytest.mark.parametrize("key", sorted(HITS))
def test_strict_derivation_recovers_every_measured_working_url_key(key):
    """Both the plain and the .html-suffixed PDP form yield the probed key."""
    probed = _rec(HITS[key][0])["url_key_probed"]
    host = _rec(HITS[key][0])["host"]
    assert mg._url_key_from_url_strict(f"https://{host}/{probed}") == probed
    assert mg._url_key_from_url_strict(f"https://{host}/en/{probed}.html") == probed


def test_strict_derivation_agrees_with_legacy_on_the_accepted_forms():
    assert mg._url_key_from_url_strict("https://klinq.com/en/dior-miss-dior-edp.html") \
        == mg._url_key_from_url("https://klinq.com/en/dior-miss-dior-edp.html")


def test_rejected_url_key_issues_no_post(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    calls = _patch_transport(monkeypatch, _rec(HITS["arenal"][0]))
    res = _run(mg.fetch_magento_graphql_url_price(
        "https://www.arenal.com/de/p/3001037119", "Whatever", "BHD"))
    assert res is None
    assert calls == []


# ===========================================================================
#  host pinning — E3 promoted 6, and the dead hosts must stay unpinned
# ===========================================================================

@pytest.mark.parametrize("apex", [
    "arenal.com", "druni.es", "beautysuccess.fr", "parfumcenter.nl",
    "klinq.com", "en-kwt.ajmal.com",
])
def test_e3_working_hosts_are_pinned(apex):
    assert apex in mg._MAGENTO_GQL_URLKEY_HOSTS


@pytest.mark.parametrize("apex", [
    "flaconi.de", "breuninger.com", "douglas.at", "dm.de", "notino.de",
    "parfum-zentrum.de",
])
def test_e3_dead_or_divergent_hosts_are_never_pinned(apex):
    assert apex not in mg._MAGENTO_GQL_URLKEY_HOSTS


# ===========================================================================
#  end-to-end: a working host ships, every failure class declines
# ===========================================================================

@pytest.mark.parametrize("key", ["arenal", "druni", "beautysuccess", "parfumcenter"])
def test_measured_working_hosts_ship_the_converted_price(monkeypatch, key):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    fname, name, amount, cur = HITS[key]
    rec = _rec(fname)
    calls = _patch_transport(monkeypatch, rec)
    url = f"https://{rec['host']}/{rec['url_key_probed']}"
    res = _run(mg.fetch_magento_graphql_url_price(
        url, name, "BHD", resolved_category="fragrances"))
    assert res is not None, f"{key} should ship"
    assert res["source_method"] == "converted_usd"
    assert res["original_currency"] == cur
    assert res["amount"] == pytest.approx(round(amount * FALLBACK_RATES[cur], 3))
    assert len(calls) == 1
    assert calls[0][0] == f"https://{rec['host']}/graphql"
    assert calls[0][1] == rec["url_key_probed"]


def test_klinq_bhd_ships_as_genuine_and_carries_the_store_view_header(monkeypatch):
    """klinq is the one measured GCC host whose response currency RECONCILES with
    the registry (BHD) — it ships genuine, and the POST carries the pinned
    store-view header."""
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    rec = _rec(HITS["klinq"][0])
    calls = _patch_transport(monkeypatch, rec)
    url = "https://klinq.com/en/" + rec["url_key_probed"] + ".html"
    res = _run(mg.fetch_magento_graphql_url_price(
        url, "Miss Dior EDP", "BHD", resolved_category="fragrances"))
    assert res is not None
    assert res["source_method"] == "magento_graphql_bhd"
    assert res["currency"] == "BHD"
    assert res["amount"] == pytest.approx(48.13)
    assert "original_currency" not in res
    assert calls[0][2].get("Store") == "default"


def test_arenal_sends_no_store_view_header(monkeypatch):
    """A non-GCC host has no pinned store view — the header must NOT be invented."""
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    rec = _rec(HITS["arenal"][0])
    calls = _patch_transport(monkeypatch, rec)
    _run(mg.fetch_magento_graphql_url_price(
        f"https://{rec['host']}/{rec['url_key_probed']}",
        "Gentleman Society Ambree", "BHD", resolved_category="fragrances"))
    assert "Store" not in calls[0][2]


def test_ajmal_kw_aed_on_a_kuwait_subdomain_pends_and_never_ships(monkeypatch, caplog):
    """THE GCC MISLABEL CLASS. The default store leaked AED on a KW subdomain;
    the registry currency is KWD. Converting the AED figure would ship a number
    ~12x below the real price, correctly labelled, and nothing downstream could
    tell. Reconciliation must PEND it."""
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    rec = _rec(HITS["ajmal"][0])
    _patch_transport(monkeypatch, rec)
    url = f"https://{rec['host']}/{rec['url_key_probed']}"
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        res = _run(mg.fetch_magento_graphql_url_price(
            url, "Violet Musc", "BHD", resolved_category="fragrances"))
    assert res is None
    blob = " ".join(r.getMessage() for r in caplog.records)
    assert "currency" in blob.lower() and "AED" in blob and "KWD" in blob


def test_expected_currency_is_pinned_for_the_measured_gcc_hosts():
    assert mg._expected_currency_for("klinq.com") == "BHD"
    assert mg._expected_currency_for("en-kwt.ajmal.com") == "KWD"
    # An unknown host has no expectation -> reconciliation is a no-op, never a
    # blanket reject of every global host.
    assert mg._expected_currency_for("arenal.com") == ""


def test_schema_miss_declines_and_never_retries_the_same_query(monkeypatch, caplog):
    """parfum-zentrum's 400 fed to a PINNED host: exactly ONE POST, no price, and
    a schema-miss log — a 400 must never trigger a re-issue of the same query."""
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    calls = _patch_transport(monkeypatch, _rec(MISSES["parfum_zentrum_400"][0]))
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        res = _run(mg.fetch_magento_graphql_url_price(
            "https://www.arenal.com/some-slug", "Anything", "BHD"))
    assert res is None
    assert len(calls) == 1, "a 400 schema miss must not be retried"
    assert "schema" in " ".join(r.getMessage() for r in caplog.records).lower()


@pytest.mark.parametrize("key", ["flaconi_404_html", "breuninger_404_html",
                                 "douglas_404_json", "dm_405_empty",
                                 "notino_403_waf"])
def test_untrustworthy_responses_never_produce_a_price(monkeypatch, key):
    """Each measured non-endpoint / walled response, fed to a PINNED host (the
    real ones are deliberately unpinned, so this is the only way to drive the
    gate end-to-end): no price, exactly one POST."""
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    calls = _patch_transport(monkeypatch, _rec(MISSES[key][0]))
    res = _run(mg.fetch_magento_graphql_url_price(
        "https://www.arenal.com/some-slug", "Anything", "BHD"))
    assert res is None
    assert len(calls) == 1


def test_mapping_miss_logs_distinctly_from_a_dead_channel(monkeypatch, caplog):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    with open(os.path.join(FIX_B3, "no_match_empty_control.json"), encoding="utf-8") as fh:
        empty = json.load(fh)
    _patch_transport(monkeypatch, {"status": 200, "content_type": "application/json",
                                   "body_json": empty})
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        res = _run(mg.fetch_magento_graphql_url_price(
            "https://www.arenal.com/unmapped-slug", "Anything", "BHD"))
    assert res is None
    blob = " ".join(r.getMessage() for r in caplog.records).lower()
    assert "mapping" in blob
    assert "no graphql endpoint" not in blob


# ===========================================================================
#  flag-OFF — the whole hardened path stays unreachable
# ===========================================================================

@pytest.mark.parametrize("host_url", [
    "https://klinq.com/en/dior-miss-dior-edp.html",
    "https://www.druni.es/one-million-estuche-paco-rabanne-eau-toilette-vaporizador",
    "https://en-kwt.ajmal.com/violet-musc-hair-mist-100-ml",
])
def test_flag_off_never_posts_on_a_newly_pinned_host(monkeypatch, host_url):
    monkeypatch.delenv("ENABLE_MAGENTO_GQL_ADAPTER", raising=False)
    calls = _patch_transport(monkeypatch, _rec(HITS["klinq"][0]))
    assert _run(mg.fetch_magento_graphql_url_price(host_url, "Miss Dior EDP", "BHD")) is None
    assert calls == []


def test_flag_off_fetch_page_price_wiring_is_unchanged(monkeypatch):
    """The cascade entry point: flag OFF -> the walled host still resolves to
    None and no POST is issued."""
    monkeypatch.delenv("ENABLE_MAGENTO_GQL_ADAPTER", raising=False)
    calls = _patch_transport(monkeypatch, _rec(HITS["klinq"][0]))

    async def fake_walled(url, domain):
        return None

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_walled)
    res = _run(ps.fetch_page_price(
        "https://klinq.com/en/dior-miss-dior-edp.html", "Miss Dior EDP", "BHD"))
    assert res is None
    assert calls == []
