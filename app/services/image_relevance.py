"""INC-I1 PICTURE-MUST-MATCH: the relevance guard of the text-compare picture cascade.

Dark behind ``ENABLE_IMAGE_RELEVANCE_GUARD`` (default OFF, read PER CALL) with the knob
``IMAGE_RELEVANCE_CANDIDATES`` (5; a finite value is truncated and clamped to 1..10;
unset, blank, garbage, inf and nan fall back to 5). With the flag ON,
``image_service.get_product_image_url`` accepts a picture of a TEXT compare only when

1. no deny channel names a banned site: the image URL, the link or domain host, the
   source or title text (``deny_hosts.is_denied_url`` / ``is_denied_source``, the
   flag-free match functions, so the deny holds in every ``ENABLE_DATA_GUARDS_V2``
   state; reason ``denied``), and
2. its URL is https (reason ``scheme``), and
3. the text that came with it names the product (``check``):

   * brand known: a brand token (the title or source text, or the registrable label of
     the link / domain host; alias-folded) AND at least one significant line token of
     the text (reasons ``brand``, ``name``);
   * brand empty: EVERY significant line token in the text (``name``) and, for the
     categories fragrances and other (an empty or non-string category reads as other),
     a fragrance word of the text or of a knowledge-graph type (``fragrance_word``).

Host labels prove the brand only, never the line; a knowledge-graph type supplies the
fragrance word only. ``first_https_raster`` is the noon adapter's seam: the first member
of a Product JSON-LD ``image`` that passes ``jsonld_widen.allowed_image_url`` with itself
as the page (https, a public host, a raster path, never a banned host).

A leaf: module level imports the stdlib, ``category_gate`` (the tokenizer),
``jsonld_widen`` (the image policy) and ``deny_hosts`` (the banned-site match functions)
only; ``price_service`` (the alias groups, the JSON-LD image reader) is imported inside
functions. No logger, no I/O, no host literal. Every public function is pure and total:
it never raises.
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple
from urllib.parse import urlsplit

from app.services import category_gate as _cg
from app.services import deny_hosts as _dh
from app.services import jsonld_widen as _jw

FLAG_ENV = "ENABLE_IMAGE_RELEVANCE_GUARD"
KNOB_ENV = "IMAGE_RELEVANCE_CANDIDATES"
KNOB_DEFAULT = 5
KNOB_MIN = 1
KNOB_MAX = 10
_TRUTHY = ("true", "1", "yes", "on")

#: The canonical category keys (extraction_service.canonicalize_category).
FRAGRANCE_CATEGORY = "fragrances"
OTHER_CATEGORY = "other"
#: I1-R2: with an empty brand the fragrance word is required for these only.
FRAGRANCE_WORD_CATEGORIES = (FRAGRANCE_CATEGORY, OTHER_CATEGORY)


def _cps(*code_points: int) -> str:
    return "".join(chr(cp) for cp in code_points)


def _fold(*words: str) -> FrozenSet[str]:
    """Each word folded with the tokenizer both sides of every comparison use."""
    out: Set[str] = set()
    for word in words:
        out.update(_cg.normalize(word))
    return frozenset(out)


# The Arabic word for perfume and its plural (I1-R12), built from code points.
_AR_PERFUME = _cps(0x0639, 0x0637, 0x0631)
_AR_PERFUMES = _cps(0x0639, 0x0637, 0x0648, 0x0631)

FRAGRANCE_WORDS = _fold(
    "perfume",
    "parfum",
    "eau",
    "edt",
    "edp",
    "cologne",
    "fragrance",
    "perfumes",
    "parfums",
    "fragrances",
    "colognes",
    _AR_PERFUME,
    _AR_PERFUMES,
)
CONCENTRATION_WORDS = _fold(
    "eau",
    "de",
    "parfum",
    "parfums",
    "toilette",
    "cologne",
    "extrait",
    "elixir",
    "fraiche",
    "edp",
    "edt",
    "edc",
    _cps(0x0623, 0x0648),
    _cps(0x062F, 0x0648),
    _cps(0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646),
    _cps(0x062A, 0x0648, 0x0627, 0x0644, 0x064A, 0x062A),
)
STOP_WORDS = _fold(
    "the",
    "a",
    "an",
    "and",
    "of",
    "for",
    "by",
    "with",
    "in",
    "on",
    "at",
    "to",
    "de",
    "du",
    "des",
    "la",
    "le",
    "les",
    "el",
    "al",
    "di",
    "da",
    "del",
    "pour",
    "et",
)
BRAND_NOISE = _fold("maison", "parfums", "perfumes", "house")
#: Compared with the brand's folded tokens joined without spaces.
PLACEHOLDER_BRANDS = frozenset(
    {
        "unknown",
        "generic",
        "brand",
        "na",
        "none",
        "null",
        "unbranded",
        "nobrand",
        "other",
    }
)
BRAND_EXCLUDE = STOP_WORDS | FRAGRANCE_WORDS | CONCENTRATION_WORDS | BRAND_NOISE
#: I1-R4 (c): a size unit is never a line token, nor is a number directly before one
#: ("100 ml" spaced; "100ml" attached is SIZE_TOKEN). The tokenizer splits on ".".
UNIT_WORDS = _fold("ml", "oz", "fl", "g", "gm")
NAME_EXCLUDE = (
    STOP_WORDS | CONCENTRATION_WORDS | FRAGRANCE_WORDS | UNIT_WORDS | _fold("spray")
)
SIZE_TOKEN = re.compile(r"[0-9]+(?:ml|oz|fl|g|gm)")
_NUMBER = re.compile(r"[0-9]+")
#: I1-R18: the one alias group the repository lacks, kept LOCAL to this leaf (the
#: price_service groups drive the price fences and stay unchanged).
EXTRA_ALIAS_GROUPS = (frozenset({"bvlgari", "bulgari"}),)

TEXT_MAX_CHARS = 512
SEARCH_ITEMS_MAX = 20
TIER3_ORGANIC_MAX = 10
JSONLD_IMAGES_MAX = 10
_HTTPS = "https://"

#: The closed vocabularies of the [IMG_RELEVANCE] line (image_service logs it).
TIERS = ("none", "piggyback", "search_payload", "serper_images", "llm_pick")
OUTCOMES = ("accepted", "rejected", "none")
REASONS = ("none", "scheme", "brand", "name", "fragrance_word", "denied")
LLM_PICK_TIER = "llm_pick"


# ---------------------------------------------------------------------------
# the flag and the knob (read per call)
# ---------------------------------------------------------------------------
def guard_enabled() -> bool:
    """True iff ``ENABLE_IMAGE_RELEVANCE_GUARD`` is set truthy. Read PER CALL."""
    return os.getenv(FLAG_ENV, "false").strip().lower() in _TRUTHY


def candidates_knob() -> int:
    """``IMAGE_RELEVANCE_CANDIDATES``, read per call (I1-R7): a finite value is
    truncated and clamped to 1..10; unset, blank, garbage, inf and nan give 5."""
    raw = os.getenv(KNOB_ENV)
    if raw is None:
        return KNOB_DEFAULT
    try:
        value = float(raw.strip())
    except (TypeError, ValueError):
        return KNOB_DEFAULT
    if not math.isfinite(value):
        return KNOB_DEFAULT
    if value < KNOB_MIN:
        return KNOB_MIN
    return min(int(value), KNOB_MAX)


def alias_groups() -> Tuple[FrozenSet[str], ...]:
    """The repository's brand alias groups plus the local {bvlgari, bulgari}."""
    try:
        from app.services.price_service import _BRAND_ALIAS_GROUPS

        return tuple(_BRAND_ALIAS_GROUPS) + EXTRA_ALIAS_GROUPS
    except Exception:  # noqa: BLE001 - a total function: the local group alone
        return EXTRA_ALIAS_GROUPS


