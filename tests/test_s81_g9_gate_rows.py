"""S81-G9 final-round gate rows (RULINGS_REBASE_S81_G9 RB-G9-3; the adversary's MIN-5,
survivors ADV-O9 / ADV-O3 of specs/S81_G9_ADV1_correctness.md).

G9-GR1 test_g9_gr1_duplicated_exempt_rule_refuses_by_rule_set (MIN-5, kills ADV-O9): a
robots body carrying the exempt pair PLUS a duplicated exempt rule ('Disallow: /sparql'
twice) REFUSES by rule_set: ``wdqs_exemption_check`` compares the rule lists for the
agent and for '*' with WDQS_EXEMPT_RULES as a MULTISET (GREEN D-G3, the sorted-list
equality); a set-equality reading admits the duplicate. Driven through the helper and
through ``main`` (one fetch, nothing written, no report, the 'check=rule_set' line); the
exempt pair alone and its reorder stay exempt (the positive controls).

G9-GR2 test_g9_gr2_named_group_token_shapes_refuse (MIN-5, kills ADV-O3): a group whose
User-agent token is the production agent token with its own version suffix
('QarenBot/1.0'), in another case ('QARENBOT') or with surrounding whitespace
('  QarenBot  ') still refuses by named_group (the token rule of
``robots_eval.rules_for_agent``: a lower-cased token occurring in the agent string); an
exact-token reading admits the version-suffixed token. Driven through the helper and
through ``main``.

ADV-O12 (the exemption consulted only on a QarenBot refusal) is recorded EQUIVALENT =
the stated limit L-S16c-5 (the 16c-M5 argument: with no named group the agent's rules
are the '*' rules; a named group refuses first). Synthetic bodies only; no network (the
fetcher is the RED rig); pure ASCII, LF.
"""
from __future__ import annotations

import pytest

from tests import test_s81_s16_kb_seed as s16
from tests import test_s81_s16c_wdqs_exemption as s16c


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in s16c.UNIT_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://" + "kbseed-test" + ".invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc" + "-" + "x" * 10)
    yield


def _check():
    return s16._attr(s16c._brands(), "wdqs_exemption_check")


def _url():
    return s16c._brands().sparql_url()


# ---------------------------------------------------------------- G9-GR1

DUP_SPARQL = s16c.COMMENT + "User-agent: *\nDisallow: /sparql\nDisallow: /sparql\nDisallow: /bigdata\n"
DUP_APPENDED = s16c.LIVE_ROBOTS + "Disallow: /sparql\n"
DUP_BIGDATA = s16c.LIVE_REORDERED + "Disallow: /bigdata\n"


@pytest.mark.parametrize("body", [DUP_SPARQL, DUP_APPENDED, DUP_BIGDATA],
                         ids=["sparql_twice_inline", "sparql_twice_appended", "bigdata_twice_reordered"])
def test_g9_gr1_duplicated_exempt_rule_refuses_by_rule_set(monkeypatch, tmp_path, caplog, body):
    check = _check()
    url = _url()
    # positive controls: the exact pair and its reorder are exempt
    assert check(s16c.LIVE_ROBOTS, url) is None
    assert check(s16c.LIVE_REORDERED, url) is None
    # the duplicate is the same SET as the pair but not the same multiset
    assert check(body, url) == "rule_set"
    rc, rig, rep, infos = s16c._go(monkeypatch, tmp_path, caplog, [(200, {}, body), s16c._bindings()])
    s16c._refused(rc, rig, rep)
    assert any(m.endswith("check=rule_set") for m in infos), infos
    assert not [m for m in infos if "robots exemption applied" in m], infos


# ---------------------------------------------------------------- G9-GR2

def _group(token):
    return "\nUser-agent: " + token + "\nDisallow: /sparql\nDisallow: /bigdata\n"


@pytest.mark.parametrize("token", ["QarenBot/1.0", "QARENBOT", "  QarenBot  "],
                         ids=["version_suffix", "upper_case", "padded"])
def test_g9_gr2_named_group_token_shapes_refuse(monkeypatch, tmp_path, caplog, token):
    from app.services import robots_eval as reval

    assert token.strip().lower() in reval.QARENBOT_UA.lower()
    check = _check()
    url = _url()
    body = s16c.LIVE_ROBOTS + _group(token)
    assert check(s16c.LIVE_ROBOTS, url) is None
    assert check(body, url) == "named_group"
    rc, rig, rep, infos = s16c._go(monkeypatch, tmp_path, caplog, [(200, {}, body), s16c._bindings()])
    s16c._refused(rc, rig, rep)
    assert any(m.endswith("check=named_group") for m in infos), infos
    assert not [m for m in infos if "robots exemption applied" in m], infos
