# S81-12 MERGE REPORT -- verdict BLOCKED
unit S81-12 LEGAL-V3 merge round (RULINGS_REBASE2_S81_12)
head_before e8c8c1dc488a5547a874ccffb7dbd8a96ec7965c; base_main 6b909e0a92067d6b3562eee325e4956c116441f7
merge_commit = head_after 6c71a5fa0e53aba81e750feed1239341acda19de (parents e8c8c1dc, 6b909e0a); git status --short empty
conflicts: CLAUDE.md, one hunk, union sha256 c92a650b... = ruled (RB2-2)
footprint 45 files = footprint45.txt
BLOCK: RB2-7 (3) before EK4 shows a third red node, tests/test_s81_12_legal_v3.py::test_r9_manifest_anthropic_row_public_and_named: 'the openai row changed'. main #398 (aed1393b) removed app/services/verdict_critique_service.py from the openai row in app/legal/processors.json; R9 pins that row at BASE_OPENAI_ROW_SHA256 c7453e56... (line 224); the row is now c67cb808...0320. Not CLASS V nor CLASS M: needs a ruling (candidate EK5 re-pin of that one constant from origin/main's manifest).
No round commit made; PR_BODY.md not written. Details: MERGE_EVIDENCE.md.


# RUN 2 (continuation, RB2-13): verdict MERGED_AND_COMMITTED
merge commit 6c71a5fa0e53aba81e750feed1239341acda19de (verified, not redone; origin/main still 6b909e0a)
round commit = head_after dd9738f77650fbda370ca75a99c8596e44d00412 (parent 6c71a5fa); git status --short empty
CLAUDE.md: merge blob c92a650b... (RB2-2), round blob 41606c55... (RB2-4), both = ruled
tests/test_s81_12_legal_v3.py: 9163cfcb... -> e860e18d... (EK4: 1013 -> 1011, 3d786372 -> 2d351a2c; EK5 CLASS B: c7453e56 -> c67cb808, main #398; positive control red, restored)
E-rows CLASS V / M: none
Gates: unit 37 + H1; gate rows 22/22; legal set + unit files 554 + H1; six alone files green (333/29/48/31/19/17); jest unit 64/64, s81_08 100/100; FULL jest 4,039 passed + 4 w37 drift (= 4,030 + 9 legalV3); fill dry / render check rc 0; diff --check clean.
Deviation: s12m-unit-post2 overlapped a foreign inc- pytest (hermetic; identical to the clean-probe run unit-post).
PR_BODY.md 24,491 bytes, 5 TO-FILL-BY-GATES markers. Evidence: MERGE_EVIDENCE.md (RUN 2 section).
