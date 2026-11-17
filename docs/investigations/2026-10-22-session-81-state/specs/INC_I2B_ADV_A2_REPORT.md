# INC-I2b ADVERSARY A2 (SHOP TIER AND PRODUCTION), 2026-11-17 03:58-04:35 AST

Verdict: SOUND (no BLOCKING, no MAJOR; 6 MINOR -> stated limits / flip-note text).
Head: aec760b5a6657765fed22f591a40d76fdd891435 (parent 5cd93c6a; log -3: aec760b5, 5cd93c6a, 16662850). Worktree untouched (status empty before and after); no scratch worktree used.

## Runs
- [pyt] tag=s96b-adva2-probes1 start=2026-11-17 04:22:06 end=04:22:15 elapsed=8s bound=600s status=OK rc=0: 7 passed (my probe file adv_a2/test_adv_a2_probes.py, observations adv_a2/probe_out.json).
- [pyt] tag=s96b-adva2-head start=2026-11-17 04:25:20 end=04:26:00 elapsed=40s bound=1200s status=OK rc=0: 185 passed (RED 28 + addenda 10 + I2a 67 + test_inc_r1_seam 80); [hermeticity] sentinel checked 185; [netguard] blocked 0 attempt(s).

## Probes (measured)
- Woo stamp identity: select_best returns the candidate OBJECT (price_service.py:8723 eligible[0]; :8669 min() also an object), exact gate ON and OFF: the id map finds it, the stamp lands on the returned dict (q2). Map is call-local, candidates alive -> no id reuse.
- OOS-only winner: returned in_stock=False and stamped (one `IMG_SHOP page ... outcome=stamped` line). Right product, the chokepoint pends the price: accepted.
- Malformed images (q3): dict / [] / list of str / None / 50 x {src:5} -> no_image, no raise; [{src:None},{good}] -> stamped from the 2nd; [{http},{good}] and [{non-raster},{good}] -> no_image (first str src decides); a Jetpack-style off-host CDN is stamped (D08 page=itself), refused later only under IMAGE_PIPELINE_V2 (stated, E11).
- Imports (q1, fresh processes): woocommerce_service, image_relevance, price_service, image_service each import first with rc 0 (no cycle); price_service alone does not load image_relevance; IR standalone 0.095 s; image_service already loads IR, so in the app the WOO import costs ~0.
- Late chooser (q5, L ON, B ON): override > attached job > fallback > shopping > none/missed_at_deadline, exactly; thumb "" -> none.
- Thumb (q6): real-shaped Serper Shopping item (gstatic `shopping?q=tbn:` URL, no raster path) -> accepted, keys line gstatic=1; W unset and W ON same; G OFF -> relevance {} -> `outcome=skipped`; garbage shapes -> none / rejected, no raise.
- OFF reads (q7): W unset: body-lotion title passes (None), relevance has 4 keys (no typed), pick name prefix imgpick:v1:a9bdcc90:.

## Carrier `_typed_name` (read every consumer after the INC-R1 hook)
Written only SCS:4240-4243 (G and W ON, rewritten dicts). Consumers of the Step-1 products list after SCS:4582 / 5298: _resolve_pair_category (SCS:480, reads search_query/name/category), category_gate.post_resolve_refusal and apply_form_override_stubs (category_gate.py:650-730, search_query/name/category), the category write-back (SCS:4674 / 5367), kb_serve.fetch_cards (kb_serve.py:151, brand/name/variant), _fetch_product_data (SCS:6195-6203 named keys only; result dict built fresh SCS:6211). No dict copy / items() / json.dumps / repr / log of a product_info dict exists in SCS; stream events and the response are built from product_data (result dicts). `relevance["typed"]` is read only by identity (IR:636) and the pick-name axis labels (IMG:557), never logged or prompted. No leak (AX-4 agrees).

