"""Assemble the W4-11 PR body: the round-3 pr_text + Fable's ship addendum, attribution last."""
NSP = "C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/0a2845de-abfe-4bca-b433-df4ce9787ab5/scratchpad"
src = open(NSP + "/pr_text_w4_11_r3.md", encoding="utf-8").read().rstrip()
ATTR = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
if src.endswith(ATTR):
    src = src[: -len(ATTR)].rstrip()
addendum = """
### Orchestrator addendum (Fable, ship time 2026-09-27)
- **Pipeline:** red (52 reds / 25 pins / 40 kills at `58a86b3c`) -> Fable red-gate rulings R16-R24 -> green -> adversary r0 SOUND (8 minors) -> fix r1 -> adversary r1 SOUND (2 minors) -> fix r2 -> adversary r2 SOUND (1 minor: the unflagged name fence raised on non-string parts) -> Fable polish rulings R25-R27 -> fix r3 -> adversary r3 SOUND (2 pin gaps). Every adversary left the worktree byte-identical to the fixer's reported shas.
- **Two pin gaps from adversary r3 closed by the orchestrator (test rows only, no app change):** `tests/test_prompt_fence.py::test_name_fence_coerces_non_string_parts` gained the `name_int`, `variant_int` and `brand_list_two` rows and a new `test_name_fence_sanitises_a_coerced_list_brand` (a hostile list brand is coerced, then sanitised); `tests/test_prompt_truth.py::test_truth_cons_counter_vocabulary_per_phrase` gained `two_phrases_one_string` (two phrases in ONE cons string count once). On the final bytes the adversary's five surviving mutants now redden: E1 (name-slot coercion dropped) 2 failed, E2 (variant slot) 2 failed, E3 (per-match count) 1 failed, E4 (list joined without a space) 4 failed, E5 (list brand not sanitised) 2 failed; every restore sha-verified. Unit files: 138 passed, 1 xfailed in each of the four states, `[netguard] blocked 0`.
- **Formatting at commit time:** the repo's pre-commit black allowlist covers `app/services/prompt_personalities.py`, so it was black-formatted before the commit (26 insertions / 9 deletions, line wraps and one quote style, no string content changed; sha `d394ba84` -> `6c336ae6`); the unit files were re-run on the formatted bytes (138 passed, 1 xfailed).
- **Post-rebase ship checks** (onto main `d66444f2`; the rebase touched none of this unit's files): the four unit files and the 38-file CI-order set in ONE process per state (unset / TRUTH / MAY_DECLINE / both), the netguard ratchet, the T-G1 digest gate, ruff E9,F63,F7,F82 and py_compile - results in the PR's first comment if they differ from the fixer's numbers above.
- **Flags on main after this merge (default OFF, read per call):** `ENABLE_VERDICT_PROMPT_TRUTH`, `ENABLE_PRICE_FALLBACK_MAY_DECLINE`. Nothing is flipped; Railway and Supabase untouched. The TRUTH flip needs Ahmed's explicit yes on zero-cons verdicts (see Activation notes).
"""
out = src + "\n" + addendum.rstrip() + "\n\n" + ATTR + "\n"
open(NSP + "/prbody_w4_11.md", "w", encoding="utf-8").write(out)
print("wrote prbody_w4_11.md", len(out))
