"""S81-10 FRAGRANCE-ONLY-GATE: the fragrance-only category gate.

Flag ``ENABLE_FRAGRANCE_ONLY_GATE`` (default OFF, read PER CALL with the house idiom);
knobs ``REFUSAL_DAILY_BUDGET`` (10, clamped 1..100) and ``FRAGRANCE_LEXICON_PATH``
(``data/fragrance_lexicon.json``, repo-root relative). Under the flag the four user
compare routes (POST / GET ``/api/v1/text/compare``, ``/api/v1/text/compare/stream``,
POST ``/api/v1/image/identify``) compare fragrances only:

* rule 1 (pre-consume, $0): a non-fragrance product-type word of the lexicon with no
  fragrance concentration / form word and no house or note hit is refused with code
  ``CATEGORY_NOT_LIVE`` (HTTP 400) before the preferences read, the budget read and
  the credit consume. A house or note hit beside such a word is no $0 refusal: the
  decision carries ``evidence`` False and the post-resolve decision settles it
  (RULINGS_S81_10 R-S10-4). A term marked ``needs_second_token`` never fires rule 1
  ALONE (GATE_S81_10 GC-5): in the lexicon file the mark is a trailing ``*`` on the
  term text (the frozen schema keeps every term a plain string; ``normalize`` drops
  the mark, so the term's tokens are unchanged);
* the refusal budget (pre-consume): every request that will consume first reads the
  day's refusal counters: the account key always and the S81-05 device key in
  addition when it is bound (R-S10-1); either at the budget -> HTTP 429 with scope
  ``refusal_daily``, never billed; the S81-09 exemptions exempt the budget, never the
  rules (R-S10-7);
* rules 2 and 3 (post-consume, inside the orchestrator right after
  ``_resolve_pair_category`` and before any profile read or fetch): a CHIP-FREE,
  per-product decision. A positive non-fragrance product refuses (the route's existing
  failure arm refunds it and ONE Lua EVAL counts it on both budget keys); ``other``
  proceeds (R-S10-3); a concentration / form word in a product's own name makes it a
  fragrance on the explicit-pair and vision paths (R-S10-5) and the pair is then
  compared as fragrances (GC-1).

The S81-09 dependency sat behind two seams (R-S10-11), collapsed at the rebase onto
the S81-09 merge (RULINGS_REBASE_S81_10 RB10-6): ``reset_window`` delegates to
S81-09's ONE usage calendar (``usage_service._usage_window`` with
``riyadh_reset_enabled`` and ``RIYADH_UTC_OFFSET_HOURS``) and ``budget_exempt_async``
to S81-09's allow-list (``usage_service._device_quota_exempt``), else the premium tier.

Module level is stdlib only; every app import is function-local, so a flag-OFF path
imports nothing new. Log lines carry constants, canonical category keys, route labels
and exception type names only (never a query, a name, a key, an id or a count); no
line is logged at ERROR.
"""
import asyncio
import json
import logging
import math
import os
import threading
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

FLAG_ENV = "ENABLE_FRAGRANCE_ONLY_GATE"
BUDGET_ENV = "REFUSAL_DAILY_BUDGET"
LEXICON_ENV = "FRAGRANCE_LEXICON_PATH"

CODE = "CATEGORY_NOT_LIVE"
CATEGORIES_LIVE = ("fragrances",)
SCOPE_REFUSAL_DAILY = "refusal_daily"
REFUSAL_MESSAGE = "MYEZ compares fragrances for now. Other categories are coming soon."
BUDGET_MESSAGE = "MYEZ compares fragrances for now. The daily limit for other searches is reached."
# Readers and tests only: the two key writers in budget_keys spell their prefixes
# literally, so the migration-043 key census sees the account key (spec C15).
KEY_PREFIX_DEV = "refusal:daily:dev:"
KEY_PREFIX_ACCT = "refusal:daily:acct:"

DEFAULT_BUDGET = 10
MAX_BUDGET = 100
# The key outlives its day by one hour (the S81-04 / S81-09 grace).
KEY_GRACE_SECONDS = 3600
MAX_RETRY_AFTER_SECONDS = 86400

