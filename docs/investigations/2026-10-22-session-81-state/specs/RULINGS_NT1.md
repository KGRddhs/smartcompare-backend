# RULINGS_NT1 (orchestrator Claude Fable 5.2, session 93, 2026-11-12): NT1a NATIVE 1.0.1, the P0 only. PART A is ruled now; PART B holds the two OWNER'S CALLS as forks and is closed by an addendum when the relay files the owner's words. The RED does not launch before PART B is closed

Precedence: these rulings (R-NT1-9..R-NT1-22), then specs/NT1_BRIEF.md (R-NT1-1..8) where a ruling below does not amend it, then the review's corrections C1-C9 where accepted by number, then the spec (sc-s81-nt1/.qa-s80/NT1_UNIT_SPEC.md, sha256 4cfb0ec2...). Base: origin/main 6b909e0a. Client, native config; FOCUS (an App-Review-visible surface and the OTA runtime). No agent runs a package manager, eas, a build or a publish.

## PART A (ruled)

### R-NT1-9 (the review's question 3; AMENDS R-NT1-3 and R-NT1-4) THE VERSION BUMP LEAVES NT1a
(a) NT1a = THE STRINGS AND THEIR PINS ONLY (the change list's steps 2 to 5 and 7 to 10). `expo.version` stays "1.0.0" on main; the w37 e1 pin stays unedited (the change list's steps 1 and 6 and the E-row E2 leave this unit). The RED file pins `expo.version == "1.0.0"` and `runtimeVersion.policy == "appVersion"` as P rows.
(b) THE RELEASE COMMIT "NT1a-V" = exactly two edits: SmartCompareApp/app.json:5 the version 1.0.0 -> 1.0.1, and the w37 e1 pin with its comment (the text of E2, with "merged" read as "cut"). It is made by the orchestrator on a branch `release/1.0.1`, cut from the main sha the 1.0.1 build is made of, on the relay's dated word, and the owner builds from that branch. The spec amendments carry it as a ready diff with its own two-node check (the e1 node green on the branch, red on main).
(c) MAIN TAKES THE BUMP LATER, by the owner's dated decision after 1.0.1 is released. Only from that commit on does the two-runtime procedure of spec 2.6 (b) apply (L100 = the last main whose app.json says 1.0.0; 1.0.0 hotfixes from `release/1.0.x`).
(d) WHY: with `runtimeVersion.policy = appVersion` a bump on main re-targets every later `eas update` to runtime 1.0.1, and no 1.0.0 install takes it. The purpose strings live in Info.plist and are not visible to the JS bundle, so merging them is runtime-neutral. Keeping the bump out of main keeps the whole live fleet reachable from main through the review (the second OTA with consent v3, every client unit of the flips) with no maintenance branch.
(e) CONSEQUENCES: G-ORDER (spec 2.6 a) no longer gates the NT1a merge; it gates (c). NT1a merges when the merge freeze on main ends (after #378; the CLAUDE.md union in merge order). Between the 1.0.1 submission and its release, no update is published for runtime 1.0.1 (spec 2.6 b step 5 stays). The build-content checklist of spec 2.6 (c) is executed against the exact sha `release/1.0.1` is cut from. OTA_READINESS gains the amended section when NT1a merges (the orchestrator files it; the memory rule "read app.json before every publish" stands).

### R-NT1-10 (C1, RC6) BYTE IDENTITY IS PINNED, NOT INFERRED
G0 gains the exact `git diff --numstat` per file (app.json 2 / 2 under R-NT1-9; locales/en.json 2 / 2; locales/ar.json 2 / 2; b3a_copy.json 4 / 4; the two suites the hunk counts of E1 and E4) and the raw-bytes check (each edited JSON file with the edited lines replaced by the base lines is sha256-equal to the base blob, LF-normalised). A P row carries the raw-bytes check where it is cheap.

### R-NT1-11 (C2, C3, C4, RC1-RC3) THE PROCEDURE'S FACTS
Accepted as the review measured them: the runtime of a publish is resolved by the PROJECT's installed expo-updates (the modern branch), so `npm ci` in the publishing checkout is MANDATORY before every publish from a release checkout, followed by the read-only list for that runtime; the republish citation is corrected; `update:roll-back-to-embedded --runtime-version` is named as the rollback lever for one runtime's fleet from any checkout. Names only; every step is the relay's or the owner's.

### R-NT1-12 (C5, RC4, Q-O5) THE ARABIC
The purpose strings use the shadda-free phrase of the consent sheet v3 (the surface shown beside the prompt); the policy and the Terms carry their own marks. The spec's chosen draft stands; [NATIVE READ] stays on both Arabic strings. (The ARFIX round of S81-12 did not touch that phrase.)

### R-NT1-13 (C6, RC5) the two missing readers join spec 1.3 / 1.4 as STAY (the step-5 onboarding suite's comment; the expo-application mock's native version).

### R-NT1-14 (C7) THE NOTES FOR REVIEW
One policy address, the one recorded in App Store Connect. A named owner step at submission: re-read the LIVE consent sheet and policy and edit the Notes to match (they name both providers today; that changes when the OpenAI-removal texts land). The camera's behaviour is stated truthfully per R-NT1-18.

### R-NT1-15 (C8, C9) C8 is absorbed by R-NT1-9 (b): the release commit is made at build time, so no gap opens on main. C9: the 12-file base record is stored in the LC-6 base file at RED with its [pyt] lines.

### R-NT1-16 (Q-O1, Q-O2, Q-O6, Q-O7) jest only (no python twin); package.json stays 1.0.0 (no lock edit); branch names per R-NT1-9; the CLAUDE.md block is written at the merge and states the runtime rule as amended (true from the merge on).

### R-NT1-17 (Q-O4, CR3) THE PRIVACY MANIFEST stays byte-identical in NT1a (a stated limit: its documented meaning names the ended OpenAI programme; it over-declares, it does not under-declare). Whether the manifest and the store label change is THE OWNER'S App Privacy label step of the legal window; if the owner changes the label, the manifest change is its own native-config unit and must ride the same 1.0.1 binary: the relay is told so with the question.

### R-NT1-18 (B1; ADDENDUM 1 of the S93 brief) INC-CAM1 IS A STATED LIMIT OF NT1a
The camera route's codeless 500 with the "try again" sentence on a non-transient vision failure (app/api/image_routes.py:417 at main) is NOT fixed by NT1a (no backend byte) and is NOT owned by the incident lane (parked, unowned; the relay's line of 2026-11-11 22:02). NT1's spec, PR body and CLAUDE.md block name it as a stated limit with the follow-up id INC-CAM1. If the owner asks for it, this lane briefs it as its own FOCUS unit (the camera refusal envelope and the refund exits are a FOCUS surface).

