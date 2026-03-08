# Smart Scoring Engine — Implementation Plan

**Date:** 2026-03-08 (Session 20)
**Design:** [2026-03-08-smart-scoring-engine-design.md](2026-03-08-smart-scoring-engine-design.md)
**Team:** 2 Opus agents per phase (not 4 simultaneous — Pro subscription limit management)

## Context Management Protocol

### Why 2 Agents, Not 4
Pro subscription tokens-per-minute limits mean 4 simultaneous Opus agents:
- Each carries its own context window
- All resume simultaneously after limit pauses → 60% spike → immediate re-pause
- 2 agents = half the token pressure = sustainable throughput

### Checkpoint Rule
After each phase completes:
1. Agent writes progress to `docs/plans/session20-progress.md` (what was done, what files changed)
2. CLAUDE.md and MEMORY.md get a 2-line update if relevant
3. New agents in next phase read ONLY the checkpoint file + the specific files they need
4. No agent should read more than 15 files in a single session

### If Limits Hit Mid-Phase
- Agents have written incremental progress to checkpoint file
- On resume: read checkpoint, continue from where they stopped
- Do NOT re-read files already processed — trust the checkpoint

## Phase 1: Scoring Engine + TS Fixes (2 agents)

### Agent 1: "backend-scoring" (Opus, bypassPermissions)
**Task:** Build `scoring_service.py` + integrate into comparison pipeline

**Steps:**
1. Create `app/services/scoring_service.py`:
   - `ScoringService` class with `compute_scores(products, specs, prices, reviews, preferences=None)`
   - 6 score dimensions: price, spec, review, value, reliability, popularity
   - Personalized weight calculation from `UserPreferences`
   - Category-specific spec scoring (use `CATEGORY_SPEC_SCHEMAS` keys as guide)
   - Normalization to 0-100 scale
   - Output: `ScoringResult` dataclass with breakdown

2. Integrate into `structured_comparison_service.py`:
   - After Phase 2 (reviews+rating), before `generate_comparison()`
   - Pass scores into verdict prompt so GPT references them
   - Add `scores` to response JSON

3. Add scoring types to response:
   - Update `text_routes.py` response to include `scores` object
   - Ensure backward compatibility (scores are additive, not breaking)

4. Write checkpoint to `docs/plans/session20-progress.md`

**Files touched:** `app/services/scoring_service.py` (new), `app/services/structured_comparison_service.py`, `app/services/extraction_service.py` (verdict prompt), `app/api/text_routes.py`

### Agent 2: "frontend-fixes" (Opus, bypassPermissions)
**Task:** Fix all 5 TS errors + add scoring types to frontend

**Steps:**
1. Fix TS errors:
   - `App.tsx(87,9)`: Fix ResultsScreenProps navigation params
   - `CameraScreen.tsx(61,22)`: Move `pickFromGallery` before usage or use useCallback
   - `ForgotPasswordScreen.tsx(18,10)`: Add `requestPasswordReset` export to authService.ts
   - `ResultsScreen.tsx(16,26)`: Fix `@expo/vector-icons` import

2. Add scoring types to `types.ts`:
   - `ScoreBreakdown`, `ProductScores`, `ScoringResult` interfaces
   - Update `ComparisonResult` to include optional `scores` field

3. Update ResultsScreen to display scores:
   - Score bar/badge in Overview tab showing overall score per product
   - Expandable breakdown showing dimension scores + weights used
   - Winner highlight with margin display

4. Run `npx tsc --noEmit` — must be ZERO errors

5. Write checkpoint

**Files touched:** `SmartCompareApp/src/types/types.ts`, `SmartCompareApp/src/screens/ResultsScreen.tsx`, `SmartCompareApp/src/screens/CameraScreen.tsx`, `SmartCompareApp/src/screens/ForgotPasswordScreen.tsx`, `SmartCompareApp/App.tsx`, `SmartCompareApp/src/services/authService.ts`

