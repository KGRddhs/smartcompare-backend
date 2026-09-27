"""Session 68b second docs checkpoint: applies the three flag-row files to CLAUDE.md's SESSION 68b block
(+ two corrections), appends s10 to the state doc and a SESSION 68b (part 2) entry to the session log.
Run INSIDE the docs worktree: python docs_patch_s68b2.py <W48PR> <W47PR> <MAINSHA> <TIME>
Byte-safe, CRLF-aware, count-checked; every anchor must match exactly once."""
import os, sys

NSP = "C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/0a2845de-abfe-4bca-b433-df4ce9787ab5/scratchpad"
W48PR, W47PR, MAINSHA, TIME = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
WT = os.getcwd()


def rd(rel):
    raw = open(os.path.join(WT, rel), "rb").read()
    return raw.decode("utf-8"), (b"\r\n" in raw)


def wr(rel, txt, crlf):
    open(os.path.join(WT, rel), "wb").write(txt.encode("utf-8"))


def replace_once(txt, old, new, crlf, what):
    o = old.replace("\n", "\r\n") if crlf else old
    n = new.replace("\n", "\r\n") if crlf else new
    c = txt.count(o)
    if c != 1:
        raise SystemExit(f"anchor count {c} != 1 for {what}: {old[:80]!r}")
    return txt.replace(o, n)


def rows(name, pr_from=None, pr_to=None):
    t = open(os.path.join(NSP, name), encoding="utf-8").read().rstrip("\n") + "\n"
    if pr_from:
        t = t.replace(pr_from, pr_to)
    return t


# ---------------------------------------------------------------- CLAUDE.md
cl, crlf = rd("CLAUDE.md")
# 1. the seven new flag rows after the ENABLE_SMART_PICK_VERDICT_CAPTION row (end of that bullet line)
lines = cl.split("\r\n" if crlf else "\n")
idx = [i for i, l in enumerate(lines) if l.startswith("- `ENABLE_SMART_PICK_VERDICT_CAPTION` (W4-12")]
if len(idx) != 1:
    raise SystemExit(f"SMART_PICK row anchor count {len(idx)}")
new_rows = (rows("docs_flagrows_w411.md")
            + rows("docs_flagrows_w48.md", "#<W48PR>", "#" + W48PR)
            + rows("docs_flagrows_w47.md", "#<W47PR>", "#" + W47PR)).rstrip("\n").split("\n")
lines[idx[0] + 1:idx[0] + 1] = new_rows
cl = ("\r\n" if crlf else "\n").join(lines)
# 2. the SESSION 68b heading + STATUS line
cl = replace_once(cl,
    "## Active runtime (SESSION 68b — the bounded harness + four more units MERGED under it: hermeticity #207, W4-13 #209, W4-6a #212, W4-12 #213; main `15e1fb89`, 2026-09-27 ~04:05 local; W4-8 green / W4-11 red / W4-7 red running)",
    f"## Active runtime (SESSION 68b — the bounded harness + SEVEN units MERGED under it: hermeticity #207, W4-13 #209, W4-6a #212, W4-12 #213, W4-11 #223, W4-8 #{W48PR}, W4-7 #{W47PR}; main `{MAINSHA}`, 2026-09-27 ~{TIME} local; W4-14 next)",
    crlf, "68b heading")
cl = replace_once(cl,
    "**STATUS — main `15e1fb89`.** The session-68 pause was a HARNESS defect",
    f"**STATUS — main `{MAINSHA}` (the first checkpoint of this block was written at `15e1fb89`; the three later units are the rows W4-11 / W4-8 / W4-7 below and the paragraph after the lessons).** The session-68 pause was a HARNESS defect",
    crlf, "68b status")
