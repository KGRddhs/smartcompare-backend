# Orchestrator RED gate: unit S77 LEGAL-DISCLOSURE (2026-10-12 ~00:57)

RED files: tests/test_legal_disclosure_s77.py (sha256 9f22d383..., 27 nodes, ASCII) + tests/fixtures/legal_disclosure_s77.json (sha256 fbe6ecd3...). Orchestrator re-run: [pyt] tag=legal-redgate 9 s FAIL rc=1 -> 25 failed, 2 passed. Only the two new files are untracked. GATE: APPROVED.

Answers (binding for GREEN):
- LG1 RL10 composition CONFIRMED as pinned: EN P2 = GENERAL_EN + " " + the spec's second P2 sentence; EN T8 tail = "; none of it identifies you. " + GENERAL_EN + " " + the spec's T8 disclosure sentence; AR disclosure sentences verbatim from the spec.
- LG2 The AR general promise pinned by structure (OpenAI named in the same sentence as data brokers and advertisers as the exception) is ACCEPTED.
- LG3 The AR general promise must NOT use the literal sh-r-k "data-sharing programme" wording in the same clause as data brokers / advertisers (it trips the d3c (k) scan). Use the RED prototype wording ("except OpenAI's programme described below, ..." form, no musharaka) - it passes (k) and all 27 nodes.
- LG4 AUTHORISED: move the d3c (i)/(j) pins PRIVACY_NOT_SOLD_EN and the fixture keys ug12_ar.privacy_not_sold / privacy_s2 / terms_derived to the NEW general-promise text. Move, never delete: each moved pin must still assert that a not-sold promise is present in the same section, and must fail if the promise is removed (prove with one mutant).
- LG5 RL11 word choices ACCEPTED as pinned.
- LG6 RL3 AR pin ACCEPTED.
- LG7 landing/README.md line 43 wording: "how MYEZ looks up prices, that its site-discovery crawler QarenBot follows robots.txt, and the support address"; D16 stays as pinned.
- LG8 D7 "gmail row directly after cloudflare" KEPT.
- LG9 Jest runs in the PR's CI frontend job; the orchestrator checks it before merge.