# ONE EVAL increments every budget key of the subject with the same EXPIREAT, so a
# key can never exist without its expiry (an INCR then EXPIREAT pair of calls could
# leave a key with no TTL and lock a device out for good).
REFUSAL_INCR_SCRIPT = (
    "for i = 1, #KEYS do\n"
    "  redis.call('INCR', KEYS[i])\n"
    "  redis.call('EXPIREAT', KEYS[i], ARGV[1])\n"
    "end\n"
    "return #KEYS\n"
)

_FRAGRANCE_GROUPS = ("concentrations", "forms", "houses", "notes")
_TYPE_GROUPS = ("concentrations", "forms")
_NON_FRAGRANCE_GROUPS = (
    "electronics", "grocery", "supplements", "makeup", "skincare", "haircare", "fashion",
)
_POSITIVE_NON_FRAGRANCE = frozenset(_NON_FRAGRANCE_GROUPS)
SECOND_TOKEN_MARK = "*"
_ROUTE_LABELS = ("text.post", "text.get", "text.stream", "image")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LEXICON_PARTS = ("data", "fragrance_lexicon.json")


# ---------------------------------------------------------------------------
# flag and knobs (read per call)
# ---------------------------------------------------------------------------
def fragrance_only_gate_enabled() -> bool:
    """ENABLE_FRAGRANCE_ONLY_GATE, read PER CALL (never cached)."""
    return os.getenv(FLAG_ENV, "false").strip().lower() in ("true", "1", "yes", "on")


def refusal_daily_budget() -> int:
    """REFUSAL_DAILY_BUDGET, read per call: a finite number >= 1 is truncated and
    clamped to MAX_BUDGET; unset, blank, garbage, inf, nan and anything below 1 fall
    back to DEFAULT_BUDGET."""
    raw = os.getenv(BUDGET_ENV)
    if raw is None:
        return DEFAULT_BUDGET
    try:
        value = float(raw.strip())
    except (TypeError, ValueError):
        return DEFAULT_BUDGET
    if not math.isfinite(value) or value < 1:
        return DEFAULT_BUDGET
    return min(int(value), MAX_BUDGET)


def lexicon_path() -> Path:
    """FRAGRANCE_LEXICON_PATH, read per call: unset or blank -> the repo's
    data/fragrance_lexicon.json; a relative value resolves against the repo root."""
    raw = os.getenv(LEXICON_ENV)
    if raw is None or not raw.strip():
        return _REPO_ROOT.joinpath(*_DEFAULT_LEXICON_PARTS)
    candidate = Path(raw.strip())
    return candidate if candidate.is_absolute() else _REPO_ROOT / candidate


# ---------------------------------------------------------------------------
# normalisation (pure)
# ---------------------------------------------------------------------------
def _cps(*code_points: int) -> str:
    return "".join(chr(cp) for cp in code_points)


# Arabic harakat U+064B..U+0652, the superscript alef U+0670 and the tatweel U+0640.
_AR_DROP = frozenset(list(range(0x064B, 0x0653)) + [0x0670, 0x0640])
# Alef forms -> bare alef; ta marbuta -> ha; alef maqsura -> ya.
_AR_FOLD = {0x0622: 0x0627, 0x0623: 0x0627, 0x0625: 0x0627, 0x0629: 0x0647, 0x0649: 0x064A}
# Arabic-Indic and extended Arabic-Indic digits -> ASCII digits.
_DIGIT_FOLD = {**{0x0660 + i: 0x30 + i for i in range(10)},
               **{0x06F0 + i: 0x30 + i for i in range(10)}}
# One leading article per token (wal, bal, kal, fal, lil, al), the longer forms first;
# a bare leading waw is never stripped (a word such as ward, rose, starts with it).
_AR_ARTICLES = (
    _cps(0x0648, 0x0627, 0x0644), _cps(0x0628, 0x0627, 0x0644), _cps(0x0643, 0x0627, 0x0644),
    _cps(0x0641, 0x0627, 0x0644), _cps(0x0644, 0x0644), _cps(0x0627, 0x0644),
)
_MIN_REMAINDER_LETTERS = 2


def _letter_count(text: str) -> int:
    return sum(1 for ch in text if unicodedata.category(ch).startswith("L"))