# 3. the second-half paragraph before the merge-time lessons
cl = replace_once(cl,
    "- **Merge-time lessons (binding):** (1) a Fable ruling can carry a wrong premise",
    f"- **The second half of the session (04:05 → {TIME}, three more units, thirteen adversary rounds):** W4-11 prompt truth (#223 `8a1e0d55`): three SOUND adversaries on the green, a polish round on Fable's R25-R27 (the unflagged name fence coerces before sanitising), two pin gaps closed by the orchestrator; W4-8 category truth (#{W48PR}): SEVEN fix rounds — the same defect class sank three rounds of carve-outs before the design ruling **grams never veto** (R13/R14), then a rung-boundary round (R15/R16: separators, a unit followed by a digit, the per-field L2 exemption), five pin gaps closed by the orchestrator; W4-7 fact-check honesty (#{W47PR}): six fix rounds — the log-silent replay (R19), the cache-hit count unknown-not-zero (R25), a synthetic empty pool is not captured (R28), and finally **captured = a non-empty pool returned this request** (R31) after the adversary measured that price_service never raises on a failed search. Follow-ups filed #215-#226 (+ the W4-8 and W4-7 sets at merge). Harness facts: a bounded fix+adversary round took 25-45 min; `s68b-round` with `maxFixRounds 1` runs ONE EXTRA fix after the first adversary (the loop counts prove-nothing rows) and that fixer sees a stale report line — pass `maxFixRounds 0` for a plain fix+adversary; a subset netguard ratchet can flag an ORDER-DEPENDENT pre-existing node (re-measure alone at base before reading a NEW as a regression — #211 comment).\n"
    "- **Merge-time lessons (binding):** (1) a Fable ruling can carry a wrong premise",
    crlf, "68b second half")
# 4. the Security paragraph's stale residual
cl = replace_once(cl,
    "Known residual: `_smart_fallback_extract` → `openai_service.extract_specs_targeted` still interpolates snippets without a region (out of the M18 finding's scope).",
    "The former residual (`_smart_fallback_extract` → `openai_service.extract_specs_targeted` interpolating snippets without a region) is CLOSED by W4-11 (#223): the targeted and synthesized refill prompts, the url-extraction page and the image tier-3 block are all fenced, every interpolated string on the verdict user message is neutralised, and the product name is coerced then sanitised (`_sanitized_full_name`); the digest fixture `tests/fixtures/w4_11_prompt_render_digests.json` pins every render.",
    crlf, "security residual")
# 5. the W1-3 row: 14 -> 15 dispatch sites
cl = replace_once(cl,
    "every OpenAI dispatch routes through `guarded_llm_create` (**14** measured call sites: `extraction_service` ×8, `openai_service` ×4, `url_extraction_service:396`, `verdict_critique_service:174`)",
    "every OpenAI dispatch routes through `guarded_llm_create` (**15** measured call sites since W4-11 #223: `extraction_service` ×8, `openai_service` ×4, `url_extraction_service`, `verdict_critique_service`, and `image_service.extract_image_via_gpt`, which W4-11 moved from a bare `create` onto the chokepoint)",
    crlf, "W1-3 sites")
wr("CLAUDE.md", cl, crlf)
print("CLAUDE.md patched")

