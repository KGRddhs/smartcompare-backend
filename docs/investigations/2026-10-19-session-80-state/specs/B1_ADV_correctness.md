# B1 adversary (correctness lens): RESULT-STATUS + TELEMETRY (ENABLE_RESULT_STATUS_METADATA)

Agent: b1-adv-correctness. Window 2026-10-20 05:35 - 06:10 AST. Unit worktree
C:/Users/SynAckITPC/Documents/AI/sc-s80-b1 (never edited), branch feature/s80-b1-result-status, HEAD
2bbd58a9eae6aa172339ee7cc717e875ff2bbc73 verified at the start and at the end; `git status --short` empty
at both points. Every probe and mutant ran in my own detached scratch worktree
<scratchpad>/B1_adv_correctness at 2bbd58a9 (created with `git worktree add --detach`, removed at the end
with `git worktree remove --force`). No .env read, no production / Railway / Supabase / Sentry / network
access; every pytest through pyt.py, one process at a time.

## Verdict: NOT_READY (0 blocking, 2 major, 7 minor)

## RED files (re-hashed at the start and at the end, both equal to the frozen rows)

| file | sha256 |
|---|---|
| tests/test_s80_b1.py | 88130f327757d9e53feb47bbe877f9a065783b2e3a01f90c623360de46a35dfb |
| tests/test_s80_b1_feedback.py | 0bd1117880ac96cee0aee35832814ae7eee620b6bef09bba7b0513648ea59ab3 |

## MAJOR

### MAJ-1 The telemetry message contradicts the stamped body on every category-conflict compare

`sentry_service.capture_result_status` (sentry_service.py:685) calls `assess_result(result)` WITHOUT
`product_categories`; `assess_result` (result_gate.py:485, :506) never reads `metadata.product_categories`
from the body, so `identity_coherence(None, ...)` is always True in the telemetry path. The builder's stamp
(response_builder.py:2275) passes the categories. Result, MEASURED at runtime on the GREEN bytes:

- a1 (builder body, lane1 grocery data, `product_categories=["electronics","fragrances"]`, flag ON):
  body `metadata.result_status = unsupported_category`, `identity_confidence = low`,
  `overview.winner.supported = False`; the ONE `comparison_result_status` message carries
  `result_status=supported_result`, `reasons=none`, `identity_confidence=high`, `winner_emitted=true`.
- a2 (the R16 vision pair "Samsung Galaxy S24 phone" / "Dior Sauvage eau de parfum" through the REAL
  orchestrator, then the REAL camera route `POST /api/v1/image/identify`, flag ON): HTTP 200,
  `action=comparison`, body `result_status=unsupported_category`, `supported=False`,
  `product_categories=["electronics","fragrances"]`; message tags `result_status=supported_result`,
  `reasons=none`, `winner_emitted=true`.

