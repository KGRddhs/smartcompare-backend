"""UNIT D3 — the per-host SEARCH DESCRIPTOR (``ENABLE_SEARCH_DESCRIPTOR``, default OFF).

WHAT A DESCRIPTOR IS. One small record, per HOST, that answers "where does this
store's product search live, and are we allowed to use it" — resolved ONCE,
off the clock, and persisted on the registry row::

    "search": {
      "kind": "platform_api" | "onsite_html" | "sitemap" | "none",
      "url_template": "https://host/path?param={q}",
      "robots_allowed": true,
      "discovered_via": "platform_probe" | "homepage_form" | "robots" | "manual",
      "resolved_at": "2026-08-30T00:00:00Z"
    }

WHY PER HOST AND NOT PER PLATFORM (B8's measurement, not a preference). Two
numbers decide this:

  * **71 of the 95 live fragrance rows carry no mechanism at all.** A cold
    compare against one of them has to work out, from scratch, where its search
    is — a probe every single time, for an answer that does not change.
  * **A per-platform template is wrong about 40% of the time**, and the reason
    is ``robots.txt`` rather than markup. Shopify ships TWO default robots
    templates in the wild: the older one carries ``Disallow: /search``, which —
    because RFC 9309 matches by prefix — kills the HTML search page AND
    ``/search/suggest.json``, the single best-performing discovery channel
    measured. On B8's panel three "Shopify" hosts block it and six do not.
    Magento's ``/catalogsearch/`` 404s on a Magento host; Shopware wants
    ``?search=``, Woo ``?s=``, PrestaShop ``/recherche?s=``. There is no
    template that is right by platform; there is only the answer per store.

WHAT THIS MODULE DOES AND DOES NOT DO. It READS a stored descriptor and formats
a search URL — zero network, zero parsing, one dict lookup. It also carries the
PROBE that fills one in (``probe_search_descriptor``), but the probe takes an
injected ``fetch`` and is called by the off-clock resolver
(``scripts/resolve_search_descriptors.py``), never by the request path. That
split is the whole point of the unit: the live path spends nothing, and the
fetches happen once, elsewhere, under a throttle.

FLAG DISCIPLINE (house rule 1). ``ENABLE_SEARCH_DESCRIPTOR`` is read PER CALL
via ``os.getenv`` — never cached at import — copying
``price_service.exact_gate_enabled`` so Railway can flip it without a restart.
With the flag OFF ``resolve_search_url`` returns ``None`` BEFORE it touches the
store, and every caller takes its existing path unchanged.

HOUSE RULE 7 IS ENFORCED IN CODE, NOT IN A COMMENT. ``fragrantica.com`` and
``parfumo.com`` raise from ``probe_search_descriptor`` before a single fetch:
both disallow our agents by name (Fragrantica names ``ClaudeBot``,
``Claude-SearchBot`` AND ``Claude-User``), and Parfumo served DECOY pages when
probed. No code path here can reach them.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urljoin, urlparse

from app.services import robots_eval

logger = logging.getLogger(__name__)

__all__ = [
    "SEARCH_KINDS",
    "RobotsUnreadableError",
    "SearchDescriptor",
    "candidate_search_templates",
    "descriptor_for_host",
    "format_search_url",
    "parse_search_descriptor",
    "probe_search_descriptor",
    "resolve_search_url",
    "search_descriptor_enabled",
    "search_form_template",
]


class RobotsUnreadableError(ValueError):
    """A host's ``robots.txt`` is UNREADABLE — fail closed, skip the host.

    THE RULING (``docs/policies/2026-08-31-robots-unreadable-ruling.md``,
    approved by Ahmed 2026-08-31): when the policy document itself is walled or
    unreachable (403 / a WAF challenge / any non-2xx wall / a 5xx / a timeout /
    a network error), the host is SKIPPED — never probed under an empty policy.
    A 404/410 is NOT unreadable: that is a host publishing no policy, which
    stays allow-all per RFC 9309 sec 2.3.1.3.

    Subclasses ``ValueError`` so the off-clock resolver's existing skip branch
    (``scripts/resolve_search_descriptors.py::resolve_hosts``) handles it the
    same way as a house-rule-7 refusal: the host prints ``SKIP``, is NOT
    persisted to the store, and the next resolver run retries it — which IS
    Option A's scheduled re-read, for free.
    """

#: The four answers a resolution can produce. ``platform_api`` and
#: ``onsite_html`` are usable search surfaces; ``sitemap`` records "no search,
#: but the already-built sitemap channel applies here" (B8: the sitemap entry
#: path is the ONLY one no host on the panel forbade — 30/30 allowed);
#: ``none`` records a resolved dead end, which is itself worth persisting so we
#: never re-probe it.
SEARCH_KINDS = frozenset({"platform_api", "onsite_html", "sitemap", "none"})

#: How a descriptor was arrived at. Kept because a hand-written record and a
#: probed one age differently, exactly like the builder's ``measured`` note.
DISCOVERED_VIA = frozenset({"platform_probe", "homepage_form", "robots", "manual"})

#: House rule 7, in code. Never fetched, by any path, for any reason.
DENY_HOSTS = ("fragrantica.com", "parfumo.com")

#: Fetch budget per host in the off-clock resolver (B8 sec 10: cheapest first,
#: cap 3). robots.txt is always the first of the three.
MAX_PROBE_FETCHES = 3

#: Bound on the HTML scanned for a search form. A homepage is the biggest page
#: on most storefronts and the form is in the header.
MAX_FORM_SCAN_CHARS = 400_000


@dataclass(frozen=True)
class SearchDescriptor:
    """One host's resolved search surface. Immutable; safe on a frozen Source."""

    kind: str
    url_template: str
    robots_allowed: bool
    discovered_via: str
    resolved_at: str

    @property
    def usable(self) -> bool:
        """True iff this descriptor can produce a search URL right now.

        ``sitemap``/``none`` are resolved answers but not search URLs, and a
        robots-disallowed surface is never usable no matter how well it works.
        """
        return (
            self.kind in ("platform_api", "onsite_html")
            and bool(self.robots_allowed)
            and "{q}" in (self.url_template or "")
        )

    def to_row(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "url_template": self.url_template,
            "robots_allowed": bool(self.robots_allowed),
            "discovered_via": self.discovered_via,
            "resolved_at": self.resolved_at,
        }


