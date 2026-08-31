"""M12 U:V1 — the robots FAIL-CLOSED ruling, pinned in code.

THE RULING (docs/policies/2026-08-31-robots-unreadable-ruling.md, approved by
Ahmed 2026-08-31): when a host's ``robots.txt`` is UNREADABLE — the policy
document itself returns 403 / a WAF challenge / any non-2xx wall / a 5xx /
times out / errors — we FAIL CLOSED and skip the host. The boundary matters
in BOTH directions and is pinned here:

  * 403/401/5xx/timeout/error  → UNREADABLE → skip the host (fail-closed).
  * 404/410                    → the host publishes NO policy → allow-all
                                 (RFC 9309 sec 2.3.1.3 — NOT "unreadable").
  * 200 with an empty/junk body → readable-but-unparseable → allow-all
                                 (RFC 9309 sec 2.3.1.3, unchanged).

TWO SURFACES WERE FAIL-OPEN AT ``6d3d2d3`` AND ARE FIXED + PINNED HERE:

  1. ``search_descriptor_service.probe_search_descriptor`` mapped a non-200 /
     erroring robots fetch to an EMPTY body — and ``robots_eval.can_fetch("")``
     is allow-all, so the probe continued under a walled policy. It now raises
     ``RobotsUnreadableError`` (a ``ValueError``, so the off-clock resolver's
     existing SKIP branch handles it: the host is not persisted and the next
     run retries it — Option A's scheduled re-read for free).

  2. ``sitemap_discovery_service.build_sitemap_index`` — the ONLY thing in the
     repo that crawls a host's sitemaps — consulted robots NOT AT ALL. It now
     fetches the host's robots.txt (status-aware, named ``QarenBot`` UA) before
     ANY sitemap fetch: unreadable → the build is skipped (0 indexed, prior
     index left in place); readable → the index URL and every child sitemap
     URL are evaluated with ``robots_eval.can_fetch`` and a disallowed URL is
     never fetched. Off-clock compliance infrastructure — fixed unconditionally
     (the live request path only reads Redis and is untouched; the channel
     stays behind ``ENABLE_SITEMAP_INDEX``, default OFF).

``robots_eval`` itself is untouched: it is a pure evaluator over a body the
caller supplies, and its empty-body allow-all is CORRECT for a genuine 200 —
the trap (mapping a FAILED fetch to "") lives in callers, which is exactly
what the two fixes close.
"""

import json

import pytest

import app.services.sitemap_discovery_service as sd
from app.services import robots_eval
from app.services import search_descriptor_service as sds

NAMED = robots_eval.NAMED_AGENT

_CF_CHALLENGE = "<html><title>Just a moment...</title></html>"

# A minimal sitemap-index + child pair (bolo-shaped, same as the recorded
# fixtures used by test_sitemap_discovery.py but inlined so this file states
# its whole world).
_INDEX_URL = "https://www.bolo.bh/products-sitemap.xml"
_CHILD1_URL = "https://www.bolo.bh/products-sitemap1.xml"
_CHILD2_URL = "https://www.bolo.bh/products-sitemap2.xml"
_INDEX_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    "<sitemap><loc>%s</loc></sitemap>"
    "<sitemap><loc>%s</loc></sitemap>"
    "</sitemapindex>" % (_CHILD1_URL, _CHILD2_URL)
)
_PDP_URL = (
    "https://www.bolo.bh/products/UO07CAPPYQ2-cerave-vitamin-c-serum-with-"
    "hyaluronic-acid-1-fl-oz"
)
_CHILD1_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    "<url><loc>%s</loc></url>"
    "</urlset>" % _PDP_URL
)


class _SitemapFetcher:
    """Async Optional[str] sitemap fetcher with a call log (child2 is absent)."""

    def __init__(self):
        self.calls = []
        self._map = {_INDEX_URL: _INDEX_XML, _CHILD1_URL: _CHILD1_XML}

    async def __call__(self, url: str):
        self.calls.append(url)
        return self._map.get(url)


def _robots_fetch(status: int, body: str = ""):
    """A status-aware async robots fetcher returning a fixed (status, body)."""

    calls = []

    async def fetch(url: str):
        calls.append(url)
        return (status, body)

    fetch.calls = calls
    return fetch


@pytest.fixture
def memory_redis(monkeypatch):
    store = {}
    monkeypatch.setattr(sd, "get_cached", lambda k: store.get(k))
    monkeypatch.setattr(
        sd, "set_cached", lambda k, v, ttl=0: store.__setitem__(k, v) or True
    )
    return store