# ---------------------------------------------------------------- state doc s10
sd, scrlf = rd("docs/investigations/2026-09-26-session-68-state.md")
s10 = f"""

## 10. SESSION 68b, second half (04:05 → {TIME} local, 2026-09-27): W4-11 #223, W4-8 #{W48PR}, W4-7 #{W47PR} merged; main `{MAINSHA}`; follow-ups #215-#226 + the two merge sets

**Ledger (every verdict from a harvested agent report; the scripts, rulings and reports are in `2026-09-26-session-68-state/s68b-part2/`).**
- **W4-11 prompt truth (#223, `8a1e0d55`).** Red 52/25/40 at `58a86b3c` → red-gate rulings R16-R24 → green → adversary r0 SOUND (8 minors) → fix r1 → adversary r1 SOUND (2) → fix r2 → adversary r2 SOUND (1: the unflagged name fence raised on a non-string brand) → Fable R25-R27 (coerce before sanitising; the `test_wall_caps_i57.py` amendment ratified; seven housekeeping pins) → fix r3 → adversary r3 SOUND (2 pin gaps, closed by the orchestrator: the name/variant/list slots and the per-string counter). Black-formatted `prompt_personalities.py` at commit time (the pre-commit allowlist). Ship: unit 138 ×4 states, CI-order 38 files 1013 ×4, ratchet OK, digest gate; CI 6/6. Flags `ENABLE_VERDICT_PROMPT_TRUTH`, `ENABLE_PRICE_FALLBACK_MAY_DECLINE`. Follow-ups #224 (PO-PROMPTS-02b), #225 (05b), #226 (05c).
- **W4-8 category truth (#{W48PR}).** The killed session-68 green resumed (a mutant on disk found by sha and restored) → adversary r1 DEFECTIVE → fix r2 → adversary r2 DEFECTIVE on the SAME two classes → design rulings R10-R12 → fix r3 → adversary r3 DEFECTIVE a THIRD time on decimal Wi-Fi bands → R13 **grams never veto** → fix r4 (started before R13; a `< 2 g` bound) → adversary r4 DEFECTIVE on R13 → R14 (R13 restated with every probe string, the micro-sign units, the qualifier floor in the hamza spelling, the bare-alef pins withdrawn → W4-8f) → fix r5 → adversary r5 SOUND (2 minors) → a stale extra fixer stopped itself; adversary r6 SOUND (4 minors) → R15/R16 (separators; a unit followed by a digit is a model code; the MG-brand-plus-year stated limit; the L2 exemption per FIELD) → fix r7 → adversary r7 SOUND (5 pin gaps, closed by the orchestrator; the MG4 conflict ratified toward R16a). Ship: unit 1173 ×4, CI-order 32 files OK ×4; the subset ratchet flagged one ORDER-DEPENDENT pre-existing node (re-measured alone at base; #211 comment). Flags `ENABLE_CATEGORY_TOKEN_FIX`, `ENABLE_BLOCKLIST_PRECISION_V2`.
- **W4-7 fact-check honesty (#{W47PR}).** Red 123/119/20 at `15e1fb89` → red-gate rulings R11-R18 → green → adversary r0 DEFECTIVE (the Part B replay emitted the W4-1/W4-2 canary lines) → R19-R23 → fix r1 → adversary r1 DEFECTIVE only on the unseen rulings → R24-R27 (**the cache-hit count is unknown, not 0**) → fix r2 → adversary r2 SOUND → fix r3 → adversary r3 (4 minors) → fix r4 → adversary r4 SOUND → R28-R30 (a synthetic empty pool is not captured) → fix r5 → adversary r5 DEFECTIVE (price_service never raises on a failed search) → R31 **captured = a non-empty pool returned this request** → fix r6 → adversary r6 SOUND (2 pin gaps, closed by the orchestrator). Flags `ENABLE_RELIABILITY_UNCHECKED_ABSENCE` (coupled to renorm), `ENABLE_CONFIDENCE_SINGLE_COMPUTATION`, `ENABLE_FACTCHECK_SHOPPING_KEY`.
- **Follow-up issues filed from the merged PR bodies:** #215 W4-13b, #216 W4-13c, #217 PO-RECORDED-MEASURED-01c, #218 W4-13d, #219 W4-6b (+W4-7d), #220 W4-6c, #221 W4-12 b-g, #222 netguard nits, #224-#226 W4-11's; the W4-8 (b-h, I18N-09b) and W4-7 (e, f, g, the client plural, two pre-existing test/builder items) sets at their merges (numbers in the session log).

**Harness facts learned (binding).** (1) `s68b-round` with `maxFixRounds 1` runs one EXTRA fix round after the first adversary — its loop condition counts prove-nothing rows — and that fixer sees a stale `latestLine`, so it stops on a sha mismatch: pass `maxFixRounds 0` for a plain fix+adversary. (2) Never stop an adversary mid-run (mutants in flight); stopping a fixer in its first minute is safe after a sha check against the last report. (3) A subset netguard ratchet can flag an order-dependent pre-existing node; re-measure the node alone at base before reading a NEW as a regression. (4) The clock: a fix+adversary round is 25-45 min on this box with two agents; twelve rounds across three units in the half-session. (5) Write rulings with the Write tool BEFORE a launch; the agents read the rulings files at start only.

**Docs owed / done:** the seven flag rows are in CLAUDE.md's SESSION 68b block (this checkpoint); the Security paragraph's stale residual and the W1-3 site count corrected. **Next:** W4-14 (client), the config-audit docs PR, the Step 6 structured review at the milestone end.
"""
sd = sd.rstrip("\r\n") + (s10.replace("\n", "\r\n") if scrlf else s10) + ("\r\n" if scrlf else "\n")
wr("docs/investigations/2026-09-26-session-68-state.md", sd, scrlf)
print("state doc s10 appended")

