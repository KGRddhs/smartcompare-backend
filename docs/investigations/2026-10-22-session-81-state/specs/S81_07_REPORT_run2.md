# MEAS-CLAUDE-GATE go / no-go

Credential variable (name only): MEAS_ANTHROPIC_TEST_KEY
Output folder: C:\Users\SynAckITPC\MYEZ-meas\s81-07-run2
The unit ceiling is per output folder; the workspace spend limit is the only cross-folder backstop.
Billing assumption (the only one): 4xx rejected requests are not billed.
The bars are PROPOSED pass bars (RULINGS_S81_07 R-S07-31); every raw figure is printed below, so a changed bar needs no second run.

| role | verdict | failed bars | bars |
|---|---|---|---|
| TEXT | GO | - | {"json_valid_pooled_min": 0.98, "json_valid_site_min": 0.9, "max_tokens_pooled_max": 0.02, "max_tokens_site_max_hits": 2, "p95_s": {"classify": 4.0, "image_tier3": 2.5, "price": 7.5, "reviews": 5.0, "specs": 4.0}, "refusals_a4_arabic_max": 0, "refusals_a4_max": 1, "schema_accept_min": 1.0, "timeouts_max": 0} |
| VERDICT | GO | - | {"a1_refusals_max": 0, "a6_agreement_min": 0.9, "a6_mismatch_max": 0.1, "a6_refusals_max": 1, "json_valid_pooled_min": 0.98, "timeouts_max": 0} |
| SONNET_ESCALATION | GO | - | {"accepted_min": 20, "json_valid_min": 0.95} |
| CRITIC | NOT RUN | - | none (not a flip bar) |
| MODERATION | NOT RUN | missing:moderation | {"fail_closed_max": 1, "false_positives_max": 0, "p95_s": 3.0, "recall_min": 0.9} |
| VISION | NOT RUN | missing:vision | {"haiku_hit_min": 0.8, "haiku_minus_sonnet_min": -0.05, "p99_s": 20.0} |
| WEB_SEARCH | NOT RUN | - | none (not a flip bar) |
- stage text: spent 0.594937 USD, stop None, not runnable no
- stage moderation: NOT RUN (no results.json)
- stage vision: NOT RUN (no results.json)
- stage web_search: NOT RUN (no results.json)

A6 measures adherence to the deterministic scores_summary carried by the prompt (the production WINNER_INDEX_MISMATCH rule), not verdict quality against owner gold.
Percentiles are nearest-rank with a timeout counted as +infinity; with n = 20, p99 = max (n = 20).

## Raw figures

