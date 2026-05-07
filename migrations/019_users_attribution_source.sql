-- 019_users_attribution_source.sql
-- Adds attribution_source column to users for "Where did you hear about us?"
-- step 11 of the new 17-screen onboarding (design Section 2 + plan task 8).
--
-- Apply via Supabase MCP `apply_migration` — NEVER SQL Editor (per CLAUDE.md
-- gotcha; multi-statement scripts wrap in a transaction and a failing view
-- can roll back the ALTER before it).

-- Single column add, idempotent. CHECK constraint mirrors the Pydantic enum
-- in app/api/auth_routes.py::AttributionBody so the DB rejects malformed
-- writes even if a future code path bypasses the route validator.
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS attribution_source TEXT
  CHECK (
    attribution_source IS NULL
    OR attribution_source IN ('friend', 'instagram', 'tiktok', 'app_store', 'google', 'other')
  );

-- No index — this is write-once-read-rarely (analytics query scans full
-- table monthly). Index on a low-cardinality 6-value column would not help.