def _strip_article(token: str) -> str:
    for article in _AR_ARTICLES:
        if token.startswith(article):
            rest = token[len(article):]
            return rest if _letter_count(rest) >= _MIN_REMAINDER_LETTERS else token
    return token


def normalize(text: Any) -> List[str]:
    """Text -> tokens: NFKC; Latin combining marks stripped (NFKD, drop U+0300..U+036F,
    NFKC: so an accented house matches its plain spelling); casefold; Arabic harakat,
    the superscript alef and the tatweel dropped; alef forms, ta marbuta and alef
    maqsura folded; Arabic-Indic digits -> ASCII; any other combining mark dropped;
    every other non-letter, non-digit -> a separator; one leading Arabic article
    stripped per token when at least two letters remain. Terms use the same function."""
    if not isinstance(text, str) or not text:
        return []
    folded = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", text))
    folded = "".join(ch for ch in folded if not 0x0300 <= ord(ch) <= 0x036F)
    folded = unicodedata.normalize("NFKC", folded).casefold()
    chars: List[str] = []
    for ch in folded:
        cp = ord(ch)
        if cp in _AR_DROP:
            continue
        cp = _AR_FOLD.get(cp, cp)
        cp = _DIGIT_FOLD.get(cp, cp)
        ch = chr(cp)
        kind = unicodedata.category(ch)[0]
        if kind in ("L", "N"):
            chars.append(ch)
        elif kind == "M":
            continue
        else:
            chars.append(" ")
    return [_strip_article(token) for token in "".join(chars).split()]


# ---------------------------------------------------------------------------
# the lexicon (cached on (path, mtime_ns, size); fail-safe)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Term:
    tokens: Tuple[str, ...]
    section: str
    group: str
    needs_second_token: bool = False


@dataclass(frozen=True)
class _Lexicon:
    terms: Tuple[_Term, ...] = ()


_EMPTY_LEXICON = _Lexicon()
_LEXICON_LOCK = threading.Lock()
_LEXICON_CACHE = {"key": None, "lexicon": None}
_LEXICON_WARNED: set = set()
_LEXICON_WARNED_CAP = 64


def _reset_lexicon_cache() -> None:
    """Test seam: forget the cached lexicon and the warned states."""
    with _LEXICON_LOCK:
        _LEXICON_CACHE["key"] = None
        _LEXICON_CACHE["lexicon"] = None
        _LEXICON_WARNED.clear()


def _compile_lexicon(raw: Any) -> _Lexicon:
    if not isinstance(raw, dict) or raw.get("version") != 1:
        raise ValueError("lexicon version")
    fragrance = raw.get("fragrance")
    non_fragrance = raw.get("non_fragrance")
    if not isinstance(fragrance, dict) or not isinstance(non_fragrance, dict):
        raise ValueError("lexicon sections")
    terms: List[_Term] = []
    for section, groups, names in (("fragrance", fragrance, _FRAGRANCE_GROUPS),
                                   ("non_fragrance", non_fragrance, _NON_FRAGRANCE_GROUPS)):
        for name in names:
            values = groups.get(name)
            if not isinstance(values, list) or not values:
                raise ValueError("lexicon group")
            for value in values:
                if not isinstance(value, str):
                    raise ValueError("lexicon term")
                tokens = tuple(normalize(value))
                if not tokens:
                    raise ValueError("lexicon term")
                marked = section == "non_fragrance" and value.rstrip().endswith(SECOND_TOKEN_MARK)
                terms.append(_Term(tokens, section, name, marked))
    # Longest first (token count, then characters, then the text) so a longer term
    # masks its sub-terms: "hair mist" (a fragrance form) before "hair" (haircare).
    terms.sort(key=lambda t: (-len(t.tokens), -len(" ".join(t.tokens)), " ".join(t.tokens),
                              t.section, t.group))
    return _Lexicon(tuple(terms))


def _lexicon_unavailable(state: tuple, exc: BaseException) -> _Lexicon:
    with _LEXICON_LOCK:
        if state not in _LEXICON_WARNED:
            if len(_LEXICON_WARNED) >= _LEXICON_WARNED_CAP:
                _LEXICON_WARNED.clear()
            _LEXICON_WARNED.add(state)
            logger.warning("[CATEGORY-GATE] lexicon unavailable type=%s", type(exc).__name__)
    return _EMPTY_LEXICON


