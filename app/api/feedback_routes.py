"""
Feedback Routes - Comparison feedback and event tracking endpoints
"""
import json
import logging
import re
import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


def _validate_optional_uuid(v):
    """M13-29: comparison_id is client-supplied and lands in a service-role
    write, so it must be a real UUID — an arbitrary string could pin a row to
    another user's comparison or carry an injection payload into the PostgREST
    filter. None/empty stay None (anonymous feedback with no comparison)."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return str(uuid.UUID(s))
    except (ValueError, AttributeError, TypeError):
        raise ValueError("comparison_id must be a valid UUID")

from app.api.auth_routes import get_optional_user
from app.middleware.rate_limiter import limiter
from app.services.feedback_service import feedback_v2_enabled, save_feedback, track_events_batch
from app.utils.async_utils import fire_and_forget

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["feedback"])

# Allowlist of mattered_most values accepted by POST /feedback. This MUST be a
# SUPERSET of every chip key the mobile app can send: FeedbackCard.tsx sends the
# tapped chip as `mattered_most: [chipKey]`, and an unknown value 422-rejects the
# WHOLE submission, which the client swallows (fire-and-forget), so the tap is
# silently dropped server-side. tests/test_feedback_allowlist_superset.py greps
# the FE chip definitions and fails if any is missing here. WIDEN this list only
# — removing an accepted value breaks any client still sending it.
VALID_MATTERED_MOST = [
    "price", "specs", "reviews", "brand", "value", "warranty", "ratings",
    # FeedbackCard.tsx chips (the MATTERED_OPTIONS array) — on phones today.
    "accurate", "detailed", "fast",
    # S80 C6 reason chips (MYEZ-023); a tap sends mattered_most: [chipKey]
    "wrong_product", "missing_info", "unclear_reasons", "slow", "wrong_winner", "unsure",
]

# Allowlist of event_type values accepted by POST /events. This MUST be a
# SUPERSET of every event_type the mobile app fires via trackEvent/trackEvents
# (api.ts) — an unknown type 422-rejects the WHOLE batch, silently dropping
# the events server-side. tests/test_events_allowlist_superset.py greps the FE
# src/ call sites and fails if any literal event_type is missing here.
#
# NOTE: comparison_wall_time is intentionally NOT here — it is a Sentry
# captureMessage (wallTimeInstrumentation.ts), not an /events write.
VALID_EVENT_TYPES = [
    # Generic / legacy.
    "save", "share", "source_click", "tab_switch",
    "feedback_submit", "result_view_duration",
    # Home compare-entry funnel (Bundle B two-input UX, HomeScreen.tsx).
    "compare_entry_view",
    "compare_cancelled",  # M23 A4 - the loader cancel control (HomeScreen) fires it; it was 422-dropped
    "compare_entry_paywall_banner_view",
    "compare_entry_paywall_banner_tap",
    "compare_entry_content_block",
    "compare_entry_submit",
    "compare_entry_paste_split",
    "compare_entry_mode_autoswitch",
    "compare_entry_ready",
    # Results screen (ResultsScreen.tsx) — share funnel + demographics modal.
    "share_sheet_opened",
    "share_completed",
    "demographics_submitted",
    "demographics_dismissed",
    # Onboarding funnel (OnboardingScreen.tsx / onboarding/OnboardingFlow.tsx).
    "onboarding_started",
    "onboarding_step_completed",
    "onboarding_completed",
    # Bundle B B.1 (F3.5) — pain-workflow signals emitted from the mobile
    # StreamingProductCard. These land in user_events; the backend
    # pain_workflow derivation (B.2, pain_workflow_service) maps them onto
    # pain_workflow_events.signal_type later.
    "spec_expand",      # user expanded the spec list past the 3-row preview (too_many_specs)
    "result_abandon",   # card unmounted before the verdict stage (abandonment mid-stream)
    "screenshot",       # user screenshotted the comparison (share-intent / decision-capture)
    # S80 C7 camera loader stages + cancel (MYEZ-015) and the image failure signal
    "scan_start", "scan_identity_resolved", "scan_comparison_ready", "scan_failed",
    "scan_cancelled", "image_load_failed",
    # S81-SF1 (R-A1, unflagged): appended LAST, the base order untouched. Their
    # event_data passes EVENT_PROPERTY_ALLOWLIST below in every flag state (R-SF1-38).
    "category_coming_soon_tap", "share_channel_selected", "share_target_opened",
    "store_cta_tap",
]

MAX_BATCH_SIZE = 50

# S81-SF1 (R-SF1-20 / R-SF1-38, unflagged): the closed property allowlist of the four
# appended event types, one key each with a value rule. An unknown key or a value that
# fails its rule is DROPPED (never a 422) and counted in ONE INFO line per item that
# carries only the event type and an int. The existing types stay unfiltered (L1).
EVENT_PROPERTY_ALLOWLIST = {
    "category_coming_soon_tap": frozenset({"category"}),
    "share_channel_selected": frozenset({"channel"}),
    "share_target_opened": frozenset({"share_target"}),
    "store_cta_tap": frozenset({"merchant_id"}),
}
# category: the two coming-soon chips (the APP_SURFACES_LIVE keys of version_routes).
EVENT_SURFACE_CATEGORIES = ("skincare", "makeup")
# channel and share_target: ONE vocabulary, the nine share values of migration 049.
EVENT_SHARE_VOCABULARY = (
    "whatsapp", "copy", "x", "telegram", "snapchat", "other", "sms", "email", "more",
)
# merchant_id is a merchant host: the host CHECK of migration 045 (the same pattern as
# the KB leaf's KB_HOST_REGEX, pinned equal by tests/test_s81_sf1_gate_rows.py), matched
# in full (re.fullmatch: a trailing newline never passes), at most 253 characters.
MERCHANT_HOST_PATTERN = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"
MERCHANT_HOST_MAX_CHARS = 253
_MERCHANT_HOST_RE = re.compile(MERCHANT_HOST_PATTERN[1:-1])


def _event_property_ok(key: str, value) -> bool:
    if not isinstance(value, str):
        return False
    if key == "merchant_id":
        return (len(value) <= MERCHANT_HOST_MAX_CHARS
                and _MERCHANT_HOST_RE.fullmatch(value) is not None)
    if key == "category":
        return value in EVENT_SURFACE_CATEGORIES
    if key in ("channel", "share_target"):
        return value in EVENT_SHARE_VOCABULARY
    return False


def _filter_event_properties(event_type: str, event_data: dict):
    """A NEW dict holding only the allowlisted keys whose values pass their rule (the
    sent dict is untouched), and the number of keys dropped."""
    allowed = EVENT_PROPERTY_ALLOWLIST[event_type]
    kept = {k: v for k, v in event_data.items() if k in allowed and _event_property_ok(k, v)}
    return kept, len(event_data) - len(kept)


# S81-SF1 (ENABLE_FEEDBACK_V2): the 046 answer sets (the CHECK constraints of
# migrations/046_comparison_feedback_v2.sql; parity pinned by the RED file's r54).
IDENTITY_VALUES = ("correct", "wrong", "unsure")
WRONG_SIDE_VALUES = ("first", "second", "both")
PREFERENCE_VALUES = ("first", "second", "neither", "unsure")
FEEDBACK_SOURCES = ("result", "contact")
CORRECTION_MAX_CHARS = 80
# The raw correction is refused past this length BEFORE the strip (R-SF1-34).
CORRECTION_RAW_MAX_CHARS = 1000
# C0 controls and DEL (R-SF1-34); built from code points so the source stays ASCII.
_CONTROL_CHARS_RE = re.compile("[" + chr(0) + "-" + chr(31) + chr(127) + "]")
# R-SF1-32: the ON-only 422 for a body that answers nothing.
NO_ANSWER_MESSAGE = "feedback body carries no answer"


def _validate_compare_request_id(v):
    """The comparison_id rule for the per-compare request id: None / blank -> None,
    else the canonical uuid string, else a 422."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return str(uuid.UUID(s))
    except (ValueError, AttributeError, TypeError):
        raise ValueError("compare_request_id must be a valid UUID")


