"""Bundle E Task 2.5 — SSE event-type contract documented in text_routes.

The route handler is event-type-agnostic by design — `_BUNDLE_E_EVENT_TYPES`
is a doc-breadcrumb set, not a runtime gate. These tests assert the
breadcrumb mentions every event the orchestrator can emit so reviewers see
the contract without grep'ing through structured_comparison_service.

A drift test catches the case where a new event type lands in the
orchestrator but the docstring whitelist forgets it — the breadcrumb then
becomes a lie. We do not invert this (orchestrator-emit-only-from-list);
runtime gating would couple route + service unnecessarily.
"""
from __future__ import annotations

import inspect

import pytest


def test_route_module_documents_bundle_e_event_types():
    """`text_routes.py` must contain a `_BUNDLE_E_EVENT_TYPES` set
    enumerating every event the orchestrator can emit. The set is purely
    documentation — its presence keeps the wire contract visible at the
    route boundary."""
    from app.api import text_routes

    source = inspect.getsource(text_routes)
    assert "_BUNDLE_E_EVENT_TYPES" in source, (
        "text_routes.py must declare _BUNDLE_E_EVENT_TYPES as a doc breadcrumb"
    )

    # Every Bundle E event type the orchestrator emits must appear in the
    # breadcrumb. If a new event lands in the service, add it here.
    required_events = {
        "status",
        "specs",
        "prices",
        "reviews",
        "first_paint",
        "scores",
        "verdict",
        "settle_update",
        "confidence_upgrade",
        "settle_complete",
        "complete",
        "error",
    }
    for ev in required_events:
        assert f'"{ev}"' in source, (
            f"event-type breadcrumb in text_routes.py is missing {ev!r}. "
            "Add it to _BUNDLE_E_EVENT_TYPES."
        )


def test_orchestrator_helpers_exist_for_new_event_types():
    """The two new event helpers must be importable from the service
    module so the route's breadcrumb maps to a real implementation."""
    from app.services.structured_comparison_service import (
        build_settle_update_event,
        build_confidence_upgrade_event,
    )

    su = build_settle_update_event(field="x", new_value=1, source_rank=90)
    cu = build_confidence_upgrade_event(dimension_key="price", new_confidence="high")

    assert su[0] == "settle_update"
    assert cu[0] == "confidence_upgrade"
