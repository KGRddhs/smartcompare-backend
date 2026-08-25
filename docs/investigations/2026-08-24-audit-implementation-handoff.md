# Audit implementation — session handoff (2026-08-24)

Continues the full-repo audit of `origin/main @ c630436`. Issues **#46–#81** were
filed from that audit; **#46, #58, #59** are implemented, pushed, and awaiting PR.
This file is the pick-up point.

## Branches pushed (no PRs opened yet, nothing merged, nothing deployed)

| Branch | Commit | Issue |
|---|---|---|
| `fix/46-dependency-lock` | `d6c52ab` | #46 — compiled universal dependency lock + CI drift gate |
| `fix/58-model-config` | `b9e962e` | #58 — OpenAI model ids in one env-overridable module |
| `fix/59-subtype-specs` | `48daac6` | #59 — subtype spec reconciliation + enriched-specs caching |

All three branch off `c630436` and are independent. `#58` and `#59` both touch
`extraction_service.py` in **disjoint regions** (model kwargs vs the alias table
and cleaning loop), so they merge in either order.

Work was done in the linked worktree `../smartcompare-fixes` so the main
checkout's dirty tree was never touched.

## Verification method used (repeat this for the remaining issues)

The repo's own comm gate, run per branch: the same test-file set on the branch and
on pristine `origin/main` (via `git stash`), diff the sorted FAILED sets, and
require **branch-only-NEW == []**.

| Branch | Files | main fails | branch fails | New | Passing |
|---|---|---|---|---|---|
| #58 | 87 | 40 | 40 | **0** | 1749 → 1802 |
| #59 | 156 | 40 | 40 | **0** | 2683 → 2697 |

`#46` changed zero `.py` files, and a floating install was proven byte-identical
to the lock for all 67 Windows-resolvable packages, so its outcome is unchanged
by construction.

---

## 🔴 Findings that are NOT yet filed as issues — read before planning tomorrow

### 1. CI has been RED on `main` for at least two months

Every run back to **2026-07-07** failed, including the live production commit
`c630436` (`gh run list --branch main`). The latest: **176 failed / 9,359 passed**.
So "tests green" has not been a functioning merge gate for the entire period the
audit covers. Two root causes, both now understood:

* `ModuleNotFoundError: No module named 'PIL'` — `tests/test_security_regression.py`
  imports PIL, which was declared only in the non-deployed `backend/pyproject.toml`.
  **Fixed on `fix/46-dependency-lock`** (pillow added to `requirements-dev.in`).
* `ImportError: cannot import name 'build_value_delta_text' / '_classify_value_match'`
  — the RED-by-design TDD stubs in `tests/test_value_math.py` (35 failures) that
  CLAUDE.md documents but CI never excluded. **Still unfixed** — belongs to #49.

Until #49 lands, expect ~40 pre-existing failures locally and a red CI.

### 2. The default test suite makes live network calls

A full free-unit run hangs. The stack shows `magento_graphql_service.py:275` and
`noon_service.py:170` performing **real `curl_cffi` requests to live retailer
sites** inside `concurrent.futures` workers, stuck in `curl.perform()` — which the
pytest timeout **cannot kill**, because a `wait_for` cannot cancel an executor
thread. That is issue **#70** reproducing inside the test suite.

With credentials present it is worse: Serper answered **403 Unauthorized** and
OpenAI **429 Too Many Requests**, and the retry loops blew the timeout. This is
issue **#48** (conftest loads the real `.env` with `override=True`) in action.

**Practical consequence:** run targeted file sets, not `pytest tests/`. The
exclusion pattern used here (adapter/network-heavy files) is recorded in the
commands above.

### 3. Production is running an unpinned dependency set that has already moved

The 2026-08-18 CI run installed **openai 3.2.0**; the floors resolve to **3.3.1**
today. `#46` freezes today's resolve, which is what the next Railway rebuild would
have installed anyway — it does not change what deploys, it makes it reproducible.

**Landmine found while verifying:** `app/services/openai_service.py:20` constructs
`AsyncOpenAI` at **module import**, and every current openai release raises
`OpenAIError: Missing credentials` when no key is in the environment. So
`import app.main` fails anywhere `OPENAI_API_KEY` is unset. Verified against
2.54.0, 3.2.0 and 3.3.1 — this is **version-independent and pre-existing**, not
caused by the lock. Making that client lazy is worth its own issue.

### 4. `app/config.py` is a trap, not just dead code

It declares **seven required pydantic fields** and instantiates `Settings()` at
module import (`:55`), so importing it raises `ValidationError` wherever those env
vars are absent. Issue #58's proposed implementation said to put the new model
config there; doing so would have broken every service import in CI. The model
config lives in `app/services/model_config.py` instead, which reads env with safe
defaults and requires no credentials. **Any future issue that says "add it to
app/config.py" needs the same correction.**

---

## What #58 deliberately did NOT do

Step 1 (indirection) only. The defaults are still `gpt-4o` / `gpt-4o-mini`, so
behavior is unchanged and flipping a model is now an env change with instant
rollback.

Step 2 (flip to `gpt-5-mini` / `gpt-5-nano`) is **not safe to do blindly.**
Researched against developers.openai.com on 2026-08-24:

* GPT-5 models are reasoning models and accept **only the default temperature**;
  `temperature=0` is a hard 400. The verdict call depends on `temperature=0` — an
  A/B in `docs/plans/2026-06-12-s2-shadow-results.md` attributes the whole
  winner-variance bucket to it. `sampling_kwargs()` drops the parameter for GPT-5
  ids, so the call will not 400 — but the determinism guarantee goes with it.
* `max_tokens` is rejected; `max_completion_tokens` is required.
  `token_limit_kwargs()` handles this.
* `max_completion_tokens` **counts invisible reasoning tokens against the same
  budget**. Carrying `1000` straight over can return empty content with
  `finish_reason="length"`. Raise the caps and/or pass `reasoning_effort="minimal"`.
* `gpt-5-pro` is Responses-API only and will fail on chat completions.

**Before flipping: smoke-test the target id against a real key.** The economics
are worth it (verdict ≈ $0.0224 → $0.0030; vision ≈ 30× cheaper on gpt-5-nano),
but this needs a live call, and OpenAI credits were exhausted at the time of writing.

## Suggested order for tomorrow

1. Open PRs for the three pushed branches (`gh pr create`), review, merge `#46` first.
2. **#49** — CI gates. Excluding the RED-by-design stubs is what finally turns CI
   green, which every later merge depends on.
3. **#48** — neutralize credentials in conftest; this is what makes the suite
   runnable end to end and stops tests touching the production cache.
4. **#60** — Serper budget gate (cheapest removal of a recurring outage).
5. Then the price-truth cluster: **#50 → #51**, **#53**.

Costed decision context for the scraper build-vs-buy question is unchanged: keep
the hybrid, and point owned-scraper investment at discovery (**#75**, the sitemap
channel that is already written and inert), not at rendering.
