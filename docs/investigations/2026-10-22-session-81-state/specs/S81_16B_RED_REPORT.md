# S81-16b KB-BRANDS RED report (RED agent, Opus 5.5, 2026-11-04)

Written through the shell (python), per the report-file rule. Unit: S81-16b KB-BRANDS (FOCUS: migration 052). Base 0b19de5bcc1416111d48bc725359b95151a658ca, real worktree sc-s81-s16b. Authority: RULINGS_S81_16B (R-S16B-1..16) > the review (BL1-BL3, C1-C10) > the spec (sha 34706e22...).

## 1. File written (the ONE new file)

- tests/test_s81_s16b_kb_brands.py  sha256 cd67db3bd75d90ae90eeb90ce48c90aac4bb9131ac8e99753e99b36738b75cbd  43652 bytes  (pure ASCII, LF, 0 bytes > 127, no 8-digit run, no key shape; ruff E9/F63/F7/F82 clean; py_compile ok)
- byte-identical copy used in the prototype (cmp OK).

## 2. Rows and node counts

| group | rows | nodes |
|---|---|---|
| B (migration 052) | B01-B12 | 14 (B02 x2, B11 x2) |
| K (leaf) | K01-K06 | 46 (K02 x7 incl. the 253-char host, K03 x35 = 29 + the six blank / padded label rows) |
| S (script) | S01-S12 | 63 (S01 x15 MODE_TABLE, S02 x24 = 8 OFF spellings incl. dry x 3 ENABLE_KB_SEED states, S04 x2, S05 x2, S08 x12, S10 x2) |
| PIN | PIN-1..PIN-6 | 6 |
| total | 36 rows | 129 nodes (123 RED + 6 PIN) |

Amendments carried (per ruling): R-S16B-1 052 everywhere (B01 also asserts no 051_*.sql, B06 the DO message starts '052 ', B10 no '051' in either file); R-S16B-2 S04 literal row list (105 rows: 4 special + 101 fillers), upsert count 2, batch sizes [100, 5], kwargs {on_conflict: qid, ignore_duplicates: True}, never build_brand_row on a written row; S06 the existing-merchant-host case (Q12 keeps store-a.example.com); R-S16B-3 S10 update case returned=lambda q, rows: []; R-S16B-4 B12 AST constants equal to 'kb_brands', only kb_service.py + the one KB_BRANDS_TABLE line; R-S16B-5 S02 main WITHOUT client=, argv with the argparse-refused --corpus + --report <tmp> with open() recorded; R-S16B-6 counters (S03 pins the WHOLE counts dict; S04/S10 writer counters added, write_failed + kb_brands_sent reported from the finally), builder refuses blank/padded labels (K03), the btrim CHECK clauses in B03/B04; R-S16B-7 S03 fixture (one brand two sites same labels, no-ar item, mul-only, neither), K02 253 / K03 254 hosts built at run time; R-S16B-8 the mul OPTIONAL + label_en_from_mul (S03, S06), M33; R-S16B-9 the numeric ORDER BY text pinned in S03; R-S16B-10 qid regex, human exclusion, OFF line naming both flags, smallest host, .eq('source','wikidata'), the report's brands list.

## 3. Base run (RED fails on AssertionError only; PINs green with the full configuration)

    [hermeticity] sentinel checked 129 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    123 failed, 6 passed, 11 warnings in 7.72s

Failure type per RED node (parsed from the long traceback of each node): 123 nodes, types ['AssertionError']. The 6 passing nodes are PIN-1..PIN-6.

<details><summary>per-node proof (node -> exception type)</summary>

- test_s16b_b01_files_exist_once -> AssertionError
- test_s16b_b02_one_transaction[forward] -> AssertionError
- test_s16b_b02_one_transaction[rollback] -> AssertionError
- test_s16b_b03_columns_match_the_leaf -> AssertionError
- test_s16b_b04_regex_texts_equal_the_leaf -> AssertionError
- test_s16b_b05_service_role_only -> AssertionError
- test_s16b_b06_trigger_and_045_guard -> AssertionError
- test_s16b_b07_host_index_not_unique -> AssertionError
- test_s16b_b08_no_personal_column_no_fk -> AssertionError
- test_s16b_b09_rollback_statements -> AssertionError
- test_s16b_b10_headers -> AssertionError
- test_s16b_b11_ascii_and_sqlfluff_clean[forward] -> AssertionError
- test_s16b_b11_ascii_and_sqlfluff_clean[rollback] -> AssertionError
- test_s16b_b12_kb_brands_literal_census -> AssertionError
- test_s16b_k01_census_constants -> AssertionError
- test_s16b_k02_builder_accepts[arabic_label] -> AssertionError
- test_s16b_k02_builder_accepts[host_253] -> AssertionError
- test_s16b_k02_builder_accepts[label_128] -> AssertionError
- test_s16b_k02_builder_accepts[minimal] -> AssertionError
- test_s16b_k02_builder_accepts[qid_12_digits] -> AssertionError
- test_s16b_k02_builder_accepts[source_operator] -> AssertionError
- test_s16b_k02_builder_accepts[with_host] -> AssertionError
- test_s16b_k03_builder_refuses[qid-Q0] -> AssertionError
- test_s16b_k03_builder_refuses[qid-Q01] -> AssertionError
- test_s16b_k03_builder_refuses[qid-lower] -> AssertionError
- test_s16b_k03_builder_refuses[qid-bare-Q] -> AssertionError
- test_s16b_k03_builder_refuses[qid-13-digits] -> AssertionError
- test_s16b_k03_builder_refuses[qid-trailing-space] -> AssertionError
- test_s16b_k03_builder_refuses[qid-trailing-newline] -> AssertionError
- test_s16b_k03_builder_refuses[qid-int] -> AssertionError
- test_s16b_k03_builder_refuses[label_en-none] -> AssertionError
- test_s16b_k03_builder_refuses[label_en-empty] -> AssertionError
- test_s16b_k03_builder_refuses[label_en-129] -> AssertionError
- test_s16b_k03_builder_refuses[label_en-nul] -> AssertionError
- test_s16b_k03_builder_refuses[label_en-surrogate] -> AssertionError
- test_s16b_k03_builder_refuses[label_en-lead-space] -> AssertionError
- test_s16b_k03_builder_refuses[label_en-trail-space] -> AssertionError
- test_s16b_k03_builder_refuses[label_en-blank] -> AssertionError
- test_s16b_k03_builder_refuses[label_ar-empty] -> AssertionError
- test_s16b_k03_builder_refuses[label_ar-129] -> AssertionError
- test_s16b_k03_builder_refuses[label_ar-nul] -> AssertionError
- test_s16b_k03_builder_refuses[label_ar-lead-space] -> AssertionError
- test_s16b_k03_builder_refuses[label_ar-trail-space] -> AssertionError
- test_s16b_k03_builder_refuses[label_ar-blank] -> AssertionError
- test_s16b_k03_builder_refuses[host-upper] -> AssertionError
- test_s16b_k03_builder_refuses[host-single-label] -> AssertionError
- test_s16b_k03_builder_refuses[host-ipv4] -> AssertionError
- test_s16b_k03_builder_refuses[host-hex-top] -> AssertionError
- test_s16b_k03_builder_refuses[host-www-deny] -> AssertionError
- test_s16b_k03_builder_refuses[host-deny] -> AssertionError
- test_s16b_k03_builder_refuses[host-rule-only] -> AssertionError
- test_s16b_k03_builder_refuses[host-path] -> AssertionError
- test_s16b_k03_builder_refuses[host-254] -> AssertionError
- test_s16b_k03_builder_refuses[source-manual] -> AssertionError
- test_s16b_k03_builder_refuses[source-none] -> AssertionError
- test_s16b_k03_builder_refuses[updated_at-naive] -> AssertionError
- test_s16b_k03_builder_refuses[updated_at-str] -> AssertionError
- test_s16b_k04_belt_holds_without_the_rule -> AssertionError
- test_s16b_k05_rule_read_at_call_time -> AssertionError
- test_s16b_k06_never_raises_on_junk -> AssertionError
- test_s16b_s01_flag_constant_and_table[None-off] -> AssertionError
- test_s16b_s01_flag_constant_and_table[-off] -> AssertionError
- test_s16b_s01_flag_constant_and_table[false-off] -> AssertionError
- test_s16b_s01_flag_constant_and_table[0-off] -> AssertionError
- test_s16b_s01_flag_constant_and_table[no-off] -> AssertionError
- test_s16b_s01_flag_constant_and_table[ OFF -off] -> AssertionError
- test_s16b_s01_flag_constant_and_table[garbage-off] -> AssertionError
- test_s16b_s01_flag_constant_and_table[true-dry] -> AssertionError
- test_s16b_s01_flag_constant_and_table[1-dry] -> AssertionError
- test_s16b_s01_flag_constant_and_table[yes-dry] -> AssertionError
- test_s16b_s01_flag_constant_and_table[on-dry] -> AssertionError
- test_s16b_s01_flag_constant_and_table[ TRUE -dry] -> AssertionError
- test_s16b_s01_flag_constant_and_table[apply-apply] -> AssertionError
- test_s16b_s01_flag_constant_and_table[ APPLY -apply] -> AssertionError
- test_s16b_s01_flag_constant_and_table[dry-off] -> AssertionError
- test_s16b_s02_off_is_inert[None-seed-apply] -> AssertionError
- test_s16b_s02_off_is_inert[None-seed-true] -> AssertionError
- test_s16b_s02_off_is_inert[None-seed-unset] -> AssertionError
- test_s16b_s02_off_is_inert[-seed-apply] -> AssertionError
- test_s16b_s02_off_is_inert[-seed-true] -> AssertionError
- test_s16b_s02_off_is_inert[-seed-unset] -> AssertionError
- test_s16b_s02_off_is_inert[false-seed-apply] -> AssertionError
- test_s16b_s02_off_is_inert[false-seed-true] -> AssertionError
- test_s16b_s02_off_is_inert[false-seed-unset] -> AssertionError
- test_s16b_s02_off_is_inert[0-seed-apply] -> AssertionError
- test_s16b_s02_off_is_inert[0-seed-true] -> AssertionError
- test_s16b_s02_off_is_inert[0-seed-unset] -> AssertionError
- test_s16b_s02_off_is_inert[no-seed-apply] -> AssertionError
- test_s16b_s02_off_is_inert[no-seed-true] -> AssertionError
- test_s16b_s02_off_is_inert[no-seed-unset] -> AssertionError
- test_s16b_s02_off_is_inert[ OFF -seed-apply] -> AssertionError
- test_s16b_s02_off_is_inert[ OFF -seed-true] -> AssertionError
- test_s16b_s02_off_is_inert[ OFF -seed-unset] -> AssertionError
- test_s16b_s02_off_is_inert[garbage-seed-apply] -> AssertionError
- test_s16b_s02_off_is_inert[garbage-seed-true] -> AssertionError
- test_s16b_s02_off_is_inert[garbage-seed-unset] -> AssertionError
- test_s16b_s02_off_is_inert[dry-seed-apply] -> AssertionError
- test_s16b_s02_off_is_inert[dry-seed-true] -> AssertionError
- test_s16b_s02_off_is_inert[dry-seed-unset] -> AssertionError
- test_s16b_s03_dry_counts_no_write -> AssertionError
- test_s16b_s04_apply_writes_kb_brands_only[apply] -> AssertionError
- test_s16b_s04_apply_writes_kb_brands_only[apply-dry-run] -> AssertionError
- test_s16b_s05_rerun_updates_wikidata_rows_only[none-returned] -> AssertionError
- test_s16b_s05_rerun_updates_wikidata_rows_only[two-returned] -> AssertionError
- test_s16b_s06_dedupe_and_host_choice -> AssertionError
- test_s16b_s07_cap_and_order -> AssertionError
- test_s16b_s08_knob_table[None-300] -> AssertionError
- test_s16b_s08_knob_table[-300] -> AssertionError
- test_s16b_s08_knob_table[garbage-300] -> AssertionError
- test_s16b_s08_knob_table[inf-300] -> AssertionError
- test_s16b_s08_knob_table[nan-300] -> AssertionError
- test_s16b_s08_knob_table[-5-300] -> AssertionError
- test_s16b_s08_knob_table[0-300] -> AssertionError
- test_s16b_s08_knob_table[7-7] -> AssertionError
- test_s16b_s08_knob_table[7.9-7] -> AssertionError
- test_s16b_s08_knob_table[9000-5000] -> AssertionError
- test_s16b_s08_knob_table[ 12 -12] -> AssertionError
- test_s16b_s08_knob_table[1-1] -> AssertionError
- test_s16b_s09_limit_hit_count -> AssertionError
- test_s16b_s10_write_failure_is_quiet[upsert] -> AssertionError
- test_s16b_s10_write_failure_is_quiet[update] -> AssertionError
- test_s16b_s11_no_label_or_host_in_logs -> AssertionError
- test_s16b_s12_script_hygiene -> AssertionError

