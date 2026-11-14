# S95 first report: the consent re-ask and the logo (2026-11-14 18:22 local = 15:22 UTC)

Main lane S95 (Claude Opus 5.5, session local_e38902f4). Read-only diagnosis of main 731bcddf531a7e123963246168ca19f262859337 by git plumbing. Plan meter at the read: 80 pct all models, 86 pct Fable (reset 2026-11-18 13:00 UTC).

## 1. The consent re-ask: the code is not the cause

### What the code does (main 731bcddf; no client file changed between ea47cbfb, the second update, and 731bcddf: `git diff --name-only ea47cbfb 731bcddf -- SmartCompareApp` is empty)

- `SmartCompareApp/src/services/aiConsent.ts:58` `AI_CONSENT_VERSION = 3`.
- `aiConsent.ts:96` `hasCurrentAiConsent` is true ONLY for a stored record whose version is exactly 3. A record of version 1 or 2, an unreadable record or no record reads false.
- `aiConsent.ts:183-184` `ensureAiConsent`: a false answer shows the sheet (`ask()`); an Agree is stored as version 3 before the compare runs.
- Every compare starts on Home through `withAiConsent`: text `HomeScreen.tsx:421` (reached from the shell's Compare button `:975` and the popular-pair tap `:740`), link `:585`, camera `:825`, `:831`, `:836`, `:893`. No other screen dispatches a compare (no other caller of `streamComparison`, `compareTextPair` or the identify upload).
- The header: `requestContext.ts:124` reads the same per-account record (memo dropped on every Agree), `:146` sets `X-AI-Consent-Version: 3`. The SSE stream (`api.ts:875`), the REST fallback (`api.ts:751`), the link compare (`HomeScreen.tsx:631`) and the camera upload (`api.ts:312`) all carry it.
- The server reads only the header: `app/services/llm_router.py:350-351` (3 or more goes to Claude); nothing per account, no stored consent row. `ENABLE_CONSENT_PERSIST` stores the Terms fields at sign-up only (the comment at `aiConsent.ts:10-13`).

So on the second update an account whose stored record is version 2 IS asked on its first compare, and after Agree it sends 3.

### Why the old account sent no 3 at 01:36 UTC on 2026-11-13

- `SmartCompareApp/app.json:275-277` sets only `updates.url`: expo-updates runs with its defaults (check on load, no wait). An update is DOWNLOADED during one launch and RUN only at the NEXT cold start.
- On the first update (group 08de6433, consent 2) the stored version-2 record is current, so that bundle shows no sheet and sends `X-AI-Consent-Version: 2`. With ENABLE_OPENAI_PRE_V3 on and the egress stop on, the server takes the old path and stops the OpenAI calls: exactly the 01:36 log lines (EXTRACT_SYNTH, EXTRACT_TARGETED, moderation: "openai dispatch stopped locally").
- The new account got Claude at 01:42, so by then the phone ran the second update: the app was restarted in between (a swipe-away, or iOS ending it while the owner was outside the app during sign-up).
- The testing plan already states the rule: "On the phone, after two launches, the consent sheet shows v3" (TESTING_PHASE_PLAN_2026-11-11.md:109).

## 2. The proof (either one)

- **A, the owner (the decisive one):** sign in to the OLD account and run one compare. The phone runs the second update now (the 2026-11-13 21:19 UTC compare on the new account ran on Claude). Expected: the version 3 sheet naming Anthropic and OpenAI appears; Agree; the result has AI text. If NO sheet appears, report it at once: then something the code does not show is wrong and this lane digs further.
- **B, the relay, read-only:** Sentry, the `comparison_wall_time` info events of 2026-11-13 near 01:36 and 01:42 UTC, field `contexts.ota_updates.update_id` (and `is_embedded_launch`). @sentry/react-native 7.2.0 adds that context to every event (default `expoContextIntegration`; the app's scrubber does not touch `contexts`). First update iOS id `01a1b620-93b8-72e1-b1b5-52499248020a`; second update iOS id `01a1ce66-2530-7898-bfef-f3782ec9daf3`.

## 3. What follows for unit 1

- No code change is needed for the re-ask: the second update already re-asks every account below 3 once.
- The lasting rule: after EVERY update (the third one too) a phone runs the new bundle only from the second cold start (open the app, swipe it away, open it again). Judge an update only after that.
- Optional later unit, not started, the owner's call: apply a downloaded update at the next launch while the splash is up (bounded wait, no loop), so a fix shows on the first reopen. It helps only the updates after the one that carries it.

## 4. The logo over the result page: found

- `SmartCompareApp/src/components/results/ResultsContent.tsx:536-548` mounts the winner-reveal celebration `RevealBurst` (size 220) in an absolute-fill slot (`revealBurstSlot`, styles `:872-880`) over the score bars, once the winner is revealed in normal mode, and never unmounts it.
- `SmartCompareApp/src/components/hero/RevealBurst.tsx`: the six particles fade out (`:156`), but the badge, a 112 px circle (`BADGE_R = 56`, `:71`) holding the MYEZ mark (`:243`), only scales from 0 to 1 (`:200`) and never fades. So the MYEZ badge stays over the bars for the life of the screen and scrolls with the page.
- Fix: remove the RevealBurst mount from the result page (ResultsContent plus its tests). It ships in the third update with nothing else (no client change since the second update).
