# Two product calls Ahmed owes — with the orchestrator's recommendation (2026-09-24)

## 1. W4-2 `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` — the "(converted from USD)" rendering

What the user will see once W4-1 and W4-2 are ON: every Serper-shopping row that today PENDS because its `url` was a search link (google.com/search or a synthesized retailer search url) becomes SHOWABLE as `converted_usd`, and the phone (97b5f15 and HEAD) renders it as "BHD x (converted from USD)" / "(محول من الدولار)" with the 'Local listing' pill. The price is a real cited number from a listing; the retailer link the user can open is gone (`url: null`), because we never fetched a PDP. The options recorded in W4-1 ruling 5:

- **(a) Accept the label as shipped.** The client already appends the "converted" copy; the row is honest about being a converted listing price, and the 'Local listing' pill stays. Cost: no PDP link for those rows; the un-cache cost in the W4-2 PR body (the 9 non-listing-template retailers re-run the cascade per request). Zero new work.
- **(b) A third label, showable-but-not-genuine** (e.g. "listing price"), touching `_showable_source_methods`, the `eval_runner` mirror and the client enum — its own unit (backend + client + OTA).
- **(c) Resolve the merchant PDP** so evidence exists before the row shows (W4-2's own option a: fetch the PDP behind `_discovery_url`, at Serper/Bright Data cost, on the request path or off-clock).

**Recommendation: (a) now, (c) later as a bounded off-clock unit.** (a) is what the code ships and is honest; (b) buys a word, not evidence; (c) is the only option that gives the user a link and a verified price, but it is a new spend line and belongs after the Bright Data gate and the OTA. Your call gates the flip; the code merged either way.

## 2. Issue #101 — a missing signal outscores a measured bad one (`MISSING_SCORE = 50`)

Today an unrated product beats an identical 2.0-star product (50 vs 40), and the void renders as a solid 50 bar. Options:

- **(A) Renormalize.** When a dimension has no data, drop it from the roll-up and renormalize the remaining weights to 1.0; render the missing dimension as "no data" (no bar), never as 50. Behind a flag (`ENABLE_MISSING_DIM_RENORMALIZE`), default OFF, per call; `missing_data` already lists the dims. Crown changes on any pair where one product lacks a dimension the other has measured badly — the honest direction.
- **(B) Keep 50 but cap it below the worst measured score** in the same pair (e.g. min(measured) - 1). Cheaper, but arbitrary and still renders a bar.
- **(C) Leave it** and document the bias.

**Recommendation: (A)**, as W4-6b, with the same TDD/adversary process; the flag's canary is `scoring_v2.overall_score` / `winner_idx` split by `missing_data`. Say "A", "B" or "C" and the spec gets written.
