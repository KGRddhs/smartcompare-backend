# Native Arabic review list, session 75 (2026-10-09)

Owner action (Ahmed or a native reviewer), before the production build. Each entry names the string, where it ships, the tag of its source and what a change must re-pin. The session-74 CLIENT-TRUTH list (33 strings + 4 push bodies) is in the PR #334 body on GitHub (it was not copied into the repo); this file holds what session 75 added.

## U3b: the AI-consent sheet disclosure sentence (ruling UB-R15; tag [SPEC], not natively reviewed)

- **Key:** `aiConsent.body` in `SmartCompareApp/src/i18n/ar.json` (the ONE new sentence, inserted before the final sentence of the existing body). Shipped to phones by the next OTA / store build that carries U3b (gated by UB-R4: not before PR #330 is live).
- **AR sentence:** وقد تستخدم OpenAI هذه المدخلات والمخرجات التي تنتجها منها للتعرف على أنماط الاستخدام وقياس جودة النماذج والاستعانة بها في تقييم نماذجها وتدريبها.
- **EN twin (`en.json` `aiConsent.body`):** OpenAI may use these inputs and the outputs it generates from them to identify usage patterns, measure model quality and inform the evaluation and training of its models.
- **Meaning that must survive:** OpenAI MAY use the inputs and the outputs it generates to identify usage patterns, measure model quality and inform the evaluation and training of its models (decision D3 = C: organisation data sharing ON, no per-user opt-out). Western digits only; the brand OpenAI in Latin letters; no scary vocabulary (`.copy-policy.json`).
- **If the reviewer changes a word:** the fence sha256 of the EN + AR copy (`372c50484085fa859a576a62367c743365735fab6dda31f336552a4ae2a21a02`, pinned by `__tests__/consent/aiConsentV2.s75.test.ts`) AND the V4 fence constant move in ONE edit, and `AI_CONSENT_VERSION` stays 2 (the sentence meaning is unchanged; a meaning change would bump it to 3 and re-ask every user). Follow-up unit, not a hotfix.

## Removed AR keys (for the record, no review needed)

`profile.aiSharing.title`, `profile.aiSharing.subtitle`, `profile.aiSharing.errorSave` (the Profile toggle is gone under D3 = C).

## Follow-ups recorded in the U3b PR body (ruling UY6), copy that a native reviewer should see with it

- The Step 5 onboarding headline and the 'Privacy' eyebrow of the consent sheet (CT2-m2): LISTING-TRUTH / native review.
- The privacy data inventory purposes and the stale row-12 `api.ts` anchors (CT2-m4 + n2): LISTING-TRUTH docs.
