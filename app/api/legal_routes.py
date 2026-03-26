"""Legal endpoints — Privacy Policy and Terms of Service."""
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/legal", tags=["legal"])

LEGAL_DIR = Path(__file__).parent.parent / "legal"


def _read_legal_file(filename: str) -> str:
    filepath = LEGAL_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return "Content not available."


@router.get("/privacy")
async def get_privacy_policy():
    """Get the current privacy policy."""
    return {
        "title": "Privacy Policy",
        "content": _read_legal_file("privacy_policy.md"),
        "last_updated": "2026-03-26",
    }


@router.get("/terms")
async def get_terms_of_service():
    """Get the current terms of service."""
    return {
        "title": "Terms of Service",
        "content": _read_legal_file("terms_of_service.md"),
        "last_updated": "2026-03-26",
    }
