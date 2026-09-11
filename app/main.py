"""
SmartCompare Backend - Main Application
Professional product comparison API with multiple input methods
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv(override=True)

# Configure structured logging before any other imports
from app.middleware.logging_config import configure_logging
configure_logging(os.getenv("LOG_LEVEL", "INFO"))

# Import routes after env vars are loaded
from app.api.auth_routes import router as auth_router    # Authentication
from app.api.text_routes import router as text_router    # Text comparison
from app.api.url_routes import router as url_router      # URL comparison
from app.api.image_routes import router as image_router  # Camera identification + comparison
from app.api.admin_routes import router as admin_router  # Admin analytics
from app.api.feedback_routes import router as feedback_router  # Feedback + events
from app.api.history_routes import router as history_router  # Comparison history
from app.api.share_routes import router as share_router  # Comparison sharing
from app.api.legal_routes import router as legal_router  # Legal (privacy, terms)
from app.api.version_routes import router as version_router  # App version check
from app.api.usage_routes import router as usage_router      # Usage tracking
from app.api.referral_routes import router as referral_router  # Referral system
from app.api.home_routes import router as home_router          # Phase 2.5 editorial HomeScreen sections
from app.api.profile_routes import router as profile_router    # Phase 2.6 editorial ProfileScreen sections

# Import middleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limiter import limiter, _default_rate_limits_enabled
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Initialize Sentry (no-op if SENTRY_DSN not set)
from app.services.sentry_service import init_sentry
init_sentry()

# Announce the resolved OpenAI model ids once, so a running deployment is
# self-identifying: which model served a request is otherwise only knowable by
# reading the code at that commit. Ids come from model_config and are
# env-overridable (OPENAI_MODEL_VERDICT / _STANDARD / _VISION / _CRITIC /
# _MODERATION); see #58.
import logging as _logging
from app.services.model_config import resolved_models as _resolved_models
_logging.getLogger(__name__).info(
    "[models] " + " ".join(f"{role}={mid}" for role, mid in sorted(_resolved_models().items()))
)

# M13-21: /openapi.json is registered independently of docs_url/redoc_url, so
# disabling the Swagger/ReDoc UIs left the full machine-readable contract (every
# /admin endpoint, the X-Admin-Key header name, the debug routes, every
# request-model constraint) world-readable in prod. Suppress it whenever
# RAILWAY_ENVIRONMENT is set — local dev + the test suite (where it is unset)
# keep the schema.
def _openapi_url():
    return None if os.getenv("RAILWAY_ENVIRONMENT") else "/openapi.json"


# Create FastAPI app
app = FastAPI(
    openapi_url=_openapi_url(),
    title="SmartCompare API",
    description="""
    AI-powered product comparison API with multiple input methods.

    ## Input Methods

    - **Image** - Take photos of products, AI identifies and compares
    - **Text** - Type "iPhone 15 vs Galaxy S24" for instant comparison
    - **URL** - Paste product URLs from Amazon, Noon, Carrefour, etc.

    ## Features

    - Structured data extraction (specs, prices, reviews)
    - GCC regional pricing (Bahrain, Saudi, UAE, Kuwait, Qatar, Oman)
    - Intelligent caching for fast responses
    - User authentication and history

    ## Supported Retailers

    Amazon, Noon, Carrefour, Sharaf DG, Lulu Hypermarket, Extra, Jarir, Xcite
    """,
    version="2.1.0",
    docs_url=None if os.getenv("RAILWAY_ENVIRONMENT") else "/docs",
    redoc_url=None if os.getenv("RAILWAY_ENVIRONMENT") else "/redoc",
)

# -- Middleware (order matters: outermost added last) --

# CORS (innermost -- runs first on response)
_DEFAULT_ORIGINS = [
    "https://web-production-58776.up.railway.app",
    "http://localhost:8000",
    "http://localhost:19006",   # Expo web
    "http://localhost:8081",    # Metro bundler
]

def _get_allowed_origins() -> list:
    """Get CORS origins from env var or defaults."""
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        return [o.strip() for o in env_origins.split(",") if o.strip()]
    return _DEFAULT_ORIGINS

ALLOWED_ORIGINS = _get_allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key", "X-Request-ID"],
)

# M13-01: register SlowAPIMiddleware so the limiter's default_limits actually
# fire on the routes WITHOUT an explicit @limiter.limit decorator. Without this
# the 21 undecorated routes (PUT /auth/password, PUT /auth/email, /usage/status,
# the referral invite endpoints, …) had no rate limit at all. Decorated routes
# stay exempt (slowapi's _should_exempt lets their decorator handle them, no
# double-limit). Added here — inside RequestIDMiddleware — so a 429 still carries
# the request_id and the security headers.
#
# M13-01 closeout gate: the blanket default (ANON_LIMIT=10/min) is keyed on the
# limiter key_func, which under the shipped default (ENABLE_PROXY_AWARE_RATELIMIT
# OFF) is the shared Railway edge-proxy IP — making the 10/min a DEPLOYMENT-WIDE
# per-path cap that would 429 the hot app-open reads and /health for every user.
# So the middleware (and therefore the blanket default_limits) is gated behind a
# NEW default-OFF flag; flag-OFF is byte-identical to 674034e (no middleware, no
# default limit). The credential-route brute-force protection is decorator-driven
# and stays live regardless. Activate ONLY with a verified proxy-aware key.
if _default_rate_limits_enabled():
    app.add_middleware(SlowAPIMiddleware)

# Exception handlers (unified error format)
app.state.limiter = limiter
from app.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    rate_limit_handler,
)
from fastapi.exceptions import RequestValidationError

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Error handler (catches unhandled exceptions)
app.add_middleware(ErrorHandlerMiddleware)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request ID (outermost -- generates ID before anything else)
app.add_middleware(RequestIDMiddleware)


# M13-34 — bound the shared thread pool the ~33 asyncio.to_thread sites (adapter
# curl fetches + sync DB/Redis offload) run on. CPython's default pool is
# host-dependent (min(32, cpu+4)) and unnamed; install an explicit, named,
# bounded pool on the running loop at startup so the ceiling is deterministic and
# a thread dump is readable. See app/utils/executor.py for the sizing rationale.
@app.on_event("startup")
async def _install_default_executor() -> None:
    from app.utils.executor import install_default_executor
    install_default_executor()


# W1-10 (LS-FAILURE-MODES-COST-13 / #81) -- event-loop lag heartbeat.
#
# /health returned a static two-key dict, so nothing reported whether the single
# uvicorn worker's loop was actually TURNING -- the one measurement that
# distinguishes "the app is slow" from "the app is wedged". A heartbeat that was
# due at T and runs at T+11s reports 11,000 ms; measuring inside the handler
# cannot see that interval at all, because the handler only runs when the loop is
# already running.
#
# The LAST value and the rolling MAX since process start are both reported: an
# external probe polling every 30 s samples 1 second in 30 and would miss almost
# every stall, so the max is what lets a low-frequency probe see one.
import asyncio

LOOP_LAG_INTERVAL_SECONDS: float = 1.0

_loop_lag_last_ms: float = 0.0
_loop_lag_max_ms: float = 0.0

# The heartbeat task handle, so shutdown can cancel it. None before startup.
_loop_lag_task = None


def record_loop_lag_tick(elapsed_seconds: float) -> None:
    """Record ONE heartbeat tick.

    ``lag_ms = max(0, (elapsed_seconds - LOOP_LAG_INTERVAL_SECONDS) * 1000)`` --
    floored at zero because an elapsed shorter than the interval is clock
    granularity, not negative lag, and a negative value would corrupt the max.
    """
    global _loop_lag_last_ms, _loop_lag_max_ms
    lag_ms = (float(elapsed_seconds) - LOOP_LAG_INTERVAL_SECONDS) * 1000.0
    if lag_ms < 0.0:
        lag_ms = 0.0
    _loop_lag_last_ms = lag_ms
    if lag_ms > _loop_lag_max_ms:
        _loop_lag_max_ms = lag_ms


def loop_lag_snapshot() -> dict:
    """The two loop-lag numbers /health merges into its payload. A dict read."""
    return {
        "loop_lag_ms": _loop_lag_last_ms,
        "loop_lag_max_ms": _loop_lag_max_ms,
    }


async def _loop_lag_heartbeat() -> None:
    """Sleep on the interval and record how far each wake-up overshot it.

    Deliberately carries NO exception handler: ``asyncio.CancelledError`` is a
    ``BaseException`` and MUST propagate so shutdown can actually stop this task.
    """
    loop = asyncio.get_running_loop()
    previous = loop.time()
    while True:
        await asyncio.sleep(LOOP_LAG_INTERVAL_SECONDS)
        now = loop.time()
        record_loop_lag_tick(now - previous)
        previous = now


@app.on_event("startup")
async def _start_loop_lag_heartbeat() -> None:
    global _loop_lag_task
    _loop_lag_task = asyncio.create_task(_loop_lag_heartbeat())


@app.on_event("shutdown")
async def _stop_loop_lag_heartbeat() -> None:
    global _loop_lag_task
    task = _loop_lag_task
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        # Suppressed at the CANCELLER; the coroutine itself still propagates.
        pass
    _loop_lag_task = None


# W1-6 (LS-FAILURE-MODES-COST-05) -- drain the fire-and-forget tasks on shutdown.
#
# `app/utils/async_utils.fire_and_forget` used to create a task nobody held, so a
# task that was mid-`await` when the loop stopped was simply dropped. The
# user-visible cost is `usage_service.refund_comparison_credit`: with
# `ENABLE_ASYNC_REDIS_OFFLOAD` ON it yields at `asyncio.to_thread`, so a deploy
# landing in that window charges a credit for a comparison that FAILED and never
# gives it back. This handler is therefore a HARD PRECONDITION for canarying that
# flag.
#
# THE THREE NUMBERS, and the arithmetic is load-bearing -- 30 > 20 + 8:
#   30 s  railway.json `deploy.drainingSeconds` -- Railway's SIGTERM->SIGKILL
#         window. Set explicitly so it is deterministic instead of an
#         undocumented platform default a bounded drain has to fit under blind.
#   20 s  `--timeout-graceful-shutdown` on both start commands -- a cap on
#         UVICORN'S OWN request-drain phase, not on this handler. Measured on the
#         installed uvicorn 0.30.0: it bounds `_wait_tasks_to_complete()` and the
#         installed default is None (unbounded), so one hung request handler used
#         to block shutdown until Railway killed the container -- taking this
#         drain with it. Lifespan shutdown, where this handler runs, happens
#         AFTER that wait and is NOT under that timeout.
#   8 s  DRAIN_TIMEOUT -- the bound on this handler. If the request cap plus this
#         drain ever exceeded the Railway window the container would die
#         mid-drain and we would lose work again behind a false sense of safety.
#
# Registered AFTER `_stop_loop_lag_heartbeat` on purpose: shutdown stops the
# things that never end before it waits on the things that do.
#
# HONEST LIMIT: this drains a GRACEFUL shutdown (SIGTERM). A SIGKILL or an OOM
# kill drains nothing, and `restartPolicyType: ON_FAILURE` implies those happen.
# The refund stays best-effort by design; this makes it survive the common case.
DRAIN_TIMEOUT: float = 8.0


@app.on_event("shutdown")
async def _drain_background_tasks() -> None:
    """Wait, bounded, for the in-flight fire-and-forget tasks to finish.

    `asyncio.wait`, never `gather`: `gather` propagates the FIRST exception
    immediately, so one raising task would end the drain while its slower
    siblings were still mid-await -- and at shutdown that means they are dropped.
    `wait` never propagates a task's exception (the `fire_and_forget`
    done-callback is what logs it), so the handler cannot fail the shutdown.

    Bounded, not best-effort-forever: whatever has not finished inside
    `DRAIN_TIMEOUT` is logged at WARNING BY LABEL and ABANDONED, and the process
    still exits. `DRAIN_TIMEOUT` is read as a module global at CALL time so ops
    (and tests) can change it without re-importing.
    """
    from app.utils.async_utils import _BACKGROUND_TASKS

    # Snapshot before awaiting: done-callbacks mutate the registry as tasks
    # finish, and iterating a set while it changes raises.
    pending = {task for task in _BACKGROUND_TASKS if not task.done()}
    if not pending:
        return

    log = _logging.getLogger(__name__)
    log.info("[DRAIN] waiting up to %ss for %d background task(s)", DRAIN_TIMEOUT, len(pending))

    _done, still_pending = await asyncio.wait(pending, timeout=DRAIN_TIMEOUT)

    for task in still_pending:
        log.warning(
            "[DRAIN] abandoning background task %s -- it did not finish within %ss",
            task.get_name(),
            DRAIN_TIMEOUT,
        )


# -- Routes --
app.include_router(auth_router)      # /api/v1/auth/*
app.include_router(text_router)      # /api/v1/text/*
app.include_router(url_router)       # /api/v1/url/*
app.include_router(image_router)     # /api/v1/image/* (camera)
app.include_router(admin_router, prefix="/api/v1/admin")  # /api/v1/admin/*
app.include_router(feedback_router)  # /api/v1/feedback, /api/v1/events
app.include_router(history_router)  # /api/v1/comparisons/*
app.include_router(share_router)   # /api/v1/share/*
app.include_router(legal_router)   # /api/v1/legal/*
app.include_router(version_router) # /api/v1/app/*
app.include_router(usage_router)   # /api/v1/usage/*
app.include_router(referral_router)  # /api/v1/referrals/*
app.include_router(home_router)      # /api/v1/home/* (savings, smart-pick, trending)
app.include_router(profile_router)   # /api/v1/profile/* (recent-decisions, monthly-stats, priorities-weighted)

# Static admin assets — serves cohort dashboard at /admin/cohort.html
# (The admin endpoints these pages call are still under /api/v1/admin/*.)
#
# Auth model: the StaticFiles mount is wrapped to require the admin key
# via EITHER `X-Admin-Key` header (curl / scripts) OR HTTP Basic auth
# (browsers — the WWW-Authenticate response triggers the native prompt).
# Without this gate, /admin/*.html shells were world-readable even though
# the underlying /api/v1/admin/* JSON endpoints were protected.
import base64
import binascii
import hmac as _hmac
from pathlib import Path as _Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.types import Receive, Scope, Send
from starlette.responses import Response as _Response


class _AdminAuthenticatedStaticFiles(StaticFiles):
    """StaticFiles subclass that gates every request on the admin key.

    Accepts the key from `X-Admin-Key` header (timing-safe compare) or
    from HTTP Basic auth's password field (any username). On miss, returns
    401 + `WWW-Authenticate: Basic` so a browser prompts the operator.
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await super().__call__(scope, receive, send)
            return

        expected = os.getenv("ADMIN_API_KEY", "")
        if not expected:
            # Misconfigured deploy — refuse to serve admin pages at all.
            await _Response("Admin not configured", status_code=503)(scope, receive, send)
            return

        # Header lookup is case-insensitive per HTTP/1.1.
        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }

        # CR-SECURITY-04: compare BYTES. Both operands below are decoded from
        # caller-controlled bytes (latin-1 for the header, UTF-8 for the Basic
        # password), so a `str` compare_digest raises TypeError on any non-ASCII
        # character — a 500 on this UNAUTHENTICATED mount, captured by Sentry
        # with `expected` (= ADMIN_API_KEY) in the frame locals. `TypeError` is
        # not caught by the `except (binascii.Error, UnicodeDecodeError)` below.
        expected_bytes = expected.encode("utf-8", errors="surrogateescape")

        x_admin = headers.get("x-admin-key", "")
        if x_admin and _hmac.compare_digest(
            x_admin.encode("utf-8", errors="surrogateescape"), expected_bytes
        ):
            await super().__call__(scope, receive, send)
            return

        authz = headers.get("authorization", "")
        if authz.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(authz[6:]).decode("utf-8")
                _, _, password = decoded.partition(":")
                if password and _hmac.compare_digest(
                    password.encode("utf-8", errors="surrogateescape"),
                    expected_bytes,
                ):
                    await super().__call__(scope, receive, send)
                    return
            except (binascii.Error, UnicodeDecodeError):
                pass

        await _Response(
            "Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Qaren Admin"'},
        )(scope, receive, send)


