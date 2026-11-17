# INC-SEC-1 WALK: every reference to a table, view or function 055 touches (origin/main 5cd93c6a)

Read-only. Built from `git show origin/main:<path>` of every .py file under app/ and scripts/ (an AST scan of every `.table("<literal>")` call: notes `sec1/walk_scan.py`, raw output `sec1/walk_raw.txt`), plus a hand read of every `.table(<variable>)`, `.rpc(` and table-name constant. No direct Postgres connection exists in app/ or scripts/ (no asyncpg, psycopg, sqlalchemy or DATABASE_URL: ESTABLISHED by grep, matching R1 section 2).

Client legend:
- **service** = a service-role client: `get_admin_supabase_client` (database_service.py:262), its deprecated alias `get_supabase_client` (:320-323), `get_admin_client` (auth_service.py:195-208), `kb_seed_common._admin_client` / `resolve_client` (scripts/kb_seed_common.py:133-173).
- **USER-SCOPED** = `get_user_supabase_client(access_token)` (database_service.py:298-317): the public key plus the caller's token, so PostgREST runs the request as `authenticated` and row security applies. Every user-scoped site falls back to the service client when no token is present.

Result (ESTABLISHED): 127 references in app/ and scripts/ (110 literal-table chains in section A, 17 by constant, variable or RPC in section B). 18 are user-scoped (section G); 2 of the 18 need a code change (C1, C2); the other 16 are SAFE under 055. The legacy backend/ folder (13 references, section F) is not deployed. The mobile app has no database reference (section D).

## A. Literal-table chains (110; sorted by table)