# ---------------------------------------------------------------- session log
sl, lcrlf = rd("docs/CONTEXT_SESSION_LOG.md")
entry = f"""# SESSION 68b, part 2 — three more W4 units merged under the bounded harness: W4-11 #223, W4-8 #{W48PR}, W4-7 #{W47PR} (2026-09-27 04:05 → {TIME}); main `{MAINSHA}`

**Twelve bounded fix+adversary rounds, every verdict harvested.** W4-11 needed one polish round after three SOUND adversaries (the unflagged name fence coerces before sanitising). W4-8 needed seven: the same defect class — device tablets routed to supplements through a gram-reading dose rung — sank three rounds of carve-outs before the design ruling **grams never veto**; a fourth-round fixer that had started before the ruling was allowed to finish and was judged against it; two more rulings closed the rung's boundaries (separators, a unit followed by a digit, the MG-brand-plus-year stated limit) and the shopping-surface exemption became per field. W4-7 needed six: the listing-count replay had to be log-silent (the W4-1/W4-2 canaries), the cache-hit count had to be UNKNOWN not zero (with Part B on, every warm compare would have read a weak price pill), a synthetic empty pool is not a captured pool, and finally — after the adversary measured that price_service never raises on a failed search — a pool is captured only when it is non-empty; every empty pool keeps today's confidence evidence. The orchestrator closed the final pin gaps of each unit itself (test rows, mutants re-run red, sha-verified restores) rather than spend a round on adjacent mutants of already-pinned rules.

**Seven flags now on main from this session, all default OFF, read per call** (rows in CLAUDE.md): `ENABLE_VERDICT_PROMPT_TRUTH`, `ENABLE_PRICE_FALLBACK_MAY_DECLINE`, `ENABLE_CATEGORY_TOKEN_FIX`, `ENABLE_BLOCKLIST_PRECISION_V2`, `ENABLE_RELIABILITY_UNCHECKED_ABSENCE`, `ENABLE_CONFIDENCE_SINGLE_COMPUTATION`, `ENABLE_FACTCHECK_SHOPPING_KEY` — thirteen for the whole of 68b. Nothing flipped; Railway and Supabase untouched; production `/health` 200 on a fresh process after each merge.

**Harness lessons (binding):** `s68b-round` `maxFixRounds 1` runs one extra fix after the first adversary (pass 0 for a plain fix+adversary); never stop an adversary mid-run; a subset netguard ratchet can flag an order-dependent pre-existing node (re-measure alone at base — #211); rulings are written with the Write tool before a launch. Full ledger: state doc §10.

**Follow-ups filed:** #215-#226 from the earlier PR bodies (W4-13b/c/d, the PostgREST cap, W4-6b/c, W4-12 b-g, the netguard nits, PO-PROMPTS-02b/05b/05c) plus the W4-8 and W4-7 sets at their merges. **Ahmed's items:** unchanged — apply 042 before `ENABLE_SEARCH_LOG_SYNTHETIC_MARKER`; the #101 call (#219); the RunnerUpWinsCard empty state; the W4-8d weapon-intent call and the W4-2 caption call; whether a verdict may ship with ZERO cons (the TRUTH flip); the key rotation.

"""
marker = "# SESSION 68b — the bounded harness built on Ahmed's ruling"
c = sl.count(marker)
if c != 1:
    raise SystemExit(f"session log anchor count {c}")
sl = sl.replace(marker, (entry.replace("\n", "\r\n") if lcrlf else entry) + marker, 1)
wr("docs/CONTEXT_SESSION_LOG.md", sl, lcrlf)
print("session log entry inserted")