Consequence: in the Sentry stream the status `unsupported_category` is UNREACHABLE (category_used is always
one of the nine, the only other route to it), `category_conflict` never appears in `reasons`, and every
cross-category camera scan (the MYEZ-001 / CAMERA-SPOT class this flag exists to size) is counted as a
crowned `supported_result` with `identity_confidence=high`. The CLAUDE.md row's canary ("the
comparison_result_status messages grouped by the result_status x input_type tags") and the PR body's
MYEZ-011 mapping (r12 / r16 = category conflict) therefore measure the wrong number for that reason, while
the stored row says the opposite. The spec (2.5 "recomputed from the body, never read from metadata")
designed the gap; no RED row checks telemetry == stamp on a conflict body (R17/R18 use same-category
supported bodies; R17b's reasons carry no category_conflict).
Fix suggestion (one line, flag-ON only): in `capture_result_status`, pass
`product_categories=(result.get("metadata") or {}).get("product_categories")` to `assess_result` (the body
field, present only when stamped), plus a RED row asserting the message tags equal the stamped
`result_status` / `reasons` / `identity_confidence` on the a1/a2 bodies.
Probe: tests/test_zz_b1adv_probe.py::test_a1/test_a2 (scratch only) ->
`[pyt] tag=b1adv-probe start=2026-10-20 05:43:41 end=2026-10-20 05:43:47 elapsed=7s bound=600s status=OK rc=0`
(`[hermeticity] sentinel checked 4 test(s)`, `[netguard] blocked 0 attempt(s) from 0 node(s)`); values in
<scratchpad>/B1_adv/probe_out.json.

### MAJ-2 Binding ruling B1-R11 Q7 (profile recent decisions) is not implemented

RULINGS_BATCH1 B1-R11 Q7: "apply the same result_status skip to profile_routes.py:75/:97/:141 in this unit
with a P8-style pin" (binding for RED and GREEN). At HEAD profile_routes.py:75, :97, :141 still read the
top-level `winner_index` with no `result_status` check, so under the flag a stamped non-supported row
(placeholder / same identity / no evidence) is still presented as a decision on the profile surface
(MYEZ-027 not closed there). GREEN disclosed it (deviation 1; CLAUDE.md row and PR body stated limit) and
asked for a ruling, because the frozen RED files carry no row. Resolution needs the orchestrator: either a
fix round (a RED row + the reader hunk) or an explicit amendment of B1-R11 Q7 deferring it to C1. Until one
of the two exists, the bytes do not meet a binding ruling.

## MINOR (documentation rulings for the orchestrator)

- min-1 CLAUDE.md row: "`/home/savings` and `/home/smart-pick` skip stamped non-supported rows" is true only
  on the legacy Python savings path. With `ENABLE_HOME_SAVINGS_AGGREGATE` ON (home_routes.py:235-240, the
  #116 RPC over migration 036) the server aggregate counts stamped rows. Both are OFF / unapplied today; the
  row should say "legacy path only" (spec section 10 says so, the row does not).
- min-2 CLAUDE.md row and PR body: "the tags are recomputed from the body, never read from `metadata`" is
  not literally true (the emitter reads `metadata.elapsed_ms`, `metadata.partial`, `metadata.partial_stage`)
  and, as worded, hides MAJ-1; rewrite with the MAJ-1 fix.
- min-3 Spec mutation table X19 says "killed by R8". MEASURED: R8 does NOT kill X19 (the Manama raw prices
  are `estimated`, unshowable before and after the chokepoint); the killer is
  test_b1_r9_builder_stamps_lane1_supported[grocery|iphone15_vs_galaxys24|now_vs_solgar|tomford_vs_creed]
  through its `section_status["price"]` assertion (tests/test_s80_b1.py:561). R9's `data_coverage >= 3`
  half admits the inflated 4, so the kill rests on section_status alone. The PR body / mutation record
  should cite R9.
- min-4 (ruling question) The AUDITABLE spec fact excludes only `_field_confidence == "tier3_synthesis"`
  (result_gate.py TIER3_MARKER). Fields lifted as `training_data` (scs `_clean_specs`, the specs prompt's
  training-data fallback) and `smart_fallback` / `tier2_fallback` count as auditable evidence. R-A4 says
  "Tier-3 synthesized specs (model knowledge) do not count"; `training_data` is model knowledge too.
  Frequency NOT MEASURED. Matches spec 2.2 / R0-5 as written, so a ruling, not a GREEN defect.
- min-5 Flag ON overrides an explicit UNSAMPLED parent on the four compare paths (measured through the real
  SDK: parent `-0` -> 40/40 sampled at rate 1.0), so backend compare transactions are recorded under client
  traces the RN SDK dropped (partial traces); and each delivered compare also sends one `info` message
  event, which counts against the Sentry error-event quota. The owner step / canary mentions only the
  transaction quota. Stated-limit wording only (R21 asks for 1.0 regardless of parent).
- min-6 Unpinned GREEN behaviour (mutants that survive the frozen unit files; behaviour correct by
  inspection, so pins are suggestions): X18s (the STREAM capture point before the write-back: R15's stream
  pair is same-category), X22a (the image_routes.py:598 site gate: the emitter's own success gate makes it
  redundant), M16 (the camera route's measured `compare_ms` argument: indistinguishable from the
  `metadata.elapsed_ms` fallback), M11 (the `metadata.partial is True` precondition on the `partial_stage`
  tag), M9 (the non-str filter on `product_categories`; equivalent in production, every element comes from
  `canonicalize_category`).
- min-7 GREEN report wording: result_gate.py is committed LF (25797 B, sha 48bcbb7d...) but a fresh
  checkout with core.autocrlf=true writes it CRLF (26417 B in my scratch tree, 620 CRLF, 0 bytes > 127);
  index content identical. Information for the engineering lens only.

## Runtime truth checks that PASSED (the claims the brief named)

- Flag-OFF identity: unit files OFF 214/214 (P1 base-literal digests, P2 nine FY25 digests with the flag
  set to the falsy values, P3 timings, P4 no message on any exit, P5 sampler); the 20-file pin set OFF
  1283 passed (FY25, W4-13 ledger + truth, stage_timings, U13 T17/T23, metering, retro_w2_1, U8d x2,
  observability, retro_w1_1, history, home, profile, feedback x3, comparison_id_echo, the two CLAUDE.md
  readers, the unit files).
- Sampler against sentry-sdk 2.68.1 (venv = pin): with the flag OFF, 360 transactions started through the
  REAL SDK (`continue_trace` + `start_transaction(custom_sampling_context={"asgi_scope": ...})`, three
  paths x parent none/-1/-0 x 40 trace ids) give the SAME `sampled` and `sample_rate` with
  `traces_sampler=compare_traces_sampler` as with no sampler (0 differences; 132 sampled). The SDK calls the
  sampler at tracing.py:1215-1217 and its default branch (:1229-1233) is what the OFF branch reproduces.
  Flag ON: the four compare paths 1.0 for every parent state; /api/v1/health keeps parent / 0.1 (4/40).
- The message through the REAL SDK + `_before_send` (capturing transport, synthetic DSN built at run
  time): one event, `message=comparison_result_status`, `level=info`, all 15 tags intact, `extra`
  {vision_ms 1234, compare_ms 8765} (plus the SDK's default `sys.argv` extra, pre-existing on every event),
  no `[RESULT_STATUS]` WARNING. `capture_message(**scope_kwargs)` -> `Scope.update_from_kwargs` accepts
  `extras` and `tags` on 2.68.1 (scope.py:1993-2001).
- Error-handler mapping: B1 adds no code and no envelope; the off-enum `winner_correct` 422 goes through
  the existing VALIDATION_ERROR envelope (F4 green; X33/M6 killed by F3/F5). No bare 503.
- Billing R-A3: nothing abstains in B1; every emitter call sits after the metering / save / lifetime block
  and before `return`; the camera unsuccessful path emits nothing in all three metering x envelope states
  (R18b; X22b killed); the stream emits only inside the CD-interactions-01 gate (X23 killed by R19/R17);
  the stamped body still passes `database_service._validate_renderable` (it reads only products + query),
  so a stamped non-supported text/camera row is saved and billed as today. The flag-ON 20-file run (1069
  passed) includes the W4-13 ledger and the metering pins.
- Contract freeze (PLAN section 0): every write is an additive key (`metadata.*`, `overview.winner.supported`);
  the crown keys never move (P6; M17/M18 killed by P6); the client (SmartCompareApp/src, grep) reads none
  of the new keys and reads `winner_index` only from the top level / overview / the history list item,
  which HistoryScreen types `0 | 1 | null` (HistoryScreen.tsx:60, :442) -- the CR1 null case accepted by
  B1-R12. `_strip_inference_markers` runs after the stamp; the tier-3 markers are read before it.
- The stamp's try/except: `overview.winner` and `metadata` are always dicts at that point
  (response_builder.py:1903-1911 assembly), and every value is computed before the first write, so the
  partial-write window the 2.12 table worries about cannot open in practice (X35 killed by P13).
- `canonicalize_category` is total (extraction_service.py:1227-1228: non-str -> "other"), so the two
  unconditional OFF-state captures (scs:4288, :4921) cannot raise where base did not.

## Mutation run (GREEN bytes, scratch worktree, `.qa-mutation.lock` held and removed; each mutant on a
## byte copy, exact edits matching once (CRLF-aware), both unit files via pyt.py bound 600, restored from
## the copy and sha256-compared: 42/42 restores ok)

Spec mutants applied: X1, X2, X5, X8, X10, X12, X15, X17, X18, X19 (by hand, GA-4), X20, X22 (as X22a site
only / X22b site + emitter gate), X23, X24, X25, X26, X27, X28, X30, X31, X33, X35 (22) + the stream variant
X18s + 18 own mutants M1-M18 on GREEN code. 42 applied, 37 KILLED (AssertionError in every killing log
except X35, whose row injects a ValueError that the mutant no longer catches, and M8's R18 KeyError beside
an AssertionError in R20), 5 SURVIVED (X18s, X22a, M9, M11, M16; min-6).

X19 hand mutant: snapshot `[dict(price) ...]` of every product price immediately before
`_guard_rejected_diag = []` (the head of the builder's price chokepoint, response_builder.py ~:1622) and
assess a copy of `result` whose `products[i]["price"]` are those pre-chokepoint prices. KILLED by
test_b1_r9_builder_stamps_lane1_supported[*] x4 (tests/test_s80_b1.py:561, `section_status["price"]`
'available' == 'unavailable'); not by R8 (min-3).

| id | mutant | result | failed | killing rows | restore | [pyt] |
|---|---|---|---|---|---|---|
| X1 | flag default true | KILLED | 15 | P13, P1[*], P2[*], P3, P4 | ok | `[pyt] tag=b1adv-mut-X1 start=2026-10-20 05:45:50 end=2026-10-20 05:46:00 elapsed=10s bound=600s status=FAIL rc=1` |
| X2 | flag read once at import | KILLED | 54 | R1[*], P12, P13, R10 | ok | `[pyt] tag=b1adv-mut-X2 start=2026-10-20 05:46:00 end=2026-10-20 05:46:10 elapsed=10s bound=600s status=FAIL rc=1` |
| X5 | same_identity ignores the brand | KILLED | 11 | R3[*], R9[*], R12 | ok | `[pyt] tag=b1adv-mut-X5 start=2026-10-20 05:46:10 end=2026-10-20 05:46:20 elapsed=9s bound=600s status=FAIL rc=1` |
| X8 | price_is_showable accepts estimated | KILLED | 1 | R5[price0] | ok | `[pyt] tag=b1adv-mut-X8 start=2026-10-20 05:46:20 end=2026-10-20 05:46:30 elapsed=9s bound=600s status=FAIL rc=1` |
| X10 | real_spec_rows counts N/A | KILLED | 6 | R6, R8[12,13], R10b, R14 | ok | `[pyt] tag=b1adv-mut-X10 start=2026-10-20 05:46:30 end=2026-10-20 05:46:39 elapsed=9s bound=600s status=FAIL rc=1` |
| X12 | dim margin dropped | KILLED | 7 | R7, R8, R10b, R15, R17 | ok | `[pyt] tag=b1adv-mut-X12 start=2026-10-20 05:46:40 end=2026-10-20 05:46:49 elapsed=9s bound=600s status=FAIL rc=1` |
| X15 | winner_index None on every body | KILLED | 10 | R9[*], R13[*], R15 | ok | `[pyt] tag=b1adv-mut-X15 start=2026-10-20 05:46:49 end=2026-10-20 05:46:58 elapsed=9s bound=600s status=FAIL rc=1` |
| X17 | section_status available on one side | KILLED | 2 | R9[now_vs_solgar], C9e | ok | `[pyt] tag=b1adv-mut-X17 start=2026-10-20 05:46:58 end=2026-10-20 05:47:07 elapsed=9s bound=600s status=FAIL rc=1` |
| X18 | categories captured after the write-back (REST) | KILLED | 2 | R15, R16 | ok | `[pyt] tag=b1adv-mut-X18 start=2026-10-20 05:47:08 end=2026-10-20 05:47:16 elapsed=9s bound=600s status=FAIL rc=1` |
| X18s | categories captured after the write-back (stream) | SURVIVED | 0 | - | ok | `[pyt] tag=b1adv-mut-X18s start=2026-10-20 05:47:17 end=2026-10-20 05:47:26 elapsed=9s bound=600s status=OK rc=0` |
| X19 | assessment reads PRE-chokepoint prices (hand) | KILLED | 4 | R9[*] (section_status.price, :561) | ok | `[pyt] tag=b1adv-mut-X19 start=2026-10-20 05:47:26 end=2026-10-20 05:47:35 elapsed=9s bound=600s status=FAIL rc=1` |
| X20 | telemetry with the flag OFF | KILLED | 4 | P3[*], P4[*] | ok | `[pyt] tag=b1adv-mut-X20 start=2026-10-20 05:47:36 end=2026-10-20 05:47:45 elapsed=9s bound=600s status=FAIL rc=1` |
| X22a | camera site gate dropped (emitter gate kept) | SURVIVED (equivalent) | 0 | - | ok | `[pyt] tag=b1adv-mut-X22a start=2026-10-20 05:47:45 end=2026-10-20 05:47:56 elapsed=11s bound=600s status=OK rc=0` |
| X22b | site gate AND emitter success gate dropped | KILLED | 1 | R18b[None-None] | ok | `[pyt] tag=b1adv-mut-X22b start=2026-10-20 05:47:58 end=2026-10-20 05:48:07 elapsed=10s bound=600s status=FAIL rc=1` |
| X23 | stream telemetry outside the client-gone gate | KILLED | 2 | R19, R17 | ok | `[pyt] tag=b1adv-mut-X23 start=2026-10-20 05:48:08 end=2026-10-20 05:48:17 elapsed=10s bound=600s status=FAIL rc=1` |
| X24 | camera timings with the flag OFF | KILLED | 3 | P3[*], R20b | ok | `[pyt] tag=b1adv-mut-X24 start=2026-10-20 05:48:18 end=2026-10-20 05:48:27 elapsed=9s bound=600s status=FAIL rc=1` |
| X25 | camera timings create the dict | KILLED | 2 | R20[absent], R20b | ok | `[pyt] tag=b1adv-mut-X25 start=2026-10-20 05:48:27 end=2026-10-20 05:48:37 elapsed=10s bound=600s status=FAIL rc=1` |
| X26 | sampler 1.0 with the flag OFF | KILLED | 16 | P5[*] | ok | `[pyt] tag=b1adv-mut-X26 start=2026-10-20 05:48:37 end=2026-10-20 05:48:47 elapsed=10s bound=600s status=FAIL rc=1` |
| X27 | sampler path set lacks the stream | KILLED | 2 | R21[*-stream] | ok | `[pyt] tag=b1adv-mut-X27 start=2026-10-20 05:49:14 end=2026-10-20 05:49:24 elapsed=9s bound=600s status=FAIL rc=1` |
| X28 | sampler ignores parent_sampled | KILLED | 37 | P5[*], P5b[*], R21[*] | ok | `[pyt] tag=b1adv-mut-X28 start=2026-10-20 05:49:24 end=2026-10-20 05:49:34 elapsed=10s bound=600s status=FAIL rc=1` |
| X30 | home skip keyed on metadata.winner_index | KILLED | 2 | R22, R23 | ok | `[pyt] tag=b1adv-mut-X30 start=2026-10-20 05:49:34 end=2026-10-20 05:49:44 elapsed=10s bound=600s status=FAIL rc=1` |
| X31 | home skip when result_status absent | KILLED | 2 | P8, R22 | ok | `[pyt] tag=b1adv-mut-X31 start=2026-10-20 05:49:44 end=2026-10-20 05:49:54 elapsed=10s bound=600s status=FAIL rc=1` |
| X33 | save_feedback writes the key when None | KILLED | 7 | F3[*], F5 | ok | `[pyt] tag=b1adv-mut-X33 start=2026-10-20 05:49:54 end=2026-10-20 05:50:04 elapsed=10s bound=600s status=FAIL rc=1` |
| X35 | assess raise not caught | KILLED (ValueError) | 1 | P13 | ok | `[pyt] tag=b1adv-mut-X35 start=2026-10-20 05:50:04 end=2026-10-20 05:50:14 elapsed=10s bound=600s status=FAIL rc=1` |
| M1 | REST partial ctx loses product_categories | KILLED | 1 | R15 | ok | `[pyt] tag=b1adv-mut-M1 start=2026-10-20 05:50:14 end=2026-10-20 05:50:25 elapsed=10s bound=600s status=FAIL rc=1` |
| M2 | partial build passes None | KILLED | 1 | R15 | ok | `[pyt] tag=b1adv-mut-M2 start=2026-10-20 05:50:25 end=2026-10-20 05:50:41 elapsed=16s bound=600s status=FAIL rc=1` |
| M3 | stream build drops product_categories | KILLED | 1 | R15 | ok | `[pyt] tag=b1adv-mut-M3 start=2026-10-20 05:50:41 end=2026-10-20 05:50:52 elapsed=10s bound=600s status=FAIL rc=1` |
| M4 | URL telemetry drops compare_ms | KILLED | 1 | R18 | ok | `[pyt] tag=b1adv-mut-M4 start=2026-10-20 05:50:52 end=2026-10-20 05:51:02 elapsed=10s bound=600s status=FAIL rc=1` |
| M5 | sampler fallback ignores the live client rate | KILLED | 3 | P5b[*] | ok | `[pyt] tag=b1adv-mut-M5 start=2026-10-20 05:51:02 end=2026-10-20 05:51:16 elapsed=14s bound=600s status=FAIL rc=1` |
| M6 | feedback route drops winner_correct | KILLED | 3 | F3[*-winner_correct] | ok | `[pyt] tag=b1adv-mut-M6 start=2026-10-20 05:51:17 end=2026-10-20 05:51:39 elapsed=23s bound=600s status=FAIL rc=1` |
| M7 | smart pick skip removed | KILLED | 1 | R23 | ok | `[pyt] tag=b1adv-mut-M7 start=2026-10-20 05:51:40 end=2026-10-20 05:51:57 elapsed=18s bound=600s status=FAIL rc=1` |
| M8 | camera vision_ms never measured | KILLED | 2 | R18, R20[dict] | ok | `[pyt] tag=b1adv-mut-M8 start=2026-10-20 05:51:58 end=2026-10-20 05:52:15 elapsed=16s bound=600s status=FAIL rc=1` |
| M9 | product_categories non-str kept | SURVIVED (equivalent in prod) | 0 | - | ok | `[pyt] tag=b1adv-mut-M9 start=2026-10-20 05:52:17 end=2026-10-20 05:52:40 elapsed=23s bound=600s status=OK rc=0` |
| M10 | identity_confidence ignores an empty brand | KILLED | 5 | R13[*], R15 | ok | `[pyt] tag=b1adv-mut-M10 start=2026-10-20 05:52:40 end=2026-10-20 05:52:49 elapsed=9s bound=600s status=FAIL rc=1` |
| M11 | partial_stage tag ignores metadata.partial | SURVIVED | 0 | - | ok | `[pyt] tag=b1adv-mut-M11 start=2026-10-20 05:52:50 end=2026-10-20 05:53:02 elapsed=12s bound=600s status=OK rc=0` |
| M12 | savings skip removed | KILLED | 1 | R22 | ok | `[pyt] tag=b1adv-mut-M12 start=2026-10-20 05:53:02 end=2026-10-20 05:53:13 elapsed=11s bound=600s status=FAIL rc=1` |
| M13 | `supported` written wrong | KILLED | 5 | R8[*], R10[*] | ok | `[pyt] tag=b1adv-mut-M13 start=2026-10-20 05:53:14 end=2026-10-20 05:53:25 elapsed=11s bound=600s status=FAIL rc=1` |
| M14 | data_coverage_literal stamped as data_coverage | KILLED | 3 | R8[*] | ok | `[pyt] tag=b1adv-mut-M14 start=2026-10-20 05:53:25 end=2026-10-20 05:53:47 elapsed=21s bound=600s status=FAIL rc=1` |
| M15 | telemetry winner_emitted always true | KILLED | 1 | R17b | ok | `[pyt] tag=b1adv-mut-M15 start=2026-10-20 05:53:47 end=2026-10-20 05:53:58 elapsed=11s bound=600s status=FAIL rc=1` |
| M16 | camera call without compare_ms | SURVIVED (near-equivalent) | 0 | - | ok | `[pyt] tag=b1adv-mut-M16 start=2026-10-20 05:53:58 end=2026-10-20 05:54:12 elapsed=14s bound=600s status=OK rc=0` |
| M17 | the stamp sets top-level winner_index None | KILLED | 6 | P6, R8[*], R10[*] | ok | `[pyt] tag=b1adv-mut-M17 start=2026-10-20 06:02:06 end=2026-10-20 06:02:17 elapsed=12s bound=600s status=FAIL rc=1` |
| M18 | the stamp edits overview.winner.product_index | KILLED | 4 | P6, R8[*] | ok | `[pyt] tag=b1adv-mut-M18 start=2026-10-20 06:02:18 end=2026-10-20 06:02:28 elapsed=11s bound=600s status=FAIL rc=1` |

## Prove-nothing rows (on the GREEN bytes)

- P7 `test_b1_p7_history_list_null_neutral_for_stamped_row`: pins history_routes behaviour B1 does not
  touch (green at base, no B1 symbol on its path); a contract pin, it cannot kill any B1 mutant.
- R18b's camera-site half: X22a survives -- image_routes.py:598 is redundant with the emitter's own
  success gate (deviation 2), so no row proves the site gate.
- R15's stream half vs the capture point: X18s survives (same-category FY25 pair).
- R18's camera `compare_ms`: M16 survives (the route wall vs `metadata.elapsed_ms` are indistinguishable).
- R14's `partial_stage` tag: M11 survives (no body with `partial_stage` and `partial` not True).
- R8 as the X19 killer named by the spec (min-3): it passes under X19.
- No row asserts the message tags equal the stamped status (MAJ-1).

## Runs ([pyt] lines verbatim; hermeticity / netguard lines with them)

- Unit ON (flag exported on the runner call; the autouse fixture still delenvs it per row): 214 passed |
  `[pyt] tag=b1adv-unit-on start=2026-10-20 05:40:43 end=2026-10-20 05:40:56 elapsed=12s bound=600s status=OK rc=0`
  | `[hermeticity] sentinel checked 214 test(s)` | `[netguard] blocked 0 attempt(s) from 0 node(s)`
- Unit OFF: 214 passed | `[pyt] tag=b1adv-unit-off start=2026-10-20 05:40:56 end=2026-10-20 05:41:08 elapsed=12s bound=600s status=OK rc=0`
  | `[hermeticity] sentinel checked 214 test(s)` | `[netguard] blocked 0 attempt(s) from 0 node(s)`
- Probes a1/a2/b1/b2: 4 passed | `[pyt] tag=b1adv-probe start=2026-10-20 05:43:41 end=2026-10-20 05:43:47 elapsed=7s bound=600s status=OK rc=0`
  | `[hermeticity] sentinel checked 4 test(s)` | `[netguard] blocked 0 attempt(s) from 0 node(s)`
- Probe c1 (real SDK + before_send): 1 passed, 4 deselected |
  `[pyt] tag=b1adv-probe2 start=2026-10-20 06:01:01 end=2026-10-20 06:01:07 elapsed=6s bound=600s status=OK rc=0`
  | `[hermeticity] sentinel checked 1 test(s)` | `[netguard] blocked 0 attempt(s) from 0 node(s)`
- Pin set flag OFF (22 files incl. the unit files): 1283 passed |
  `[pyt] tag=b1adv-ciorder-off start=2026-10-20 05:58:43 end=2026-10-20 05:59:38 elapsed=55s bound=1200s status=OK rc=0`
  | `[hermeticity] sentinel checked 1283 test(s)` | `[netguard] blocked 20 attempt(s) from 4 node(s)` (the base
  baseline class: test_paid_route_metering x2 sentinel neutralized.supabase.invalid:443; test_stage_timings x2
  egress api.openai.com:443 -- the same four nodes GREEN recorded)
- Pin set flag ON (20 files, information): 1069 passed |
  `[pyt] tag=b1adv-ciorder-on start=2026-10-20 05:59:47 end=2026-10-20 06:00:30 elapsed=43s bound=1200s status=OK rc=0`
  | `[hermeticity] sentinel checked 1069 test(s)` | `[netguard] blocked 20 attempt(s) from 4 node(s)` (same four)
- 42 mutant runs: the table above (each `bound=600s`; none TIMEOUT).

NOT MEASURED: the comm set and ruff / py_compile / hook files (engineering lens); the frequency of
`training_data`-marked spec fields in production (min-4); a text-route conflict probe (same function as a1).

## Files written (all under <scratchpad>/B1_adv, ASCII, LF)

notes.md, test_zz_b1adv_probe.py (copied into the scratch worktree only), mutate.py, probe_out.json,
probe_out2.json, mutants_batch1/2/3.json, mutant_lines.txt, unit_on.log, unit_off.log, probe*.log,
ciorder_off.log, ciorder_on.log, mut_*.log, this report. Nothing written in sc-s80-b1.

## End state

sc-s80-b1: HEAD 2bbd58a9, `git status --short` empty, RED hashes equal the frozen rows. Scratch worktree
removed (`git worktree remove --force`), `git worktree list` carries no B1_adv entry, no .qa-mutation.lock
left, no pytest process of mine alive (every run was synchronous through pyt.py).
