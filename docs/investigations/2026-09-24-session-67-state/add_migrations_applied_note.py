"""Record the 2026-09-24 migration applies (037/038/040/041) in the four docs files. Byte-safe, line endings preserved."""
import io
import sys

W = sys.argv[1]
FLAG_LINE = sys.argv[2] if len(sys.argv) > 2 else "`ENABLE_CONSENT_PERSIST=true` was set on `web` right after (its own redeploy)"

NOTE = (
    "**MIGRATIONS APPLIED 2026-09-24 17:50–18:35 local** (Ahmed's clicks in the Supabase SQL editor, driven from the "
    "browser pane; every step measured, the pre-state first): **040** → `cleanup_expired_ratings()` is SECURITY INVOKER "
    "(`prosecdef=false` — the review's \"SECURITY DEFINER\" was wrong; body `DELETE FROM rating_cache WHERE expires_at < NOW()`), "
    "proacl `{=X,postgres,anon,authenticated,service_role}` → `{postgres,service_role}`; anon GET on the rpc 25006 → 42501. "
    "**037** → `delete_user_cascade` + `increment_lifetime_comparisons` `{postgres,service_role}` only, `resolve_referral_code` "
    "`{postgres,anon,authenticated,service_role}` (PUBLIC removed, anon kept by design); the anon-executable SECURITY DEFINER census "
    "= `resolve_referral_code` alone; anon POST `rpc/delete_user_cascade` (nil uuid) 204 → 42501; "
    "`tests/test_migration_037_security_definer_grants.py -m live_db` 4 passed. All three had carried the stock explicit grants, so a "
    "PUBLIC-only revoke would have been a no-op — 037's `FROM PUBLIC, anon, authenticated` was exactly right. **037's RLS half was a "
    "no-op by 037's own rule:** `user_events` already had RLS enabled (owner postgres, force off) and FOUR policies — the leak was the "
    "out-of-band policy \"Service role can read all events\" (PERMISSIVE, SELECT, {public}, USING (true); service_role bypasses RLS, so "
    "it granted every role, anon included: 147 rows), plus a harmless out-of-band duplicate of events_insert (\"Users can insert own "
    "events\", left in place). **041** (`migrations/041_user_events_drop_public_select_policy.sql`, PR #199 → `3b0ea5d7`, test-first, "
    "rollback re-creates the policy verbatim) dropped it BY NAME → three policies remain, anon `count=exact` 147 → 0. **038** → the "
    "three nullable consent columns exist on `users`. NOT applied: 035, 036 (re-run the idempotent 037 after a late 036); 039 stays "
    "reserved. " + FLAG_LINE + "; `ENABLE_CONSENT_REQUIRED` still waits for the smoke-probe consent fields (and phones on the new OTA)."
)


def patch(rel, old, new, must=True):
    p = W + "/" + rel
    b = io.open(p, "rb").read()
    t = b.decode("utf-8")
    n = t.count(old)
    if "MIGRATIONS APPLIED 2026-09-24 17:50" in t and rel.endswith(("CLAUDE.md", "CONTEXT_SESSION_LOG.md")):
        print("already patched:", rel)
        return
    assert n == 1, (rel, old[:50], n)
    io.open(p, "wb").write(t.replace(old, new).encode("utf-8"))
    print("patched:", rel)


# CLAUDE.md — the Migrations paragraph
patch("CLAUDE.md",
      "Applied 010–032 (all via MCP since 013; 027–032 = Bundle B B.1, dispatcher-applied 2026-06-10).",
      "Applied 010–032 (all via MCP since 013; 027–032 = Bundle B B.1, dispatcher-applied 2026-06-10); 033/034 applied 2026-09-06; "
      "**037, 038, 040, 041 applied 2026-09-24 (session 67, SQL editor, each verified — census and proofs in the SESSION 67 "
      "Active-runtime block)**; 035/036 UNAPPLIED; 039 reserved.")
# CLAUDE.md — the SESSION 67 Active-runtime block, new bullet before the hazards bullet
patch("CLAUDE.md",
      "- **Four latent hazards the CI-red PRs exposed are issues, not fixed in code:**",
      "- " + NOTE + "\r\n- **Four latent hazards the CI-red PRs exposed are issues, not fixed in code:**")
# session log — after the production paragraph of the SESSION 67 entry
p = W + "/docs/CONTEXT_SESSION_LOG.md"
t = io.open(p, "rb").read().decode("utf-8")
if "MIGRATIONS APPLIED 2026-09-24 17:50" not in t:
    lines = t.split("\r\n")
    idx = next(i for i, l in enumerate(lines) if l.startswith("**Production, measured 2026-09-24 ~15:00"))
    lines.insert(idx + 1, "")
    lines.insert(idx + 2, NOTE)
    io.open(p, "wb").write("\r\n".join(lines).encode("utf-8"))
    print("patched: docs/CONTEXT_SESSION_LOG.md")
# state doc — Ahmed's list item 4
patch("docs/investigations/2026-09-24-session-67-state.md",
      "4. Migrations: 038 (W3-16) before `ENABLE_CONSENT_PERSIST`; 037 and 040 any time (run the 040 header census first); 039 reserved.",
      "4. ~~Migrations~~ — DONE 2026-09-24 17:50–18:35: 040, 037, 038 and the new 041 applied and verified (the measured census, the "
      "no-op RLS half of 037 and the policy leak 041 closes are in CLAUDE.md's SESSION 67 block and in "
      "`2026-09-24-session-67-state/APPLY_PACK_AHMED.md` §A). Still unapplied: 035, 036; 039 reserved.")
# apply pack — §A heading gets the DONE line
patch("docs/investigations/2026-09-24-session-67-state/APPLY_PACK_AHMED.md",
      "## A. Migrations — Supabase SQL editor, in this order",
      "## A. Migrations — DONE 2026-09-24 17:50–18:35 (kept as the record of what was run and measured)\n\n" + NOTE.replace("\r\n", "\n") +
      "\n\n### Original plan — Supabase SQL editor, in this order")
