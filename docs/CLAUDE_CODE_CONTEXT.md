# SmartCompare - Project Context Index

> **Last Updated:** 2026-09-28 (session 68b close)
>
> This document was split into topic files for easier navigation. Read what you need:

## Context Files

| File | Contents | When to Read |
|------|----------|--------------|
| [CONTEXT_ARCHITECTURE.md](CONTEXT_ARCHITECTURE.md) | Vision, tech stack, file structure, backend/frontend deep dive | Starting work or understanding the system |
| [CONTEXT_DATABASE_API.md](CONTEXT_DATABASE_API.md) | Database schemas, API endpoints | Working on DB or API changes |
| [CONTEXT_DECISIONS_BUGS.md](CONTEXT_DECISIONS_BUGS.md) | Architecture decisions, problems solved, known issues | Before making design decisions |
| [CONTEXT_REFERENCE.md](CONTEXT_REFERENCE.md) | Code snippets, deployment, testing guide, roadmap | Running tests, deploying, or planning next work |
| [CONTEXT_SESSION_LOG.md](CONTEXT_SESSION_LOG.md) | Full development history (sessions 1–68b; newest first from the top down to session 17, older and appended entries below) | Understanding why something was built a certain way |
| `investigations/<date>-session-NN-state.md` + its folder | The per-session state doc: measured facts, Fable rulings, the bounded harness and pipeline scripts, and the close files `NEXT_SESSION_PROMPT.md` / `APPLY_PACK_AHMED.md` / `DECISIONS_AHMED.md` (latest: `2026-09-26-session-68-state`) | Resuming a session, or before flipping any flag |

## Quick Links

- **Run tests:** `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
- **Deploy:** `git push origin main` (Railway auto-deploys)
- **Health check:** `curl https://web-production-58776.up.railway.app/health`
- **Main service:** `app/services/structured_comparison_service.py`
- **CLAUDE.md** has the condensed version of all critical patterns and rules; every feature flag's row (default, effect ON, flag-OFF identity, canary, preconditions) is in its `## Active runtime (SESSION …)` blocks, newest first — nothing flips without its row's preconditions
- **Tests are hermetic since #207:** `tests/conftest.py` installs a network guard; CI's ratchet (`scripts/netguard_ratchet.py` over `tests/.network_attempt_baseline.txt`) fails on any NEW egress node