</details>

## 4. Prototype (detached scratch worktree S81-16b_red/w at 0b19de5b, no junction; removed, verified gone)

Change list implemented (thrown away; diff saved): migrations/052_kb_brands.sql + rollback (the spec agent's proto renamed 051 -> 052 and amended with the btrim clauses merged into the label_en / label_ar column CHECKs; sqlfluff 'All Finished!'); kb_service KB_TABLES + kb_brands LAST, KB_COLUMNS, KB_QID_REGEX / KB_BRAND_SOURCES / KB_BRAND_UPSERT_SET, _trimmed + build_brand_row; kb_seed_common KB_BRANDS_TABLE + KbWriter.brands (brand_updates bumped per attempt); the script (FLAG, MAX_KNOB, SPARQL_LIMIT, SPARQL with en / mul / ar + human exclusion + numeric ORDER BY, brands_max, qid_of, _label (strip), _brand_host, derive_brands with the counters, _run(args, client, mode) with the writer counters added in a finally, the OFF / mode lines, the docstring); EK0-EK2 + E1 exactly as spec 4.1; APPLY_052 PRECHECK / ONE_PASTE (regenerated from the final 052 bytes) / POSTCHECK (+ anon/authenticated UPDATE/DELETE columns, C10; check_count stays 6), sqlfluff clean.

- red_proto1.log
    [hermeticity] sentinel checked 129 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    129 passed, 11 warnings in 6.91s
- red_proto_on.log
    [hermeticity] sentinel checked 129 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    129 passed, 11 warnings in 5.11s
- red_proto_erows.log
    [hermeticity] sentinel checked 678 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    5 failed, 673 passed, 11 warnings in 12.86s
- red_proto_g6.log
    [hermeticity] sentinel checked 168 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    168 passed, 4 deselected, 1 warning in 26.53s

red_proto_on = the RED file with ENABLE_KB_BRANDS=apply, KB_BRANDS_MAX=1, ENABLE_KB_SEED=apply exported (the leak check: the rows set their own env). red_proto_erows = test_s81_kb_schema.py + test_s81_s16_kb_seed.py + test_s81_g2_gate_rows.py with EK0-EK2 + E1 applied: the only failures are the five G2 R27 CRLF nodes (environmental; the same five R27 conditions evaluated on the LF-normalised prototype bytes all hold). red_proto_g6 = the seven migration readers with 052 present.

Prototype files: S81-16b_red/prototype.diff (sha c178301dce060d965b091c53837ef836ae92ec79c603cc82f68c62f04ac36815) and S81-16b_red/prototype_files/ (incl. apply/APPLY_052_*.sql).

```diff
diff --git a/app/services/kb_service.py b/app/services/kb_service.py
index a0096a24..dfaca603 100644
--- a/app/services/kb_service.py
+++ b/app/services/kb_service.py
@@ -54,7 +54,7 @@ KB_CATEGORY = "fragrances"
 
 KB_TABLES: Tuple[str, ...] = (
     "kb_merchants", "kb_products", "kb_variants", "kb_offers", "kb_images",
-    "kb_specs", "kb_reviews", "kb_gaps", "kb_feedback", "kb_coverage_daily",
+    "kb_specs", "kb_reviews", "kb_gaps", "kb_feedback", "kb_coverage_daily", "kb_brands",
 )
 
 KB_COLUMNS: Dict[str, Tuple[str, ...]] = {
@@ -94,6 +94,7 @@ KB_COLUMNS: Dict[str, Tuple[str, ...]] = {
         "id", "compare_request_id", "product_id", "field", "verdict", "device_key", "created_at",
     ),
     "kb_coverage_daily": ("day", "metric", "value", "n"),
+    "kb_brands": ("qid", "label_en", "label_ar", "official_host", "source", "created_at", "updated_at"),
 }
 
 #: Tables whose ``id`` is a server-side uuid (never built by the leaf).
@@ -153,6 +154,12 @@ KB_OFFER_OBSERVATION_KEY: Tuple[str, ...] = (
 )
 KB_OFFER_UPSERT_SET: Tuple[str, ...] = ("last_seen", "in_stock", "evidence_rung", "canonical_url")
 
+#: S81-16b (migration 052): the Wikidata item id CHECK (no leading zero: one item, one key).
+KB_QID_REGEX = "^Q[1-9][0-9]{0,11}$"
+KB_BRAND_SOURCES: Tuple[str, ...] = ("wikidata", "operator")
+#: What a Wikidata re-run sets on an existing row (never qid, source, created_at).
+KB_BRAND_UPSERT_SET: Tuple[str, ...] = ("label_en", "label_ar", "official_host", "updated_at")
+
 _DEFAULT_PORTS = {"http": 80, "https": 443}
 _MAX_SKU_ML = 5000
 _INT4_MAX = 2 ** 31 - 1
@@ -804,3 +811,38 @@ def build_coverage_row(*, day: Any, metric: Any, value: Any, n: Any) -> Optional
         return {"day": str(day), "metric": metric, "value": str(num), "n": n}
     except Exception:
         return None
+
+
+def _trimmed(value: Any) -> bool:
+    """A label equal to its own strip() (the 052 btrim CHECK; stricter: every
+    whitespace kind is refused at both ends)."""
+    return isinstance(value, str) and value == value.strip()
+
+
+def build_brand_row(*, qid: Any, label_en: Any, updated_at: Any, label_ar: Any = None,
+                    official_host: Any = None, source: Any = "wikidata") -> Optional[Dict[str, Any]]:
+    """One kb_brands row (S81-16b, migration 052) or None; never raises."""
+    try:
+        upd = _ts_iso(updated_at)
+        if not _pg_text_ok((qid, label_en, label_ar, official_host, source)):
+            return None
+        ok = (
+            _sql_match(KB_QID_REGEX, qid)
+            and _str_len(label_en, 1, 128) and _trimmed(label_en)
+            and (label_ar is None or (_str_len(label_ar, 1, 128) and _trimmed(label_ar)))
+            and (official_host is None or (
+                _str_len(official_host, 1, 253)
+                and _belted_host(official_host)
+                and kb_source_allowed(official_host)
+            ))
+            and isinstance(source, str) and source in KB_BRAND_SOURCES
+            and upd is not None
+        )
+        if not ok:
+            return None
+        return {
+            "qid": qid, "label_en": label_en, "label_ar": label_ar,
+            "official_host": official_host, "source": source, "updated_at": upd,
+        }
+    except Exception:
+        return None
diff --git a/migrations/052_kb_brands.sql b/migrations/052_kb_brands.sql
new file mode 100644
index 00000000..1fb0e4d1
--- /dev/null
+++ b/migrations/052_kb_brands.sql
@@ -0,0 +1,95 @@
+-- Migration 052: public.kb_brands -- fragrance brand entities from Wikidata (S81-16b KB-BRANDS, S81)
+--
+-- One row per brand entity: the Wikidata item id (qid), the English label
+-- (required), the Arabic label (NULL when Wikidata has none), the official-site
+-- host (NULL when the item has no usable official website) and the row source
+-- ('wikidata' for the import, 'operator' for a hand-curated row). The rows are
+-- built by app/services/kb_service.py build_brand_row and written only by
+-- scripts/seed_kb_brands_wikidata.py under ENABLE_KB_BRANDS=apply (insert-ignore
+-- on qid, then one update of the label and host columns of the 'wikidata' rows
+-- the insert did not return; a brand gone from Wikidata is never deleted and an
+-- 'operator' row is never updated by the import). Wikidata data is CC0 (public
+-- domain dedication): no attribution or share-alike duty attaches to the rows.
+-- kb_products.brand stays free text: no foreign key, no alias and no product
+-- link in this table (later units). Two brands may share one official host (a
+-- house and its sub-brand): official_host is indexed, not UNIQUE.
+--
+-- MERGING THIS CHANGES NOTHING IN PRODUCTION: no request-path code reads or
+-- writes kb_brands, and the one writer runs only on the kbseed service with
+-- ENABLE_KB_BRANDS=apply.
+--
+-- APPLY ORDER: after 045 (it reuses public.kb_set_updated_at and the 045
+-- host belts; the DO block below refuses to run without 045); none against
+-- 047 or 050. Rollback 052 BEFORE any rollback of 045 (the trigger depends on
+-- the 045 trigger function).
+--
+-- Service role only (the 045 pattern; the 037 both-readings rule): RLS on, no
+-- policy; REVOKE ALL from PUBLIC, anon, authenticated, service_role, then
+-- GRANT SELECT, INSERT, UPDATE, DELETE to service_role. No user, device,
+-- session or address column and no foreign key to users: the 043 deletion
+-- fence does not apply. The import excludes Wikidata items that are humans
+-- (P31 Q5), so a label is a brand or company name, never a person's name.
+--
+-- Both labels are trimmed (label = btrim(label)): a blank or padded label is
+-- refused here and by the builder.
+--
+-- The official_host CHECK mirrors the 045 host belts: the host regex
+-- (kb_service.KB_HOST_REGEX), the deny label belt (kb_service
+-- kb_host_deny_regex, a strict SUBSET of deny_hosts.kb_source_allowed, which
+-- the builder applies) and the top-label rule (KB_HOST_TOP_LABEL_REGEX).
+--
+-- Postcheck: APPLY_052_3_POSTCHECK.sql. Rollback: migrations/rollback/052_kb_brands.sql
+
+BEGIN;
+
+DO $$
+BEGIN
+  IF to_regprocedure('public.kb_set_updated_at()') IS NULL THEN
+    RAISE EXCEPTION '052 needs 045 applied first (public.kb_set_updated_at is missing)';
+  END IF;
+END
+$$;
+
+CREATE TABLE IF NOT EXISTS public.kb_brands (
+    qid text PRIMARY KEY CHECK (qid ~ '^Q[1-9][0-9]{0,11}$'),
+    label_en text NOT NULL CHECK (
+        char_length(label_en) BETWEEN 1 AND 128 AND label_en = btrim(label_en)
+    ),
+    label_ar text CHECK (
+        label_ar IS NULL OR (
+            char_length(label_ar) BETWEEN 1 AND 128 AND label_ar = btrim(label_ar)
+        )
+    ),
+    official_host text CHECK (
+        official_host IS NULL OR (
+            char_length(official_host) BETWEEN 1 AND 253
+            AND official_host ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'
+            AND official_host !~ '(^|[.])(basenotes|fimgs|fragrantica|parfumo)[.]'
+        )
+    ),
+    source text NOT NULL DEFAULT 'wikidata' CHECK (source IN ('wikidata', 'operator')),
+    created_at timestamptz NOT NULL DEFAULT now(),
+    updated_at timestamptz NOT NULL DEFAULT now(),
+    CONSTRAINT kb_brands_host_top_label_letter CHECK (
+        official_host IS NULL
+        OR official_host ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)'
+    )
+);
+
+CREATE INDEX IF NOT EXISTS idx_kb_brands_official_host
+    ON public.kb_brands (official_host) WHERE official_host IS NOT NULL;
+
+CREATE OR REPLACE TRIGGER kb_brands_set_updated_at
+BEFORE UPDATE ON public.kb_brands
+FOR EACH ROW EXECUTE FUNCTION public.kb_set_updated_at();
+
+ALTER TABLE public.kb_brands ENABLE ROW LEVEL SECURITY;
+
+REVOKE ALL ON TABLE public.kb_brands FROM PUBLIC, anon, authenticated, service_role;
+
+GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_brands TO service_role;
+
+COMMENT ON TABLE public.kb_brands IS
+'Fragrance brand entities imported from Wikidata (CC0) by scripts/seed_kb_brands_wikidata.py (S81-16b). No user data. Service role only.';
+
+COMMIT;
diff --git a/migrations/rollback/052_kb_brands.sql b/migrations/rollback/052_kb_brands.sql
new file mode 100644
index 00000000..205b8e7f
--- /dev/null
+++ b/migrations/rollback/052_kb_brands.sql
@@ -0,0 +1,16 @@
+-- Rollback for migration 052_kb_brands.sql (S81-16b KB-BRANDS, S81)
+--
+-- Unset ENABLE_KB_BRANDS on the kbseed service first (the only writer). Run
+-- this BEFORE any rollback of 045: the kb_brands trigger depends on the 045
+-- function public.kb_set_updated_at, which this file keeps. The table's
+-- trigger, index and checks go with it.
+--
+-- IMPORTANT: this is destructive. Every imported brand row is lost; a re-run
+-- of the import (ENABLE_KB_BRANDS=apply) after re-applying 052 restores the
+-- Wikidata rows, not the 'operator' rows.
+
+BEGIN;
+
+DROP TABLE IF EXISTS public.kb_brands;
+
+COMMIT;
diff --git a/scripts/kb_seed_common.py b/scripts/kb_seed_common.py
index 94b57223..3d1277db 100644
--- a/scripts/kb_seed_common.py
+++ b/scripts/kb_seed_common.py
@@ -16,7 +16,7 @@ nothing of the app (no client, no SDK, no settings, no dotenv). What lives here:
   (insert-ignore; the offer re-observation update of KB_OFFER_UPSERT_SET; the
   kb_gaps last_seen-only re-discovery update).
 
-The five KB table names below are the only kb_* relation literals of G2 and
+The six KB table names below are the only kb_* relation literals of G2 and
 ``kb_leaf`` is the only importer of the S81-14 leaf (tests/test_s81_kb_schema.py
 E1 / E2 key both by exact line).
 """
@@ -52,6 +52,7 @@ KB_VARIANTS_TABLE = "kb_variants"
 KB_OFFERS_TABLE = "kb_offers"
 KB_SPECS_TABLE = "kb_specs"
 KB_GAPS_TABLE = "kb_gaps"
+KB_BRANDS_TABLE = "kb_brands"
 LLM_SPEND_LEDGER_TABLE = "llm_spend_ledger"
 
 #: Every reason ``url_gate`` can return (in the order the gate checks them).
@@ -436,5 +437,24 @@ class KbWriter:
         self.counts["gap_updates"] += updates
         return updates
 
+    def brands(self, rows: Sequence[Any]) -> int:
+        """S81-16b: insert-ignore on qid; every row the insert did not return gets
+        ONE update of KB_BRAND_UPSERT_SET restricted to source = 'wikidata' (an
+        operator row never moves; nothing is deleted). ``brand_updates`` counts
+        update ATTEMPTS. Returns the update count."""
+        kb = kb_leaf()
+        built = self._built(KB_BRANDS_TABLE, rows)
+        inserted = self._send(KB_BRANDS_TABLE, built, "qid")
+        seen = {r.get("qid") for r in inserted}
+        updates = 0
+        for row in built:
+            if row["qid"] in seen or row.get("source") != "wikidata":
+                continue
+            (self.client.table(KB_BRANDS_TABLE).update({k: row[k] for k in kb.KB_BRAND_UPSERT_SET})
+             .eq("qid", row["qid"]).eq("source", "wikidata").execute())
+            updates += 1
+            self.counts["brand_updates"] += 1
+        return updates
+
     def ledger(self, row: Dict[str, Any]) -> None:
         self.client.table(LLM_SPEND_LEDGER_TABLE).insert(row).execute()
diff --git a/scripts/seed_kb_brands_wikidata.py b/scripts/seed_kb_brands_wikidata.py
index 1b47a1b6..80ff6fde 100644
--- a/scripts/seed_kb_brands_wikidata.py
+++ b/scripts/seed_kb_brands_wikidata.py
@@ -1,12 +1,16 @@
-"""S81-16 brand hosts from Wikidata: DRY-ONLY by ruling R-G2-3.
-
-The same flag and mode as seed_kb_batch (ENABLE_KB_SEED, read per call, the
-FIRST statement of ``main``). In DRY and APPLY alike it reads the query
-service's robots.txt once, then makes ONE SPARQL GET (both through the polite
-named-agent fetcher, SSRF-checked on every hop), derives the official-site
-hosts and writes the host list to --report only. It writes NOTHING to the KB in
-any mode: a brands table needs its own migration (S81-16b), so APPLY behaves as
-DRY and its mode line says so.
+"""S81-16 brand hosts and S81-16b brand rows from Wikidata (ENABLE_KB_BRANDS).
+
+Its OWN flag since S81-16b: ENABLE_KB_BRANDS (read per call, the FIRST
+statement of ``main``; unset / false / dry -> OFF, true -> DRY, the exact word
+apply -> WRITE) and the knob KB_BRANDS_MAX (300, 1..5000). ENABLE_KB_SEED never
+runs this script. In DRY and APPLY alike it reads the query service's
+robots.txt once, then makes ONE SPARQL GET (both through the polite named-agent
+fetcher, SSRF-checked on every hop), derives the official-site hosts and the
+brand rows (en / mul / ar labels, humans excluded) and writes both with the
+counts to --report. Only APPLY writes, and only public.kb_brands (migration 052)
+through KbWriter.brands: insert-ignore on qid, then one update of the label and
+host columns of the 'wikidata' rows the insert did not return. Never a
+kb_merchants write; nothing is deleted. Wikidata data is CC0.
 """
 from __future__ import annotations
 
@@ -23,14 +27,23 @@ from scripts import kb_seed_common as common
 
 logger = logging.getLogger("seed_kb_brands_wikidata")
 
-FLAG = "ENABLE_KB_SEED"
+FLAG = "ENABLE_KB_BRANDS"
+MAX_KNOB = "KB_BRANDS_MAX"
 PREFIX = "[KB_BRANDS]"
 ROBOTS_URL = "https://query.wikidata.org/robots.txt"
 SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
-# P1056 product or material produced = Q131746 perfume; P856 official website
-# (offline-unverified ids: the dry-run binding count is the check, S16 L7).
-SPARQL = ("SELECT DISTINCT ?brand ?site WHERE { ?brand wdt:P1056 wd:Q131746 . "
-          "?brand wdt:P856 ?site . } LIMIT 2000")
+SPARQL_LIMIT = 2000
+# P1056 product or material produced = Q131746 perfume; P856 official website;
+# P31 Q5 = human (excluded). Offline-unverified ids: the dry-run counts are the
+# check (S16 L7). Labels: exact en, else mul (the default-language label), and
+# exact ar; ordered by the numeric qid so a LIMIT truncation is deterministic.
+SPARQL = ("SELECT DISTINCT ?brand ?site ?label_en ?label_mul ?label_ar WHERE { "
+          "?brand wdt:P1056 wd:Q131746 . ?brand wdt:P856 ?site . "
+          "FILTER NOT EXISTS { ?brand wdt:P31 wd:Q5 . } "
+          'OPTIONAL { ?brand rdfs:label ?label_en . FILTER(LANG(?label_en) = "en") } '
+          'OPTIONAL { ?brand rdfs:label ?label_mul . FILTER(LANG(?label_mul) = "mul") } '
+          'OPTIONAL { ?brand rdfs:label ?label_ar . FILTER(LANG(?label_ar) = "ar") } '
+          '} ORDER BY xsd:integer(STRAFTER(STR(?brand), "/entity/Q")) ?site LIMIT ' + str(SPARQL_LIMIT))
 MAX_BRAND_HOSTS = 300
 
 
@@ -38,6 +51,11 @@ def sparql_url() -> str:
     return SPARQL_ENDPOINT + "?format=json&query=" + quote(SPARQL, safe="")
 
 
+def brands_max() -> int:
+    """KB_BRANDS_MAX read per call: 300 by default, clamped to 1..5000."""
+    return common.int_knob(MAX_KNOB, 300, 1, 5000)
+
+
 def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
     p = argparse.ArgumentParser(prog="seed_kb_brands_wikidata")
     p.add_argument("--dry-run", action="store_true")
@@ -88,7 +106,89 @@ def derive_hosts(bindings: Any, existing: set, counts: Dict[str, int]) -> List[s
     return hosts
 
 
-async def _run(args: argparse.Namespace, client: Any) -> int:
+def qid_of(binding: Any) -> Optional[str]:
+    """The last path segment of the brand IRI (a bare id stays); validity is the builder's."""
+    value = ((binding or {}).get("brand") or {}).get("value") if isinstance(binding, dict) else None
+    if not isinstance(value, str) or not value:
+        return None
+    return value.rsplit("/", 1)[-1]
+
+
+def _label(binding: Any, key: str) -> Optional[str]:
+    value = ((binding or {}).get(key) or {}).get("value") if isinstance(binding, dict) else None
+    if not isinstance(value, str):
+        return None
+    value = value.strip()
+    return value or None
+
+
+def _brand_host(site: Optional[str]) -> Optional[str]:
+    from app.services import deny_hosts as dh
+
+    if not site:
+        return None
+    try:
+        host = dh.normalize_host(urlsplit(site).hostname or "")
+    except ValueError:
+        return None
+    return host or None
+
+
+def derive_brands(bindings: Any, counts: Dict[str, int], now: Any, cap: int) -> List[Dict[str, Any]]:
+    """The kb_brands rows of one SPARQL answer, sorted by numeric qid, at most ``cap``."""
+    kb = common.kb_leaf()
+    if isinstance(bindings, list) and len(bindings) == SPARQL_LIMIT:
+        counts["sparql_limit_hit"] = 1
+    groups: Dict[str, Dict[str, Any]] = {}
+    for b in bindings if isinstance(bindings, list) else []:
+        qid = qid_of(b)
+        if qid is None or not kb._sql_match(kb.KB_QID_REGEX, qid):
+            common.bump(counts, "bad_qid")
+            continue
+        g = groups.setdefault(qid, {"en": None, "mul": None, "ar": None, "sites": []})
+        for key, var in (("en", "label_en"), ("mul", "label_mul"), ("ar", "label_ar")):
+            if g[key] is None:
+                g[key] = _label(b, var)
+        site = _site_host(b)
+        if site is not None:
+            g["sites"].append(site)
+    rows: List[Dict[str, Any]] = []
+    for qid, g in groups.items():
+        if g["en"] is not None:
+            common.bump(counts, "with_label_en")
+        if g["ar"] is not None:
+            common.bump(counts, "with_label_ar")
+        label_en = g["en"] if g["en"] is not None else g["mul"]
+        if label_en is None or kb.build_brand_row(qid=qid, label_en=label_en, updated_at=now) is None:
+            common.bump(counts, "no_label_en")
+            continue
+        if g["en"] is None:
+            common.bump(counts, "label_en_from_mul")
+        label_ar = g["ar"]
+        if label_ar is not None and kb.build_brand_row(qid=qid, label_en=label_en, label_ar=label_ar,
+                                                       updated_at=now) is None:
+            common.bump(counts, "label_ar_dropped")
+            label_ar = None
+        host = None
+        for h in sorted({h for h in (_brand_host(s) for s in g["sites"]) if h}):
+            if kb.build_brand_row(qid=qid, label_en=label_en, official_host=h, updated_at=now) is not None:
+                host = h
+                break
+        if host is None:
+            common.bump(counts, "brand_host_null")
+        row = kb.build_brand_row(qid=qid, label_en=label_en, label_ar=label_ar, official_host=host,
+                                 source="wikidata", updated_at=now)
+        if row is not None:
+            rows.append(row)
+    rows.sort(key=lambda r: int(r["qid"][1:]))
+    if len(rows) > cap:
+        counts["over_cap_brands"] = len(rows) - cap
+        rows = rows[:cap]
+    counts["brand_rows"] = len(rows)
+    return rows
+
+
+async def _run(args: argparse.Namespace, client: Any, mode: str) -> int:
     from app.services import robots_eval as re_
 
     try:
@@ -121,7 +221,19 @@ async def _run(args: argparse.Namespace, client: Any) -> int:
         return 0
     counts: Dict[str, int] = {}
     hosts = derive_hosts(bindings, existing, counts)
-    common.write_report(args.report, {"hosts": hosts, "counts": counts})
+    brand_rows = derive_brands(bindings, counts, common._now(), brands_max())
+    if mode == common.MODE_APPLY:
+        writer = common.KbWriter(client)
+        try:
+            writer.brands(brand_rows)
+        except Exception as exc:  # noqa: BLE001 - an owner precondition (052 not applied) ends quietly
+            logger.warning("%s kb_brands write failed (%s)", PREFIX, type(exc).__name__)
+            counts["write_failed"] = 1
+        finally:
+            for key, value in writer.counts.items():
+                counts[key] = counts.get(key, 0) + int(value)
+    report_rows = [{k: r[k] for k in ("qid", "label_en", "label_ar", "official_host")} for r in brand_rows]
+    common.write_report(args.report, {"hosts": hosts, "brands": report_rows, "counts": counts})
     common.log_counts(PREFIX, counts)
     return 0
 
@@ -129,15 +241,16 @@ async def _run(args: argparse.Namespace, client: Any) -> int:
 def main(argv: Optional[List[str]] = None, client: Any = None) -> int:
     mode = common.run_mode(FLAG)
     if mode == common.MODE_OFF:
-        logger.info("%s mode=off ENABLE_KB_SEED not set; skipping run", PREFIX)
+        logger.info("%s mode=off ENABLE_KB_BRANDS not set; skipping run (ENABLE_KB_SEED does not run this script)",
+                    PREFIX)
         return 0
     args = _parse_args(argv)
     mode = common.cli_mode(mode, args.dry_run)
-    logger.info("%s mode=%s (writes nothing in any mode; apply behaves as dry)", PREFIX, mode)
+    logger.info("%s mode=%s (apply writes kb_brands; dry writes nothing)", PREFIX, mode)
     client = common.resolve_client(client, PREFIX)
     if client is None:
         return 0
-    return asyncio.run(_run(args, client))
+    return asyncio.run(_run(args, client, mode))
 
 
 run = main
diff --git a/tests/test_s81_kb_schema.py b/tests/test_s81_kb_schema.py
index 1f7d392b..d483665e 100644
--- a/tests/test_s81_kb_schema.py
+++ b/tests/test_s81_kb_schema.py
@@ -1485,7 +1485,7 @@ def test_s14_r27_builder_keys(table):
     assert tuple(want) == tuple(_attr(kb, "KB_BUILDER_KEYS")[table])
     if table in ("kb_merchants", "kb_products", "kb_variants"):
         assert row["updated_at"] == T0.isoformat(), "R-S14-2: builders emit updated_at (belt)"
-    assert tuple(_attr(kb, "KB_TABLES")) == KB_TABLE_NAMES
+    assert tuple(_attr(kb, "KB_TABLES")) == KB_TABLE_NAMES + ("kb_brands",)  # S81-16b E1: 052 joins the census last
 
 
 NAIVE = datetime(2026, 10, 23, 12, 0)
diff --git a/tests/test_s81_s16_kb_seed.py b/tests/test_s81_s16_kb_seed.py
index 6888a80a..dedf45c9 100644
--- a/tests/test_s81_s16_kb_seed.py
+++ b/tests/test_s81_s16_kb_seed.py
@@ -51,7 +51,8 @@ def _attr(mod, name):
 def _env(monkeypatch):
     import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)
 
-    for name in ("ENABLE_KB_SEED", "ENABLE_LLM_SPEND_BREAKER", "ANTHROPIC_API_KEY") + KNOBS:
+    for name in ("ENABLE_KB_SEED", "ENABLE_KB_BRANDS", "KB_BRANDS_MAX", "ENABLE_LLM_SPEND_BREAKER",
+                 "ANTHROPIC_API_KEY") + KNOBS:
         monkeypatch.delenv(name, raising=False)
     monkeypatch.setenv("SUPABASE_URL", "https://" + "kbseed-test" + ".invalid")
     monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc" + "-" + "x" * 10)
@@ -984,7 +985,8 @@ def _brand_bindings(hosts_extra=()):
 
     sites = ["https://brand-b.example.com/", "https://store-a.example.com/",
              "https://www.%s/" % dh.DENY_HOSTS[0], "http://192.0.2.10/"] + list(hosts_extra)
-    return json.dumps({"results": {"bindings": [{"brand": {"value": "Q%d" % i}, "site": {"value": s}}
+    return json.dumps({"results": {"bindings": [{"brand": {"value": "Q%d" % (i + 1)}, "site": {"value": s},
+                                                 "label_en": {"value": "Brand %d" % i}}
                                                 for i, s in enumerate(sites)]}})
 
 
@@ -997,7 +999,8 @@ def test_s16_r23_brands_dry_and_apply(monkeypatch, tmp_path, mode):
     over = ["https://brand%03d.example.org/" % i for i in range(301)]
     rig = Rig(monkeypatch, common, merchants=[_merchant("store-a.example.com")])
     rig.fetch_responses = [(200, {}, "User-agent: *\nAllow: /\n"), (200, {}, _brand_bindings(over))]
-    _dry(monkeypatch, mode)
+    monkeypatch.setenv("ENABLE_KB_BRANDS", mode)
+    monkeypatch.setenv("ENABLE_KB_SEED", "apply")
     rep = tmp_path / "brands.json"
     assert _attr(brands, "main")(["--report", str(rep)], client=rig.client) == 0
     assert len(rig.fetches) == 2
@@ -1005,7 +1008,11 @@ def test_s16_r23_brands_dry_and_apply(monkeypatch, tmp_path, mode):
     assert rig.fetches[1]["url"].startswith("https://query.wikidata.org/sparql?")
     assert rig.validates == [f["url"] for f in rig.fetches]
     assert all(f["headers"] == rr._REQUEST_HEADERS and f["allow_redirects"] is False for f in rig.fetches)
-    assert rig.client.writes() == []
+    writes = rig.client.writes()
+    if mode == "true":
+        assert writes == []
+    else:
+        assert writes and {w[0] for w in writes} == {"kb_brands"} and {w[1] for w in writes} <= {"upsert", "update"}
     hosts = _report(rep)["hosts"]
     assert len(hosts) == 300 and hosts == sorted(hosts)
     assert "brand-b.example.com" in hosts
@@ -1021,7 +1028,7 @@ def test_s16_r24_brands_robots_failclosed(monkeypatch, tmp_path, caplog, case):
     first = {"403": (403, {}, "forbidden"), "timeout": TimeoutError("t"),
              "disallow": (200, {}, "User-agent: *\nDisallow: /sparql\n")}[case]
     rig.fetch_responses = [first, (200, {}, _brand_bindings())]
-    _dry(monkeypatch)
+    monkeypatch.setenv("ENABLE_KB_BRANDS", "true")
     caplog.set_level(logging.INFO)
     assert _attr(brands, "main")([], client=rig.client) == 0
     assert len(rig.fetches) == 1 and rig.client.writes() == []

```

## 5. Mutation table (33 mutants on byte copies in the scratch worktree; lock file; restore + sha256 verified)

Each run: the RED file + G2 R23 + G2 R24 + schema R27 through pyt.py, bound 600. KILLED = an assertion failure.

| id | mutant | file | failed nodes | killing rows | types |
|---|---|---|---|---|---|
| M01 | brands_max() ignored (cap = 300) | scripts/seed_kb_brands_wikidata.py | 2 | s16b_kb_brands.py::test_s16b_s07_cap_and_order,s16b_kb_brands.py::test_s16b_s09_limit_hit_count | AssertionError |
| M02 | KbWriter.brands update loop removed | scripts/kb_seed_common.py | 3 | s16b_kb_brands.py::test_s16b_s05_rerun_updates_wikidata_rows_only,s16b_kb_brands.py::test_s16b_s10_write_failure_is_quiet | AssertionError |
| M03 | .eq('source', 'wikidata') dropped from the update | scripts/kb_seed_common.py | 2 | s16b_kb_brands.py::test_s16b_s05_rerun_updates_wikidata_rows_only | AssertionError |
| M04 | the update sets source too | app/services/kb_service.py | 3 | s16b_kb_brands.py::test_s16b_k01_census_constants,s16b_kb_brands.py::test_s16b_s05_rerun_updates_wikidata_rows_only | AssertionError |
| M05 | the deny belt dropped from the builder | app/services/kb_service.py | 1 | s16b_kb_brands.py::test_s16b_k04_belt_holds_without_the_rule | AssertionError |
| M06 | kb_source_allowed dropped from the builder | app/services/kb_service.py | 2 | s16b_kb_brands.py::test_s16b_k03_builder_refuses,s16b_kb_brands.py::test_s16b_k05_rule_read_at_call_time | AssertionError |
| M07 | with_label_en not bumped | scripts/seed_kb_brands_wikidata.py | 1 | s16b_kb_brands.py::test_s16b_s03_dry_counts_no_write | AssertionError |
| M08 | the write runs in DRY too | scripts/seed_kb_brands_wikidata.py | 4 | s16_kb_seed.py::test_s16_r23_brands_dry_and_apply,s16b_kb_brands.py::test_s16b_s03_dry_counts_no_write,s16b_kb_brands.py::test_s16b_s04_apply_writes_kb_brands_only,s16b_kb_brands.py::test_s16b_s06_dedupe_and_host_choice | AssertionError |
| M09 | FLAG = ENABLE_KB_SEED | scripts/seed_kb_brands_wikidata.py | 32 | s16_kb_seed.py::test_s16_r23_brands_dry_and_apply,s16_kb_seed.py::test_s16_r24_brands_robots_failclosed,s16b_kb_brands.py::test_s16b_s01_flag_constant_and_table,s16b_kb_brands.py::test_s16b_s02_off_is_inert,s16b_kb_brands.py::test_s16b_s03_dry_counts_no_write,s16b_kb_brands.py::test_s16b_s06_dedupe_and_host_choice | AssertionError |
| M10 | a kb_merchants write in place of writer.brands | scripts/seed_kb_brands_wikidata.py | 7 | s16_kb_seed.py::test_s16_r23_brands_dry_and_apply,s16b_kb_brands.py::test_s16b_s04_apply_writes_kb_brands_only,s16b_kb_brands.py::test_s16b_s05_rerun_updates_wikidata_rows_only,s16b_kb_brands.py::test_s16b_s07_cap_and_order,s16b_kb_brands.py::test_s16b_s10_write_failure_is_quiet | AssertionError |
| M11 | the human exclusion removed | scripts/seed_kb_brands_wikidata.py | 1 | s16b_kb_brands.py::test_s16b_s03_dry_counts_no_write | AssertionError |
| M12 | the en OPTIONAL made mandatory | scripts/seed_kb_brands_wikidata.py | 1 | s16b_kb_brands.py::test_s16b_s03_dry_counts_no_write | AssertionError |
| M13 | the host choice takes the LARGEST valid host | scripts/seed_kb_brands_wikidata.py | 4 | s16b_kb_brands.py::test_s16b_s03_dry_counts_no_write,s16b_kb_brands.py::test_s16b_s04_apply_writes_kb_brands_only,s16b_kb_brands.py::test_s16b_s06_dedupe_and_host_choice | AssertionError |
| M14 | KB_QID_REGEX = ^Q[0-9]{1,12}$ | app/services/kb_service.py | 5 | s16b_kb_brands.py::test_s16b_b04_regex_texts_equal_the_leaf,s16b_kb_brands.py::test_s16b_k01_census_constants,s16b_kb_brands.py::test_s16b_k03_builder_refuses,s16b_kb_brands.py::test_s16b_s06_dedupe_and_host_choice | AssertionError |
| M15 | rows sorted by the qid STRING | scripts/seed_kb_brands_wikidata.py | 4 | s16b_kb_brands.py::test_s16b_s04_apply_writes_kb_brands_only,s16b_kb_brands.py::test_s16b_s06_dedupe_and_host_choice,s16b_kb_brands.py::test_s16b_s07_cap_and_order | AssertionError |
| M16 | the OFF line after resolve_client | scripts/seed_kb_brands_wikidata.py | 21 | s16b_kb_brands.py::test_s16b_s02_off_is_inert | AssertionError |
| M17 | a label in the totals line | scripts/seed_kb_brands_wikidata.py | 1 | s16b_kb_brands.py::test_s16b_s11_no_label_or_host_in_logs | AssertionError |
| M18 | rows built with source operator | scripts/seed_kb_brands_wikidata.py | 4 | s16b_kb_brands.py::test_s16b_s04_apply_writes_kb_brands_only,s16b_kb_brands.py::test_s16b_s05_rerun_updates_wikidata_rows_only,s16b_kb_brands.py::test_s16b_s10_write_failure_is_quiet | AssertionError |
| M19 | service_role dropped from the REVOKE | migrations/052_kb_brands.sql | 1 | s16b_kb_brands.py::test_s16b_b05_service_role_only | AssertionError |
| M20 | GRANT SELECT TO anon added | migrations/052_kb_brands.sql | 1 | s16b_kb_brands.py::test_s16b_b05_service_role_only | AssertionError |
| M21 | the host index UNIQUE | migrations/052_kb_brands.sql | 1 | s16b_kb_brands.py::test_s16b_b07_host_index_not_unique | AssertionError |
| M22 | the trigger statement removed | migrations/052_kb_brands.sql | 1 | s16b_kb_brands.py::test_s16b_b06_trigger_and_045_guard | AssertionError |
| M23 | the !~ deny clause removed | migrations/052_kb_brands.sql | 2 | s16b_kb_brands.py::test_s16b_b03_columns_match_the_leaf,s16b_kb_brands.py::test_s16b_b04_regex_texts_equal_the_leaf | AssertionError |
| M24 | the 045 DO guard removed | migrations/052_kb_brands.sql | 1 | s16b_kb_brands.py::test_s16b_b06_trigger_and_045_guard | AssertionError |
| M25 | DROP FUNCTION kb_set_updated_at added to the rollback | migrations/rollback/052_kb_brands.sql | 1 | s16b_kb_brands.py::test_s16b_b09_rollback_statements | AssertionError |
| M26 | label_ar upper bound 128 -> 256 | migrations/052_kb_brands.sql | 1 | s16b_kb_brands.py::test_s16b_b03_columns_match_the_leaf | AssertionError |
| M27 | label_ar_dropped drops the brand | scripts/seed_kb_brands_wikidata.py | 1 | s16b_kb_brands.py::test_s16b_s06_dedupe_and_host_choice | AssertionError |
| M28 | the write-failed WARNING at ERROR | scripts/seed_kb_brands_wikidata.py | 2 | s16b_kb_brands.py::test_s16b_s10_write_failure_is_quiet | AssertionError |
| M29 | kb_brands FIRST in KB_TABLES | app/services/kb_service.py | 12 | kb_schema.py::test_s14_r27_builder_keys,s16b_kb_brands.py::test_s16b_k01_census_constants,s16b_kb_brands.py::test_s16b_pin3_the_045_census_unchanged | AssertionError |
| M30 | derive_hosts caps at brands_max() | scripts/seed_kb_brands_wikidata.py | 2 | s16b_kb_brands.py::test_s16b_pin2_host_derivation_literal,s16b_kb_brands.py::test_s16b_s07_cap_and_order | AssertionError |
| M31 | official_host only from the NEW host list | scripts/seed_kb_brands_wikidata.py | 3 | s16b_kb_brands.py::test_s16b_s04_apply_writes_kb_brands_only,s16b_kb_brands.py::test_s16b_s06_dedupe_and_host_choice | AssertionError |
| M32 | qid_of returns the full IRI | scripts/seed_kb_brands_wikidata.py | 11 | s16b_kb_brands.py::test_s16b_s03_dry_counts_no_write,s16b_kb_brands.py::test_s16b_s04_apply_writes_kb_brands_only,s16b_kb_brands.py::test_s16b_s05_rerun_updates_wikidata_rows_only,s16b_kb_brands.py::test_s16b_s06_dedupe_and_host_choice,s16b_kb_brands.py::test_s16b_s07_cap_and_order,s16b_kb_brands.py::test_s16b_s09_limit_hit_count,s16b_kb_brands.py::test_s16b_s10_write_failure_is_quiet,s16b_kb_brands.py::test_s16b_s11_no_label_or_host_in_logs | AssertionError |
| M33 | the mul fallback dropped | scripts/seed_kb_brands_wikidata.py | 4 | s16b_kb_brands.py::test_s16b_s03_dry_counts_no_write,s16b_kb_brands.py::test_s16b_s04_apply_writes_kb_brands_only,s16b_kb_brands.py::test_s16b_s06_dedupe_and_host_choice | AssertionError |

Result: 33 / 33 KILLED, 0 survived, no equivalent claimed (M05 is killed by K04, whose rule patch opens the deny rule on purpose; under the production rule M05 is equivalent, the R-S14-6 precedent).

Mutation [pyt] lines:
    [pyt] tag=s16b-mut-M01 start=2026-11-04 20:37:12 end=2026-11-04 20:37:22 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M01.log
    [pyt] tag=s16b-mut-M02 start=2026-11-04 20:37:23 end=2026-11-04 20:37:36 elapsed=13s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M02.log
    [pyt] tag=s16b-mut-M03 start=2026-11-04 20:37:36 end=2026-11-04 20:37:53 elapsed=17s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M03.log
    [pyt] tag=s16b-mut-M04 start=2026-11-04 20:37:54 end=2026-11-04 20:38:13 elapsed=19s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M04.log
    [pyt] tag=s16b-mut-M05 start=2026-11-04 20:38:14 end=2026-11-04 20:38:24 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M05.log
    [pyt] tag=s16b-mut-M06 start=2026-11-04 20:38:24 end=2026-11-04 20:38:32 elapsed=8s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M06.log
    [pyt] tag=s16b-mut-M07 start=2026-11-04 20:38:32 end=2026-11-04 20:38:42 elapsed=9s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M07.log
    [pyt] tag=s16b-mut-M08 start=2026-11-04 20:38:43 end=2026-11-04 20:38:54 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M08.log
    [pyt] tag=s16b-mut-M09 start=2026-11-04 20:38:55 end=2026-11-04 20:39:04 elapsed=9s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M09.log
    [pyt] tag=s16b-mut-M10 start=2026-11-04 20:39:04 end=2026-11-04 20:39:13 elapsed=9s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M10.log
    [pyt] tag=s16b-mut-M11 start=2026-11-04 20:39:14 end=2026-11-04 20:39:24 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M11.log
    [pyt] tag=s16b-mut-M12 start=2026-11-04 20:39:25 end=2026-11-04 20:39:34 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M12.log
    [pyt] tag=s16b-mut-M13 start=2026-11-04 20:39:35 end=2026-11-04 20:39:45 elapsed=10s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M13.log
    [pyt] tag=s16b-mut-M14 start=2026-11-04 20:39:45 end=2026-11-04 20:39:56 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M14.log
    [pyt] tag=s16b-mut-M15 start=2026-11-04 20:39:57 end=2026-11-04 20:40:07 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M15.log
    [pyt] tag=s16b-mut-M16 start=2026-11-04 20:40:08 end=2026-11-04 20:40:21 elapsed=13s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M16.log
    [pyt] tag=s16b-mut-M17 start=2026-11-04 20:40:22 end=2026-11-04 20:40:42 elapsed=20s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M17.log
    [pyt] tag=s16b-mut-M18 start=2026-11-04 20:40:43 end=2026-11-04 20:40:56 elapsed=13s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M18.log
    [pyt] tag=s16b-mut-M19 start=2026-11-04 20:40:57 end=2026-11-04 20:41:14 elapsed=17s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M19.log
    [pyt] tag=s16b-mut-M20 start=2026-11-04 20:41:14 end=2026-11-04 20:41:28 elapsed=14s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M20.log
    [pyt] tag=s16b-mut-M21 start=2026-11-04 20:41:29 end=2026-11-04 20:41:43 elapsed=14s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M21.log
    [pyt] tag=s16b-mut-M22 start=2026-11-04 20:41:43 end=2026-11-04 20:41:57 elapsed=14s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M22.log
    [pyt] tag=s16b-mut-M23 start=2026-11-04 20:41:58 end=2026-11-04 20:42:11 elapsed=13s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M23.log
    [pyt] tag=s16b-mut-M24 start=2026-11-04 20:42:12 end=2026-11-04 20:42:25 elapsed=13s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M24.log
    [pyt] tag=s16b-mut-M25 start=2026-11-04 20:42:25 end=2026-11-04 20:42:38 elapsed=13s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M25.log
    [pyt] tag=s16b-mut-M26 start=2026-11-04 20:42:38 end=2026-11-04 20:42:52 elapsed=14s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M26.log
    [pyt] tag=s16b-mut-M27 start=2026-11-04 20:42:53 end=2026-11-04 20:43:15 elapsed=21s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M27.log
    [pyt] tag=s16b-mut-M28 start=2026-11-04 20:43:17 end=2026-11-04 20:43:29 elapsed=11s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M28.log
    [pyt] tag=s16b-mut-M29 start=2026-11-04 20:43:31 end=2026-11-04 20:43:44 elapsed=13s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M29.log
    [pyt] tag=s16b-mut-M30 start=2026-11-04 20:43:45 end=2026-11-04 20:43:56 elapsed=12s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M30.log
    [pyt] tag=s16b-mut-M31 start=2026-11-04 20:43:58 end=2026-11-04 20:44:13 elapsed=15s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M31.log
    [pyt] tag=s16b-mut-M32 start=2026-11-04 20:44:14 end=2026-11-04 20:44:26 elapsed=13s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M32.log
    [pyt] tag=s16b-mut-M33 start=2026-11-04 20:44:27 end=2026-11-04 20:44:39 elapsed=12s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\mutants\M33.log

## 6. Comm set and base record

- Re-derived once by the union rule (comm_plan.py: the spec 7.1 module list UNION the source scanners UNION the common brief's named pins (test_model_config*, prompt_fence, u3c, migration_index_predicate, openai_key_log, sentry_channels, ci_gates, behavior_dimension_translation, secret_scan_static, start_command*) MINUS the test_precommit_hook*.py files and the RED file): 302 members, set sha256 c57341827e783b49d685423cb557ac102315428afebcabd4508a7fb257d63479; vs the spec's 302-file list: 0 added, 0 dropped (identical). COMM_SET.txt and comm_reasons.tsv in S81-16b_red/. Head set = base + the RED file (303, sha fcceee0b..., the spec's).
- GC-9 per-file reuse of 744616e3/ba26af35: 92 reused, 210 run at base (incl. test_secret_scan_static.py ALONE, run although reusable); 744616e3..0b19de5b changed 15 files.
- Stored: harness/base_records/0b19de5bcc1416111d48bc725359b95151a658ca/c57341827e783b49d685423cb557ac102315428afebcabd4508a7fb257d63479.{txt,files,pyt.log,header.txt} (the G4 RED's 661-file record shares the folder under its own set hash; nothing of it was touched).
- Base failures in the set: 8 (run 6, reused 2):
    tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
    tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
    tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]

Comm [pyt] lines (progress.txt):
    2026-11-04 20:47:22 WAIT another lane's pytest is running before s16b-red-secret
    2026-11-04 20:56:07 [pyt] tag=s16b-red-secret start=2026-11-04 20:55:47 end=2026-11-04 20:56:07 elapsed=21s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\comm\s16b-red-secret.log
    2026-11-04 20:56:08 WAIT another lane's pytest is running before s16b-red-comm-00
    2026-11-04 20:57:31 [pyt] tag=s16b-red-comm-00 start=2026-11-04 20:56:40 end=2026-11-04 20:57:31 elapsed=51s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\comm\s16b-red-comm-00.log
    2026-11-04 20:57:49 [pyt] tag=s16b-red-comm-01 start=2026-11-04 20:57:32 end=2026-11-04 20:57:48 elapsed=16s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\comm\s16b-red-comm-01.log
    2026-11-04 20:59:55 [pyt] tag=s16b-red-comm-02 start=2026-11-04 20:57:50 end=2026-11-04 20:59:55 elapsed=125s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\comm\s16b-red-comm-02.log
    2026-11-04 21:00:43 [pyt] tag=s16b-red-comm-03 start=2026-11-04 20:59:56 end=2026-11-04 21:00:42 elapsed=46s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\comm\s16b-red-comm-03.log
    2026-11-04 21:02:24 [pyt] tag=s16b-red-comm-04 start=2026-11-04 21:00:49 end=2026-11-04 21:02:23 elapsed=94s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\comm\s16b-red-comm-04.log
    2026-11-04 21:05:01 [pyt] tag=s16b-red-comm-05 start=2026-11-04 21:02:30 end=2026-11-04 21:05:01 elapsed=151s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\comm\s16b-red-comm-05.log
    2026-11-04 21:08:34 [pyt] tag=s16b-red-comm-06 start=2026-11-04 21:05:02 end=2026-11-04 21:08:33 elapsed=211s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\comm\s16b-red-comm-06.log
    2026-11-04 21:10:08 [pyt] tag=s16b-red-comm-07 start=2026-11-04 21:08:41 end=2026-11-04 21:10:07 elapsed=86s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\comm\s16b-red-comm-07.log
    2026-11-04 21:10:17 [pyt] tag=s16b-red-comm-08 start=2026-11-04 21:10:10 end=2026-11-04 21:10:17 elapsed=7s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-16b_red\comm\s16b-red-comm-08.log

## 7. G5 / G6 at base (real worktree, flags unset)

    [hermeticity] sentinel checked 845 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    5 failed, 840 passed, 4 deselected, 11 warnings in 30.38s

5 failed = the five G2 R27 CRLF nodes (environmental F1-3, as the spec's 1.10 and the review measured); 845 nodes = schema 529 + G2 140 + G2 gate rows 9 + sqlfluff_config 11 + index 46 + 043 51 + 037 + w1_2d + w1_2c + 044 (4 deselected by the runner's marker filter).

## 8. Restore check

- HEAD 0b19de5bcc1416111d48bc725359b95151a658ca (= base)
- git diff --name-only HEAD (tracked files vs base, autocrlf-normalised): 0 files
- untracked: ?? tests/test_s81_s16b_kb_brands.py 
- scratch worktree S81-16b_red/w: removed with git worktree remove --force; git worktree list shows it 0 times; the directory exists: no
- mutation lock: removed by the harness (no .qa-mutation.lock anywhere); 33 restores sha256-verified against proto_sha_before_mut.txt
- orphan pytest of this agent: 0
- no tracked file in sc-s81-s16b was edited; no git write command ran there (the only git writes were worktree add/remove of my own detached scratch and an intent-to-add inside that scratch)


git status --short (real worktree):

    ?? tests/test_s81_s16b_kb_brands.py

git worktree list (no S81-16b_red scratch):
    C:/Users/SynAckITPC/Documents/AI/sc-s81-s16b                                                                                                    0b19de5b (detached HEAD)

## 9. Deviations, choices and questions for the gate

Deviations (stated, not hidden):
- D1 CONCURRENCY: the G4 RED lane's comm driver (S81-G4_red/tools/comm_driver, chunks g4red-comm-00..) was running while my mutation harness (33 pyt runs in my scratch worktree, 20:37-20:44) and my G5/G6 base run (20:45:55-20:46:28, real worktree sc-s81-s16b) ran; I had checked for a live pytest only before the first base run (none then). Different worktrees and files; no DUPLICATE tag, no killed process; every one of my results is internally consistent. From 20:47 my comm driver waits until no other lane's pytest / comm driver is alive before each chunk.
- D2 S04 dry-run node: the spec's "--dry-run present -> writes() == []" alone would PASS at base; the node also asserts the report's literal brands list so it is RED at base.
- D3 S09 is one node (2000 then 1999 bindings in one test) so the 1999 half cannot pass at base on its own.
- D4 S02 parametrisation = s16.OFF_SPELLINGS + "dry" (8) x ENABLE_KB_SEED in {apply, true, unset} = 24 nodes; main is driven through a SystemExit catcher so the base argparse exit is an AssertionError, not a SystemExit.
- D5 K03 holds 35 ids (29 of the review + 3 blank / padded rows per label, R-S16B-6/7); K02 holds 7 (the 253-char host added).
- D6 B11 lints in-process (sqlfluff.core Linter + FluffConfig.from_path(ROOT), the repo .sqlfluff), measured on the pinned sqlfluff 4.3.0.
- D7 B04 also asserts the two btrim clauses; B10 asserts no "051" text in either 052 file.
Choices the RED pins (the gate may rule otherwise; GREEN must follow the RED):
- C1 with_label_en / with_label_ar count DISTINCT qids carrying the exact en / ar label; a mul-only brand counts label_en_from_mul, not with_label_en.
- C2 an en label present but refused by the builder (129 chars) counts no_label_en and does NOT fall back to mul.
- C3 S03 pins the WHOLE counts dict: {bindings, with_site, new, with_label_en, with_label_ar, label_en_from_mul, no_label_en, brand_rows}; derive-side counters are bump-style (absent at 0); brand_rows always present; over_cap_brands / sparql_limit_hit absent when not hit; sparql_limit_hit when len(bindings) == 2000 exactly.
- C4 the btrim clauses are MERGED into the label_en / label_ar column CHECKs (B03 literal): label_en ... BETWEEN 1 AND 128 AND label_en = btrim(label_en); label_ar IS NULL OR (... AND label_ar = btrim(label_ar)); POSTCHECK check_count stays 6.
- C5 the SPARQL text binds ?label_mul with OPTIONAL { ?brand rdfs:label ?label_mul . FILTER(LANG(?label_mul) = "mul") } (S03 pins all three OPTIONAL clauses verbatim, the human exclusion, the ORDER BY xsd:integer(STRAFTER(STR(?brand), "/entity/Q")) ?site and LIMIT 2000).
- C6 the report's brands entries are {qid, label_en, label_ar, official_host} (S03/S04/S06/S07/S11); the writer counters kb_brands_sent / brand_updates (and not_built) are ADDED to counts; write_failed = 1 on a write exception.
- C7 the builder refuses a label that differs from its Python strip() (every whitespace kind), stricter than btrim (spaces only): a superset, as the house rule wants.
- C8 S12 requires the brand script's docstring to name ENABLE_KB_BRANDS (beyond "no DRY-ONLY / writes NOTHING").
Questions:
- Q1 confirm C1-C3 (the counter semantics) before GREEN; they are pinned by literal dicts.
- Q2 the spec's EK1 (an APPLY R23 over 300+ brands) now writes through KbWriter.brands in the prototype and stays green; no other frozen row needed an edit beyond EK0-EK2 + E1 (measured).


## 10. Not measured

- The expected Wikidata row count (offline; the DRY counts are the owner's check).
- G9 (local PostgreSQL), the fourteen client fences, the full jest: GREEN's.
