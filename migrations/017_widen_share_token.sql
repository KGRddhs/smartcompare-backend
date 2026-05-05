-- 017_widen_share_token.sql
-- Fixes a latent schema-vs-code drift caught by pre-canary smoke chain
-- (Session 42 referral build).
--
-- Symptom: ``comparisons.share_token`` was ``varchar(12)`` in prod but
-- ``database_service.create_share_token`` generates 22-char tokens via
-- ``secrets.token_urlsafe(16)``. Every share-token write raised
-- PostgreSQL ``22001 value too long``. ``create_share_token``'s broad
-- try/except returned None, the route mapped None to 404. Comparison-
-- Share has been silently broken since Session 22 (verified pre-fix:
-- 6 comparisons / 0 with_token).
--
-- Fix: widen to TEXT — more forgiving for future format changes.
--
-- The ``comparisons_select`` RLS policy references ``share_token``, so we
-- have to DROP -> ALTER -> CREATE the policy around the ALTER TYPE.
-- Recreated policy is byte-identical to the captured pg_policy.polqual
-- snapshot ("(auth.uid() = user_id) OR (share_token IS NOT NULL)").

-- 1. Drop the dependent policy
DROP POLICY IF EXISTS comparisons_select ON public.comparisons;

-- 2. Widen the column
ALTER TABLE public.comparisons ALTER COLUMN share_token TYPE TEXT;

-- 3. Recreate the policy with identical predicate
CREATE POLICY comparisons_select ON public.comparisons FOR SELECT
    USING ((auth.uid() = user_id) OR (share_token IS NOT NULL));
