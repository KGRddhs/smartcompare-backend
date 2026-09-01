-- 036_home_savings_aggregate.sql
-- #116 (M18 LS-event-loop-01) — move the /home/savings aggregate server-side.
--
-- GET /api/v1/home/savings previously SELECTed EVERY full_response blob for a
-- user (no LIMIT, no projection) and summed two floats per row in Python on
-- the event loop — unbounded in rows AND payload, growing with history
-- forever. This function computes the same aggregate in Postgres in one small
-- round trip.
--
-- Semantics mirror app/api/home_routes.py:_extract_winner_loser_prices
-- exactly:
--   * only schema_version = 2 rows for the user (Migration 020 invariant)
--   * winner_index must be JSON 0 or 1 (anything else: row skipped)
--   * BOTH winner and loser prices must be labelled 'BHD' (single-currency
--     rule; non-BHD rows are skipped, never converted)
--   * non-numeric / null amounts are skipped, never coerced
--   * per-row contribution = GREATEST(loser - winner, 0) — a pricier winner
--     contributes 0, never a negative
--   * decisions_count counts ONLY contributing rows (the Python code's
--     behaviour; its old comment claimed otherwise and was corrected)
--
-- Known deliberate skew vs Python (malformed legacy rows only): a winner_index
-- stored as the JSON STRING "0"/"1" is accepted here (->> flattens both) but
-- rejected by the Python `in (0, 1)` check. v2 rows write integer indices, so
-- no renderable row diverges.
--
-- SECURITY DEFINER (the delete_user_cascade / increment_lifetime_comparisons
-- precedent): callable through the RLS-scoped user client; the aggregate is
-- scoped strictly by p_user_id, which the route always passes as the
-- authenticated user's id.
--
-- Apply via Supabase MCP (apply_migration). NOT applied at commit time — the
-- consuming code path is dark behind ENABLE_HOME_SAVINGS_AGGREGATE (default
-- OFF) and an unused function is inert. After apply, verify against
-- information_schema.routines (the SQL Editor wraps multi-statement scripts in
-- one transaction; a later failure silently rolls back earlier statements).

CREATE OR REPLACE FUNCTION public.home_savings_aggregate(p_user_id uuid)
RETURNS TABLE (savings_bhd numeric, decisions_count integer)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  WITH candidate AS (
    SELECT
      (c.full_response ->> 'winner_index')::int AS widx,
      c.full_response -> 'products' AS products
    FROM comparisons c
    WHERE c.user_id = p_user_id
      AND c.schema_version = 2
      AND jsonb_typeof(c.full_response) = 'object'
      AND jsonb_typeof(c.full_response -> 'products') = 'array'
      AND jsonb_array_length(c.full_response -> 'products') >= 2
      AND (c.full_response ->> 'winner_index') IN ('0', '1')
  ),
  priced AS (
    SELECT
      (products -> widx -> 'price' ->> 'amount')::numeric        AS winner_amt,
      (products -> (1 - widx) -> 'price' ->> 'amount')::numeric  AS loser_amt
    FROM candidate
    WHERE products -> widx -> 'price' ->> 'currency' = 'BHD'
      AND products -> (1 - widx) -> 'price' ->> 'currency' = 'BHD'
      -- numeric-castable amounts only (JSON numbers, or numeric strings the
      -- Python float() cast also accepted); everything else is skipped.
      AND (products -> widx -> 'price' ->> 'amount')
            ~ '^-?[0-9]+(\.[0-9]+)?$'
      AND (products -> (1 - widx) -> 'price' ->> 'amount')
            ~ '^-?[0-9]+(\.[0-9]+)?$'
  )
  SELECT
    ROUND(COALESCE(SUM(GREATEST(loser_amt - winner_amt, 0)), 0), 2)::numeric
      AS savings_bhd,
    COUNT(*)::integer AS decisions_count
  FROM priced;
$$;

-- Locked down to the roles the API uses (service-role admin client and the
-- RLS-scoped authenticated user client).
REVOKE ALL ON FUNCTION public.home_savings_aggregate(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.home_savings_aggregate(uuid)
  TO authenticated, service_role;