def _feedback_has_answer(data: dict) -> bool:
    """R-SF1-32 / GC-4d: an answer is useful, a 027 or 046 answer column, a non-blank
    correction or change_suggestion, or a non-empty mattered_most. source,
    comparison_id and compare_request_id are not answers."""
    for key in ("useful", "winner_correct", "price_correct", "specs_correct",
                "identity_correct", "wrong_side", "preference"):
        if data.get(key) is not None:
            return True
    for key in ("correction", "change_suggestion"):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or value.strip()):
            return True
    return bool(data.get("mattered_most"))


# ============================================
# Request Models
# ============================================

class _FeedbackRequestBase(BaseModel):
    """S81-SF1: the FROZEN 18cb9e04 FeedbackRequest, the flag-OFF contract. Under
    ENABLE_FEEDBACK_V2 OFF, FeedbackRequest validates a dict body through this class
    first, so its errors (the base 422 bytes) and its field set are exactly the base
    ones. Never edit it: it is the base model, not a second live model."""
    useful: bool
    comparison_id: Optional[str] = None
    mattered_most: List[str] = Field(default_factory=list)
    change_suggestion: Optional[str] = Field(None, max_length=1000)
    winner_correct: Optional[Literal["correct", "wrong", "unsure"]] = None
    price_correct: Optional[Literal["correct", "wrong", "unsure"]] = None
    specs_correct: Optional[Literal["correct", "wrong", "unsure"]] = None

    @field_validator("comparison_id")
    @classmethod
    def _validate_comparison_id(cls, v: Optional[str]) -> Optional[str]:
        return _validate_optional_uuid(v)

    @field_validator("mattered_most")
    @classmethod
    def validate_mattered_most(cls, v: List[str]) -> List[str]:
        for item in v:
            if item not in VALID_MATTERED_MOST:
                raise ValueError(
                    f"Invalid mattered_most item: {item}. "
                    f"Must be one of {VALID_MATTERED_MOST}"
                )
        return v


