# RULINGS_WINDOW_S81_12 (orchestrator Claude Fable 5.2, session 93, 2026-11-12): the LEGAL-V3 window commit of S81-12 (recipe G of the unit spec, section 3, as re-ruled for PATH C). Binding on the window round.

In this file "<scratch>" is the session-93 scratchpad and "<notes>" is `<scratch>/S81-12_window`. Everything that depends on the day is in `<scratch>/s12/window/WINDOW_INPUTS.txt` and wins over any date written elsewhere: the window date D in its three spellings (ISO, English, Arabic), the head H the round starts from, main, the folder of the expected files with their sha256, the relay's dated line, the PR body to start from.

## W-1 WHAT THE WINDOW IS UNDER PATH C
The window is the publication day of LEGAL-V3: the day the branch merges. No console step belongs to it (specs/RULINGS_V3C_S81_12.md, V3C-12). The window date D comes from the relay's dated line in the owner's name, quoted in WINDOW_INPUTS.txt. D is at once: TERMS_VERSION (both constants), the effective date of the four documents, the date of the two change notices, the value of AI_SWITCH_DATE / _AR and the window record. THE COMMIT CARRIES D, SO IT IS MADE AND MERGED ON D (the local date of this machine): a local date other than D at the opening or right before the commit is a STOP.

