"""S76 DOMAIN-MYEZ (RED) -- the backend's web host is getmyez.com; qaren.app is retired.

Owner decision 2026-10-10: the product domain is getmyez.com. The identifiers stay qaren
(scheme qaren://, bundle id com.qaren.app, the Supabase recovery redirect
qaren://reset-password); none of them is a web host, so none moves here.

Pins:
* T1 ``referral_service.APP_BASE_URL`` is ``https://getmyez.com`` (no trailing slash).
* T2 the share link ``create_invite`` builds starts with ``https://getmyez.com/c/`` and still
  carries the token and ``?ref=<code>`` (the shape open.html hands to qaren://).
* T3 the admin cost list names the domain it pays for: ``Domain (getmyez.com)``.
* T4 the two robots-reading User-Agents (live sitemap channel + off-clock resolver) still
  mirror each other and point their info URL at ``https://getmyez.com/bot``.
* T6 (GREEN, ruling DG6) the Cloudflare redirect Worker is retired: RETIRED banners, and no
  active route in wrangler.toml, so an accidental ``wrangler deploy`` binds nothing.
* T5 a source scan: no file under app/ or scripts/ contains ``qaren.app`` once the KEEP
  identifier ``com.qaren.app`` is stripped. PR #330 (U8) filled the legal drafts with getmyez.com
  addresses, so the scan covers them too (no allowlist entry left). A retired domain can be re-registered by a
  stranger, so even the prod-smoke throwaway sign-up address moves.

No network, no env, no database: T2 drives the service through the same MagicMock chain as
tests/test_referral_service.py::TestCreateInvite.
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parent.parent
HOST = "getmyez.com"
WEB = "https://" + HOST
RETIRED = re.compile(r"qaren\.app", re.IGNORECASE)
KEEP_IDENTIFIER = re.compile(r"\bcom\.qaren\.app\b")

# Files exempt from the scan, each with its reason (kept >= 40 characters). Empty since PR #330
# filled the two legal drafts with getmyez.com addresses.
ALLOWLIST: dict[str, str] = {}
TEXT_SUFFIXES = {
    ".py", ".md", ".json", ".txt", ".toml", ".yaml", ".yml", ".sql", ".sh", ".ps1",
    ".html", ".cfg", ".ini", ".csv", ".j2", ".tmpl",
}


def test_t1_app_base_url_is_getmyez():
    from app.services import referral_service

    assert referral_service.APP_BASE_URL == WEB


@pytest.mark.asyncio
async def test_t2_create_invite_share_link_is_on_getmyez():
    from app.services.referral_service import ReferralService

    existing_user = MagicMock()
    existing_user.data = {"referral_code": "QR-TESTXY"}
    comp_data = MagicMock()
    comp_data.data = {"id": "cmp-1", "user_id": "user-1", "share_token": "tok-22-chars-aaaaaaaaaa"}
    invite_row = MagicMock()
    invite_row.data = [{"id": "invite-uuid-1"}]

    def table_side_effect(name):
        t = MagicMock()
        if name == "referral_invites":
            t.insert.return_value.execute.return_value = invite_row
        elif name == "users":
            t.select.return_value.eq.return_value.single.return_value.execute.return_value = existing_user
        elif name == "comparisons":
            t.select.return_value.eq.return_value.single.return_value.execute.return_value = comp_data
        elif name == "deep_review_credits":
            t.insert.return_value.execute.return_value = MagicMock(data=[{"id": "credit-1"}])
        return t

    client = MagicMock()
    client.table.side_effect = table_side_effect
    with patch("app.services.referral_service.get_admin_supabase_client", return_value=client):
        result = await ReferralService().create_invite(
            referrer_user_id="user-1",
            comparison_id="cmp-1",
            share_target="whatsapp",
            device_fingerprint_hash="dev-1",
        )

    assert result["share_link"] == WEB + "/c/tok-22-chars-aaaaaaaaaa?ref=QR-TESTXY"
    assert not RETIRED.search(result["share_link"])


def test_t3_admin_cost_line_names_the_paid_domain():
    from app.api.admin_routes import _FIXED_SUBSCRIPTIONS

    lines = [row["line"] for row in _FIXED_SUBSCRIPTIONS]
    assert "Domain (" + HOST + ")" in lines, lines
    assert not [line for line in lines if RETIRED.search(line)], lines


def _ua_literal(rel: str, name: str) -> str:
    text = (REPO / rel).read_text(encoding="utf-8")
    m = re.search(name + r'\s*=\s*"([^"]*)"\s*%', text)
    assert m, f"{rel}: {name} literal not found"
    return m.group(1)


def test_t4_robots_user_agents_point_at_getmyez_and_mirror_each_other():
    live = _ua_literal("app/services/sitemap_discovery_service.py", "_ROBOTS_UA")
    offclock = _ua_literal("scripts/resolve_search_descriptors.py", "USER_AGENT")
    assert live == offclock
    assert "(+" + WEB + "/bot;" in live, live
    assert not RETIRED.search(live)


def _scan(root: str):
    hits = []
    for path in sorted((REPO / root).rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(REPO).as_posix()
        if rel in ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            if RETIRED.search(KEEP_IDENTIFIER.sub(" ", line)):
                hits.append(f"{rel}:{number}")
    return hits


def test_t5_no_retired_host_under_app_or_scripts():
    assert all(len(reason) >= 40 for reason in ALLOWLIST.values())
    assert (REPO / "app").is_dir() and (REPO / "scripts").is_dir()
    hits = _scan("app") + _scan("scripts")
    assert hits == [], hits


def test_t5b_scanner_positive_control():
    """The scanner's two rules, on literals built at runtime (never a real host in a file)."""
    retired = "qaren" + ".app"
    assert RETIRED.search(KEEP_IDENTIFIER.sub(" ", "x https://" + retired + "/c/T"))
    assert not RETIRED.search(KEEP_IDENTIFIER.sub(" ", "bundle com." + retired + " ok"))
    assert RETIRED.search(KEEP_IDENTIFIER.sub(" ", "mail support@" + retired))


def test_t6_redirect_worker_is_retired_and_binds_no_route():
    """DG6: the Worker's only route was on the retired zone, and re-pointed at the new domain it
    would shadow the landing's open.html hand-off. Retired: a RETIRED banner on top of
    wrangler.toml and README.md, and no active (uncommented) route key, so an accidental
    ``wrangler deploy`` binds nothing. The code stays as history."""
    worker = REPO / "cloudflare-workers" / "qaren-redirect"
    toml = (worker / "wrangler.toml").read_text(encoding="utf-8").splitlines()
    assert toml[0].startswith("# RETIRED 2026-10-10"), toml[0]
    active = [line.split("#", 1)[0] for line in toml]
    route_keys = re.compile(r"\broutes?\s*=|\[\[?\s*routes?\s*\]|\bpattern\s*=|\bzone_name\s*=|\bcustom_domain\b")
    assert not [line for line in active if route_keys.search(line)], active
    head = "\n".join((worker / "README.md").read_text(encoding="utf-8").splitlines()[:6])
    assert "RETIRED 2026-10-10" in head, head
