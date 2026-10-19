# RED gate S78-F8 (orchestrator, 2026-10-17 ~07:52 AST): PASS. GREEN waits for the owner's yes.

**Inputs.** RED workflow `wf_870c0f35-25a` (one Opus agent, model verified `claude-opus-5-5` in its first
transcript; 57 min, 52 tool calls, 41 bounded runs, 0 TIMEOUTs). Report: `runs/s79_f8_red_wf_870c0f35.json`.
Spec `sha256 bfd14cc0...`, review, and rulings `RULINGS_S78_F8_SPEC_REVIEW.md` (R1-R13).

**Files (sha256 first 16).** `tests/test_s78_all_timeout_cap_as_timeout.py` `579af2dec504e076` (43,546 bytes,
pure ASCII, LF, 936 lines; 35 test defs, 10 parametrize decorators = 84 nodes); `.qa-s78/comm_set.txt`
`c349146abe142a7e` (230 files); `.qa-s78/ci_order_set.txt` `fd3103d18d54e63e` (15 files);
`.qa-s78/proto_S78-F8.patch` `61c12297ff26e2ed` (the satisfiability prototype, 106 insertions, reference only).

**Re-measured by the orchestrator at base `e0f3e475`** (bounded runner, conftest netguard, flag unset):

```
================= 58 failed, 26 passed, 12 warnings in 43.06s =================
[netguard] blocked 4 attempt(s) from 2 node(s)   (F15[on]/[off]: the sentinel neutralized.supabase.invalid:443 only)
[pyt] tag=gate-f8-red start=2026-10-17 07:49:24 end=2026-10-17 07:50:11 elapsed=48s bound=600s status=FAIL rc=0->1
```

The failed-id set equals the RED agent's base run exactly (`comm` both ways empty). All 58 failures are
AssertionError (the agent's logs: 58 of 58 in both flag states; no ImportError / AttributeError / KeyError /
collection error). Secret and personal-data scan over the test file: key shape 0, `@gmail` 0, `+973` 0,
email-like 0, 8-digit runs 0, owner / controller names 0. `git status --short`: only the untracked test file;
no scratch worktree left (`git worktree list` has no `proto` entry); no `.env` under the agent's scratchpad.

**RED agent's measurements (its [pyt] lines are in the report):**
- Base: 58 failed / 26 passed in both flag states (the failed set identical: the autouse fixture delenvs the flag).
- Prototype (a detached scratch worktree at e0f3e475, the ruled design incl. R2's eager record): unit file
  84/84 flag unset (58 s), 85/85 with the flag exported ON plus the FY25 node (64 s); ruff E9/F63/F7/F82 and
  py_compile clean; `git diff --stat` 106 insertions, 0 deletions, CRLF kept.
- Mutation non-vacuity on the prototype bytes: 31 of 31 mutants killed (M1-M29 with M16a/b and M22a/b), every
  restore sha-verified; M30 survived and is EQUIVALENT by ruling R2 (recorded). Notable killers: M1 11 nodes,
  M14 13, M22a 21, M26 (the D5 line at ERROR) 13, M27 (7.2 removed) 2, M28 (eager callbacks absent) 5,
  M29 (a cancelled task recorded) 3; M3, M5, M12, M13, M19, M21, M24 have a single killer each.
- Netguard ratchet (R10): `scripts/netguard_ratchet.py` rc=0, "2 attempting node(s), baseline 205", the two
  F15 nodes attempt sentinel hosts only ("allowed for now"). F15 stays.
- Comm set (R8): 230 files = the spec's 218 + the 12 symbol-only consumers (chunk 09); chunk 09 at base
  169 passed in 7 s; the base failure set stays the spec's 4 pre-existing nodes (2 `.pre_impl_failures.txt`
  rows in test_page_scraping, 2 tiktoken-cache ERRORs in test_prompt_truth).
- CI-order set (15 files, sorted): without the new file 733 passed (68 s, = the spec's base); with it
  58 failed / 759 passed (114 s): the 58 are exactly the new REDs, 0 failures leak into the files that sort after.
- Preserve run (the five existing hard-cap pin files at HEAD): 53 passed (93 s).

**Answers to the RED agent's three questions (binding for GREEN):**
- **G1.** The F11 key-order pin stands: the post-loop block REPLACES the slot dict (`outcomes[slot] = {...}` in
  `phase1_keys` order), exactly spec 2.4; a merge (`{**old, **new}`) is wrong.
- **G2.** M12 (the mid-gather arm ignores a landed `price` key) keeps its single killer F18 r05; no new row.
  The rule is pinned; an adjacent real-entry flip row is not required (the house norm for an adjacent mutant
  of an already-pinned rule). Recorded in the PR body.
- **G3.** The gate count is 58 RED / 26 PIN in the new file, plus the existing F14 node
  `tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main`. Confirmed.

**Spec disagreements accepted as recorded by RED:** M10 redefined as its inverse ("an absent data race counts
as completed"); the killer moves under the eager design (M3 -> F4c only, M5 -> F18 r08, M23 -> F1's WARNING
count); the D5 "timed out" count always equals "data races recorded" on the TIMEOUT path (a swapped-arguments
mutant is equivalent); the spec's TG helper names are not on main at e0f3e475, the file uses the spec 1.5
`_install_real` stubs and `tests.test_s75_fanout_identity._install` (helpers only).

**Rulings for GREEN (after the owner's yes):**
- **G4.** The RED file is FROZEN. GREEN implements spec section 2 as amended by R2 (the eager record + the
  predicate), R3 (7.2 first), R5, R6 (WARNING level), R7 (the line and the three counts) in
  `app/services/structured_comparison_service.py` only; the prototype patch is a shape reference, every line
  justified by a row. If an assertion is wrong, STOP and report.
- **G5.** Gates: the unit file green in both flag states; the FY25 node at HEAD in both states (R11); the
  mutation table M1-M29 (M16a/b, M22a/b) re-run on the GREEN bytes, M30 recorded as equivalent; ruff
  E9/F63/F7/F82 + py_compile; the CI-order set in one process per state WITH the new file (expect 817 passed,
  0 failed); the comm set at HEAD in 10 chunks of at most 25 (bound 1200 each, one at a time), branch-only-NEW
  empty against the recorded 4 base nodes; the preserve files; the CLAUDE.md row per R12 (byte-safe CRLF edit,
  the row at the same anchor as the TG/SM rows, before `## Tests`); `pr_text`; never commit.
- **G6.** Then the two adversaries (correctness, engineering) on the exact bytes; at most one fix round, with a
  re-adversary; the orchestrator's diff review; commit; PR with `pr_rest.py`.
- **G7.** Scope: the owner's call at this gate. Option A (this unit as specified; S78-F8b for the two H6 guards
  next, on the same flag, before any flip) needs nothing more. Option B (fold the H6 sites in now) needs a RED
  extension (about 6 rows + 2 mutants, a second RED agent, ~30 min) BEFORE GREEN. An unqualified "approve" or
  "go" means A.