def parse_search_descriptor(raw: Any) -> Optional[SearchDescriptor]:
    """Build a descriptor from a registry row (or its inner ``search`` dict).

    Returns ``None`` — never raises, never guesses — for anything malformed: an
    unknown ``kind``, a non-dict, a missing kind. A bad descriptor must degrade
    to "this host has none", which is the pre-D3 world.
    """
    try:
        if isinstance(raw, dict) and "search" in raw and isinstance(raw["search"], dict):
            raw = raw["search"]
        if not isinstance(raw, dict):
            return None
        kind = str(raw.get("kind") or "").strip().lower()
        if kind not in SEARCH_KINDS:
            return None
        via = str(raw.get("discovered_via") or "manual").strip().lower()
        if via not in DISCOVERED_VIA:
            via = "manual"
        return SearchDescriptor(
            kind=kind,
            url_template=str(raw.get("url_template") or ""),
            robots_allowed=bool(raw.get("robots_allowed", False)),
            discovered_via=via,
            resolved_at=str(raw.get("resolved_at") or ""),
        )
    except Exception:  # noqa: BLE001 — one bad row must never brick a load
        return None


def search_descriptor_enabled() -> bool:
    """True iff the per-host search descriptor is consulted (default OFF).

    Read PER CALL (house rule 1) — never cached at import — so Railway can flip
    it without a restart, mirroring ``price_service.exact_gate_enabled``.
    """
    return os.getenv("ENABLE_SEARCH_DESCRIPTOR", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def descriptor_for_host(host: str) -> Optional[SearchDescriptor]:
    """The stored descriptor for ``host``, apex-matched against the registry.

    ``bh.afnan.com`` resolves under its own row; a regional subdomain of a
    registry apex resolves to the apex, the same suffix rule
    ``source_router.match_registry_apex`` uses. Import is LAZY so this module
    stays importable from ``source_router`` itself without a cycle.
    """
    if not host:
        return None
    try:
        from app.services.source_router import (  # lazy: cycle-safe
            _registry_row_for_host,
        )

        raw = str(host)
        if "://" in raw or "/" in raw:
            raw = urlparse(raw if "://" in raw else "//" + raw).netloc or raw
        domain = raw.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]
        if not domain:
            return None
        # M13-12 — the ONE shared longest-match resolver, filtered to rows that
        # carry a descriptor (preserving the legacy "first match WITH a
        # descriptor" semantic on the flag-OFF path). Flag ON: a subdomain host
        # resolves to its OWN {q} template, not the apex storefront's.
        row = _registry_row_for_host(
            domain,
            where=lambda s: getattr(s, "search_descriptor", None) is not None,
        )
        return getattr(row, "search_descriptor", None) if row is not None else None
    except Exception:  # noqa: BLE001 — a lookup must never break discovery
        return None


