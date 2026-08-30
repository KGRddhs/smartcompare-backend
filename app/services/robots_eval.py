"""An RFC 9309-correct ``robots.txt`` evaluator. Pure, offline, total.

WHY THIS EXISTS INSTEAD OF ``urllib.robotparser``. B8 evaluated the cached
``robots.txt`` of 30 real fragrance hosts under both readers and the stdlib
gave the WRONG answer on two of them, in two independent ways. Both are real
files, both are pinned in ``tests/test_search_descriptor_d3.py`` against the
cached bodies, and both fail OPEN in the stdlib — i.e. they make a crawler
fetch a path the site forbade, which is the one direction that must never
happen:

1. **Same-agent groups MUST MERGE** (RFC 9309 sec 2.2.1: "records with the same
   product token are combined"). ``urllib.robotparser`` lets a LATER
   ``User-agent: *`` group OVERWRITE an earlier one. ``scentsplit.com`` ships
   two ``*`` groups; the second does not repeat the first's
   ``Disallow: /search``, so the stdlib reports ``/search?q=`` as ALLOWED when
   it is not. This is not exotic: Yoast, Shopify apps and CDN snippets all
   append a second ``*`` block to a file that already has one.

2. **Agent matching is by PRODUCT TOKEN, not by a prefix of the UA string.**
   The stdlib takes ``useragent.split("/")[0]`` and then asks whether a group's
   agent is a substring of it, so a browser-shaped UA (``Mozilla/5.0 ...`` —
   what ``curl_cffi impersonate="chrome"`` sends) is a "Mozilla" token.
   ``klinq.com`` carries ``User-agent: Mozilla`` / ``Disallow: /``: under a
   browser UA the whole site is off limits, PDPs included, while under a NAMED
   token (``QarenBot``) the permissive ``*`` group applies. MEASURED
   consequence, and it is counter-intuitive enough to be worth stating: klinq
   is MORE crawlable when we identify honestly than when we impersonate.

SCOPE. This module answers one question — "may agent A fetch URL U under this
robots body" — plus "what sitemaps does it publish". It never fetches
anything; the caller supplies the body. It never raises: a junk or empty body
is allow-all, which is what RFC 9309 sec 2.3.1.3 requires of an unparseable
file, and a crawler that crashes on a malformed robots is a crawler that stops.

PATH MATCHING. Longest-match wins, ``*`` is any run of characters, a trailing
``$`` anchors the end (sec 2.2.2), and Allow beats Disallow at equal length
(sec 2.2.2's tie-break). The query string participates in matching, because
``Disallow: /*?add-to-cart=`` is a real and common rule.

BOUNDS. A hostile host can serve a multi-megabyte robots body or a pattern
with hundreds of wildcards; both are bounded here (``MAX_ROBOTS_CHARS``,
``MAX_PATTERN_CHARS``, ``MAX_RULES``) so an evaluation is O(small) no matter
what arrives on the wire.
"""
from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple
from urllib.parse import urlparse

__all__ = [
    "NAMED_AGENT",
    "MAX_ROBOTS_CHARS",
    "can_fetch",
    "parse_groups",
    "sitemaps",
]

#: The product token we identify as. B8 probed its whole panel under it, and
#: the klinq.com finding above is the reason it is a NAME and not a browser UA.
NAMED_AGENT = "QarenBot"

#: The largest robots body considered. The biggest on B8's panel was 22,664
#: bytes (h3jssz.zid.store); 512 KB is ~23x headroom and bounds a hostile file.
MAX_ROBOTS_CHARS = 512_000
#: A single rule pattern longer than this is ignored rather than compiled.
MAX_PATTERN_CHARS = 2_048
#: Upper bound on rules kept from one file.
MAX_RULES = 4_000

_Group = Tuple[frozenset, List[Tuple[bool, str]]]


def _clean_lines(txt: object) -> List[str]:
    if not isinstance(txt, str):
        return []
    return txt[:MAX_ROBOTS_CHARS].splitlines()


