# Rulings on the S78-LEGAL spec review (binding, 2026-10-14 ~04:05 AST)

## Inputs

- **Spec:** `sc-s78-legal/.qa-s78/S78_LEGAL_UNIT_SPEC.md`, sha256 `09c349c5…`.
- **Reviews:** `runs/s78_legal_spec_wf_cb452fd6.json`; findings in `runs/s78_spec_review_findings.md`.
- **Verdicts:** legal truth APPROVE_WITH_CHANGES (11), machinery APPROVE_WITH_CHANGES (10).

These rulings amend the spec. Where they conflict, they win. `RULINGS_S78_LEGAL.md` (LR1–LR11) still binds.

## Accepted as proposed (the proposed ruling text in the findings file is the binding text)

**Legal-truth findings**

| ID | Ruling |
|---|---|
| LT1 | ToS s6: drop "specifications" from the third-party-sources sentence, in EN and AR. |
| LT2 | ToS s16 item 4: "Apple will refund the purchase price of the App to you (the App is free, so that amount is zero)". AR: "وستردّ Apple". The developer's sole responsibility applies as between us, you and Apple; our liability to you is subject to sections 11 and 12. R13 gains the marker "will refund". |
| LT3 | AR third-party-beneficiary sentence as proposed. Marker "أطرافًا ثالثة مستفيدة". Add it to the native-review list. |
| LT4 | Privacy s11: "Apart from the reminders described above, we do not use your personal data for direct marketing ...", with the AR as proposed. Adjust R23. |
| LT5 | Drop "before it takes effect". Material changes are told "in the App or on our website when we publish it", in both documents and both languages. Keep the ToS continued-use sentence. Adjust R16 and R23. |
| LT6 | AR s12 carve-outs use the Civil Code vocabulary: "الغش أو الخطأ الجسيم أو الخطأ العمدي". Update the `carveouts_ar` fixture. Add it to the native and counsel lists. |
| LT7 | AR trade-name clause: "، ويعمل باسم {value}". The EN "trading as" stays. Counsel question Q3 covers both languages. If counsel says no, `trade_name` becomes empty, which is a one-value re-fill. |
| LT8 | ToS s16 item 3 gets both halves: we are solely responsible, Apple has no obligation. Item 7 reads "You represent and warrant", AR "تقرّ وتضمن". |
| LT9 | Precedence: "governs your licence to use the App; these Terms govern your use of the MYEZ service provided through it. If they conflict about the service, these Terms apply; otherwise the Standard EULA applies." Use the AR EULA name as proposed. Add to Q4 that the service then falls outside the Standard EULA's USD 50 cap and California law. |
| LT10 | Make the text true. Amend the first sentence to "Except as section 4 describes for OpenAI and as this section describes for our mailbox provider, each of our service providers ...", with an AR twin. If the d3c (n) pin forbids it, change that pin deliberately and list it in the P-list with this reason. Truth wins over a byte pin. |
| LT11 | ToS s8: "before your first comparison or scan", with the AR as proposed. |

**Machinery findings**

| ID | Ruling |
|---|---|
| M1 | HOSTING_REGIONS nonempty text: EN ", as well as in {value}", AR "، وكذلك في {value}". Add a generic node: for every {value} clause, the longest literal of its nonempty text must not occur in the filled documents of that language when the value is empty. `test_polish_f1_empty_hosting_regions_first_fill_is_accepted` must stay rc 0. |
| M3 | The R16 s13 marker is "Section 9 of our Privacy Policy". RED's satisfiability prototype must cover every marker of R13–R16 against the filled text. |
| M4 | R12's role words are exactly the P11 list: database, hosting, temporary / temporary-storage. The vendor list belongs to R10. |
| M5 | Append the new retired AR sentences at the END of `retired_ar`. No existing index changes. |
| M7 | Add the 7 source-scanning files to comm chunk 2. Record `landing.domain.s76.test.ts` L8 in the frontend note. |
| M8 | Rewrite the `_placeholders_comment` sentence in place: the clause names countries only. |
| M9 | The orchestrator fixes CLAUDE.md:17 in the session docs PR. It is not in this unit. |
| M10 | R7 also asserts that PRIVACY_EMAIL occurs inside POSTAL_ADDRESS and POSTAL_ADDRESS_AR whenever the interim form is used. |

## Orchestrator choices

**M2.** Keep the literal address-count pins. GREEN re-measures `ADDRESS_COUNTS` in `landing.brand.s69.test.ts` and `PRIVACY_PAGE_ADDRESSES` in `test_legal_disclosure_s77.py`. Amend L1/R20: the future P.O. Box swap re-measures these two pins, and R20 asserts the expected count delta.
- A test-code edit at swap time is accepted. The worktree cannot run jest, so a derived jest count is a larger unverifiable change.

**M6.** Use only the Latin town digest; the AR documents carried the Latin value. For Arabic script there is no town list. R7 asserts that the AR postal value equals the fixture's `POSTAL_ADDRESS_AR` exactly, which contains no town.

**Q2 (P.O. Box format).** The swap value takes the form "P.O. Box NNNN, Kingdom of Bahrain" with NO town or post-office area name. R2 stays as specified.

**Q9 (scope expansion LR7b).** In the same unit:
- Replace the personal email in the `authors` entry of `pyproject.toml:6` and `backend/pyproject.toml:6` with `support@getmyez.com`. No other key moves, and the lock is untouched.
- Replace the personal-looking address at `tests/test_abuse_detection.py:122` with an `example.com` address that keeps the test's meaning: same domain class, and disposable or not as before.
- Add both files to the R18 denylist scope.

**Other open questions.** Q1, Q3, Q4 and Q5 go to counsel. Q6 is D9, the owner's call. Q7 is a re-date if the merge slips; the orchestrator does it. Q8: the orchestrator verifies the Standard EULA and DSA status in App Store Connect. Q10 is owner actions. All are recorded in the spec's limits and need no code.

## RED phase instructions

- RED writes `tests/test_legal_s78.py` and `tests/fixtures/legal_s78.json` only.
- Every node must fail at base for the stated reason. R8, R19 and R24 are guard pins that pass at base, as the spec says; the M1 generic node may also pass at base.
- Prove satisfiability with a throwaway prototype in the scratchpad: a copy of the six markdowns filled with the spec texts plus these rulings. Every node must pass on the prototype. Never write into the worktree beyond the two RED files.
- No personal value may appear in any file (LR8).
