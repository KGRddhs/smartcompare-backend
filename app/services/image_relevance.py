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

INC-I2e GUARD-SHORT-LINE: ``ENABLE_IMAGE_GUARD_SHORT_LINE`` (default OFF, read PER CALL
inside ``check``, so only under the guard) matches a short line: both sides fold the
numero forms (``N 5``, ``No.5``, ``N5`` -> ``no5``); with the brand known a line with no
significant token matches by its one-character tokens (an elision letter only when it is
the whole line) or by an adjacent-pair join (``J'adore`` -> ``jadore``, never with a
brand form); a candidate text adds its own adjacent-pair joins (never across two texts);
a line with nothing to match falls to the fragrance word (fragrances, other) or ``name``.
With an empty brand every significant line token must be covered (a token or a join).
OFF: ``check`` is the base code, byte for byte.

INC-I2b GUARD-WORDS: ``ENABLE_IMAGE_GUARD_WORDS`` (default OFF, read PER CALL inside
``check`` after a passing base verdict, so only under the guard) refuses a title that
names another FORM (body care, a set, a refill, a miniature; reason ``form``) or a
concentration the user did not ask for (a free-standing flanker intense, or a TYPED
concentration the title contradicts; reason ``concentration``). A word the user typed
and a brand form never count. OFF: ``check`` returns ``_check_base``, the base code.

INC-I2c GUARD-RECALL: ``ENABLE_IMAGE_GUARD_RECALL`` (default OFF; read once per
``RelevanceCall`` construction, in ``RelevanceCall.__new__`` and only under the guard,
and once per ``image_service.pick_cache_name``) makes ``RelevanceCall(...)`` build the
recall subclass ``_RecallCall``. With the short-line flag ON, a candidate the base
refused with ``fragrance_word`` for an empty-brand identity gets a second look: it
passes on a RECALL_FRAGRANCE_WORDS word (edc, an Arabic perfume, parfum, toilette or
cologne) of its text or knowledge-graph type, or, for a line of two significant words
or more, on a candidate host that is a perfume shop of the code registry
(``source_router.SOURCE_REGISTRY`` rows whose categories are exactly fragrances, read
as is: no refresh, no I/O). A rescued title naming a home-scent good is refused
``form``; then the words test runs whatever ENABLE_IMAGE_GUARD_WORDS reads. Every other
reason stands. ``check`` and every base method are unchanged; OFF: the base class.

A leaf: module level imports the stdlib, ``category_gate`` (the tokenizer),
``jsonld_widen`` (the image policy) and ``deny_hosts`` (the banned-site match functions)
only; ``price_service`` (the alias groups, the JSON-LD image reader) and
``source_router`` (the code registry of the INC-I2c second look) are imported inside
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
REASONS = (
    "none",
    "scheme",
    "brand",
    "name",
    "fragrance_word",
    "denied",
    "form",
    "concentration",
)
LLM_PICK_TIER = "llm_pick"

#: INC-I2e GUARD-SHORT-LINE (default OFF, read per call inside ``check``).
SHORT_LINE_FLAG_ENV = "ENABLE_IMAGE_GUARD_SHORT_LINE"
#: The elision letters (l', d', j', s', c', n', m'): never a short line token unless the
#: one letter is the whole line once brand forms and the excluded words are removed.
ELISION = frozenset({"l", "d", "j", "s", "c", "n", "m"})
_NUMERO_PREFIX = frozenset({"n", "no", "nr"})
_NUMERO = re.compile(r"n(?:o|r)?([0-9]+)")
_WHOLE_LINE_DROP = STOP_WORDS | CONCENTRATION_WORDS | FRAGRANCE_WORDS | UNIT_WORDS