## Flag-mix walk, today's production (G ON, S ON, L ON since 02:45, R OFF; head file:line)
| Mix | Behaviour | Where |
|---|---|---|
| W A B OFF, R OFF (merge state) | base verdicts (check -> _check_base, IR:664); relevance 4 keys (IR:859); WOO reads A per winner only (WOO:298); B block not entered (SCS:6734); chooser base (SCS:6169 -> None). OFF difference: PICK_GUARD_RULES a9bdcc90 (IMG:489) and the axis s1 -> s1w0 (IMG:556-558): every L-ON imgpick entry unread (below) | P1, q7 |
| W ON, R OFF, L ON | typed = full_name (SCS:1396-1409) at the late job (SCS:6330); words in the job's RelevanceCall; axis s1w1:<typed labels> | E5, E8, AX-7 |
| W ON, R ON, L ON | carrier SCS:4240-4243 -> _typed_image_text; rewritten dict without carrier -> "" (fail-open) | E5, AX-4 |
| R ON, W OFF | no carrier, base dict | P1 |
| W ON, L OFF (rollback of L) | inline cascade typed= at SCS:6547 | E1-E6 |
| A ON, L ON | stamp -> bind override on the current price (SCS:6120 / 6153 via SCS:1475) or fallback on price_phase1 (SCS:6698, 6164) | E10, q5 |
| A ON, L OFF | inline override SCS:6695-6729 on the pre-swap price | E9 |
| B ON, L ON | thumb -> _late_entry["shop_thumb"] (SCS:6756) -> last resort SCS:6168-6171 | E12, E18, q5 |
| B ON, L OFF | thumb only when no cascade / override picture (SCS:6734, 6757) | E12 |
| G OFF, any W A B | W never read; stamp skipped (IMG:798); thumb skipped (IMG:860) | P3, q6 |
| camera | relevance {} -> thumb skipped; stamp used by the vision override | E15 |
| hard cap | L OFF: B block cancelled with the fetch; L ON drain: base outcome | AX-6 |

## Merge-time cost (L ON on web since 02:45)
PICK_CACHE_PREFIX moves imgpick:v1:b39b9d79: -> imgpick:v1:a9bdcc90: AND the digest axis moves s1 -> s1w0, so every imgpick entry written since L went ON is never read again (orphans expire at IMAGE_PICK_CACHE_TTL_SECONDS, default 604800 s): one paid late cascade (Serper Images credit, possibly an llm_pick) per product name once, and the L window's `IMG_LATE cache outcome=hit` rate resets to 0 at the deploy.

## Findings (all MINOR)
- A2-1 W flip costs a second one-time miss per product (axis w0 -> w1:<labels>), and under W ON typed-label variants split one product into several pick names; L9 names only the merge.
- A2-2 The deploy resets the L window's cache reading (hit -> 0); merge after the L reading or record the deploy time in the ledger as a break in that reading.
- A2-3 Under today's L ON, `IMG_SHOP page outcome=stamped` and `IMG_SHOP thumb outcome=accepted` prove a candidate, not a shown picture: the stamp is logged before is_price_showable / content safety (WOO:390-400) and before the fan-out picks a price; the thumb is computed for every picture-less product even when the bind later attaches the job. The flip proof must read `IMG_LATE bind outcome=override|fallback` (A) and `IMG_LATE bind outcome=shopping` (B).
- A2-4 Flip notes write `[IMG_RELEVANCE] ... outcome=accepted` (spec 8): a Railway filter with the bracket matches nothing; name the plain-word filters (IMG_RELEVANCE, IMG_SHOP page, IMG_SHOP thumb, IMG_LATE bind). The new lines themselves carry no bracket. With B ON, a pending job at the deadline binds `shopping` instead of `missed_at_deadline`, so that count drops.
- A2-5 `keys=` / `names=` print remote JSON key names that fullmatch the closed pattern; a nonstandard store key such as Dior_Sauvage_EDP is printed (q3). Ruled I-5 (names only); state it.
- A2-6 The stamp takes the FIRST item with a str src: an http or non-raster first image gives no_image even when a later image is good (q3); the shop's featured image is first in the Store API, so this is a stated limit.