# ===========================================================================
# 1. The probe (search_descriptor_service / resolve_search_descriptors.py)
# ===========================================================================
class TestProbeFailsClosed:
    def test_unreadable_403_robots_skips_host_after_one_fetch(self):
        """A WAF-403 on robots.txt = UNREADABLE = skip. Exactly ONE fetch is
        spent (the robots read); no probe runs under the walled policy."""
        calls = []

        def fetch(url, **kw):
            calls.append(url)
            return (403, _CF_CHALLENGE)

        with pytest.raises(sds.RobotsUnreadableError):
            sds.probe_search_descriptor("walled.test", fetch, mechanism="shopify")
        assert calls == ["https://walled.test/robots.txt"]

    def test_unreadable_robots_fetch_exception_skips_host(self):
        calls = []

        def fetch(url, **kw):
            calls.append(url)
            raise TimeoutError("connect timeout")

        with pytest.raises(sds.RobotsUnreadableError):
            sds.probe_search_descriptor("dead.test", fetch, mechanism="shopify")
        assert calls == ["https://dead.test/robots.txt"]

    @pytest.mark.parametrize("status", [401, 403, 429, 500, 502, 503])
    def test_walled_and_erroring_statuses_are_unreadable(self, status):
        def fetch(url, **kw):
            return (status, "whatever")

        with pytest.raises(sds.RobotsUnreadableError):
            sds.probe_search_descriptor("h%d.test" % status, fetch, mechanism="shopify")

    @pytest.mark.parametrize("status", [404, 410])
    def test_absent_robots_is_no_policy_not_unreadable(self, status):
        """404/410 = the host publishes NO policy = allow-all (RFC 2.3.1.3).
        The probe proceeds and can still resolve a platform API."""

        def fetch(url, **kw):
            if url.endswith("/robots.txt"):
                return (status, "")
            return (200, json.dumps({"resources": {"results": {"products": []}}}))

        desc = sds.probe_search_descriptor(
            "norobots%d.test" % status, fetch, mechanism="shopify"
        )
        assert desc.kind == "platform_api"
        assert desc.robots_allowed is True

    def test_empty_200_robots_stays_allow_all(self):
        """A genuine 200-empty body is READABLE-but-unparseable — allow-all per
        RFC 2.3.1.3. Only a FAILED fetch is fail-closed."""

        def fetch(url, **kw):
            if url.endswith("/robots.txt"):
                return (200, "")
            return (200, json.dumps({"products": []}))

        desc = sds.probe_search_descriptor("empty.test", fetch, mechanism="shopify")
        assert desc.kind == "platform_api"

    def test_robots_unreadable_error_is_a_value_error(self):
        """The off-clock resolver's SKIP branch catches ValueError (house rule
        7 refusals). The unreadable skip rides the SAME branch — the host
        prints SKIP, is NOT persisted, and the next run retries it."""
        assert issubclass(sds.RobotsUnreadableError, ValueError)

    def test_resolve_search_url_fails_closed_on_unreadable(self, monkeypatch):
        """Flag ON, no stored descriptor, caller-injected fetch, robots walled
        -> None (fail-closed), no raise. (The LIVE path never injects a fetch,
        so this is the worst reachable case.)"""
        monkeypatch.setenv("ENABLE_SEARCH_DESCRIPTOR", "true")
        monkeypatch.setattr(sds, "descriptor_for_host", lambda host: None)

        def fetch(url, **kw):
            return (403, _CF_CHALLENGE)

        assert sds.resolve_search_url("walled.test", "creed aventus", fetch) is None

    def test_resolver_script_skips_and_does_not_persist_unreadable_host(self, capsys):
        import scripts.resolve_search_descriptors as res

        def fetch(url, **kw):
            host = url.split("/")[2]
            if host == "walled.test":
                return (403, _CF_CHALLENGE)
            if url.endswith("/robots.txt"):
                return (200, "User-agent: *\nDisallow: /admin\n")
            return (200, json.dumps({"products": []}))

        resolved = res.resolve_hosts(
            [("walled.test", "shopify"), ("open.test", "shopify")], fetch
        )
        assert "walled.test" not in resolved, (
            "an unreadable-robots host must NOT be persisted — staying "
            "unresolved is what makes the next run retry it (Option A re-read)"
        )
        assert "open.test" in resolved
        assert "SKIP walled.test" in capsys.readouterr().out