#: INC-I2b GUARD-WORDS (default OFF, read per call inside ``check`` after a passing base
#: verdict, so only under the guard) and the shop page image tier A (read by the
#: WooCommerce adapter per match call with a winner).
WORDS_FLAG_ENV = "ENABLE_IMAGE_GUARD_WORDS"
SHOP_PAGE_IMAGE_FLAG_ENV = "ENABLE_SHOP_PAGE_IMAGE"
#: INC-I2b rule 1: a title word naming another FORM of the product (body care, a set,
#: a refill, a miniature). A word the user typed or a brand form never counts. The
#: bare gift / travel words never count alone (I-10): only the joins below.
FORM_WORDS = _fold(
    "deodorant",
    "deodorants",
    "deo",
    "antiperspirant",
    "shower",
    "gel",
    "lotion",
    "balm",
    "aftershave",
    "shave",
    "soap",
    "cream",
    "mist",
    "oil",
    "body",
    "hair",
    "bath",
    "wash",
    "scrub",
    "powder",
    "candle",
    "diffuser",
    _cps(0x0645, 0x0632, 0x064A, 0x0644),
    _cps(0x062C, 0x0644),
    _cps(0x0627, 0x0633, 0x062A, 0x062D, 0x0645, 0x0627, 0x0645),
    _cps(0x0634, 0x0639, 0x0631),
    _cps(0x0644, 0x0648, 0x0634, 0x0646),
    "giftset",
    "set",
    "sets",
    "coffret",
    "kit",
    "bundle",
    "duo",
    "trio",
    _cps(0x0637, 0x0642, 0x0645),
    "refill",
    "refills",
    "recharge",
    "mini",
    "minis",
    "miniature",
    "miniatures",
    "atomiser",
    "atomizer",
    "atomisers",
    "atomizers",
    "purse",
    "vial",
    "vials",
    "sample",
    "samples",
    "decant",
    "decants",
    "rollerball",
    _cps(0x0639, 0x064A, 0x0646, 0x0629),
)
FORM_JOINS = frozenset(
    {
        ("gift", "set"),
        ("gift", "box"),
        ("gift", "pack"),
        ("travel", "size"),
        ("travel", "spray"),
        ("travel", "set"),
        ("travel", "kit"),
    }
)
INTENSE_WORDS = _fold("intense")
#: FIX-1: no longer read; the positional test in ``_conc_scan`` decides (these words
#: are never a flanker slot, so they stay generic). Kept: the guard version text
#: (E19 / E22) names it. The slot words live inside ``_conc_scan`` so they are hashed.
INTENSE_GENERIC_NEXT = _fold("fragrance", "perfume")


def _phrase(text: str) -> Tuple[str, ...]:
    return tuple(_cg.normalize(text))


_AR_EAU = _cps(0x0627, 0x0648)
_AR_PARFUM = _cps(0x0628, 0x0627, 0x0631, 0x0641, 0x0627, 0x0646)
_AR_TOILETTE = _cps(0x062A, 0x0648, 0x0627, 0x0644, 0x064A, 0x062A)
#: INC-I2b rule 2: the concentration phrases (folded), longest first.
CONC_PHRASES: Tuple[Tuple[Tuple[str, ...], str], ...] = tuple(
    sorted(
        (
            (_phrase("extrait de parfum"), "Extrait"),
            (_phrase("parfum intense"), "Parfum Intense"),
            (_phrase("eau de parfum"), "EDP"),
            (_phrase("eau de toilette"), "EDT"),
            (_phrase("eau de cologne"), "EDC"),
            (_phrase("eau fraiche"), "Eau Fraiche"),
            (_phrase("edp"), "EDP"),
            (_phrase("edt"), "EDT"),
            (_phrase("edc"), "EDC"),
            (_phrase("extrait"), "Extrait"),
            (_phrase("elixir"), "Elixir"),
            (_phrase("parfum"), "Parfum"),
            (_phrase(_AR_EAU + " " + _cps(0x062F, 0x0648) + " " + _AR_PARFUM), "EDP"),
            (_phrase(_AR_EAU + " " + _cps(0x062F, 0x064A) + " " + _AR_PARFUM), "EDP"),
            (_phrase(_AR_EAU + " " + _cps(0x062F, 0x064A) + " " + _AR_TOILETTE), "EDT"),
            (_phrase(_AR_EAU + " " + _cps(0x062F, 0x0648) + " " + _AR_TOILETTE), "EDT"),
            (_phrase(_AR_PARFUM), "Parfum"),
            (_phrase(_AR_TOILETTE), "EDT"),
            (_phrase(_cps(0x0627, 0x0644, 0x0643, 0x0633, 0x064A, 0x0631)), "Elixir"),
            (
                _phrase(_cps(0x0627, 0x0643, 0x0633, 0x062A, 0x0631, 0x064A, 0x062A)),
                "Extrait",
            ),
        ),
        key=lambda p: -len(p[0]),
    )
)
#: I-13: Extrait and Parfum are one class for rule 2(b).
CONC_CLASS = {"Extrait": "Parfum"}
#: The shopping thumbnail tier (never in TIERS: it never reaches [IMG_RELEVANCE]).
SHOPPING_TIER = "shopping"