# ---------------------------------------------------------------------------
# small total helpers
# ---------------------------------------------------------------------------
def _str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _slot(value: Any) -> Optional[int]:
    """The product slot 0 or 1 (an int, never a bool); None for anything else."""
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return value
    return None


def _seq(values: Any) -> Tuple[Any, ...]:
    """A tuple of the given values: a lone str is one value; a non-sequence none."""
    if isinstance(values, str):
        return (values,)
    if isinstance(values, (list, tuple)):
        return tuple(values)
    return ()


def dict_items(values: Any, cap: int) -> List[Dict[str, Any]]:
    """The dict members of ``values[:cap]`` (a list or tuple); [] otherwise."""
    if not isinstance(values, (list, tuple)):
        return []
    return [item for item in values[:cap] if isinstance(item, dict)]


def _category(value: Any) -> str:
    """The canonical category key; an empty or non-string value reads as other."""
    if isinstance(value, str):
        key = value.strip().lower()
        if key:
            return key
    return OTHER_CATEGORY


def _host(value: Any) -> str:
    """The lower-cased host of a URL or of a bare host name; "" for a non-str, a blank
    or an unparsable value. A trailing dot and one leading ``www.`` are removed."""
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text:
        return ""
    if "://" not in text and not text.startswith("//"):
        text = "//" + text
    try:
        host = urlsplit(text).hostname or ""
    except ValueError:
        return ""
    host = host.rstrip(".")
    return host[4:] if host.startswith("www.") else host


