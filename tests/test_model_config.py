"""Issue #58 — OpenAI model ids must resolve from one env-overridable place.

Two things are pinned here:

1. **Indirection is complete.** No OpenAI model id may remain a bare literal in a
   service module; every call site resolves through ``app.services.model_config``.
2. **Step 1 is behavior-neutral.** With no ``OPENAI_MODEL_*`` env set, every role
   resolves to exactly the id that was hardcoded at main ``c630436``, so the
   refactor cannot move production. Flipping a model is then an env change only.

The parameter-shim tests exist because the GPT-5 family and the GPT-4o family do
not accept the same token-limit parameter — selecting a GPT-5 id by env must not
silently drop the caller's token cap.
"""
import re
from pathlib import Path

import pytest

from app.services import model_config


# The ids that were hardcoded in the tree at c630436, per role.
LEGACY_DEFAULTS = {
    "verdict": "gpt-4o",
    "standard": "gpt-4o-mini",
    "vision": "gpt-4o-mini",
    "critic": "gpt-4o-mini",
    "moderation": "omni-moderation-latest",
}

RESOLVERS = {
    "verdict": model_config.verdict_model,
    "standard": model_config.standard_model,
    "vision": model_config.vision_model,
    "critic": model_config.critic_model,
    "moderation": model_config.moderation_model,
}

ENV_VARS = {
    "verdict": "OPENAI_MODEL_VERDICT",
    "standard": "OPENAI_MODEL_STANDARD",
    "vision": "OPENAI_MODEL_VISION",
    "critic": "OPENAI_MODEL_CRITIC",
    "moderation": "OPENAI_MODEL_MODERATION",
}


@pytest.fixture(autouse=True)
def _clear_model_env(monkeypatch):
    """Every test starts from 'no model env set'."""
    for var in ENV_VARS.values():
        monkeypatch.delenv(var, raising=False)


class TestDefaultsAreBehaviorNeutral:
    @pytest.mark.parametrize("role", sorted(LEGACY_DEFAULTS))
    def test_default_matches_the_previously_hardcoded_id(self, role):
        assert RESOLVERS[role]() == LEGACY_DEFAULTS[role]


class TestEnvOverride:
    @pytest.mark.parametrize("role", sorted(LEGACY_DEFAULTS))
    def test_env_var_overrides_the_default(self, role, monkeypatch):
        monkeypatch.setenv(ENV_VARS[role], "some-other-model")
        assert RESOLVERS[role]() == "some-other-model"

    @pytest.mark.parametrize("role", sorted(LEGACY_DEFAULTS))
    def test_blank_env_falls_back_to_default(self, role, monkeypatch):
        """An empty/whitespace env var must not select the empty string."""
        monkeypatch.setenv(ENV_VARS[role], "   ")
        assert RESOLVERS[role]() == LEGACY_DEFAULTS[role]

    def test_resolution_is_per_call_not_import_time(self, monkeypatch):
        """Flipping a model in Railway must take effect without a code change."""
        assert model_config.verdict_model() == "gpt-4o"
        monkeypatch.setenv("OPENAI_MODEL_VERDICT", "gpt-5-mini")
        assert model_config.verdict_model() == "gpt-5-mini"


class TestTokenLimitParamShim:
    """GPT-5-family ids reject ``max_tokens``; GPT-4o-family reject
    ``max_completion_tokens``. The shim must pick the right one per model."""

    @pytest.mark.parametrize("model", ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"])
    def test_legacy_models_use_max_tokens(self, model):
        assert model_config.token_limit_kwargs(model, 1000) == {"max_tokens": 1000}

    @pytest.mark.parametrize(
        "model",
        ["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5.1", "gpt-5.4-mini", "gpt-5.6-luna"],
    )
    def test_gpt5_family_uses_max_completion_tokens(self, model):
        assert model_config.token_limit_kwargs(model, 1000) == {"max_completion_tokens": 1000}

    def test_unknown_model_defaults_to_max_tokens(self):
        """Unknown ids keep today's behavior rather than guessing."""
        assert model_config.token_limit_kwargs("some-future-model", 500) == {"max_tokens": 500}

    def test_none_limit_yields_no_kwarg(self):
        assert model_config.token_limit_kwargs("gpt-4o", None) == {}


class TestSamplingParamShim:
    """GPT-5-family models reject any non-default temperature with a 400
    ("Only the default (1) value is supported"), so it must be omitted for
    them and passed through untouched for the 4o family."""

    @pytest.mark.parametrize("model", ["gpt-4o", "gpt-4o-mini", "gpt-4.1"])
    def test_legacy_models_keep_temperature(self, model):
        assert model_config.sampling_kwargs(model, 0) == {"temperature": 0}

    @pytest.mark.parametrize("model", ["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5.6-luna"])
    def test_gpt5_family_drops_temperature(self, model):
        assert model_config.sampling_kwargs(model, 0) == {}

    def test_none_temperature_yields_no_kwarg(self):
        assert model_config.sampling_kwargs("gpt-4o", None) == {}


class TestNoStrayModelLiterals:
    """The whole point of #58: changing a model must not mean editing 8 files."""

    # model_config.py owns the literals. content_safety_service keeps the
    # moderation id inline only if it also routes through model_config.
    ALLOWED = {"model_config.py"}

    def test_no_hardcoded_openai_model_ids_in_services(self):
        services = Path(__file__).resolve().parents[1] / "app" / "services"
        pattern = re.compile(r'["\'](gpt-[0-9a-zA-Z.\-]+|omni-moderation-[a-z]+)["\']')
        offenders = {}
        for path in sorted(services.glob("*.py")):
            if path.name in self.ALLOWED:
                continue
            hits = []
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                for match in pattern.finditer(line):
                    hits.append(f"{path.name}:{lineno}: {match.group(0)}")
            if hits:
                offenders[path.name] = hits
        assert not offenders, "hardcoded model ids remain:\n" + "\n".join(
            h for hits in offenders.values() for h in hits
        )
