"""Version-robust FastAPI/Starlette route introspection for the test tree.

WHY THIS MODULE EXISTS -- do not re-flatten its call sites back into
``for route in app.routes: route.path``.

``requirements.txt`` pins ``fastapi==0.141.1`` / ``starlette==1.6.0`` -- that is
what CI and Railway install. A developer machine can be running something much
older (observed 2026-09-01: fastapi 0.115.0 / starlette 0.38.6), so a test that
hard-codes one framework's ``app.routes`` shape passes locally and fails in CI.

On fastapi 0.141 an entry in ``app.routes`` can be an ``_IncludedRouter``
wrapper that has NO ``.path`` attribute but does expose ``.routes``. Both naive
introspection idioms break on it:

* ``[r.path for r in app.routes]``               -> AttributeError
* ``getattr(r, "path", "")`` inside a filter loop -> silently sees ZERO routes
  and reports a FALSE "that endpoint is not mounted" failure

Both were real. Together they cost three CI failures -- a legacy-route guard, the
ENDPOINT_MANIFEST contract, and the Wave-1 security pin on
``GET /api/v1/text/price-kpi`` -- while the endpoints were provably mounted in
production.

The fix is duck typing, not version sniffing:

* an entry that HAS ``.path`` is a real route and is yielded as-is (so a
  ``Mount`` stays opaque, exactly as the old code treated it);
* an entry with NO ``.path`` that exposes ``.routes`` is a container --
  ``_IncludedRouter``, a bare ``APIRouter``, a sub-application -- and is
  descended into, carrying whatever ``prefix`` the container declares;
* anything else is skipped.

The prefix carry is what makes the walk correct under BOTH shapes. When the
framework has already baked the include-time prefix into the child path
(fastapi 0.115) the child path already starts with the prefix and is left
alone; when the wrapper applies it lazily the prefix is prepended here.

There is no bare ``except: pass`` swallowing a route lookup anywhere in this
module: an empty route table must stay VISIBLE, which is what
``assert_route_table_visible`` exists to enforce. Call it before any assertion
whose negative form ("path X is NOT registered") would pass vacuously against
an empty table.
"""

from __future__ import annotations

from typing import Any, Iterator, NamedTuple, Optional

__all__ = [
    "MountedRoute",
    "walk_routes",
    "route_paths",
    "route_method_paths",
    "find_route",
    "assert_route_table_visible",
]

# Fallback positive-control anchors, used only when the app exposes no OpenAPI
# schema. One route of each mounting style this app uses, so a walker that
# loses a whole style goes red loudly instead of silently reporting nothing:
#   /health                -> plain starlette Route on the app itself
#   /api/v1/text/compare   -> APIRoute under a router-declared prefix
#   /api/v1/admin/costs    -> APIRoute under an include_router(prefix=...) prefix
_ANCHOR_PATHS = ("/health", "/api/v1/text/compare", "/api/v1/admin/costs")


class MountedRoute(NamedTuple):
    """One real route, with its fully-resolved mount path.

    ``path`` is the resolved path (prefixes applied), ``methods`` the HTTP verbs
    (empty for routes that declare none, e.g. websockets), and ``route`` the
    underlying framework object -- use it for ``.dependant``, ``.endpoint``,
    ``.name`` and anything else version-specific.
    """

    path: str
    methods: frozenset
    route: Any


def _join_prefix(prefix: str, path: str) -> str:
    """Prepend ``prefix`` to ``path`` unless the framework already did.

    Idempotent on purpose: it must be a no-op on the fastapi shape that bakes
    the prefix into the child route at include time, and effective on the shape
    that keeps it on the wrapper.
    """
    if not prefix or path.startswith(prefix):
        return path
    return prefix + path


def _iterable_routes(candidate: Any) -> Optional[list]:
    """Return ``candidate`` as a list if it looks like a route collection."""
    if candidate is None or isinstance(candidate, (str, bytes)):
        return None
    if not hasattr(candidate, "__iter__"):
        return None
    return list(candidate)


def _discover_prefix(obj: Any) -> str:
    """The include-time mount prefix of a router-like container, RENAME-PROOF.

    ``.prefix`` is the documented name and is tried first. It is NOT trusted as
    the only name: CI proved (fastapi 0.141.1, run 886c483) that the real
    ``_IncludedRouter`` does not surface it there -- all 72 ``/api/v1/admin/*``
    paths walked without their mount prefix. Rather than hard-code whatever the
    private attribute happens to be called this release, fall back to scanning
    the instance dict for a path-shaped string under a prefix-ish key. A wrong
    guess cannot pass silently: ``assert_route_table_visible`` cross-checks the
    walk against the app's own OpenAPI paths.
    """
    prefix = getattr(obj, "prefix", None)
    if isinstance(prefix, str) and prefix:
        return prefix
    # fastapi 0.141's `_IncludedRouter` keeps the include-time prefix on a
    # context object, and its `original_router.prefix` is EMPTY -- so this is
    # the only place the mount prefix exists. Verified against a real 0.141.1
    # install: `include_context.prefix == '/api/v1/admin'`.
    ctx_prefix = getattr(getattr(obj, "include_context", None), "prefix", None)
    if isinstance(ctx_prefix, str) and ctx_prefix:
        return ctx_prefix
    try:
        attrs = vars(obj)
    except TypeError:  # objects without __dict__ (slots/builtins)
        return ""
    for key, value in attrs.items():
        if "prefix" not in key.lower():
            continue
        if isinstance(value, str) and value.startswith("/") and value != "/":
            return value
    return ""


