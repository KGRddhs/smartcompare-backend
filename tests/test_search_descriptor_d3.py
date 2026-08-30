"""UNIT D3 — the per-host SEARCH DESCRIPTOR (``ENABLE_SEARCH_DESCRIPTOR``, default OFF).

WHAT THIS UNIT IS. B8 measured the discovery lane and found two things that
together decide the shape of this code:

  1. Of the 95 LIVE fragrance rows in ``data/bh_gcc_sources.json``, **71 carry
     no mechanism at all** (re-counted here, not quoted: see
     ``TestRegistryGapIsReal``). Every cold compare against one of them pays a
     platform probe to work out where its search lives.
  2. A per-PLATFORM hard-coded search template is wrong about 40% of the time,
     and the dominant reason is ``robots.txt``, not markup: three "Shopify"
     hosts on B8's 30-host panel Disallow ``/search`` and six do not — the same
     platform, two different shipped robots templates.

So the answer is a per-HOST descriptor, resolved ONCE off-clock and persisted,
not a template per platform. This file pins the four properties that make that
safe: the descriptor survives a registry rebuild, the robots evaluator is
RFC-9309-correct where the stdlib is not, the read path spends ZERO fetches,
and with the flag off nothing changes at all.

WHY WE SHIP OUR OWN ROBOTS EVALUATOR. ``urllib.robotparser`` gives the WRONG
answer on real files from B8's panel, in two independent ways, and both are
pinned below against the CACHED robots bodies (``TestRobotsEvaluator``):

  * it lets a LATER ``User-agent: *`` group OVERWRITE an earlier one instead of
    MERGING same-agent groups (RFC 9309 sec 2.2.1) — scentsplit.com ships two
    ``*`` groups and the second silently erases the first's ``Disallow: /search``;
  * it matches the agent by a prefix token of the UA string, so a browser-shaped
    UA falls into klinq.com's ``User-agent: Mozilla`` / ``Disallow: /`` group.
    Under a NAMED token (what we identify as) the correct reading is the
    permissive ``*`` group — klinq is MORE crawlable named than impersonating.

NO LIVE CALLS ANYWHERE IN THIS FILE. Every robots body and the one HTML
fragment came off disk from the B8 measurement cache; ``SOURCES.json`` in the
fixture directory names the host, the fetch date and what was kept. The probe
tests inject a fake fetch and assert its call count — that is the whole point
of the unit.
"""
from __future__ import annotations

import io
import json
import urllib.robotparser
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services import robots_eval
from app.services import search_descriptor_service as sds

FIXTURES = Path(__file__).parent / "fixtures" / "search_descriptor_d3"
_REPO = Path(__file__).resolve().parents[1]

# The named token we identify as. B8 probed the whole panel under it.
NAMED = "QarenBot"
# A browser-shaped UA — what ``curl_cffi impersonate="chrome"`` sends.
BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _fixture(name: str) -> str:
    with io.open(FIXTURES / name, encoding="utf-8") as fh:
        return fh.read()


def _robots(name: str) -> str:
    return _fixture(name)


def _stdlib_can_fetch(txt: str, agent: str, url: str) -> bool:
    p = urllib.robotparser.RobotFileParser()
    p.parse(txt.splitlines())
    return p.can_fetch(agent, url)


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_SEARCH_DESCRIPTOR", raising=False)
    yield


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_SEARCH_DESCRIPTOR", "true")
    yield


