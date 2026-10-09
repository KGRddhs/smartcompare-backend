"""Request-shape pins for the inert ``ai_sharing_enabled`` preference field.

History: B1.4 (design 2026-05-05 section 6.1) added the field together with a
per-user OpenAI client routing (``select_client_for_user``). Since U3b
(session 75, decision D3 = C, 2026-10-08) there is NO per-user AI-sharing
control: the routing is deleted and ``get_client()`` takes no argument
(tests/test_u3b_sharing_branch_removed.py pins the removal). The field itself
stays accepted by ``UserPreferencesRequest`` so phones on older bundles keep
working; it is stored unchanged and read by nothing.
"""
from __future__ import annotations


# ============================================
# B1.4 — Pydantic body extension
# ============================================


class TestAISharingPreferenceShape:
    def test_preferences_request_accepts_ai_sharing_enabled_field(self):
        """UserPreferencesRequest must accept ai_sharing_enabled (Optional[bool])."""
        from app.api.auth_routes import UserPreferencesRequest

        req = UserPreferencesRequest(
            priorities=["best_price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
            ai_sharing_enabled=False,
        )
        assert req.ai_sharing_enabled is False

    def test_preferences_request_default_ai_sharing_is_none_or_true(self):
        """Field default should be None (treated as ON downstream) OR explicit True."""
        from app.api.auth_routes import UserPreferencesRequest

        req = UserPreferencesRequest(
            priorities=["best_price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
        )
        # Either None (default ON) or explicit True is acceptable
        assert getattr(req, "ai_sharing_enabled", None) in (None, True)

    def test_preferences_request_accepts_explicit_true(self):
        from app.api.auth_routes import UserPreferencesRequest

        req = UserPreferencesRequest(
            priorities=["best_price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
            ai_sharing_enabled=True,
        )
        assert req.ai_sharing_enabled is True
