# RED gate S78-TG and S78-SM (orchestrator, 2026-10-14 ~08:35 AST): PASS for both

**Inputs**

- RED workflow: wf_ed16ead8-d40.
- Report: `runs/s78_tg_sm_red_wf_ed16ead8.json`.

**Re-measured by the orchestrator at base `e0f3e475`**

- **TG:** 35 failed / 19 passed.
  - Run: `[pyt] tag=gate-tierguard`.
  - Prototype (RED agent): 54 / 54 passed.
  - Mutants: 26 / 26 killed.
- **SM:** 49 failed / 23 passed.
  - Run: `[pyt] tag=gate-serpermemo`.
  - Prototype (RED agent): 72 / 72 passed.
  - Mutants: all spec-table mutants killed, except X18. X18 is accepted.
- **Secret and personal-data scan:** both test files have 0 matches for sk-, @gmail and +973.

**Rulings for GREEN**

- **TG-G1:** R17 relies on the existing node `tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main` in the comm set. Do not add a duplicate. The prototype `scs` diff from the RED agent (79 insertions, 8 deletions) is a reference only. GREEN implements the spec plus the rulings and must not edit the RED test file.
- **SM-G1:** keep the generation clear in `_reset_serper_key_state_memo`, as in spec section 2.2.
- **SM-G2:** the p8c 0.5 s join is acceptable.
- **SM-G3:** GREEN adds the single reset line to `tests/conftest.py`. GREEN runs the SM-ADV-8 base and HEAD comm chunks, including `test_conftest_env_safety.py` and `test_api_budget_service.py`.
- **Both:**
  - The RED files are frozen. If an assertion is wrong, STOP and report.
  - Gates:
    - the unit file is green;
    - the comm set at HEAD vs base is branch-only-NEW empty, in chunks of 25 or fewer;
    - ruff E9/F63/F7/F82 and py_compile;
    - flag-OFF identity, pinned;
    - the mutation table re-run on the GREEN bytes;
    - CLAUDE.md flag rows are added in GREEN, under the Environment Variables / Feature Flags section, each with effect, flag-OFF identity, stated limits and canary.
