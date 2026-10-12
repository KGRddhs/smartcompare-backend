# Orchestrator rulings: unit S77 LEGAL-DISCLOSURE (spec 5b7e5be9..., spec review APPROVE_WITH_RULINGS)

Orchestrator: Opus 5.5. 2026-10-12. BINDING; supersede the spec where they differ. The spec reviewer's full rulings text: notes/legal_spec_review_rulings.txt (scratchpad).

- RL1 (= R1) Keep "October 11, 2026" and all twelve anchors. PR body records: the literal s15/s14 deviation; API last_updated stays 2026-10-11; the 2026-10-11 text is archived at git 10135306; the FIRST post-release change bumps every anchor incl. consent.ts TERMS_VERSION and publishes the prior version.
- RL2 (= R2) ADOPT the privacy s5 own-terms sentence: EN "Retailer websites (section 6), the sign-in providers Apple and Google, and Google as our mailbox provider act under their own terms." and the reviewer's AR twin (replace fix3_ar.s5_own_terms); move S5_OWN_TERMS_EN (tests/test_legal_docs_u8_d3c.py) and the fixture key.
- RL3 (= R3) ADOPT privacy s7 "(OpenAI)" -> "(OpenAI and Google)" with the AR twin (plain text outside HOSTING_REGIONS; live + snapshot); measure it.
- RL4 (= R4) Add landing/README.md:43 to the doc edits.
- RL5 (= R5) Expect the real fill-in run to re-render the four legal landing regions; the renderer step is --check only.
- RL6 (= R6) Keep T4 exactly as specified (pure accuracy fix).
- RL7 (= R7) Licence extension for OpenAI's own training use is OUT of this unit (needs an owner yes); record the s8 tension in the PR body as limit L3.
- RL8 (= R8) No "5 working days" promise.
- RL9 (= R9) The consent sheet free-use sentence (AI_CONSENT_VERSION 3) goes in the post-approval OTA with M6; record L1 in the PR body.
- RL10 (= R10, alternative wording) P2 (privacy s2) and T8 (terms s8) use the GENERAL promise: EN "Apart from OpenAI's data-sharing programme described below, we do not sell or otherwise exchange your personal data for anything of value, and we do not share it with data brokers or advertisers." followed by the spec's OpenAI disclosure sentence(s) (training use + some free use in return). Write the AR twin in the existing terminology. It must pass the d3c (k) scan and the D4 / UG12 pins (aggregated or anonymised statistics are not personal data and stay permitted); if a pin conflicts, report it before changing any pin.
- RL11 (= R11) ADOPT: privacy s8 retention gains "Email you send to our addresses: kept in our mailbox until we delete it; no fixed period." (+ AR); privacy s3.2 "Feedback and messages" also covers email sent to support@ / privacy@ (+ AR). Live + snapshot.
- RL12 (= R12) Gate set as spec section 7; the three landing jest suites run in the PR's CI frontend job (the orchestrator checks it before merge); D8/D9 mirror them.
- RL13 RED must fail for the right reason: every new D-node either fails because the new text is absent / the old text is present, or is a pin passing at base. No collection errors.
