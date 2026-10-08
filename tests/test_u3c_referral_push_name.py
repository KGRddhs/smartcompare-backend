"""U3c (session 74) -- the Loop 2 referral push never shows the part of the
invitee's email before the @.

Privacy-policy sentence made true (U8 redraft at 6c74d9b6, section 5,
landing/privacy.html:264): "If you joined through
a friend's invite, the notification we send that friend can show your display
name." The push carries the invitee's display name or no name at all (ruling R3:
a nameless, localised body, so no English fallback lands in the Arabic copy).
The named copy stays identical except the days token; the full Arabic body is
pinned by code points (ruling F6, bonus=5). Rider R7: the expiry day count in
both languages is referral_service.BONUS_EXPIRY_DAYS (the bonus lasts 7 days;
the copy said 3).

The other half of U3c (tests/test_u3c_store_false_pin.py): every chat completion
is sent with store=False, so none becomes a stored completion (dashboard Logs);
the organisation data-sharing setting (OA2) is separate and unaffected (OA3).

Hermetic: fake Supabase client, push transport patched. Pure ASCII (Arabic via
chr() code points).
"""
import asyncio
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import push_service
from app.services.referral_service import BONUS_EXPIRY_DAYS, ReferralService


def _cps(*codes):
    return "".join(chr(c) for c in codes)


AR_YOUR_FRIEND = _cps(0x0635, 0x062F, 0x064A, 0x0642, 0x0643)
AR_COMMA = chr(0x060C)
# The Arabic Loop 2 body at main dfbda511 (push_service.py:185-186) after the
# "<name>" + U+060C + " " prefix, rendered with bonus=5 ('5' = 0x0035), split at
# the days digit (0x0033 at main; ruling R7 makes it BONUS_EXPIRY_DAYS).
AR_REST_HEAD = _cps(
    0x0635, 0x062F, 0x064A, 0x0642, 0x0643, 0x0020, 0x0627, 0x0633, 0x062A, 0x062E,
    0x062F, 0x0645, 0x0020, 0x0645, 0x064A, 0x0651, 0x0632, 0x0020, 0x0644, 0x0644,
    0x062A, 0x0648, 0x002E, 0x0020, 0x062D, 0x0635, 0x0644, 0x062A, 0x0020, 0x0639,
    0x0644, 0x0649, 0x0020, 0x0035, 0x0020, 0x0645, 0x0642, 0x0627, 0x0631, 0x0646,
    0x0627, 0x062A, 0x0020, 0x0625, 0x0636, 0x0627, 0x0641, 0x064A, 0x0629, 0x002E,
    0x0020, 0x062A, 0x0646, 0x062A, 0x0647, 0x064A, 0x0020, 0x062E, 0x0644, 0x0627,
    0x0644, 0x0020,
)
# " <ayyam>." -- the Arabic plural "days", correct for counts 3 to 10.
AR_REST_TAIL = _cps(0x0020, 0x0623, 0x064A, 0x0627, 0x0645, 0x002E)
# The Arabic Loop 2 title at main dfbda511 (push_service.py:183).
AR_TITLE = _cps(
    0x0635, 0x062F, 0x064A, 0x0642, 0x0643, 0x0020, 0x0642, 0x0627, 0x0631, 0x0646,
    0x0020, 0x0645, 0x0646, 0x062A, 0x062C, 0x0627, 0x064B, 0x0020, 0x0644, 0x0644,
    0x062A, 0x0648,
)
EN_TITLE = "Your friend just compared something"
EN_REST_HEAD = " just used MYEZ. You got 5 bonus comparisons. Expires in "
EN_REST_TAIL = " days."
DAYS = r"(\d+)"
EMAIL = "sara.q" + "@" + "example.com"


def _esc(text):
    return text.encode("unicode_escape").decode("ascii")


def _days_in(body, lead, language):
    """The day count when body is exactly lead + the localised rest (days masked), else None."""
    if language == "Arabic":
        pattern = re.escape(lead + AR_REST_HEAD) + DAYS + re.escape(AR_REST_TAIL)
    else:
        pattern = re.escape(lead + EN_REST_HEAD) + DAYS + re.escape(EN_REST_TAIL)
    m = re.fullmatch(pattern, body)
    return int(m.group(1)) if m else None


def _svc():
    with patch("app.services.referral_service.get_admin_supabase_client", return_value=MagicMock()):
        return ReferralService()


def _sent_name(invitee):
    svc = _svc()
    with patch("app.services.push_service.send_loop2_push", new_callable=AsyncMock) as mock_push:
        asyncio.run(svc._send_loop2_push("ref-1", invitee, 5))
    mock_push.assert_called_once()
    return mock_push.call_args.kwargs["invitee_display_name"]


def test_u3c_10_display_name_is_sent_when_present():
    """GUARD (green at main)."""
    assert _sent_name({"display_name": "Sara Q", "email": EMAIL}) == "Sara Q"


