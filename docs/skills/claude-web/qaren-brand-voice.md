---
name: qaren-brand-voice
description: Use whenever drafting copy, ad text, headlines, CTAs, push notifications, or any user-facing string for Qaren (قارن) — a Bahrain-based product comparison app. Auto-applies invisibly when Claude is asked to write Qaren ad copy, lead-form thank-you text, Instagram captions, or any user-facing language. Enforces forbidden-vocabulary list, Arabic-first cadence with Bahraini code-switching, emerald-as-signal-color discipline, and trust framing.
---

# Qaren Brand Voice — Copy Contract

## When this skill applies

ANY time you're writing user-facing language for Qaren, including but not limited to:

- Ad copy (headline, body, CTA)
- Lead form labels, questions, thank-you screens
- Instagram captions, Stories text
- Push notification bodies
- Onboarding screen copy
- Error / empty / loading states (rare — Qaren has very few)

This skill does NOT apply to:
- Internal logs, backend code, technical documentation
- Names of campaign / ad set / ad entities (those follow the naming convention in `qaren-meta-campaign-setup-bahrain`)

## Forbidden vocabulary (HARD BAN)

Never use these in user-facing strings — neither Arabic nor English. They violate the brand contract.

**English forbidden:**
- couldn't, can't (in error contexts)
- failed, failure
- error, oops
- try again
- something went wrong
- estimated, approx, approximately (in price/spec contexts)
- problem, issue, broken

**Arabic forbidden:**
- تعذر (could not)
- فشل (failed)
- خطأ (error)
- مشكلة (problem) — when describing app state
- تقدير, مُقدَّر (estimate, estimated) — when describing price/spec

If you find yourself wanting to use one of these, the framing is wrong — reword to describe what IS happening instead of what isn't.

## Approved framing patterns

**For "missing data" situations:**
- EN: "More data coming soon" / "We're still finding info on this"
- AR: "نجمع المعلومات الآن" / "بنحدّث قريباً"

**For "loading":**
- EN: "Comparing..." / "Finding the best option..."
- AR: "نقارن لك..." / "نلقي نظرة..."

**For "wait, please":**
- EN: "Almost there..."
- AR: "بنخلص..." (Bahraini cadence — NOT الصبر / wait)

## Language strategy

**Primary: Arabic** — 80%+ of Qaren's Bahrain target audience is Arabic-primary or bilingual (per Fillout n=337 survey: 41% AR, 48% bilingual, 12% EN-only).

**English: secondary, used when:**
- Targeting the bilingual segment (24% surveyed prefer EN-leaning content)
- Specific videos / creatives are scripted with English code-switching (Bahraini millennial speech pattern)
- Form field labels where translation adds ambiguity

**Code-switching is good** when it sounds natural to a Bahraini millennial. Example: "اختر الخيار اللي يناسبك — smart pick" feels native. Bad: full-sentence English with stranded Arabic words.

## Tone

- **Warm, never urgent.** No "ACT NOW", no "LAST CHANCE", no countdown timers.
- **Confident, never dismissive.** Qaren tells you why it picked something; never says "trust us."
- **Concise.** Hero headlines < 50 chars. CTAs ≤ 3 words.
- **Personal.** Use the singular "you" / "أنت" (not "you all" / "أنتم").

## Color discipline (verbal cue when describing UI)

- **Emerald #10B981** is Qaren's signal color — reserved for winner reveal, success ticks, cohort accents. NOT primary CTA color. If asked to describe a CTA, say "black with emerald accent on hover" not "emerald button".
- **Black #0A0A0B** is the primary surface.
- When describing brand visuals to a designer or another AI, lead with this distinction.

## Trust framing (lifted from Fillout survey n=337)

These are the framings 22-69% of survey respondents said would make them trust a tool:

| Framing | % said this builds trust | Suggested usage |
|---|---|---|
| "Explicit pros and cons" (إيجابيات وسلبيات صريحة) | 69% | Use in ad body and verdict text |
| "Recommendation that fits my budget / need" | 38% | Use near pricing or in onboarding |
| "Clear reason for the recommendation" | 23% | Use under verdict line |
| "Doesn't feel like an ad" | 18% | Avoid hard-sell phrasings |

When drafting a CTA or headline, lean into the 69%-trust framing first (pros/cons / clear comparison) — it's the strongest signal.

## Examples — DO vs DON'T

| Context | DO ✅ | DON'T ❌ |
|---|---|---|
| Ad headline (AR) | "تردد قبل ما تشتري؟ Qaren يقارن لك." | "أوقف الندم! اشتري بثقة الآن!" |
| Ad headline (EN) | "Hesitate before you buy? Qaren compares for you." | "Stop regretting! Buy smart NOW!" |
| Thank-you text (AR) | "شكراً! بنرسلك أول ما ينطلق Qaren 🌿" | "تم بنجاح! انتظر إيميل التأكيد." |
| Lead-form field label | "البريد الإلكتروني" (just the field name) | "أدخل بريدك الإلكتروني للمتابعة *" |
| Price uncertainty | "السعر يبدأ من X دينار" | "السعر التقديري X دينار" |

## Self-check before delivering Qaren copy

Before returning any user-facing string to the user, run this checklist:

- [ ] No forbidden vocabulary (EN list + AR list above)
- [ ] Arabic-first when audience is Arabic-primary or bilingual
- [ ] No urgency / scarcity language
- [ ] Singular "you" / "أنت"
- [ ] Trust framing leans on pros/cons or fits-your-budget angles
- [ ] CTA ≤ 3 words

If any item fails, rewrite before returning.
