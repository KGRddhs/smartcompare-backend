"""S81-05 RequestContextMiddleware: pure ASGI, the innermost user middleware.

Behind ``ENABLE_REQUEST_CONTEXT_HEADERS`` (default OFF), read once per call as
the FIRST statement, so the flag OFF reads no scope key and binds nothing. With
the flag ON an HTTP request binds ``x-ai-consent-version``,
``x-device-fingerprint`` and ``x-compare-request-id`` into the ContextVars of
the stdlib leaf ``app/utils/request_context.py`` for the downstream app and
resets them in ``finally`` when it returns or raises. Lifespan and websocket
scopes pass through unbound.

The SAME ``scope``, ``receive`` and ``send`` objects go downstream in both flag
states (no wrapper, no copied scope), so no response byte can change. This
module never logs. Registered unconditionally in ``app/main.py`` just before
the CORS add, i.e. inside RequestID / SecurityHeaders / ErrorHandler /
SlowAPIASGI / CORS, none of which can observe the values.
"""

from app.utils.request_context import (
    bind_from_headers,
    request_context_headers_enabled,
    reset_request_context,
)


class RequestContextMiddleware:
    """Bind the three request headers for the downstream app (flag-gated)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if not request_context_headers_enabled() or scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        tokens = bind_from_headers(scope.get("headers"))
        try:
            await self.app(scope, receive, send)
        finally:
            reset_request_context(tokens)