# ===========================================================================
# 2. The sitemap builder (the repo's only sitemap crawler)
# ===========================================================================
class TestSitemapBuilderFailsClosed:
    @pytest.mark.asyncio
    async def test_unreadable_robots_skips_build_and_fetches_nothing(
        self, memory_redis
    ):
        """Robots 403 -> the whole build is skipped: 0 indexed, ZERO sitemap
        fetches, nothing written to Redis (the prior index is left in place)."""
        fetch = _SitemapFetcher()
        robots = _robots_fetch(403, _CF_CHALLENGE)
        count = await sd.build_sitemap_index(
            "bolo.bh", index_url=_INDEX_URL, fetch=fetch, robots_fetch=robots
        )
        assert count == 0
        assert fetch.calls == [], "no sitemap may be fetched under an unreadable robots"
        assert memory_redis == {}

    @pytest.mark.asyncio
    async def test_robots_fetch_exception_fails_closed(self, memory_redis):
        fetch = _SitemapFetcher()

        async def robots(url):
            raise TimeoutError("connect timeout")

        count = await sd.build_sitemap_index(
            "bolo.bh", index_url=_INDEX_URL, fetch=fetch, robots_fetch=robots
        )
        assert count == 0
        assert fetch.calls == []

    @pytest.mark.asyncio
    async def test_absent_robots_404_builds_normally(self, memory_redis):
        """404 robots = no policy published = allow-all; the build proceeds."""
        fetch = _SitemapFetcher()
        count = await sd.build_sitemap_index(
            "bolo.bh", index_url=_INDEX_URL, fetch=fetch,
            robots_fetch=_robots_fetch(404, ""),
        )
        assert count > 0
        assert _INDEX_URL in fetch.calls

    @pytest.mark.asyncio
    async def test_permissive_robots_builds_normally(self, memory_redis):
        fetch = _SitemapFetcher()
        count = await sd.build_sitemap_index(
            "bolo.bh", index_url=_INDEX_URL, fetch=fetch,
            robots_fetch=_robots_fetch(200, "User-agent: *\nDisallow: /admin\n"),
        )
        assert count > 0

    @pytest.mark.asyncio
    async def test_readable_disallow_all_is_obeyed(self, memory_redis):
        """A READABLE robots that disallows us is obeyed — this is not the
        unreadable branch, it is the ordinary half of the ruling's posture."""
        fetch = _SitemapFetcher()
        count = await sd.build_sitemap_index(
            "bolo.bh", index_url=_INDEX_URL, fetch=fetch,
            robots_fetch=_robots_fetch(200, "User-agent: *\nDisallow: /\n"),
        )
        assert count == 0
        assert fetch.calls == []

    @pytest.mark.asyncio
    async def test_disallowed_child_sitemap_is_never_fetched(self, memory_redis):
        """Per-URL gating: robots disallows child1 -> child1 is never fetched;
        the index and child2 (allowed) still are."""
        fetch = _SitemapFetcher()
        robots = _robots_fetch(
            200, "User-agent: *\nDisallow: /products-sitemap1.xml\n"
        )
        count = await sd.build_sitemap_index(
            "bolo.bh", index_url=_INDEX_URL, fetch=fetch, robots_fetch=robots
        )
        assert _INDEX_URL in fetch.calls
        assert _CHILD1_URL not in fetch.calls, (
            "a child sitemap the robots disallows must never be fetched"
        )
        assert _CHILD2_URL in fetch.calls
        assert count == 0  # child2 is absent (None) -> nothing indexed, honestly

    @pytest.mark.asyncio
    async def test_robots_fetched_once_per_host_before_any_sitemap(self, memory_redis):
        fetch = _SitemapFetcher()
        robots = _robots_fetch(200, "User-agent: *\nAllow: /\n")
        await sd.build_sitemap_index(
            "bolo.bh", index_url=_INDEX_URL, fetch=fetch, robots_fetch=robots
        )
        assert robots.calls == ["https://www.bolo.bh/robots.txt"], (
            "one robots read per host, memoized across the index + children"
        )

    def test_default_robots_fetch_identifies_as_the_named_agent(self):
        """The builder's live robots read identifies as QarenBot, never as a
        browser (the klinq measurement: a browser UA is LESS entitled)."""
        assert sd._ROBOTS_UA.startswith(robots_eval.NAMED_AGENT)


# ===========================================================================
# 3. robots_eval — the evaluator's own boundary, restated under the ruling
# ===========================================================================
class TestEvaluatorBoundaryUnderTheRuling:
    def test_empty_body_is_allow_all_which_is_why_callers_must_fail_closed(self):
        """``can_fetch("")`` is True (RFC unparseable-body allow-all). CORRECT
        for a genuine 200-empty response — and exactly why a caller must NEVER
        map a FAILED robots fetch to an empty body: that silently converts
        'walled policy' into allow-all. The two fixes above pin the callers."""
        assert robots_eval.can_fetch("", NAMED, "https://x.test/anything") is True

    def test_evaluator_never_fetches(self):
        """The evaluator is pure: it IMPORTS no fetching machinery, so the
        unreadable-robots decision CANNOT live here — it is owned by every
        caller that performs the fetch (and is pinned above)."""
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(robots_eval))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not imported & {
            "curl_cffi", "httpx", "requests", "aiohttp", "urllib3", "socket"
        }, "robots_eval must stay a pure, fetch-free evaluator"