def _host_tokens(hosts: Any) -> Set[str]:
    """I1-R4 (a): the tokens of each host's REGISTRABLE label only (no TLD, no www),
    by the repository's one registrable-label rule (deny_hosts, ruling C10)."""
    out: Set[str] = set()
    for value in _seq(hosts):
        label = _dh._registrable_label(_host(value))
        if label:
            out.update(_cg.normalize(label))
    return out


def _text_tokens(texts: Any) -> Set[str]:
    out: Set[str] = set()
    for text in _seq(texts):
        if isinstance(text, str):
            out.update(_cg.normalize(text[:TEXT_MAX_CHARS]))
    return out


def _https(url: Any) -> bool:
    return isinstance(url, str) and url.startswith(_HTTPS)


def _raster_path(url: str) -> bool:
    """I1-R10: a raster extension (the repository's set) on the URL PATH."""
    try:
        path = urlsplit(url).path or ""
    except ValueError:
        return False
    return path.lower().endswith(_jw.RASTER_EXTENSIONS)


def _related(a: str, b: str) -> bool:
    """Two hosts are related when equal or one is a subdomain of the other."""
    if not a or not b:
        return False
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def _denied(url: Any = None, hosts: Any = (), texts: Any = ()) -> bool:
    """I1-R1: an image URL or a link / domain host on a banned host, or a source or
    title text naming a banned site. The flag-free deny_hosts match functions only."""
    if _dh.is_denied_url(url):
        return True
    if any(_dh.is_denied_url(value) for value in _seq(hosts)):
        return True
    return any(_dh.is_denied_source(value) for value in _seq(texts))


# ---------------------------------------------------------------------------
# the identity and the test
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Identity:
    """The folded identity of one product (built once per cascade call)."""

    brand_empty: bool
    brand_forms: FrozenSet[str]
    brand_joined: str
    name_tokens: FrozenSet[str]
    fragrance: bool
    needs_fragrance_word: bool


def _line_tokens(line: str, brand_forms: FrozenSet[str]) -> FrozenSet[str]:
    """The significant line tokens: stop, concentration, fragrance and unit words, a
    size token, a number directly before a unit and the brand's own forms never count.
    """
    toks = _cg.normalize(line[:TEXT_MAX_CHARS])
    out: Set[str] = set()
    for i, tok in enumerate(toks):
        if len(tok) < 2 or tok in NAME_EXCLUDE or tok in brand_forms:
            continue
        if SIZE_TOKEN.fullmatch(tok):
            continue
        if _NUMBER.fullmatch(tok) and i + 1 < len(toks) and toks[i + 1] in UNIT_WORDS:
            continue
        out.add(tok)
    return frozenset(out)