#: INC-I2c GUARD-RECALL (default OFF; read once per RelevanceCall construction, only
#: under the guard, and once per pick_cache_name).
RECALL_FLAG_ENV = "ENABLE_IMAGE_GUARD_RECALL"
#: The base reasons the second look reads again; every other reason stands.
RECALL_REASONS = ("fragrance_word",)
#: R1: words that name a perfume but are not in FRAGRANCE_WORDS: edc, the Arabic
#: parfum and toilette, four Arabic spellings of perfume and two of cologne.
RECALL_FRAGRANCE_WORDS = _fold(
    "edc",
    _AR_PARFUM,
    _AR_TOILETTE,
    _cps(0x0628, 0x064A, 0x0631, 0x0641, 0x064A, 0x0648, 0x0645),
    _cps(0x0628, 0x0631, 0x0641, 0x064A, 0x0648, 0x0645),
    _cps(0x0628, 0x0627, 0x0631, 0x0641, 0x064A, 0x0648, 0x0645),
    _cps(0x0628, 0x0627, 0x0631, 0x0641, 0x0648, 0x0645),
    _cps(0x0643, 0x0648, 0x0644, 0x0648, 0x0646),
    _cps(0x0643, 0x0648, 0x0644, 0x0648, 0x0646, 0x064A, 0x0627),
)
#: R3: a perfume shop is a code-registry row whose categories are exactly these; it
#: proves a line of at least RECALL_SHOP_MIN_WORDS significant words.
RECALL_SHOP_CATEGORIES = (FRAGRANCE_CATEGORY,)
RECALL_SHOP_MIN_WORDS = 2
#: R-4: a RESCUED title naming a home-scent good is refused ``form``: bakhoor and its
#: spellings, incense, burners, charcoal, chips, and the Arabic bakhoor, mabkhar and
#: mabkhara (a burner), fahm (charcoal), dukhoon and mamoul.
RECALL_HOME_WORDS = _fold(
    "bakhoor",
    "bakhour",
    "bukhoor",
    "bukhour",
    "bakhur",
    "bukhur",
    "incense",
    "burner",
    "burners",
    "charcoal",
    "chips",
    _cps(0x0628, 0x062E, 0x0648, 0x0631),
    _cps(0x0645, 0x0628, 0x062E, 0x0631),
    _cps(0x0645, 0x0628, 0x062E, 0x0631, 0x0629),
    _cps(0x0641, 0x062D, 0x0645),
    _cps(0x062F, 0x062E, 0x0648, 0x0646),
    _cps(0x0645, 0x0639, 0x0645, 0x0648, 0x0644),
)
#: R-4: the home-scent word pairs: room spray, linen spray, air freshener (and the
#: Arabic air freshener).
RECALL_HOME_JOINS = frozenset(
    {
        _phrase("room spray"),
        _phrase("linen spray"),
        _phrase("air freshener"),
        _phrase(_cps(0x0645, 0x0639, 0x0637, 0x0631) + " " + _cps(0x062C, 0x0648)),
    }
)
#: R-4: a weight is a number then a gram unit, or the two joined (36g, 500gr, 40gms).
RECALL_GRAM_UNITS = _fold("g", "gm", "gms", "gr", "gram", "grams")
RECALL_WEIGHT = re.compile(r"[0-9]+(?:grams|gram|gms|gm|gr|g)")