# ---------------------------------------------------------------------------
# 1. The corrected robots evaluator — the two urllib.robotparser bugs, pinned
#    against the cached bodies that produced them.
# ---------------------------------------------------------------------------
class TestRobotsEvaluator:
    def test_later_star_group_merges_it_does_not_overwrite(self):
        """scentsplit.com ships TWO ``User-agent: *`` groups.

        RFC 9309 sec 2.2.1: records with the same product token are ONE group.
        The first group carries ``Disallow: /search``; the second does not
        repeat it. Merging keeps the rule, overwriting loses it — and losing it
        is what makes a crawler fetch a path the site forbade.
        """
        txt = _robots("robots_scentsplit_com.txt")
        url = "https://scentsplit.com/search?q=creed+aventus"
        assert robots_eval.can_fetch(txt, NAMED, url) is False
        # The bug this replaces: the stdlib says the same URL is allowed.
        assert _stdlib_can_fetch(txt, NAMED, url) is True

    def test_named_token_is_not_prefix_matched_into_a_mozilla_group(self):
        """klinq.com carries ``User-agent: Mozilla`` / ``Disallow: /``.

        Agent matching is by PRODUCT TOKEN. ``QarenBot`` is not ``Mozilla``, so
        the named agent falls into the permissive ``*`` group and may fetch;
        a browser-shaped UA IS a Mozilla token and is disallowed site-wide.
        The stdlib gets the browser direction wrong.
        """
        txt = _robots("robots_klinq_com.txt")
        home = "https://klinq.com/"
        assert robots_eval.can_fetch(txt, NAMED, home) is True
        assert robots_eval.can_fetch(txt, BROWSER, home) is False
        # The bug this replaces: the stdlib admits the browser UA site-wide.
        assert _stdlib_can_fetch(txt, BROWSER, home) is True

    def test_shopify_legacy_template_blocks_both_search_surfaces(self):
        """bh.afnan.com is on Shopify's OLDER default robots (``Disallow: /search``).

        RFC 9309 path matching is prefix-based, so that ONE line kills the HTML
        search page AND ``/search/suggest.json`` — the single best-performing
        discovery channel B8 measured. This is why the descriptor is per-host.
        """
        txt = _robots("robots_bh_afnan_com.txt")
        assert robots_eval.can_fetch(
            txt, NAMED, "https://bh.afnan.com/search?q=oud"
        ) is False
        assert robots_eval.can_fetch(
            txt, NAMED, "https://bh.afnan.com/search/suggest.json?q=oud"
        ) is False
        # ...while the PDP itself stays allowed, which is why the row is live.
        assert robots_eval.can_fetch(
            txt, NAMED, "https://bh.afnan.com/products/gift-set-dehn-al-oud-abiyad"
        ) is True

    def test_woo_host_allows_its_own_search_and_publishes_a_sitemap(self):
        txt = _robots("robots_fragrancebh_com.txt")
        assert robots_eval.can_fetch(
            txt, NAMED, "https://fragrancebh.com/?s=oud&post_type=product"
        ) is True
        assert robots_eval.sitemaps(txt) == [
            "http://fragrancebh.com/sitemap_index.xml"
        ]

    def test_empty_or_junk_robots_is_allow_all_and_never_raises(self):
        for txt in ("", "   \n\n", "not a robots file at all"):
            assert robots_eval.can_fetch(txt, NAMED, "https://x.test/search?q=a") is True