def load_lexicon() -> _Lexicon:
    """The compiled lexicon. One os.stat per call; the file is parsed again only
    when its (resolved path, mtime_ns, size) changes. A missing, unreadable, invalid
    or wrongly shaped file is the EMPTY lexicon (no $0 refusal, no evidence) with ONE
    WARNING per file state: the gate fails safe, never into a false refusal."""
    path = lexicon_path()
    try:
        stat = os.stat(path)
    except OSError as exc:
        return _lexicon_unavailable((str(path), None, None), exc)
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    with _LEXICON_LOCK:
        if _LEXICON_CACHE["key"] == key and _LEXICON_CACHE["lexicon"] is not None:
            return _LEXICON_CACHE["lexicon"]
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lexicon = _compile_lexicon(json.load(handle))
    except Exception as exc:  # noqa: BLE001 - fail safe: an unusable file refuses nothing
        lexicon = _lexicon_unavailable(key, exc)
    with _LEXICON_LOCK:
        _LEXICON_CACHE["key"] = key
        _LEXICON_CACHE["lexicon"] = lexicon
    return lexicon


# ---------------------------------------------------------------------------
# scan / evaluate (pure but for the lexicon read)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ScanResult:
    non_fragrance: Tuple[Tuple[str, str], ...]
    fragrance_type: bool
    houses: int
    notes: int
    evidence: bool
    # GC-5: True when the non-fragrance hits can fire rule 1: an unmarked term, or
    # two distinct terms (a needs_second_token term never fires it alone).
    rule1_trigger: bool = False


@dataclass(frozen=True)
class BudgetSubject:
    """The refusal-budget subject: the account id and / or the S81-05 device key.
    Neither value is ever part of a repr, a log line or an exception text."""

    user_id: Optional[str] = field(default=None, repr=False)
    device_key: Optional[str] = field(default=None, repr=False)


@dataclass(frozen=True)
class GateDecision:
    outcome: str
    category: Optional[str]
    evidence: bool
    subject: Optional[BudgetSubject] = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class PostResolveVerdict:
    """The post-resolve decision: ``refused`` is the refused canonical category (None
    = proceed); ``form_override`` is True when a concentration / form word in a
    product's own name made it a fragrance on the explicit-pair or vision path."""

    refused: Optional[str] = None
    form_override: bool = False


def scan(texts: Optional[Iterable[Any]]) -> ScanResult:
    """Every lexicon term matched as whole tokens over the concatenated token stream
    of ``texts``, longest first; a match masks its tokens."""
    lexicon = load_lexicon()
    stream: List[str] = []
    for text in texts or ():
        stream.extend(normalize(text))
    masked = [False] * len(stream)
    positions: dict = {}
    for index, token in enumerate(stream):
        positions.setdefault(token, []).append(index)
    hits: List[Tuple[int, _Term]] = []
    for term in lexicon.terms:
        width = len(term.tokens)
        for start in positions.get(term.tokens[0], ()):
            end = start + width
            if end > len(stream) or any(masked[start:end]):
                continue
            if tuple(stream[start:end]) == term.tokens:
                for index in range(start, end):
                    masked[index] = True
                hits.append((start, term))
    hits.sort(key=lambda hit: hit[0])
    non_terms = [term for _start, term in hits if term.section == "non_fragrance"]
    non_fragrance = tuple((term.group, " ".join(term.tokens)) for term in non_terms)
    fragrance_type = any(term.section == "fragrance" and term.group in _TYPE_GROUPS
                         for _start, term in hits)
    houses = sum(1 for _start, term in hits if term.section == "fragrance" and term.group == "houses")
    notes = len({term.tokens for _start, term in hits
                 if term.section == "fragrance" and term.group == "notes"})
    rule1_trigger = (any(not term.needs_second_token for term in non_terms)
                     or len({term.tokens for term in non_terms}) >= 2)
    blocked = bool(non_fragrance) and not fragrance_type
    evidence = (fragrance_type or houses >= 1 or notes >= 2) and not blocked
    return ScanResult(non_fragrance, fragrance_type, houses, notes, evidence, rule1_trigger)