@pytest.mark.parametrize("invitee", [
    {"email": EMAIL},
    {"email": EMAIL, "display_name": None},
    {"email": EMAIL, "display_name": ""},
    {"email": EMAIL, "display_name": "   "},
], ids=["email_only", "name_none", "name_empty", "name_blank"])
def test_u3c_11_email_local_part_is_never_sent(invitee):
    """RED at main: 'sara.q' (the local part) is sent; blank name sends '   '."""
    name = _sent_name(invitee)
    assert "sara" not in name.lower() and "@" not in name, name
    assert name == "", repr(name)


@pytest.mark.parametrize("invitee", [{}, {"email": ""}, {"email": None}], ids=["empty", "email_blank", "email_none"])
def test_u3c_12_no_name_no_email_sends_empty(invitee):
    """RED at main: 'A friend' (English) is sent and lands inside the Arabic body."""
    assert _sent_name(invitee) == ""


def test_u3c_13_load_invitee_selects_display_name():
    """RED at main: _load_invitee selects 'id, email, subscription_tier', so the display-name
    branch is dead in production and every push fell to the email local part."""
    client = MagicMock()
    chain = client.table.return_value.select.return_value.eq.return_value.single.return_value
    chain.execute.return_value = MagicMock(data={"id": "u", "email": EMAIL, "display_name": "Sara Q"})
    with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
        svc = ReferralService()
        row = asyncio.run(svc._load_invitee("u"))
    cols = {c.strip() for c in client.table.return_value.select.call_args.args[0].split(",")}
    assert {"id", "email", "display_name"} <= cols, cols
    assert row["display_name"] == "Sara Q"


def _push(language, name):
    with patch.object(push_service, "_send_to_expo", new_callable=AsyncMock) as send, \
         patch.object(push_service, "_get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[U3C]"), \
         patch.object(push_service, "_get_user_language", new_callable=AsyncMock, return_value=language):
        asyncio.run(push_service.send_loop2_push(referrer_user_id="r", invitee_display_name=name, bonus_amount=5))
    return send.call_args[0][0]


def test_u3c_14_nameless_english_copy():
    """RED at main: 'Your friend, your friend just used MYEZ. ...' (days token masked; T20 pins it)."""
    p = _push("English", "")
    assert p["title"] == EN_TITLE
    assert _days_in(p["body"], "Your friend", "English") is not None, p["body"]


def test_u3c_15_nameless_arabic_copy_has_no_latin_fallback():
    """RED at main: the Arabic body starts with the English 'Your friend'. The nameless
    body is today's Arabic body minus the name prefix, every code point pinned except
    the days digit (F6; T20 pins the day count)."""
    p = _push("Arabic", "")
    body = p["body"]
    assert body.startswith(AR_YOUR_FRIEND), _esc(body)
    assert not re.search(r"[A-Za-z]", body), _esc(body)
    assert _days_in(body, "", "Arabic") is not None, _esc(body)
    assert p["title"] == AR_TITLE, _esc(p["title"])


def test_u3c_16_named_copy_is_unchanged():
    """GUARD: the named path stays identical in both languages except the days token
    (AR by code points, F6; ruling R7)."""
    assert _days_in(_push("English", "Sara")["body"], "Sara, your friend", "English") is not None
    p = _push("Arabic", "Sara")
    assert _days_in(p["body"], "Sara" + AR_COMMA + " ", "Arabic") is not None, _esc(p["body"])
    assert p["title"] == AR_TITLE, _esc(p["title"])


@pytest.mark.parametrize("language", ["English", "Arabic"])
def test_u3c_17_end_to_end_payload_never_carries_the_email_local_part(language):
    """RED at main: the expo payload body starts with 'sara.q'."""
    svc = _svc()
    with patch.object(push_service, "_send_to_expo", new_callable=AsyncMock) as send, \
         patch.object(push_service, "_get_user_push_token", new_callable=AsyncMock, return_value="ExponentPushToken[U3C]"), \
         patch.object(push_service, "_get_user_language", new_callable=AsyncMock, return_value=language):
        asyncio.run(svc._send_loop2_push("ref-1", {"id": "u", "email": EMAIL}, 5))
    payload = send.call_args[0][0]
    text = payload["title"] + " " + payload["body"]
    assert "sara" not in text.lower() and "@" not in text, _esc(text)


