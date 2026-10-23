-- Migration 050: public.llm_spend_ledger -- off-clock LLM spend of batches and crons (S81-03, S81)
--
-- One row per batch or cron job's calls to ONE provider and model: request
-- count, token sums (input, output, cache read, 5-minute and 1-hour cache
-- writes), server web-search requests and the LIST-PRICE USD cost
-- (app/services/llm_pricing.py: spend_ledger_row builds the row, the keys are
-- llm_pricing.SPEND_LEDGER_COLUMNS). The live compare path never writes here
-- (its cost rides comparisons.full_response.metadata.llm); the first writers
-- are the off-clock units S81-16 (KB seeding batches) and S81-22 (compare
-- runs). NULL cost_usd means unpriced, never 0. No user, device, session or
-- address column and no foreign key to users: the 043 deletion fence does not
-- apply.
--
-- MERGING THIS CHANGES NOTHING IN PRODUCTION: no flag reads or writes this
-- table (ENABLE_LLM_LEDGER_V2 included) and no code writes it yet.
--
-- APPLY ORDER: apply any time; no ordering against 045-049; no flag depends
-- on it.
--
-- Service role only and APPEND-ONLY BY GRANT: RLS on, no policy; REVOKE ALL
-- from PUBLIC, anon, authenticated AND service_role (on a stock Supabase
-- project a table created in public carries default-privilege grants to all
-- three roles, and service_role bypasses RLS, not grants: the
-- migrations/037 both-readings rule), then GRANT SELECT, INSERT only to
-- service_role. Pruning, if ever needed, is a later migration with its own
-- function.
--
-- Owner postcheck (APPLY_050_3_POSTCHECK.sql): relrowsecurity = true;
-- has_table_privilege('service_role', 'public.llm_spend_ledger', 'INSERT') and
-- 'SELECT' = true; 'UPDATE', 'DELETE' and 'TRUNCATE' = false; anon and
-- authenticated 'SELECT' = false.
--
-- Rollback: migrations/rollback/050_llm_spend_ledger.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.llm_spend_ledger (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    job text NOT NULL CHECK (char_length(job) BETWEEN 1 AND 64),
    lane text NOT NULL CHECK (lane IN ('live', 'escalation', 'search', 'offclock')),
    mode text NOT NULL CHECK (mode IN ('sync', 'batch')),
    provider text NOT NULL CHECK (provider IN ('openai', 'anthropic')),
    model text NOT NULL CHECK (char_length(model) BETWEEN 1 AND 64),
    role text CHECK (role IS NULL OR char_length(role) BETWEEN 1 AND 32),
    provider_batch_id text CHECK (
        provider_batch_id IS NULL OR char_length(provider_batch_id) BETWEEN 1 AND 128
    ),
    request_count integer NOT NULL DEFAULT 0 CHECK (request_count >= 0),
    input_tokens bigint NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
    output_tokens bigint NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
    cache_read_tokens bigint NOT NULL DEFAULT 0 CHECK (cache_read_tokens >= 0),
    cache_write_5m_tokens bigint NOT NULL DEFAULT 0 CHECK (cache_write_5m_tokens >= 0),
    cache_write_1h_tokens bigint NOT NULL DEFAULT 0 CHECK (cache_write_1h_tokens >= 0),
    web_search_requests integer NOT NULL DEFAULT 0 CHECK (web_search_requests >= 0),
    cost_usd numeric(14, 6) CHECK (cost_usd IS NULL OR cost_usd >= 0),
    cost_complete boolean NOT NULL,
    basis text NOT NULL DEFAULT 'list_price' CHECK (basis = 'list_price'),
    price_table_as_of text NOT NULL,
    period_start timestamptz,
    period_end timestamptz
);

ALTER TABLE public.llm_spend_ledger ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.llm_spend_ledger FROM PUBLIC, anon, authenticated, service_role;

GRANT SELECT, INSERT ON TABLE public.llm_spend_ledger TO service_role;

COMMENT ON TABLE public.llm_spend_ledger IS
'List-price spend of off-clock LLM batches and crons (S81-03). No user data. Written and read by the service role only; append-only by grant.';

COMMENT ON COLUMN public.llm_spend_ledger.cost_usd IS
'List-price USD from llm_pricing.price_call; NULL means unpriced (an unknown model or rate), never 0.';

COMMIT;