# ---------------------------------------------------------------------------
# 2. The descriptor shape + its round trip through the registry BUILDER.
# ---------------------------------------------------------------------------
class TestDescriptorRoundTrip:
    def test_parse_and_serialize_are_inverse(self):
        row = {
            "search": {
                "kind": "onsite_html",
                "url_template": "https://fragrancebh.com/?s={q}&post_type=product",
                "robots_allowed": True,
                "discovered_via": "homepage_form",
                "resolved_at": "2026-08-30T00:00:00Z",
            }
        }
        desc = sds.parse_search_descriptor(row)
        assert desc is not None
        assert desc.kind == "onsite_html"
        assert desc.robots_allowed is True
        assert desc.to_row() == row["search"]

    def test_unknown_kind_is_rejected_not_coerced(self):
        assert sds.parse_search_descriptor({"kind": "algolia_maybe"}) is None
        assert sds.parse_search_descriptor({}) is None
        assert sds.parse_search_descriptor(None) is None

    def test_rebuild_preserves_the_resolved_descriptor(self, tmp_path, monkeypatch):
        """THE #94 PROPERTY: a rebuild must not erase the resolver's work.

        The resolver writes ``data/search_descriptors.json`` (a per-host
        overlay). The builder reads that overlay on EVERY run, so consolidating
        twice is a fixed point — exactly the failure mode issue #94 documented
        for hand-edits made directly in the generated file.
        """
        import scripts.build_source_registry_data as builder

        overlay = tmp_path / "search_descriptors.json"
        overlay.write_text(
            json.dumps(
                {
                    "hosts": {
                        "fragrancebh.com": {
                            "kind": "onsite_html",
                            "url_template": "https://fragrancebh.com/?s={q}&post_type=product",
                            "robots_allowed": True,
                            "discovered_via": "homepage_form",
                            "resolved_at": "2026-08-30T00:00:00Z",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(builder, "_SEARCH_DESCRIPTORS", overlay)

        first = builder.consolidate()
        row = next(r for r in first if r["domain"] == "fragrancebh.com")
        assert row["search"]["kind"] == "onsite_html"
        assert "{q}" in row["search"]["url_template"]

        # Round trip: write, re-read as the prior generated file, re-consolidate.
        out = tmp_path / "bh_gcc_sources.json"
        out.write_text(json.dumps(first, indent=1, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(builder, "_OUT", out)
        second = builder.consolidate()
        row2 = next(r for r in second if r["domain"] == "fragrancebh.com")
        assert row2["search"] == row["search"]

    def test_rows_without_a_descriptor_are_untouched(self, tmp_path, monkeypatch):
        """No overlay entry -> no ``search`` key. The generated file must not
        grow an empty descriptor on every row (that would be 368 rows of noise
        and a diff nobody can read)."""
        import scripts.build_source_registry_data as builder

        overlay = tmp_path / "search_descriptors.json"
        overlay.write_text(json.dumps({"hosts": {}}), encoding="utf-8")
        monkeypatch.setattr(builder, "_SEARCH_DESCRIPTORS", overlay)
        rows = builder.consolidate()
        assert rows, "consolidation produced no rows"
        assert not any("search" in r for r in rows)

    def test_row_to_source_carries_the_descriptor(self):
        from app.services.source_router import _row_to_source

        src = _row_to_source(
            {
                "domain": "fragrancebh.com",
                "tier": "gcc",
                "weight": 1.5,
                "categories": ["fragrances"],
                "status": "live",
                "search": {
                    "kind": "onsite_html",
                    "url_template": "https://fragrancebh.com/?s={q}&post_type=product",
                    "robots_allowed": True,
                    "discovered_via": "homepage_form",
                    "resolved_at": "2026-08-30T00:00:00Z",
                },
            }
        )
        assert src is not None
        assert src.search_descriptor is not None
        assert src.search_descriptor.kind == "onsite_html"

    def test_a_malformed_descriptor_never_bricks_the_row(self):
        from app.services.source_router import _row_to_source

        src = _row_to_source(
            {
                "domain": "fragrancebh.com",
                "tier": "gcc",
                "weight": 1.5,
                "categories": ["fragrances"],
                "status": "live",
                "search": "not-a-dict",
            }
        )
        assert src is not None
        assert src.search_descriptor is None


# ---------------------------------------------------------------------------
# 3. The READ path — a stored descriptor costs ZERO fetches.
# ---------------------------------------------------------------------------
_STORED = sds.SearchDescriptor(
    kind="onsite_html",
    url_template="https://fragrancebh.com/?s={q}&post_type=product",
    robots_allowed=True,
    discovered_via="homepage_form",
    resolved_at="2026-08-30T00:00:00Z",
)


class TestReadPathSpendsNothing:
    def test_flag_on_stored_descriptor_zero_probes(self, flag_on, monkeypatch):
        monkeypatch.setattr(sds, "descriptor_for_host", lambda host: _STORED)
        fetch = MagicMock()
        url = sds.resolve_search_url("fragrancebh.com", "Creed Aventus", fetch=fetch)
        assert url == "https://fragrancebh.com/?s=Creed+Aventus&post_type=product"
        assert fetch.call_count == 0, "a stored descriptor must never touch the network"

    def test_flag_on_no_descriptor_falls_back_to_the_probe(self, flag_on, monkeypatch):
        monkeypatch.setattr(sds, "descriptor_for_host", lambda host: None)
        fetch = MagicMock(return_value=(200, ""))
        sds.resolve_search_url("nodescriptor.test", "Creed Aventus", fetch=fetch)
        assert fetch.call_count >= 1, "absent descriptor must fall back to today's probe"

    def test_flag_on_no_descriptor_and_no_probe_is_none(self, flag_on, monkeypatch):
        monkeypatch.setattr(sds, "descriptor_for_host", lambda host: None)
        assert sds.resolve_search_url("nodescriptor.test", "x") is None

    def test_a_robots_blocked_descriptor_is_not_usable(self, flag_on, monkeypatch):
        blocked = sds.SearchDescriptor(
            kind="platform_api",
            url_template="https://bh.afnan.com/search/suggest.json?q={q}",
            robots_allowed=False,
            discovered_via="platform_probe",
            resolved_at="2026-08-30T00:00:00Z",
        )
        monkeypatch.setattr(sds, "descriptor_for_host", lambda host: blocked)
        fetch = MagicMock()
        assert sds.resolve_search_url("bh.afnan.com", "oud", fetch=fetch) is None
        assert fetch.call_count == 0, "robots said no — do not probe it either"

    def test_kind_none_is_not_a_search_url(self, flag_on, monkeypatch):
        nothing = sds.SearchDescriptor(
            kind="none", url_template="", robots_allowed=True,
            discovered_via="platform_probe", resolved_at="2026-08-30T00:00:00Z",
        )
        monkeypatch.setattr(sds, "descriptor_for_host", lambda host: nothing)
        assert sds.resolve_search_url("x.test", "oud") is None

    def test_the_query_is_url_encoded(self, flag_on, monkeypatch):
        monkeypatch.setattr(sds, "descriptor_for_host", lambda host: _STORED)
        url = sds.resolve_search_url("fragrancebh.com", "L'Interdit Elixir 100 ml")
        assert " " not in url
        assert "%27" in url or "%E2" in url or "'" not in url


# ---------------------------------------------------------------------------
# 4. FLAG OFF = today's behaviour, byte for byte.
# ---------------------------------------------------------------------------
class TestFlagOffIsInert:
    def test_resolve_search_url_is_none_and_reads_nothing(self, flag_off, monkeypatch):
        boom = MagicMock(side_effect=AssertionError("store must not be read"))
        monkeypatch.setattr(sds, "descriptor_for_host", boom)
        fetch = MagicMock()
        assert sds.resolve_search_url("fragrancebh.com", "oud", fetch=fetch) is None
        assert fetch.call_count == 0
        assert boom.call_count == 0

    def test_build_retailer_url_is_unchanged_for_a_descriptor_host(
        self, flag_off, monkeypatch
    ):
        """The wiring point. With the flag OFF the descriptor is never consulted,
        so a host that HAS one still gets exactly today's hard-coded answer."""
        from app.services import price_service

        monkeypatch.setattr(sds, "descriptor_for_host", lambda host: _STORED)
        assert price_service.build_retailer_url("noon", "Creed Aventus") == (
            "https://www.noon.com/search?q=Creed+Aventus"
        )
        assert price_service.build_retailer_url("fragrancebh.com", "Creed Aventus") is None

    def test_build_retailer_url_prefers_the_descriptor_when_on(
        self, flag_on, monkeypatch
    ):
        from app.services import price_service

        monkeypatch.setattr(sds, "descriptor_for_host", lambda host: _STORED)
        assert price_service.build_retailer_url("fragrancebh.com", "Creed Aventus") == (
            "https://fragrancebh.com/?s=Creed+Aventus&post_type=product"
        )
        # A retailer NAME that is not host-shaped keeps the legacy table answer.
        assert price_service.build_retailer_url("noon", "Creed Aventus") == (
            "https://www.noon.com/search?q=Creed+Aventus"
        )


# ---------------------------------------------------------------------------
# 5. The off-clock RESOLVER — robots first, capped fetches, never the two
#    forbidden hosts.
# ---------------------------------------------------------------------------
class TestResolverProbe:
    def test_robots_is_fetched_first_and_a_blocked_surface_is_never_requested(self):
        """bh.afnan.com is on Shopify's legacy robots (``Disallow: /search``).

        The resolver must learn that from robots and then NEVER request the
        blocked surface — not the suggest.json probe, not the search page. It
        still records the sitemap channel, which afnan's robots publishes and
        which B8 measured as allowed on 30 of 30 panel hosts.
        """
        calls = []

        def fetch(url, **kw):
            calls.append(url)
            if url.endswith("/robots.txt"):
                return (200, _robots("robots_bh_afnan_com.txt"))
            return (200, "{}")

        desc = sds.probe_search_descriptor("bh.afnan.com", fetch, mechanism="shopify")
        assert calls[0] == "https://bh.afnan.com/robots.txt"
        assert not any("/search" in c for c in calls), (
            "robots disallowed the search surface — it must never be fetched"
        )
        assert desc.kind == "sitemap"
        assert len(calls) <= 2

    def test_platform_api_probe_wins_when_robots_allows_and_it_answers(self):
        calls = []

        def fetch(url, **kw):
            calls.append(url)
            if url.endswith("/robots.txt"):
                return (200, "User-agent: *\nDisallow: /admin\n")
            return (200, json.dumps({"resources": {"results": {"products": [{}]}}}))

        desc = sds.probe_search_descriptor("shopifyish.test", fetch, mechanism="shopify")
        assert desc.kind == "platform_api"
        assert desc.robots_allowed is True
        assert "{q}" in desc.url_template
        assert desc.discovered_via == "platform_probe"
        assert len(calls) <= 3, "the resolver is capped at 3 fetches per host"

    def test_homepage_form_discovery_reads_the_sites_own_form(self):
        """The B8 lesson: the on-site search path is NOT guessable per platform.

        The fixture is fragrancebh.com's real ``<form role=search>`` — action
        ``https://fragrancebh.com/``, text input ``s``, and a HIDDEN
        ``post_type=product``. Reproducing the hidden field is what turns a
        site-wide blog search into a PRODUCT search.
        """
        html = _fixture("bh_fragrancebh_com_search_form.html")
        tmpl = sds.search_form_template(html, "https://fragrancebh.com/")
        assert tmpl == (
            "https://fragrancebh.com/?s={q}&post_type=product&dgwt_wcas=1"
        )

    def test_form_discovery_returns_none_when_there_is_no_search_form(self):
        html = "<html><body><form action='/cart' method='post'></form></body></html>"
        assert sds.search_form_template(html, "https://x.test/") is None

    def test_probe_falls_through_from_the_platform_api_to_the_form(self):
        calls = []
        form_html = _fixture("bh_fragrancebh_com_search_form.html")

        def fetch(url, **kw):
            calls.append(url)
            if url.endswith("/robots.txt"):
                return (200, _robots("robots_fragrancebh_com.txt"))
            if "/wp-json/" in url:
                return (404, "")
            return (200, form_html)

        desc = sds.probe_search_descriptor(
            "fragrancebh.com", fetch, mechanism="woo_store_json"
        )
        assert desc.kind == "onsite_html"
        assert desc.discovered_via == "homepage_form"
        assert desc.url_template == (
            "https://fragrancebh.com/?s={q}&post_type=product&dgwt_wcas=1"
        )
        assert len(calls) <= 3

    def test_the_two_forbidden_hosts_are_refused_without_a_fetch(self):
        fetch = MagicMock()
        for host in ("fragrantica.com", "www.parfumo.com"):
            with pytest.raises(ValueError):
                sds.probe_search_descriptor(host, fetch)
        assert fetch.call_count == 0


class TestResolverScript:
    def test_live_host_cap_is_twelve(self):
        import scripts.resolve_search_descriptors as res

        assert res.MAX_LIVE_HOSTS == 12
        with pytest.raises(SystemExit):
            res.main(["--hosts", ",".join("h%d.test" % i for i in range(13)), "--live"])

    def test_throttle_floor_is_two_seconds(self):
        import scripts.resolve_search_descriptors as res

        assert res.MIN_THROTTLE_SECONDS >= 2.0

    def test_merge_never_drops_another_hosts_descriptor(self, tmp_path):
        import scripts.resolve_search_descriptors as res

        store = tmp_path / "search_descriptors.json"
        res.write_descriptors(store, {"a.test": _STORED})
        res.write_descriptors(store, {"b.test": _STORED})
        data = json.loads(store.read_text(encoding="utf-8"))
        assert set(data["hosts"]) == {"a.test", "b.test"}


# ---------------------------------------------------------------------------
# 6. The measurement this unit exists for, re-counted from the shipped file.
# ---------------------------------------------------------------------------
class TestRegistryGapIsReal:
    def test_most_live_fragrance_rows_still_have_no_mechanism(self):
        rows = json.loads(
            (_REPO / "data" / "bh_gcc_sources.json").read_text(encoding="utf-8")
        )
        live_frag = [
            r for r in rows
            if r.get("status") == "live" and "fragrances" in (r.get("categories") or [])
        ]
        no_mech = [r for r in live_frag if not (r.get("mechanism") or "").strip()]
        assert len(live_frag) >= 90
        # B8 measured 71 of 95. The point is the RATIO, not the exact integer:
        # a majority of live fragrance rows cannot say where their search is.
        assert len(no_mech) / len(live_frag) > 0.6
