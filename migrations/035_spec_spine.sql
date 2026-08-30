-- Migration 035: spec_spine — the amortised fragrance spec index (UNIT D2)
--
-- ############################################################################
-- ## NOT APPLIED. This file is written, committed and DELIBERATELY UNRUN.    ##
-- ## Nothing in the shipped code path requires it: `spec_spine_service`      ##
-- ## reads the local JSON store `data/spec_spine.json` and only ever touches ##
-- ## Supabase when BOTH `ENABLE_SPEC_SPINE` is on AND `SPEC_SPINE_TABLE`     ##
-- ## names a table (`_supabase_table()`), which is unset everywhere today.   ##
-- ## Apply this only when the store has outgrown a file — see ROLLOUT ORDER. ##
-- ############################################################################
--
-- WHY A TABLE EVENTUALLY. The spine is a per-FRAGRANCE record of facts that do
-- not change between comparisons (scent family, the note pyramid,
-- concentration, longevity/sillage, season/occasion), seeded off-clock by
-- `scripts/seed_spec_spine.py` from PDP prose already cached on disk. As a
-- file it is perfect for the first few hundred rows: it ships in the repo,
-- diffs in review, and costs one stat() per lookup. It stops being perfect
-- the moment (a) more than one process seeds, (b) the seeder runs on Railway
-- rather than a workstation, or (c) rows outnumber what anyone wants to read
-- in a pull request. Postgres is where it goes then — NOT before, because a
-- table that no code reads is schema debt with a monitoring cost.
--
-- WHY `spine_key` IS THE PRIMARY KEY, not a surrogate id. The key IS the
-- identity: `spec_spine_service.spine_key` composes the price path's own
-- identity machinery (`_identity_tokens_ps` minus the fragrance padding, the
-- brand alias groups, `extract_concentration`, `extract_size_ml_any`) into a
-- deterministic string such as
--     fragrances|christian+dior|sauvage|EDP|100
-- Two retailer titles for one juice produce the same string; an EDP and an EDT
-- produce different ones. A surrogate id would invite a second row for the same
-- fragrance and there would be no constraint left to notice.
--
-- WHY `specs` IS jsonb, not columns. The served field set is deliberately
-- narrow and deliberately UNSTABLE at the edges — B5 measured `perfumer`
-- (13/79 corpus pages) and `launch_year` (7/79) as too sparse to ship, and
-- either could become viable with a licensed source later. `SPINE_FIELDS` in
-- the service is the single authority on what is read back; a jsonb column
-- lets that list move without a migration, and the service's `_entry_specs`
-- already drops anything not in it (so a stray key in a row can never leak
-- into a response).
--
-- RLS POSTURE: enabled, service-role only, mirroring migration 032's stance on
-- `products`. The spine holds no user data, but the anon key has no business
-- reading or writing a table the backend seeds; a single permissive
-- FOR ALL TO service_role policy keeps the admin client working (it bypasses
-- RLS regardless) while giving anon exactly zero access.
--
-- ROLLOUT ORDER (important, and the same shape as migration 033's):
--   1. apply THIS migration,
--   2. seed the table (port the JSON store, or point the seeder at it),
--   3. THEN set `SPEC_SPINE_TABLE=spec_spine` in Railway,
--   4. and only then flip `ENABLE_SPEC_SPINE=true`.
-- Reversing 3 and 1 is not a crash — `_lookup_supabase_sync` swallows the
-- error and falls back to the local JSON store — but it is a silent, permanent
-- fallback that looks like a working Supabase spine, which is worse than a
-- loud failure. Do it in order.
--
-- Rollback: migrations/rollback/035_spec_spine.sql
-- Additive, new table only, no backfill, no lock on any existing object.

BEGIN;

CREATE TABLE IF NOT EXISTS public.spec_spine (
    -- The normalised fragrance identity produced by
    -- app/services/spec_spine_service.spine_key(). See the header for the
    -- shape and for why it is the primary key.
    spine_key   TEXT PRIMARY KEY,

    -- Human-readable provenance of the identity, for debugging a surprising
    -- key. NEVER read back into a response — the response's brand/model come
    -- from the user's own query, exactly as in extract_specs.
    brand       TEXT,
    name        TEXT,

    -- {field: value} for the fields in spec_spine_service.SPINE_FIELDS ONLY.
    -- Written by scripts/seed_spec_spine.py, which keeps a field only when the
    -- model cited a snippet for it (the A3 no-fabrication contract).
    specs       JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- How many cached PDPs the seed extraction was allowed to cite, and which
    -- ones. A one-page seed is weaker evidence than a four-page one; keeping
    -- the count makes a future "re-seed the thin rows" pass a query.
    seed_pages  INT  NOT NULL DEFAULT 0,
    seed_urls   JSONB NOT NULL DEFAULT '[]'::jsonb,

    seeded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- The only query the service issues is an equality lookup on the primary key,
-- which the PK index already serves. No secondary index is created here: an
-- index nothing queries is write cost and vacuum surface for nothing. Add one
-- when a real access pattern (e.g. "re-seed everything older than N days")
-- exists, not in anticipation of it.

ALTER TABLE public.spec_spine ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS spec_spine_service_role_all ON public.spec_spine;
CREATE POLICY spec_spine_service_role_all
    ON public.spec_spine
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

COMMENT ON TABLE public.spec_spine IS
    'UNIT D2 amortised fragrance spec spine. One row per fragrance identity '
    '(spec_spine_service.spine_key). Seeded off-clock by '
    'scripts/seed_spec_spine.py from cached PDP prose under a citation-or-omit '
    'prompt; read by spec_spine_service only when ENABLE_SPEC_SPINE is on AND '
    'SPEC_SPINE_TABLE names this table.';

COMMIT;