### Phase 1 Cross-QA Protocol:
- backend-scoring QAs frontend-fixes: check types match backend response, verify TS errors are truly fixed
- frontend-fixes QAs backend-scoring: check scoring logic correctness, verify integration doesn't break existing tests
- Reject criteria: failing tests, incorrect normalization math, type mismatches
- Idle agent writes tests (see Testing section below)

---

## Phase 2: SSE Streaming + Feedback (2 agents)

**Prerequisite:** Phase 1 checkpoint complete

### Agent 1: "backend-streaming" (Opus, bypassPermissions)
**Task:** Add SSE streaming endpoint

**Steps:**
1. Create SSE streaming in `text_routes.py`:
   - New endpoint: `GET /api/v1/text/compare/stream` (or `Accept: text/event-stream` on existing)
   - Use FastAPI `StreamingResponse` with `media_type="text/event-stream"`
   - Event sequence: status → specs → reviews → scores → verdict → complete
   - Keep existing non-streaming endpoint working (backward compat)

2. Modify comparison pipeline for incremental results:
   - `compare_from_text()` yields partial results via callback or async generator
   - Each phase completion triggers an SSE event
   - Final `complete` event sends full JSON (same as current response)

3. Add health check endpoint for cold-start prevention:
   - Document the Railway cron setup (or add a lightweight keep-alive)

4. Write checkpoint

**Files touched:** `app/api/text_routes.py`, `app/services/structured_comparison_service.py` (async generator refactor)

### Agent 2: "feedback-system" (Opus, bypassPermissions)
**Task:** Feedback collection + event tracking

**Steps:**
1. Create Supabase tables via migration:
   - `comparison_feedback`: id, user_id (nullable), comparison_id (nullable), useful (bool), mattered_most (text[]), change_suggestion (text), created_at
   - `user_events`: id, user_id (nullable), event_type (text), event_data (jsonb), comparison_id (nullable), session_id (text), created_at
   - RLS: users can insert own feedback, read own feedback

2. Create `app/services/feedback_service.py`:
   - `save_feedback(user_id, comparison_id, useful, mattered_most, change_suggestion)`
   - `track_event(user_id, event_type, event_data, comparison_id)`
   - Both fire-and-forget (asyncio.create_task pattern)

3. Create `app/api/feedback_routes.py`:
   - `POST /api/v1/feedback` — save feedback (auth optional, anonymous allowed)
   - `POST /api/v1/events` — batch event tracking (auth optional)

4. Register router in `app/main.py`

5. Write checkpoint

**Files touched:** `app/services/feedback_service.py` (new), `app/api/feedback_routes.py` (new), `app/main.py`

### Phase 2 Cross-QA Protocol:
- backend-streaming QAs feedback-system: verify table schema, RLS policies, endpoint security
- feedback-system QAs backend-streaming: verify SSE events fire correctly, backward compat intact
- Idle agent writes tests

---

## Phase 3: Frontend Integration + Final QA (2 agents)

**Prerequisite:** Phase 2 checkpoint complete

### Agent 1: "frontend-streaming" (Opus, bypassPermissions)
**Task:** Progressive rendering with SSE + feedback UI

**Steps:**
1. Create SSE client in `api.ts`:
   - `streamComparison(query, options)` using fetch + ReadableStream
   - Parse SSE events, dispatch to state updates
   - Fallback to non-streaming if SSE fails

2. Update HomeScreen.tsx:
   - Switch from single fetch to stream
   - Navigate to ResultsScreen on first `specs` event (not `complete`)

3. Update ResultsScreen.tsx:
   - Progressive tab population (specs first, reviews second, scores third)
   - Loading skeleton for tabs not yet received
   - Verdict streams in word-by-word or sentence-by-sentence

4. Add FeedbackCard component:
   - Shown below results after verdict loads
   - Thumbs up/down (1-tap feedback)
   - "What mattered most?" multi-select chips (price, specs, reviews, brand, value)
   - Optional text field "What would you change?"
   - Submit → `POST /api/v1/feedback` fire-and-forget

5. Add event tracking:
   - Track: tab_switch, source_click, save, share, result_view_duration
   - Batch send via `POST /api/v1/events` on screen unmount

