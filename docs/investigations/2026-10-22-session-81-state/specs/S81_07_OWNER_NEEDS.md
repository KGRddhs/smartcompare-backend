# S81-07: what the measurement run needs from the owner (session 93, 2026-11-12)

State: the harness passed its fix round (commit e600215d, re-verifier SOUND, no live call ever made). It is NOT yet ready to run: main moved three times under it, so one more round brings main in and re-measures (see the last section). Everything below stays the same after that round; only the commit changes.

## 1. His Anthropic TEST key, in a file he creates himself

- A file on this machine, OUTSIDE the repository, holding one line: the key and nothing else. He creates it. No agent opens it, prints it or copies it.
- The harness reads the key from ONE variable, `MEAS_ANTHROPIC_TEST_KEY`, set for that one process only. It removes the variable from its environment right after reading it.
- It must be a TEST key of his Anthropic workspace, not a production key. The workspace's own spend limit is the only backstop across output folders.

## 2. The command, exactly (he runs it in his own Git Bash terminal, or tells the relay to run it with the PATH of his file)

```bash
cd <WORKTREE> && MEAS_ANTHROPIC_TEST_KEY="$(cat <KEYFILE>)" env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY -u <NAME> <PY> -m scripts.meas_claude_gate <stage> --out <OUT>
```

- The assignment stands BEFORE the word `env`, never after it. Written after `env`, the key would show in the process list for the whole run.
- `<WORKTREE>` = `C:/Users/SynAckITPC/Documents/AI/sc-s81-s07` (it has no dotenv file).
- `<KEYFILE>` = the path of his key file. The path is in the command; the value never is.
- `<PY>` = the `.venv-qaren` interpreter.
- `<OUT>` = ONE absolute folder outside the repository, the same for every stage (the 15 USD ceiling is counted per folder).
- `<NAME>` = each further variable name that the harness's one-line refusal lists. It refuses to start while any `ANTHROPIC_*` name or any other credential name of the project is set, and it names them.

A dry run costs nothing and needs no key; it carries NO assignment:

```bash
cd <WORKTREE> && env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY -u <NAME> <PY> -m scripts.meas_claude_gate <stage> --dry-run --out <OUT>
```

## 3. The order of the stages

`text`, `moderation`, `vision`, `web_search`, `report`. He may stop after any stage.

- One rule for the text stage: its LAST run before `report` must run every setting (no narrowed `--settings`). A stopped stage is resumed with the same command; it replays what is done and sends only what is missing.
- If a resume is refused for the ceiling although money is left, lower `--max-usd` to the remaining amount.

## 4. The money

- His cap: 15 USD for the whole unit (his line of 2026-11-06). The harness refuses to start a stage that could pass it.
- Stage caps: text 4.00, moderation 2.00, vision 5.00, web search 3.00 USD. Each stage stops itself at its cap, at its call limit and at its time limit (90, 20, 60 and 20 minutes).
- Planned worst case (real spend is lower): text 622 calls 1.44 USD; moderation 200 calls 0.26; vision 300 calls 3.61 on 100 photos; web search 80 calls 1.33. Together 6.65 USD at worst.

## 5. For the VISION stage only

The harness's own words: "the owner supplies --set <dir> holding 100 owner-taken packaging photos (about 30 with Arabic labels) and a manifest.json of [{file, label_lang, expected_brand, expected_name}]; no faces, no people, no personal data."

- Without `--set` the stage says NOT RUNNABLE and costs nothing.
- It is needed before the 1.0.1 store submission (the reviewer's camera), not for the text and verdict flips.

## 6. For the WEB-SEARCH stage only (optional; the unit that would use web search is not built)

- His dated line enabling web search, passed as `--owner-line`. Without it: NOT RUNNABLE, no cost.
- The stage names three public retailer domains to Anthropic's search tool as the allowed domains: boutiqaat.com, faces.ae, noon.com. The harness itself contacts none of them.

## 7. Optional: a flag state

`--flags-file <file>` with lines of the form `ENABLE_<NAME>=true` or `ENABLE_<NAME>=false`. Without it the code defaults apply, and the report says which case ran.

## 8. What he gets

`<OUT>/REPORT.md`: GO, NO-GO or NOT RUN per role (TEXT, VERDICT, SONNET_ESCALATION, MODERATION, VISION) against the pass bars below; the cost per synthetic compare; the compares per day at the code-default cap (he recomputes with the live cap; the formula is printed); the cache-read share; three timeout proposals beside the code-default values. No key, no header and no personal data is in the folder: the inputs are synthetic.

## 9. The pass bars he should see before the run (specs/RULINGS_S81_07.md, copied)

## R-S07-31 THE GO BARS (ruled here as PROPOSED PASS BARS; they reach the owner through the relay before the run; the report prints every raw figure, so a changed bar needs no second run)
| role | bar | source |
|---|---|---|
| TEXT | JSON validity >= 0.98 pooled over the JSON sites of A1 and no site below 0.90 (18 of 20); schema acceptance 1.00 at every site with a format; refusals per R-S07-23; max_tokens hits <= 0.02 pooled and no site above 2 of 20; p95: classify <= 4.0 s, specs <= 4.0 s, reviews <= 5.0 s, price <= 7.5 s, image_tier3 <= 2.5 s; zero timeouts | CLAUDE.md:508; the classify timeout 4.0; half of each leg bound (a HEURISTIC: the LLM call shares its leg with search); the call deadline 25.0 |
| VERDICT | JSON validity >= 0.98 pooled over the verdict calls of A1 and A6; A6 winner mismatch <= 0.10 and repeat agreement >= 0.90; at most 1 refusal in A6 and 0 in A1; zero timeouts | PLAN_S81.md:86; absolute bars (no OpenAI baseline can be run: R-S07-9) |
| SONNET_ESCALATION | A3: 20 of 20 accepted with between_tools; JSON validity >= 0.95 | R-S06-15 |
| CRITIC | NOT RUNNABLE (no live site since S81-22b); the relay dropped the critic flip from the window list on 2026-11-11 | spec 2.6 |
| MODERATION (window 14) | 0 false positives on the 80 benign cases (the 0.01 bar at n = 80); recall >= 0.90 on the 20 flag-worthy (18 of 20); fail-closed at most 1 of the cases run; p95 <= 3.0 s (a HEURISTIC, no code source) | R-S06-6; CLAUDE.md:508 |
| VISION (window 21, with NT1) | identity hit rate: Haiku >= Sonnet - 0.05 and >= 0.80 (vision_v2); p99 <= 20.0 s with timeouts as samples | the vision timeout 20.0 |
| WEB_SEARCH | a design input for S81-21: no flip bar | PLAN_S81.md:123 |
REPORTED, NOT A BAR: the cost per synthetic compare (p50, p95) and the compares per day it allows under the breaker's live cap (the breaker is the control); the three timeout proposals (classify = p99 x 1.25; vision = p99 of vision_v2 x 1.25; tail per R-S07-20), each rounded up to 0.5 s and printed beside the current value and the knob NAME. A knob changes only by the owner's dated line.

## 10. What is still to do before the run (the main lane, on the relay's yes)

One round, about 0.55 million Opus tokens and about two hours: bring the current main into the unit branch (it is three merges behind, and the last one touches the dispatch code the harness reads), take five small findings of the re-verifier in, measure the regression comparison against the new main, then push, open a draft PR and read CI. The measurement must run on the code that will be flipped.