def kb_evidence(texts: Optional[Iterable[Any]]) -> bool:
    """The KB arm of rule 2: a seam, inert in this unit (no I/O, no match) until
    S81-16 seeds the knowledge base and S81-18 ships the product-card read."""
    return False


def _kb_evidence_safe(texts: Optional[Iterable[Any]]) -> bool:
    try:
        return bool(kb_evidence(texts))
    except Exception as exc:  # noqa: BLE001 - a raising seam fails open (no match)
        logger.warning("[CATEGORY-GATE] kb lookup failed type=%s", type(exc).__name__)
        return False


def evaluate(texts: Optional[Iterable[Any]], *, subject: Optional[BudgetSubject] = None) -> GateDecision:
    """Rule 1 and the rule-2 evidence. ``refuse`` only for a non-fragrance product-type
    word with no concentration / form word and no house or note hit (and not a lone
    needs_second_token term); otherwise ``proceed`` with the evidence (a form or
    concentration word, a house, two distinct notes, or the KB seam; never beside a
    non-fragrance word without a form or concentration word)."""
    result = scan(texts)
    blocked = bool(result.non_fragrance) and not result.fragrance_type
    if blocked and result.rule1_trigger and result.houses == 0 and result.notes == 0:
        return GateDecision("refuse", result.non_fragrance[0][0], False, subject)
    kb = _kb_evidence_safe(texts)
    evidence = (result.fragrance_type or result.houses >= 1 or result.notes >= 2 or kb) and not blocked
    return GateDecision("proceed", None, bool(evidence), subject)


def vision_texts(products: Sequence[Any]) -> List[str]:
    """The camera's gate texts: "<brand> <name>" of the identified products the route
    compares (the first two; one in the single-product exit)."""
    texts = []
    for product in list(products or [])[:2]:
        if isinstance(product, dict):
            texts.append(" ".join(str(product.get(key) or "") for key in ("brand", "name")).strip())
    return texts


# ---------------------------------------------------------------------------
# the refusal budget (two axes, R-S10-1)
# ---------------------------------------------------------------------------
def budget_subject(user: Any) -> Optional[BudgetSubject]:
    """The account id (always, when the caller is signed in) and the S81-05 device key
    (in addition, when the request bound a valid device fingerprint and the device-key
    secret is set). The raw fingerprint never leaves this function."""
    from app.utils import request_context as _request_context

    fingerprint = _request_context.device_fingerprint()
    device_key = _request_context.device_key(fingerprint) if fingerprint else None
    user_id = user.get("id") if isinstance(user, dict) else None
    user_id = user_id if isinstance(user_id, str) and user_id else None
    device_key = device_key if isinstance(device_key, str) and device_key else None
    if user_id is None and device_key is None:
        return None
    return BudgetSubject(user_id=user_id, device_key=device_key)


def budget_keys(subject: Optional[BudgetSubject], day: date) -> List[str]:
    """The subject's counter keys for ``day``: the account key, then the device key."""
    if subject is None:
        return []
    day_txt = day.strftime("%Y-%m-%d")
    keys: List[str] = []
    user_id = subject.user_id
    if user_id:
        keys.append(f"refusal:daily:acct:{user_id}:{day_txt}")
    device_key = subject.device_key
    if device_key:
        keys.append(f"refusal:daily:dev:{device_key}:{day_txt}")
    return keys


def reset_window(now: datetime) -> Tuple[date, datetime, int]:
    """The S81-09 seam, collapsed (RB10-6): ``(day, next_reset, utc_offset_hours)`` =
    S81-09's ONE usage calendar, ``usage_service._usage_window(now)``, and its offset
    (``RIYADH_UTC_OFFSET_HOURS`` under ``riyadh_reset_enabled()``, else 0), so the
    refusal budget and the usage quota never disagree on the day or the reset."""
    from app.services import usage_service as _usage_service

    day, next_reset = _usage_service._usage_window(now)
    offset = _usage_service.RIYADH_UTC_OFFSET_HOURS if _usage_service.riyadh_reset_enabled() else 0
    return day, next_reset, offset