# ---------------------------------------------------------------------------
# the flag and the knob (read per call)
# ---------------------------------------------------------------------------
def guard_enabled() -> bool:
    """True iff ``ENABLE_IMAGE_RELEVANCE_GUARD`` is set truthy. Read PER CALL."""
    return os.getenv(FLAG_ENV, "false").strip().lower() in _TRUTHY


def short_line_enabled() -> bool:
    """True iff ``ENABLE_IMAGE_GUARD_SHORT_LINE`` is set truthy. Read PER CALL."""
    return os.getenv(SHORT_LINE_FLAG_ENV, "false").strip().lower() in _TRUTHY


def guard_words_enabled() -> bool:
    """True iff ``ENABLE_IMAGE_GUARD_WORDS`` is set truthy. Read PER CALL."""
    return os.getenv(WORDS_FLAG_ENV, "false").strip().lower() in _TRUTHY


def shop_page_image_enabled() -> bool:
    """True iff ``ENABLE_SHOP_PAGE_IMAGE`` is set truthy. Read PER CALL."""
    return os.getenv(SHOP_PAGE_IMAGE_FLAG_ENV, "false").strip().lower() in _TRUTHY


def recall_enabled() -> bool:
    """True iff ``ENABLE_IMAGE_GUARD_RECALL`` is set truthy. Read once per
    RelevanceCall construction (only under the guard) and once per pick_cache_name."""
    return os.getenv(RECALL_FLAG_ENV, "false").strip().lower() in _TRUTHY


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
    # INC-I2e: the line keys, filled always, READ only with the short-line flag ON.
    line_sig: FrozenSet[str] = frozenset()
    line_short: FrozenSet[str] = frozenset()
    line_pairs: FrozenSet[Tuple[str, str]] = frozenset()
    line_joins: FrozenSet[str] = frozenset()
    # INC-I2b: the query's folded words (product name, line, typed text) and the
    # TYPED concentration labels (I-8), read only with the words flag ON.
    query_words: FrozenSet[str] = frozenset()
    query_conc: FrozenSet[str] = frozenset()


def fold_numero(tokens: Any) -> List[str]:
    """INC-I2e NUMERO FOLD: n / no / nr directly before an all-digit token become ONE
    token "no" + digits; a token n5 / no5 / nr5 becomes "no" + digits. Total."""
    toks = (
        [t for t in tokens if isinstance(t, str)]
        if isinstance(tokens, (list, tuple))
        else []
    )
    out: List[str] = []
    i = 0
    while i < len(toks):
        tok = toks[i]
        if (
            tok in _NUMERO_PREFIX
            and i + 1 < len(toks)
            and _NUMBER.fullmatch(toks[i + 1])
        ):
            out.append("no" + toks[i + 1])
            i += 2
            continue
        m = _NUMERO.fullmatch(tok)
        out.append("no" + m.group(1) if m else tok)
        i += 1
    return out


def _before_unit(toks: List[str]) -> Set[int]:
    return {
        i
        for i, tok in enumerate(toks)
        if _NUMBER.fullmatch(tok) and i + 1 < len(toks) and toks[i + 1] in UNIT_WORDS
    }


def _line_keys(
    line: str, brand_forms: FrozenSet[str]
) -> Tuple[FrozenSet[str], FrozenSet[str], FrozenSet[Tuple[str, str]]]:
    """INC-I2e: (sig2, short2, the joinable pairs) of the folded line."""
    toks = fold_numero(_cg.normalize(line[:TEXT_MAX_CHARS]))
    unit = _before_unit(toks)
    sig: Set[str] = set()
    for i, tok in enumerate(toks):
        if len(tok) < 2 or tok in NAME_EXCLUDE or tok in brand_forms:
            continue
        if SIZE_TOKEN.fullmatch(tok) or i in unit:
            continue
        sig.add(tok)
    rest = [t for t in toks if t not in brand_forms and t not in _WHOLE_LINE_DROP]
    short: Set[str] = set()
    for i, tok in enumerate(toks):
        if len(tok) != 1 or not tok.isalnum() or i in unit:
            continue
        if tok in ELISION and rest != [tok]:
            continue
        short.add(tok)
    pairs: Set[Tuple[str, str]] = set()
    for i in range(len(toks) - 1):
        a, b = toks[i], toks[i + 1]
        if a in brand_forms or b in brand_forms:
            continue
        if SIZE_TOKEN.fullmatch(a) or SIZE_TOKEN.fullmatch(b):
            continue
        if i in unit or (i + 1) in unit:
            continue
        if a in NAME_EXCLUDE and b in NAME_EXCLUDE:
            continue
        pairs.add((a, b))
    return frozenset(sig), frozenset(short), frozenset(pairs)


