# SmartCompare - Project Context Index

> **Last Updated:** March 3, 2026 (Session 14)
>
> This document was split into topic files for easier navigation. Read what you need:

## Context Files

| File | Contents | When to Read |
|------|----------|--------------|
| [CONTEXT_ARCHITECTURE.md](CONTEXT_ARCHITECTURE.md) | Vision, tech stack, file structure, backend/frontend deep dive | Starting work or understanding the system |
| [CONTEXT_DATABASE_API.md](CONTEXT_DATABASE_API.md) | Database schemas, API endpoints | Working on DB or API changes |
| [CONTEXT_DECISIONS_BUGS.md](CONTEXT_DECISIONS_BUGS.md) | Architecture decisions, problems solved, known issues | Before making design decisions |
| [CONTEXT_REFERENCE.md](CONTEXT_REFERENCE.md) | Code snippets, deployment, testing guide, roadmap | Running tests, deploying, or planning next work |
| [CONTEXT_SESSION_LOG.md](CONTEXT_SESSION_LOG.md) | Full development history (Sessions 1-13) | Understanding why something was built a certain way |

## Quick Links

- **Run tests:** `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
- **Deploy:** `git push origin main` (Railway auto-deploys)
- **Health check:** `curl https://smartcompare-backend-production.up.railway.app/health`
- **Main service:** `app/services/structured_comparison_service.py`
- **CLAUDE.md** has the condensed version of all critical patterns and rules