def retry_fields(now: datetime, next_reset: datetime, offset_hours: int) -> Tuple[int, str]:
    """``(retry_after_seconds, resets_at)``: the ceiling of the seconds to the reset,
    clamped to 1..86400, and the reset instant in the reset zone (ISO 8601, seconds)."""
    seconds = (next_reset - now).total_seconds()
    retry_after = int(math.ceil(seconds)) if math.isfinite(seconds) else MAX_RETRY_AFTER_SECONDS
    retry_after = max(1, min(MAX_RETRY_AFTER_SECONDS, retry_after))
    zone = timezone(timedelta(hours=offset_hours))
    return retry_after, next_reset.astimezone(zone).isoformat(timespec="seconds")


async def budget_exempt_async(user_id: Optional[str]) -> bool:
    """The S81-09 exemption seam (R-S10-7), collapsed (RB10-6): an account in S81-09's
    allow-list (``usage_service._device_quota_exempt``: DEVICE_QUOTA_EXEMPT_USER_IDS, its
    parsing) or of the premium tier is exempt from the refusal BUDGET (never from the
    rules). Read only when a budget is spent; never raises (a failed read is not exempt)."""
    if not isinstance(user_id, str) or not user_id:
        return False
    from app.services import usage_service as _usage_service

    if _usage_service._device_quota_exempt(user_id):
        return True
    try:
        info = await _usage_service._get_user_tier_info(user_id)
    except Exception:  # noqa: BLE001 - not exempt; the budget applies
        return False
    return isinstance(info, dict) and info.get("subscription_tier") == "premium"


async def _redis_dispatch(fn, *args):
    """The #115 dispatch: off the loop iff ENABLE_ASYNC_REDIS_OFFLOAD, else inline."""
    from app.services import cache_service as _cache_service

    if _cache_service._redis_offload_enabled():
        return await asyncio.to_thread(fn, *args)
    return fn(*args)


def _read_counts(client: Any, keys: List[str]) -> List[int]:
    """ONE MGET; a missing key is 0; a non-numeric value raises (a fail-open read)."""
    replies = client.mget(*keys)
    if not isinstance(replies, (list, tuple)) or len(replies) != len(keys):
        raise ValueError("budget reply shape")
    counts = []
    for reply in replies:
        if reply is None:
            counts.append(0)
            continue
        if isinstance(reply, bytes):
            reply = reply.decode("ascii")
        counts.append(int(str(reply).strip()))
    return counts


def _incr_keys(client: Any, keys: List[str], expireat: int) -> Any:
    from app.services import llm_spend_breaker as _llm_spend_breaker

    return _llm_spend_breaker._eval(client, REFUSAL_INCR_SCRIPT, keys, [str(expireat)])


async def budget_state_async(subject: Optional[BudgetSubject]) -> Optional[Tuple[int, str]]:
    """None (the request may consume) or ``(retry_after_seconds, resets_at)`` when either
    of the subject's counters has reached REFUSAL_DAILY_BUDGET and the account is not
    exempt. No subject or no Redis client: None, silently. A raising read or a
    non-numeric counter: None plus ONE WARNING (fail-open)."""
    if subject is None:
        return None
    from app.services import cache_service as _cache_service

    client = _cache_service.redis_client
    if client is None:
        return None
    now = datetime.now(timezone.utc)
    try:
        day, next_reset, offset_hours = reset_window(now)
        keys = budget_keys(subject, day)
        if not keys:
            return None
        counts = await _redis_dispatch(_read_counts, client, keys)
    except Exception as exc:  # noqa: BLE001 - fail open: the base consume is fail-open too
        logger.warning("[CATEGORY-GATE] budget read fail-open type=%s", type(exc).__name__)
        return None
    budget = refusal_daily_budget()
    if not any(count >= budget for count in counts):
        return None
    if await budget_exempt_async(subject.user_id):
        return None
    return retry_fields(now, next_reset, offset_hours)


