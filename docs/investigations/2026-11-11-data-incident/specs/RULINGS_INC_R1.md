# RULINGS_INC_R1 (orchestrator S95-FIX, Claude Opus 5.5, 2026-11-14): rulings on .qa-s80/INC-R1_UNIT_SPEC.md (sha256 0676c198...) and .qa-s80/INC-R1_SPEC_REVIEW.md (BLOCK, five blocking points), with the brief's open points O-1..O-13. Binding on the RED and on GREEN

Precedence: this file, then the review's corrections, then the spec, then the brief (specs/INC_R1_BRIEF.md), then the rulings brief (specs/INC_R1_RULINGS_BRIEF.md) where they differ.

## A. The blocking points

- R1-R1 (B1, PC-1) E6 joins section 4.1: tests/test_s81_s22b_self_critique_retire.py SITES_BASE gains the resolve row in the form R1-R7 fixes; the file joins 1.10 B1, G3 and the G5 CI-order set.
- R1-R2 (B2, Q1, OQ-11, O-6) DEFER: llm_router.route stays BYTE-EQUAL, docstring included (MON1's AST digest of route, tests/test_inc_mon1_credential_health.py:102, stays green). R30, P30b, M36 and E7 are dropped. Stated limit: if ENABLE_SONNET_ESCALATION is ever flipped, the resolve site could take the compare's single escalation; a follow-up must land before that flip (filed as a candidate).
- R1-R3 (B3, Q2, RC-3, O-7) NON-FRAGRANCE PAIRS ARE NEVER ASKED: (a) D10: a house hit marks a side as a fragrance only when category_gate.scan reports no non-fragrance term for that side (bag, shoes, watch, pen, coat, jacket, and the gate's own blocked/evidence words); (b) clause 4: the model's is_fragrance for a side wins when it is True or False, the deterministic signal counts only when the model said nothing; (c) explicit R1-7 (iv): model false/false (or deterministic non-fragrance on both) with no Fragrances chip -> passthrough, no refusal; (d) the model call itself is skipped when a non-fragrance chip is sent or both names keyword-classify to a non-fragrance category. Rows R14, R22 d15-d17 and the worked cases ('Gucci Marmont bag' vs 'Prada Galleria bag', Montblanc pen vs Cartier pen, Burberry coat vs Gucci jacket, 'FreeStyle Libre 2' vs 'FreeStyle Libre 3') plus their mutants.
- R1-R4 (B4, Q3) A QUALIFIER set (for, men, mens, man, male, him, his, homme, pour (before homme), tester, original, authentic, genuine, new) is dropped from the D8 residual and allowed outside the guard-(d) window; it is never removed before the line search. Her, femme, women, woman, lady, ladies and female are KEPT as distinct-product words (Aventus for Her stays unresolved). Rows R11b, R21 g12, R22 d18 and a mutant.
- R1-R5 (B5, Q4) Size removal is SPAN-BASED on the raw text with the repository's extract_size_ml_any patterns (_SIZE_ML_RE, _SIZE_OZ_RE); a digit token outside a size span is never removed. Rows R06b: 'Baccarat Rouge 540 70 ml' -> size 70, line keeps 540; 'Baccarat Rouge 540 Extrait 70ml'; 'Dior Sauvage 3.4oz' -> 100; '1.7 fl oz' -> 50.

## B. The review's other questions

- R1-R6 (Q5, CR-1, RC-6, OQ-5, O-4) Only an answer obtained while _llm_router.decide('text') == 'anthropic' counts as a usable model verdict; otherwise the model arm is SKIPPED (no call). The LRU serves a cached model answer only to a request whose decide('text') is anthropic. So R1-7 (iii) and R1-12 (4) hold in every flag mix, not only through the egress stop.
- R1-R7 (Q7, CR-3, OQ-13, OQ-14) The resolve site takes R-S06-1 option (b): NO output_config.format (no closed schema), the JSON-only line and the Claude-branch fence strip, like the eleven prose-JSON sites and image_tier3 since S81-07c (the measured first-use grammar compile and the +0.25 to +0.35 s p50 per schema site). The deterministic guard (R1-6) validates every field, so a schema adds latency without adding safety. SiteSpec('text', 384, None, True). PRODUCT_RESOLVER_TIMEOUT_SECONDS stays 2.5; a timeout is a passthrough (today's behaviour), never a refusal. The canary reads the [RESOLVE] ms= field; adding the site to the S81-07 harness is a follow-up.
- R1-R8 (Q6, CR-2, OQ-2) A single-token line matched at distance > 0 with no typed house is HIGH only when the pair carries a fragrance context (the other side resolved as a fragrance, the Fragrances chip, or a concentration or form word on either side); otherwise MEDIUM (it then goes to the model arm when R1-R6 allows a call, else passthrough). The owner's pair still resolves ('Tyger' with 'stronger with you' resolved). SL16 is rewritten with the measured words (sausage, salvage, savage, aventis, dalton, lire, errs, tagar ...).
- R1-R9 (Q8, CR-4, OQ-6) The ask carries usage_consumed_keys and refunds through the _result_gate_exit form (the S81-20 precedent), so R-A3 holds literally: no credit consumed, no lifetime count, no history row.
- R1-R10 (Q9, CR-5, OQ-7) When ENABLE_FRAGRANCE_ONLY_GATE is ON, an ask is counted on the S81-10 refusal budget exactly as S81-20 counts its refusals; with the gate OFF nothing is counted (today's production).
- R1-R11 (Q10, C-5) A typed concentration outside the line's concentrations ('Khamrah EDT', 'Aventus EDT') resolves MEDIUM, never HIGH.
- R1-R12 (Q11, C-8) The INC-R1 pointer sentence joins the CLAUDE.md '**Feature Flags:**' line (the S81-12d and S81-07c convention) besides the block before '## Tests'.

## C. The spec's and the brief's open questions

- R1-R13 (OQ-1) Optimal-string-alignment distance (an adjacent transposition costs 1).
- R1-R14 (OQ-3) The backend error string of the ask is the reviewed OTA sentence of en.json:703.
- R1-R15 (OQ-4) A guard-rejected model answer with is_fragrance True (any confidence) is a fragrance-intent signal for R1-7 (ii): ASK.
- R1-R16 (OQ-8) The [RESOLVE] line gains cached=<0|1>.
- R1-R17 (OQ-9, C-10) product_resolver.py and the two RED files join .github/black-clean-paths.txt.
- R1-R18 (OQ-10, O-1, O-2) YES: under ENABLE_PRODUCT_RESOLVER the reason placeholder_identity and the additive candidates reach the sync 400 at both gates (text_routes._surface_comparison_failure and error_handler.http_exception_handler) for the resolver's own refusal only, with the flag-mix walk of spec 2.14 (ENABLE_RESULT_GATE on and off). RC-2: the error handler reads the flag only after the refusal marker matches (no flag read on every HTTPException), or the spec states and pins the read; C-3's getenv and open() spies join P01.
- R1-R19 (OQ-12) Twelve seed lines (the R1-4 list).
- R1-R20 (OQ-15, CR-7) A pair that resolves to one canonical product proceeds (S81-20 decides when its gate is on); stated limit SL19.
- R1-R21 (OQ-16) A backend unit with no client file runs the fourteen client fences that read repository files, not the full jest suite (the memory rule), once at GREEN.
- R1-R22 (O-3) The resolver is keyed on the request's explicit_pair; the q= pre-split and stall-guard shapes built by _explicit_pair_products are unchanged.
- R1-R23 (O-5) Concentration when none is typed: the line file's base; for a model-resolved line with no seed entry, None (the model's concentration is not used unless typed). A typed concentration always wins.
- R1-R24 (O-8) PROOF ON THE PHONE gains check 5: on a consent-3 account, an unseeded pair typed without houses, 'hacivat' vs 'erba pura', resolves through the model arm to Nishane Hacivat and Xerjoff Erba Pura (backing: the [RESOLVE] line with source llm on both sides).
- R1-R25 (O-9) The store JS 683f56c0 shows its generic thin-data line for every INSUFFICIENT_DATA: a stated limit (the frozen contract anticipates it).
- R1-R26 (O-10, O-11, C-15) The backing of an ask is the GET /api/v1/text/compare access line with status 400 plus the [RESOLVE] outcome=ask line and no 'Fetching reviews for:' line for that request; every backing read is on the sync GET route; for check 4 the primary backing is the [RESOLVE] line plus the OpenAIEgressStoppedError class WARNING, never an absence on a shared log.
- R1-R27 (O-12) History titles show line names without the house (product_names hold names): a stated limit.
- R1-R28 (O-13) PRODUCT_RESOLVER_ASK values '0', 'false', 'no' and 'off' (case-insensitive, stripped) mean resolve-only; anything else, blank or unset included, is ON.

## D. Corrections and class

- R1-R29 (C-1 to C-16, RC-1 to RC-7, PC-1 to PC-4) Accepted as written, with R1-R2 replacing every part that edited route() and R1-R7 replacing the closed schema (RESOLVE_SCHEMA becomes the parser's own validation, not a router schema; the E-rows carry None for the schema). C-14: a brand accepted through guard (c)'s typed-token clause is logged as '-' in the [RESOLVE] line.
- R1-R30 Class FOCUS: two adversaries at GREEN (correctness; contract-and-live-bundles including billing, the refusal envelopes on both bundles and the LLM routing in every flag mix).
- R1-R31 The RED round writes tests/test_inc_r1_resolver.py and tests/test_inc_r1_seam.py on the spec as amended here, proves each RED fails at base on an AssertionError only and each PIN is green at base, measures the base pass state of the files the unit touches through harness/gate.py only, and freezes the files with their sha256.