| table | function | read / write | file:line | client | verdict under 055 |
|---|---|---|---|---|---|
| admin_audit_log | referrals_abuse | read select | app/api/admin_routes.py:1069 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| admin_audit_log | get_audit_log | read select | app/api/admin_routes.py:618 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| admin_audit_log | get_audit_log_summary | read select | app/api/admin_routes.py:640 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| admin_audit_log | log_audit_event | write insert | app/services/audit_service.py:31 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparison_feedback | save_feedback | write insert | app/services/feedback_service.py:220 | USER-SCOPED when a token is present (anon key + user JWT), else service | CODE CHANGE C2 (signed-in branch moves to the service key; deploy BEFORE 055) |
| comparison_feedback | _update_behavior_profile | read select | app/services/structured_comparison_service.py:6093 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | _stats_for | read select | app/api/admin_routes.py:1003 | service (caller referrals_cohort_uplift :978 get_admin_supabase_client) | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | _fetch | read select | app/api/admin_routes.py:177 | service (caller api_costs / costs route: get_supabase_client alias :489, get_admin_supabase_client :1138) | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | _fetch | read select | app/api/admin_routes.py:356 | service (same callers as :177) | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | api_costs | read select | app/api/admin_routes.py:508 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | home_savings | read select | app/api/home_routes.py:270 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: filters eq user_id; own-only read kept |
| comparisons | home_smart_pick | read select | app/api/home_routes.py:804 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: filters eq user_id; own-only read kept |
| comparisons | profile_recent_decisions | read select | app/api/profile_routes.py:201 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: filters eq user_id; own-only read kept |
| comparisons | profile_monthly_stats | read select | app/api/profile_routes.py:328 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: filters eq user_id; own-only read kept |
| comparisons | _load_comparison | read select | app/services/abuse_detection_service.py:207 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | save_comparison | write insert | app/services/database_service.py:493 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | get_user_comparisons | read select | app/services/database_service.py:517 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: filters eq user_id; own-only read kept |
| comparisons | get_comparison_by_id | read select | app/services/database_service.py:550 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: filters eq user_id; own-only read kept |
| comparisons | delete_comparison | write delete | app/services/database_service.py:570 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: comparisons_delete and the DELETE grant kept |
| comparisons | create_share_token | write update | app/services/database_service.py:640 | USER-SCOPED when a token is present (anon key + user JWT), else service | CODE CHANGE C1 (the user branch is dead in production: share_routes.py:29 passes no token; C1 removes it) |
| comparisons | get_shared_comparison | read select | app/services/database_service.py:686 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | get_user_comparison_count | read select | app/services/database_service.py:718 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: filters eq user_id; own-only read kept |
| comparisons | _find_14d_comparison_no_retrospective | read select | app/services/reengagement_service.py:271 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | create_invite | read select | app/services/referral_service.py:328 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | resolve_invite | read select | app/services/referral_service.py:443 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | run_invitee_quiz | read select | app/services/referral_service.py:509 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | _count_user_comparisons | read select | app/services/referral_service.py:779 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| comparisons | _update_behavior_profile | read select | app/services/structured_comparison_service.py:6092 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | referrals_abuse | read select | app/api/admin_routes.py:1054 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | referrals_metrics | read select | app/api/admin_routes.py:862 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | referrals_metrics | read select | app/api/admin_routes.py:872 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | referrals_viral | read select | app/api/admin_routes.py:928 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | _get_referrer_device_hash | read select | app/services/abuse_detection_service.py:136 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | resolve_code_to_invite_id | write insert | app/services/referral_service.py:130 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | create_invite | write insert | app/services/referral_service.py:356 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | resolve_invite | read select | app/services/referral_service.py:456 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | resolve_invite | write update | app/services/referral_service.py:470 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | link_invite_to_user | read select | app/services/referral_service.py:636 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | link_invite_to_user | write update | app/services/referral_service.py:646 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | _find_unredeemed_invite_for_invitee | read select | app/services/referral_service.py:756 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | _update_invite_as_redeemed | write update | app/services/referral_service.py:940 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| referral_invites | _flag_invite | write update | app/services/referral_service.py:948 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| search_logs | get_cost_trends | read select | app/services/analytics_service.py:102 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| search_logs | get_error_stats | read select | app/services/analytics_service.py:143 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| search_logs | get_daily_stats | read select | app/services/analytics_service.py:31 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| search_logs | get_popular_queries | read select | app/services/analytics_service.py:79 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| search_logs | log_search | write insert | app/services/database_service.py:830 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| user_events | cohort_retention | read select | app/api/admin_routes.py:785 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| user_events | track_event | write insert | app/services/feedback_service.py:259 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| user_events | track_events_batch | write insert | app/services/feedback_service.py:298 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| user_events | _update_behavior_profile | read select | app/services/structured_comparison_service.py:6094 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | cohort_metrics | read select | app/api/admin_routes.py:707 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | cohort_retention | read select | app/api/admin_routes.py:772 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | referrals_cohort_uplift | read select | app/api/admin_routes.py:992 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | update_push_token | write update | app/api/auth_routes.py:1466 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: users_update kept; writes expo_push_token / preferences only (not in the 055 guard) |
| users | update_reengagement_subs | read select | app/api/auth_routes.py:1543 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: users_select kept (own row) |
| users | update_reengagement_subs | write update | app/api/auth_routes.py:1548 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: users_update kept; writes expo_push_token / preferences only (not in the 055 guard) |
| users | update_preference_toggles | read select | app/api/auth_routes.py:1614 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: users_select kept (own row) |
| users | update_preference_toggles | write update | app/api/auth_routes.py:1622 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: users_update kept; writes expo_push_token / preferences only (not in the 055 guard) |
| users | _inherit_device_counter | read select | app/api/auth_routes.py:565 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _inherit_device_counter | write update | app/api/auth_routes.py:576 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _inherit_device_counter_with_legacy | read select | app/api/auth_routes.py:603 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _inherit_device_counter_with_legacy | write update | app/api/auth_routes.py:621 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _apply_social_device_fingerprint | read select | app/api/auth_routes.py:655 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | home_smart_pick | read select | app/api/home_routes.py:763 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: users_select kept (own row) |
| users | home_trending | read select | app/api/home_routes.py:983 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: users_select kept (own row) |
| users | profile_priorities_weighted | read select | app/api/profile_routes.py:494 | USER-SCOPED when a token is present (anon key + user JWT), else service | SAFE: users_select kept (own row) |
| users | _enrich_response_with_profile | read select | app/services/auth_service.py:375 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | register_user | write insert | app/services/auth_service.py:408 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | login_user | read select | app/services/auth_service.py:458 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | refresh_session | read select | app/services/auth_service.py:512 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | get_user_profile | read select | app/services/auth_service.py:592 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | sign_in_with_social | read select | app/services/auth_service.py:822 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | sign_in_with_social | write insert | app/services/auth_service.py:830 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | sign_in_with_social | read select | app/services/auth_service.py:841 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | update_user_profile | write update | app/services/auth_service.py:909 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | get_user_preferences | read select | app/services/auth_service.py:923 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | save_user_preferences | write update | app/services/auth_service.py:961 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | get_user_by_id | read select | app/services/database_service.py:356 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | get_user_by_email | read select | app/services/database_service.py:368 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | create_user | write insert | app/services/database_service.py:379 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | update_user_subscription | write update | app/services/database_service.py:404 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | health_check | read select | app/services/database_service.py:897 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | save_user_demographics | write update | app/services/database_service.py:916 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | get_user_demographics | read select | app/services/database_service.py:929 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | save_user_attribution | write update | app/services/database_service.py:954 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _get_user_push_token | read select | app/services/push_service.py:124 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _get_user_language | read select | app/services/push_service.py:141 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | resolve_code_to_invite_id | read select | app/services/referral_service.py:114 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | ensure_code_for_user | read select | app/services/referral_service.py:243 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | ensure_code_for_user | write update | app/services/referral_service.py:256 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _lifetime_invites_used | read select | app/services/referral_service.py:401 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | get_status | read select | app/services/referral_service.py:554 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | get_status | write update | app/services/referral_service.py:568 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _load_invitee | read select | app/services/referral_service.py:792 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _referrer_device_lifetime_count | read select | app/services/referral_service.py:821 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _referrer_device_lifetime_count | read select | app/services/referral_service.py:831 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _get_referrer_subscription_tier | read select | app/services/referral_service.py:853 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _grant_loop2_rewards | read select | app/services/referral_service.py:903 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _grant_loop2_rewards | write update | app/services/referral_service.py:910 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _grant_loop2_rewards | read select | app/services/referral_service.py:926 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _grant_loop2_rewards | write update | app/services/referral_service.py:933 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _fetch_behavior_profile | read select | app/services/structured_comparison_service.py:6068 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _update_behavior_profile | write update | app/services/structured_comparison_service.py:6103 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _get_user_tier_info | read select | app/services/usage_service.py:881 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _maybe_reset_referral_bonus | write update | app/services/usage_service.py:927 | service (only caller _get_user_tier_info, get_admin_supabase_client; 054 W03) | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| users | _fetch_eligible_users | read select | scripts/cron_reengagement.py:45 | service (callers :103 / :130 get_admin_supabase_client) | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| vw_cohort_feedback_lift | cohort_feedback | read select | app/api/admin_routes.py:746 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| vw_cohort_match_rate | cohort_metrics | read select | app/api/admin_routes.py:681 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |
| vw_cohort_persona_distribution | cohort_metrics | read select | app/api/admin_routes.py:688 | service | SAFE: service role (BYPASSRLS + its own grants; 055 changes no service_role privilege) |