def _candidate_keys(texts: Any) -> Set[str]:
    """INC-I2e t2: per text, its folded tokens plus its adjacent-pair joins."""
    out: Set[str] = set()
    for text in _seq(texts):
        if isinstance(text, str):
            toks = fold_numero(_cg.normalize(text[:TEXT_MAX_CHARS]))
            out.update(toks)
            out.update(a + b for a, b in zip(toks, toks[1:], strict=False))
    return out


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
    sig2, short2, pairs2 = _line_keys(line, brand_forms)
    typed = rel.get("typed")
    qwords: Set[str] = set()
    for text in (product_name, rel.get("line"), typed):
        if isinstance(text, str):
            qwords.update(fold_numero(_cg.normalize(text[:TEXT_MAX_CHARS])))
    return Identity(
        brand_empty=not tokens,
        brand_forms=brand_forms,
        brand_joined="".join(kept) if tokens else "",
        name_tokens=_line_tokens(line, brand_forms),
        fragrance=category == FRAGRANCE_CATEGORY,
        needs_fragrance_word=category in FRAGRANCE_WORD_CATEGORIES,
        line_sig=sig2,
        line_short=short2,
        line_pairs=pairs2,
        line_joins=frozenset(a + b for a, b in pairs2),
        query_words=frozenset(qwords),
        query_conc=_conc_labels(typed),
    )


def check(
    ident: Identity, texts: Any, hosts: Any = (), fragrance_texts: Any = ()
) -> Optional[str]:
    """None when the candidate passes, else the FIRST failing reason: the base
    verdict (brand, name, fragrance_word), then with ENABLE_IMAGE_GUARD_WORDS ON the
    words of the first text (form, concentration)."""
    reason = _check_base(ident, texts, hosts, fragrance_texts)
    if reason is not None or not guard_words_enabled():
        return reason
    return _words_reason(ident, texts)


def _check_base(
    ident: Identity, texts: Any, hosts: Any = (), fragrance_texts: Any = ()
) -> Optional[str]:
    """None when the candidate's text names the product, else the FIRST failing
    reason: brand, name or fragrance_word. Host labels serve the brand test only; a
    knowledge-graph type (``fragrance_texts``) serves the fragrance-word test only."""
    if short_line_enabled():
        return _check_short_line(ident, texts, hosts, fragrance_texts)
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


def _check_short_line(
    ident: Identity, texts: Any, hosts: Any, fragrance_texts: Any
) -> Optional[str]:
    """INC-I2e: ``check`` with the short-line flag ON (spec section 2 rules 1 and 2)."""
    t2 = _candidate_keys(texts)
    sig, short, joins = ident.line_sig, ident.line_short, ident.line_joins
    if not ident.brand_empty:
        t = _text_tokens(texts)
        h = _host_tokens(hosts)
        if not (ident.brand_forms & (t | h)) and not (
            ident.brand_joined and ident.brand_joined in h
        ):
            return "brand"
        if sig:
            return None if (sig | joins) & t2 else "name"
        if short:
            return None if (short <= t2 or joins & t2) else "name"
        if joins:
            return None if joins & t2 else "name"
        if not ident.needs_fragrance_word:
            return "name"
        if FRAGRANCE_WORDS & (t2 | _text_tokens(fragrance_texts)):
            return None
        return "fragrance_word"
    if sig:
        for tok in sig:
            if tok in t2:
                continue
            if any(
                tok in pair and pair[0] + pair[1] in t2 for pair in ident.line_pairs
            ):
                continue
            return "name"
    elif not short or not short <= t2:
        return "name"
    if ident.needs_fragrance_word and not (
        FRAGRANCE_WORDS & (t2 | _text_tokens(fragrance_texts))
    ):
        return "fragrance_word"
    return None


