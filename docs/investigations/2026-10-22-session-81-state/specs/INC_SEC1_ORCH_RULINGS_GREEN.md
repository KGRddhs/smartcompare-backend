# Orchestrator rulings for INC-SEC-1 GREEN (relay, 2026-11-17 about 11:55 AST), binding

- **ORCH-SEC1-A (Q9).** We create no throwaway sign-in user; creating an account is the owner's alone, and he is away.
  - P8(b) is a cluster-only proof and a stated limit.
  - The apply note carries ONE option for the owner: the live P8(b) on his two tester-level test accounts, picked inside the block by their level. No id is shown, and the block ends in its verdict error, so nothing is saved. It runs only if his yes names it.
- **ORCH-SEC1-B (Q8).** C2 and C2b unflagged is accepted as a design. But they change a live write path with no switch, so THE MERGE WORD FOR THIS PR WAITS FOR THE OWNER, together with the apply of 055.
  - Build it, gate it, both adversaries, open the PR, bring it to 7 of 7, then STOP: no merge while he is away.
  - The TOP of the PR body and the TOP of the owner summary state this, with the order for his sitting: his yes, merge, deploy seen healthy, 055, proofs.
- **ORCH-SEC1-C (ADV-2, answer with evidence).** Can a LEGITIMATE signed-in user lose the comparison link through C2b? Walk at least these cases:
  - (1) feedback arriving before the comparison row is persisted: is the row written before the response that carries its id, on the text, image and url routes?
  - (2) a comparison made signed-out and rated after sign-in;
  - (3) a history item;
  - (4) a shared comparison opened by another signed-in user.

  Name each case's outcome; the PR body carries them.
- **Q7, A-1, the test_gr1 shape, and "C3 is dark, not user-facing" stand.**
- **METER ORDER.** Do the no-box preparation first: the commits, black, the note drafts, and the E27 deflake commit.
  - Take the NEWEST main before the heavy gates, so they run once. PR #419 (INC-H2 with INC-T0) may merge any minute; the S96 orchestrator writes its merge sha into MAIN_SHA.txt beside this file.
  - If #419 is not merged when you reach the heavy gates, go on with origin/main as fetched (7f672cfe or later).
  - After a later merge, re-run ONLY the one-process CI-order run and the source-scanning pins.
