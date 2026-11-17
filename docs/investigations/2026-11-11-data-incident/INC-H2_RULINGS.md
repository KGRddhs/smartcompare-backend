# RULINGS_INC_H2 (orchestrator S96-FIX, 2026-11-17 ~09:00 AST)

H2R-1 The relay accepted the spec at 08:45 AST: part A unflagged, part B behind ENABLE_SMART_PICK_BHD_ONLY (default OFF), part (b) dropped. SMALL class: there is no separate spec review. The spec stands, as amended by these rulings.
H2R-2 "Spec section 5" in your prompt means the spec's "RED rows" section. The only new test file is tests/test_inc_h2_smart_pick_guard.py.
H2R-3 Base: PR #418 head 8bb97fe0 (main bd0500a3 plus INC-P2), detached in the real worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-h2.
  - `_pair_price_sizes_differ` exists there.
  - Part A rows fail at base on the selector's behaviour, never on a missing helper.
  - The flag reader for part B does not exist at base: assert its absence through getattr or find_spec, as an AssertionError.
H2R-4 The flag idiom: the same reader shape as the other per-call readers in home_routes.py (for example smart_pick_verdict_caption_enabled). Copy its env parsing exactly. Default OFF.
H2R-5 The route rows R1 and R2 drive the Home endpoint that calls `_select_smart_pick` (home_routes :821 at base) with the DB reader patched. Find the real patch target by reading the code; never hit the network.
H2R-6 Part B is a prerequisite for the link lane's later INC-U1b: it needs ENABLE_SMART_PICK_BHD_ONLY on. Record this in the flip note only; it adds no rows.
H2R-7 Comm set as in the spec. The base failures are recorded at 8bb97fe0; reuse <SP>/INC-P2_rb2/comm/*.xml for files already covered there if their bytes are unchanged, and say which.
H2R-8 BOX: no box gate until <SP>/INC-H2/BOX_GO exists (the BOX RULE in your prompt).
H2R-9 (added 09:20 for GREEN and the adversary; the RED agent may have started before it): a test file that sets ENABLE_LLM_SPEND_BREAKER (or any PROD_ON list carrying it) must reset llm_spend_breaker._reset_spend_breaker_state() after each test, or CI's one-process run fails the /health readers (P2R-39). The same holds for llm_router._reset_router_state() if a role flag is walked ON.
