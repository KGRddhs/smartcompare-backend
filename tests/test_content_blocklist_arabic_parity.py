"""W4-8 Half B -- ``ENABLE_BLOCKLIST_PRECISION_V2`` (default OFF, read per call).

The Arabic lists of ``app/data/content_blocklist.json`` still carry the bare
tokens the EN lists tightened (9f6e498 replaced EN ``opium`` with four phrases):
bare-hamza AFYUN blocks every Arabic YSL (Black) Opium query, bare BUNDUQIYA
(rifle) blocks water guns / Nerf / air rifles, KATIM SAWT (silencer) blocks car
exhausts and generators, SIKKIN QITALI (tactical knife) blocks Gerber EDC
knives; EN ``silencer`` / ``tactical knife`` block the same household,
automotive and EDC collisions.

Design under test = Fable ruling R1 (Half B is FLAGGED) as inverted by design
ruling R11: both matchers are compiled when the service is built and the
matcher selects per call, so OFF is byte-identical to HEAD on L1
(``check_query_intent``) and L2 (``is_text_safe``, ``filter_shopping_items``).
Every v2 list EQUALS its v1 list (nothing dropped, nothing added -- the bare
token blocks every phrasing that contains it); precision comes from the
per-token exemption map ``v2.exempt.<cat>.<lang>.<token>: [qualifiers]``:
under the flag a token with exemptions does not block a query that also
contains one of ITS qualifiers (whole token, lowercased, re.escape'd, the
matcher's own boundary); every other token still blocks. The qualifiers
follow rulings R13c / R14b -- R11's named context words are the FLOOR, plus
every measured collision word: EN silencer exhaust / generator / bosch /
walker / hilux / car / muffler; EN tactical knife gerber + the measured EDC
brands victorinox / leatherman; the Arabic water / Nerf / air rifle, car-exhaust
and generator silencer and Gerber knife forms; the hamza-spelled AFYUN with the
perfume word, its plural, SAN LORAN, BLAK, ysl, yves saint laurent, saint
laurent. The allowed set is OPEN over co-occurrence (R13d): ANY query that
pairs an exempted token with one of its qualifiers is allowed under the flag,
intent wording included -- a stated limit, pinned below with measured
examples; the enumerated newly-allowed keys are measured collision EXAMPLES.
The bare-alef AFYUN spelling is allowed in BOTH states (v1 lists only the hamza
form; R14c, follow-up W4-8f), pinned as the measured fact.

Every test sets its own flag state; the service singleton is reset; a
zero-network guard (sockets + libcurl) fails any network attempt. Query strings
come from the committed HEAD-records fixture (``l1_queries``, keys BL:/BI:) and
the corpus fixture (keys C:), or are written below as escaped literals (IX:).
Labels: RED = fails at HEAD 04acb757 for the stated reason; PIN = green at HEAD.
"""
from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path

import pytest

import app.services.content_safety_service as css

FLAG = "ENABLE_BLOCKLIST_PRECISION_V2"
FLAG_A = "ENABLE_CATEGORY_TOKEN_FIX"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
BLOCKLIST = Path(css.__file__).resolve().parent.parent / "data" / "content_blocklist.json"

HEAD_L1_SHA = "8c8de712de00844c081901b4e1afc628ef5200bfd1ca7b89629bf5d2ea144627"
HEAD_L1_CORPUS_SHA = "3885d2701484167362f2241faa3b50b965b04c1771d149946764ae26d0238a07"
HEAD_V1_LISTS_SHA = "29a290b6c31ab402d8d3bae8ef78836cfd1a1c38d6872a0dfab0b4f70f3d4ebb"

AFYUN = "أفيون"                      # opium (bare hamza)
BUNDUQIYA = "بندقية"            # rifle
KATIM = "كاتم صوت"          # silencer
SIKKIN = "سكين قتالي"  # tactical knife
MUSADDAS = "مسدس"                          # handgun
DHAKHIRA = "ذخيرة"                    # ammunition


def _load(name):
    with open(FIXTURES / name, encoding="utf-8") as fh:
        return json.load(fh)


_HEAD = _load("category_corpus_gcc_360_head_records.json")
_CORPUS = {"C:%s:%02d" % (r["truth"], r["idx"]): r["query"]
           for r in _load("category_corpus_gcc_360.json")["rows"]}
