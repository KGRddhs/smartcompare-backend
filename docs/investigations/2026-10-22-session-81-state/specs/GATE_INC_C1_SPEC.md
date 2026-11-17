# GATE INC-C1 SPEC (S96 orchestrator, 2026-11-17 about 06:35 AST): spec draft ACCEPTED with rulings; the build WAITS for the relay's word after INC-SEC-1

The draft is wf_48c7a0c7-f18: two Opus 5.5 agents, 614k tokens. It is c1/INC_C1_UNIT_SPEC_DRAFT.md, at origin/main 5cd93c6a. No client byte has changed since #412, and the #416 merge moved no client file. The review is c1/INC_C1_SPEC_REVIEW.md, verdict AMEND: 1 MAJOR, 12 MINOR.

## The Hold-on cause (the relay's 02:50 question 6)
LIKELY, independently confirmed by the reviewer:
- The phone's own 35 s request deadline (COMPARE_TIMEOUT_MS, api.ts:56) expires before the capped success:true partial arrives.
- The 30 s cap is armed only after the route's pre-work (SCS:4296). The cancel tail, the persist and the network come on top.
- The client draws "Hold on" only for a parsed TIMEOUT: a TIMEOUT body, a codeless 503, or no response at all. The server sent none of those; the quoted log line is printed just before `return partial`.
- The alternative is a dropped network.
- Phones never stream: ENABLE_EXPO_FETCH_SSE_DEFAULT is false.
- On the server side, the credit is kept and the row is saved to History, though the phone never got it.
- **ESTABLISHED** only if a read-only proof read shows search_logs.duration_ms >= 35,000 for that request. 31,000-35,000 stays LIKELY. The proof read is the comparisons row 23:27-23:29Z plus search_logs, and the relay's to take.

## Scope (rulings)
**IN, the core:**
- C1-1: the deadline, 35 s -> 50 s, plus an honest partial note. It absorbs T7-10.
- C1-2: price_asof and "Last checked ...".
- C1-4: the honest camera message, keyed on the server's answer, 503 LLM_UNAVAILABLE at identify. It is never keyed on the native version, because 1.0.1 runs before the vision flip. It makes no time promise.
- T7-04: link wording per refusal code, including STORE_UNREADABLE and UNRESOLVED_PRODUCT. This answers addendum A-4 and A-5.
- T7-08: the converted label printed once.

**OUT:**
- C1-3, the size beside the price: DROPPED, because #412 already draws size_ml and INC-P2 owns the size contract.
- T7-09 and T7-11 go to INC-C1b, a client-only follow-up.
- The INC-R1 picker is its own later unit.

**ADDENDUM A-1..A-3:** the screenshot defects (Volume "100" vs "100 ml"; "107 reviews" vs 16,000; a con about our data) were not researched; the draft began before the message. The amend round before RED classifies each as IN (client rendering) or a SERVER DEPENDENCY named for the owning lane. A-2 and A-3 are LIKELY server (model text).

## Rulings on the review
- **F1 MAJOR, accepted.** Every RED row observes only through surfaces that exist at base: ResultsContent / ResultsScreen renders, and HomeScreen with a mocked navigation whose popTo is a jest.fn. Type mode is asserted through its testID after a focus event, and a second focus must not re-apply it. No RED import of a new symbol and no jest.mock of a new path. tsc stays at 0 errors at base.
- **F2, accepted.** H3 drives the real streamComparison with jest.requireActual; only the axios instance is mocked.
- **F3, accepted.** D4 uses now 23:58 local, as_of 00:02 the next day.
- **F4, accepted.** as_of is built from local Date parts, or TZ is pinned in the test.
- **F5, accepted.** A positive control: each key exists, non-empty, in both catalogs.
- **F6, accepted.** One table holds every new AR string literally, each marked [NATIVE READ].
- **F7, accepted.** The threshold is 35,000.
- **F8, accepted.** P1 precondition: ENABLE_FIELD_STATUS_METADATA is off on web. The relay reads the flag list. Stated limit.
- **F9, accepted.** Neutral words for STORE_UNREADABLE: "This shop's page did not open for us. You can type the two names instead." It covers transport errors, the redirect cap and non-2xx, in plural-safe wording. The words are the owner's read.
- **F10, accepted.** L7 says typing is also refused for an account under consent 3.
- **F11, accepted.** Added to the backend fence list: test_s81_sf1_gate_rows.py, test_s81_sf1_surfaces_be.py, test_timeout_partial_integration.py.
- **F12, accepted.** Fix the cites, and update the two bundle-file comments that say "35 s".
- **F13.** The engine empty state gets TWO buttons: "Type the names" (primary) and Back (secondary, testID results-empty-back). The header back stays as it is.

## Rulings on the open questions
- **Q1:** a relay question (the read-only proof read).
- **Q2:** 50 s. A lost result costs the user a kept credit, so a longer wait is the better failure. SD-H2: keep the server cap at 30 s or below.
- **Q3:** "did not arrive in time". It is true on REST, where the body is final.
- **Q4:** one wording, "Last checked ...", replaces both the fresh and the stale lines (the owner's wording).
- **Q5:** keep the unused asOf / lastSeen keys, so the pins do not move.
- **Q6:** a relay question (are INC-C1a's bytes already on the phones?).
- **Q7:** yes, the moved pin. Re-record BASE_I18N_KEY_COUNT and its name-set sha, following the CC-8 precedent.
- **Q8:** popTo('Main') plus the one-shot intent module (the spec's plan), so types.ts and linking.ts do not move.
- **Q9:** FOCUS, with two adversaries:
  - correctness: every server answer and the flag mixes;
  - words and RTL: the P1 golden.

  The deadline change touches every compare, and the dated wording is price truth.
- **Q10:** a relay question for the camera lane (CAM-2).
