# RULINGS_INC_H1 (orchestrator S95-FIX, Claude Opus 5.5, 2026-11-14): rulings on .qa-s80/INC-H1_UNIT_SPEC.md (sha256 28504e3a5ebc...) and .qa-s80/INC-H1_SPEC_REVIEW.md (BLOCK, three blocking points). Binding on the RED and on GREEN

Precedence: this file, then the review's corrections, then the spec, then the rulings brief (specs/INC_H1_RULINGS_BRIEF.md) where they differ.

## A. The blocking points

- H1-R1 (review B2, Q1) S1 IS NARROWED, so no real-data pair's score moves:
  (a) THE SPECS CHIP: the specs-leg citation count (the input of compute_confidence's specs leg, _product_fact_check_pcts and its peers) excludes empty and NA-token values and non-field keys, in every category, under the flag. A chip can then no longer read strong from empty fields; a pair whose real fields are few reads lower than today, which is the intended honesty.
  (b) RELIABILITY: verify_spec_citations (and the #107 cached map filter) changes ONLY for a product with NO real spec field: its fact-check rows become empty, so its reliability total is 0 = missing, and no reliability-proxy bar or "leads on <dim>" line is built from nothing. A product with at least one real field keeps today's grading and reliability BYTE-IDENTICAL (its empty fields still count as today in the reliability denominator).
  RED rows: the recorded D2F fixture pair (data-rich Sauvage) keeps its 79/68 reliability and its Versatility dim with the flag ON (a PIN); the incident shape (all empty on one or both sides) loses the reliability dim; a non-fragrance pair with real fields is unchanged (a PIN). Add L-DENOMINATOR as the stated limit: a product with real fields still has its empty fields in the reliability denominator (INC-X6 owns the bar semantics).
- H1-R2 (review B1) R12 asserts has_review_data occurs exactly twice per twin (the shape line and the rule line), plus count(_H1_SHAPE_LINE) == 1 and count(_H1_RULE_LINE) == 1.
- H1-R3 (review B3, Q5) YES, inside H1-4: under the flag the fact-check skips non-field keys (not spec_field_key(key)), so an extraction error dict ({"error": ...}) grades nothing; with H1-R1 (b) such a product has reliability missing. Add R7b, an error-dict case in R10 and the matching mutant.

## B. The review's other questions

- H1-R4 (Q2, M3) has_review_data true WINS over the phrase guard; the phrase guard applies only when has_review_data is absent (older cached dicts, a model that omitted the key); "provided search results" counts only together with a negation word (no, not, without, unavailable, insufficient); the rule line drops "(the same brand, line and concentration)". Add the PIN row of M3 (has_review_data true, no positive highlight, a "Based on the provided search results..." consensus -> praise equals the OFF praise).
- H1-R5 (Q3, M5) Pre-flip empty L2 entries are PROMOTED AS TODAY (option b); the wire views still apply to them, so no dash row or no-data praise reaches the phone. No negative cache in this unit. New writes follow H1-6 (an all-empty sheet or a no-data review is not written). State L-RECOMPUTE (an always-empty product re-runs its specs and reviews calls on each request) and L-OLDCACHE.
- H1-R6 (Q4, M4) With H1-R1 (b) the one-side shape is no longer enlarged by this unit (the real side keeps today's reliability; the empty side becomes missing). L-ONESIDE stays a stated limit owned by INC-X6; H1 may flip before or after INC-X6. The spec measures the one-side cell again under H1-R1 and states the numbers.
- H1-R7 (Q6, O4) YES: the two prompt twins join tests/test_prompt_fence.py's guard loop (the D08 E2 precedent), as an E-row.
- H1-R8 (Q7) The orchestrator files the INC-H1 row (and INC-R1, INC-I1) in DEFECT_LEDGER_INCIDENT.md before this RED; the RED does not wait for it.
- H1-R9 (Q8, M1) _verdict_safe_product strips has_review_data (a one-key edit, under the flag), so the verdict prompt input is unchanged by the new key; the twin-shaped reviews' other effects on the verdict input are a stated limit (L-VERDICT-INPUT).

## C. The spec's open questions

- H1-R10 (O1) ACCEPTED: omit on the WIRE (the response projections, the specs rows and the SSE frames); the data-stage stamps at extraction_service.py:1706-1707 and structured_comparison_service.py:3551-3552 stay, so refills, scoring of real pairs, captions and the verdict input do not move.
- H1-R11 (O2, RC4, M2) The token set is the measured union; the client NA set differs ("-", the em dash, "or null"), so the spec restates 1.5 and 2.6 and adds the T04-like row of M2.
- H1-R12 (O3) cached=<yes|no> means "served from L1 or L2 for this request".
- H1-R13 (O5) YES: honest_empty.py and the RED files join .github/black-clean-paths.txt (the MON1 precedent, the same rule as INC-I1).
- H1-R14 (O6) No coverage floor on the chip in this unit (candidate follow-up, filed in the ledger).
- H1-R15 (O7, O8, O9, O10, O11) Accepted as the spec proposes.
- H1-R16 (O12) The flip order is the relay's; the proof (H1-R18) does not depend on INC-R1 being off.

## D. Corrections, class and proof

- H1-R17 (M1, M2, M5 to M11, m1 to m10, RC1 to RC12) Accepted as written, with H1-R1 replacing every part that assumed the wide S1 (the D2F rows become PINs that it is unchanged, M7's walk recomputed under H1-R1, M4's numbers recomputed). The scanner-keyword renames of m1 are binding (HONEST_NA_WORDS, SPEC_META_FIELDS, REVIEW_TEXT_LISTS).
- H1-R18 PROOF ON THE PHONE (amended): (1) on a consent-3 account, a comparison of a product with no spec data shows no dash rows, the Specs chip not High, no Versatility bar or "leads on Versatility" built from the empty product, and no "No review data was available" sentence; the check counts only when the log shows specs_dropped > 0 (or a reviews=no_data line) for that product and the saved row's reviews carries a review_summary without an "error" key; (2) Sauvage EDP vs Bleu de Chanel EDP: every row whose two values are real is still shown with the same values, and the Versatility bar is unchanged (backing: the saved row's scoring_v2 dims against a pre-flip row of the same pair); (3) a below-consent-3 account: no Versatility bar built from error dicts.
- H1-R19 Class FOCUS: two adversaries at GREEN (correctness including the scoring PINs of H1-R1; contract-and-live-bundles).
- H1-R20 The RED round writes the RED files on the spec as amended by this file, proves each RED fails at base on an AssertionError only and each PIN is green at base, measures the base pass state of the touched files through harness/gate.py only, and freezes the files with their sha256.