Q = dict(_HEAD["l1_queries"])
Q.update(_CORPUS)
# The review's 22 natural intent phrasings (R12) + one pin row for the added
# entry KATIM SAWT SILAH.
Q.update({
    "IX:00": "buy silencer",
    "IX:01": "silencer for sale",
    "IX:02": "silencer for rifle",
    "IX:03": "9mm silencer",
    "IX:04": "sniper rifle silencer",
    "IX:05": "silencer for glock",
    "IX:06": "handgun silencer",
    "IX:07": "firearm silencer",
    "IX:08": "tactical knife for self defense",
    "IX:09": "buy tactical knife",
    "IX:10": "hunting rifle",
    "IX:11": KATIM + " للمسدس",              # for the pistol
    "IX:12": KATIM + " لمسدس",                    # for a pistol
    "IX:13": KATIM + " للبندقية",  # for the rifle
    "IX:14": KATIM + " مسدسات",              # pistols
    "IX:15": "شراء " + KATIM,                          # buy a silencer
    "IX:16": BUNDUQIYA + " قنص",                            # sniper rifle
    "IX:17": "شراء " + BUNDUQIYA,                      # buy a rifle
    "IX:18": SIKKIN + " للبيع",                   # tactical knife for sale
    "IX:19": "بيع " + AFYUN,                                # sell opium
    "IX:20": AFYUN + " للبيع",                    # opium for sale
    "IX:21": "تهريب " + AFYUN,                    # smuggle opium
    "BX:00": KATIM + " سلاح",                          # silencer weapon
    # Fix round 1 (re-adversary major 1): intent phrasings blocked at HEAD that
    # the round-1 phrase list allowed -- incl. the AR twins of EN phrases (R3:
    # never MORE permissive in Arabic). Under R11 the bare token blocks them.
    "IX:22": "glock silencer",
    "IX:23": "shotgun silencer",
    "IX:24": "ar15 silencer",
    "IX:25": "22lr silencer",
    "IX:26": "9 mm silencer",
    "IX:27": ".45 acp silencer",
    "IX:28": "silencer kit for rifle",
    "IX:29": "sell silencer",
    "IX:30": "suppressor silencer",
    "IX:31": "tactical knife for sale",
    "IX:32": KATIM + " للبيع",                    # silencer for sale
    "IX:33": "بيع " + KATIM,                                # sell a silencer
    "IX:34": BUNDUQIYA + " للبيع",                # rifle for sale
    "IX:35": "بيع " + BUNDUQIYA,                            # sell a rifle
    "IX:36": "شراء " + SIKKIN,                         # buy a combat knife
    "IX:37": "بيع " + SIKKIN,                               # sell a combat knife
})
# Design ruling R11 pin (b): EVERY weapon / drug-intent phrasing of adversary
# round 1 (probe_b.py) and adversary round 2 (probe_b2.py), verbatim -- each is
# BLOCKED in both flag states (under v2 through the bare v1 token).
LILBAY = "للبيع"                      # for sale
BAY = "بيع"                                        # sell
SHIRA = "شراء"                               # buy
ADV_R1 = {
    "A1:00": "glock silencer", "A1:01": "shotgun silencer", "A1:02": "ar15 silencer",
    "A1:03": "22lr silencer", "A1:04": "9 mm silencer", "A1:05": ".45 acp silencer",
    "A1:06": "silencer kit for rifle", "A1:07": "sell silencer", "A1:08": "suppressor silencer",
    "A1:09": "silencer", "A1:10": "tactical knife", "A1:11": "tactical knife for sale",
    "A1:12": KATIM + " " + LILBAY, "A1:13": BAY + " " + KATIM, "A1:14": KATIM,
    "A1:15": BUNDUQIYA + " " + LILBAY, "A1:16": BAY + " " + BUNDUQIYA,
    "A1:17": SHIRA + " " + SIKKIN, "A1:18": BAY + " " + SIKKIN,
    "A1:19": AFYUN, "A1:20": AFYUN + " " + LILBAY,
}
ADV_R2 = {
    "A2:00": "buy a silencer", "A2:01": "silencer for pistol", "A2:02": "silencer for ar15",
    "A2:03": "cheap silencer", "A2:04": "silencer price", "A2:05": "where to buy silencer",
    "A2:06": "silencer for sale online", "A2:07": "glock 17 silencer",
    "A2:08": "solvent trap silencer", "A2:09": "tactical knife", "A2:10": "buy a tactical knife",
    "A2:11": "tactical knife price", "A2:12": KATIM + " سعر", "A2:13": BUNDUQIYA,
    "A2:14": BUNDUQIYA + " 9mm", "A2:15": SIKKIN, "A2:16": AFYUN,
    "A2:17": KATIM + " غلوك",
}
# Adversary round 2's two controls: a car-exhaust silencer (a collision form --
# allowed under the flag through the 'exhaust' qualifier) and a surge
# suppressor (an electronics product, allowed in both states).
ADV_CONTROLS = {"AX:00": "car exhaust silencer", "AX:01": "surge suppressor"}
Q.update(ADV_R1)
Q.update(ADV_R2)
Q.update(ADV_CONTROLS)
# R11: the bare tokens that carry exemptions block alone, in both states.
BARE_TOKENS = {"BD:00": "silencer", "BD:01": "tactical knife", "BD:02": KATIM,
               "BD:03": BUNDUQIYA, "BD:04": SIKKIN, "BD:05": AFYUN}

OPIUM_BRAND = ["BL:01", "BL:04", "BL:06", "BI:25"]
COLLISIONS = ["BL:%02d" % i for i in range(7, 18)] + ["C:other:06", "C:other:37"]
# (key, blocklist_match in BOTH states) -- R11: v2 == v1, the bare token matches.
INTENT_NEW_MATCH = [
    ("BI:12", "silencer"), ("BI:13", "silencer"), ("BI:14", "silencer"),
    ("BI:17", KATIM), ("BI:18", KATIM), ("BI:19", BUNDUQIYA), ("BX:00", KATIM),
]
# Design rulings R11 / R13c / R14b: the exemption map = the qualifier FLOOR (R11's
# named context words + every measured collision word, never a minimal cover).
# Each row's string carries its token and ONE of that token's qualifiers (for
# 'yves saint laurent' also the sub-phrase 'saint laurent' it contains) -- a
# measured collision string, or (QX:) the single-qualifier form of one:
# (category, lang, token, qualifier, key), in the JSON's order.
AADIM = "عادم"                          # exhaust
MUWALLID = "مولد"                       # generator
JARBAR = "جربر"                         # Gerber
MAA = "ماء"                                   # water
NERF = "نيرف"                           # Nerf
HAWAA = "هواء"                          # air
ATR = "عطر"                                   # perfume
SAN_LORAN = "سان لوران"  # Saint Laurent
BLAK = "بلاك"                           # black
UTUR = ATR[:2] + chr(0x0648) + ATR[2:]              # perfumes (plural)
AFYUN_ALEF = chr(0x0627) + AFYUN[1:]                # opium, bare-alef spelling
Q.update({
    "QX:00": "Bosch silencer",                                  # R11: Bosch silencer
    "QX:01": BUNDUQIYA + " " + NERF,                            # BL:16's first half
    "QX:02": ATR + " " + AFYUN,                                 # opium perfume
    "QX:03": AFYUN + " ايف " + SAN_LORAN,                  # BL:01 minus the perfume word
    "QX:04": AFYUN + " YSL",
    "QX:05": AFYUN + " Yves Saint Laurent",
    # Rulings R13c / R14b: the floor words' single-qualifier forms.
    "QX:06": "exhaust silencer",
    "QX:07": "Walker silencer",
    "QX:08": "car silencer",
    "QX:09": "silencer muffler",
    "QX:10": "Gerber tactical knife",
    "QX:11": "Victorinox tactical knife",
    "QX:12": "Leatherman tactical knife",
    "QX:13": UTUR + " " + AFYUN,                                # perfumes opium
    "QX:14": AFYUN + " Saint Laurent",
    "QX:15": AFYUN + " " + SAN_LORAN,                           # R14b pin, no 'Yves'
})
QUALIFIER_ROWS = [
    ("weapons", "en", "silencer", "exhaust", "QX:06"),
    ("weapons", "en", "silencer", "generator", "BL:09"),
    ("weapons", "en", "silencer", "bosch", "QX:00"),
    ("weapons", "en", "silencer", "walker", "QX:07"),
    ("weapons", "en", "silencer", "hilux", "BL:08"),
    ("weapons", "en", "silencer", "car", "QX:08"),
    ("weapons", "en", "silencer", "muffler", "QX:09"),
    ("weapons", "en", "tactical knife", "gerber", "QX:10"),
    ("weapons", "en", "tactical knife", "victorinox", "QX:11"),
    ("weapons", "en", "tactical knife", "leatherman", "QX:12"),
    ("weapons", "ar", BUNDUQIYA, MAA, "BL:15"),
    ("weapons", "ar", BUNDUQIYA, NERF, "QX:01"),
    ("weapons", "ar", BUNDUQIYA, HAWAA, "BL:17"),
    ("weapons", "ar", KATIM, AADIM, "BL:12"),
    ("weapons", "ar", KATIM, MUWALLID, "BL:13"),
    ("weapons", "ar", SIKKIN, JARBAR, "BL:14"),
    ("illegal_drugs", "ar", AFYUN, ATR, "QX:02"),
    ("illegal_drugs", "ar", AFYUN, UTUR, "QX:13"),
    ("illegal_drugs", "ar", AFYUN, SAN_LORAN, "QX:03"),
    ("illegal_drugs", "ar", AFYUN, BLAK, "BI:25"),
    ("illegal_drugs", "ar", AFYUN, "ysl", "QX:04"),
    ("illegal_drugs", "ar", AFYUN, "yves saint laurent", "QX:05"),
    ("illegal_drugs", "ar", AFYUN, "saint laurent", "QX:14"),
]
QX_KEYS = ["QX:%02d" % i for i in range(16)]
RULED_EXEMPT = {}
for _cat, _lang, _tok, _qual, _key in QUALIFIER_ROWS:
    RULED_EXEMPT.setdefault(_cat, {}).setdefault(_lang, {}).setdefault(_tok, []).append(_qual)