_static_dir = _Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount(
        "/admin",
        _AdminAuthenticatedStaticFiles(directory=str(_static_dir / "admin"), html=True),
        name="admin-static",
    )

_favicon_path = _static_dir / "favicon.png"


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    if _favicon_path.exists():
        return FileResponse(str(_favicon_path), media_type="image/png")
    from fastapi import Response
    return Response(status_code=204)


@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "status": "healthy",
        "app": "SmartCompare API",
        "version": "2.1.0",
        "endpoints": {
            "image_identify": "/api/v1/image/identify",
            "text_compare": "/api/v1/text/compare",
            "url_compare": "/api/v1/url/compare",
            "auth": "/api/v1/auth/*",
            "admin": "/api/v1/admin/*",
            "docs": "/docs"
        },
        "input_methods": [
            {"type": "image", "description": "Upload product photos"},
            {"type": "text", "description": "Natural language comparison"},
            {"type": "url", "description": "Product URLs from retailers"}
        ],
        "supported_regions": [
            "bahrain", "saudi_arabia", "uae", "kuwait", "qatar", "oman"
        ]
    }


# Cold-start prevention: Railway supports cron jobs to keep the service warm.
# Set up a Railway cron service that pings GET /health every 5 minutes:
#   Schedule: */5 * * * *
#   Command:  curl -sf https://web-production-58776.up.railway.app/health
#
# W1-10 (2026-09-08): the host above USED to read
# `smartcompare-backend-production.up.railway.app`, which returns Railway's edge
# 404 "Application not found" -- no service is bound to it. The live service is
# the host now written here (verified 200), and it is the one the mobile client
# already targets (`SmartCompareApp/src/services/api.ts`). Anyone who had
# followed these instructions would have built a cron against a dead hostname
# and believed the worker was being kept warm.
# This prevents the ~10-20s cold start penalty on first request after idle.

@app.get("/health")
async def health_check():
    """Basic health check

    Additive only: `status` and `message` keep their exact values (an external
    uptime check may be string-matching them). The two loop-lag numbers are a
    pure dict read of state the heartbeat already wrote -- no await, no I/O.
    This is Railway's deploy healthcheck with a 30 s timeout and must not become
    a thing that can fail.
    """
    return {
        "status": "healthy",
        "message": "Qaren API is running",
        **loop_lag_snapshot()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
