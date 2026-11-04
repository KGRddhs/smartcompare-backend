-- Rollback for migration 052_kb_brands.sql (S81-16b KB-BRANDS)
--
-- Run no ENABLE_KB_BRANDS=apply command while this runs (the import is the
-- only writer). Run this BEFORE any rollback of 045: the kb_brands trigger
-- depends on the 045 function public.kb_set_updated_at, which this file
-- keeps. The table's trigger, index and checks go with the table.
--
-- IMPORTANT: destructive. Every brand row is lost; re-applying 052 and
-- re-running the import (ENABLE_KB_BRANDS=apply) restores the Wikidata rows,
-- never the 'operator' rows.

BEGIN;

DROP TABLE IF EXISTS public.kb_brands;

COMMIT;