## W-2 THE EXACT SITES (nothing else moves; NEVER a global replace; every replacement asserted with its count)
(1) app/services/consent_service.py: the one line `TERMS_VERSION = "2026-10-29"` -> D (ISO).
(2) SmartCompareApp/src/services/consent.ts: the one line `export const TERMS_VERSION = '2026-10-29';` -> D (ISO).
(3) tests/test_consent_capture_w3_16.py: the one line `TERMS_VERSION = "2026-10-29"` -> D (ISO); in its trailing comment the words "S81-12: provisional" become "S81-12: the window".
(4) tests/fixtures/legal_fill_in_u8.json: placeholders.AI_SWITCH_DATE (English) and placeholders.AI_SWITCH_DATE_AR (day, the month of the pinned table GULF_MONTHS_AR in tests/test_legal_docs_u8.py, year; Western digits) -> D. If a comment value of this file still calls the date provisional, or names the old date as the current value, that ONE sentence is re-worded to say that the date is the window date D; old -> new reported.
(5) The four pre-fill snapshots tests/fixtures/legal_prefill_u8/*.md: the effective-date line (:5) -> D in the file's language.
(6) NEW tests/fixtures/legal_v3_window.json: the record the hold row reads (the key window_date with D in ISO form), in exactly the shape the hold row and its companion H1b accept; LF line ends, a final newline.
(7) Then the machinery: restore the six sources from the snapshots, `scripts/fill_in_legal.py` (rc 0), `--dry-run` (rc 0, no output), `scripts/render_legal_landing.py --check` (rc 0). The four documents move on lines 5 and 7 only; the four landing pages follow by the render. No document and no landing page is edited by hand; the two catalogs do not move.
(8) CLAUDE.md, in place, by a Python script on the git bytes (the blob is LF, the working copy CRLF: explicit newline handling), an exact old -> new list with count 1 each, reported: the sentences that call the date provisional or say that the unit is held for its window are re-told (the window was D; TERMS_VERSION = D; the hold row is green). No other block moves.
THE OLD DATE STAYS wherever it is history or foreign data: scripts/seed_zyte_luxury.py; the two flag-off goldens under tests/fixtures (s81_d08, s81_s09); the `_comment` values of scripts/legal_variants_u8.json and of the legal fixtures; the docstring of the unit file that dates a ruling; every other file.

## W-3 THE EXPECTED BYTES
After the commit the six artefacts equal the files under the expected folder named in WINDOW_INPUTS.txt (derived by `<scratch>/s12/window/window_expected.py` from the fix round's bytes: the date strings alone, on lines 5 and 7). They are for `cmp` only and are never copied into the tree.

## W-4 STEPS AND GATES (cheapest first; every [pyt] line and jest summary line pasted)
Before EVERY pytest and EVERY jest: the cross-session probe (RB2-7 of the older rulings), and when a foreign run is live, WAIT through a wait script with 30 s polls, every time. One pytest process and one jest process at a time; never kill a process you did not start.
(1) Opening: the branch, HEAD = H, an empty git status, `git fetch origin main` still the main of WINDOW_INPUTS.txt, the local date equals D, the sha256 of the six artefacts at H as listed, and the unit file at H red on the hold row H1 alone.
(2) The edits of W-2 by ONE Python script with count assertions; the machinery; the `cmp`.
(3) The unit file with the gate rows, one process: ZERO red (H1 and H1b green).
(4) The legal set, then the CI-order set of RB2-7 (10), one process each: ZERO red.
(5) Client: the consent suites and the unit's client rows by path, tsc, then THE FULL JEST ONCE (red only on the known w37 four).
(6) The comm set of the fix round STANDS for this head when main has not moved and this commit moves the date literals alone: state both facts with their evidence; it is not run again. CI's whole-suite run on the pushed head is the regression control.
(7) The PR body (W-6); then, with the local date checked again, the ONE commit (W-5).
(8) The report `<notes>/WINDOW_REPORT.md`: every site with old -> new and its count, the footprint, every gate line, the sha256 of every changed file, a per-file statement that the diff is the date strings and the ruled sentences alone.
Budget 75 minutes from the first tool call. A gate the budget cannot fit is reported NOT MEASURED by name.

## W-5 THE COMMIT AND THE FOOTPRINT
ONE commit through the hook (in this worktree only: `git add <paths>` and `git commit -m ... -- <paths>`; never --no-verify, amend, rebase, merge, stash, reset, checkout --, restore, clean or push), message head `chore(s81-12): the LEGAL-V3 window, re-dated to <D> (recipe G)`, the Co-Authored-By trailer naming the agent's own model.
THE FOOTPRINT, exactly these 18 files (anything else is a STOP): app/services/consent_service.py; SmartCompareApp/src/services/consent.ts; tests/test_consent_capture_w3_16.py; tests/fixtures/legal_fill_in_u8.json; the four snapshots; the new tests/fixtures/legal_v3_window.json; the four documents; the four landing pages; CLAUDE.md.

## W-6 THE PR BODY
From the body named in WINDOW_INPUTS.txt into `<notes>/PR_BODY.md` through the shell: ONE window paragraph (D; the relay's dated line; what moved; the hold row green; every gate figure of this round), the sentences that said "held" or "provisional" re-told, the window checklist ticked up to the merge. Pure ASCII apart from the attribution line; AT MOST 25,600 bytes measured with python (compress older round history first, never the window order, the checklist, the E-rows table or the stated limits); it still ends with the attribution line.

## W-7 THE STOP RULES
A site of W-2 not found with count 1; a `cmp` mismatch; any moved byte outside W-2 (in every changed file the diff is the date strings and the ruled sentences alone); any red node in (3) or (4); a full-jest red outside the w37 four; main moved; the local date is not D at the opening or right before the commit; the PR body above the limit after compression. STOP = leave the tree as it is (no commit) and return BLOCKED with the evidence. Never claim a state you did not observe.

## W-8 AFTER THE COMMIT (the orchestrator; no second agent: the commit moves dates alone and these checks are an independent derivation)
(a) From git bytes: exactly one parent H; the footprint of W-5; the six sha256 equal the expected values; a script shows that every changed line differs from its old line only by the date strings or is one of the ruled sentences of W-2 (3), (4), (8); the bytes of the window record. (b) `git push origin feature/s81-legal-v3` as a FAST-FORWARD (no force flag); `pr_update.py 378`; `ci_wait.py 378` (read-only; never `pr_rest.py watch`): SEVEN of seven green. (c) `pr_ready.py 378 --ready`. (d) The relay is told: ready, with the head sha and the CI reading. (e) THE MERGE only on the relay's dated word in the owner's name that names D, and only while the local date is D; then the merge sha goes to the relay at once (the landing redeploy, the store label and the second update are the relay's). (f) If the day ends before the merge, nothing merges and a new window round re-dates.

## W-9 IF THE OWNER STRIKES THE VERIFY-BEFORE-RELYING SENTENCE BEFORE THE WINDOW
It comes out in this round as one more ruled edit (the sentence in both Terms snapshots, the row V3C-5 turned into its absence form, its fixture entry removed), with new expected bytes derived by the orchestrator before the launch and named in WINDOW_INPUTS.txt. Without the relay's word the sentence stays.
