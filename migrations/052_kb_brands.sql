-- Migration 052: public.kb_brands, the fragrance brand entities imported from Wikidata (S81-16b KB-BRANDS)
--
-- One row per brand entity, keyed by the Wikidata item id (qid, no leading
-- zero, so one item has one key): the English label (required; the en label,
-- else the default-language mul label), the Arabic label (NULL when Wikidata
-- has none), the official-site host (NULL when the item has no usable official
-- website) and the row source ('wikidata' for the import, 'operator' for a
-- hand-curated row). Rows are built by app/services/kb_service.py
-- build_brand_row and written only by scripts/seed_kb_brands_wikidata.py under
-- ENABLE_KB_BRANDS=apply: insert-ignore on qid, then ONE update of the label
-- and host columns of each 'wikidata' row the insert did not return. An
-- 'operator' row is never updated by the import and nothing is ever deleted.
-- Wikidata structured data is CC0 (public domain dedication): no attribution
-- or share-alike duty attaches to these rows; the source column records the
-- provenance. kb_products.brand stays free text: no foreign key, no alias and
-- no product link here (later units). A house and its sub-brand may share one
-- official site, so official_host is indexed but NOT UNIQUE.
--
-- MERGING THIS CHANGES NOTHING IN PRODUCTION: the file is written, not
-- applied; no request-path code reads or writes kb_brands, and its one writer
-- runs only as a one-off command with ENABLE_KB_BRANDS=apply.
--
-- APPLY ORDER: after 045 (it reuses public.kb_set_updated_at and the 045 host
-- belts; the DO block below refuses to run without 045); no dependency on 047
-- or 050. Roll 052 back BEFORE any rollback of 045: the kb_brands trigger
-- depends on the 045 trigger function.
--
-- Service role only (the 045 pattern and the 037 both-readings rule): row
-- level security on with no policy; REVOKE ALL from PUBLIC, anon,
-- authenticated and service_role, then GRANT SELECT, INSERT, UPDATE, DELETE
-- to service_role. No user, device, session or address column and no foreign
-- key to users, so the 043 deletion fence does not apply. The import excludes
-- Wikidata items that are humans (P31 Q5): a label is a brand or company name,
-- never a person's name.
--
-- Both labels are trimmed (label = btrim(label)): a blank or padded label is
-- refused here and, more strictly (every whitespace kind), by the builder.
-- The official_host CHECK mirrors the 045 host belts: the host regex
-- (kb_service.KB_HOST_REGEX), the deny label belt (kb_host_deny_regex, a
-- strict subset of deny_hosts.kb_source_allowed, which the builder applies)
-- and the top-label rule (KB_HOST_TOP_LABEL_REGEX).
--
-- Postcheck: APPLY_052_3_POSTCHECK.sql. Rollback: migrations/rollback/052_kb_brands.sql

BEGIN;

DO $$
BEGIN
  IF to_regprocedure('public.kb_set_updated_at()') IS NULL THEN
    RAISE EXCEPTION '052 needs 045 applied first (public.kb_set_updated_at is missing)';
  END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.kb_brands (
    qid text PRIMARY KEY CHECK (qid ~ '^Q[1-9][0-9]{0,11}$'),
    label_en text NOT NULL CHECK (
        char_length(label_en) BETWEEN 1 AND 128 AND label_en = btrim(label_en)
    ),
    label_ar text CHECK (
        label_ar IS NULL OR (
            char_length(label_ar) BETWEEN 1 AND 128 AND label_ar = btrim(label_ar)
        )
    ),
    official_host text CHECK (
        official_host IS NULL OR (
            char_length(official_host) BETWEEN 1 AND 253
            AND official_host ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'
            AND official_host !~ '(^|[.])(basenotes|fimgs|fragrantica|parfumo)[.]'
        )
    ),
    source text NOT NULL DEFAULT 'wikidata' CHECK (source IN ('wikidata', 'operator')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kb_brands_host_top_label_letter CHECK (
        official_host IS NULL
        OR official_host ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)'
    )
);

CREATE INDEX IF NOT EXISTS idx_kb_brands_official_host
    ON public.kb_brands (official_host) WHERE official_host IS NOT NULL;

CREATE OR REPLACE TRIGGER kb_brands_set_updated_at
BEFORE UPDATE ON public.kb_brands
FOR EACH ROW EXECUTE FUNCTION public.kb_set_updated_at();

ALTER TABLE public.kb_brands ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.kb_brands FROM PUBLIC, anon, authenticated, service_role;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_brands TO service_role;

COMMENT ON TABLE public.kb_brands IS
'Fragrance brand entities imported from Wikidata (CC0) by scripts/seed_kb_brands_wikidata.py (S81-16b). No user data. Service role only.';

COMMIT;
