# S81_11_NATIVE_READ: the Arabic strings of S81-11 HONEST-FRAGRANCE-UI (+ D20) for the owner's native read

Written by the S81-11 GREEN agent (GC-16, R-S11-40) from the catalogs at the GREEN commit (base 6869a3e6); the format of S81_10_NATIVE_READ.md (key | EN | AR | note). The PR body stays pure ASCII and points here; this file carries the Arabic script itself so it can be read (the S81-10 precedent).

Diacritics (GC-4, the B3-A A8 / MR11 rule pinned by __tests__/b3a/honestCopy.b3a r31b): every new or changed AR value below is written WITHOUT harakat, shadda or tanween, except inside the brand word (the spec KEYS-table cells that carried tanween or shadda were re-cut by rule, e.g. the tanween of "for now" / "soon" and the shadda in the share message verbs). The native reader may restore a mark only through a follow-up that re-pins r31b.

## [NATIVE READ] added (15) and changed (10) keys

| key | EN | AR | note |
|---|---|---|---|
| `home.categories.fragrancesOnly` (added) | Fragrances only for now | العطور فقط حاليا | the line under the category row (both row states); also the title of the CATEGORY_NOT_LIVE alert and the camera empty state |
| `home.categories.comingSoon` (added) | Soon | قريبا | the badge inside a coming-soon chip and its accessibility hint (renders only under /app/version surfaces, SF1) |
| `home.categories.comingSoonToast` (added) | {{category}} is coming soon. Fragrances are ready now. | {{category}} قريبا. العطور جاهزة الآن. | the inline toast after a coming-soon tap; {{category}} = the chip label |
| `home.errors.categoryNotLive` (added) | We compare fragrances for now. More categories are coming soon. | نقارن العطور حاليا. فئات أخرى قريبا. | the ONE refusal body for CATEGORY_NOT_LIVE 400 / 429 on text, link and camera (no date, no seconds) |
| `home.errors.insufficientDataReason.same_identity` (added) | Those two look like the same product. Pick two different fragrances to compare. | يبدو أن المنتجين نفس العطر. اختر عطرين مختلفين للمقارنة. | INSUFFICIENT_DATA reason same_identity (text, link, camera) |
| `home.errors.insufficientDataReason.placeholder_identity` (added) | We need clearer names to tell which products these are. Add the brand and the fragrance name. | نحتاج أسماء أوضح لنعرف المنتجين. أضف اسم الماركة واسم العطر. | INSUFFICIENT_DATA reason placeholder_identity (text and link; the camera keeps visionFailed) |
| `home.errors.insufficientDataReason.category_conflict` (added) | Those two are different kinds of product. Pick two fragrances to compare. | المنتجان من نوعين مختلفين. اختر عطرين للمقارنة. | INSUFFICIENT_DATA reason category_conflict (text, link, camera) |
| `results.honest.notListed` (added) | Not listed by the stores we can read yet | غير مذكور لدى المتاجر التي نقرؤها حتى الآن | the D20 honest-unknown line (price card, accordion sections, the size / concentration rows) |
| `results.price.asOf` (added) | {{store}}, as of {{date}} | {{store}}، بتاريخ {{date}} | a fresh price: store (as the retailer string arrives, a host for a KB price) + date |
| `results.price.asOfNoStore` (added) | As of {{date}} | بتاريخ {{date}} | a fresh price with no store string |
| `results.price.lastSeen` (added) | {{store}}, last seen {{date}} | {{store}}، آخر ظهور {{date}} | a stale price (past the fresh window, within 30 days) |
| `results.price.lastSeenNoStore` (added) | Last seen {{date}} | آخر ظهور {{date}} | a stale price with no store string |
| `results.price.listedOn` (added) | Listed at {{store}} on {{date}} | معروض لدى {{store}} بتاريخ {{date}} | a STORED result (History / recents): the store listed it on that date; never aged out (R-S11-13) |
| `results.price.listedOnNoStore` (added) | Listed on {{date}} | معروض بتاريخ {{date}} | a stored result with no store string |
| `results.price.checkedEarlier` (added) | Price checked earlier | تم التحقق من السعر سابقا | a stale price whose date is unknown (R-S11-18): no date is shown |
| `home.errors.comparison` (changed) | Sharper match coming up — add the brand and the fragrance name. | نطابق بدقة أكبر قريبا — اكتب اسم الماركة واسم العطر. | fragrance-neutral (brand and fragrance name, R-S11-22) |
| `home.errors.insufficientData` (changed) | Thin data on that pair — swap in two fragrances with the brand and name. | البيانات قليلة عن هذين المنتجين — جرب عطرين مع اسم الماركة واسم العطر. | fragrance-neutral (brand and name, no "model", R-S11-22) |
| `onboarding.s1.quote_1` (changed) | Sauvage or Bleu de Chanel? See their prices and details side by side. | سوفاج أم بلو دو شانيل؟ اعرض الأسعار والتفاصيل جنبا إلى جنب. | onboarding step 1 example (was Galaxy or iPhone) |
| `onboarding.s1.quote_2` (changed) | Two oud perfumes? See which one fits your budget. | عطران من العود؟ اعرف أيهما يناسب ميزانيتك. | onboarding step 1 example (was two sunscreens) |
| `onboarding.s1.quote_3` (changed) | EDP or EDT of the same scent? See how size and price compare. | أو دو بارفان أم أو دو تواليت لنفس العطر؟ اعرف الفرق في الحجم والسعر. | onboarding step 1 example (was two multivitamins); AR avoids the standalone verb that the brand fence reserves |
| `onboarding.s17.tag_echoes_body` (changed) | When peers your age just compared the same pair. | عندما يقارن أقرانك في عمرك نفس الزوج. | step 17 notification type, now digit-free (was "5+ peers", R-S11-32) |
| `home.hero` (changed) | Compare two fragrances. | قارن بين عطرين. | the Home hero (was "Compare anything.", R-S11-30); the verb "compare" stays as before |
| `home.compare.box_a_text` (changed) | Product A · e.g. Dior Sauvage EDP | المنتج أ · مثال: ديور سوفاج أو دو بارفان | input A placeholder, fragrance example (was e.g. iPhone 15); "o de parfan" = eau de parfum |
| `home.compare.box_b_text` (changed) | Product B · e.g. Bleu de Chanel EDP | المنتج ب · مثال: بلو دو شانيل أو دو بارفان | input B placeholder, fragrance example (was e.g. Galaxy S24) |
| `referrals.share.messageWithLink` (changed) | I overthink every purchase. MYEZ helps me pick between two fragrances. Try it: {{link}} (or use code {{code}} in the app) | أفكر زيادة قبل أي شراء. ميّز يساعدني أختار بين عطرين. جربه: {{link}} (أو استخدم رمز {{code}} داخل التطبيق) | only the "30 seconds" clause replaced; the brand word, {{link}} and {{code}} kept |