def format_search_url(descriptor: Optional[SearchDescriptor], query: str) -> Optional[str]:
    """Fill a usable descriptor's template with a URL-encoded query."""
    if descriptor is None or not descriptor.usable:
        return None
    q = (query or "").strip()
    if not q:
        return None
    try:
        return descriptor.url_template.replace("{q}", quote_plus(q))
    except Exception:  # noqa: BLE001
        return None


def resolve_search_url(
    host: str,
    query: str,
    fetch: Optional[Callable[..., Tuple[int, str]]] = None,
) -> Optional[str]:
    """THE READ PATH. A search URL for ``host``, or ``None``.

    Flag OFF -> ``None`` immediately, without reading the store: the caller
    takes its pre-D3 path and behaviour is unchanged.

    Flag ON with a stored descriptor -> the formatted URL, at the cost of ONE
    dict lookup and ZERO fetches. That saved probe is the entire measured
    payoff (B8: 71 of 95 live fragrance rows pay one today, on every cold
    compare, for an answer that does not change between compares).

    Flag ON with NO stored descriptor -> today's behaviour: if the caller
    handed us a ``fetch`` we probe for one (that is what a cold host costs
    now); with no ``fetch`` we return ``None`` and the caller falls back. The
    live path passes no ``fetch`` — probing belongs to the off-clock resolver.
    """
    if not search_descriptor_enabled():
        return None
    descriptor = descriptor_for_host(host)
    if descriptor is not None:
        # A resolved answer is FINAL, including a resolved "no" — re-probing a
        # host we already probed is the cost this unit exists to remove.
        return format_search_url(descriptor, query)
    if fetch is None:
        return None
    try:
        probed = probe_search_descriptor(host, fetch)
    except Exception as exc:  # noqa: BLE001
        logger.info("[search_descriptor] probe failed for %s: %s", host, exc)
        return None
    return format_search_url(probed, query)


# ---------------------------------------------------------------------------
# Resolution — used by scripts/resolve_search_descriptors.py, never by a request.
# ---------------------------------------------------------------------------

#: Platform product-search endpoints, keyed by the registry ``mechanism``.
#: Every one of these was exercised live by B8; the ones that are NOT here
#: (Algolia, Unbxd, noon) are already direct adapters with their own search.
_PLATFORM_TEMPLATES: Dict[str, str] = {
    "shopify": "https://{host}/search/suggest.json?q={q}&resources[type]=product&resources[limit]=10",
    "woo_store_json": "https://{host}/wp-json/wc/store/v1/products?search={q}&per_page=10",
    "salla_api": "https://{host}/search?q={q}",
    "zid": "https://{host}/search?q={q}",
}
#: With NO mechanism recorded (the 71-of-95 case) probe the two cheapest
#: platform APIs in order — this is precisely the 2-fetch cost the descriptor
#: is meant to pay once instead of every compare.
_UNKNOWN_MECHANISM_ORDER = ("shopify", "woo_store_json")


def candidate_search_templates(host: str, mechanism: str = "") -> List[str]:
    """Platform-API templates to try for ``host``, cheapest first."""
    mech = (mechanism or "").strip().lower()
    if mech in _PLATFORM_TEMPLATES:
        keys = [mech]
    elif mech:
        keys = []  # a known non-search mechanism (algolia/unbxd/noon/occ/...)
    else:
        keys = list(_UNKNOWN_MECHANISM_ORDER)
    return [_PLATFORM_TEMPLATES[k].replace("{host}", host) for k in keys]


_FORM_RE = re.compile(r"<form\b[^>]*>.*?</form>", re.IGNORECASE | re.DOTALL)
_ATTR_RE = re.compile(r"""([a-zA-Z_:][-\w:.]*)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""")
_INPUT_RE = re.compile(r"<input\b[^>]*>", re.IGNORECASE)
_SEARCHY_PARAMS = ("q", "s", "search", "query", "keyword", "term", "text", "wd")
_SEARCHY_WORDS = ("search", "recherche", "suche", "suchen", "arama", "busca", "bahth")


