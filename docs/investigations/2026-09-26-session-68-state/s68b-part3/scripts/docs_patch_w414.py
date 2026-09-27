"""Docs checkpoint for W4-14 (session 68b, part 3). Run INSIDE the docs worktree (cwd = worktree root)
AFTER PR #<PR> merged:  python docs_patch_w414.py <PR> <MAINSHA> <TIME> <W414B> <W414C> <W414D> <W414E> <DEC>
Edits CLAUDE.md (heading, STATUS, the two W4-14 rows after the W4-7 corrections bullet, a part-3 paragraph),
appends s11 to docs/investigations/2026-09-26-session-68-state.md and inserts a part-3 entry in
docs/CONTEXT_SESSION_LOG.md. Every anchor is count-checked; CRLF preserved."""
import io, os, sys

PR, SHA, TIME, W414B, W414C, W414D, W414E, DEC = sys.argv[1:9]
NSP = "C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/0a2845de-abfe-4bca-b433-df4ce9787ab5/scratchpad"


def rw(path, fn):
    raw = io.open(path, "rb").read()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    text = fn(text)
    io.open(path, "wb").write((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def rep(text, old, new, count=1):
    n = text.count(old)
    assert n == count, ("expected", count, "found", n, old[:90])
    return text.replace(old, new)


rows = io.open(NSP + "/docs_flagrows_w414.md", encoding="utf-8").read().rstrip("\n")
rows = (rows.replace("#<W414PR>", "#" + PR).replace("#<W414B>", "#" + W414B)
        .replace("#<W414C>", "#" + W414C).replace("#<W414D>", "#" + W414D))
assert "#<" not in rows, "unfilled placeholder in the flag rows"

PART3 = (
    "- **The third part of the session (W4-14, the lane's first CLIENT unit under the harness; ~14:32 \u2192 "
    + TIME + "):** red 28 RED / 14 PIN / 21 KILL at `3985eaac` in 29 min with a green satisfiability prototype "
    "(full jest 328 suites / 44 snapshots); Fable red-gate rulings R1-R11 answered the red's three questions "
    "(no `lang` on the dead `compareTextPair`; the minutes `_zero` copy; the directive text accepted verbatim with a "
    "file-derived copy-policy fence); the green implemented the prototype; three SOUND adversaries in a row, each "
    "finding only test-strength minors, the fixers touching tests only \u2014 the nine production files never moved "
    "after the green. Adversary r0 REFUTED the spec review's route inventory: `/url/compare` HAS a live client caller "
    "(HomeScreen Link mode), so Link-mode AND camera Arabic users stay English until W4-14b #" + W414B + ". "
    "Fable closed adversary r2's three pin gaps (the reader's unrecognised values, the RESULT half of the flag-OFF "
    "identity, the `_two`/`_few`/`_many` referral copy) with mutants red. Shipped as #" + PR + " (`" + SHA + "`): "
    "client half unflagged + OTA-gated, `ENABLE_ARABIC_VERDICT_OUTPUT` dark. Follow-ups #" + W414B + " W4-14b, #"
    + W414C + " W4-14c (the flip's hard precondition), #" + W414D + " W4-14d, #" + W414E + " W4-14e, #" + DEC
    + " the `category_switched` DECISIONS item. Client-unit harness facts: the `SmartCompareApp/node_modules` "
    "JUNCTION to the clone (create with `cmd /c mklink /J`, UNLINK with `cmd /c rmdir` before any removal, verify "
    "the clone's `@babel/core` after); jest / tsc / eslint by path under coreutils `timeout -k 15` (subsets 600 s, "
    "the full suite 1500 s); the FULL jest suite is the arbiter (no `-u`, no `.snap` in the diff); a "
    "`testPathIgnorePatterns` of `w414` also matched the scratch path `w414proto` and selected 0 tests (pattern "
    "hygiene); the stall monitor must be started from the scratchpad, never from a worktree (it pinned `sc-w4-7` as "
    "its cwd); `s68b-green.mjs` needs no change for a client unit \u2014 the client rules ride its `extra` argument."
)


def patch_claude(t):
    t = rep(t,
            "SEVEN units MERGED under it: hermeticity #207, W4-13 #209, W4-6a #212, W4-12 #213, W4-11 #223, W4-8 #227, W4-7 #228; main `3985eaac`, 2026-09-27 ~14:11 local; W4-14 next)",
            "EIGHT units MERGED under it: hermeticity #207, W4-13 #209, W4-6a #212, W4-12 #213, W4-11 #223, W4-8 #227, W4-7 #228, W4-14 #" + PR + "; main `" + SHA + "`, 2026-09-27 ~" + TIME + " local; every spec'd W4 unit of the lane is shipped \u2014 next = the config-audit docs PR + the Step 6 structured review)")
    t = rep(t,
            "**STATUS \u2014 main `3985eaac` (the first checkpoint of this block was written at `15e1fb89`; the three later units are the rows W4-11 / W4-8 / W4-7 below and the paragraph after the lessons).**",
            "**STATUS \u2014 main `" + SHA + "` (the first checkpoint of this block was written at `15e1fb89`; the four later units are the rows W4-11 / W4-8 / W4-7 / W4-14 below and the two part paragraphs after the W4-12 callers bullet).**")
    # the two W4-14 rows after the W4-7 corrections bullet
    lines = t.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith("- **W4-7 CLAUDE.md corrections:**")]
    assert len(idx) == 1, idx
    lines[idx[0] + 1:idx[0] + 1] = rows.split("\n")
    t = "\n".join(lines)
    # the part-3 paragraph after the second-half paragraph
    lines = t.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith("- **The second half of the session (04:05")]
    assert len(idx) == 1, idx
    lines.insert(idx[0] + 1, PART3)
    return "\n".join(lines)


