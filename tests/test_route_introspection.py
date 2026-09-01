"""Contract tests for ``tests/_route_introspection.py``.

The helper exists because ``requirements.txt`` pins fastapi 0.141 / starlette
1.6 (what CI and Railway install) while a dev machine can be running fastapi
0.115 / starlette 0.38. The 0.141-only failure mode -- an ``_IncludedRouter``
entry in ``app.routes`` with no ``.path`` -- is therefore NOT reproducible on
the stale local install, so it is reproduced here with stand-in objects of the
same duck shape. These tests are the reason the walker can be trusted on a
version this machine cannot run.
"""

import pytest
from starlette.routing import Mount

from app.main import app
from tests._route_introspection import (
    assert_route_table_visible,
    find_route,
    route_method_paths,
    route_paths,
    walk_routes,
)


class _FakeRoute:
    """An APIRoute stand-in: has ``.path`` and ``.methods``."""

    def __init__(self, path, methods=("GET",)):
        self.path = path
        self.methods = set(methods)


class _FakeIncludedRouter:
    """Stand-in for the fastapi 0.141 ``_IncludedRouter`` wrapper.

    The whole point: NO ``.path``, but ``.routes`` and the include-time
    ``.prefix``.
    """

    def __init__(self, routes, prefix=""):
        self.routes = routes
        self.prefix = prefix


class _FakeIndirectRouter:
    """Wrapper variant that exposes its routes via ``.router`` instead."""

    def __init__(self, routes, prefix=""):
        self.router = _FakeIncludedRouter(routes, prefix)


class _Opaque:
    """Neither a route nor a container -- must be skipped, not crashed on."""


class _FakeApp:
    def __init__(self, routes):
        self.routes = routes


def test_the_naive_idioms_really_do_break_on_the_wrapper_shape():
    """Documents the defect this helper exists for -- do not delete.

    Both pre-M19 idioms fail on the 0.141 shape: the direct attribute read
    raises, and the getattr-defended read silently reports an EMPTY table,
    which is what turned three CI guards into false alarms / no-ops.
    """
    wrapped = _FakeApp([_FakeIncludedRouter([_FakeRoute("/compare")], "/api/v1/text")])

    with pytest.raises(AttributeError):
        [r.path for r in wrapped.routes]

    blind = [getattr(r, "path", "") for r in wrapped.routes]
    assert blind == [""], "the silent half of the defect no longer reproduces"

    assert route_paths(wrapped) == ["/api/v1/text/compare"]


def test_lazy_prefix_is_applied_when_the_wrapper_holds_it():
    wrapped = _FakeApp(
        [
            _FakeIncludedRouter(
                [_FakeRoute("/stats/daily"), _FakeRoute("/costs")],
                "/api/v1/admin",
            )
        ]
    )
    assert route_paths(wrapped) == ["/api/v1/admin/stats/daily", "/api/v1/admin/costs"]


def test_baked_prefix_is_not_applied_twice():
    """fastapi 0.115 bakes the prefix into the child path at include time."""
    wrapped = _FakeApp(
        [_FakeIncludedRouter([_FakeRoute("/api/v1/admin/costs")], "/api/v1/admin")]
    )
    assert route_paths(wrapped) == ["/api/v1/admin/costs"]


def test_routes_reached_through_a_router_attribute():
    wrapped = _FakeApp([_FakeIndirectRouter([_FakeRoute("/quick")], "/api/v1/text")])
    assert route_paths(wrapped) == ["/api/v1/text/quick"]


def test_nested_containers_and_non_route_entries():
    wrapped = _FakeApp(
        [
            _Opaque(),
            _FakeIncludedRouter(
                [_FakeIncludedRouter([_FakeRoute("/deep")], "/inner")],
                "/outer",
            ),
        ]
    )
    assert route_paths(wrapped) == ["/outer/inner/deep"]


def test_methods_are_carried_through_the_wrapper():
    wrapped = _FakeApp(
        [_FakeIncludedRouter([_FakeRoute("/quick", ("GET", "POST"))], "/api/v1/text")]
    )
    assert route_method_paths(wrapped) == {
        "GET /api/v1/text/quick",
        "POST /api/v1/text/quick",
    }


def test_a_cycle_does_not_hang_the_walk():
    inner = _FakeIncludedRouter([_FakeRoute("/x")])
    inner.routes.append(inner)
    assert route_paths(_FakeApp([inner])) == ["/x"]


def test_assert_route_table_visible_goes_red_on_a_blind_table():
    """The positive control must itself be able to fail."""
    with pytest.raises(AssertionError) as exc:
        assert_route_table_visible(_FakeApp([_Opaque(), _Opaque()]))
    assert "ZERO routes" in str(exc.value)


def test_find_route_returns_none_instead_of_raising_stopiteration():
    assert find_route(_FakeApp([]), "/nope") is None


def test_find_route_filters_on_method():
    wrapped = _FakeApp([_FakeIncludedRouter([_FakeRoute("/x", ("POST",))])])
    assert find_route(wrapped, "/x", method="POST") is not None
    assert find_route(wrapped, "/x", method="GET") is None


# ---------------------------------------------------------------------------
# Against the real app
# ---------------------------------------------------------------------------


def test_real_app_every_documented_path_is_visible():
    """The self-generating positive control, on the real app.

    Whatever fastapi is installed, every path the app documents in its own
    OpenAPI schema must be reachable by the walk.
    """
    walked = assert_route_table_visible(app)
    assert len(walked) > 50, f"suspiciously small route table: {len(walked)}"


def test_real_app_mounts_are_yielded_not_descended():
    """A ``Mount`` has ``.path``, so it is a leaf -- its sub-app's internal
    routes must not leak into the table (that is the pre-M19 semantics this
    helper deliberately preserves)."""
    mounts = [e for e in walk_routes(app) if isinstance(e.route, Mount)]
    assert mounts, "expected the /admin static mount"
    for mount in mounts:
        assert not mount.path.endswith("/{path:path}")


def test_real_app_price_kpi_is_reachable_by_path():
    entry = find_route(app, "/api/v1/text/price-kpi", method="GET")
    assert entry is not None
    assert hasattr(entry.route, "dependant")
