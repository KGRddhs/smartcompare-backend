-- migrations/020_comparisons_schema_version.sql
-- Add schema_version to comparisons table.
-- v1 = legacy rows (pre-structured-response). Hidden from history list.
-- v2 = full structured response. Renderable in ResultsScreen.
-- Bumped on every breaking shape change to the ResultsScreen contract.

ALTER TABLE comparisons
  ADD COLUMN IF NOT EXISTS schema_version INT NOT NULL DEFAULT 1;

-- Future inserts default to v2 (after this ALTER).
ALTER TABLE comparisons
  ALTER COLUMN schema_version SET DEFAULT 2;

-- Index for fast "list user's v2 history newest-first"
CREATE INDEX IF NOT EXISTS idx_comparisons_user_schema
  ON comparisons (user_id, schema_version, created_at DESC);

COMMENT ON COLUMN comparisons.schema_version IS
  'v1 = legacy pre-structured-response (hidden from history). v2 = full structured response, renderable.';