async def record_refusal_async(subject: Optional[BudgetSubject]) -> None:
    """Count one post-consume refusal: ONE EVAL of REFUSAL_INCR_SCRIPT over the
    subject's keys, EXPIREAT the next reset + KEY_GRACE_SECONDS. Never raises: a failure
    is ONE WARNING and the counter misses that refusal."""
    if subject is None:
        return
    from app.services import cache_service as _cache_service

    client = _cache_service.redis_client
    if client is None:
        return
    try:
        day, next_reset, _offset_hours = reset_window(datetime.now(timezone.utc))
        keys = budget_keys(subject, day)
        if not keys:
            return
        expireat = int(next_reset.timestamp()) + KEY_GRACE_SECONDS
        await _redis_dispatch(_incr_keys, client, keys, expireat)
    except Exception as exc:  # noqa: BLE001 - the refusal still answers
        logger.warning("[CATEGORY-GATE] budget record failed type=%s", type(exc).__name__)


# ---------------------------------------------------------------------------
# bodies (key order pinned)
# ---------------------------------------------------------------------------
def refusal_result(category: Optional[str]) -> dict:
    """The orchestrator's refusal result (the route adds nothing but the timings)."""
    return {"success": False, "error": REFUSAL_MESSAGE, "code": CODE, "category": category,
            "categories_live": list(CATEGORIES_LIVE)}


def refusal_detail(category: Optional[str]) -> dict:
    """The structured HTTPException detail of a rule-1 / post-resolve refusal (400)."""
    return {"code": CODE, "error": REFUSAL_MESSAGE, "category": category,
            "categories_live": list(CATEGORIES_LIVE)}


def budget_detail(retry_after: int, resets_at: str) -> dict:
    """The structured HTTPException detail of the budget refusal (429)."""
    return {"code": CODE, "error": BUDGET_MESSAGE, "scope": SCOPE_REFUSAL_DAILY,
            "retry_after": retry_after, "resets_at": resets_at,
            "categories_live": list(CATEGORIES_LIVE)}


def http_detail(result: Any) -> dict:
    """A post-resolve refusal result -> its 400 detail (the constant copy; the error
    handler validates the category)."""
    category = result.get("category") if isinstance(result, dict) else None
    return refusal_detail(category)


def camera_refusal_body(category: Optional[str], vision_cost: Any) -> dict:
    """The camera refusal (HTTP 200, the review-safe action "error" shape)."""
    return {"success": False, "action": "error", "error": REFUSAL_MESSAGE, "code": CODE,
            "category": category, "categories_live": list(CATEGORIES_LIVE),
            "vision_cost": vision_cost}


def camera_budget_body(retry_after: int, resets_at: str) -> dict:
    """The camera budget refusal (HTTP 200, action "error"; never billed)."""
    return {"success": False, "action": "error", "error": BUDGET_MESSAGE, "code": CODE,
            "scope": SCOPE_REFUSAL_DAILY, "retry_after_seconds": retry_after,
            "resets_at": resets_at, "categories_live": list(CATEGORIES_LIVE)}


def log_refused(stage: str, category: Optional[str], route: Optional[str] = None) -> None:
    """ONE INFO line per refusal (the stage, the canonical category, the route label)."""
    if route in _ROUTE_LABELS:
        logger.info("[CATEGORY-GATE] refused stage=%s category=%s route=%s", stage, category, route)
    else:
        logger.info("[CATEGORY-GATE] refused stage=%s category=%s", stage, category)


def log_budget_spent(route: str) -> None:
    """ONE INFO line per budget refusal (the route label only)."""
    logger.info("[CATEGORY-GATE] budget spent stage=pre_consume route=%s",
                route if route in _ROUTE_LABELS else "image")


# ---------------------------------------------------------------------------
# the route and orchestrator entry points
# ---------------------------------------------------------------------------
async def text_gate(texts: Sequence[Any], user: Any, *, route: str) -> GateDecision:
    """The pre-consume gate of the three text routes: rule 1 raises the 400, a spent
    budget raises the 429 (both before the preferences read and the consume); else the
    decision, carrying the budget subject, for the orchestrator."""
    from fastapi import HTTPException

    decision = evaluate(texts)
    if decision.outcome == "refuse":
        log_refused("pre_consume", decision.category, route)
        raise HTTPException(status_code=400, detail=refusal_detail(decision.category))
    subject = budget_subject(user)
    spent = await budget_state_async(subject)
    if spent is not None:
        log_budget_spent(route)
        raise HTTPException(status_code=429, detail=budget_detail(*spent))
    return replace(decision, subject=subject)


