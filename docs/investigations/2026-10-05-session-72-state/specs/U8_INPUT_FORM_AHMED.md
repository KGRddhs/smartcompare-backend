# U8 privacy policy + terms: what only you can tell us (about 10 minutes)

Reply with the item number and your answer (a letter is enough where there are options). Nothing here is legal advice: it lists the facts the new documents need and what each choice changes. Claude never invents a name, address, number or email.

## Already answered - not asked again
- Response times: 10 working days (correction, deletion, objection), 15 working days (access to your data).
- No "Beta" label anywhere.
- An in-app control to withdraw the AI-processing permission ships with U3b.
- Account deletion is fixed in code (U8b, PR #290; migration 043 written, waiting for you to apply it).
- Minimum age 13+. App name MYEZ (Arabic name as in the app). Email addresses stay on qaren.app.
- Effective date = the day the new documents go live (Claude fills it in).

## Questions

| # | Question | Why it is needed | Recommended default, and what follows otherwise | Needed for 1.0.0? |
|---|---|---|---|---|
| 1 | Who is the publisher and data controller (the "we" in both documents)? **A** Hussain Aseeri as an individual (he is the Apple account holder, so he is the seller on the App Store). **B** a company. | Both documents and the App Store copyright must name the same person or company as the seller (Apple 5.1.1(i), 5.2.1; Bahrain PDPL Art 17). | **A** (fastest). Under A, if you (not Hussain) own the app's code and brand, you two need a short written licence or transfer between you; Claude cannot write it. **B** needs a D-U-N-S number and an organisation Apple account (weeks), plus item 3. | Yes |
| 2 | Should the documents show a trade name ("Hussain Aseeri, trading as ...")? | Shown next to the name in item 1. | No trade name: "MYEZ" stays the app name only. If you have a registered trade name, give it exactly as registered. | Optional |
| 3 | Commercial registration (CR) number. | Only if item 1 is B. | Skip under A. | Only under B |
| 4 | A postal address where legal letters reach the publisher (building, road, block, city, country). | Required contact detail in the privacy policy and the terms; its country also decides which country's law and courts the terms name. | No default possible. If it is in Bahrain, the terms keep Bahraini law and courts. | Yes |
| 5 | Do `privacy@qaren.app` and `support@qaren.app` really deliver to an inbox someone reads? (Send one test email to each.) | The policy promises replies within 10/15 working days at these addresses; the App Store support link points to support@. | Use these two and drop `legal@qaren.app`. If either fails, give a working address instead (or fix Cloudflare Email Routing first). | Yes |
| 6 | **D3** OpenAI data sharing. **A** keep it OFF (MYEZ never lets OpenAI use user data to improve its models). **B** keep sharing ON with a separate opt-in. | The AI section of the policy must say which is true; today the policy promises an opt-out that does nothing. | **A**, and then switch the organisation's data-sharing setting OFF in the OpenAI dashboard and tell Claude it is done. **B** adds a separate opt-in screen, asks every existing user again, and needs a second OpenAI key. | Yes |
| 7 | Where will the app be available at launch? **A** Bahrain only. **B** all six GCC countries. | Decides whether the policy adds the Saudi complaint route (SDAIA) next to Bahrain's authority. | **B** (the store listing targets the GCC). Under A the Saudi part is left out and must be added before you open Saudi Arabia. | Yes |
| 8 | Will a lawyer review the documents before they go live? | With a review, the legal-basis, transfer, breach and governing-law sentences wait for the lawyer's wording. | Your call. **Yes**: Claude prepares the drafts, you send them, publication waits for the markup. **No**: Claude publishes plain, factual defaults (flagged in the PR) and nothing claims a lawyer reviewed them. | Yes |
| 9 | Hosting regions: the region shown in the Supabase project settings, the Railway service settings and the Upstash database page (three words, e.g. "eu-central-1"). | The policy must say where data is stored outside Bahrain. | If skipped, the policy names only what is known (United States for OpenAI, Germany for Sentry) and says "including", which is incomplete. | Optional |
| 10 | How long to keep records that are NOT tied to an account after deletion (sign-in security logs, which hold IP addresses, and anonymous search/activity logs)? **A** no fixed period (truthful today: nothing deletes them). **B** 12 months, with a small cleanup job Claude adds before publication. | The policy must give a retention period per category; today there is none for these records. | **B** 12 months (or give another period). A is truthful but leaves the policy without a period for these records. | Yes |
| 11 | Users between 13 and adulthood: add "if you are under the age of majority where you live, a parent or guardian must agree to these terms"? | The documents must say how users without full legal capacity are handled; no age-check code changes either way. | **Yes** (one sentence in each document). If no, the documents say only "13 and over". | Optional |
| 12 | Will you apply migration 043 (send the PRECHECK result first) BEFORE the new policy goes live? | The deletion paragraph is only true once 043 is applied; the old function keeps your email, name and answers after deletion. | **Yes**. If no, the policy must describe today's partial deletion (truthful but it reads badly, and the store listing sentence "delete your account and its data" must be removed). | Yes |

## What you do on launch day anyway (no answer needed)
Apply 043 (item 12) -> merge U8 -> redeploy the landing site the same hour (`railway up landing --path-as-root -s qaren-landing -d`) -> a native Arabic speaker reads the Arabic pages -> paste the Railway privacy URL into App Store Connect.