S11 = """

## 11. SESSION 68b, part 3 (~14:32 \u2192 %(TIME)s local, 2026-09-27): W4-14 #%(PR)s merged \u2014 the lane's first client unit under the bounded harness; main `%(SHA)s`

**Ledger (every verdict from a harvested agent report; rulings, reports and scripts in `2026-09-26-session-68-state/s68b-part3/`).**
- **Red** (`wf_b0829c52-6bc`, 29 min): 28 RED / 14 PIN / 21 KILL at `3985eaac`; every RED right-reason in five backend flag states and under the real jest toolchain (node v24.11.1 / jest 29.7.0 / typescript 5.9.3 by path through the junction); the satisfiability prototype in a detached scratch worktree green on every gate \u2014 backend unit 203 passed \u00d7 5 states, full jest 328 suites / 3172 tests / 44 snapshots, the 24-cell prompt byte-identity in both `ENABLE_VERDICT_PROMPT_TRUTH` states, preserve 551, ratchet 0 new nodes. Drift recorded: with W4-11's flag ON, 18/18 system digests moved against the `61585c58` capture (W4-11's own prompt), user unchanged.
- **Fable red-gate rulings R1-R11** answered the red's three questions: R1 no `lang` on `compareTextPair` (0 callers \u2192 W4-14e); R2 the minutes `_zero` copy "Expires in under a minute" in both languages; R3 the directive accepted verbatim (874 chars) with test 36 file-derived from `.copy-policy.json`; R5 the comm gate HEAD-only in 25-file chunks; R8 read `currentOutputLang()` once per request; R9 the identity gate protocol; R10 the exact file set.
- **Green pipeline** (`wf_ee832d39-95e`, 107 min, six agents): green (the prototype's design + R2/R8; 27 mutants, comm 261 files / 8506 passed, full jest 3172 / 44) \u2192 adversary r0 SOUND (3 minors: the route inventory, two backend pins, four client pins) \u2192 fix r1 (tests only) \u2192 adversary r1 SOUND (3 minors: test 36 pinned vocabulary not meaning, the capture compared kwarg NAMES only, the R2 copy unpinned) \u2192 fix r2 (tests only: exact-text + sha pin, value-level kwargs capture, the R2 `_zero` pin) \u2192 adversary r2 SOUND (3 minors). The nine production files stayed sha-identical to the green's bytes through every round.
- **Adversary r0's correction of the spec review:** `/url/compare` HAS a live client caller (`HomeScreen.handleUrlCompare`, Link mode, present since at least `61585c58`) and `url_extraction_service` calls `generate_comparison` without `output_lang`; the review's R2.7 and ruling Q3 were wrong. Consequence: Link-mode and camera Arabic users keep English verdicts until W4-14b.
- **Fable's closing pins** (adversary r2's minors, test rows only, `s68b-part3/scripts/add_pins.py` + `mut_fable.py`): `test_38` unrecognised values read as OFF (mutant X4 \u2192 5 red); `_capture(with_result=True)` + `test_40` \u2014 the RESULT of `generate_comparison` is identical for `output_lang` None / en / ar with the flag OFF and for None / en with it ON, flag ON + ar changes the prompt only (mutant X2 \u2192 3 red); the `_two` / `_few` / `_many` referral copy pinned by value with the Arabic rendering at 2 / 3 / 11 (mutant C3 \u2192 suite red). Backend file 209 \u2192 226 nodes.
- **Ship** (`d3516a40` rebased onto the docs-only `3424da3c`; `ship_w414.sh`): backend unit 230 \u00d7 5 states; the backend CI-order set 443 \u00d7 2 states, ratchet OK (18 attempting nodes, all baseline); ruff / py_compile clean; the must-not-touch gate empty, no `.snap` moved; client CI-order 18 suites / 134 tests / 4 snapshots; FULL jest 328 + 3 skipped suites, 3177 tests, 44/44 snapshots; tsc 0; eslint 0 errors (148 warnings, the pre-unit count). PR #%(PR)s merged \u2192 main `%(SHA)s`; prod `/health` 200.
- **Follow-ups filed:** #%(W414B)s W4-14b (PersonalizationChip `dim_key` + `lang` on `/url/compare` and `/image/identify`), #%(W414C)s W4-14c (Arabic-aware guards + English replacement paths + `_PRICE_ADJECTIVE_RE` + the Arabic `max_tokens` measurement \u2014 the flip's hard precondition), #%(W414D)s W4-14d (`delta_text` + factual verdict lines as key+params), #%(W414E)s W4-14e (`compareTextPair`), #%(DEC)s DECISIONS `category_switched`.

**Client-unit harness facts (binding).** (1) `SmartCompareApp/node_modules` in a unit worktree is a JUNCTION to the clone's (`cmd /c mklink /J`); unlink it with `cmd /c rmdir <link>` BEFORE any worktree removal and verify the clone's `node_modules/@babel/core/package.json` afterwards. (2) jest / tsc / eslint run by path from `SmartCompareApp` under coreutils `timeout -k 15` (subsets 600 s, the full suite 1500 s, `--listTests` 120 s), one jest process at a time, never `-u`. (3) The FULL jest suite is the client arbiter (the memory rule); its snapshot count is a gate. (4) A `testPathIgnorePatterns` of `w414` also matched the scratch path `w414proto` and selected 0 tests \u2014 anchor patterns on `\\.w414\\.test`. (5) The stall monitor must be launched from the scratchpad: started from a worktree it pins that directory as its cwd (the `sc-w4-7` delete failed until it was restarted). (6) `s68b-green.mjs` / `s68b-round.mjs` need no client mode \u2014 the client rules ride `extra` (they are injected into the green, adversary and fix prompts).

**Docs owed / done:** the two W4-14 rows are in CLAUDE.md's SESSION 68b block (this checkpoint). **Next:** the config-audit docs PR, the Step 6 structured review at the milestone end; Ahmed: the native review of the 51 Arabic labels, then the OTA.
""" % dict(PR=PR, SHA=SHA, TIME=TIME, W414B=W414B, W414C=W414C, W414D=W414D, W414E=W414E, DEC=DEC)