**Files touched:** `SmartCompareApp/src/services/api.ts`, `SmartCompareApp/src/screens/HomeScreen.tsx`, `SmartCompareApp/src/screens/ResultsScreen.tsx`, `SmartCompareApp/src/components/FeedbackCard.tsx` (new)

### Agent 2: "test-qa" (Opus, bypassPermissions)
**Task:** Test coverage + final QA of all phases

**Steps:**
1. Write tests for scoring_service.py:
   - Test each score dimension independently
   - Test personalized weight adjustments
   - Test normalization edge cases (missing data, zero prices, null ratings)
   - Test category-specific scoring
   - Target: 90%+ coverage on scoring_service.py

2. Write tests for feedback endpoints:
   - Test feedback submission (auth + anonymous)
   - Test event tracking (batch + single)
   - Test RLS (can't read other users' feedback)

3. Write tests for SSE streaming:
   - Test event sequence
   - Test fallback to non-streaming
   - Test partial response handling

4. Run FULL test suite: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
   - ALL existing 505+ tests must pass
   - New tests must pass
   - Target: 80%+ coverage on ALL new code

5. Final QA checklist:
   - `python -m py_compile` on every changed Python file
   - `npx tsc --noEmit` = 0 errors
   - Verify scoring produces deterministic results (same input → same output)
   - Verify SSE events fire in correct order
   - Verify feedback writes to Supabase

**Files touched:** `tests/test_scoring_service.py` (new), `tests/test_feedback.py` (new), `tests/test_streaming.py` (new)

### Phase 3 Cross-QA:
- frontend-streaming QAs test-qa: verify test assertions are meaningful (not just passing)
- test-qa QAs frontend-streaming: run frontend type check, review SSE client logic, verify event tracking fires

---

## Testing Requirements (80% coverage minimum)

### New Test Files:
| File | Tests | Coverage Target |
|------|-------|-----------------|
| `tests/test_scoring_service.py` | ~30 | 90% of scoring_service.py |
| `tests/test_feedback.py` | ~15 | 80% of feedback_service.py + feedback_routes.py |
| `tests/test_streaming.py` | ~12 | 80% of streaming logic |
| `tests/test_ts_fixes.py` | N/A | TS errors verified via `npx tsc --noEmit` |

### Red-Green Protocol:
Idle agents write tests BEFORE implementation exists (red), then verify they pass after (green):
1. Write test → assert expected behavior → test FAILS (red)
2. Implement feature
3. Run test → test PASSES (green)
4. If test still fails → implementation is wrong, send back

---

## Checkpoint File Template

`docs/plans/session20-progress.md` should follow this format:

```markdown
# Session 20 Progress

## Phase 1 Status: [pending|in_progress|complete]
### backend-scoring
- [x] scoring_service.py created
- [x] integrated into pipeline
- [ ] tests written
- Files changed: app/services/scoring_service.py, ...
- Notes: <any issues or decisions>

### frontend-fixes
- [x] TS errors fixed (0 remaining)
- [ ] scoring types added
- Files changed: ...

## Phase 2 Status: [pending]
...
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Pro limits pause mid-phase | High | Medium | 2 agents not 4, checkpoint files, incremental progress |
| SSE not working in Expo/RN | Medium | High | Test early in Phase 2; fallback to polling if needed |
| Scoring normalization produces weird results | Low | Medium | Extensive unit tests, edge case coverage |
| Feedback table grows unbounded | Low | Low | Add retention policy later (delete >90 days) |
| Existing tests break from pipeline refactor | Medium | High | Run full suite after each phase, never merge broken |

## Deliverables Checklist

- [x] Proposed architecture (design doc)
- [x] Latency reduction plan (SSE streaming + cold start fix)
- [x] Real-time vs async vs precompute split (in design doc)
- [x] Personalization/scoring design (scoring_service.py spec)
- [ ] TS + ResultScreen fix (Phase 1, Agent 2)
- [ ] Learning loop (feedback tables + event tracking, Phase 2-3)
- [x] Risks and priorities (risk register above)