def parse_groups(txt: object) -> List[_Group]:
    """Parse a robots body into ``[(agents, [(is_allow, pattern), ...]), ...]``.

    Consecutive ``User-agent`` lines share one rule block (sec 2.2.1). A
    ``User-agent`` line that follows a rule line STARTS a new record — the
    grouping ``can_fetch`` then merges across, which is bug (1) above.
    """
    groups: List[_Group] = []
    agents: set = set()
    rules: List[Tuple[bool, str]] = []
    total = 0
    for raw in _clean_lines(txt):
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if rules:
                groups.append((frozenset(agents), rules))
                agents, rules = set(), []
            if value:
                agents.add(value.lower())
        elif key in ("allow", "disallow"):
            if not agents:
                continue  # a rule with no group above it is not addressed to anyone
            if len(value) > MAX_PATTERN_CHARS or total >= MAX_RULES:
                continue
            # An EMPTY `Disallow:` means "nothing is disallowed" and is kept as
            # a rule that matches nothing (`_match_len` returns -1 for "").
            rules.append((key == "allow", value))
            total += 1
    if agents:
        groups.append((frozenset(agents), rules))
    return groups


def sitemaps(txt: object) -> List[str]:
    """Every ``Sitemap:`` URL, in file order. Group-independent (sec 2.2.4)."""
    out: List[str] = []
    for raw in _clean_lines(txt):
        line = raw.split("#", 1)[0].strip()
        if not line.lower().startswith("sitemap:"):
            continue
        value = line.partition(":")[2].strip()
        if value and value not in out:
            out.append(value)
    return out


_RX_CACHE: Dict[str, "re.Pattern"] = {}


def _compile(pattern: str) -> "re.Pattern":
    cached = _RX_CACHE.get(pattern)
    if cached is not None:
        return cached
    out = []
    for i, ch in enumerate(pattern):
        if ch == "*":
            out.append(".*")
        elif ch == "$" and i == len(pattern) - 1:
            out.append("$")
        else:
            out.append(re.escape(ch))
    rx = re.compile("".join(out))
    if len(_RX_CACHE) < 4_000:
        _RX_CACHE[pattern] = rx
    return rx


def _match_len(pattern: str, path: str) -> int:
    """``len(pattern)`` when it matches ``path`` from the start, else ``-1``.

    Pattern length is the RFC's specificity measure, so the longest matching
    rule wins regardless of the order it appears in the file.
    """
    if not pattern:
        return -1
    try:
        return len(pattern) if _compile(pattern).match(path) else -1
    except re.error:  # noqa: PERF203 — a pathological pattern is simply ignored
        return -1


def _rules_for_agent(groups: Sequence[_Group], agent: str) -> List[Tuple[bool, str]]:
    """The MERGED rule list addressed to ``agent``.

    The most specific matching product token wins (longest token that occurs in
    the agent string); every group carrying that token contributes its rules.
    With no named match, every ``*`` group contributes — that MERGE is bug (1).
    """
    low = (agent or "").lower()
    best_token = None
    for tokens, _ in groups:
        for token in tokens:
            if token == "*":
                continue
            if token in low and (best_token is None or len(token) > len(best_token)):
                best_token = token
    rules: List[Tuple[bool, str]] = []
    for tokens, group_rules in groups:
        if best_token is not None:
            if best_token in tokens:
                rules.extend(group_rules)
        elif "*" in tokens:
            rules.extend(group_rules)
    return rules


def can_fetch(robots_txt: object, agent: str, url: str) -> bool:
    """True iff ``agent`` may fetch ``url`` under ``robots_txt``.

    Fails OPEN on an empty/unparseable body (RFC 9309 sec 2.3.1.3) and on any
    internal error — but note that "open" here is only ever reached when there
    are no applicable rules at all; a body that HAS rules is evaluated, and the
    two stdlib bugs above are exactly the cases where it wrongly failed open.
    """
    try:
        groups = parse_groups(robots_txt)
        if not groups:
            return True
        rules = _rules_for_agent(groups, agent)
        if not rules:
            return True
        parsed = urlparse(url if "://" in str(url) else "//" + str(url))
        path = parsed.path or "/"
        if parsed.query:
            path = path + "?" + parsed.query
        best_len, best_allow = 0, True
        for is_allow, pattern in rules:
            n = _match_len(pattern, path)
            if n > best_len or (n == best_len and n > 0 and is_allow):
                best_len, best_allow = n, is_allow
        return best_allow
    except Exception:  # noqa: BLE001 — a robots reader must never be the crash
        return True