def _attrs(tag: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for name, value in _ATTR_RE.findall(tag):
        out[name.lower()] = value.strip("\"'")
    return out


def search_form_template(html: str, base_url: str) -> Optional[str]:
    """Read the site's OWN search form out of its homepage HTML.

    B8's finding is that the on-site search PATH is not guessable per platform —
    it is stated, by the store, in its own ``<form role=search>``. This reads
    the action, the first text/search input's name, AND the form's HIDDEN
    inputs, then rebuilds the URL the browser would submit.

    The hidden inputs are not a detail: ``fragrancebh.com``'s search form ships
    ``<input type=hidden name=post_type value=product>``, and dropping it turns
    a PRODUCT search into a site-wide blog search over the same path.

    Returns a template containing ``{q}``, or ``None`` when the page has no
    search form (which is a real and common answer — B8 found none on
    reefperfumes.com, noon.com and gcc.luluhypermarket.com).
    """
    if not isinstance(html, str) or not html:
        return None
    best: Optional[Tuple[str, str, List[Tuple[str, str]]]] = None
    for block in _FORM_RE.findall(html[:MAX_FORM_SCAN_CHARS]):
        open_tag = block[: block.find(">") + 1]
        form_attrs = _attrs(open_tag)
        if (form_attrs.get("method") or "get").lower() != "get":
            continue  # a POST search cannot be expressed as a URL template
        identity = " ".join(
            [
                form_attrs.get("action", ""),
                form_attrs.get("id", ""),
                form_attrs.get("class", ""),
                form_attrs.get("role", ""),
            ]
        ).lower()
        param: Optional[str] = None
        hidden: List[Tuple[str, str]] = []
        for tag in _INPUT_RE.findall(block):
            attrs = _attrs(tag)
            name = attrs.get("name")
            if not name:
                continue
            itype = (attrs.get("type") or "text").lower()
            if itype in ("search", "text") and param is None:
                param = name
            elif itype == "hidden" and attrs.get("value"):
                hidden.append((name, attrs["value"]))
        if not param:
            continue
        named = any(w in identity for w in _SEARCHY_WORDS)
        if not (named or param.lower() in _SEARCHY_PARAMS):
            continue
        candidate = (form_attrs.get("action") or "/", param, hidden)
        if best is None or named:
            best = candidate
        if named:
            break
    if best is None:
        return None
    action, param, hidden = best
    try:
        url = urljoin(base_url, action or "/")
    except Exception:  # noqa: BLE001
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    sep = "&" if parsed.query else "?"
    tail = "".join("&%s=%s" % (quote_plus(k), quote_plus(v)) for k, v in hidden)
    return "%s%s%s={q}%s" % (url, sep, param, tail)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _deny(host: str) -> bool:
    h = (host or "").lower().strip()
    if h.startswith("www."):
        h = h[4:]
    return any(h == d or h.endswith("." + d) for d in DENY_HOSTS)


def _looks_like_products(body: str) -> bool:
    """A platform search endpoint ANSWERED — i.e. returned product-shaped JSON.

    A 200 alone is not enough: B8 measured hosts that return an HTML 200 for a
    missing JSON endpoint, and reefperfumes.com answered ``/search/suggest.json``
    with 410. So parse, and require a product array to exist (empty is fine —
    the probe query is not the point, the SURFACE is).
    """
    try:
        data = json.loads(body)
    except Exception:  # noqa: BLE001
        return False
    if isinstance(data, list):
        return True
    if isinstance(data, dict):
        results = (
            data.get("resources", {}).get("results", {})
            if isinstance(data.get("resources"), dict)
            else {}
        )
        if isinstance(results, dict) and isinstance(results.get("products"), list):
            return True
        for key in ("products", "data", "items", "results"):
            if isinstance(data.get(key), list):
                return True
    return False


def probe_search_descriptor(
    host: str,
    fetch: Callable[..., Tuple[int, str]],
    mechanism: str = "",
    agent: str = robots_eval.NAMED_AGENT,
) -> SearchDescriptor:
    """Resolve ONE host's search descriptor. Off-clock only. Capped at 3 fetches.

    ROBOTS FIRST, ALWAYS. The first fetch is ``/robots.txt`` and every candidate
    path is checked against it with the corrected evaluator BEFORE it is
    requested — so a host that forbids its search surface costs exactly one
    fetch and yields ``kind="none"``, which we then never re-probe.

    UNREADABLE ROBOTS FAILS CLOSED (ruling 2026-08-31). A robots fetch that
    fails (exception) or returns a walled/erroring status (403/401/5xx/anything
    that is not 200 or 404/410) raises ``RobotsUnreadableError`` — the host is
    skipped for this run and NOT persisted, so a later run retries it. Before
    this ruling the branch mapped a failed read to an EMPTY body, and
    ``robots_eval.can_fetch("")`` is allow-all — i.e. it silently converted
    "the policy is walled" into "there is no policy", the exact fail-open the
    ruling forbids. A 404/410 (no policy published) and a genuine 200-empty
    body remain allow-all per RFC 9309 sec 2.3.1.3.

    Order (B8 sec 10, cheapest first):
      1. the platform product-search API for the recorded mechanism (or, with
         none recorded, Shopify then Woo — the 2-fetch probe this unit exists
         to amortise);
      2. the homepage's own ``<form role=search>`` — one fetch, and the only
         thing that found the robots-allowed ``/recherche?s=`` variant;
      3. ``sitemap`` when robots publishes one (the channel already built and
         dormant behind ``ENABLE_SITEMAP_INDEX``), else ``none``.

    ``fetch(url) -> (status, body)`` is INJECTED: this function performs no I/O
    of its own, which is what lets the tests assert a call count.
    """
    if _deny(host):
        raise ValueError(
            "house rule 7: %s is never fetched (robots.txt disallows our agents "
            "by name, and decoy pages were served when probed)" % host
        )
    spent = 0
    robots_txt = ""
    try:
        status, body = fetch("https://%s/robots.txt" % host)
        spent += 1
    except Exception as exc:  # noqa: BLE001 — unreadable ⇒ fail-closed skip
        raise RobotsUnreadableError(
            "robots.txt UNREADABLE for %s (fetch failed: %s) — fail-closed "
            "ruling 2026-08-31: host skipped" % (host, exc)
        ) from exc
    if status == 200:
        # Readable. A non-str/empty body is readable-but-unparseable ⇒
        # allow-all (RFC 9309 sec 2.3.1.3) — that is a property of the BODY,
        # not of the fetch, so it is not the unreadable branch.
        robots_txt = body if isinstance(body, str) else ""
    elif status in (404, 410):
        robots_txt = ""  # no policy published ⇒ allow-all (NOT "unreadable")
    else:
        # 403 / 401 / 429 / 5xx / a WAF challenge / anything else: the policy
        # document itself is walled ⇒ UNREADABLE ⇒ skip the host (fail-closed).
        raise RobotsUnreadableError(
            "robots.txt UNREADABLE for %s (HTTP %s) — fail-closed ruling "
            "2026-08-31: host skipped" % (host, status)
        )

    def allowed(url: str) -> bool:
        return robots_eval.can_fetch(robots_txt, agent, url)

    blocked_any = False
    for template in candidate_search_templates(host, mechanism):
        probe_url = template.replace("{q}", "probe")
        if not allowed(probe_url):
            blocked_any = True
            continue
        if spent >= MAX_PROBE_FETCHES:
            break
        try:
            status, body = fetch(probe_url)
            spent += 1
        except Exception:  # noqa: BLE001
            spent += 1
            continue
        if status == 200 and _looks_like_products(body or ""):
            return SearchDescriptor(
                kind="platform_api",
                url_template=template,
                robots_allowed=True,
                discovered_via="platform_probe",
                resolved_at=_now_iso(),
            )

    home = "https://%s/" % host
    if spent < MAX_PROBE_FETCHES and allowed(home):
        try:
            status, body = fetch(home)
            spent += 1
            if status == 200 and body:
                template = search_form_template(body, home)
                if template:
                    if allowed(template.replace("{q}", "probe")):
                        return SearchDescriptor(
                            kind="onsite_html",
                            url_template=template,
                            robots_allowed=True,
                            discovered_via="homepage_form",
                            resolved_at=_now_iso(),
                        )
                    blocked_any = True
        except Exception as exc:  # noqa: BLE001
            logger.info("[search_descriptor] homepage fetch failed for %s: %s", host, exc)

    if robots_eval.sitemaps(robots_txt) and allowed("https://%s/sitemap.xml" % host):
        # No search surface, but the (already-built, dormant) sitemap channel
        # applies — and robots is the evidence, so no further fetch is spent.
        return SearchDescriptor(
            kind="sitemap",
            url_template="",
            robots_allowed=True,
            discovered_via="robots",
            resolved_at=_now_iso(),
        )
    return SearchDescriptor(
        kind="none",
        url_template="",
        robots_allowed=not blocked_any,
        discovered_via="platform_probe",
        resolved_at=_now_iso(),
    )
