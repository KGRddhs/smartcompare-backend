-- Migration 036: home_savings_aggregate — SQL-side savings SUM/COUNT (issue #116)
--
-- ############################################################################
-- ## NOT APPLIED YET. Written and committed ahead of apply, per repo         ##
-- ## convention. The Python path is gated by ENABLE_HOME_SAVINGS_AGGREGATE   ##
-- ## (default OFF) and degrades to the legacy inline scan if this function   ##
-- ## is missing, so a deploy never breaks on unapplied DDL — but flip the    ##
-- ## flag only AFTER this is applied, or every cache miss pays a failed rpc  ##
-- ## round trip before the fallback.                                         ##
-- ## Apply via Supabase MCP (apply_migration), then VERIFY the function      ##
-- ## exists (pg_proc / information_schema.routines) — the SQL Editor wraps   ##
-- ## multi-statement scripts in one transaction and a late failure silently  ##
-- ## rolls back earlier statements.                                          ##
-- ############################################################################
--
-- WHY. GET /api/v1/home/savings fires on every app open. Pre-#116, a 5-minute
-- cache miss pulled EVERY full_response blob the user ever generated (the
-- single largest column in `comparisons`, no LIMIT, no projection) through a
-- blocking socket read on the event loop, to compute what is arithmetically a
-- SUM and a COUNT of two floats per row. Cost grew linearly with history,
-- forever (M18 finding LS-event-loop-01). This function computes exactly the
-- same aggregate server-side: one small round trip, constant-size response.
--
-- SEMANTICS — a 1:1 mirror of app/api/home_routes.py
-- `_extract_winner_loser_prices` + the accumulation loop:
--   * only rows with user_id = p_user_id AND schema_version = 2 (migration
--     020 invariant: never legacy v1 rows);
--   * winner_index must be 0 or 1 (textual IN ('0','1') guards the cast);
--   * products must be a jsonb array with >= 2 entries;
--   * BOTH winner and loser price currency must be 'BHD' — the deliberate
--     single-currency rule (mixing currencies would require conversion and
--     dilutes the headline);
--   * amounts must parse as plain decimals (the regex guards the ::numeric
--     cast; a null/garbage amount SKIPS the row, exactly like the Python
--     _safe_float -> None -> continue path — skipped rows contribute to
--     NEITHER the sum NOR the count);
--   * per-row contribution is GREATEST(loser - winner, 0) — never frame a
--     pricier-winner row as negative savings;
--   * zero qualifying rows return (0, 0), not NULL (COALESCE).
--
-- WHY SECURITY INVOKER, deviating from the delete_user_cascade SECURITY
-- DEFINER pattern the issue pointed at: PostgREST exposes rpc functions to
-- any authenticated caller with an arbitrary p_user_id. Under SECURITY
-- DEFINER that would let user A read user B's savings aggregate. INVOKER
-- keeps the comparisons RLS policy in force: a user-JWT caller only ever
-- aggregates their OWN rows regardless of p_user_id, while the service-role
-- admin client (which bypasses RLS) relies on the WHERE user_id filter.
--
-- STABLE (reads only), no index added (the existing comparisons access path
-- on user_id serves the filter; an index nothing else queries is write cost
-- for nothing — add one only if this shows up in pg_stat_statements).
--
-- Rollback: migrations/rollback/036_home_savings_aggregate.sql
-- Additive, new function only, no table/lock impact.

BEGIN;

CREATE OR REPLACE FUNCTION public.home_savings_aggregate(p_user_id uuid)
RETURNS TABLE (savings_bhd numeric, decisions_count integer)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
    SELECT
        COALESCE(SUM(GREATEST(t.loser_amt - t.winner_amt, 0)), 0)::numeric
            AS savings_bhd,
        COUNT(*)::integer AS decisions_count
    FROM (
        SELECT
            (c.full_response->'products'
                ->((c.full_response->>'winner_index')::int)
                ->'price'->>'amount')::numeric AS winner_amt,
            (c.full_response->'products'
                ->(1 - (c.full_response->>'winner_index')::int)
                ->'price'->>'amount')::numeric AS loser_amt
        FROM public.comparisons c
        WHERE c.user_id = p_user_id
          AND c.schema_version = 2
          AND c.full_response->>'winner_index' IN ('0', '1')
          AND jsonb_typeof(c.full_response->'products') = 'array'
          AND jsonb_array_length(c.full_response->'products') >= 2
          AND c.full_response->'products'
                ->((c.full_response->>'winner_index')::int)
                ->'price'->>'currency' = 'BHD'
          AND c.full_response->'products'
                ->(1 - (c.full_response->>'winner_index')::int)
                ->'price'->>'currency' = 'BHD'
          AND (c.full_response->'products'
                ->((c.full_response->>'winner_index')::int)
                ->'price'->>'amount') ~ '^-?[0-9]+(\.[0-9]+)?$'
          AND (c.full_response->'products'
                ->(1 - (c.full_response->>'winner_index')::int)
                ->'price'->>'amount') ~ '^-?[0-9]+(\.[0-9]+)?$'
    ) t;
$$;

-- PostgREST exposes rpc to whichever roles hold EXECUTE. anon has no business
-- here (the endpoint requires auth); authenticated is safe under INVOKER+RLS.
REVOKE ALL ON FUNCTION public.home_savings_aggregate(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.home_savings_aggregate(uuid)
    TO authenticated, service_role;

COMMENT ON FUNCTION public.home_savings_aggregate(uuid) IS
    'Issue #116: server-side SUM(GREATEST(loser-winner,0)) + COUNT of BHD-only '
    'schema_version=2 comparisons for /api/v1/home/savings. SECURITY INVOKER '
    'so RLS confines authenticated callers to their own rows. Read by '
    'app/api/home_routes.py only when ENABLE_HOME_SAVINGS_AGGREGATE is on.';

COMMIT;