## B. By constant, variable or RPC (17)

| object | function | read / write | file:line | client | verdict under 055 |
|---|---|---|---|---|---|
| comparison_feedback, comparisons, user_events, search_logs, verdict_critiques (READ_TABLES, cron_learning.py:67) | cron_learning `_read_table` / `windowed` / `_read_by` | read | scripts/cron_learning.py:293 (callers :538-551) | service (`common._admin_client()`, :715) | SAFE (five rows, one per table) |
| comparison_feedback (FEEDBACK_TABLE, cron_compare_judge.py:54) | the judge's winner_correct join | read | scripts/cron_compare_judge.py:617 | service (`common.resolve_client`, :824) | SAFE |
| search_logs (SEARCH_LOGS_TABLE, cron_kb_coverage.py:41) | the coverage proxy | read | scripts/cron_kb_coverage.py:276 | service (`common.resolve_client`, :389) | SAFE |
| referral_invites (and referral_redemptions) | `_count_since` | read | app/api/admin_routes.py:830 (callers :855-858) | service (:850) | SAFE |
| eval_runs | persist_eval_run / fetch_eval_run | write insert / read | scripts/eval_persistence.py:83, :97 | service (:82, :95) | SAFE (F9 revokes all from the app roles) |
| products | upsert / get_product_stats | write upsert / read | app/services/database_service.py:855; app/services/analytics_service.py:182 | service (get_supabase_client alias) | SAFE (F9 revokes all from the app roles) |
| rpc resolve_referral_code | ReferralService code resolve | rpc | app/services/referral_service.py:429 | service (self.client, :232) | SAFE (F8 revokes anon / authenticated only) |
| rpc delete_user_cascade | delete_user_data_cascade | rpc (writes users: email and the profile columns, 048:259-279) | app/services/database_service.py:419 | service | SAFE: definer owner plus claims service_role pass the 055 role test (the 054 C03 analog) |
| rpc increment_lifetime_comparisons | usage_service | rpc (a users counter, not a 055 column) | app/services/usage_service.py:868, :1121 | service | SAFE |
| rpc home_savings_aggregate | home_savings (flag ENABLE_HOME_SAVINGS_AGGREGATE) | rpc | app/api/home_routes.py:101 | USER-SCOPED when a token is present | NOT TOUCHED by 055 (the function is not live, R2 step 3; an invoker aggregate would read own comparisons, which stays allowed) |

