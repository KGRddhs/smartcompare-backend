# RULINGS_COMM_S81_07 (orchestrator Claude Fable 5.2, session 93, 2026-11-12): the three gates that the merge round of S81-07 left NOT MEASURED. Binding on the gates-only agent.

Why: the merge-and-fix agent of round wf_b4f31dc8-1dd committed the merge a52523ac and the fix dca3a360, but the pytest slot was held by another lane from 13:28 to 14:46 and its last three gates never ran. The slot is free now (the relay holds that lane until this agent's comm set is done). The round's ONE re-verifier is running at the same time: it reads the same worktree and runs short pytest calls under the same wait rule.
In this file "<scratch>" is the session-93 scratchpad, "<merge>" is `<scratch>/S81-07_merge` (the merge round's notes: its report S81-07_MERGE_REPORT.md, its scripts run_seq.sh, fences.sh, waitfree.ps1, comm.py, and the folder comm/ with comm_list.txt, chunk_01..08.txt and derive.json) and "<notes>" is `<scratch>/S81-07_comm`. The binding rulings of the round are `<scratch>/s07/RULINGS_MERGE_S81_07.md` (M-5 defines these gates).

## C-1 SCOPE
GATES ONLY. You edit NOTHING in the unit worktree and you make NO commit. The head is dca3a36042a9dfea000d4538d6d72da3cdf1820b on feature/s81-07-meas-claude-gate (verify it and an empty git status --short at the start and at the end). The one git write allowed: ONE detached scratch worktree of main 445f8de3e624d3d52a6903bafa6bfae0cb750cf6 under `<notes>/base` for the base runs (python only, no junction; removed afterwards with `git worktree remove --force` and verified gone with `git worktree list`). No live run, no network call beyond that worktree creation, no key file, no credential.

## C-2 THE WAIT RULE (M-5), for every pytest and every jest
Probe first (PowerShell Get-CimInstance Win32_Process; `<merge>/waitfree.ps1` is the merge agent's probe: read it, and make your own copy exclude ONLY your own tag prefix); when a foreign run is live, wait in a loop with 30 s polls and NO bound; after every run wait 20 s and probe again (the re-verifier's short runs go in between). One pytest process and one jest process at a time; never kill a process you did not start. If the budget ends while waiting, the gate is NOT MEASURED: it never runs beside a foreign process.

## C-3 GATE ONE: THE 18 PINS AT THE FIX HEAD
The list and the exact commands are in `<merge>/run_seq.sh` and the merge report (the M-3 run on the merged code). Expected: the same counts as M-3; tests/test_s81_s22_judge.py shows its ONE known CRLF base failure (j01) and nothing else is red.

## C-4 GATE TWO: THE FOURTEEN CLIENT FENCES
By path, from SmartCompareApp of the unit worktree (it has a live node_modules junction: never touch it), as `<merge>/fences.sh` prepared them. Expected: 13 suites green and config/nativeBundle.w37 red on its four known nodes only (d5, k2, k4, k5).

## C-5 GATE THREE: THE COMM SET AT THE NEW MAIN
The member list is prepared: `<merge>/comm/comm_list.txt` (187 members, set sha256 d79dfdf0...), eight chunk lists, derive.json. First check the lists (LF line ends, a byte check, 187 distinct existing files, the sha256). Then run every chunk at BASE (the scratch worktree of 445f8de3) and at HEAD (the unit worktree at dca3a360), one process at a time, each through pyt.py with its own tag and log under `<notes>`.
Store the base record under `<scratch>/harness/base_records/445f8de3e624d3d52a6903bafa6bfae0cb750cf6/`: `<set sha256>.files` (the member list), `<set sha256>.txt` (the sorted FAILED and ERROR node ids at base) and `<set sha256>.pyt.log` (the [pyt] lines).
RESULT: `comm -13` of the sorted FAILED and ERROR ids (base, head) must be EMPTY; also report `comm -23` (base-only ids). Known on both sides: the CRLF class of failures of this box (the GREEN round measured 12 at the old base). A branch-only failure is REPORTED with its assertion from both sides, never fixed.
THE MARKERS (a watcher reads them): append `WAIT <epoch seconds>` to `<merge>/comm_wait.txt` each time you start waiting for a comm chunk and `RUN <epoch seconds>` when the chunk starts; after the last chunk write `<merge>/comm_done.txt` with one line (the result).

## C-6 THE ORDER, THE BUDGET, THE REPORT
Order: the comm set FIRST (it is what another lane waits for), then the pins, then the fences. Budget 70 minutes from the first tool call; a gate the budget cannot fit is reported NOT MEASURED by name, with how far it got. Report `<notes>/S81-07_COMM_REPORT.md` through the shell: every [pyt] line, every jest summary line, the id lists' paths, the two comm results. Never claim a state you did not observe.