def _conc_scan(tokens: Any) -> Tuple[FrozenSet[str], bool]:
    """INC-I2b: (the concentration labels, a free-standing intense) of folded tokens.
    One scan, longest phrase first; Extrait folds into Parfum (I-13); an intense right
    after a phrase is part of its label (I-9); a parfum right after an Elixir or an
    Extrait phrase adds nothing. FIX-1: any other intense is free only in a flanker
    slot, i.e. before the end, a phrase, a size or a closed word (spray, for, pour,
    men, women, homme, femme, edition, by); before anything else it is generic."""
    toks = (
        [t for t in tokens if isinstance(t, str)]
        if isinstance(tokens, (list, tuple))
        else []
    )
    labels: Set[str] = set()
    free = False
    prev: Optional[str] = None
    i = 0
    while i < len(toks):
        for phrase, label in CONC_PHRASES:
            width = len(phrase)
            if tuple(toks[i : i + width]) == phrase:
                i += width
                lab = CONC_CLASS.get(label, label)
                if (
                    i < len(toks)
                    and toks[i] in INTENSE_WORDS
                    and not lab.endswith("Intense")
                ):
                    lab += " Intense"
                    i += 1
                if not (label == "Parfum" and prev in ("Elixir", "Extrait")):
                    labels.add(lab)
                prev = label
                break
        else:
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            if toks[i] in INTENSE_WORDS and (
                not nxt
                or any(phrase[0] == nxt for phrase, _lab in CONC_PHRASES)
                or SIZE_TOKEN.fullmatch(nxt)
                or _NUMBER.fullmatch(nxt)
                or nxt
                in {
                    "spray",
                    "for",
                    "pour",
                    "men",
                    "women",
                    "homme",
                    "femme",
                    "edition",
                    "by",
                }
            ):
                free = True
            prev = None
            i += 1
    return frozenset(labels), free


def _conc_labels(text: Any) -> FrozenSet[str]:
    """INC-I2b: the concentration labels of one text (frozenset() for a non-str)."""
    if not isinstance(text, str):
        return frozenset()
    return _conc_scan(fold_numero(_cg.normalize(text[:TEXT_MAX_CHARS])))[0]


def _words_reason(ident: Identity, texts: Any) -> Optional[str]:
    """INC-I2b: the words test of the FIRST text (the title): form, then concentration
    (a free intense the user did not type; a typed concentration the title contradicts;
    FIX-1: with a typed intense, a trailing " Intense" is dropped from every label on
    both sides first, so "Intense EDP" matches "Eau de Parfum Intense").
    None when it passes or when the first text is not a str."""
    seq = _seq(texts)
    title = seq[0] if seq else None
    if not isinstance(title, str):
        return None
    toks = fold_numero(_cg.normalize(title[:TEXT_MAX_CHARS]))
    exempt = ident.query_words | ident.brand_forms
    for tok in toks:
        if tok in FORM_WORDS and tok not in exempt:
            return "form"
    for a, b in zip(toks, toks[1:], strict=False):
        if (a, b) in FORM_JOINS and not (a in exempt and b in exempt):
            return "form"
    labels, free = _conc_scan(toks)
    typed_intense = bool(INTENSE_WORDS & ident.query_words)
    if free and not typed_intense:
        return "concentration"
    typed = ident.query_conc
    if typed_intense:
        labels = frozenset(lab.removesuffix(" Intense") for lab in labels)
        typed = frozenset(lab.removesuffix(" Intense") for lab in typed)
    if typed and labels and not (labels & typed):
        return "concentration"
    return None