def identity(product_name: Any, relevance: Any) -> Identity:
    """The identity of ``relevance`` ({brand, line, category, slot}); a blank or
    non-string line falls back to ``product_name``. Total."""
    rel = relevance if isinstance(relevance, dict) else {}
    brand = _str(rel.get("brand"))
    line = rel.get("line")
    if not (isinstance(line, str) and line.strip()):
        line = _str(product_name)
    category = _category(rel.get("category"))
    folded = _cg.normalize(brand[:TEXT_MAX_CHARS])
    placeholder = "".join(folded) in PLACEHOLDER_BRANDS
    kept = [tok for tok in folded if tok not in BRAND_EXCLUDE]
    tokens = frozenset() if placeholder else frozenset(t for t in kept if len(t) >= 2)
    forms: Set[str] = set(tokens)
    if tokens:
        # I1-R4 (b): a group joins only when the brand's kept tokens are its subset.
        for group in alias_groups():
            if tokens <= group:
                forms |= group
    brand_forms = frozenset(forms)
    return Identity(
        brand_empty=not tokens,
        brand_forms=brand_forms,
        brand_joined="".join(kept) if tokens else "",
        name_tokens=_line_tokens(line, brand_forms),
        fragrance=category == FRAGRANCE_CATEGORY,
        needs_fragrance_word=category in FRAGRANCE_WORD_CATEGORIES,
    )


def check(
    ident: Identity, texts: Any, hosts: Any = (), fragrance_texts: Any = ()
) -> Optional[str]:
    """None when the candidate's text names the product, else the FIRST failing
    reason: brand, name or fragrance_word. Host labels serve the brand test only; a
    knowledge-graph type (``fragrance_texts``) serves the fragrance-word test only."""
    t = _text_tokens(texts)
    if not ident.brand_empty:
        h = _host_tokens(hosts)
        if not (ident.brand_forms & (t | h)) and not (
            ident.brand_joined and ident.brand_joined in h
        ):
            return "brand"
        if not (ident.name_tokens & t):
            return "name"
        return None
    # I1-R3: with an empty brand EVERY significant line token (and at least one).
    if not ident.name_tokens or not ident.name_tokens <= t:
        return "name"
    if ident.needs_fragrance_word and not (
        FRAGRANCE_WORDS & (t | _text_tokens(fragrance_texts))
    ):
        return "fragrance_word"
    return None


def image_query(product_name: Any, ident: Identity) -> str:
    """The Tier-1 query: the full name, plus the word perfume for the fragrance
    category only."""
    name = _str(product_name)
    return name + " perfume" if ident.fragrance else name


def first_https_raster(value: Any) -> Optional[str]:
    """The first member of a schema.org ``image`` (a string, a list, an ImageObject)
    that passes the D08 image policy with itself as the page URL (so only the host
    allowlist is satisfied): https, a public host, a raster path, no banned host."""
    try:
        from app.services.price_service import _jsonld_image_urls

        urls = _jsonld_image_urls(value)
    except Exception:  # noqa: BLE001 - a total function: no picture
        return None
    if not isinstance(urls, list):
        return None
    for url in urls[:JSONLD_IMAGES_MAX]:
        allowed = _jw.allowed_image_url(url, url)
        if allowed:
            return allowed
    return None


def relevance_kwargs(
    brand: Any, line: Any, category: Any, slot: Any, is_vision: Any
) -> Dict[str, Any]:
    """The scs seam: ``{"relevance": {...}}`` for a TEXT product under the flag, else
    ``{}`` (flag OFF or a camera product: the base call, byte for byte)."""
    if not guard_enabled():
        return {}
    if is_vision:
        return {}
    return {
        "relevance": {
            "brand": _str(brand),
            "line": _str(line),
            "category": _str(category),
            "slot": _slot(slot),
        }
    }