# R11 pin (d): a qualifier exempts ONLY its own token -- (query, the other v1
# token that still blocks it under the flag).
CROSS_TOKEN = [
    ("exhaust silencer for glock 19", "glock 19"),
    ("exhaust silencer ammunition", "ammunition"),
    ("Gerber tactical knife vs switchblade", "switchblade"),
    (KATIM + " " + AADIM + " " + MUSADDAS, MUSADDAS),
    (BUNDUQIYA + " هجومية " + MAA, BUNDUQIYA + " هجومية"),
    # ... nor another EXEMPTED token of the same category:
    ("exhaust silencer vs tactical knife", "tactical knife"),
    (KATIM + " " + BUNDUQIYA + " " + MAA, KATIM),
    # ... and the kept tokens stay in v1 list order: with KATIM SAWT exempted,
    # BUNDUQIYA (listed first) matches before BUNDUQIYA HUJUMIYA at one position.
    (KATIM + " " + AADIM + " " + BUNDUQIYA + " هجومية", BUNDUQIYA),
]
# R11 stated limit (co-occurrence), measured by adversary round 3
# (probe_b3.py): a token with exemptions does not block ANY query that also
# carries one of its qualifiers -- intent wording included. Blocked OFF,
# allowed ON; pinned so a change is deliberate.
COOCCURRENCE_LIMIT = [
    "glock 17 exhaust silencer", "buy silencer hilux", "exhaust silencer for sale",
    "tactical knife gerber for combat",
    SHIRA + " " + BUNDUQIYA + " " + HAWAA,                     # buy an air rifle
    BUNDUQIYA + " قنص " + HAWAA,                           # air sniper rifle
    SHIRA + " " + AFYUN + " " + BLAK,                          # buy opium 'black'
    KATIM + " " + BUNDUQIYA + " " + HAWAA + " " + AADIM,       # both tokens exempted
    "car silencer for pistol",                                 # R13c floor word 'car'
    "buy walker silencer",                                     # R13c floor word 'walker'
]
# ... and only the listed qualifiers exempt: a brand that is NOT a qualifier
# beside a token still blocks in both states (R14b: 'Honda' is not in the floor).
UNQUALIFIED_ROWS = [("Honda silencer", "silencer"), ("Yamaha silencer", "silencer"),
                    ("Spyderco tactical knife", "tactical knife"),
                    (KATIM + " بوش", KATIM)]
# Ruling R14b pins: the floor words allow under v2 and block under v1; the bare
# hamza AFYUN and the bare 'silencer' block in both states.
R14B_ALLOWED_V2_BLOCKED_V1 = ["Walker silencer", "car silencer", "silencer muffler",
                              "Bosch silencer", ATR + " " + AFYUN, UTUR + " " + AFYUN,
                              AFYUN + " " + SAN_LORAN]
R14B_BLOCKED_BOTH = [(AFYUN, "illegal_drugs"), ("silencer", "weapons")]
# Ruling R14c (measured fact, follow-up W4-8f): v1 lists only the hamza AFYUN, so
# the bare-alef spelling is ALLOWED under v1 AND v2 (a pre-existing Arabic
# alef / hamza normalisation gap, identical in both states).
R14C_BARE_ALEF_ALLOWED_BOTH = [AFYUN_ALEF, AFYUN_ALEF + " " + SAN_LORAN]
# R11: a qualifier matches as a WHOLE token (a substring does not exempt) --
# (query, the token that blocks it under the flag).
SUBSTRING_QUALIFIER = [
    ("exhaustive silencer review", "silencer"),
    ("generators silencer", "silencer"),
    ("gerbera tactical knife", "tactical knife"),
    ("carbon silencer", "silencer"),
    (KATIM + " " + AADIM + "ة", KATIM),
]
# (key, reason, match) unchanged in both flag states.
INTENT_SAME_MATCH = [
    ("BI:16", "weapons", "switchblade"), ("BI:21", "weapons", MUSADDAS),
    ("BI:22", "weapons", MUSADDAS), ("BI:23", "weapons", DHAKHIRA),
    ("C:other:38", "weapons", "shotgun shells"), ("IX:06", "weapons", "handgun"),
    ("IX:07", "weapons", "firearm"),
]
# Ruling R1's intent table: 21 of the review's 22 phrasings + the two HEAD-blocked
# intent probes the spec listed as losing their block (buy opium AR, hunting
# rifle AR) + 'silencer suppressor' (BI:15, red-gate ruling R4) + the fix-round
# phrasings IX:22..IX:37. Each must stay blocked in both states.
R1_INTENT_KEYS = (["IX:%02d" % i for i in range(38) if i != 10]
                  + ["BI:11", "BI:20", "BI:15"])
ADV_INTENT_KEYS = sorted(ADV_R1) + sorted(ADV_R2)
# The newly-allowed keys over the ENUMERATED strings (R11 pin c; R13d: measured
# collision EXAMPLES, not a closed set -- the allowed set is open over
# co-occurrence, see COOCCURRENCE_LIMIT): blocked at HEAD, allowed under the
# flag -- over the 413 committed strings the collisions + the Arabic opium brand
# strings (17 keys); over the intent table, both adversaries' lists and the
# single-qualifier strings, only the r2 car-exhaust control and the QX: strings.
RULED_NEWLY_ALLOWED = sorted(OPIUM_BRAND[:3] + ["BI:25"] + COLLISIONS)
RULED_NEWLY_ALLOWED_ADV = sorted(["AX:00"] + QX_KEYS)


# --------------------------------------------------------------------- fixtures

_LOOPBACK = {"127.0.0.1", "::1", "localhost", "0.0.0.0", "", None}


