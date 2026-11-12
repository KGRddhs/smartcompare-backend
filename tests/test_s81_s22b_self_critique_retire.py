"""S81-G10 / S81-22b SELF-CRITIQUE-RETIRE -- RED and PIN rows.

Spec .qa-s80/S81-G10_UNIT_SPEC.md section 22b.5 as amended by RULINGS_S81_G10 (R-G10-2: the
router's `critic` role, the `critique` SiteSpec, ENABLE_ANTHROPIC_CRITIC, the consent gates and
model_config's Claude critic default are KEPT byte-identical; only `_self_critique_on` and the
preflight critic leg go). Base 90d4ed74.

The verdict self-critique pass (app/services/verdict_critique_service.py and every path that
only serves it) is deleted; ENABLE_SELF_CRITIQUE (unset in production) becomes an INERT retired
name: with it unset and with it set to true every compare path returns the bytes it returns at
base with it unset, and the `critique` site is never dispatched.

Every RED row fails at base on an AssertionError only (missing / present symbols are read with
importlib.util.find_spec / hasattr and asserted). Every identity row runs with the FULL
companion configuration (ENABLE_FULL_STREAM_DEADLINE both states, ENABLE_ARABIC_VERDICT_OUTPUT
with output_lang ar, ENABLE_COMPARISON_ID_ECHO, ENABLE_COMPARE_RUN_LEDGER (the row through
compare_runs.build_run_row), ENABLE_LLM_LEDGER_V2 ON, every S81-06 role flag OFF) plus a
recorder on llm_router.route (the routed site keys; a scripted critique answer at the
`critique` site) and on feedback_service.save_comparison (the persisted payload). The
orchestrator driver is the S81-18 harness (tests/test_s81_s18_kb_first_serve.py, imported as a
test-support module). The P1 golden tests/fixtures/s81_s22b_flag_off_golden.json was recorded
at base by the RED agent (ASCII, LF). Hermetic: no network, no .env, no credential; synthetic
ids. Pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.main  # noqa: F401  FIRST: the dotenv guard (load_dotenv at import)
import app.services.structured_comparison_service as scs
from app.services import api_budget_service as abs_
from app.services import compare_runs as cr
from app.services import feedback_service, referral_service
from app.services import llm_router as lr
from app.services import model_config as mc
from tests import test_s81_s18_kb_first_serve as s18

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "s81_s22b_flag_off_golden.json"
VCS = "app.services.verdict_critique_service"
FLAG = "ENABLE_SELF_CRITIQUE"
OFF_SPELLINGS = [None, "", "false", "0", "off", " FALSE "]
OFF_IDS = ["unset", "empty", "false", "zero", "off", "padded-FALSE"]
UID = "-".join(["0" * 8, "0" * 4, "4000", "8000", "0" * 10 + "b2"])  # synthetic, built at run time
CRITIQUE_AXES_BASE = ("bias_score", "vagueness_score", "hedging_score", "missing_citation_score",
                      "pain_workflow_align_score")
RETIRED = ("verdict_critique_service", "ENABLE_SELF_CRITIQUE", "_apply_self_critique", "_verdict_critique_metadata",
           "_verdict_critique_outcome", "_persist_verdict_critique", "_without_verdict_critique", "critique_verdict",
           "critique_and_maybe_regenerate", "CritiqueResult", "persist_critique", "is_self_critique_enabled",
           "_self_critique_on", "critic_model", "_regen_model_downgraded", '"_verdict_critique"', "'_verdict_critique'")
COMPANION_ON = ("ENABLE_ARABIC_VERDICT_OUTPUT", "ENABLE_COMPARISON_ID_ECHO", "ENABLE_COMPARE_RUN_LEDGER",
                "ENABLE_LLM_LEDGER_V2")
ROUTER_FLAGS = ("ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VISION", "ENABLE_ANTHROPIC_VERDICT",
                "ENABLE_ANTHROPIC_CRITIC", "ENABLE_ANTHROPIC_MODERATION", "ENABLE_SONNET_ESCALATION",
                "ENABLE_OPENAI_PRE_V3", "ENABLE_LLM_PREFLIGHT_BREAKER")
CLEAR = tuple(sorted(set(s18.CLEARED_ENV + (FLAG,) + COMPANION_ON + ROUTER_FLAGS + (
    "ANTHROPIC_MODEL_CRITIC", "OPENAI_MODEL_VERDICT", "OPENAI_MODEL_STANDARD", "OPENAI_MODEL_VISION",
    "OPENAI_MODEL_CRITIC", "OPENAI_MODEL_MODERATION", "ENABLE_COMPARISON_QUALITY_V2"))))

# ---- base literals (recorded at 90d4ed74) ---------------------------------------------------
ROLE_FLAGS_BASE = {"text": "ENABLE_ANTHROPIC_TEXT", "vision": "ENABLE_ANTHROPIC_VISION",
                   "verdict": "ENABLE_ANTHROPIC_VERDICT", "critic": "ENABLE_ANTHROPIC_CRITIC",
                   "moderation": "ENABLE_ANTHROPIC_MODERATION"}
ENTRY_ROLES_BASE = ("text", "verdict", "critic", "moderation")
# site -> [role, claude_max_tokens, expects_json, schema is None]
SITES_BASE = {
    "classify": ["text", 32, False, True], "critique": ["critic", 512, True, True],
    "disambiguate": ["text", 256, True, False], "image_tier3": ["text", 256, True, True],
    "parse": ["text", 768, True, True], "price": ["text", 512, True, True],
    "price_training": ["text", 384, True, True], "reviews": ["text", 1024, True, True],
    "specs": ["text", 1536, True, True], "specs_synthesized": ["text", 512, True, True],
    "specs_targeted": ["text", 384, True, True], "url_extract": ["text", 1200, True, True],
    "verdict": ["verdict", 1536, True, True], "verdict_fallback": ["verdict", 1536, True, True],
    "vision_v1": ["vision", 768, True, False], "vision_v2": ["vision", 1536, True, False],
}
ANTHROPIC_DEFAULTS_BASE = {"text": "claude-haiku-5-5", "vision": "claude-haiku-5-5", "verdict": "claude-haiku-5-5",
                           "critic": "claude-haiku-5-5", "moderation": "claude-haiku-5-5"}
RESOLVED_MODELS_AFTER = {"moderation": "omni-moderation-latest", "standard": "gpt-4o-mini", "verdict": "gpt-4o",
                         "vision": "gpt-4o-mini"}
OPENAI_MODULES_AFTER = ["app/services/openai_service.py", "app/services/extraction_service.py",
                        "app/services/url_extraction_service.py", "app/services/llm_provider.py",
                        "app/services/content_safety_service.py", "app/services/image_service.py"]
OPENAI_ROW_OTHER_BASE = {"category_ar": "OpenAI", "category_en": "OpenAI", "gate_flag": None,
                         "hosts": ["api.openai.com"], "id": "openai", "kind": "processor", "name_ar": "OpenAI",
                         "name_en": "OpenAI", "personal_data": True, "public_name": True}
PROCESSOR_IDS_BASE = ["supabase", "railway", "upstash", "sentry", "openai", "expo_push", "eas_update", "apple",
                      "google_sign_in", "google_fonts", "serper", "bright_data", "firecrawl", "scrapedo",
                      "cloudflare", "gmail", "youtube", "retailers", "anthropic"]
# The digests below are sha256 values recorded at base, written as base64 of the 32 raw bytes
# (the added-line sweep reads hex digit runs as phone-shaped; the S81-22 BASE_BLOBS precedent).
# The canonical JSON of [id, kind, module, hosts, gate_flag, personal_data] of every row other
# than openai (the R22 identity fields):
OTHER_ROWS_DIGEST = "V1MeN/G3kG2UbX715gtOGWB7W7zWLDLPXRpN3DjMAI0="
# migrations/030_verdict_critiques.sql and its rollback, LF-normalised:
MIG030_LF_SHA256 = "6fdNVEWy/cZtX3cxtSodSNesheQaKrWDaoWbEPepsos="
MIG030_RB_LF_SHA256 = "mOm6jLF1NuhI+O8iIyUDsmQTAJrjBI0fYcBTPsz7ydk="
# the sorted file listings of migrations/ and migrations/rollback/ ("\n"-joined):
MIG_LISTING_DIGEST = "NNFcDVRL8EzLLJUzZ1/p3rwLAXf8SyHsFK45KW4/0Qw="
MIG_RB_LISTING_DIGEST = "pVP1Rv/9vpICB37fb4zvJNAfyPvLPGkFK3hGuDYi1w0="


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in CLEAR:
        monkeypatch.delenv(name, raising=False)
    kbs = importlib.import_module(s18.SERVE)
    seen = getattr(kbs, "_SEEN", None)
    if hasattr(seen, "clear"):
        seen.clear()
    reset = getattr(lr, "_reset_router_state", None)
    if callable(reset):
        reset()
    yield
    if callable(reset):
        reset()
    if hasattr(seen, "clear"):
        seen.clear()


def _vcs_or_none():
    return importlib.import_module(VCS) if importlib.util.find_spec(VCS) is not None else None


def _b64sha(data):
    return base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")


def _set(mp, name, value):
    if value is None:
        mp.delenv(name, raising=False)
    else:
        mp.setenv(name, value)


def _companions(mp, *, deadline):
    s18._full_config(mp, flag=None, log_flag=None)
    for name in COMPANION_ON:
        mp.setenv(name, "true")
    for name in ROUTER_FLAGS:
        mp.delenv(name, raising=False)
    _set(mp, "ENABLE_FULL_STREAM_DEADLINE", "true" if deadline else None)


class _Critique:
    """The scripted answer at the `critique` site (every axis 9: no regeneration)."""

    def __init__(self):
        axes = getattr(_vcs_or_none(), "CRITIQUE_AXES", CRITIQUE_AXES_BASE)
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=json.dumps({a: 9 for a in axes})))]
        self.usage = SimpleNamespace(prompt_tokens=11, completion_tokens=7)


def _route_recorder(mp):
    sites = []
    real = lr.route

    async def _route(site, dispatch, client, **kwargs):
        sites.append(site)
        if site == "critique":
            return _Critique()
        return await real(site, dispatch, client, **kwargs)

    mp.setattr(lr, "route", _route)
    vcs = _vcs_or_none()
    if vcs is not None:
        mp.setattr(vcs, "get_client", lambda: SimpleNamespace(name="g10b-critic-client"))
    return sites


class _Persist:
    """Recorders on the comparisons insert and on the three follow-ups (plus the retired
    critique persist, recorded only where it exists)."""

    def __init__(self, mp):
        self.saved = []
        self.follow = []
        rec = self

        async def _save(**kwargs):
            rec.saved.append(kwargs)
            return {"id": "cmp-g10b"}

        mp.setattr(feedback_service, "save_comparison", _save)

        def _delete_cached(key):
            rec.follow.append("cache_bust")
            return True

        mp.setattr(feedback_service, "delete_cached", _delete_cached)

        def _track_event(**kwargs):
            rec.follow.append("track_event")

            async def _done():
                return {"success": True, "id": "evt-g10b"}
            return _done()

        mp.setattr(feedback_service, "track_event", _track_event)
        if hasattr(feedback_service, "_persist_verdict_critique"):
            def _persist_critique(comparison_id, crit_meta):
                rec.follow.append("persist_critique")

                async def _done():
                    return None
                return _done()

            mp.setattr(feedback_service, "_persist_verdict_critique", _persist_critique)

        class _Referrals:
            async def try_trigger_loop2(self, **kwargs):
                rec.follow.append("loop2")

        mp.setattr(referral_service, "ReferralService", _Referrals)

    def run(self, body):
        cid = asyncio.run(feedback_service.persist_comparison(full_response=body, query=s18.QUERY,
                                                              input_type="text", user_id=UID))
        asyncio.run(feedback_service.track_after_persist(cid, full_response=body, user_id=UID))
        return cid


def _run_row(body):
    row = cr.build_run_row(copy.deepcopy(body), "text")
    row = s18._normalize(row)
    row.pop("stage_timings", None)
    return row


def _snapshot(mp, critique):
    """REST + SSE (deadline OFF and ON) through the orchestrator driver, the routed site keys,
    the persisted payload, the follow-ups and the compare_runs row, ENABLE_SELF_CRITIQUE set to
    `critique` (None = unset)."""
    sites = _route_recorder(mp)
    out = {}
    rest = None
    for deadline in (False, True):
        _companions(mp, deadline=deadline)
        _set(mp, FLAG, critique)
        tag = "deadline_on" if deadline else "deadline_off"
        start = len(sites)
        rest = asyncio.run(s18._compare(mp, "rest", output_lang="ar"))
        events = asyncio.run(s18._compare(mp, "stream", output_lang="ar"))
        out["rest_" + tag] = s18._normalize(rest)
        out["stream_" + tag] = s18._normalize(events)
        out["sites_" + tag] = list(sites[start:])
    persist = _Persist(mp)
    cid = persist.run(rest)
    assert cid == "cmp-g10b" and len(persist.saved) == 1
    out["persisted"] = s18._normalize(persist.saved[0]["full_response"])
    out["persisted_is_body"] = persist.saved[0]["full_response"] is rest
    out["followups"] = list(persist.follow)
    out["run_row"] = _run_row(rest)
    return out


def _golden():
    assert GOLDEN.exists(), "the S81-22b golden is missing: " + str(GOLDEN)
    return json.loads(GOLDEN.read_text(encoding="ascii"))


def _has_crit_key(obj):
    if isinstance(obj, dict):
        return "_verdict_critique" in obj or any(_has_crit_key(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_has_crit_key(v) for v in obj)
    return False


def _scan_files():
    files = set(ROOT.glob("app/**/*.py")) | set(ROOT.glob("scripts/**/*.py")) | set(ROOT.glob("data/**/*.json"))
    files |= set(ROOT.glob("railway*.json")) | {ROOT / "app" / "legal" / "processors.json"}
    return sorted(files)


# =============================================================== RED rows (R1-R9b)

def test_r1_module_absent():
    """R1: app/services/verdict_critique_service.py is deleted."""
    assert importlib.util.find_spec(VCS) is None, "verdict_critique_service still exists"


def test_r2_no_reference_left():
    """R2: no app / scripts / data / railway / processors.json line names a retired identifier
    (the kept table name verdict_critiques is allowed)."""
    hits = []
    for path in _scan_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel == "app/services/verdict_critique_service.py":
            hits.append((rel, 0, "the module file"))
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            found = [x for x in RETIRED if x in line]
            if found:
                hits.append((rel, i, found[0]))
    assert hits == [], "%d retired references, first %r" % (len(hits), hits[:5])


def test_r3_orchestrator_surface():
    """R3: StructuredComparisonService has no _apply_self_critique / _verdict_critique_metadata
    and a fresh instance carries no _regen_model_downgraded."""
    cls = scs.StructuredComparisonService
    assert not hasattr(cls, "_apply_self_critique") and not hasattr(cls, "_verdict_critique_metadata")
    assert not hasattr(cls(), "_regen_model_downgraded")


def test_r4_save_path_surface():
    """R4: feedback_service has no _persist_verdict_critique / _without_verdict_critique /
    critic_model."""
    present = [n for n in ("_persist_verdict_critique", "_without_verdict_critique", "critic_model")
               if hasattr(feedback_service, n)]
    assert present == [], present


def test_r5_model_config_without_the_openai_critic():
    """R5: model_config has no critic_model and resolved_models() (every OPENAI_MODEL_* unset) is
    the four remaining roles."""
    assert not hasattr(mc, "critic_model")
    assert mc.resolved_models() == RESOLVED_MODELS_AFTER, mc.resolved_models()


def test_r6_preflight_ignores_the_retired_name(monkeypatch):
    """R6: role flags text + verdict ON, consent 3, the openai breaker OPEN, the anthropic one
    CLOSED: _llm_preflight_short_circuits() is False with ENABLE_SELF_CRITIQUE unset AND set to
    true (the critic leg is gone; the name is inert)."""
    monkeypatch.setenv("ENABLE_LLM_PREFLIGHT_BREAKER", "true")
    for role, name in lr.ROLE_FLAGS.items():
        _set(monkeypatch, name, "true" if role in ("text", "verdict") else None)
    monkeypatch.setattr(lr, "_consent_version", lambda: 3)
    monkeypatch.setattr(abs_, "openai_preflight_allows_compare", lambda: False)
    monkeypatch.setattr(lr, "_anthropic_preflight_allows", lambda: True)
    monkeypatch.delenv(FLAG, raising=False)
    assert scs._llm_preflight_short_circuits() is False
    monkeypatch.setenv(FLAG, "true")
    assert scs._llm_preflight_short_circuits() is False, "ENABLE_SELF_CRITIQUE still adds the critic's provider"


def test_r7_manifest_row():
    """R7: processors.json: the openai row's module list is the base list minus the deleted
    module; every other openai field, the row ids and the identity fields of every other row
    equal base; json.loads clean."""
    doc = json.loads((ROOT / "app" / "legal" / "processors.json").read_text(encoding="utf-8"))
    rows = doc["rows"]
    assert [r["id"] for r in rows] == PROCESSOR_IDS_BASE
    op = next(r for r in rows if r["id"] == "openai")
    assert {k: v for k, v in op.items() if k != "module"} == OPENAI_ROW_OTHER_BASE
    struct = [[r["id"], r["kind"], r["module"], r["hosts"], r["gate_flag"], r["personal_data"]]
              for r in rows if r["id"] != "openai"]
    blob = json.dumps(struct, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    assert _b64sha(blob) == OTHER_ROWS_DIGEST
    assert op["module"] == OPENAI_MODULES_AFTER, op["module"]


def test_r8_rest_inertness(monkeypatch):
    """R8: ENABLE_SELF_CRITIQUE=true with a critique answer available at the `critique` site:
    the routed site keys hold no 'critique', the REST body has no _verdict_critique and equals
    the unset body (deadline OFF and ON)."""
    on = _snapshot(monkeypatch, "true")
    off = _snapshot(monkeypatch, None)
    for tag in ("deadline_off", "deadline_on"):
        assert "critique" not in on["sites_" + tag], on["sites_" + tag]
        assert not _has_crit_key(on["rest_" + tag])
        assert on["rest_" + tag] == off["rest_" + tag], tag


def test_r9_stream_inertness(monkeypatch):
    """R9: the stream path with ENABLE_FULL_STREAM_DEADLINE unset: the event sequence and every
    payload with ENABLE_SELF_CRITIQUE=true equal the unset ones; no _verdict_critique."""
    on = _snapshot(monkeypatch, "true")
    off = _snapshot(monkeypatch, None)
    assert "critique" not in on["sites_deadline_off"], on["sites_deadline_off"]
    assert not _has_crit_key(on["stream_deadline_off"])
    assert [e[0] for e in on["stream_deadline_off"]] == [e[0] for e in off["stream_deadline_off"]]
    assert on["stream_deadline_off"] == off["stream_deadline_off"]


def test_r9b_stream_inertness_under_the_full_stream_deadline(monkeypatch):
    """R9b: R9 with ENABLE_FULL_STREAM_DEADLINE ON; plus the persisted payload, the follow-ups and
    the compare_runs row equal the unset ones."""
    on = _snapshot(monkeypatch, "true")
    off = _snapshot(monkeypatch, None)
    assert "critique" not in on["sites_deadline_on"], on["sites_deadline_on"]
    assert not _has_crit_key(on["stream_deadline_on"])
    assert on["stream_deadline_on"] == off["stream_deadline_on"]
    for key in ("persisted", "persisted_is_body", "followups", "run_row"):
        assert on[key] == off[key], key


# =============================================================== PIN rows (R10, P1-P3)

def test_r10_persisted_payload_is_the_body(monkeypatch):
    """R10 (PIN): persist_comparison over a body carrying no _verdict_critique hands
    save_comparison the SAME object, and track_after_persist runs exactly cache bust,
    track_event, Loop 2."""
    _companions(monkeypatch, deadline=False)
    body = asyncio.run(s18._compare(monkeypatch, "rest", output_lang="ar"))
    assert not _has_crit_key(body)
    persist = _Persist(monkeypatch)
    assert persist.run(body) == "cmp-g10b"
    assert len(persist.saved) == 1 and persist.saved[0]["full_response"] is body
    assert persist.follow == ["cache_bust", "track_event", "loop2"], persist.follow


@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=OFF_IDS)
def test_p1_off_identity_golden(monkeypatch, value):
    """P1 (PIN, the FULL configuration): ENABLE_SELF_CRITIQUE unset / blank / false / 0 / off /
    padded FALSE: the REST and SSE payloads (deadline OFF and ON), the routed site keys, the
    persisted payload, the follow-ups and the compare_runs row equal the golden recorded at
    base."""
    got = json.loads(json.dumps(_snapshot(monkeypatch, value)))
    want = _golden()["snapshot"]
    moved = sorted(k for k in set(got) | set(want) if got.get(k) != want.get(k))
    assert moved == [], moved
    assert got["persisted_is_body"] is True and got["sites_deadline_off"] == [] == got["sites_deadline_on"]


def test_p2_router_and_model_tables_kept():
    """P2 (PIN): llm_router ROLE_FLAGS, _ENTRY_ROLES, the SITES table (the `critique` SiteSpec
    included) and model_config's Claude role defaults equal base; the judge's Haiku selector
    anthropic_model('critic') is claude-haiku-5-5."""
    assert dict(lr.ROLE_FLAGS) == ROLE_FLAGS_BASE
    assert tuple(lr._ENTRY_ROLES) == ENTRY_ROLES_BASE
    got = {k: [s.role, s.claude_max_tokens, s.expects_json, s._schema is None] for k, s in lr.SITES.items()}
    assert got == SITES_BASE, got
    assert dict(mc._ANTHROPIC_ROLE_DEFAULTS) == ANTHROPIC_DEFAULTS_BASE
    assert mc.anthropic_model("critic") == "claude-haiku-5-5"
    assert callable(getattr(lr, "compare_refuses_for_consent", None))
    assert callable(getattr(lr, "camera_refuses_for_consent", None))


def test_p3_the_table_and_its_migration_kept():
    """P3 (PIN): migration 030 and its rollback are byte-identical to base (LF sha256) and no
    migration or rollback file is added or removed."""
    def lf(path):
        return _b64sha(path.read_bytes().replace(b"\r\n", b"\n"))

    assert lf(ROOT / "migrations" / "030_verdict_critiques.sql") == MIG030_LF_SHA256
    assert lf(ROOT / "migrations" / "rollback" / "030_verdict_critiques.sql") == MIG030_RB_LF_SHA256
    listing = "\n".join(sorted(os.listdir(ROOT / "migrations"))).encode("utf-8")
    rb_listing = "\n".join(sorted(os.listdir(ROOT / "migrations" / "rollback"))).encode("utf-8")
    assert _b64sha(listing) == MIG_LISTING_DIGEST, sorted(os.listdir(ROOT / "migrations"))
    assert _b64sha(rb_listing) == MIG_RB_LISTING_DIGEST
