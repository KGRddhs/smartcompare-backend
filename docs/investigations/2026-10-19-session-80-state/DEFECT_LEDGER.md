# DEFECT_LEDGER (session 80): every audit defect and owner item -> unit -> flag -> evidence -> PR

Status vocabulary: PLANNED (in PLAN_S80), SPEC (spec written and reviewed), RED (reproducing tests fail at base, gate passed), GREEN (fix merged dark, pins green), FLIPPED (flag ON in production after canary), CLOSED (client half live on phones). "RED nodes" are the test node ids that fail at base and pass after the fix; "pins" are the flag-OFF identity rows and the regression rows that stay in the blocking suites.

| Defect | Title (short) | Unit(s) | Flag | RED nodes | PR | Status |
|---|---|---|---|---|---|---|
| MYEZ-001 | products that are not the photographed ones (V04) | B3 vision v2; B2 gate (category conflict); B7 KG identity check | ENABLE_VISION_IDENTITY_V2, ENABLE_RESULT_GATE, ENABLE_IMAGE_PIPELINE_V2 | tests/test_s80_b3_vision_identity_v2.py (69 RED / 36 PIN at base) | B3 branch feature/s80-b3-vision-identity-v2 @ 764d4416, PR pending adversaries | GREEN (B3 half; adversaries pending) |
| MYEZ-002 | winner on two Unknown Products (V09) | B1 status; B2 gate (placeholder); B4 URL unresolved | ENABLE_RESULT_STATUS_METADATA, ENABLE_RESULT_GATE, ENABLE_URL_MODE_V2 | tests/test_s80_b1.py + tests/test_s80_b1_feedback.py (191 RED / 23 PIN at base) | B1 branch feature/s80-b1-result-status @ 2bbd58a9, PR pending adversaries | GREEN (B1 half; adversaries pending) |
| MYEZ-003 | winner with an empty spec table (V10) | B1 coverage; B2 gate (no evidence) | ENABLE_RESULT_STATUS_METADATA, ENABLE_RESULT_GATE | tests/test_s80_b1.py + tests/test_s80_b1_feedback.py (191 RED / 23 PIN at base) | B1 branch feature/s80-b1-result-status @ 2bbd58a9, PR pending adversaries | GREEN (B1 half; adversaries pending) |
| MYEZ-004 | two different shirts as one identity (V07) | B2 gate (same identity); B3 distinguishing features | ENABLE_RESULT_GATE, ENABLE_VISION_IDENTITY_V2 | tests/test_s80_b1.py + tests/test_s80_b1_feedback.py (191 RED / 23 PIN at base) | B1 branch feature/s80-b1-result-status @ 2bbd58a9, PR pending adversaries | GREEN (B1 half; adversaries pending) + B3 GREEN @ 764d4416 (vision half) |
| MYEZ-005 | homepage links accepted as product links (V02/V09) | B4 pre-gate; C3 hints | ENABLE_URL_MODE_V2 | tbd | tbd | PLANNED |
| MYEZ-006 | link failure dialog gives no cause | B4 typed codes; C3 copy map | ENABLE_URL_MODE_V2 | tbd | tbd | PLANNED |
| MYEZ-007 | typed input never resolves a model (Hyper X MIC) | B2 gate (no evidence) now; candidates route = follow-up after approval | ENABLE_RESULT_GATE | tbd | tbd | PLANNED (partial) |
| MYEZ-008 | fragrance metrics on beard oil, fashion dims without data (V06/V07) | B5 category truth | ENABLE_CATEGORY_TRUTH | tbd | tbd | PLANNED |
| MYEZ-009 | "Owners say" claims without a source | B6 claims provenance | ENABLE_CLAIMS_PROVENANCE | tbd | tbd | PLANNED |
| MYEZ-010 | price provenance / currency / timestamp | B7 (captured_at, stock_state, retailer_domain, size on the price object); C1 render | ENABLE_IMAGE_PIPELINE_V2 (price keys ride B7) | tbd | tbd | PLANNED |
| MYEZ-011 | visual confidence vs weak data (badge always) | B1 status; B2 gate; C1 three states | ENABLE_RESULT_STATUS_METADATA, ENABLE_RESULT_GATE | tests/test_s80_b1.py + tests/test_s80_b1_feedback.py (191 RED / 23 PIN at base) | B1 branch feature/s80-b1-result-status @ 2bbd58a9, PR pending adversaries | GREEN (B1 half; adversaries pending) |
| MYEZ-012 | credit consumed on an unusable compare | B2 (abstain = non-delivery, R-A3); B1 measures delivered partials | ENABLE_RESULT_GATE | tests/test_s80_b1.py + tests/test_s80_b1_feedback.py (191 RED / 23 PIN at base) | B1 branch feature/s80-b1-result-status @ 2bbd58a9, PR pending adversaries | GREEN (B1 half; adversaries pending) |
| MYEZ-013 | quota renewal copy inconsistent | B9 usage status v2; C4 quota copy | ENABLE_USAGE_STATUS_V2 | tbd | tbd | PLANNED |
| MYEZ-014 | images missing or late, no image state (V01/V03/V06/V07/V10) | B7 image pipeline v2; B4 URL image normalization; C1 placeholder states | ENABLE_IMAGE_PIPELINE_V2, ENABLE_URL_MODE_V2 | tbd | tbd | PLANNED |
| MYEZ-015 | ~40 s scan with a silent loader | B1 timings + telemetry; B3 vision bound; C7 progress + cancel | ENABLE_RESULT_STATUS_METADATA, ENABLE_VISION_IDENTITY_V2 | tests/test_s80_b1.py + tests/test_s80_b1_feedback.py (191 RED / 23 PIN at base) | B1 branch feature/s80-b1-result-status @ 2bbd58a9, PR pending adversaries | GREEN (B1 half; adversaries pending) + B3 GREEN @ 764d4416 (vision half) |
| MYEZ-016 | English inside the Arabic UI | B8 Arabic output (server-side values, lang on image/url, guards); C2 client templates | ENABLE_ARABIC_VERDICT_OUTPUT (existing) | tbd | tbd | PLANNED |
| MYEZ-017 | empty "why we chose" with two prices (V03, URL mode) | B4 recommendation fill; B12 URL unified (later) | ENABLE_URL_MODE_V2, ENABLE_URL_MODE_UNIFIED_RESPONSE | tbd | tbd | PLANNED |
| MYEZ-018 | 16-step onboarding | C5 onboarding short | client | tbd | tbd | PLANNED |
| MYEZ-019 | Google consent says SmartCompare | owner action (Google Cloud branding) after approval; brand pin in C6 | n/a | n/a | n/a | OWNER |
| MYEZ-020 | AI consent sheet long at task start | C6 (placement + sentence-by-sentence render, text unchanged) | client | tbd | tbd | PLANNED |
| MYEZ-021 | bars without scale or source | B5 limited_data captions, measured-fact deltas; C1 render | ENABLE_CATEGORY_TRUTH | tbd | tbd | PLANNED |
| MYEZ-022 | empty sections look loaded | B1 section_status; C1 honest rows | ENABLE_RESULT_STATUS_METADATA | tests/test_s80_b1.py + tests/test_s80_b1_feedback.py (191 RED / 23 PIN at base) | B1 branch feature/s80-b1-result-status @ 2bbd58a9, PR pending adversaries | GREEN (B1 half; adversaries pending) |
| MYEZ-023 | feedback cannot say "not useful" | B1 allowlist widening (unflagged, R-A1a); C6 feedback card | n/a (allowlist) | tests/test_s80_b1.py + tests/test_s80_b1_feedback.py (191 RED / 23 PIN at base) | B1 branch feature/s80-b1-result-status @ 2bbd58a9, PR pending adversaries | GREEN (B1 half; adversaries pending) |
| MYEZ-024 | examples ignore the selected category | C6 trending filter | client | tbd | tbd | PLANNED |
| MYEZ-025 | "Northern · GCC" profile label | B9 region key; C6 label | ENABLE_USAGE_STATUS_V2 | tbd | tbd | PLANNED |
| MYEZ-026 | disabled Compare button unexplained | C3 hints (Build Principle #4 yields) | client | tbd | tbd | PLANNED |
| MYEZ-027 | unreliable results saved and shared as decisions | B1 stored status + winner_index None; B2 (abstains are not saved) | ENABLE_RESULT_STATUS_METADATA, ENABLE_RESULT_GATE | tests/test_s80_b1.py + tests/test_s80_b1_feedback.py (191 RED / 23 PIN at base) | B1 branch feature/s80-b1-result-status @ 2bbd58a9, PR pending adversaries | GREEN (B1 half; adversaries pending) |
| MYEZ-028 | results page hierarchy | C6 results hierarchy; C1 decision block | client | tbd | tbd | PLANNED |
| OWNER-CAMERA | the AI cannot spot products from the camera | B3 vision v2 (+ OPENAI_MODEL_VISION knob, owner smoke test) | ENABLE_VISION_IDENTITY_V2 | tests/test_s80_b3_vision_identity_v2.py (69 RED / 36 PIN at base) | B3 branch feature/s80-b3-vision-identity-v2 @ 764d4416, PR pending adversaries | GREEN (B3 half; adversaries pending) |
| OWNER-IMAGES | product pictures missing | B7 image pipeline v2; B4 URL images | ENABLE_IMAGE_PIPELINE_V2, ENABLE_URL_MODE_V2 | tbd | tbd | PLANNED |
| OWNER-INFO | product information does not show | B4 (URL mode), B12 (URL unified), B7 early stash, B5 | ENABLE_URL_MODE_V2, ENABLE_URL_MODE_UNIFIED_RESPONSE | tbd | tbd | PLANNED |
| OWNER-SCRAPERS | fix the scrapers incl. ours | B4 (URL-mode scraper), B7 (image tiers), B11 (breakers, timeouts); owner keys | ENABLE_URL_MODE_V2, ENABLE_IMAGE_PIPELINE_V2, ENABLE_SCRAPER_HEALTH_V2 | tbd | tbd | PLANNED |
| OWNER-OPENAI | fix the OpenAI response/flows | B3 (json_schema, finish_reason, bound); B10 (typed errors, seam) | ENABLE_VISION_IDENTITY_V2, ENABLE_ANTHROPIC_PROVIDER | tbd | tbd | PLANNED |
| OWNER-ANTHROPIC | Anthropic placeholder | B10 | ENABLE_ANTHROPIC_PROVIDER | tbd | tbd | PLANNED |
| OWNER-FRAGRANCEX | ingest the FragranceX catalog | D1 (warm list + spine, Option C); Option B = owner/legal; Option A rejected (R-A11) | ENABLE_SPEC_SPINE (existing) + SPEC_SPINE_SKIP_LLM knob | tbd | tbd | PLANNED / OWNER |

Audit regression list T01-T15 -> hermetic layer and unit: see `runs/research/eval_regression.json` (T11 is owner/device only; the vision half of T01, the CDN halves of T07/T08, the GPT halves of T09/T14 are live/eval rows, recorded as such, never claimed as unit-tested).
