# Qaren ToS Fact Base — Analysis Design

**Date:** 2026-05-06
**Status:** Approved by Ahmed (2026-05-06)
**Owner:** Claude (main session, Opus 4.7)

---

## 1. Goal

Produce a single self-contained markdown document that answers all 365 sub-questions in `c:\Users\SynAckITPC\Downloads\qaren_ai_tos_questions_english.md` with file/line evidence drawn from the Qaren codebase, ready to be handed to a downstream AI document drafter that will produce the final Terms of Service and Privacy Policy for App Store / Google Play submission.

## 2. Deliverable

**Path:** `c:\Users\SynAckITPC\Downloads\qaren_ai_tos_answers_english.md`

**Format (top to bottom):**

1. **AI DRAFTER INSTRUCTIONS** — preamble with hard rules:
   - Must read **DECISIONS REQUIRED** block before drafting.
   - If any item is "Undecided", first reply must list those items and ask the user to fill them in. Must not proceed to draft. Must not invent placeholders.
   - If user says "just go", repeat the request rather than proceed. Reason: doc may be forwarded by a non-author who would not catch missing decisions.
   - Format guide: how to read per-question entries, what compliance tags mean, where pre-filled store-form sections live.
2. **DECISIONS REQUIRED** — consolidated block of every "Undecided" item across all 22 sections (legal entity name, official support email, official privacy email, official address, commercial registration #, ToS effective date, response SLA for privacy requests, etc.). Numbered. Inline answers reference these by number.
3. **22 question sections**, mirroring the input file 1:1. Each entry has: answer, evidence (file:line + tiny snippet), retention semantics where applicable, third-party transfer info where applicable, compliance tags.
4. **APPLE PRIVACY NUTRITION LABELS** — pre-filled form fields ready to paste into App Store Connect.
5. **GOOGLE PLAY DATA SAFETY FORM** — pre-filled form fields ready to paste into Play Console.
6. **CROSS-BORDER DATA TRANSFER MAP** — table of third party × data fields × hosting country.
7. **DRAFTER: EXTRA-CARE FLAGS** — high-risk areas the drafter must not gloss over (AI-recommendation disclaimer, supplements/health adjacency, cross-border transfer language, beta/MVP status).

## 3. Constraints

- **No fabricated values.** Strict "Undecided" markers — never propose default legal entity, address, email, or any identifying info. (See `feedback_no_fabricated_legal_identifiers.md`.)
- **No legal interpretation.** PDPL articles cited factually (article number + brief topic) without commentary on compliance.
- **Bahrain-only at launch.** GCC framed as future expansion. Governing law: Bahrain.
- **No invention.** Every claim must have a `file:line` source or be marked "Undecided" / "Not available".
- **AI drafter is downstream.** This doc is a fact base, not a draft of the actual ToS or Privacy Policy.

## 4. Methodology — 4 parallel forensic agents → main synthesis

| Agent | Model | Scope | Reads |
|-------|-------|-------|-------|
| **A. Backend forensics** | **Opus** | Every route, service, third-party API call, every piece of data sent to OpenAI / Serper / Sentry / Firecrawl / Scrape.do / Supabase / Upstash. Trace data-flow end-to-end. | `app/api/*.py`, `app/services/*.py`, `app/middleware/*.py`, `app/main.py`, `app/utils/*.py` |
| **B. Frontend forensics** | **Sonnet** | Every screen, every permission, every storage write (SecureStore vs AsyncStorage), every user-input field, every analytics call, every SDK in `package.json`. | `SmartCompareApp/src/screens/*`, `SmartCompareApp/src/services/*`, `SmartCompareApp/App.tsx`, `app.json`, `package.json` |
| **C. Database + infra** | **Sonnet** | Every table from migrations 001-017, every RLS policy, every column, retention semantics, hosting regions (Supabase / Railway / Upstash / OpenAI), security posture. | `migrations/*.sql`, deployment-config docs, env-var inventory |
| **D. Existing legal + store-config audit** | **Sonnet** | Read current `app/legal/privacy_policy.md` + `terms_of_service.md` and flag what's stale vs current code. Audit `app.json` iOS/Android config. Audit each `package.json` dep for SDK behavior. | `app/legal/*.md`, `app.json`, `package.json`, `requirements.txt` |

Model assignment rationale: data-flow tracing (Agent A) is the highest-stakes legal-accuracy work — what data leaves Bahrain — so Opus. The other three are mostly structured enumeration and benefit from Sonnet's lower cost without accuracy loss when given an explicit checklist.

Each agent produces a **structured fact report** (not the final doc). Main session (Opus) synthesizes all four reports into the deliverable.

## 5. Verification — zero-mistake protocol

Because this is legal material:

1. **Every agent claim must have `file:line` evidence.** Claims without evidence are rejected and the agent re-runs that section.
2. **Main-session cross-validation pass before writing the final doc:**
   - Spot-check 10% of agent claims by reading the cited file.
   - Cross-reference data-flow claims: Agent A's "field X is sent to OpenAI" must reconcile with Agent C's "field X is stored in table Y" — same field names, same shapes.
3. **Five high-risk facts main session personally verifies in code:**
   - (i) Exactly what data appears in OpenAI prompts (verify CLAUDE.md privacy invariant: no raw demographics in prompts).
   - (ii) What data appears in Sentry events post-scrub (verify `before_send` scrubber removes JWT / API keys).
   - (iii) What is logged at all (`logging_config.py` + structured logs).
   - (iv) Every RLS policy claimed in migrations is actually enabled (read migrations 010, 011, 013, 014, 017 line-by-line).
   - (v) `delete_user_cascade()` actually purges everything (read the function definition).
4. **Final read-through:** open the answer doc and the questions file side by side, walk through line by line, confirm every numbered question has an answer.

## 6. PDPL citation strategy

Bahrain Personal Data Protection Law — Legislative Decree No. 30 of 2018. Article numbers used factually, without interpretation:

- **Art. 4** — legitimate basis for processing
- **Art. 5** — sensitive data (health, religion) — requires explicit consent
- **Art. 6** — data subject rights (access, correction, deletion)
- **Art. 11-13** — cross-border data transfer (adequacy or consent)
- **Art. 14** — children / minors
- **Art. 15-19** — data controller obligations (notification, security, records)

Tag format inside answer entries: `[PDPL Art. 4 — legitimate interest, security]`. The drafter AI maps these to actual ToS clauses; we just provide the factual hook.

## 7. Out of scope

- Producing the actual ToS or Privacy Policy text — that is the downstream drafter AI's responsibility.
- Legal advice on compliance, governance, or risk acceptance — beyond Claude's competence and beyond the user's request.
- Marketing-channel disclosures (Meta SDK, ad networks) — none are in code; will be marked "Not available".
- Future features not yet implemented — only `ENABLE_*` flags in code count as tracked state.
- Translating the answer doc to Arabic — English only per the questions file.

## 8. Acceptance criteria

- All 365 sub-questions have an answer (factual, "Undecided", or "Not available").
- Every code-derived claim has a `file:line` reference.
- DECISIONS REQUIRED block at top consolidates every "Undecided" item; no `[CONFIRM]` tags or fake names anywhere.
- Apple Privacy Nutrition Label and Google Play Data Safety form sections are pre-filled from collected data inventory.
- Cross-border data transfer map enumerates every third party that receives any user data with hosting country.
- DRAFTER: EXTRA-CARE FLAGS section explicitly calls out: AI-recommendation disclaimer, supplements/health adjacency, cross-border transfer language, beta/MVP status.
- Final doc lives at `c:\Users\SynAckITPC\Downloads\qaren_ai_tos_answers_english.md`.

## 9. Open questions resolved during brainstorming

| Q | Resolution |
|---|------------|
| Depth of answers | Factual + file:line evidence + pre-filled store-form data + PDPL/GDPR factual flags |
| Output location | Single file at `c:\Users\SynAckITPC\Downloads\qaren_ai_tos_answers_english.md` |
| Handling of undecided business items | Strict "Undecided", consolidated in top DECISIONS REQUIRED block, no proposed defaults |
| Cofounder safety | Drafter AI must verify all decisions are filled before drafting; explicit hard rule in preamble |
| Launch scope | Bahrain at launch, GCC later |
| Compliance lens | Bahrain PDPL (primary, factual citations) + GDPR-equivalent disclosures + Apple Privacy Nutrition Labels + Google Play Data Safety Form |
| Methodology | 4 parallel agents (1 Opus + 3 Sonnet) → main-session synthesis with verification protocol |

## 10. Next step

Invoke `superpowers:writing-plans` to produce the executable plan — concrete agent prompts, file lists per agent, synthesis structure, validation checks.
