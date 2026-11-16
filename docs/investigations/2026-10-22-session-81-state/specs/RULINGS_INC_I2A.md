# RULINGS INC-I2a PICTURE-NOT-CUT (S96 orchestrator, 2026-11-16 about 22:30 AST)

Draft spec s96/i2a/spec/INC_I2A_UNIT_SPEC.md (wf_a87336e8-257, Opus 5.5) and its spec review INC_I2A_SPEC_REVIEW.md (verdict AMEND). These rulings are binding. Where they differ from the draft, they win.

## Class
- R-1 (Q1, B9) FOCUS: the unit adds a new Redis key family. So TWO adversaries after GREEN: (1) correctness and concurrency (tasks, cancels, drains, the bind, the stream and sync parity); (2) Redis, cost and production behaviour (the key family, the TTL, the off-loop pool load, the credit accounting, the log lines, the flag-mix walk against production with G ON, S ON, R OFF and ON). There is no further spec review: this review was the Opus spec review.

## The open questions
- R-2 (Q2) APPROVED: under the flag, the page-image override moves to the bind point after reconcile_pair_fairness, so it reads the POST-swap price (V2 missed point 8). OFF keeps the override where it is today.
- R-3 (Q3) KEEP the fallback: ON never shows fewer pictures than OFF. Stated limit: the fallback picture can be another bottle size of the same product.
- R-4 (Q4) Defaults accepted: IMAGE_LATE_BIND_RESERVE_SECONDS 2.0, IMAGE_LATE_BIND_MAX_WAIT_SECONDS 3.0, IMAGE_LATE_MAX_SECONDS 20.0, IMAGE_PICK_CACHE_TTL_SECONDS 604800 (7 days). Each is read per call with the house parsing: finite positive, else the default; clamp the job bound to at most 30.
- R-5 (Q5) The spec must not depend on the production value of STREAM_HARD_CAP_SECONDS. The bind residual comes from the run's own deadline. Rows cover a 25 s and a 30 s cap. The orchestrator is asked for the names-only reading separately.
- R-6 (Q6) CONFIRMED: no cache read or write unless ENABLE_IMAGE_RELEVANCE_GUARD is ON and the product is not a camera product.
- R-7 (Q7) No KB seeding.
- R-8 (Q8) The RED agent greps scripts/, tests/ and docs/ for Redis key-prefix enumerations (flush or purge lists) and reports them. The unit adds `imgpick:` to any list it finds, or states that none exists.
- R-9 (Q9) Merge order with the data lane's INC-P2 is the orchestrator's call; the second to merge rebases. The spec lists the exact SCS regions it edits (function and anchor text, not line numbers) so the rebase is mechanical.

## The review findings
- R-10 (A1) ACCEPTED: the cascade awaits asyncio.shield(fut); both set sites use `if not fut.done(): fut.set_result(...)`; IMAGE_LATE_MAX_SECONDS is stated against the unified-search bound. RED row: bound 0.2 s, unified fake 0.5 s, Serper miss; the compare succeeds with no InvalidStateError and nothing is logged at ERROR.
- R-11 (A2) ACCEPTED: the drain runs the bind's synchronous chain on the current price: the override hit, else the done job, else the Phase-1 page image. Parity row on BOTH the sync and stream partials: the page image is present, the job is pending, and a cap fires during the verdict; ON carries the picture exactly as OFF does.
- R-12 (A3) ACCEPTED: the cache name adds the folded concentration (the variant minus size and unit tokens). E19: EDT != EDP; 100ml == 50ml; equal across slot 0 and slot 1; with R ON and with R OFF (a typed full name and a resolved line give the same name when they name the same product, or the spec states they do not).
- R-13 (A4) ACCEPTED: on read, require a dict value, https, `deny_hosts.is_denied_url` false and `_is_valid_image_url`. The key prefix carries a guard-rules version: `imgpick:v1:<g>:` where `<g>` is the first 8 hex digits of a sha256 pinned by a row over the source of image_relevance.check, _check_short_line, identity and the RelevanceCall accept methods. Any guard edit (INC-I2b next) then fails that row, and the unit that edits the guard bumps it. Rows: a denied-host hit (DATA_GUARDS_V2 OFF), an http value and a non-dict value are each a miss.
- R-14 (B1) ACCEPTED: evaluate the override first and wait only on the products whose override misses; return early on an empty registry.
- R-15 (B2) ACCEPTED: the bind sits just before the `elapsed =` line at both sites, still after the verdict.
- R-16 (B3) ACCEPTED: new lines use the prefix IMG_LATE (filterable in plain words): `IMG_LATE bind product=<0|1> outcome=<attached|cached|override|fallback|missed_at_deadline|none> wait_ms=<n>`, `IMG_LATE job product=... outcome=<accepted|none|cancelled|timeout|error> ms=<n> stored=<0|1>`, `IMG_LATE page_override outcome=<hit|skipped|fallback> product=...`. The closed X2a IMG_TIER grammar is unchanged. E11 cancels at each new await point.
- R-17 (B4, B5, B7, B8) ACCEPTED as the review states: E13 caps during Phase 1; E1 stamps the credit or search fake; store_failed is logged on a False return and stored only on True; error is reachable only through a raising fake; every listed mutant joins the table; P4 asserts source_trace.products[i].races.image exists with the flag ON.
- R-18 (B6) DECIDED: the late job never runs the llm_pick tier after the bind. Tier 3 runs only inside the request's own life. That also keeps the stopped OpenAI path out of a background job. Row: a pending job past the bind with organic results makes zero llm_pick calls.

## The guard version and INC-I2b
- R-19 INC-I2b (the guard words and the free shop-image tier) follows this unit and edits image_relevance.py, so it bumps `<g>` by the R-13 row. Stated in both specs.