# ---------------------------------------------------------------------------
# one guarded cascade call
# ---------------------------------------------------------------------------
class RelevanceCall:
    """The guard state of ONE get_product_image_url call (plain attributes, nothing
    shared). ``n`` counts every image URL the guard tested; the summary names the
    accepted tier, or the tier and reason of the LAST rejection."""

    def __init__(self, product_name: Any, relevance: Any) -> None:
        self.product_name = _str(product_name)
        self.ident = identity(product_name, relevance)
        slot = _slot(relevance.get("slot")) if isinstance(relevance, dict) else None
        self.slot = "-" if slot is None else str(slot)
        self.n = 0
        self.accepted_tier: Optional[str] = None
        self.last_tier = "none"
        self.last_reason = "none"
        self._num: Optional[int] = None

    def query(self) -> str:
        return image_query(self.product_name, self.ident)

    def num(self) -> int:
        """The knob, read ONCE per call (the request size and the walk cap agree)."""
        if self._num is None:
            self._num = candidates_knob()
        return self._num

    def _record(self, tier: str, reason: Optional[str]) -> bool:
        if reason is None:
            self.accepted_tier = tier
            return True
        self.last_tier, self.last_reason = tier, reason
        return False

    def accept(
        self,
        tier: str,
        url: Any,
        *,
        texts: Any = (),
        hosts: Any = (),
        fragrance_texts: Any = (),
        deny_only_hosts: Any = (),
        deny_only_texts: Any = (),
    ) -> bool:
        """One payload or Serper candidate: the deny first (GC-5 Q-5), then https,
        then ``check``. ``deny_only_*`` are channels read by the deny alone."""
        self.n += 1
        if _denied(
            url,
            _seq(hosts) + _seq(deny_only_hosts),
            _seq(texts) + _seq(deny_only_texts),
        ):
            return self._record(tier, "denied")
        if not _https(url):
            return self._record(tier, "scheme")
        return self._record(tier, check(self.ident, texts, hosts, fragrance_texts))

    def accept_scheme(self, tier: str, url: Any) -> bool:
        """The piggyback page image (the priced product's own; no text to test):
        the deny and https only."""
        self.n += 1
        if _denied(url):
            return self._record(tier, "denied")
        if not _https(url):
            return self._record(tier, "scheme")
        return self._record(tier, None)

    def _organic_reason(self, item: Dict[str, Any]) -> Optional[str]:
        title, link = item.get("title"), item.get("link")
        if _denied(None, (link,), (title,)):
            return "denied"
        return check(self.ident, (title,), (link,))

    def organic_passes(self, organic: Any) -> bool:
        """The Tier-3 precondition: some item of ``organic[:10]`` (the model's view)
        passes; a denied item never does. Counts nothing."""
        return any(
            self._organic_reason(item) is None
            for item in dict_items(organic, TIER3_ORGANIC_MAX)
        )

    def accept_pick(self, url: Any, organic: Any) -> bool:
        """The Tier-3 pick: the deny, https and a raster path (else scheme), never an
        organic page link (scheme), and a passing ``organic[:10]`` item on a related
        host; with no related item the empty text decides (brand or name), else the
        first related item's reason."""
        self.n += 1
        if _denied(url):
            return self._record(LLM_PICK_TIER, "denied")
        if not _https(url) or not _raster_path(url):
            return self._record(LLM_PICK_TIER, "scheme")
        items = dict_items(organic, TIER3_ORGANIC_MAX)
        for item in items:
            link = item.get("link")
            if isinstance(link, str) and link.strip() == url:
                return self._record(LLM_PICK_TIER, "scheme")
        pick_host = _host(url)
        related = [i for i in items if _related(pick_host, _host(i.get("link")))]
        if not related:
            return self._record(LLM_PICK_TIER, check(self.ident, (), ()))
        first_reason: Optional[str] = None
        for item in related:
            reason = self._organic_reason(item)
            if reason is None:
                return self._record(LLM_PICK_TIER, None)
            if first_reason is None:
                first_reason = reason
        return self._record(LLM_PICK_TIER, first_reason)

    def summary(self) -> Tuple[str, str, str, int, str]:
        """(product, tier, outcome, candidates, reason) of the one log line."""
        if self.accepted_tier is not None:
            return (self.slot, self.accepted_tier, "accepted", self.n, "none")
        if self.n > 0:
            return (self.slot, self.last_tier, "rejected", self.n, self.last_reason)
        return (self.slot, "none", "none", 0, "none")
