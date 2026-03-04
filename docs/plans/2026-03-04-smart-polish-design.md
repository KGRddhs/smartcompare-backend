# Smart Polish: AI Quality & Bug Fixes

**Date:** 2026-03-04 (Session 17)
**Approach:** A — Smart Polish (zero additional cost)
**Goal:** Fix broken Expo build, improve AI output quality through prompt engineering and stricter validation, fix broken retailer URLs

## Scope

| # | Item | Type | Owner | QA By |
|---|------|------|-------|-------|
| 1 | Fix Expo startup (expo-image-manipulator plugin error) | Bug fix | agent-expo-urls | agent-specs |
| 2 | Tighten review extraction prompt (authenticity, citations) | Prompt eng | agent-prompts | agent-expo-urls |
| 3 | Tighten spec citation verification (exact numeric match) | Code + prompt | agent-specs | agent-prompts |
| 4 | Fix broken retailer URLs (validate, stop search-page fallbacks) | Code | agent-expo-urls | agent-specs |
| 5 | Improve comparison verdict prompt (trade-offs, numeric diffs) | Prompt eng | agent-prompts | agent-expo-urls |

**Cost impact:** $0 additional per comparison — stays at ~$0.010

## Team Structure

3 Opus agents with cross-QA:

- **agent-expo-urls**: Owns #1 + #4, QAs #2 + #5
- **agent-prompts**: Owns #2 + #5, QAs #3
- **agent-specs**: Owns #3, QAs #1 + #4

## Technical Details

### #1 Expo Fix
- Remove `expo-image-manipulator` from `plugins` array in `app.json`
- Verify `npx expo start` launches without errors
- Library still works as a regular import (not a config plugin)

### #2 Review Prompt Improvements
- Require `[snippet_N]` citation for every praise/complaint
- Add examples of good (specific) vs bad (generic) output in prompt
- Replace synthetic `rating_distribution` estimates with "not available" when no real data
- Require product-specific evidence, not generic claims
- Mandate user_quotes come from identifiable snippet text

### #3 Spec Citation Verification
- Tighten `_verify_spec_citations()` — exact numeric matches for quantifiable specs
- Current: 50% keyword overlap passes. New: numeric values must match exactly
- Fallback: if citation fails, downgrade confidence to "unverified" and flag which specs failed
- Improve cross-validation against Shopping titles for numeric fields

### #4 URL Fixes
- Stop returning `_build_retailer_url()` search-page URLs as product links
- Extract actual retailer domain URL from Serper Shopping `link` (strip Google redirect)
- When no direct link: return `null` instead of generic search URL
- Frontend: if `url` is null, show "Search on [retailer]" with Google Shopping search link

### #5 Verdict Prompt Improvements
- Mandate trade-off structure: "A wins for [use case], B wins for [use case]"
- Require numeric differences: "15% faster" not "better performance"
- Add "who should buy which" section with specific user profiles
- Add examples of strong vs weak verdicts in prompt

## Workflow

1. Each agent implements their items
2. While waiting for QA assignment, write red-green tests (target 80%+ coverage on changes)
3. QA the assigned teammate's work
4. If issues found → send back with specific feedback
5. Fix and re-QA until approved
6. Team lead does final integration check

## Files Modified

- `SmartCompareApp/app.json` — remove plugin entry
- `app/services/extraction_service.py` — review + verdict prompts
- `app/services/structured_comparison_service.py` — spec verification + URL logic
- `SmartCompareApp/src/screens/ResultsScreen.tsx` — handle null URLs gracefully
- `tests/` — new test files for changed behavior