def words_reason_for(product_name: Any, title: Any) -> Optional[str]:
    """INC-I2b: the words test of one listing title for ``product_name`` (rule 1 and
    2(a) only: no typed concentration reaches an adapter). Total."""
    return _words_reason(identity(product_name, None), (title,))


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
    brand: Any, line: Any, category: Any, slot: Any, is_vision: Any, typed: Any = None
) -> Dict[str, Any]:
    """The scs seam: ``{"relevance": {...}}`` for a TEXT product under the flag, else
    ``{}`` (flag OFF or a camera product: the base call, byte for byte)."""
    if not guard_enabled():
        return {}
    if is_vision:
        return {}
    rel: Dict[str, Any] = {
        "brand": _str(brand),
        "line": _str(line),
        "category": _str(category),
        "slot": _slot(slot),
    }
    # INC-I2b (I-8): the text the user typed, only with the words flag ON.
    if isinstance(typed, str) and guard_words_enabled():
        rel["typed"] = typed[:TEXT_MAX_CHARS]
    return {"relevance": rel}


# ---------------------------------------------------------------------------
# one guarded cascade call
# ---------------------------------------------------------------------------
class RelevanceCall:
    """The guard state of ONE get_product_image_url call (plain attributes, nothing
    shared). ``n`` counts every image URL the guard tested; the summary names the
    accepted tier, or the tier and reason of the LAST rejection."""

    def __new__(cls, product_name: Any = None, relevance: Any = None) -> RelevanceCall:
        """INC-I2c (the pathlib.Path pattern): with the guard and
        ENABLE_IMAGE_GUARD_RECALL ON, ``RelevanceCall(...)`` builds the recall subclass
        ``_RecallCall``; the switch is read once per construction, only under the guard.
        The defaults let ``copy`` and ``pickle`` call ``cls.__new__(cls)``."""
        if cls is RelevanceCall and guard_enabled() and recall_enabled():
            cls = _RecallCall
        return super().__new__(cls)

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

    def accept_thumb(self, url: Any, *, texts: Any = (), hosts: Any = ()) -> bool:
        """INC-I2b B: a Shopping thumbnail: ``accept`` (the shopping tier), then the
        words test whatever ENABLE_IMAGE_GUARD_WORDS reads (I-12)."""
        if not self.accept(SHOPPING_TIER, url, texts=texts, hosts=hosts):
            return False
        reason = _words_reason(self.ident, texts)
        if reason is None:
            return True
        self.accepted_tier = None
        return self._record(SHOPPING_TIER, reason)

    def summary(self) -> Tuple[str, str, str, int, str]:
        """(product, tier, outcome, candidates, reason) of the one log line."""
        if self.accepted_tier is not None:
            return (self.slot, self.accepted_tier, "accepted", self.n, "none")
        if self.n > 0:
            return (self.slot, self.last_tier, "rejected", self.n, self.last_reason)
        return (self.slot, "none", "none", 0, "none")


# ---------------------------------------------------------------------------
# INC-I2c GUARD-RECALL: the second look (reached only through _RecallCall)
# ---------------------------------------------------------------------------
def _perfume_domains() -> FrozenSet[str]:
    """R3: the hosts of the code-registry rows whose categories are exactly
    RECALL_SHOP_CATEGORIES. ``source_router.SOURCE_REGISTRY`` (built at its import) is
    read as is, never through the merchant-registry memo, so no refresh is scheduled
    and no I/O runs; source_router is imported here (the leaf holds no host). Total:
    frozenset() on any fault."""
    try:
        from app.services import source_router

        domains: Set[str] = set()
        for row in _seq(source_router.SOURCE_REGISTRY):
            categories = tuple(getattr(row, "categories", None) or ())
            host = _host(getattr(row, "domain", None))
            if host and categories == RECALL_SHOP_CATEGORIES:
                domains.add(host)
        return frozenset(domains)
    except Exception:  # noqa: BLE001 - a total function: no perfume shop
        return frozenset()


def _perfume_shop(hosts: Any) -> bool:
    """R3: True when a candidate host is a perfume-shop host or one of its subdomains
    (never its parent). The registry is read once, and only when there is a host."""
    candidates = [host for host in map(_host, _seq(hosts)) if host]
    if not candidates:
        return False
    domains = _perfume_domains()
    return any(
        host == domain or host.endswith("." + domain)
        for host in candidates
        for domain in domains
    )


