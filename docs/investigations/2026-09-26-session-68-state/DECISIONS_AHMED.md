# Eleven product calls Ahmed owes — with the orchestrator's recommendation (2026-09-28, session 68b close)

Each item gates a flag flip or a unit; none blocks anything already on main (every flag is OFF). Items 1 and 2 carry the session-67 options unchanged (the flag name and the #219 scope updated; the numbering is swapped); 3–11 were recorded in the W4 rulings and PR bodies during sessions 68/68b. Answer with the letter; the spec or the flip follows.

## 1. Issue #101 / W4-6b (#219) — a missing signal outscores a measured bad one (`MISSING_SCORE = 50`)

Unchanged from 2026-09-24: **(A) renormalize** over the dimensions actually present and render the missing one as "no data" (the flag `ENABLE_MISSING_DIM_RENORM` already exists, default OFF; W4-6b #219 adds the honest sentinel arithmetic under renorm, lifts the tie/renorm coupling and the N/A for a renorm-excluded dimension winner); **(B)** keep 50 but cap it below the worst measured score; **(C)** leave it and document the bias. **Recommendation: (A).** #101 itself is CLOSED (2026-09-01); the call is still open — answer here or on #219. Your answer unblocks #219, and through it the activation of `ENABLE_RELIABILITY_UNCHECKED_ABSENCE` (W4-7 A: W4-6b's tie-break → renorm → A), and lets `ENABLE_TIE_IS_NOT_MISSING` stay effective once `ENABLE_MISSING_DIM_RENORM` is ON (today renorm silently disables it).

## 2. W4-2 `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` — the "(converted from USD)" rendering

Unchanged from 2026-09-24: **(a)** accept the label as shipped (honest, no PDP link for those rows); **(b)** a third showable-but-not-genuine label (its own backend + client + OTA unit); **(c)** resolve the merchant PDP before the row shows (a new spend line). **Recommendation: (a) now, (c) later as a bounded off-clock unit.**

## 3. #248 — `category_switched`: disclose the switch or make the chip authoritative

The type and both catalogs carry `category_switched`, but it renders nowhere (its banner was deleted under the no-info-banners rule), so when a deterministic name hit outranks the user's chip on the explicit-pair path the user is never told. **(a)** a one-line disclosure (the catalog key exists in both languages; a small mobile unit + OTA); **(b)** chip-authoritative precedence on explicit_pair (`ENABLE_CHIP_WINS_OVER_NAME_DETECT`, a resolver change in the W4-8 family). **Recommendation: (a) first** (zero scoring risk, honest), **(b) as a flagged W4-8-adjacent unit** measured on the 360-query corpus.

## 4. #231 — W4-8d: EN weapon-intent phrasings v3 and an intent-word guard on the co-occurrence exemption

`ENABLE_BLOCKLIST_PRECISION_V2` shipped with the ruled recall-over-precision default and an OPEN co-occurrence exemption (a weapon term beside a device/game term passes). Issue #231 lists the measured phrasings v2 still misses and the guard that would close them. **(a)** ship a v3 list + the intent-word guard as its own flagged unit (`ENABLE_BLOCKLIST_PRECISION_V3`), corpus-gated like v2; **(b)** keep v2 as is and accept the listed misses. **Recommendation: (a)**, after v2 has run ON for a week with its canary (the `CONTENT_UNAVAILABLE` rate, the newly-allowed queries carrying an exempted token plus intent wording, the L2 `dropped N/M` INFO lines) so v3 is measured against real traffic, not only the corpus.

## 5. W4-7 ruling R12 — ANY pending shown price caps the price-confidence leg at "weak"

The spec had "PDP + google strong at every count"; the ruling replaced it with: when any shown price is still pending, the price leg is at most weak and the overall is recomputed. **(a)** keep R12 (the pill never claims strength on a price the user cannot see); **(b)** loosen to the spec's rule. **Recommendation: (a).** Only matters once `ENABLE_CONFIDENCE_SINGLE_COMPUTATION` is ON.

## 6. W4-11 `ENABLE_VERDICT_PROMPT_TRUTH` — verdicts with ZERO cons

The TRUTH prompt removes the "never return empty cons" rule and the "2–4 cons" quota: a con appears only when the sources show one, so some verdicts will ship with an empty cons list (the pros list is still never empty). **(a)** yes — honest cons, with the canary (the `[VERDICT_TRUTH] cons empty=N data_gap=N` line — the share of verdicts shipping empty cons and the data-gap phrase hits — read for a week after the flip; a per-category split needs the category added to that line); **(b)** no — keep the quota. **Recommendation: (a).** Its response-side twin, the data-gap cons scrubber, is #225 (W4-11's PO-PROMPTS-05b) and can follow.

## 7. W4-6a — the RunnerUpWinsCard empty state before either W4-6a flag flips

`ENABLE_VALUE_DIM_PARTIAL_SIGNAL` and `ENABLE_TIE_IS_NOT_MISSING` both turn the tradeoff guard on: a sweep pair ships `tradeoffs: []` and `key_tradeoff: ''`, which reverses today's always-render fallback on the phone. The card needs an honest empty state (or to hide) before the flip. **(a)** hide the card when there is nothing to show; **(b)** a one-line "no clear runner-up wins" copy in both languages. **Recommendation: (a)** — the no-info-banners rule already applies; a small mobile unit + OTA.

## 8. #220 — W4-6c: a non-numeric merit discriminator for fashion / other

For categories with no numeric spec merit the rubric cannot separate two products beyond price and reviews; the issue proposes a bounded qualitative discriminator (its xfail(strict) pin is on main). **(a)** spec it as a flagged unit now; **(b)** defer until the W4 canaries have run. **Recommendation: (b)** — it is the one W4 item with no measured defect count behind it yet.

## 9. W4-12 — the gpt-4o spend on a verdict sentence the phone out-renders, and the stored leaking share reasons

Recorded in the W4-12 rulings (F5) and in PR #213's body under "DECISIONS_AHMED (F5)"; no issue carries them (#221 is W4-12 b–g + the mobile lane). **(i)** whether to keep paying the gpt-4o `priority=high` call for a verdict sentence that `FactualVerdict` out-renders on 23 of 23 recorded payloads, or cut / downgrade that spend — **recommendation: downgrade (the cheaper model), not cut**, until W4-11's TRUTH prompt and OpenAI credits are live and the sentence can be re-measured; **(ii)** whether to backfill the stored `overview.winner.reason` values that leak score internals and are served verbatim by the unauthenticated `GET /share/{token}` — 17 of the 26 recorded corpus rows leak; the production count is UNMEASURED, so a dry-run count is the real number — **recommendation: yes, one script, dry-run counted first.**

## 10. W4-13 — PO-RECORDED-MEASURED-17: an `anon_id` on `search_logs` rows

Today anonymous compares write `user_id` NULL (only 37 of 16,283 rows in the review's pull carried a user_id) and NO device identifier — nothing is written that could be "kept". The recorded call is whether to START writing a fingerprint-derived `anon_id`: it needs a new column plus a migration, it makes the analytics rows re-linkable to `users.device_fingerprint_hash` (a `docs/privacy-data-inventory.md` line), and W4-13 deliberately did NOT build it (ruling Q5). **(a)** build it behind a flag with the migration and the privacy line; **(b)** leave the rows anonymous as today. **Recommendation: (b)** — W4-13's synthetic marker already fixes the measurement problem the finding was about, and (a) is a privacy cost no reader has asked for yet.

## 11. W4-6a ruling R7 — sign off the score movement `ENABLE_TIE_IS_NOT_MISSING` causes

The design is correct and pinned, but the FLIP is a product sign-off (ruling R7): with T ON, 54 of 144 grid rows, 11 margins and 6 badges move, 0 winner flips (32 of 144 badges with `ENABLE_CATEGORY_VALUE_BADGE`). **(a)** sign off and flip T after V has run alone; **(b)** hold T. **Recommendation: (a)**, after V's week alone.
