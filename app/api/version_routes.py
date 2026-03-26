"""App version check endpoint."""
import os
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/app", tags=["app"])


def get_version_info() -> dict:
    """Read version info from environment variables."""
    return {
        "min_version": os.getenv("APP_MIN_VERSION", "1.0.0"),
        "latest_version": os.getenv("APP_LATEST_VERSION", "1.0.0"),
        "force_update": os.getenv("APP_FORCE_UPDATE", "false").lower() == "true",
        "update_url_ios": os.getenv("APP_STORE_URL", ""),
        "update_url_android": os.getenv("PLAY_STORE_URL", ""),
    }


@router.get("/version")
async def check_version():
    """Check minimum and latest app versions."""
    return get_version_info()