@pytest.mark.parametrize("language", ["English", "Arabic"])
def test_u3c_20_push_day_count_matches_bonus_expiry_days(language):
    """RED at main: the copy says 3 days while the bonus lasts BONUS_EXPIRY_DAYS (7).
    Ruling R7 rider: the day count in the named AND the nameless body equals
    BONUS_EXPIRY_DAYS, in both languages."""
    assert 3 <= BONUS_EXPIRY_DAYS <= 10, (
        "harness: the pinned Arabic word (ayyam) is the plural for 3 to 10; "
        "another count needs a native-reviewed word")
    tail = (AR_REST_TAIL if language == "Arabic" else EN_REST_TAIL)
    head_end = (AR_REST_HEAD[-5:] if language == "Arabic" else "Expires in ")
    counts = {}
    for label, name in (("named", "Sara"), ("nameless", "")):
        body = _push(language, name)["body"]
        m = re.search(re.escape(head_end) + DAYS + re.escape(tail) + r"\Z", body)
        assert m, "%s %s body has no day count: %s" % (language, label, _esc(body))
        counts[label] = int(m.group(1))
    assert counts == {"named": BONUS_EXPIRY_DAYS, "nameless": BONUS_EXPIRY_DAYS}, (
        "%s push day count %s != BONUS_EXPIRY_DAYS %d" % (language, counts, BONUS_EXPIRY_DAYS))


def test_u3c_21_loop2_copy_reads_bonus_expiry_days():
    """RED at main: _loop2_copy hard-codes the day count, and T20 alone passes a
    literal 7. Ruling R7 / Gate 15:55 (c), source rule: _loop2_copy reads the NAME
    BONUS_EXPIRY_DAYS (an AST Name load inside the function), imported unaliased
    from app.services.referral_service (module level or inside the function),
    push_service never binds that name itself, and no string literal of the
    function (docstring aside) carries a digit, so neither language can keep a
    hard-coded day count beside the derived one. Ruling X7: no numeric constant
    inside an f-string replacement field ("{7}", adversary mutants e08 / mp1b), and
    BOTH language branches read BONUS_EXPIRY_DAYS by name."""
    import ast
    from pathlib import Path

    tree = ast.parse(Path(push_service.__file__).read_text(encoding="utf-8"))
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_loop2_copy"]
    assert len(fns) == 1, "harness: expected one _loop2_copy, saw %d" % len(fns)
    reads = [
        n for n in ast.walk(fns[0])
        if isinstance(n, ast.Name) and n.id == "BONUS_EXPIRY_DAYS" and isinstance(n.ctx, ast.Load)
    ]
    assert reads, "_loop2_copy must read BONUS_EXPIRY_DAYS by name (no hard-coded day count)"
    imports = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and n.module == "app.services.referral_service"
        and any(a.name == "BONUS_EXPIRY_DAYS" and a.asname is None for a in n.names)
    ]
    assert imports, "BONUS_EXPIRY_DAYS must be imported unaliased from app.services.referral_service"
    binds = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Name) and n.id == "BONUS_EXPIRY_DAYS" and isinstance(n.ctx, (ast.Store, ast.Del))
    ]
    assert binds == [], "push_service must not bind BONUS_EXPIRY_DAYS itself: lines %s" % [b.lineno for b in binds]
    doc = fns[0].body[0].value if isinstance(fns[0].body[0], ast.Expr) else None
    digit_literals = [
        ascii(n.value) for n in ast.walk(fns[0])
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n is not doc
        and any(ch.isdigit() for ch in n.value)
    ]
    assert digit_literals == [], "hard-coded number in the Loop 2 copy: %s" % digit_literals
    numeric_fields = [
        ast.unparse(fv.value) for fv in ast.walk(fns[0]) if isinstance(fv, ast.FormattedValue)
        for c in ast.walk(fv.value)
        if isinstance(c, ast.Constant) and isinstance(c.value, (int, float, complex))
        and not isinstance(c.value, bool)
    ]
    assert numeric_fields == [], "hard-coded number in a Loop 2 copy field: %s" % numeric_fields
    branches = [
        s for s in fns[0].body
        if isinstance(s, ast.If) and any(isinstance(n, ast.Name) and n.id == "language" for n in ast.walk(s.test))
    ]
    assert len(branches) == 1 and branches[0].orelse, "harness: expected one if/else on language in _loop2_copy"
    for label, stmts in (("Arabic", branches[0].body), ("non-Arabic", branches[0].orelse)):
        branch_reads = [
            n for s in stmts for n in ast.walk(s)
            if isinstance(n, ast.Name) and n.id == "BONUS_EXPIRY_DAYS" and isinstance(n.ctx, ast.Load)
        ]
        assert branch_reads, "the %s branch of _loop2_copy must read BONUS_EXPIRY_DAYS by name" % label


@pytest.mark.parametrize("language", ["English", "Arabic"])
def test_u3c_23_blank_name_gets_the_nameless_body_at_the_push_level(language):
    """GUARD (ruling X9): send_loop2_push / _loop2_copy strip the display name themselves,
    so a whitespace-only name reaching the push layer directly yields exactly the
    nameless body (kills green mutant g23, which drops the push-level strip)."""
    blank = _push(language, "   ")
    nameless = _push(language, "")
    assert blank["body"] == nameless["body"], _esc(blank["body"])
    assert blank["title"] == nameless["title"], _esc(blank["title"])
    lead = "Your friend" if language == "English" else ""
    assert _days_in(blank["body"], lead, language) == BONUS_EXPIRY_DAYS, _esc(blank["body"])