async def post_resolve_refusal(decision: GateDecision, products: Sequence[dict], *, parser_path: bool,
                               selected_category: Optional[str] = None,
                               category_used: Optional[str] = None,
                               classify: Any = None) -> PostResolveVerdict:
    """The chip-free post-resolve decision (rules 2 and 3), run only when a route
    passed its pre-consume decision.

    Per product (R-S10-6): the parse's category on the q= path; on the explicit-pair /
    vision path the deterministic name stub, overridden to fragrances by a
    concentration / form word in that product's own name (R-S10-5). Any positive
    non-fragrance product refuses. On the q= path nothing else is asked ('other'
    proceeds, R-S10-3). On the explicit / vision path, with every product 'other': no
    client chip -> the resolver's own chip-free category (its A2b already ran, C11);
    with lexicon evidence -> proceed without a classifier (a stated limit, GC-2);
    else ONE A2b call through ``classify`` (the orchestrator's own module name).
    A classifier 'other' (its failure value too) proceeds."""
    from app.services.extraction_service import canonicalize_category

    names = [product.get("search_query") or product.get("name") for product in products]
    per_product: List[str] = []
    form_override = False
    for product, name in zip(products, names, strict=True):
        if not parser_path and isinstance(name, str) and name and scan([name]).fragrance_type:
            per_product.append("fragrances")
            form_override = True
        else:
            per_product.append(canonicalize_category(product.get("category")))
    for category in per_product:
        if category in _POSITIVE_NON_FRAGRANCE:
            return PostResolveVerdict(refused=category)
    if parser_path or "fragrances" in per_product:
        return PostResolveVerdict(form_override=form_override)
    chip = canonicalize_category(selected_category) if selected_category else None
    if not chip or chip == "other":
        detected = canonicalize_category(category_used)
    elif decision.evidence:
        return PostResolveVerdict()
    else:
        if classify is None:
            from app.services.extraction_service import classify_category_llm as classify
        detected = canonicalize_category(await classify(names))
    if detected in _POSITIVE_NON_FRAGRANCE:
        return PostResolveVerdict(refused=detected)
    return PostResolveVerdict()


def form_override_category(selected_category: Optional[str]) -> Tuple[str, bool, Optional[str]]:
    """GC-1: ``(category_used, category_switched, original_category)`` for a pair the
    form override made a fragrance pair, by the resolver's own ladder with the
    detection 'fragrances'."""
    from app.services.extraction_service import canonicalize_category

    chip = canonicalize_category(selected_category) if selected_category else None
    switched = bool(chip and chip != "other" and chip != "fragrances")
    return "fragrances", switched, (selected_category if switched else None)


def apply_form_override_stubs(verdict: PostResolveVerdict, products: Sequence[dict]) -> None:
    """F1-2 (RULINGS_FIX1_S81_10): when the form override fired, each product whose own name
    carries a concentration / form word (the product the override made a fragrance) takes
    'fragrances' as its own stub, together with category_used, so B1's per-product
    categories (captured right after the gate block) agree with the pair and result_gate
    never reports category_conflict for a pair the gate made a fragrance pair. Every other
    product keeps its stub; the q= path never overrides (R-S10-5)."""
    if not verdict.form_override:
        return
    for product in products:
        name = product.get("search_query") or product.get("name")
        if isinstance(name, str) and name and scan([name]).fragrance_type:
            product["category"] = "fragrances"


def is_live_row(row: Any) -> bool:
    """A History / smart-pick row whose stored pair category is fragrances."""
    from app.services.extraction_service import canonicalize_category

    full = row.get("full_response") if isinstance(row, dict) else None
    category = full.get("category") if isinstance(full, dict) else None
    return canonicalize_category(category) == "fragrances"


def is_live_tag(tag: Any) -> bool:
    """A curated trending entry whose tag is the fragrances category."""
    from app.services.extraction_service import canonicalize_category

    return canonicalize_category(tag) == "fragrances"
