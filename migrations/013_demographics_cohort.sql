-- Migration 013: Demographics + cohort match cache + metric views
-- Apply manually via Supabase SQL Editor.
--
-- Adds:
--   - users.demographics_profile JSONB (raw demographics + cached cohort_match)
--   - users.demographics_dismissed_count INT (frontend bottom-sheet dismissal counter)
--   - users.demographics_dismissed_at TIMESTAMPTZ (last dismissal for 7-day cooldown)
--
-- Three views to power /api/v1/admin/cohort/* endpoints:
--   - vw_cohort_match_rate
--   - vw_cohort_persona_distribution
--   - vw_cohort_feedback_lift
--
-- RLS: users.demographics_profile lives on the same row that's already protected
--      by the row-level security policies introduced in migration 010. No new
--      policies needed.

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS demographics_profile JSONB DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS demographics_dismissed_count INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS demographics_dismissed_at TIMESTAMPTZ DEFAULT NULL;

CREATE OR REPLACE VIEW vw_cohort_match_rate AS
SELECT
  date_trunc('day', updated_at) AS day,
  COUNT(*) FILTER (
    WHERE demographics_profile->'cohort_match'->>'match_quality'
          IN ('exact', 'broadened_governorate', 'broadened_language')
  ) AS strong_matches,
  COUNT(*) FILTER (WHERE demographics_profile IS NOT NULL) AS total_with_demographics,
  COUNT(*) AS total_users
FROM public.users
GROUP BY day;

CREATE OR REPLACE VIEW vw_cohort_persona_distribution AS
SELECT
  demographics_profile->'cohort_match'->>'persona_label' AS persona,
  COUNT(*) AS user_count
FROM public.users
WHERE demographics_profile IS NOT NULL
GROUP BY persona
ORDER BY user_count DESC;

CREATE OR REPLACE VIEW vw_cohort_feedback_lift AS
SELECT
  cf.rating,
  ce.event_data->>'cohort_injected' AS cohort_injected,
  COUNT(*) AS n,
  AVG(cf.rating) AS avg_rating
FROM comparison_feedback cf
JOIN user_events ce ON ce.comparison_id = cf.comparison_id
GROUP BY cf.rating, cohort_injected;