- text / A0_capabilities: {"calls": 2, "error_classes": {}, "hosts_refused": [], "n_censored": 0, "ok": 2, "p50_s": 0.281, "p95_s": 0.922, "p99_s": 0.922, "stop_reason": null, "timeout_rate": 0.0, "usd": 0.0}
- text / A1_sites: {"cache_read_share": {"pooled": 0.0, "sites": {"classify": 0.0, "disambiguate": 0.0, "image_tier3": 0.0, "parse": 0.0, "price": 0.0, "price_training": 0.0, "reviews": 0.0, "specs": 0.0, "specs_synthesized": 0.0, "specs_targeted": 0.0, "url_extract": 0.0, "verdict": 0.0}}, "calls": 320, "cost_per_compare": {"n": 20, "p50_usd": 0.0039416, "p95_usd": 0.0040283}, "error_classes": {}, "hosts_refused": [], "n_censored": 0, "ok": 320, "p50_s": 1.016, "p95_s": 3.688, "p99_s": 4.265, "sites": {"classify": {"json_n": 0, "json_valid": 0, "max_tokens_hits": 0, "n": 20, "p95_s": 1.046, "p99_s": 1.469, "refusals": 0, "schema_accepted": 0, "schema_n": 0, "timeouts": 0}, "disambiguate": {"json_n": 20, "json_valid": 20, "max_tokens_hits": 0, "n": 20, "p95_s": 1.313, "p99_s": 1.39, "refusals": 0, "schema_accepted": 20, "schema_n": 20, "timeouts": 0}, "image_tier3": {"json_n": 40, "json_valid": 40, "max_tokens_hits": 0, "n": 40, "p95_s": 1.125, "p99_s": 1.453, "refusals": 0, "schema_accepted": 0, "schema_n": 0, "timeouts": 0}, "parse": {"json_n": 20, "json_valid": 20, "max_tokens_hits": 0, "n": 20, "p95_s": 1.312, "p99_s": 1.313, "refusals": 0, "schema_accepted": 0, "schema_n": 0, "timeouts": 0}, "price": {"json_n": 40, "json_valid": 37, "max_tokens_hits": 0, "n": 40, "p95_s": 2.109, "p99_s": 4.422, "refusals": 0, "schema_accepted": 0, "schema_n": 0, "timeouts": 0}, "price_training": {"json_n": 20, "json_valid": 20, "max_tokens_hits": 0, "n": 20, "p95_s": 1.062, "p99_s": 1.094, "refusals": 0, "schema_accepted": 0, "schema_n": 0, "timeouts": 0}, "reviews": {"json_n": 40, "json_valid": 40, "max_tokens_hits": 0, "n": 40, "p95_s": 2.125, "p99_s": 2.531, "refusals": 0, "schema_accepted": 0, "schema_n": 0, "timeouts": 0}, "specs": {"json_n": 40, "json_valid": 40, "max_tokens_hits": 0, "n": 40, "p95_s": 2.313, "p99_s": 2.359, "refusals": 0, "schema_accepted": 0, "schema_n": 0, "timeouts": 0}, "specs_synthesized": {"json_n": 20, "json_valid": 20, "max_tokens_hits": 0, "n": 20, "p95_s": 1.422, "p99_s": 1.828, "refusals": 0, "schema_accepted": 0, "schema_n": 0, "timeouts": 0}, "specs_targeted": {"json_n": 20, "json_valid": 20, "max_tokens_hits": 0, "n": 20, "p95_s": 1.172, "p99_s": 1.328, "refusals": 0, "schema_accepted": 0, "schema_n": 0, "timeouts": 0}, "url_extract": {"json_n": 20, "json_valid": 20, "max_tokens_hits": 0, "n": 20, "p95_s": 1.203, "p99_s": 1.969, "refusals": 0, "schema_accepted": 0, "schema_n": 0, "timeouts": 0}, "verdict": {"json_n": 20, "json_valid": 20, "max_tokens_hits": 0, "n": 20, "p95_s": 4.406, "p99_s": 4.438, "refusals": 0, "schema_accepted": 0, "schema_n": 0, "timeouts": 0}}, "stop_reason": null, "tail_n_censored": 0, "tail_n_failed": 0, "tail_span_ms": [7000.0, 5766.0, 7094.0, 6594.0, 5812.0, 5375.0, 5891.0, 6156.0, 5484.0, 5906.0, 5297.0, 4891.0, 5860.0, 5860.0, 5406.0, 6109.0, 5469.0, 5734.0, 6234.0, 6047.0], "timeout_rate": 0.0, "usd": 0.079016}
- text / A2_ttft: {"calls": 40, "error_classes": {}, "hosts_refused": [], "n_censored": 0, "ok": 40, "p50_s": 2.172, "p95_s": 4.532, "p99_s": 4.937, "stop_reason": null, "timeout_rate": 0.0, "ttft_p50_s": 0.703, "ttft_p95_s": 0.906, "usd": 0.031029}
- text / A3_sonnet_between_tools: {"accepted": 20, "calls": 20, "error_classes": {}, "hosts_refused": [], "json_n": 20, "json_valid": 20, "n": 20, "n_censored": 0, "ok": 20, "p50_s": 6.766, "p95_s": 7.719, "p99_s": 8.141, "stop_reason": null, "timeout_rate": 0.0, "usd": 0.360742}
- text / A4_refusal_names: {"calls": 100, "error_classes": {}, "hosts_refused": [], "n": 100, "n_arabic": 31, "n_censored": 0, "n_sensitive": 21, "ok": 100, "p50_s": 1.062, "p95_s": 1.406, "p99_s": 1.766, "refusals": 0, "refusals_arabic": 0, "refusals_sensitive": 0, "stop_reason": null, "timeout_rate": 0.0, "usd": 0.018386}
- text / A5_count_tokens: {"calls": 20, "error_classes": {}, "hosts_refused": [], "n_censored": 0, "ok": 20, "p50_s": 0.281, "p95_s": 0.282, "p99_s": 0.453, "stop_reason": null, "timeout_rate": 0.0, "usd": 0.0}
- text / A6_verdict_eval: {"agreement": 1.0, "calls": 120, "error_classes": {}, "hosts_refused": [], "json_n": 120, "json_valid": 120, "mismatches": 0, "n": 120, "n_censored": 0, "n_scored": 120, "ok": 120, "p50_s": 3.719, "p95_s": 4.359, "p99_s": 4.5, "refusals": 0, "stop_reason": null, "timeout_rate": 0.0, "timeouts": 0, "usd": 0.105764}

## Reported figures (not bars)

- Cost per synthetic compare (an A1 round: the booked usd of its calls from the ledger, nearest-rank over the rounds that completed every call): p50 0.003942 USD, p95 0.004028 USD (n = 20)
- Compares per day under the breaker's live-lane cap (code default, not the production value; recompute with the live value): cap 3.0 USD; floor(cap / p95) = 744, floor(cap / p50) = 761
- cache_read share (cache-read input tokens / all input tokens: uncached + cache creation + cache read; A1 sites, from the ledger): pooled 0.0; classify 0.0, disambiguate 0.0, image_tier3 0.0, parse 0.0, price 0.0, price_training 0.0, reviews 0.0, specs 0.0, specs_synthesized 0.0, specs_targeted 0.0, url_extract 0.0, verdict 0.0
- A4 refusals (the bars are R-S07-23; the sensitive subset is reported, not a bar): all n = 100, refusals = 0; Arabic-script names n = 31, refusals = 0; sensitive-looking names n = 21, refusals = 0
- VISION hit rate = hits / n_scored: successful calls only (a failed call is not scored).
- A6 mismatch rate = mismatches / n_scored: successful calls whose winner_index parsed only.

## Timeout knob proposals (a knob changes only by the owner's dated line)

- ANTHROPIC_CLASSIFY_LLM_TIMEOUT: current 4.0, proposed 2.0 (p99 x 1.25, n = 20, censored 0); current = the code default (a production override is not visible to this run: every ANTHROPIC_* name refuses the start)
- ANTHROPIC_VISION_TIMEOUT_SECONDS: current 20.0, proposed NOT MEASURED (p99 of vision_v2 x 1.25, n = 0, censored 0); current = the code default (a production override is not visible to this run: every ANTHROPIC_* name refuses the start)
- ANTHROPIC_TAIL_RESERVE_SECONDS: current 6.5, proposed 9.0 (p95 of tail_span x 1.25, n = 20, censored 0, rounds excluded for a failed tail leg 0; LLM legs only: no search, no scoring); current = the code default (a production override is not visible to this run: every ANTHROPIC_* name refuses the start)
