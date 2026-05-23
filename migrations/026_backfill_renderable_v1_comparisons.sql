-- Migration 026: Backfill renderable schema_version=1 comparisons to v2
--
-- Bundle D Task: R3 (history detail fail) RCA outcome.
--
-- Discovery (2026-05-23 via Supabase MCP, Backend lane):
-- - 8 rows in `comparisons` have schema_version=1, ALL pre-date Migration 020.
-- - 7 of those rows have the same renderable shape as v2 rows
--   (products array of length 2, both with non-empty name, metadata.query
--   non-empty) — they pass exactly the predicate `_validate_renderable`
--   uses in `app/services/database_service.py` to gate writes.
-- - 1 row (id=e154397c-a77f-4203-91c5-ed050c999429, "Sony WH-1000XM5 vs
--   Bose QuietComfort Ultra", 2026-05-05) has only a `metadata` top-level
--   key, n_products=0 — a failed save. INTENTIONALLY LEFT v1 (filtered).
--
-- The history list/get/count queries filter on schema_version=2, hiding
-- the renderable v1 rows. Backfilling is the right fix per the design:
-- Bundle A §5.2 + R3 recipe (anchor) — "if v1 → backfill, NOT new screen
-- code." This migration is data-only; no schema change, no read-path
-- change, no FE code touched.
--
-- Authorization: Bundle D dispatcher PR comment (TBD).
--
-- Rollback: see migrations/rollback/026_backfill_renderable_v1_comparisons.sql
--           which flips the same 7 UUIDs back to schema_version=1.

BEGIN;

-- Predicate-gated update — applies the same _validate_renderable check
-- the Python code uses. Even if extra v1 rows were inserted between
-- discovery and migration apply, only renderable ones get bumped.
UPDATE comparisons
SET schema_version = 2
WHERE schema_version = 1
  -- Predicate (a): products array length >= 2 (matches Python `len(products) < 2` reject)
  AND jsonb_typeof(
        COALESCE(full_response->'products', full_response#>'{overview,products}', '[]'::jsonb)
      ) = 'array'
  AND jsonb_array_length(
        COALESCE(full_response->'products', full_response#>'{overview,products}', '[]'::jsonb)
      ) >= 2
  -- Predicate (b): products[0..1] each have non-empty name
  AND (
        COALESCE(full_response->'products', full_response#>'{overview,products}')->0->>'name'
      ) IS NOT NULL
  AND (
        COALESCE(full_response->'products', full_response#>'{overview,products}')->0->>'name'
      ) <> ''
  AND (
        COALESCE(full_response->'products', full_response#>'{overview,products}')->1->>'name'
      ) IS NOT NULL
  AND (
        COALESCE(full_response->'products', full_response#>'{overview,products}')->1->>'name'
      ) <> ''
  -- Predicate (c): metadata.query non-empty
  AND (full_response#>>'{metadata,query}') IS NOT NULL
  AND (full_response#>>'{metadata,query}') <> '';

-- Post-update verification: expected count is 7 (from 2026-05-23 discovery).
-- The unrenderable Sony/Bose row must remain v1 with this query returning 1.
DO $$
DECLARE
  remaining_v1 integer;
  unrenderable_v1 integer;
BEGIN
  SELECT COUNT(*) INTO remaining_v1 FROM comparisons WHERE schema_version = 1;
  -- Specifically check the known unrenderable row is still v1
  SELECT COUNT(*) INTO unrenderable_v1
  FROM comparisons
  WHERE id = 'e154397c-a77f-4203-91c5-ed050c999429'
    AND schema_version = 1;
  RAISE NOTICE 'Post-backfill: % v1 rows remain (expected: 1 — the known unrenderable Sony/Bose row); known unrenderable still v1: % (expected: 1)', remaining_v1, unrenderable_v1;
END $$;

COMMIT;