class FeedbackRequest(BaseModel):
    # S81-SF1: optional under ENABLE_FEEDBACK_V2; flag OFF it stays REQUIRED through
    # _FeedbackRequestBase (the base 422 bytes of a body without it).
    useful: Optional[bool] = None
    comparison_id: Optional[str] = None
    mattered_most: List[str] = Field(default_factory=list)
    change_suggestion: Optional[str] = Field(None, max_length=1000)
    # S80 B1 (R0-2, unflagged, request-side): the live 027 correctness columns, written
    # only when sent; an off-enum value is a 422 at the model.
    winner_correct: Optional[Literal["correct", "wrong", "unsure"]] = None
    price_correct: Optional[Literal["correct", "wrong", "unsure"]] = None
    specs_correct: Optional[Literal["correct", "wrong", "unsure"]] = None
    # S81-SF1 (ENABLE_FEEDBACK_V2, migration 046): the v2 answers. Flag OFF every one is
    # accepted and DROPPED (the base dump below never carries them).
    identity_correct: Optional[Literal["correct", "wrong", "unsure"]] = None
    wrong_side: Optional[Literal["first", "second", "both"]] = None
    preference: Optional[Literal["first", "second", "neither", "unsure"]] = None
    correction: Optional[str] = None
    source: Literal["result", "contact"] = "result"
    compare_request_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _feedback_v2_gate(cls, data):
        if not feedback_v2_enabled():
            # OFF: the frozen base model decides (its ValidationError propagates
            # unchanged) and only its fields come back. A non-dict body is left to this
            # class, so the base non-dict error names the same model.
            if isinstance(data, dict):
                return _FeedbackRequestBase.model_validate(data).model_dump()
            return data
        if isinstance(data, dict) and not _feedback_has_answer(data):
            raise ValueError(NO_ANSWER_MESSAGE)
        return data

    @field_validator("correction", mode="before")
    @classmethod
    def _validate_correction(cls, v):
        # ON only (OFF never carries the field): the raw cap, then no control
        # character, then strip; blank -> None; at most CORRECTION_MAX_CHARS after.
        if not isinstance(v, str):
            return v
        if len(v) > CORRECTION_RAW_MAX_CHARS:
            raise PydanticCustomError(
                "string_too_long", "String should have at most {max_length} characters",
                {"max_length": CORRECTION_RAW_MAX_CHARS},
            )
        if _CONTROL_CHARS_RE.search(v):
            raise ValueError("correction must not contain control characters")
        s = v.strip()
        if not s:
            return None
        if len(s) > CORRECTION_MAX_CHARS:
            raise PydanticCustomError(
                "string_too_long", "String should have at most {max_length} characters",
                {"max_length": CORRECTION_MAX_CHARS},
            )
        return s

    @field_validator("compare_request_id")
    @classmethod
    def _validate_request_id(cls, v: Optional[str]) -> Optional[str]:
        return _validate_compare_request_id(v)

    @field_validator("comparison_id")
    @classmethod
    def _validate_comparison_id(cls, v: Optional[str]) -> Optional[str]:
        return _validate_optional_uuid(v)

    @field_validator("mattered_most")
    @classmethod
    def validate_mattered_most(cls, v: List[str]) -> List[str]:
        for item in v:
            if item not in VALID_MATTERED_MOST:
                raise ValueError(
                    f"Invalid mattered_most item: {item}. "
                    f"Must be one of {VALID_MATTERED_MOST}"
                )
        return v