def _as_container(obj: Any) -> Optional[tuple]:
    """Return ``(child_routes, own_prefix)`` if ``obj`` holds routes, else None.

    Covers the app, a bare ``APIRouter``, a starlette ``Router``, and the
    fastapi 0.141 ``_IncludedRouter`` wrapper -- including the variant that
    exposes its routes indirectly via ``.router``.
    """
    prefix = _discover_prefix(obj)

    children = _iterable_routes(getattr(obj, "routes", None))
    if children is None:
        # Indirect holders. `original_router` is fastapi 0.141's `_IncludedRouter`
        # (verified against a real 0.141.1 install): it exposes NEITHER `.routes`
        # NOR `.router`, so without this the whole included router -- every
        # /api/v1/admin/* route -- is skipped as a non-container. Its child paths
        # are UNPREFIXED and may nest another `_IncludedRouter`, which the
        # recursion in `_walk` handles.
        for attr in ("router", "original_router"):
            inner = getattr(obj, attr, None)
            if inner is None or inner is obj:
                continue
            children = _iterable_routes(getattr(inner, "routes", None))
            if children is not None:
                if not prefix:
                    prefix = _discover_prefix(inner)
                break
    if children is None:
        return None
    return children, prefix


def _walk(target: Any, prefix: str, seen: set) -> Iterator[MountedRoute]:
    container = _as_container(target)
    if container is None:
        return
    children, own_prefix = container
    if own_prefix:
        prefix = _join_prefix(prefix, own_prefix)

    for child in children:
        path = getattr(child, "path", None)
        if isinstance(path, str):
            yield MountedRoute(
                path=_join_prefix(prefix, path),
                methods=frozenset(getattr(child, "methods", None) or ()),
                route=child,
            )
            continue
        # No .path -- a wrapper/sub-router. Descend, guarding against cycles.
        # PER-BRANCH guard, not walk-global: `seen` means "is an ancestor of this
        # node". A single shared set would walk a router reachable at TWO mount
        # points only once and silently drop the second mount's routes.
        child_id = id(child)
        if child_id in seen:
            continue
        yield from _walk(child, prefix, seen | {child_id})


def walk_routes(target: Any) -> Iterator[MountedRoute]:
    """Yield every real route reachable from ``target`` (an app or a router).

    Recursive and duck-typed: see the module docstring for the fastapi 0.141
    ``_IncludedRouter`` shape this exists to survive.
    """
    yield from _walk(target, "", {id(target)})


def route_paths(target: Any) -> list:
    """Every resolved route path, in mount order (duplicates preserved)."""
    return [entry.path for entry in walk_routes(target)]


def route_method_paths(target: Any) -> set:
    """``{"GET /api/v1/home/trending", ...}`` for every mounted route."""
    return {
        f"{method} {entry.path}"
        for entry in walk_routes(target)
        for method in entry.methods
    }


def find_route(
    target: Any, path: str, method: Optional[str] = None
) -> Optional[MountedRoute]:
    """First route matching ``path`` (and ``method``, if given), else None.

    Returns None rather than raising so callers can assert with a readable
    message -- the old ``next(r for r in app.routes if ...)`` idiom raised
    ``StopIteration``, which surfaces as an ERROR with no diagnostic.
    """
    wanted = method.upper() if method else None
    for entry in walk_routes(target):
        if entry.path != path:
            continue
        if wanted is None or wanted in entry.methods:
            return entry
    return None


def _documented_paths(app: Any) -> set:
    """The app's OWN view of its mounted paths, via ``app.openapi()``.

    A self-generating positive control: FastAPI builds this schema from the
    resolved route table, so every documented path MUST be reachable by the
    walk above on any framework version. Returns an empty set when there is no
    schema to compare against (a bare router, or a schema build that raises) --
    the caller then falls back to ``_ANCHOR_PATHS``, which still asserts.
    """
    getter = getattr(app, "openapi", None)
    if not callable(getter):
        return set()
    try:
        schema = getter()
    except Exception:
        return set()
    if not isinstance(schema, dict):
        return set()
    paths = schema.get("paths")
    if not isinstance(paths, dict):
        return set()
    return {p for p in paths if isinstance(p, str)}


def assert_route_table_visible(app: Any) -> list:
    """Positive control: prove introspection actually SEES the route table.

    Guards the silent half of the fastapi 0.141 defect. A negative assertion
    ("legacy path X is not registered", "no editorial endpoint lacks a
    manifest") passes vacuously against an empty route table, so every such
    test calls this first and gets a loud, diagnostic failure instead.

    Returns the walked routes so callers can use them directly.
    """
    walked = list(walk_routes(app))
    assert walked, (
        "Route introspection saw ZERO routes on the app. Either the app really "
        "has no routes, or tests/_route_introspection.py needs to learn a new "
        f"container shape from {type(app).__module__}.{type(app).__name__}. "
        "Do NOT weaken the assertions that depend on this."
    )

    seen_paths = {entry.path for entry in walked}
    documented = _documented_paths(app)
    if documented:
        missing = sorted(documented - seen_paths)
        assert not missing, (
            f"{len(missing)} path(s) that the app documents in its own OpenAPI "
            f"schema are NOT reachable by walk_routes: {missing[:10]}. The walk "
            "is losing routes or losing a mount prefix -- fix "
            "tests/_route_introspection.py against the installed fastapi "
            "shape (see requirements.txt for the version CI installs)."
        )
    else:
        missing = [p for p in _ANCHOR_PATHS if p not in seen_paths]
        assert not missing, (
            f"Anchor route(s) {missing} not visible to walk_routes (saw "
            f"{len(walked)} routes). Route introspection is blind to at least "
            "one mounting style -- fix tests/_route_introspection.py."
        )
    return walked
