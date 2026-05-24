-- Rollback for Migration 026: revert the 7 backfilled rows to schema_version=1
--
-- This rollback ONLY targets the 7 specific UUIDs we backfilled on 2026-05-23.
-- It uses explicit UUIDs (NOT the predicate) so a rollback after fresh v2
-- inserts cannot accidentally demote them.
--
-- The unrenderable row (e154397c-a77f-4203-91c5-ed050c999429) was NEVER
-- touched by 025, so it's not in this list either.

BEGIN;

UPDATE comparisons
SET schema_version = 1
WHERE id IN (
  '1a65b17f-a083-46b5-a7f9-d4d1cf3779e2',  -- Apple iPhone 14 vs Samsung Galaxy S24 Ultra (2026-05-08)
  '6ff5f5b4-0d29-48df-bb3f-6128f481b245',  -- iPhone 15 vs Galaxy S24 (2026-05-05, user 8fbc1548)
  '4b4ad16a-de31-4e85-ae8b-9326b43f348c',  -- iPhone 15 vs Galaxy S24 (2026-05-05, 03:08)
  'eaf479bb-22b3-4171-b047-94bbc48a3e8d',  -- iPhone 15 vs Galaxy S24 (2026-05-05, 03:06)
  '8c115710-54e6-4337-bca6-1e7f732e2e85',  -- LV Mesh Cap vs Hermès cap (2026-03-19)
  '1390cedf-14b1-4cf3-86bb-75dec6cf5af0',  -- LV Mesh Cap vs Hermès cap (2026-03-18)
  '894d1926-9c44-4935-9c45-b6a6a5dc7e11'   -- HealthAid Vit D3 vs NOW Vit D-3 (2026-03-13)
);

DO $$
DECLARE
  reverted integer;
BEGIN
  SELECT COUNT(*) INTO reverted FROM comparisons
  WHERE id IN (
    '1a65b17f-a083-46b5-a7f9-d4d1cf3779e2',
    '6ff5f5b4-0d29-48df-bb3f-6128f481b245',
    '4b4ad16a-de31-4e85-ae8b-9326b43f348c',
    'eaf479bb-22b3-4171-b047-94bbc48a3e8d',
    '8c115710-54e6-4337-bca6-1e7f732e2e85',
    '1390cedf-14b1-4cf3-86bb-75dec6cf5af0',
    '894d1926-9c44-4935-9c45-b6a6a5dc7e11'
  ) AND schema_version = 1;
  RAISE NOTICE 'Rollback: % of 7 target rows reverted to schema_version=1', reverted;
END $$;

COMMIT;
