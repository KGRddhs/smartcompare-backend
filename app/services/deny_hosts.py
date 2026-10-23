"""The ONE banned-host list (D03 DENY-AND-GUARDS, ``ENABLE_DATA_GUARDS_V2``).

HOUSE RULE. Fragrantica, Parfumo and Basenotes are banned sources: their
robots.txt files disallow our agents by name, Parfumo served decoy pages when
probed, and no licence covers their data. ``fimgs.net`` (the Fragrantica image
CDN) is denied for images. robots stays fail-closed. A denied host is never
fetched, scored, rated, quoted or shown by any path that consults this module.

This module holds the two deny literal tuples, ``DENY_HOSTS`` and the
re-exported ``LEGACY_DESCRIPTOR_DENY_HOSTS``; no other deny literal list exists
in ``app/`` (pinned by the D03 RED file, row R1i, which scans every module but
this one). ``DENY_HOSTS`` holds bare registrable domains only (no scheme, no
``www.``, no port), so the T7b legal-manifest scan, which looks for scheme
literals, sees nothing here. The 26 entries are the documented list: Fragrantica and the 20
language editions measured in the held corpora, Parfumo .com / .de, Basenotes
.com / .net and the Fragrantica image CDN.

MATCHING (ruling C10, gate rulings GC-1..GC-3). A host is denied when

  1. it equals a ``DENY_HOSTS`` entry or is a subdomain of one (the suffix
     arm; behaviourally redundant under rule 2, kept on purpose as defence in
     depth so a bug in the label heuristic can never reopen a listed host), or
  2. its REGISTRABLE LABEL is one of ``DENY_LABELS`` with ANY public suffix,
     so an unlisted edition (``fragrantica.cn``, ``parfumo.it``) is denied
     without a list edit. The registrable label is the second-to-last label,
     or the third-to-last when the top-level label has two letters and the
     second level is a common generic second level (``com``, ``co``, ``net``,
     ``org``, ``ac``, ``gov``, ``edu``, ``or``, ``ne``, ``go``). Stated limit:
     exotic multi-label public suffixes are not recognised by this stdlib
     heuristic; the 26-host tuple still catches the listed hosts by suffix.

FLAG. The match functions are pure and flag-FREE. The flag is read PER CALL at
each consumer site (``source_router``, ``rating_service``,
``search_descriptor_service``, ``image_service``, ``review_service``,
``price_service``, ``structured_comparison_service``): the flag read precedes
every behavioural branch (a pure base precondition, such as an empty-input
check, may run first), so flag OFF reads no other state. The KB-writer
guard (``kb_source_allowed`` / ``assert_kb_source_allowed``) is flag-free on
purpose: the KB units call it unconditionally behind their own flags.

This module is a stdlib-only leaf (no ``app.*`` import), so every service can
import it at module top without an import cycle. Every function here never
raises on any input.
"""

from __future__ import annotations

import os
import re
from typing import Any, FrozenSet, Tuple
from urllib.parse import urlsplit

#: The documented banned registrable domains (lower case, bare host names).
DENY_HOSTS: Tuple[str, ...] = (
    "fragrantica.com",
    "fragrantica.asia",
    "fragrantica.co.il",
    "fragrantica.com.br",
    "fragrantica.cz",
    "fragrantica.de",
    "fragrantica.es",
    "fragrantica.fr",
    "fragrantica.gr",
    "fragrantica.hu",
    "fragrantica.it",
    "fragrantica.jp",
    "fragrantica.kr",
    "fragrantica.mn",
    "fragrantica.nl",
    "fragrantica.pl",
    "fragrantica.ro",
    "fragrantica.ru",
    "fragrantica.se",
    "fragrantica.tr",
    "fragrantica.ua",
    "parfumo.com",
    "parfumo.de",
    "basenotes.com",
    "basenotes.net",
    "fimgs.net",
)

#: The registrable labels of the banned sites (ruling C10): a host whose
#: registrable label is one of these is denied with any public suffix, and a
#: source NAME ("Fragrantica", "Parfumo.de") carrying one as a whole token is
#: a denied source.
DENY_LABELS: FrozenSet[str] = frozenset(
    {"fragrantica", "parfumo", "basenotes", "fimgs"}
)

#: The search descriptor's base deny list, moved here verbatim (value and
#: object identity) so ``search_descriptor_service.DENY_HOSTS`` is byte-identical
#: with the flag OFF.
LEGACY_DESCRIPTOR_DENY_HOSTS: Tuple[str, ...] = ("fragrantica.com", "parfumo.com")

# Common generic second levels under a two-letter country top-level label
# (``com.br``, ``co.il``, ``co.uk`` ...): the registrable label is then the
# third-to-last label (gate ruling GC-3).
_GENERIC_SECOND_LEVELS: FrozenSet[str] = frozenset(
    {"com", "co", "net", "org", "ac", "gov", "edu", "or", "ne", "go"}
)