def _host_of(address):
    host = address[0] if isinstance(address, tuple) and address else address
    return host.decode("ascii", "replace") if isinstance(host, bytes) else host


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Refuse and record every non-loopback socket / DNS / libcurl attempt."""
    attempts = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def guard_connect(self, address):
        host = _host_of(address)
        if host not in _LOOPBACK:
            attempts.append(("connect", host))
            raise OSError("W4-8 zero-network guard: blocked connect to %r" % (host,))
        return real_connect(self, address)

    def guard_connect_ex(self, address):
        host = _host_of(address)
        if host not in _LOOPBACK:
            attempts.append(("connect_ex", host))
            raise OSError("W4-8 zero-network guard: blocked connect_ex to %r" % (host,))
        return real_connect_ex(self, address)

    def guard_getaddrinfo(host, *args, **kwargs):
        name = _host_of(host)
        if name not in _LOOPBACK:
            attempts.append(("getaddrinfo", name))
            raise socket.gaierror("W4-8 zero-network guard: blocked getaddrinfo(%r)" % (name,))
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guard_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guard_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guard_getaddrinfo)

    import curl_cffi.requests as curl_requests

    def curl_guard(*args, **kwargs):
        attempts.append(("curl_cffi", str(args[:2])))
        raise RuntimeError("W4-8 zero-network guard: blocked curl_cffi request")

    monkeypatch.setattr(curl_requests, "get", curl_guard)
    monkeypatch.setattr(curl_requests.Session, "request", curl_guard)
    monkeypatch.setattr(curl_requests.AsyncSession, "request", curl_guard)
    yield
    assert not attempts, "W4-8 zero-network guard: the test attempted network I/O: %r" % (attempts,)


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    """Both W4-8 flags start UNSET; the content-safety singleton is reset."""
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv(FLAG_A, raising=False)
    monkeypatch.setattr(css, "_service", None)
    yield


@pytest.fixture
def svc():
    """A fresh service over the LIVE committed blocklist file."""
    return css.ContentSafetyService()


def _flag(monkeypatch, value, name=FLAG):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _verdict(service, q):
    r = service.check_query_intent(q)
    return [r.allowed, r.reason, r.blocklist_match]


def _canon_sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


OFF_STATES = [pytest.param(None, None, id="unset"), pytest.param("false", None, id="false"),
              pytest.param(None, "true", id="unset+category_flag_on")]
BOTH_STATES = [pytest.param(None, id="off"), pytest.param("true", id="on")]


# ------------------------------------------------------------------------ tests

@pytest.mark.parametrize("value,expected_allowed", [
    (None, False), ("", False), ("false", False), ("0", False), ("no", False),
    ("off", False), ("true", True), ("TRUE", True), (" true ", True), ("1", True),
    ("yes", True), ("on", True), ("On", True),
])
def test_blocklist_flag_truthy_forms(monkeypatch, svc, value, expected_allowed):
    """RED for the truthy rows / PIN for the falsy rows: the flag is read with
    .strip().lower() against the repo's truthy set; the probe is a collision
    string (Bosch exhaust silencer) that the v2 list allows."""
    _flag(monkeypatch, value)
    assert svc.check_query_intent(Q["BL:07"]).allowed is expected_allowed


@pytest.mark.parametrize("key", OPIUM_BRAND)
def test_arabic_opium_brand_name_no_longer_blocks(monkeypatch, svc, key):
    """RED (15): the Arabic YSL (Black) Opium queries pass L1 under the flag.
    HEAD: illegal_drugs / bare AFYUN (Arabic twin of
    test_ysl_black_opium_passes_l1_prefilter)."""
    _flag(monkeypatch, "true")
    assert _verdict(svc, Q[key]) == [True, None, None]


@pytest.mark.parametrize("value,a_flag", OFF_STATES)
@pytest.mark.parametrize("key", OPIUM_BRAND)
def test_arabic_opium_brand_name_still_blocks_flag_off(monkeypatch, svc, key, value, a_flag):
    """PIN (15b): flag OFF is byte-identical -- the same four strings still
    block on the bare token."""
    _flag(monkeypatch, value)
    _flag(monkeypatch, a_flag, FLAG_A)
    assert _verdict(svc, Q[key]) == [False, "illegal_drugs", AFYUN]


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("key", ["BI:06", "BI:24", "BI:08", "BI:10", "BI:11"])
def test_arabic_opium_intent_blocked_on_bare_token(monkeypatch, svc, key, value):
    """PIN (16, rewritten by design ruling R11): opium tincture (SIBGHAT AFYUN),
    poppy (KHASHKHASH AFYUN), raw opium (AFYUN KHAM), opium den (WAKR AFYUN) and
    buy opium block in BOTH states exactly as at HEAD, on the bare AFYUN (v2
    keeps every v1 token; the rounds-1/2 phrase entries were removed)."""
    _flag(monkeypatch, value)
    assert _verdict(svc, Q[key]) == [False, "illegal_drugs", AFYUN] == _HEAD["l1_verdicts_head"][key]


@pytest.mark.parametrize("key", COLLISIONS)
def test_weapons_false_positives_pass(monkeypatch, svc, key):
    """RED (17): the household / automotive / EDC collisions (car exhaust and
    generator silencers, Gerber vs Victorinox, water gun / Nerf / air rifle, and
    corpus rows C:other:06 / C:other:37) pass L1 under the flag. HEAD: blocked."""
    _flag(monkeypatch, "true")
    assert _verdict(svc, Q[key]) == [True, None, None]


@pytest.mark.parametrize("value,a_flag", OFF_STATES)
@pytest.mark.parametrize("key", COLLISIONS)
def test_weapons_false_positives_blocked_flag_off(monkeypatch, svc, key, value, a_flag):
    """PIN (17b, the R1 table's OFF column): each collision is blocked exactly as
    at HEAD (verdict equal to the committed HEAD record)."""
    _flag(monkeypatch, value)
    _flag(monkeypatch, a_flag, FLAG_A)
    head = _HEAD["l1_verdicts_head"][key]
    assert head[0] is False
    assert _verdict(svc, Q[key]) == head


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("key", [k for k, _ in INTENT_NEW_MATCH] + [k for k, _, _ in INTENT_SAME_MATCH])
def test_weapons_intent_still_blocks(monkeypatch, svc, key, value):
    """PIN (18): weapon-intent strings stay blocked as weapons in both states."""
    _flag(monkeypatch, value)
    got = _verdict(svc, Q[key])
    assert got[:2] == [False, "weapons"], (key, got)


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("key,match", INTENT_NEW_MATCH, ids=[k for k, _ in INTENT_NEW_MATCH])
def test_weapons_intent_match_is_the_v1_token_both_states(monkeypatch, svc, key, match, value):
    """PIN (18, rewritten by design ruling R11): v2 == v1, so gun / pistol /
    rifle silencer, KATIM SAWT MUSADDAS / BUNDUQIYA / SILAH and BUNDUQIYA
    HUJUMIYA match the same v1 token in both states (no qualifier present)."""
    _flag(monkeypatch, value)
    assert _verdict(svc, Q[key]) == [False, "weapons", match]


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("key,reason,match", INTENT_SAME_MATCH,
                         ids=[k for k, _, _ in INTENT_SAME_MATCH])
def test_weapons_intent_match_unchanged_rows(monkeypatch, svc, key, reason, match, value):
    """PIN (18b): rows the edit must not touch -- switchblade, bare MUSADDAS
    (R4: out of this unit), DHAKHIRA, shotgun shells, handgun and firearm
    ('firearm silencer' matches 'firearm', the earlier entry)."""
    _flag(monkeypatch, value)
    assert _verdict(svc, Q[key]) == [False, reason, match]


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("key", R1_INTENT_KEYS)
def test_r1_intent_phrasings_blocked_both_states(monkeypatch, svc, key, value):
    """PIN (R1 table): every natural intent phrasing the review measured stays
    BLOCKED in both flag states (buy silencer, silencer for sale, ..., the AR
    buy / sell / smuggle / for-sale forms)."""
    _flag(monkeypatch, value)
    assert svc.check_query_intent(Q[key]).allowed is False, key


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("key", ADV_INTENT_KEYS)
def test_adversary_intent_phrasings_blocked_both_states(monkeypatch, svc, key, value):
    """PIN (design ruling R11 pin b): every weapon / drug-intent phrasing of
    adversary rounds 1 and 2 (probe_b.py / probe_b2.py, verbatim, EN + AR) is
    BLOCKED in both states -- 'buy a silencer', 'silencer for pistol', 'glock 17
    silencer', 'tactical knife price', the bare AR rifle / silencer /
    combat-knife / opium tokens, ... (the phrase-list design allowed them)."""
    _flag(monkeypatch, value)
    assert svc.check_query_intent(Q[key]).allowed is False, key


@pytest.mark.parametrize("key", sorted(R1_INTENT_KEYS + ADV_INTENT_KEYS))
def test_intent_verdict_identical_in_both_states(monkeypatch, svc, key):
    """PIN (R11): no intent phrasing carries a qualifier, so each one's verdict
    (reason AND matched token) under the flag equals its verdict without it."""
    off = _verdict(svc, Q[key])
    _flag(monkeypatch, "true")
    assert _verdict(svc, Q[key]) == off, key


@pytest.mark.parametrize("value", BOTH_STATES)
def test_r1_hunting_rifle_allowed_both_states(monkeypatch, svc, value):
    """PIN: EN 'hunting rifle' (the 22nd phrasing) is ALLOWED at HEAD -- weapons.en
    has no bare 'rifle' -- so it cannot be 'blocked in both states' without
    breaking flag-OFF identity; it stays allowed in both (recorded as a spec
    disagreement)."""
    _flag(monkeypatch, value)
    assert _verdict(svc, Q["IX:10"]) == [True, None, None]


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("key", sorted(BARE_TOKENS))
def test_bare_exempted_tokens_block_both_states(monkeypatch, svc, key, value):
    """PIN (design ruling R11, replaces the round-1/2 stated limit): each token
    that carries exemptions still blocks ALONE in both states, on itself -- a
    bare token blocks every phrasing that contains it unless one of its own
    qualifiers is present."""
    _flag(monkeypatch, value)
    q = BARE_TOKENS[key]
    got = _verdict(svc, q)
    assert got[0] is False and got[2] == q, (key, got)


@pytest.mark.parametrize("value", BOTH_STATES)
def test_catalog_parity_ar_never_more_permissive(monkeypatch, svc, value):
    """PIN (19, rewritten by R11 (g) / red-gate R3): in both states the bare AR
    AFYUN / BUNDUQIYA / KATIM SAWT / SIKKIN QITALI block; EN 'silencer' /
    'tactical knife' block; EN 'opium' and 'rifle' stay allowed as at HEAD (that
    EN gap is follow-up W4-8d, unchanged)."""
    _flag(monkeypatch, value)
    for ar in (AFYUN, BUNDUQIYA, KATIM, SIKKIN):
        assert svc.check_query_intent(ar).allowed is False, ar
    for en in ("silencer", "tactical knife"):
        assert svc.check_query_intent(en).allowed is False, en
    for en in ("opium", "rifle"):
        assert svc.check_query_intent(en).allowed is True, en


def test_blocklist_edit_strictly_narrows(monkeypatch, svc):
    """PIN (20): over the 413 committed strings + the intent table, nothing
    allowed with the flag OFF is blocked with it ON (guards against a widening
    re-edit, e.g. the natural AL- forms of variant A)."""
    off = {k: _verdict(svc, q) for k, q in Q.items()}
    _flag(monkeypatch, "true")
    on = {k: _verdict(svc, q) for k, q in Q.items()}
    assert sorted(k for k in Q if off[k][0] and not on[k][0]) == []
    head = _HEAD["l1_verdicts_head"]
    assert sorted(k for k in head if head[k][0] and not on[k][0]) == []


@pytest.mark.parametrize("value,a_flag", OFF_STATES)
def test_blocklist_flag_off_equals_head_verdicts(monkeypatch, svc, value, a_flag):
    """PIN (R7 gate): flag OFF, all 413 verdicts equal the committed HEAD records
    field for field; whole-map hash 8c8de712..., C: subset 3885d270..."""
    _flag(monkeypatch, value)
    _flag(monkeypatch, a_flag, FLAG_A)
    head = _HEAD["l1_verdicts_head"]
    got = {k: _verdict(svc, Q[k]) for k in head}
    assert sorted(k for k in head if got[k] != head[k]) == []
    assert _canon_sha(got) == HEAD_L1_SHA
    assert _canon_sha({k: v for k, v in got.items() if k.startswith("C:")}) == HEAD_L1_CORPUS_SHA


def test_blocklist_v1_lists_unchanged():
    """PIN: the v1 en/ar lists of the committed file are byte-for-byte HEAD's
    (the v2 list sits alongside; the OFF matcher compiles exactly HEAD's lists)."""
    doc = json.loads(BLOCKLIST.read_text(encoding="utf-8"))
    v1 = {c: {"en": lists["en"], "ar": lists["ar"]} for c, lists in doc["categories"].items()}
    assert _canon_sha(v1) == HEAD_V1_LISTS_SHA


def test_blocklist_v2_shape():
    """PIN (red-gate ruling R6 + design rulings R11/R12): the committed file
    carries a top-level "v2": {"notes", "categories", "exempt"} whose notes name
    the flag; every v2 (category, lang) list is a non-empty list of non-empty,
    distinct strings that replaces an existing v1 list; the top-level "version"
    is "2" (the file's own rule: bump on a shape change) and "updated_at" is the
    edit date. HEAD: no "v2" key, version "1"."""
    doc = json.loads(BLOCKLIST.read_text(encoding="utf-8"))
    assert doc["version"] == "2"
    assert doc["updated_at"] == "2026-09-27"
    v2 = doc.get("v2")
    assert isinstance(v2, dict) and set(v2) == {"notes", "categories", "exempt"}, v2
    assert FLAG in v2["notes"]
    cats = v2["categories"]
    assert cats, "v2.categories is empty"
    for cat, lists in cats.items():
        assert cat in doc["categories"], cat
        assert lists and set(lists) <= {"en", "ar"}, (cat, lists)
        for lang, terms in lists.items():
            assert isinstance(terms, list) and terms, (cat, lang)
            assert all(isinstance(t, str) and t.strip() for t in terms), (cat, lang)
            assert len(set(terms)) == len(terms), (cat, lang)


def test_v2_lists_equal_v1_lists():
    """PIN (design ruling R11 pin a): for EVERY category / lang the list the
    flag selects (the v2 override or the v1 fallback) is the v1 list -- set
    equality (and v1 order, so the reported match is HEAD's); the rounds-1/2
    intent entries are removed and no v1 token is dropped."""
    doc = json.loads(BLOCKLIST.read_text(encoding="utf-8"))
    overrides = doc["v2"]["categories"]
    for cat, lists in doc["categories"].items():
        for lang, v1 in lists.items():
            v2 = overrides.get(cat, {}).get(lang, v1)
            assert set(v2) == set(v1), (cat, lang)
            assert v2 == v1, (cat, lang)


def test_exempt_map_is_exactly_the_ruled_table():
    """PIN (design rulings R11 / R13c / R14b): v2.exempt is EXACTLY the ruled
    qualifier-floor table -- no token outside it has an exemption, no qualifier
    is missing or extra; every exempted token is an entry of its own v1 list
    (the hamza AFYUN, as spelled in v1); every qualifier is a non-empty string
    that occurs as a whole word in the string it is recorded against."""
    doc = json.loads(BLOCKLIST.read_text(encoding="utf-8"))
    assert doc["v2"]["exempt"] == RULED_EXEMPT
    for cat, lang, token, qual, key in QUALIFIER_ROWS:
        assert token in doc["categories"][cat][lang], (cat, lang, token)
        assert qual.strip() == qual and qual, qual
        assert (" " + qual + " ") in (" " + Q[key].lower() + " "), (qual, key)


@pytest.mark.parametrize("cat,lang,token,qual,key", QUALIFIER_ROWS,
                         ids=["%s-%s-%d" % (r[0], r[1], i) for i, r in enumerate(QUALIFIER_ROWS)])
def test_each_qualifier_alone_exempts_its_collision(monkeypatch, svc, cat, lang, token, qual, key):
    """RED (R11 / R14b, one row per qualifier): the string contains its token
    and ONE of that token's qualifiers (plus, for 'yves saint laurent', only the
    sub-phrase 'saint laurent' it contains), is blocked on that token with the
    flag off and allowed under it -- so dropping the qualifier from the map
    reddens this row (dropping 'yves saint laurent' alone is subsumed by 'saint
    laurent'; the exact-table pin catches it)."""
    s = " " + Q[key].lower() + " "
    present = [q for q in RULED_EXEMPT[cat][lang][token] if (" " + q + " ") in s]
    assert qual in present, (key, present)
    assert all(q == qual or (" " + q + " ") in (" " + qual + " ") for q in present), (key, present)
    assert _verdict(svc, Q[key])[:2] == [False, cat]
    _flag(monkeypatch, "true")
    assert _verdict(svc, Q[key]) == [True, None, None], key


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("query,blocker", CROSS_TOKEN, ids=[str(i) for i in range(len(CROSS_TOKEN))])
def test_qualifier_exempts_only_its_own_token(monkeypatch, svc, query, blocker, value):
    """PIN (R11 pin d): a qualifier exempts ONLY its own token -- 'exhaust
    silencer for glock 19' stays blocked (on 'glock 19' under the flag),
    'Gerber tactical knife vs switchblade' on 'switchblade', the Arabic exhaust
    silencer + handgun on MUSADDAS, the water + assault rifle on BUNDUQIYA
    HUJUMIYA."""
    _flag(monkeypatch, value)
    got = _verdict(svc, query)
    assert got[:2] == [False, "weapons"], (query, got)
    if value == "true":
        assert got[2] == blocker, (query, got)


@pytest.mark.parametrize("query", COOCCURRENCE_LIMIT, ids=[str(i) for i in range(len(COOCCURRENCE_LIMIT))])
def test_stated_limit_qualifier_cooccurrence_allows_intent_wording(monkeypatch, svc, query):
    """PIN (R11 stated limit, adversary round 3): the exemption is a
    co-occurrence rule, not a closed phrase set -- 'glock 17 exhaust silencer',
    'exhaust silencer for sale', 'tactical knife gerber for combat', the AR buy
    / sniper air-rifle forms are blocked with the flag off and ALLOWED under it
    (no other v1 token in them). pr_text states it; the canary audits it."""
    assert svc.check_query_intent(query).allowed is False, query
    _flag(monkeypatch, "true")
    assert _verdict(svc, query) == [True, None, None], query


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("query,blocker", UNQUALIFIED_ROWS, ids=[str(i) for i in range(len(UNQUALIFIED_ROWS))])
def test_unlisted_brand_does_not_exempt(monkeypatch, svc, query, blocker, value):
    """PIN (R11 / R14b): a brand that is NOT a qualifier ('Honda' and 'Yamaha'
    beside silencer, 'Spyderco' beside tactical knife -- not in the floor, not
    measured -- and the Arabic BOSH beside KATIM SAWT) exempts nothing --
    blocked on the token in both states."""
    _flag(monkeypatch, value)
    got = _verdict(svc, query)
    assert got[0] is False and got[2] == blocker, (query, got)


@pytest.mark.parametrize("query", R14B_ALLOWED_V2_BLOCKED_V1,
                         ids=[str(i) for i in range(len(R14B_ALLOWED_V2_BLOCKED_V1))])
def test_r14b_floor_words_allowed_v2_blocked_v1(monkeypatch, svc, query):
    """RED (ruling R14b pins): 'Walker silencer', 'car silencer', 'silencer
    muffler', 'Bosch silencer' and the hamza-spelled perfume / perfumes + AFYUN
    and AFYUN + SAN LORAN are BLOCKED under v1 (on the bare token) and ALLOWED
    under v2 (the qualifier floor)."""
    assert _verdict(svc, query)[0] is False, query
    _flag(monkeypatch, "true")
    assert _verdict(svc, query) == [True, None, None], query


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("query,reason", R14B_BLOCKED_BOTH, ids=["afyun_hamza", "silencer"])
def test_r14b_bare_tokens_blocked_both(monkeypatch, svc, query, reason, value):
    """PIN (ruling R14b): the bare hamza AFYUN and the bare 'silencer' block in
    both states, on themselves."""
    _flag(monkeypatch, value)
    assert _verdict(svc, query) == [False, reason, query]


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("query", R14C_BARE_ALEF_ALLOWED_BOTH, ids=["alef", "alef_san_loran"])
def test_r14c_bare_alef_afyun_allowed_both_states(monkeypatch, svc, query, value):
    """PIN (ruling R14c, the measured fact; follow-up W4-8f alef / hamza
    normalisation): v1's drug list carries only the hamza AFYUN, so the
    bare-alef spelling is ALLOWED under v1 and v2 alike -- a pre-existing gap,
    identical in both states (v1 stays byte-unchanged, R12)."""
    _flag(monkeypatch, value)
    assert _verdict(svc, query) == [True, None, None]


@pytest.mark.parametrize("query,blocker", SUBSTRING_QUALIFIER,
                         ids=[str(i) for i in range(len(SUBSTRING_QUALIFIER))])
def test_qualifier_matches_whole_token_only(monkeypatch, svc, query, blocker):
    """PIN (R11): a qualifier inside a longer word ('exhaustive', 'generators',
    'gerbera', AADIM + TA MARBUTA) does not exempt -- blocked under the flag on
    the token."""
    _flag(monkeypatch, "true")
    assert _verdict(svc, query) == [False, "weapons", blocker], query


def test_qualifier_is_casefolded(monkeypatch, svc):
    """PIN (R11): the qualifier match uses the matcher's lowercase + IGNORECASE
    normalisation -- an upper-case collision is exempted too."""
    _flag(monkeypatch, "true")
    assert _verdict(svc, "BOSCH EXHAUST SILENCER") == [True, None, None]
    assert _verdict(svc, "GERBER Tactical Knife") == [True, None, None]


def test_v2_blocks_every_v1_term_with_the_flag_set_inside_the_test(monkeypatch):
    """PIN (R11 pin e): the flag is set HERE (the process env stays clean), and
    under it every v1 term of every category and language -- adult products,
    gore, self harm too, not only the categories that carry exemptions -- still
    blocks alone, on itself, as its own category."""
    _flag(monkeypatch, "true")
    service = css.ContentSafetyService()
    doc = json.loads(BLOCKLIST.read_text(encoding="utf-8"))
    bad = []
    for cat, lists in doc["categories"].items():
        for lang, terms in lists.items():
            for t in terms:
                r = service.check_query_intent("compare " + t)
                if (r.allowed, r.reason) != (False, cat) or service.is_text_safe(t):
                    bad.append((cat, lang, t))
    assert bad == []


def _synthetic_service(monkeypatch, tmp_path, term, exempt_for_term):
    synthetic = {
        "version": "2", "categories": {"weapons": {"en": [term], "ar": []}},
        "v2": {"notes": FLAG, "categories": {"weapons": {"en": [term]}},
               "exempt": {"weapons": {"en": {term: exempt_for_term}}}},
    }
    path = tmp_path / ("blocklist_%d.json" % len(exempt_for_term))
    path.write_text(json.dumps(synthetic), encoding="utf-8")
    monkeypatch.setattr(css, "_BLOCKLIST_PATH", path)
    return css.ContentSafetyService()


def test_v2_terms_and_qualifiers_are_escaped(monkeypatch, tmp_path):
    """PIN (R11 pin f): every v2 term and every qualifier is re.escape'd and
    matched with the matcher's normalisation -- over a synthetic blocklist (the
    module global _BLOCKLIST_PATH is read at construction) a '.45 ACP' term does
    not match 'x45 acp', its exemption key is lowercased like the term, and a
    'v1.2' qualifier exempts only the literal 'v1.2' (not 'v1x2')."""
    service = _synthetic_service(monkeypatch, tmp_path, ".45 ACP", ["v1.2"])
    _flag(monkeypatch, "true")
    assert service.check_query_intent("x45 acp").allowed is True
    assert service.check_query_intent(".45 acp").allowed is False
    assert service.check_query_intent(".45 acp v1.2").allowed is True
    assert service.check_query_intent(".45 acp v1x2").allowed is False


def test_v2_empty_qualifier_list_exempts_nothing(monkeypatch, tmp_path):
    """PIN (R11): a token whose qualifier list is empty gets NO exemption (an
    empty alternation would match every text and silently unblock the token)."""
    service = _synthetic_service(monkeypatch, tmp_path, ".45 acp", [])
    _flag(monkeypatch, "true")
    assert service.check_query_intent(".45 acp").allowed is False
    assert service.check_query_intent("compare .45 acp kits").allowed is False


@pytest.mark.parametrize("value,expected", [
    (None, False), ("", False), ("false", False), ("0", False), ("no", False),
    ("off", False), ("true", True), ("TRUE", True), (" true ", True), ("1", True),
    ("yes", True), ("on", True), ("On", True),
])
def test_blocklist_reader_named_and_truthy_forms(monkeypatch, value, expected):
    """PIN by name (red-gate ruling R7): the Half B reader is
    content_safety_service.blocklist_precision_v2_enabled(), default OFF, the
    repo's truthy set read per call with .strip().lower() -- exactly like
    extraction_service.category_token_fix_enabled(). HEAD: absent."""
    reader = getattr(css, "blocklist_precision_v2_enabled", None)
    assert reader is not None, (
        "content_safety_service.blocklist_precision_v2_enabled() does not exist")
    _flag(monkeypatch, value)
    assert reader() is expected


def test_corpus_l1_delta_is_exactly_two_rows(monkeypatch, svc):
    """RED (21): over the 360 corpus rows the flag moves exactly C:other:06 (Bosch
    silencer) and C:other:37 (Gerber tactical knife); C:other:38 (shotgun shells)
    stays blocked. HEAD: 0 rows move."""
    head = _HEAD["l1_verdicts_head"]
    _flag(monkeypatch, "true")
    moved = sorted(k for k in _CORPUS if _verdict(svc, _CORPUS[k]) != head[k])
    assert moved == ["C:other:06", "C:other:37"]


def test_newly_allowed_set_is_exactly_the_ruled_collisions(monkeypatch, svc):
    """RED (R11 pin c; R13d: measured collision EXAMPLES, the allowed set is
    open over co-occurrence): over the 413 committed strings, the keys blocked
    at HEAD and allowed under the flag are EXACTLY the collisions + the Arabic
    opium brand strings (17 keys; 'silencer suppressor' BI:15 stays blocked on
    the bare 'silencer'); over the intent table, both adversaries' lists and the
    QX: strings, ONLY the r2 'car exhaust silencer' control and the QX: strings.
    HEAD: empty."""
    head = _HEAD["l1_verdicts_head"]
    extra = sorted(set(Q) - set(head))
    off = {k: svc.check_query_intent(Q[k]).allowed for k in extra}
    _flag(monkeypatch, "true")
    newly = sorted(k for k in head if not head[k][0] and svc.check_query_intent(Q[k]).allowed)
    assert newly == RULED_NEWLY_ALLOWED
    newly_extra = sorted(k for k in extra if not off[k] and svc.check_query_intent(Q[k]).allowed)
    assert newly_extra == RULED_NEWLY_ALLOWED_ADV


@pytest.mark.parametrize("key", COLLISIONS + OPIUM_BRAND)
def test_l2_is_text_safe_follows_flag(monkeypatch, svc, key):
    """RED (L2): is_text_safe selects the same list per call -- a collision
    title is safe under the flag. HEAD: unsafe."""
    _flag(monkeypatch, "true")
    assert svc.is_text_safe(Q[key]) is True


@pytest.mark.parametrize("value,a_flag", OFF_STATES)
def test_l2_surfaces_flag_off_unchanged(monkeypatch, svc, value, a_flag):
    """PIN (L2): flag OFF, every collision title is unsafe and dropped from a
    shopping list; intent titles are unsafe (HEAD behaviour)."""
    _flag(monkeypatch, value)
    _flag(monkeypatch, a_flag, FLAG_A)
    for key in COLLISIONS + OPIUM_BRAND + R1_INTENT_KEYS:
        assert svc.is_text_safe(Q[key]) is False, key
    items = [{"title": Q[k], "snippet": ""} for k in COLLISIONS + R1_INTENT_KEYS]
    assert svc.filter_shopping_items(items) == []


def test_l2_filter_shopping_items_follows_flag(monkeypatch, svc):
    """RED (L2): under the flag filter_shopping_items keeps the collision rows and
    still drops every intent row (title or snippet). HEAD: drops all."""
    _flag(monkeypatch, "true")
    keep = [{"title": Q[k], "snippet": "in stock"} for k in COLLISIONS]
    drop = [{"title": "listing", "snippet": Q[k]} for k in R1_INTENT_KEYS]
    assert svc.filter_shopping_items(keep + drop) == keep
    for key in R1_INTENT_KEYS:
        assert svc.is_text_safe(Q[key]) is False, key


# Ruling R16c: on the L2 title + snippet surface a qualifier exempts a token only
# when both sit in the SAME field; the tokens are still found over the joined
# surface (v1 identity), so a token spanning the two fields is exempted by none.
# (title, snippet, kept under v1, kept under v2)
R16C_L2_ROWS = [
    ("Silencer 9mm", "ships by car", False, False),                   # adversary r6
    ("Solvent trap silencer kit .22", "fits car cleaning", False, False),  # adversary r6
    ("Bosch exhaust silencer", "in stock", False, True),
    ("Bosch exhaust silencer", "", False, True),
    ("Bosch exhaust silencer", "free delivery in Manama", False, True),
    ("Silencer 9mm", "Bosch exhaust silencer for cars", False, False),  # qualifier in the other field
    ("Bosch exhaust silencer", "Silencer 9mm", False, False),           # ... either way round
    ("Silencer", "", False, False),                                     # bare token
    ("Gerber tactical", "knife for combat", False, False),              # an exempted token spanning the fields
    ("car ghost", "gun kit", False, False),                             # any multi-word token spanning
    ("tactical knife gerber", "in stock", False, True),                 # a token at offset 0, exempted
    ("Gerber tactical knife vs tactical", "knife", False, False),       # a 2nd occurrence spans
    (KATIM + " " + MUWALLID, "in stock", False, True),
    (KATIM, AADIM, False, False),
    # Fable, after adversary r7 (mutants A7_junction_off_by_one / A7_spanning_end_ge): an
    # exempted multi-word token that ENDS the title does not span into the snippet.
    ("Gerber tactical knife", "in stock", False, True),
    ("Gerber Tactical Knife", "", False, True),
    # Fable, after adversary r7 (mutant A7_fastpath_title_only): the token and its qualifier
    # both in the SNIPPET exempt it there (the positive half of R16c).
    ("Accessories", "Bosch exhaust silencer", False, True),
    ("Spare part", "Honda generator silencer box", False, True),
]


@pytest.mark.parametrize("value", BOTH_STATES)
@pytest.mark.parametrize("title,snippet,kept_v1,kept_v2", R16C_L2_ROWS,
                         ids=[str(i) for i in range(len(R16C_L2_ROWS))])
def test_r16c_l2_exemption_is_decided_per_field(monkeypatch, svc, title, snippet,
                                                kept_v1, kept_v2, value):
    """PIN (ruling R16c): filter_shopping_items keeps an item only when every
    token it carries is exempted by a qualifier in the token's OWN field
    (title 'Silencer 9mm' + snippet 'ships by car' is dropped under v1 AND v2);
    flag OFF is the v1 joined-surface verdict."""
    _flag(monkeypatch, value)
    item = {"title": title, "snippet": snippet}
    kept = svc.filter_shopping_items([item]) == [item]
    assert kept is (kept_v2 if value == "true" else kept_v1), (title, snippet)


@pytest.mark.parametrize("value", BOTH_STATES)
def test_r16c_is_text_safe_is_one_field(monkeypatch, svc, value):
    """PIN (stated limit, ruling R16c): is_text_safe receives ONE caller-composed
    string (title + retailer / domain / product name at its 22 call sites), so
    it has no field boundary and the co-occurrence exemption applies over the
    whole string -- unchanged by R16c, measured both ways."""
    _flag(monkeypatch, value)
    assert svc.is_text_safe("Silencer 9mm ships by car") is (value == "true")
    assert svc.is_text_safe("Silencer 9mm") is False


def test_blocklist_flag_read_per_call(monkeypatch):
    """RED: one service instance, the flag flipped between calls -- built OFF:
    ON allows, unset blocks, ON allows; built ON: unset blocks (catches a
    list selected at construction or import)."""
    q = Q["BL:07"]
    built_off = css.ContentSafetyService()
    _flag(monkeypatch, "true")
    assert built_off.check_query_intent(q).allowed is True
    _flag(monkeypatch, None)
    assert built_off.check_query_intent(q).allowed is False
    _flag(monkeypatch, "true")
    assert built_off.check_query_intent(q).allowed is True
    built_on = css.ContentSafetyService()
    _flag(monkeypatch, None)
    assert built_on.check_query_intent(q).allowed is False
    assert built_on.is_text_safe(q) is False
    _flag(monkeypatch, "true")
    assert built_on.is_text_safe(q) is True


def test_v2_does_not_block_audit_corpus_names(monkeypatch, svc):
    """PIN (22, v2 half of the EN audit): every legitimate name of the
    collision-audit corpus (gold-truth queries + price_service brands + the
    curated catalogue) that passes L1 with the flag OFF also passes with it ON."""
    from scripts import audit_blocklist_collisions as aud
    names = (aud._gold_truth_queries() + aud._price_service_brand_corpus()
             + aud._PRODUCT_NAME_CATALOGUE)
    off = {n: svc.check_query_intent(n).allowed for n in names}
    _flag(monkeypatch, "true")
    newly_blocked = sorted(n for n in names if off[n] and not svc.check_query_intent(n).allowed)
    assert newly_blocked == []