Recorded, not counted: `ReferralService.user_client` (referral_service.py:228-230) is built and never used (grep `self.user_client`: only those two lines). `cron_compare_judge.py:798` calls the prune functions (not 055 objects).

## C. The share page and the share flow (the owner's first concern)

| step | where | client | under 055 |
|---|---|---|---|
| The app asks for a link | SmartCompareApp/src/services/api.ts:1231 posts to `/api/v1/share/{id}` on our server | none (the app has no database client) | unchanged |
| The server mints the token | app/api/share_routes.py:29 calls `create_share_token(str(comparison_id), current_user["id"])` with NO access_token | so database_service.py:611 takes the service branch, and the ownership read at :617 is service too | SAFE today; C1 removes the dead user branch so it cannot come back |
| Ownership check | database_service.py:626 compares the row's user_id with the caller | service | unchanged |
| Token write | database_service.py:639-645, update share_token where id and user_id match | service | SAFE: comparisons_update can be dropped |
| Public page | app/api/share_routes.py:52-90 calls `get_shared_comparison` (database_service.py:678-707) | service (:684) | SAFE: the share page never used the `share_token IS NOT NULL` read branch. It strips the personalisation keys (:700) and metadata.openai / llm (share_routes.py:71-79) |
| The owner's own views | history_routes.py:98, :127, :147, :183, :194 | USER-SCOPED | SAFE: own rows. A foreign id now reads as no row; the route already answers 404 for a foreign row (:150-154, :188-192) |

## D. The mobile app ships no database client (ESTABLISHED)
- SmartCompareApp/package.json has no supabase or postgrest dependency (grep -i supabase / postgrest: no hit).
- SmartCompareApp has no `createClient`, `@supabase`, `/rest/v1`, `/graphql/v1` or `SUPABASE_` (node_modules and tests excluded). The only hits are a comment (src/services/api.ts:116) and a log-redaction word list (src/services/sentry.ts:63).
- app.json carries no supabase key. tests/test_security_regression.py:501-512 already pins that SmartCompareApp/src holds no service-role reference.
- landing/ and cloudflare-workers/ have no supabase reference.

## E. Crons and other entry points (ESTABLISHED)
- Procfile and railway.json start `uvicorn app.main:app`. The judge, learning, kbcoverage, warmer, robots, feedwalker, kbenrich, kbseed and pdpdiscovery railway files start `python -m scripts.<name>`. None starts backend/.
- Every cron builds the service client (kb_seed_common.resolve_client / _admin_client, or get_admin_supabase_client at cron_reengagement.py:103 / :130). migrations/ holds no pg_cron job.

## F. Legacy backend/ (13 references, NOT deployed: no start command names it)
- search_logs reads: backend/app/api/text_routes.py:181, :186, :189, :192.
- search_logs insert: backend/app/services/comparison_service_v3.py:205.
- comparisons: backend/app/services/database_service.py:120 (insert), :146, :164, :181.
- rating_cache: backend/app/services/rating_extractor.py:245 (read), :286 (upsert).
- users: the three writers R1-12 names (backend/app/services/auth_service.py:42, database_service.py:55, :80).

If anyone redeployed backend/ with the public key, its rating_cache and search_logs writes would be refused after 055. That is intended.

## G. The 18 user-scoped references, one line each
- database_service.py: :517 (history list, read own), :550 (one comparison, read; the route re-checks ownership), :570 (delete own), :640 (share-token write: C1), :718 (history count).
- home_routes.py: :270 (savings, read own comparisons), :763 (smart pick, read own users row), :804 (smart pick, read own comparisons), :983 (trending region, read own users row).
- profile_routes.py: :201 and :328 (read own comparisons), :494 (read own users row).
- auth_routes.py: :1466 (write expo_push_token), :1543 and :1614 (read own preferences), :1548 and :1622 (write preferences).
- feedback_service.py: :220 (feedback insert: C2).

Also user-scoped but not a 055 table: profile_routes.py:351 reads referral_redemptions (its select-own policy stays).
