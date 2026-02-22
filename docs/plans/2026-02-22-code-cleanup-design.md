# Code Cleanup Design

**Date**: 2026-02-22
**Status**: Approved

## Goal

Remove dead code, fix corrupted .gitignore, consolidate pyproject.toml with requirements.txt, and add gitignore patterns for ~80 untracked debug files. Zero behavior change.

## Scope

### 1. Dead Code Removal (~200 lines)

Remove from `app/services/structured_comparison_service.py`:
- `REVIEW_SITES` class variable (~10 lines) — only used by dead Tier 0 methods
- `_get_expert_review()` method (~80 lines) — Tier 0, defined but never called
- `_parse_review_jsonld()` method (~25 lines) — only called by `_get_expert_review`
- `_extract_rating_from_jsonld_item()` method (~85 lines) — only called by `_get_expert_review`
- Unused `Tuple` import from typing

Remove from `app/services/extraction_service.py`:
- Unused `Tuple` import from typing

### 2. Fix `.gitignore`
- Remove PowerShell heredoc wrapper (line 1: `@"`, line 31: `"@ | Out-File...`)
- Add patterns for untracked debug artifacts:
  - `response_*.json` — test response dumps
  - `/test_*.py` — root-level test scripts (NOT `tests/` directory)
  - `/extract_*.py` — root-level extraction scripts
  - `import_batches/` — SQL batch import files
  - `.expo/` — Expo cache
  - `nul` — Windows null device artifact
  - `*.jpg` / `*.png` in root — test images

### 3. Consolidate `pyproject.toml`
- Authority: `requirements.txt` (what Railway deploys)
- Update all pyproject.toml versions to match requirements.txt
- Add missing packages: `beautifulsoup4`, `lxml`, `curl_cffi`
- Remove `pillow` (not in requirements.txt, not used by backend)
- Fix openai: `>=1.12.0` (not `>=2.17.0`)

### 4. Legacy Routes — SKIP
- No TypeErrors found in deployed `app/api/routes.py`
- Documentation was outdated; issue already resolved

## Team Structure

2 Opus agents (small scope, 2 is sufficient). Cross-QA: each reviews the other's work.

| Agent | Owns (writes) | QAs (reviews) |
|-------|--------------|---------------|
| Agent A | Dead code removal (structured_comparison_service.py + extraction_service.py) | Agent B's work |
| Agent B | .gitignore fix + pyproject.toml consolidation | Agent A's work |

## Success Criteria

- `python -m py_compile app/services/structured_comparison_service.py` passes
- `python -m py_compile app/services/extraction_service.py` passes
- All 120 existing tests still pass: `python -m pytest tests/ -v -m "unit or live_unit or live_db"`
- `.gitignore` has no PowerShell syntax, `git status` is clean (only expected files)
- `pyproject.toml` dependencies match `requirements.txt` exactly
- ~200 lines of dead code removed
- Zero behavior change