## The month-name rule (R-S11-24, GC-7)

The {{date}} of the as-of / last-seen / listed-on lines is formatted on the GREGORIAN calendar in both locales: EN `en-US` month short + day (e.g. "Nov 3"); AR the `ar-SA-u-ca-gregory` locale with the explicit calendar option, digits converted to the app digit system (ASCII by default). Never Hijri. The Arabic month names as Node 24 / ICU 77 renders them (day 3 of each month; Hermes on device is unmeasured: owner TestFlight check, stated limit S81-11-L16):

| month | AR as rendered (before the digit conversion) |
|---|---|
| 1 | ٣ يناير |
| 2 | ٣ فبراير |
| 3 | ٣ مارس |
| 4 | ٣ أبريل |
| 5 | ٣ مايو |
| 6 | ٣ يونيو |
| 7 | ٣ يوليو |
| 8 | ٣ أغسطس |
| 9 | ٣ سبتمبر |
| 10 | ٣ أكتوبر |
| 11 | ٣ نوفمبر |
| 12 | ٣ ديسمبر |

## Deleted keys (17, both catalogs; no read needed)

`cohort.trainedBy`, `history.hero.savings`, `home.cat.electronics`, `home.cat.makeup`, `home.cat.skincare`, `home.cat.supplements`, `home.categories.nudge`, `home.savings.amount`, `home.savings.eyebrow`, `loading.tip.peer_prioritize`, `onboarding.s14.cohort_footer`, `profile.month.savings`, `profile.styleProfile.basedOn`, `profile.styleProfile.peersInGovernorate`, `referrals.share.toast.confirm`, `results.cohort_badge`, `results.tips.cohort_priority`