LOG = """# SESSION 68b, part 3 \u2014 W4-14 #%(PR)s merged: the lane's first client unit under the bounded harness (2026-09-27 ~14:32 \u2192 %(TIME)s); main `%(SHA)s`

**One red, one green, three SOUND adversaries, two test-only fix rounds.** W4-14 puts the 51 dimension labels through the `results.dimension.*` catalog with the `localizedCurrency` echo guard (EN renders byte-identical, 72/72 rows pinned under the real catalog and the global jest mock; the 51 Arabic values are a proposal awaiting native review before the OTA), completes the six Arabic referral-expiry plural forms, sends `lang=ar` on the Home text-compare requests only when the app language is Arabic, and adds the dark `ENABLE_ARABIC_VERDICT_OUTPUT` directive (appended LAST to the verdict system prompt; flag OFF byte-identical over 24 cells in both W4-11 states \u2014 prompt, call kwargs by value and the returned result). Adversary r0 refuted the spec review's route inventory: `/url/compare` is a live client caller (Link mode), so Link-mode and camera Arabic users stay English until W4-14b. The nine production files never moved after the green; Fable closed the last three pin gaps with mutants red.

**Flag on main:** `ENABLE_ARABIC_VERDICT_OUTPUT`, default OFF, read per call \u2014 fourteen flags for the whole of 68b, all default OFF. Nothing flipped; Railway and Supabase untouched; prod `/health` 200 after the merge. Its flip has hard preconditions (W4-14c #%(W414C)s, the Arabic `max_tokens` measurement, the device walkthrough); the client half is main-only until Ahmed's next `eas update --branch preview --clear-cache`.

**Client-unit harness facts (binding):** the node_modules junction (create with `mklink /J`, unlink with `cmd /c rmdir` before removal); jest / tsc / eslint by path under coreutils `timeout`; the full jest suite as the arbiter; anchor jest path patterns on `\\.w414\\.test` (a bare `w414` also matched the scratch worktree); start the stall monitor from the scratchpad, never from a worktree; the green / round scripts take the client rules through `extra`. Full ledger: state doc \u00a711.

**Follow-ups filed:** #%(W414B)s W4-14b, #%(W414C)s W4-14c, #%(W414D)s W4-14d, #%(W414E)s W4-14e, #%(DEC)s DECISIONS `category_switched`. **Ahmed's items (unchanged + one):** the native review of the 51 Arabic labels before the OTA; apply migration 042 before `ENABLE_SEARCH_LOG_SYNTHETIC_MARKER`; the #101 call (#219); W4-8d (#231); the W4-2 caption call; the leaked-key + `ADMIN_API_KEY` rotation.

""" % dict(PR=PR, SHA=SHA, TIME=TIME, W414B=W414B, W414C=W414C, W414D=W414D, W414E=W414E, DEC=DEC)


def patch_state(t):
    assert "## 11. SESSION 68b, part 3" not in t
    return t.rstrip("\n") + "\n" + S11


def patch_log(t):
    anchor = "# SESSION 68b, part 2 \u2014 three more W4 units merged under the bounded harness"
    assert t.count(anchor) == 1
    assert "# SESSION 68b, part 3" not in t
    return t.replace(anchor, LOG + anchor, 1)


assert os.path.exists("CLAUDE.md"), "run inside the docs worktree root"
rw("CLAUDE.md", patch_claude); print("CLAUDE.md patched")
rw("docs/investigations/2026-09-26-session-68-state.md", patch_state); print("state doc s11 appended")
rw("docs/CONTEXT_SESSION_LOG.md", patch_log); print("session log part-3 entry inserted")