class EventItem(BaseModel):
    event_type: str
    event_data: dict = Field(default_factory=dict)
    comparison_id: Optional[str] = None
    # S81-SF1 (ENABLE_FEEDBACK_V2): the per-compare request id, uuid-validated ON;
    # flag OFF accepted and dropped (never validated, never stored).
    compare_request_id: Optional[str] = None

    @field_validator("compare_request_id", mode="before")
    @classmethod
    def _gate_compare_request_id(cls, v):
        if not feedback_v2_enabled():
            return None
        return _validate_compare_request_id(v)

    @field_validator("comparison_id")
    @classmethod
    def _validate_comparison_id(cls, v: Optional[str]) -> Optional[str]:
        # M13-29 (closeout): the /events vector is the one the finding's
        # failure_scenario centres on ("50 events per request at 60/min pinned to
        # another user's comparison_id … poisoning … user_events"). track_events_batch
        # writes evt.comparison_id to user_events via the service-role client, so an
        # arbitrary string here is an unvalidated forged/injection value under RLS
        # bypass. Same UUID guard the FeedbackRequest path already carries.
        return _validate_optional_uuid(v)

    @field_validator("event_data")
    @classmethod
    def validate_event_data_size(cls, v: dict) -> dict:
        if len(json.dumps(v, default=str)) > 10_000:
            raise ValueError("event_data too large (max 10KB)")
        return v

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type: {v}. Must be one of {VALID_EVENT_TYPES}"
            )
        return v


class EventBatchRequest(BaseModel):
    events: List[EventItem] = Field(..., max_length=MAX_BATCH_SIZE)


# ============================================
# Endpoints
# ============================================

@router.post("/feedback")
@limiter.limit("30/minute")
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    user=Depends(get_optional_user),
):
    """
    Submit feedback on a comparison result.
    Auth is optional — anonymous feedback accepted.
    """
    v2 = feedback_v2_enabled()
    user_id = user.get("id") if user else None

    kwargs = dict(
        user_id=user_id,
        comparison_id=body.comparison_id,
        useful=body.useful,
        mattered_most=body.mattered_most,
        change_suggestion=body.change_suggestion,
        access_token=(user.get("access_token") if user else None),
        winner_correct=body.winner_correct,
        price_correct=body.price_correct,
        specs_correct=body.specs_correct,
    )
    # S81-SF1 (ENABLE_FEEDBACK_V2): the v2 answers reach the writer ON only; OFF the
    # call carries exactly the nine base kwargs.
    if v2:
        kwargs.update(
            identity_correct=body.identity_correct,
            wrong_side=body.wrong_side,
            preference=body.preference,
            correction=body.correction,
            source=body.source,
            compare_request_id=body.compare_request_id,
        )

    # Fire-and-forget — Bundle D 2.B.6 WRAP: feedback is an audit-grade
    # write; silent failures must surface to Sentry via the done callback.
    fire_and_forget(save_feedback(**kwargs), label="save_feedback")

    return {"success": True, "message": "Feedback received"}


@router.post("/events")
@limiter.limit("60/minute")
async def track_events(
    request: Request,
    body: EventBatchRequest,
    user=Depends(get_optional_user),
):
    """
    Batch track user events.
    Auth is optional — anonymous events accepted.
    Max 50 events per request.
    """
    v2 = feedback_v2_enabled()
    user_id = user.get("id") if user else None

    events = []
    for evt in body.events:
        event_data = evt.event_data
        # S81-SF1 (R-SF1-38, unflagged): the four appended types keep only their
        # allowlisted, rule-passing properties; the 10 KB cap already ran at the model.
        if evt.event_type in EVENT_PROPERTY_ALLOWLIST:
            event_data, dropped = _filter_event_properties(evt.event_type, event_data)
            if dropped:
                logger.info("[EVENTS] properties dropped type=%s n=%d", evt.event_type, dropped)
        item = {
            "user_id": user_id,
            "event_type": evt.event_type,
            "event_data": event_data,
            "comparison_id": evt.comparison_id,
        }
        # S81-SF1 (ENABLE_FEEDBACK_V2): the request id ON only, when sent.
        if v2 and evt.compare_request_id is not None:
            item["compare_request_id"] = evt.compare_request_id
        events.append(item)

    # Fire-and-forget — Bundle D 2.B.6 WRAP: event tracking failures
    # were previously invisible; logger.warning on done callback surfaces
    # them in Sentry without breaking the response.
    fire_and_forget(track_events_batch(events), label="track_events_batch")

    return {"success": True, "message": f"{len(events)} events received"}