# A banned label as a whole token inside free text (a rating source name).
_LABEL_TOKEN_RE = re.compile(
    r"(?<![a-z0-9])(?:" + "|".join(sorted(DENY_LABELS)) + r")(?![a-z0-9])"
)

_TRUTHY = ("true", "1", "yes", "on")

# The backslash, spelled by its code point (fix-round ruling F1-4).
_BACKSLASH = chr(92)


def data_guards_v2_enabled() -> bool:
    """True iff ``ENABLE_DATA_GUARDS_V2`` is set truthy. Read PER CALL."""
    return os.getenv("ENABLE_DATA_GUARDS_V2", "false").strip().lower() in _TRUTHY


def normalize_host(value: Any) -> str:
    """Lower-case bare host for matching; ``""`` for a non-str.

    Strips whitespace, lower-cases, drops a ``:port`` suffix, drops trailing
    dots and ONE leading ``www.``. Never raises.
    """
    if not isinstance(value, str):
        return ""
    h = value.strip().lower()
    head, sep, tail = h.rpartition(":")
    if sep and tail.isdigit():
        h = head
    h = h.rstrip(".")
    if h.startswith("www."):
        h = h[4:]
    return h


def _registrable_label(host: str) -> str:
    labels = host.split(".")
    if len(labels) < 2:
        return ""
    if (
        len(labels) >= 3
        and len(labels[-1]) == 2
        and labels[-2] in _GENERIC_SECOND_LEVELS
    ):
        return labels[-3]
    return labels[-2]


def is_denied_host(host: Any) -> bool:
    """True iff ``host`` is a banned host (module docstring, MATCHING).

    Flag-free, pure, never raises: ``notfragrantica.com`` and
    ``fragrantica.com.evil.test`` are False, ``fr.fragrantica.com`` and
    ``fragrantica.cn`` are True.
    """
    h = normalize_host(host)
    if not h:
        return False
    # Rule 1, the suffix arm (defence in depth, gate ruling GC-2).
    for d in DENY_HOSTS:
        if h == d or h.endswith("." + d):
            return True
    # Rule 2, the registrable label (ruling C10).
    return _registrable_label(h) in DENY_LABELS


def is_denied_url(url: Any) -> bool:
    """True iff the host of ``url`` is a banned host.

    The decision reads the parsed HOSTNAME (``urlsplit().hostname``:
    lower-cased, userinfo and port removed), never the netloc. A
    protocol-relative ``//host/x`` and a schemeless ``host/x`` are read as
    ``//host/x``. An authority carrying a backslash is one a WHATWG parser
    (a browser, an image loader) reads differently (the backslash ends the
    authority there), so it is denied conservatively when a banned label
    appears in that authority anywhere (fix-round ruling F1-4); a label in the
    path, the query or the fragment is never a host. A non-str, an empty
    string or a value ``urlsplit`` rejects is False. Flag-free, never raises.
    """
    if not isinstance(url, str):
        return False
    s = url.strip()
    if not s:
        return False
    if "://" not in s and not s.startswith("//"):
        s = "//" + s
    try:
        parts = urlsplit(s)
        host = parts.hostname
    except ValueError:
        return False
    if _BACKSLASH in parts.netloc and _LABEL_TOKEN_RE.search(parts.netloc.casefold()):
        return True
    return is_denied_host(host or "")


def is_denied_source(value: Any) -> bool:
    """True iff ``value`` (a URL, a host or a source NAME) names a banned site.

    A source name is denied when it carries a banned label as a whole token
    ("Fragrantica", "Parfumo.de" True; "Notfragrantica" False). Flag-free,
    never raises.
    """
    if not isinstance(value, str) or not value.strip():
        return False
    if is_denied_url(value) or is_denied_host(value):
        return True
    return _LABEL_TOKEN_RE.search(value.casefold()) is not None


class DeniedSourceError(ValueError):
    """Raised by ``assert_kb_source_allowed``; the message is the constant
    ``"denied source"`` (never the refused value)."""


def kb_source_allowed(value: Any) -> bool:
    """Flag-FREE KB-writer guard: False iff ``value`` names a banned site.

    ``None`` and ``""`` are allowed (whether provenance must be present is the
    writer's own rule).
    """
    return not is_denied_source(value)


def assert_kb_source_allowed(value: Any) -> None:
    """Raise ``DeniedSourceError`` when ``value`` names a banned site."""
    if not kb_source_allowed(value):
        raise DeniedSourceError("denied source")


__all__ = [
    "DENY_HOSTS",
    "DENY_LABELS",
    "LEGACY_DESCRIPTOR_DENY_HOSTS",
    "DeniedSourceError",
    "assert_kb_source_allowed",
    "data_guards_v2_enabled",
    "is_denied_host",
    "is_denied_source",
    "is_denied_url",
    "kb_source_allowed",
    "normalize_host",
]
