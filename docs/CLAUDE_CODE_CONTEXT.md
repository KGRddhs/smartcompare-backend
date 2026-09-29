# MYEZ (ميّز) - Project Context Index (repo: smartcompare; identifiers stay qaren)

> **Last Updated:** 2026-09-29 (session 69 close)
>
> This document was split into topic files for easier navigation. Read what you need:

## Context Files

| File | Contents | When to Read |
|------|----------|--------------|
| [CONTEXT_ARCHITECTURE.md](CONTEXT_ARCHITECTURE.md) | Vision, tech stack, file structure, backend/frontend deep dive | Starting work or understanding the system |
| [CONTEXT_DATABASE_API.md](CONTEXT_DATABASE_API.md) | Database schemas, API endpoints | Working on DB or API changes |
| [CONTEXT_DECISIONS_BUGS.md](CONTEXT_DECISIONS_BUGS.md) | Architecture decisions, problems solved, known issues | Before making design decisions |
| [CONTEXT_REFERENCE.md](CONTEXT_REFERENCE.md) | Code snippets, deployment, testing guide, roadmap | Running tests, deploying, or planning next work |
| [CONTEXT_SESSION_LOG.md](CONTEXT_SESSION_LOG.md) | Full development history (sessions 1–69; newest first from the top down to session 17, older and appended entries below) | Understanding why something was built a certain way |
| `investigations/<date>-session-NN-state.md` + its folder | The per-session state doc: measured facts, Fable rulings, specs and the close files (latest: `2026-09-29-session-69-state` — its folder carries `APP_STORE_LAUNCH_RUNBOOK.md` (Ahmed's ordered launch checklist: decisions D1–D11 and the 8 legal inputs in §3 B; D12–D14 — spelling, Arabic form, domain/emails — are listed in CLAUDE.md's SESSION 69 block), `LLM_PROVIDER_DECISION.md`, the unit specs, the migration-042 SQL files (`APPLY_042_1_PRECHECK` / `_2_ONE_PASTE` / `_3_POSTCHECK`) and `verify_after_credits.py`; the bounded harness and pipeline scripts stay in `2026-09-26-session-68-state/scripts/` (pr_rest.py, ci_logs.py, issue_rest.py, harvest.py) and `2026-09-26-session-68-state/harness-2026-09-27/` (pyt.py, stall_monitor.py)) | Resuming a session, or before flipping any flag |

## Quick Links

- **Run tests:** `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
- **Deploy:** backend `web` = merge to main (Railway auto-deploys); the static landing (`qaren-landing`) is NOT redeployed by a merge — `railway up landing --path-as-root -s qaren-landing -d` from the repo root (Ahmed); mobile JS = `eas update` (today `preview`; after the store build, hotfixes go to `--branch production`), native changes = a new `eas build` (see skill `qaren-eas-deploy`)
- **Health check:** `curl https://web-production-58776.up.railway.app/health`
- **Main service:** `app/services/structured_comparison_service.py`
- **CLAUDE.md** has the condensed version of all critical patterns and rules; every feature flag's row (default, effect ON, flag-OFF identity, canary, preconditions) is in its `## Active runtime (SESSION …)` blocks, newest first — nothing flips without its row's preconditions
- **Tests are hermetic since #207:** `tests/conftest.py` installs a network guard; CI's ratchet (`scripts/netguard_ratchet.py` over `tests/.network_attempt_baseline.txt`) fails on any NEW egress node
