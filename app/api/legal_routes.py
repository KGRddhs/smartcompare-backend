"""Legal endpoints — Privacy Policy and Terms of Service."""
import re
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/legal", tags=["legal"])

LEGAL_DIR = Path(__file__).parent.parent / "legal"

# U8 (ruling UL13): the documents exist in English and Arabic. Only the exact
# primary subtag "ar" selects Arabic; every other value (absent, empty,
# unknown, over-long) serves English.
_LANG_MAX_CHARS = 8
_LANG_SUBTAG_SEP = re.compile(r"[-_]")


def _read_legal_file(filename: str) -> str:
    filepath = LEGAL_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return "Content not available."


def _normalise_lang(lang) -> str:
    """'ar' or 'en': strip, lower-case, cap at 8 chars, primary subtag (split on - and _)."""
    if not isinstance(lang, str):
        return "en"
    value = lang.strip().lower()[:_LANG_MAX_CHARS]
    primary = _LANG_SUBTAG_SEP.split(value, maxsplit=1)[0]
    return "ar" if primary == "ar" else "en"


def _legal_filename(stem: str, lang) -> str:
    """The markdown file for a document stem in the requested language."""
    if _normalise_lang(lang) == "ar":
        return f"{stem}_ar.md"
    return f"{stem}.md"


@router.get("/privacy")
@router.get("/privacy_policy")
async def get_privacy_policy(lang: str = "en"):
    """Get the current privacy policy.

    Two paths are exposed:
    - `/privacy` (short, legacy)
    - `/privacy_policy` (mirrors the markdown filename; what the mobile
      `LegalScreen.tsx` calls)

    `?lang=ar` serves the Arabic document; any other value serves English.
    """
    return {
        "title": "Privacy Policy",
        "content": _read_legal_file(_legal_filename("privacy_policy", lang)),
        "last_updated": "2026-10-11",
    }


@router.get("/terms")
@router.get("/terms_of_service")
async def get_terms_of_service(lang: str = "en"):
    """Get the current terms of service.

    Two paths are exposed:
    - `/terms` (short, legacy)
    - `/terms_of_service` (mirrors the markdown filename; what the mobile
      `LegalScreen.tsx` calls)

    `?lang=ar` serves the Arabic document; any other value serves English.
    """
    return {
        "title": "Terms of Service",
        "content": _read_legal_file(_legal_filename("terms_of_service", lang)),
        "last_updated": "2026-10-11",
    }
