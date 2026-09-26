"""The ONE test-side loader for tiktoken encodings (R22b, PR #207's cold-runner finding).

``tiktoken.encoding_for_model`` reads its BPE file from a download cache
(``TIKTOKEN_CACHE_DIR``, else ``<tmp>/data-gym-cache``) and, on a cold cache, fetches it
from ``openaipublic.blob.core.windows.net``. Under the netguard that fetch raises
``NetworkBlocked`` (wrapped by requests as ``ConnectionError``), so a raw call at module
level killed CI's collection and a raw call in a test failed it. Every test goes through
``encoding_for_model_or_skip`` instead:

* in CI (``GITHUB_ACTIONS`` set) a cold cache is a FAILURE naming the missing
  ``Warm tiktoken cache`` step in ``.github/workflows/ci.yml``;
* anywhere else it is a SKIP carrying the one-line warm command.

``tests/test_hermeticity_pins.py`` pins the behaviour and statically forbids any other
``tiktoken.encoding_for_model`` / ``tiktoken.get_encoding`` call under ``tests/``.
"""

import os

import pytest

from tests._netguard import NetworkBlocked

WARM_STEP = "Warm tiktoken cache"


def encoding_for_model_or_skip(model, *, module_level=False):
    """Return ``tiktoken.encoding_for_model(model)``, or fail (CI) / skip (elsewhere)
    when the encoding is not cached and the network is guarded."""
    import requests
    import tiktoken

    try:
        return tiktoken.encoding_for_model(model)
    except (NetworkBlocked, requests.exceptions.ConnectionError, OSError) as exc:
        if os.environ.get("GITHUB_ACTIONS"):
            pytest.fail(
                "tiktoken encoding for %s is not cached and the network is guarded - "
                "the CI '%s' step did not run (%s: %s)"
                % (model, WARM_STEP, type(exc).__name__, exc)
            )
        pytest.skip(
            "tiktoken encoding not cached; warm it once with: "
            "python -c \"import tiktoken; tiktoken.encoding_for_model('%s')\" "
            "(network) or set TIKTOKEN_CACHE_DIR" % model,
            allow_module_level=module_level,
        )
