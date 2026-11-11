"""App version check endpoint."""
import os
from fastapi import APIRouter

# S81-10 FRAGRANCE-ONLY-GATE: categories_live is additive under the flag (a stdlib-only
# module; build 3 reads the five named keys only).
from app.services import category_gate as _category_gate

router = APIRouter(prefix="/api/v1/app", tags=["app"])

# S81-SF1 (ENABLE_SURFACES_FIELD + the knob APP_SURFACES_LIVE): the closed set of the
# remotely switchable category chips, in wire order (the S81-11 launchSurfaces contract).
SURFACE_KEYS = ("skincare", "makeup")


def surfaces_field_enabled() -> bool:
    """S81-SF1 (`ENABLE_SURFACES_FIELD`, default OFF, read PER CALL; a new name)."""
    return os.getenv("ENABLE_SURFACES_FIELD", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def surfaces_live() -> dict:
    """The `surfaces` value from the comma-separated knob: a chip is True only when its
    key is listed (case and padding ignored); unknown tokens are ignored; unset, blank
    or garbage = every chip False. JSON booleans, SURFACE_KEYS order."""
    tokens = {t.strip().lower() for t in os.getenv("APP_SURFACES_LIVE", "").split(",")}
    return {key: (key in tokens) for key in SURFACE_KEYS}


def get_version_info() -> dict:
    """Read version info from environment variables."""
    info = {
        "min_version": os.getenv("APP_MIN_VERSION", "1.0.0"),
        "latest_version": os.getenv("APP_LATEST_VERSION", "1.0.0"),
        "force_update": os.getenv("APP_FORCE_UPDATE", "false").lower() == "true",
        "update_url_ios": os.getenv("APP_STORE_URL", ""),
        "update_url_android": os.getenv("PLAY_STORE_URL", ""),
    }
    # S81-SF1 (ENABLE_SURFACES_FIELD, read per call): ON only, before categories_live.
    if surfaces_field_enabled():
        info["surfaces"] = surfaces_live()
    # S81-10 (ENABLE_FRAGRANCE_ONLY_GATE, read per call): the LAST key, ON only.
    if _category_gate.fragrance_only_gate_enabled():
        info["categories_live"] = list(_category_gate.CATEGORIES_LIVE)
    return info


@router.get("/version")
async def check_version():
    """Check minimum and latest app versions."""
    return get_version_info()
