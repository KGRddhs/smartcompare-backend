"""Python port of SmartCompareApp/src/config/featureBucket.ts.

Mirrors the frontend djb2 hash byte-for-byte so a `(stable_id, percent)` pair
buckets identically on backend (re-engagement canary) and frontend
(onboarding canary). Used by `reengagement_service.evaluate()` to gate
push delivery by `REENGAGEMENT_CANARY_PERCENT`.

Stability invariant: `hash_bucket(id, percent)` is a pure function — same
inputs always produce the same boolean. Verified against the frontend
implementation by `tests/test_feature_bucket_parity.py` (~963 cases).
"""
from __future__ import annotations


def djb2(s: str) -> int:
    """djb2 hash — mirror of the TS implementation in featureBucket.ts.

    The TS source uses `(h << 5) + h + char` with `| 0` to coerce to a
    signed 32-bit int after every step, then `>>> 0` once at the end to
    coerce to unsigned. Python ints are arbitrary precision; we simulate
    the JS semantics with explicit 32-bit masking.
    """
    h = 5381
    for ch in s:
        # JS: h = ((h << 5) + h + char) | 0  → signed-32-bit overflow each step
        h = (h << 5) + h + ord(ch)
        # Truncate to 32 bits with sign extension (mirror `| 0`).
        h = h & 0xFFFFFFFF
        if h >= 0x80000000:
            h -= 0x100000000
    # JS: `>>> 0` coerces signed → unsigned 32-bit.
    return h & 0xFFFFFFFF


def hash_bucket(stable_id: str | None, percent: int) -> bool:
    """Bucket `stable_id` into the lowest `percent`% of the 0-99 distribution.

    Matches `hashBucket()` in featureBucket.ts exactly:
    - falsy id → False
    - percent <= 0 → False
    - percent >= 100 → True
    - otherwise: djb2(id) % 100 < percent
    """
    if not stable_id:
        return False
    if percent <= 0:
        return False
    if percent >= 100:
        return True
    return (djb2(stable_id) % 100) < percent
