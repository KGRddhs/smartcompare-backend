# RULINGS_S81_12D (orchestrator S93-FIX, Claude Fable 5.2, 2026-11-12): the rulings on specs/S81-12d_UNIT_SPEC.md and specs/S81-12d_SPEC_REVIEW.md. Binding on the RED round and on every round after it

Precedence: this file, then the review, then the spec, then the brief (specs/S81_12D_BRIEF.md) where they differ. Hashes of record (the working-copy bytes as filed by S92-FIX): the spec 01e9dc32e9ea01dd66ca80e01131bb82d819b2a2adaaf2778e8afd1cabb283c8, the review b5784db1dc5e15274968547373d4a81b1458ad99058998313c1b5268e0c0ebd6. Base: origin/main 6b909e0a92067d6b3562eee325e4956c116441f7 (re-measured 2026-11-12 05:20; PR #378 not merged).

## A. Verdict

APPROVED WITH THE CHANGES BELOW. The design stands as specified: ONE dark flag ENABLE_OPENAI_EGRESS_STOP read per call, ONE new typed refusal OpenAIEgressStoppedError (a subclass of LLMUnavailableError), FOUR hooks (H1 the chat chokepoint, H2 the moderation arm, H3 and H4 the two operator scripts), no arm, router, route, client or legal file edited. The orchestrator re-checked the census independently at the base (git grep for every OpenAI host literal and for tiktoken, litellm and langchain under app/, scripts/ and the requirements): it agrees with the spec's section 1.4, with one addition (ruling G-3).

## B. The owner's choice of legal text, and what it changes here

The owner's words, relayed verbatim by the relay on 2026-11-12 about 05:10: "C: this week". The question it answers: "Which text should the new privacy policy publish with? C. Publish this week. Today's OpenAI wording stays and Anthropic is added. OpenAI is removed from the texts the week after. B. Wait until about Tuesday. Publish with OpenAI already removed."

- B-1 This unit is NOT needed before the legal window (PR #378). Wherever the brief, the spec or the review says "under path B the first step of the legal window", read: "its own window after the legal window, on the owner's yes". The day the flag goes ON on the web service is the date the LATER text (OpenAI removed, S81-12b) may carry.
- B-2 THE LANE ORDER (the orchestrator's ruling, sent to the relay). Today, on base 6b909e0a, in this lane's one slot: S81-12d through RED, the gate, GREEN, two adversaries and its fix rounds. After the relay sends the #378 merge sha: the final rounds in the order G-INC-1, then S81-12d, then MON1, each replayed onto the main of that moment, each PR and merge in the same order on the relay's "merge window open". INC-X1's RED comes after them. Reasons: G-INC-1 carries the first change the owner can see on the phone (INC-X9) and has no open ruling; S81-12d before MON1 keeps the contract of section 2.9 inside MON1's own files (merge order "S81-12d FIRST"), and MON1 also waits for the owner's O2 / O3.

## C. The spec's open questions

- C-1 (OQ-1) Part B stays IN: H3 and H4 are built, with rows S12D-18, -19, -20 and mutants M20, M21. Reason: the census is the claim; two statements close its last two dispatch statements.
- C-2 (OQ-2) The NEW subclass is approved (not the bare LLMUnavailableError): the deploy log and MON1 can tell a stop from a breaker or spend denial by type name.
- C-3 (OQ-3) The stop is host-blind (stated limit L5 stands). The flag means "no request through the OpenAI SDK".
- C-4 (OQ-4) Proof step P2 reads: "the screen stays the engine-unavailable state", with the backing of correction D-3. A device read of the camera before the flip is optional.
- C-5 (OQ-5, with the review's K2 and question 2) THE UNIT IS BUILT AS SPECIFIED: the stop is a typed refusal in every configuration; row S12D-09 stays. In addition:
  - C-5a THE FLIP-ORDER RULE goes into the CLAUDE.md block and the owner steps as the rule of record until a later unit changes it: "While ENABLE_OPENAI_EGRESS_STOP is ON and any ENABLE_ANTHROPIC_* role flag is ON, ENABLE_OPENAI_PRE_V3 must be OFF. With both ON, a text compare from a client below consent version 3 runs the whole scrape and then answers the coded LLM_UNAVAILABLE (no byte to OpenAI, but search spend and no delivery); with ENABLE_OPENAI_PRE_V3 OFF the entry refuses before any provider work." Stated limit L1 is re-worded to say exactly this (the review's K2: on the day of the first role flip every installed client is below consent 3, measured: AI_CONSENT_VERSION = 2 at 683f56c0 and f1e20c39).
  - C-5b A NEW RED ROW E10 pins the forbidden configuration end to end, so that the no-byte claim holds in EVERY configuration: ENABLE_ANTHROPIC_TEXT and ENABLE_ANTHROPIC_VERDICT ON, no consent version in the request, ENABLE_OPENAI_PRE_V3 ON, the stop ON, one text compare: ZERO OpenAI requests; the answer is the coded LLM_UNAVAILABLE envelope with the refund of the existing path (status, code and refund label measured on the in-place prototype and frozen). RED at base (requests leave).
  - C-5c THE OWNER'S QUESTION (section H) does not block the RED: every answer keeps this unit's bytes. Answer 1 becomes a follow-up unit (working id S81-12e) that changes what the role-ON arms do with this one class, ruled with the main lane because those arms are the consent router's contract.
- C-6 (OQ-6) The K1 re-pin is an E-row of this unit's PR body (E1), measured on the GREEN bytes.

## D. The review's corrections (C1-C11) and refuted claims (RF1-RF6)

- D-1 (C1, RF1; REQUIRED) The owner steps of 8.2 / 8.3 are replaced by section F below. The legal date rests on the WEB service (the only service that reaches OpenAI today); the price-warmer is covered by a standing precondition on its own flip, not by a variable typed onto a deployment that may not contain this unit.
- D-2 (C2; REQUIRED; the review's question 5: YES, the frozen literal set of E08 may grow) The FULL configuration of section 5 gains: OPENAI_MAX_RETRIES and OPENAI_FALLBACK_MAX_RETRIES at non-default values (the OFF rows then pin ONE 401 request and no SDK retry); OPENAI_BASE_URL set explicitly to the stock URL as one parameter of S12D-12; the LLM_SPEND_* knobs and LLM_BREAKER_CACHE_TTL at non-default values; ENABLE_VISION_IDENTITY_V2 ON as a parameter of E04 and of the vision rows of S12D-14; ENABLE_URL_MODE_V2 ON as a parameter of E05; ENABLE_FULL_STREAM_DEADLINE ON as a parameter of E03. Each added parameter freezes its own OFF base literal in E08. Parameters are added row by row as listed, never as a cross product.
- D-3 (C3, RF2) P2's backing: "503 (today 500) in Railway's HTTP log for POST /api/v1/image/identify; in the deploy log the WARNING '[IMAGE] Vision call failed: OpenAIEgressStoppedError' (today an ERROR with the 401 text)". The app writes no access line.
- D-4 (C4, RF3) P1: the once-per-process stop lines are checked SINCE THE DEPLOYMENT STARTED; the per-call markers for the owner's minutes are the arms' "<prefix>: OpenAIEgressStoppedError" WARNINGs and the moderation WARNING carrying the constant, beside ZERO "HTTP Request: POST" lines to the OpenAI host.
- D-5 (C5) 8b cites the detector (httpx2 logs each request at INFO; logging_config does not quiet httpx2) and says the zero-lines check means something only while the log level is INFO. THE POSITIVE CONTROL IS REQUIRED, not optional: one text comparison just BEFORE the flip, whose deploy-log lines show the 401 request lines; without it the after-read proves nothing.
- D-6 (C6) The census row S12D-20 excludes Anthropic calls by the callee chain (a ".messages." segment), never by a receiver name.
- D-7 (C7; RF4, RF5, RF6) Wording. 2.7: the flag-OFF runtime difference is one os.getenv per dispatch attempt, one call frame per hook and, in H2 / H3 / H4, one inline import statement. L3: the latch is NOT locked and stays so (the add precedes the log line and nothing awaits between the membership test and the add, so on an event loop it cannot log twice; only a caller on several OS threads could log one extra line per surface, and no such caller exists at the base). No lock is added: its effect could not be pinned by a deterministic row. The path of the client file is SmartCompareApp/src/services/failureClassification.ts.
- D-8 (C8) E1 keeps the file's existing construction (concatenated fragments); the GREEN agent checks every fragment of the new literal for a run of eight digits and splits differently if one appears.
- D-9 (C9) The placement of H4 before or after the store write is an EQUIVALENT SURVIVOR by ruling (both raise before any create); it is listed in the mutation report, not counted as a gap.
- D-10 (C10) The pointer sentence in the Feature Flags clause is anchored directly after the newest S81 pointer sentence at the then-main (at the base: the S81-04c sentence), never "after its newest sentence" of the whole paragraph.
- D-11 (C11) P4 (the saved rows keep zero OpenAI calls and zero cost) is labelled a NON-REGRESSION read, not evidence of the stop.
- D-12 The review's pin note stands: the census-comment line of 3.1 must not contain the literal "moderations.create".

## E. Contract risks

- E-1 (K1) None for the response contract: confirmed.
- E-2 (K2) Ruled in C-5.
- E-3 (K3) The dated line and every text built on it say "our services stopped sending requests to OpenAI", never "the code": the two operator scripts stop only where the flag is set in the operator's shell (L7).

## F. Owner steps (they replace 8.2's last bullet and 8.3; names only; nobody but the owner decides; the relay acts on the owner's yes)

0. Before the flip: the relay confirms, read-only, that the running WEB deployment's commit contains the S81-12d merge.
1. The positive control (D-5): one text comparison just before the flip; the relay reads the 401 request lines in the deploy log.
2. ENABLE_OPENAI_EGRESS_STOP is set ON on the web service by the relay on the owner's yes, in its own window (a variable change redeploys web; no other proof runs in that window).
3. The proof of 8b as corrected (D-3, D-4, D-5, D-11).
4. The dated ledger line: the service name, its deployment commit, the time, "ON". That date is the one a legal text may carry for "our services stopped sending requests to OpenAI".
5. The price-warmer: the same variable may be set there in the same window, and the line then records that service's deployment commit. STANDING PRECONDITION, added to the ENABLE_PRICE_CACHE_WARMER flip's window: the warmer is not switched on until the price-warmer deployment contains the S81-12d merge AND the stop is set there (a merge to main does not redeploy that service; a variable on an older deployment does nothing).
6. The flip-order rule of C-5a.

## G. Additions by the orchestrator

- G-1 STATED LIMIT L9 (moderation): with the stop ON the OpenAI moderation call is not made and the arm fails OPEN, exactly as today on the rejected credential. AI text is therefore unmoderated by a provider until the Claude moderation role is ON (the main lane's window 14). The stop does not make this worse than today; the PR body says it in words.
- G-2 THE COMM SET stays the whole free tier at RED (the base record at 6b909e0a) and at GREEN (measured from the S92-FIX runner ledger: one whole-tree pass costs 20 to 25 minutes of the box's one pytest slot). At the final rounds a head record whose tree equals the then-main's tree (git rev-parse of both ^{tree}) IS that main's base record: no second whole-tree pass for the next unit.
- G-3 STATED LIMIT L10 and one census assertion: scripts/audit_exemplar_token_cost.py imports tiktoken, which can download a public encoding file from an OpenAI-operated host on first use. It is operator-run only, sends no user content and is not an API request: outside the stop. The census row S12D-20 ALSO asserts that no module under app/ imports tiktoken (true at the base), so the claim cannot rot silently.
- G-4 Row count after these rulings: 24 RED rows (the spec's 23 + E10) and 6 PIN rows in the two files of the spec; names, tags and the branch as R-12D-11.
- G-5 THE MON1 CONTRACT (2.9) under the ruled order "S81-12d FIRST" becomes addition M-5 of MON1's final round: (a) a row pins that MON1's classifier returns None for OpenAIEgressStoppedError; (b) the first statement of MON1's OpenAI probe leg skips while api_budget_service.openai_egress_stop_enabled() is true, with a transport-recorder row of zero OpenAI requests per tick; (c) MON1's in-use predicate for OpenAI is false while the stop is ON. MON1 reads the predicate by module attribute, never by a copied name. This unit's files do not change for it.

## H. The owner's question (sent to the relay 2026-11-12; it is the same decision as the main lane's open owner call on ENABLE_OPENAI_PRE_V3, "item 10": ask it once)

In plain words: "After Claude is on, what should a phone get that has not yet accepted the new privacy terms? (1) Today's result without AI text, with nothing sent to OpenAI: one more small build, about a day. (2) The 'AI engine unavailable' message until it accepts the new terms: no extra build. (3) Today's result, but its requests keep going to OpenAI, which refuses them, until most phones have updated: no extra build, and 'nothing goes to OpenAI' becomes true only after that."

The orchestrator's recommendation: (1). Reasons: every new install starts on the store binary's built-in consent version 2 and takes the new consent only after its second cold launch, so until 1.0.1 is live every new user's FIRST session is such a phone; (2) shows that session an error on its first comparison; (3) keeps sending to OpenAI, so the text "OpenAI removed" the owner wants the week after could not be true until 1.0.1 forces the update. Only (1) gives both. The reviewer recommended the rule of (2) for its zero code; the main lane's ruling C3 (b) of RULINGS_CLAUDE_PATH called the delivery of (2) "worse than today's result".

Until the answer: the unit is built as specified, the flip-order rule C-5a is the rule of record, and the stop may be switched on at any time BEFORE the first Claude role flip with no visible change on any phone.

## I. Procedure notes for the RED round (they amend spec sections 5, 6 and 7 where they differ)

- I-1 The prototype and every mutant live in the RED agent's OWN detached scratch worktree (the standing procedure). The spec's "in place on byte copies, no scratch worktree" sentence is superseded: no tracked file of the real worktree sc-inc-12d is ever modified by the RED round; it only ADDS the two test files.
- I-2 The base comm record is the whole free tier at 6b909e0a (every tests/test_*.py minus the four test_precommit_hook*.py files), chunks of at most 25 files, one at a time, stored once (LC-6) under harness/base_records/6b909e0a92067d6b3562eee325e4956c116441f7/ with the set's sha256 as the file stem (.files, .header.txt, .txt = the sorted FAILED and ERROR node ids). A chunk that times out is split in two and re-run once.
- I-3 The CI-order set of 7.3 runs at base in both stated orders: the failing node-id set of the two RED files must equal the set of the alone run (AssertionError only) and every PIN row must be green in both orders; it runs again on the prototype with the flag ON and OFF (all green). Every row deletes or sets EVERY environment variable its subject reads (the S92-FIX lesson: another test file can set one at collection time).
- I-4 One mutant is added: M25 "an app module gains `import tiktoken`", killed by S12D-20 (ruling G-3). Mutants run only their killing rows (-k); a survivor is reported with its diff, never deleted from the table.
- I-5 Frozen base literals (E08 and the parameters of D-2) are built from the base measurement by the RED agent; a literal with a run of eight digits or more is split or built at run time (the added-line sweep).
- I-6 The gates B1, B2, B3 and B4 of spec 1.10 run at base as four runner calls with the file lists as written there (not file by file); B5 is the RED files; B6 is I-2.