def _recall_reason(
    ident: Identity,
    texts: Any,
    hosts: Any,
    fragrance_texts: Any,
    reason: Optional[str],
) -> Optional[str]:
    """INC-I2c: the second look at a base refusal ``reason``. An empty-brand
    RECALL_REASONS refusal with the short-line flag ON is rescued (None) by R1, a
    RECALL_FRAGRANCE_WORDS word of the texts or of a knowledge-graph type, or by R3,
    RECALL_SHOP_MIN_WORDS significant line words and a perfume-shop host. Any other
    reason, and a refusal neither rule rescues, is returned as is."""
    if (
        reason not in RECALL_REASONS
        or not ident.brand_empty
        or not short_line_enabled()
    ):
        return reason
    words = _candidate_keys(texts) | _text_tokens(fragrance_texts)
    if RECALL_FRAGRANCE_WORDS & words:
        return None
    if len(ident.line_sig) >= RECALL_SHOP_MIN_WORDS and _perfume_shop(hosts):
        return None
    return reason


def _home_reason(ident: Identity, texts: Any) -> Optional[str]:
    """INC-I2c R-4: ``form`` when the FIRST text (the title) names a home-scent good: a
    RECALL_HOME_WORDS word, a weight (RECALL_WEIGHT, or a number then a
    RECALL_GRAM_UNITS word) or a RECALL_HOME_JOINS pair. A word the user typed and a
    brand form never count; a pair counts unless both of its words are exempt. None
    otherwise or when the first text is not a str."""
    seq = _seq(texts)
    title = seq[0] if seq else None
    if not isinstance(title, str):
        return None
    toks = fold_numero(_cg.normalize(title[:TEXT_MAX_CHARS]))
    exempt = ident.query_words | ident.brand_forms
    for tok in toks:
        if tok in exempt:
            continue
        if tok in RECALL_HOME_WORDS or RECALL_WEIGHT.fullmatch(tok):
            return "form"
    for a, b in zip(toks, toks[1:], strict=False):
        if a in exempt and b in exempt:
            continue
        if (a, b) in RECALL_HOME_JOINS or (
            _NUMBER.fullmatch(a) and b in RECALL_GRAM_UNITS
        ):
            return "form"
    return None


class _RecallCall(RelevanceCall):
    """INC-I2c: ``RelevanceCall`` with the second look, built only by
    ``RelevanceCall.__new__``. ``accept`` and ``_organic_reason`` run the base method
    first and look again only at its RECALL_REASONS refusal (``organic_passes``,
    ``accept_pick`` and ``accept_thumb`` reach the second look through them). A rescued
    candidate takes the home-scent test, then the words test whatever
    ENABLE_IMAGE_GUARD_WORDS reads (the I-12 rule of ``accept_thumb``)."""

    def _second_look(
        self, texts: Any, hosts: Any, fragrance_texts: Any, reason: Optional[str]
    ) -> Optional[str]:
        """The verdict on a RECALL_REASONS refusal: the recall rules, then for a
        rescue the home-scent test and the words test."""
        reason = _recall_reason(self.ident, texts, hosts, fragrance_texts, reason)
        if reason is not None:
            return reason
        return _home_reason(self.ident, texts) or _words_reason(self.ident, texts)

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
        """``RelevanceCall.accept``, then the second look at its RECALL_REASONS
        refusal; the candidate is counted once."""
        if super().accept(
            tier,
            url,
            texts=texts,
            hosts=hosts,
            fragrance_texts=fragrance_texts,
            deny_only_hosts=deny_only_hosts,
            deny_only_texts=deny_only_texts,
        ):
            return True
        if self.last_reason not in RECALL_REASONS:
            return False
        reason = self._second_look(texts, hosts, fragrance_texts, self.last_reason)
        return self._record(tier, reason)

    def _organic_reason(self, item: Dict[str, Any]) -> Optional[str]:
        """``RelevanceCall._organic_reason``, then the second look at its
        RECALL_REASONS refusal (the title and the link host)."""
        reason = super()._organic_reason(item)
        if reason not in RECALL_REASONS:
            return reason
        return self._second_look((item.get("title"),), (item.get("link"),), (), reason)
