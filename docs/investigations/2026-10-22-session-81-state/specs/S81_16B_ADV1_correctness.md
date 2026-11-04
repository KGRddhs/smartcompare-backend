# S81-16b KB-BRANDS adversary report, lens: correctness (Opus 5.5, 2026-11-04)

Verdict: SOUND (no blocking, no major; 7 minors as stated-limit / documentation candidates, LC-4).
The body was written with the Write tool (a heredoc over ~7 KB is refused by this box's Bash tool) and then normalised and checked through the shell with python (ASCII, LF).

## Exact bytes
- Worktree sc-s81-s16b HEAD 28eec42b2055920604acb1e4ef9765fe74126625 verified first and last; `git status --short` empty first and last; never edited.
- Frozen RED tests/test_s81_s16b_kb_brands.py sha256 cd67db3bd75d90ae90eeb90ce48c90aac4bb9131ac8e99753e99b36738b75cbd first and last (on disk and the HEAD blob).
- The nine files on disk == the GREEN report's after-hashes (fef8ec19 052, 766cff1c rollback 052, b9c25bc1 leaf, e1bb9d46 common, 61c54417 script, 234da82c schema test, 9f6f0209 s16 test, cd67db3b RED, 8b0725bc CLAUDE.md).
- Scratch worktree `git worktree add --detach <scratchpad>/S81-16b_adv_correctness 28eec42b` (no junction). core.autocrlf=true checked the three LF-only new files (052, rollback 052, the RED file) out as CRLF there (RED on-disk sha 16bac1b0...); the three were byte-copied from sc-s81-s16b so all nine files were sha-identical to the worktree before any run; restored and sha-verified after the mutants; lock created and removed; the scratch worktree removed (`git worktree list` shows none, folder gone); no orphan pytest.

## Runs ([pyt] lines)
- RED file OFF (flags unset): 129 passed; netguard 0. `[pyt] tag=s16b-advc-red-off elapsed=17s bound=600s status=OK rc=0`
- ON (ENABLE_KB_BRANDS=apply KB_BRANDS_MAX=1 ENABLE_KB_SEED=apply for that one call): RED + test_s81_s16_kb_seed.py + test_s81_kb_schema.py + test_s81_g2_gate_rows.py: 802 passed / 5 failed = exactly the five environmental G2 R27 CRLF nodes. `[pyt] tag=s16b-advc-red-on elapsed=26s bound=600s status=FAIL rc=1`
- OFF: test_s81_s16_kb_seed.py + test_s81_kb_schema.py + test_s81_g2_gate_rows.py: 673 passed / the same 5 R27 CRLF nodes (G2 R02 / R23 / R24, E1, EK0-EK2 green). `[pyt] tag=s16b-advc-erows-off elapsed=28s bound=1200s status=FAIL rc=1`
- R27 re-checked in-process on the LF HEAD blobs of kb_seed_common.py and seed_kb_brands_wikidata.py (no CR, ASCII, no hygiene token, no `.table('kb_` in the script): clean.
- The seven migration readers + the five CLAUDE.md readers: 649 passed (= GREEN's 168 + 481). `[pyt] tag=s16b-advc-readers elapsed=57s bound=1200s status=OK rc=0` (netguard: the 24 neutralized.supabase.invalid attempts from 2 s04 nodes that GREEN recorded as D7; both passed; unrelated).
- PIN-1..6 green in both RED runs.

## Mutants (sha-verified byte copies in the scratch worktree; targets = the RED file + the two E-row files; kill = a failing node beyond the 5 R27 baseline nodes; every kill an AssertionError only)
Spec mutants 20 / 20 KILLED: M01 (7 nodes: s07, s08), M02 (s05 x2, s10[update]), M03 (s05 x2), M04 (k01, s05), M06 (k03[host-rule-only], k05), M08 (r23[true], s03, s04), M09 (34 nodes), M10 (8 nodes incl. s14_p02), M13 (s03, s06), M14 (b04, k01, k03), M16 (29 nodes incl. r02, s02), M18 (s04), M21 (b07), M23 (b03, b04), M27 (s06), M28 (s10 x2), M29 (12 nodes: r27 + k01), M31 (s04 x2, s06), M32 (11 nodes), M33 (s03, s04 x2, s06).
Adversary extras 15 / 18 KILLED: X01 builder strip rule dropped (k03 blank / lead / trail rows), X02 writer counters added only on success, no finally (s10[update]), X04 with_label_en counted per binding (s03), X05 update not filtered on qid (s05 x2), X06 brand_updates bumped before the call (s10[update]), X07 string ORDER BY (s03), X08 sparql_limit_hit never set (s09), X09 label bound 256 (k03, s06), X10 report carries source (s03, s04), X11 script does not strip labels (s06), X12 label_ar btrim dropped from the SQL (b03, b04), X13 RLS line removed (b05), X15 write_failed not set (s10 x2), X16 human exclusion removed (s03), X18 builder accepts any source (k03[source-manual]).
SURVIVED: X03, X14, X17. The code is correct on each (measured by probe); the frozen rows do not pin them (minors m1-m3).
Logs: <scratchpad>/S81-16b_adv/mutants/<id>.log and results.json; driver output <scratchpad>/S81-16b_adv/mutants_driver.out; harness <scratchpad>/S81-16b_adv/probes/mutate_adv.py.

## Runtime probes (<scratchpad>/S81-16b_adv/probes/probe1.py; fetcher and client faked; no network; no .env in the scratch worktree)
- Flag-OFF inertness: 14 OFF spellings (unset, '', blanks, false, 0, no, off, dry, DRY, garbage, apply2, applied, Off, n) x ENABLE_KB_SEED {unset, true, apply} = 42 cases through main(['--corpus', 'x', '--report', f], client=None). Every case: rc 0, 0 client-factory calls, 0 fetches, 0 open() calls, argv never parsed. apply / APPLY / ' Apply ' -> apply; true / 1 / yes / on / TRUE -> dry.
- Counters against GC-4 Q1 on a 13-binding fixture:
  - with_label_en 6 and with_label_ar 3 count DISTINCT qids (a qid bound twice is counted once).
  - A mul-only brand counts label_en_from_mul.
  - An en label of 129 chars WITH a mul label counts no_label_en and does NOT fall back (Q1 as ruled).
  - An over-long ar label counts label_ar_dropped; the row is kept with ar NULL.
  - Denied and IP-only sites count brand_host_null.
  - bad_qid is counted per binding (Q012, P31).
  - Padded labels are stripped and accepted.
  - brand_rows is always present (0 on an empty answer).
  - sparql_limit_hit is absent at 1999 bindings and 1 at 2000.
  - The cap keeps the numerically smallest qids (Q4, Q10 of Q4 / Q10 / Q21 / Q101).
  - KB_BRANDS_MAX 0 -> 300; 99999 -> 5000.
- Host choice: the www. prefix is stripped and the smallest builder-accepted host kept; an EXISTING kb_merchants host stays as official_host (counted `existing` only on the host side).
- Writer:
  - 250 rows -> 3 upserts (100 / 100 / 50) and 0 updates when every row is returned.
  - The idempotent re-run with returned=[] (the FakeClient shape of R-S16B-3) -> 250 updates. The payload keys are exactly KB_BRAND_UPSERT_SET and the filters [('qid', q), ('source', 'wikidata')]. The ops are only upsert / update, on kb_brands only.
  - An 'operator' row is never updated.
  - A non-builder row is counted not_built and never sent.
- The finally:
  - An update raising on the 3rd call -> counts {kb_brands_sent 250, brand_updates 2, write_failed 1} beside the derive keys; none overwritten.
  - An upsert raising on the first batch -> {write_failed 1}.
  - In both cases, one WARNING carrying only the exception type name.
- Reports (DRY, APPLY + --dry-run, APPLY, APPLY max 2):
  - Top keys {brands, counts, hosts}; the brand entries are exactly {qid, label_en, label_ar, official_host}.
  - DRY and --dry-run write nothing; APPLY writes only kb_brands.
  - The totals line carries ints only.
- Request path:
  - kb_service.py is reached lazily (kb_ingest via structured_comparison_service, and merchant_registry).
  - grep: no app/ or scripts/ code other than KbWriter._built reads KB_TABLES / KB_COLUMNS / KB_BUILDER_KEYS, and the leaf diff only adds. The request path is behaviourally unchanged.
  - Billing R-A3, the error-handler mapping and the PLAN section 0 contract freeze are not touched: no route, quota, refund or response-shape change.
- AST string constants equal to "kb_brands" in app/ + scripts/: kb_service.py :58 and :98, and kb_seed_common.py :55 (the KB_BRANDS_TABLE line), nowhere else. No `.table('kb_` literal in app/ or scripts/. The script names kb_merchants only in a docstring, a comment and the read-failure log.
- railway.*.json: no service runs the brand script. kbseed / feedwalker / pdpdiscovery watch kb_seed_common.py (L6 true). The web railway.json has no watch pattern (it redeploys on any merge, as for every unit).
- Hygiene:
  - Edited files keep CRLF (0 LF-only lines); new files are LF; the code files are ASCII.
  - CLAUDE.md's non-ASCII byte count is unchanged (3913 at base = HEAD).
  - The added-line sweep (@gmail, +973, 8-digit runs, sk- / eyJ / PEM shapes) is empty.
  - numstat: 9 files. The only deleted lines are the rewritten docstring / flag / SPARQL / mode-line / R23-R24 lines.
- ONE_PASTE carries the final 052 bytes from `BEGIN;` on, verbatim (only the header differs, as designed).

## Claims checked against the bytes
- GREEN report: every item below was reproduced.
  - G4 129 / 129 both ways, G5 673 + 5, G6 168, G10 481, and the mutant kill sets.
  - D2: brand_updates is bumped after the call returns (S10 pins 0 on a raising update).
  - D3: _run defaults to MODE_DRY. D4: the write lives in _write_brands.
- CLAUDE.md sentences: all true. Checked: the own flag; the mode idiom; the OFF line naming both flags before any I/O; the numeric ORDER BY and LIMIT 2000; insert-ignore plus one update per existing 'wikidata' row; no delete; no kb_merchants write; the kb_ingest correction of R-S16B-13; the one-off owner commands.
- PR body: true except m5 and m6. Checked: the E-row node counts (EK1 2, EK2 3, E1 10), L1-L13, owner steps 0-6, and the size (10,909 B).

## Blocking
none

## Major
none

## Minor (stated-limit / documentation candidates, LC-4)
- m1 (X03 survives): GC-4 Q1 says a refused en label does not fall back to mul. The code does this (probe: an en label of 129 chars plus a mul label -> no_label_en, no row), but no frozen row pins it: S06's Q14 has no mul label. A later edit could add the fallback without any row failing. Stated limit.
- m2 (X14 survives): the in-Python `row["source"] != "wikidata"` skip in KbWriter.brands is unpinned (the script never builds an 'operator' row). The protection that matters, the `.eq("source", "wikidata")` filter, IS pinned (S05 / M03). Prove-nothing for the Python guard.
- m3 (X17 survives): "brand_rows always present" (Q1) is unpinned for an empty answer (probe: {'brand_rows': 0}).
- m4: `_label` strips a whitespace-only en label to None before the builder sees it. With a mul label present it then falls back to mul and counts label_en_from_mul, not no_label_en. This follows spec 2.5 (empty -> None) literally but reads against the Q1 wording; Wikidata labels are never blank in practice. Documentation.
- m5: the PR body's "app/services/kb_service.py (the leaf; no request path imports it)" is inaccurate: kb_ingest (imported by structured_comparison_service) and merchant_registry import it lazily. Runtime is unchanged (the diff only adds, and no request-path code reads the census). Reword to "no request-path code reads the new names".
- m6: PR owner step 6's canary `count(*) FILTER (WHERE updated_at > created_at) > 0` can pass with no update at all. An inserted row's updated_at comes from the runner's Python clock, while created_at is the database's now(). If the runner's clock is ahead of the database's, the canary passes without any update. Prefer `updated_at > <the second run's start>`, or the second run's brand_updates with write_failed absent.
- m7: the seed_kb_brands_wikidata parametrisation of G2 R02 is now vacuous for the brand flag: it passes because EK0 unsets ENABLE_KB_BRANDS, and the script ignores ENABLE_KB_SEED. S02 (24 nodes) is the real OFF row. Prove-nothing.

## Prove-nothing rows
- R02[seed_kb_brands_wikidata-*] (m7).
- R23[apply]'s write assertion is a subset check ({kb_brands}, and ops within {upsert, update}); the literal rows are S04's.
- Observation for later rounds: on this box (core.autocrlf=true) a fresh worktree checks the three LF-only new files out as CRLF. There the frozen RED file's ON-DISK sha differs (16bac1b0...) while its HEAD blob stays cd67db3b. Re-hash the blob (`git show HEAD:<path> | sha256sum`) or byte-copy, as done here.

## Not measured
- G9: the schema lens's; not re-run.
- The comm set: the engineering duty, not this lens; GREEN's comparison against the stored record was not re-run.
- The client fences and the full jest (LC-7).
- The PostgREST return shape (L7).
- Wikidata itself (offline).