### R-NT1-19 THE RED ROUND (after PART B closes)
The orchestrator creates the worktree's node_modules junction first (the junction rule). The RED agent first writes `.qa-s80/NT1_SPEC_AMENDMENTS.md` (one entry per ruling: the amended change list, rows, numstat values, the release-commit diff, the procedure text), then the RED file; every R row red at base on an assertion only, every P row green at base; the comm base record per R-NT1-15. Then the gate (specs/GATE_NT1.md), GREEN, two adversaries (correctness; app-review-and-privacy), the final round with the full jest once (R-NT1-8).

## PART B (THE OWNER'S CALLS; each closed by the owner's words through the relay)

### R-NT1-20 THE SPLIT (R-NT1-1)
GRANTED -> this file stands. REFUSED -> NT1 is re-specified as one unit; PART A is void except the runtime rule of R-NT1-9 (d). The orchestrator's recommendation stays: grant it (every NT1b item changes native dependencies and none is needed to bring the camera back).

### R-NT1-21 THE REVIEWER'S CAMERA (B1)
(a) `ENABLE_ANTHROPIC_VISION` ON before the 1.0.1 submission: the reviewer's scan works on Claude vision under consent v3; for the review window the 1.0.0 installs that accepted consent v3 send photos to Anthropic while their installed permission text still names OpenAI (CLAUDE.md:508 names this risk as "accepted or 1.0.1 live"); the consent sheet and the policy name both providers. It needs the S81-07 stage V go, or the owner's dated acceptance without it.
(b) Vision OFF through the review, with a Notes disclosure that photo identification is temporarily unavailable: the reviewer grants the two new prompts and the feature they describe fails; a guideline 2.1 rejection is likely, and INC-CAM1 (the "try again" sentence) then becomes a precondition to brief before submission.
THE ORCHESTRATOR'S RECOMMENDATION: (a). The answer changes spec 2.6 (c), the owner steps O5 / O6 and the Notes draft; it changes no RED row.

### R-NT1-22 WHAT THE RELAY SENDS BACK
The owner's words on R-NT1-20 and R-NT1-21, verbatim, as dated lines. The RED launches on R-NT1-20 alone (R-NT1-21 moves no row).

## ADDENDUM 2026-11-12 05:22: PART B CLOSED UNDER THE OWNER'S STANDING AUTHORIZATION
- THE OWNER'S WORDS (2026-11-12 about 05:20, relayed verbatim by session 82): "look continue with the work as ill be busy and cant attend so consider and use the bypass permissions on anything that needs my approval is considered approved". THE RELAY'S READING (the relay's): covered = every gate of the agreed plan that waited only for the owner's yes, taken at the recommendation already put to him; for NT1: the split as recommended (1.0.1 = the permission strings without a provider name plus the version bump only) and the reviewer's camera = Claude vision ON before 1.0.1 is submitted, only after the S81-07 vision stage says go and the legal window is done. Not covered (the relay's words): anything secret, the proofs on the owner's phone, new scope, any text or ruling the owner has seen no recommendation for.
- R-NT1-23 R-NT1-20 IS CLOSED: THE SPLIT IS GRANTED. PART A stands (the version bump is the release commit of R-NT1-9: it is in the 1.0.1 binary, not in the NT1a merge). The RED launches.
- R-NT1-24 R-NT1-21 IS CLOSED AS OPTION (a), WITH THE RELAY'S TWO CONDITIONS (the S81-07 vision stage says go; the legal window is done). THE ORCHESTRATOR'S CONSEQUENCE: the vision stage is NOT RUNNABLE without the owner's OWN photo set (about 100 packaging photos with a manifest; S81_07_BRIEF R-S07-2), which no authorization can supply. Until the photos exist the 1.0.1 SUBMISSION waits; the build of NT1a does not. The alternative of R-NT1-21 (the owner's dated acceptance without the measurement) was not put to the owner as a recommendation and is NOT covered. The relay is told. Spec 2.6 (c), the owner steps O5 / O6 and the Notes draft are written for option (a).
- R-NT1-25 UNCHANGED IN THIS LANE: no permission setting changes; a refusal by a classifier or a deny rule is never worked around; no flag, variable, credential or production read; the NT1a merge keeps its gates (the merge freeze, CI, both adversaries, the full jest once).
