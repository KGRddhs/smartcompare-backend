# RULINGS INC-C1 OTA-BATCH spec V2 (S98 orchestrator, 2026-11-22 about 00:40 AST)

Spec V2: c1/spec/INC_C1_UNIT_SPEC_V2.md (sha256 3f226eb8c7fe7904..., wf_1813e99c-64b, Opus 5.5), written from the accepted draft, the review, GATE_INC_C1_SPEC.md (F1-F13, Q1-Q10) and the addendum A-1..A-5, re-measured at main d2f49d8b. These rulings bind on V2 at the lane level; the relay's questions stay open for the relay.

- RC-1 (Q11) ACCEPTED: F13's two buttons ("Type the names" primary, Back secondary with testID results-empty-back; header back unchanged) sit on the NEW camera photo-unavailable state, which is C1-4's state (the 503 LLM_UNAVAILABLE identify answer). Every other engine / outage state stays byte-identical with its one Back button. This meets F13's intent for the camera failure and keeps the change minimal; row C2 pins the other states.
- RC-2 (Q12) ACCEPTED: the generic link sentence only for BAD_REQUEST and codeless failures; AUTH_REQUIRED, VALIDATION_ERROR and other codes keep today's copy.
- RC-3 (Q13) ACCEPTED: SD-L2 stands; ENABLE_URL_MODE_V2 stays off until same_url / url_too_long are worded in a later unit; no key is added now (scope).
- RC-4 (Q14) ACCEPTED: A-1 is server dependency SD-V1 for the extraction lane (extract_specs copies volume_ml without its unit); no client unit normaliser (it would guess the unit).
- RC-5 A-2 (SD-V2) and A-3 (SD-V3) are server dependencies for the verdict-prompt lane; the relay routes SD-V1..SD-V3 to the owning lanes. Nothing server-side is built in this unit.
- RC-6 Q10 is answered by code at d2f49d8b: CAM-2 refuses through the same 503 {code LLM_UNAVAILABLE} at identify; C1-4 keys on that answer. The relay may close Q10.
- RC-7 Class FOCUS, two adversaries after GREEN (gate Q9): correctness (every server answer and flag mix) and words / RTL (the strings, the AR plurals, the P1 golden).
- RC-8 For the relay (non-blocking for RED): Q1 the read-only proof read (the comparisons row and search_logs.duration_ms, threshold 35,000 ms); Q6 are INC-C1a's bytes already on the phones; Q15 is ENABLE_FIELD_STATUS_METADATA off on web (F8 precondition).
