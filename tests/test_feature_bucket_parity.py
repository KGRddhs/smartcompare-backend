"""Cross-language parity test for djb2 hash + hash_bucket.

Loads `tests/fixtures/featurebucket_parity.json` (generated from the
SmartCompareApp/src/config/featureBucket.ts implementation via node)
and asserts the Python port produces identical (hash, bucket) for every
(id, percent) pair. Any divergence breaks the canary contract — same
user MUST land in the same bucket on backend and frontend.

Fixture regeneration (run from worktree root):

    node -e "
    function djb2(s) {
      let h = 5381;
      for (let i = 0; i < s.length; i++) {
        h = ((h << 5) + h + s.charCodeAt(i)) | 0;
      }
      return h >>> 0;
    }
    function hashBucket(id, percent) {
      if (!id) return false;
      if (percent <= 0) return false;
      if (percent >= 100) return true;
      return (djb2(id) % 100) < percent;
    }
    // ... build the fixture array ...
    " > tests/fixtures/featurebucket_parity.json
"""
from __future__ import annotations

import json
import os

import pytest

from app.utils.feature_bucket import djb2, hash_bucket

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "featurebucket_parity.json"
)


def _load_fixtures():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


FIXTURES = _load_fixtures()


def test_fixture_file_has_meaningful_size():
    """Guard against an empty fixture silently passing the parity loop."""
    assert len(FIXTURES) >= 100, (
        f"parity fixture has {len(FIXTURES)} entries — expected at least 100. "
        "Regenerate via the node snippet in the module docstring."
    )


@pytest.mark.parametrize("case", FIXTURES, ids=lambda c: f"id={c['id']!r}/pct={c['percent']}")
def test_hash_bucket_matches_typescript(case):
    """Each fixture entry: Python output must equal TS output exactly."""
    py_hash = djb2(case["id"])
    py_bucket = hash_bucket(case["id"], case["percent"])
    assert py_hash == case["hash"], (
        f"djb2 mismatch for id={case['id']!r}: "
        f"python={py_hash}, typescript={case['hash']}"
    )
    assert py_bucket == case["expected"], (
        f"hash_bucket mismatch for id={case['id']!r}, percent={case['percent']}: "
        f"python={py_bucket}, typescript={case['expected']}"
    )
