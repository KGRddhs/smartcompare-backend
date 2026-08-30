"""UNIT D2 — the fragrance spec SPINE, shipped dark behind ``ENABLE_SPEC_SPINE``.

WHAT THE SPINE IS. B5 measured the two corpora and found the fragrance spec
signal is ALREADY on the PDPs we cache: notes on 47/79 captured Gulf pages,
family/accords on 56/79, concentration on 48/79 — while ``perfumer`` (13/79)
and ``launch_year`` (7/79) are too sparse to ship, so this unit ships them
ABSENT. Today that prose is thrown away and every comparison pays a fresh
specs LLM call for facts that do not change between compares. The spine seeds
those fields ONCE PER FRAGRANCE, off-clock, into a local store keyed on a
normalised brand+name identity, and the per-compare path reads them for free.

THE THREE PIECES, all dark:
  1. ``app/services/spec_spine_service.py`` — the lookup.
  2. ``scripts/seed_spec_spine.py`` — the off-clock seeder (no key -> no-op).
  3. the wiring in ``structured_comparison_service._get_specs``.

WHY THE KEY CARRIES THE SIZE AND CONCENTRATION AXES. A spine entry is a claim
about a specific fragrance. "Sauvage EDP" and "Sauvage EDT" are different
juices with different notes, so they must never share a row — and the identity
machinery that already refuses to match them on the PRICE path
(``price_service._identity_tokens_ps`` + ``extract_concentration`` +
``extract_size_ml_any``) is exactly the machinery the key reuses, rather than a
second, drifting normaliser.

NO LIVE CALLS ANYWHERE IN THIS FILE. Every fixture byte came off disk
(``tests/fixtures/spec_spine_d2/SOURCES.json`` names the cached page each was
cut from); the seeder tests assert the LLM entrypoint is never reached.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.services import spec_spine_service as spine
from app.services.structured_comparison_service import get_comparison_service

FIXTURES = Path(__file__).parent / "fixtures" / "spec_spine_d2"

# The two REAL retailer titles for the same fragrance, taken from the cached
# PDPs in FIXTURES (see SOURCES.json). Neither string was authored here.
FRAGRANCEX_TITLE = ("Christian Dior", "Sauvage Cologne")
PERFUMECOM_TITLE = ("Christian Dior", "Sauvage Cologne")


@pytest.fixture
def spine_off(monkeypatch):
    monkeypatch.delenv("ENABLE_SPEC_SPINE", raising=False)
    monkeypatch.delenv("SPEC_SPINE_TABLE", raising=False)
    spine.reset_store_cache()
    yield
    spine.reset_store_cache()


@pytest.fixture
def spine_on(monkeypatch):
    monkeypatch.setenv("ENABLE_SPEC_SPINE", "true")
    monkeypatch.delenv("SPEC_SPINE_TABLE", raising=False)
    spine.reset_store_cache()
    yield
    spine.reset_store_cache()


def _write_store(tmp_path, payload) -> str:
    p = tmp_path / "spec_spine.json"
    io.open(p, "w", encoding="utf-8").write(json.dumps(payload))
    spine.reset_store_cache()
    return str(p)


# ---------------------------------------------------------------------------
# 1. Key normalisation — the pins that decide what a "fragrance" IS.
# ---------------------------------------------------------------------------
class TestSpineKeyNormalisation:
    def test_same_fragrance_different_retailer_titles_share_a_key(self):
        """The whole spine depends on this: two retailers describing one juice
        must land on ONE row, or the amortised seed never gets re-read."""
        a = spine.spine_key("Christian Dior", "Sauvage Eau de Parfum 100ml Spray for Men")
        b = spine.spine_key("Dior", "Sauvage EDP 100 ml Natural Spray")
        assert a == b

    def test_brand_abbreviation_and_house_name_share_a_key(self):
        """``price_service._BRAND_ALIAS_GROUPS`` already unifies YSL / Yves
        Saint Laurent on the price path; the spine key must not re-split them."""
        a = spine.spine_key("Yves Saint Laurent", "Black Opium Eau de Parfum 90ml")
        b = spine.spine_key("YSL", "Black Opium EDP 90 ml for Women")
        assert a == b

    def test_concentration_axis_splits_edp_from_edt(self):
        """EDP and EDT are different juices with different notes. If they merged
        the spine would confidently serve one fragrance's notes for the other."""
        edp = spine.spine_key("Dior", "Sauvage Eau de Parfum 100ml")
        edt = spine.spine_key("Dior", "Sauvage Eau de Toilette 100ml")
        assert edp != edt

    def test_size_axis_splits_50ml_from_100ml(self):
        edp50 = spine.spine_key("Dior", "Sauvage Eau de Parfum 50ml")
        edp100 = spine.spine_key("Dior", "Sauvage Eau de Parfum 100ml")
        assert edp50 != edp100

    def test_different_fragrances_do_not_collide(self):
        a = spine.spine_key("Dior", "Sauvage Eau de Parfum 100ml")
        b = spine.spine_key("Dior", "Homme Intense Eau de Parfum 100ml")
        assert a != b

    def test_key_is_stable_and_deterministic(self):
        k1 = spine.spine_key("Christian Dior", "Sauvage Cologne")
        k2 = spine.spine_key("Christian Dior", "Sauvage Cologne")
        assert k1 == k2 and k1


# ---------------------------------------------------------------------------
# 2. The lookup service.
#
# `spine_specs_for` is ASYNC because the (dark) Supabase branch is a blocking
# network read that has to go through asyncio.to_thread; the local-JSON branch
# is a stat + memo lookup. One entry point, not two.
# ---------------------------------------------------------------------------
def test_shipped_store_is_empty():
    """``data/spec_spine.json`` ships as ``{}`` — the spine is DARK on arrival,
    so flipping the flag in Railway changes nothing until a seed run has
    actually happened."""
    shipped = json.load(io.open(spine.DEFAULT_STORE_PATH, encoding="utf-8"))
    assert shipped == {}


@pytest.mark.asyncio
class TestSpineLookup:
    async def test_seeded_entry_hit_fills_fields_with_a_spine_source_tag(
        self, spine_on, monkeypatch, tmp_path
    ):
        key = spine.spine_key("Christian Dior", "Sauvage Eau de Parfum 100ml")
        store = _write_store(tmp_path, {
            key: {
                "specs": {"scent_family": "Aromatic Fougere",
                          "notes_top": "Calabrian bergamot, pepper"},
                "seed_pages": 2,
            }
        })
        monkeypatch.setenv("SPEC_SPINE_STORE_PATH", store)

        got = await spine.spine_specs_for("Dior", "Sauvage EDP 100ml")
        assert got["scent_family"] == "Aromatic Fougere"
        assert got["notes_top"] == "Calabrian bergamot, pepper"
        # Every filled field carries the provenance tag — a spine value must be
        # distinguishable from a snippet-cited one downstream.
        assert got["scent_family_source"] == spine.SPINE_SOURCE_TAG
        assert got["notes_top_source"] == spine.SPINE_SOURCE_TAG

    async def test_flag_off_never_serves_a_spine_value(self, spine_off, monkeypatch, tmp_path):
        key = spine.spine_key("Christian Dior", "Sauvage Eau de Parfum 100ml")
        store = _write_store(tmp_path, {key: {"specs": {"scent_family": "Aromatic Fougere"}}})
        monkeypatch.setenv("SPEC_SPINE_STORE_PATH", store)
        assert await spine.spine_specs_for("Dior", "Sauvage EDP 100ml") == {}

    async def test_non_fragrance_category_is_never_served_from_the_spine(
        self, spine_on, monkeypatch, tmp_path
    ):
        """The spine is a FRAGRANCE artifact (B5). A phone must never read it,
        however the key happens to hash."""
        key = spine.spine_key("Apple", "iPhone 17 256GB", category="electronics")
        store = _write_store(tmp_path, {key: {"specs": {"scent_family": "Woody"}}})
        monkeypatch.setenv("SPEC_SPINE_STORE_PATH", store)
        assert await spine.spine_specs_for("Apple", "iPhone 17 256GB", category="electronics") == {}

    async def test_miss_returns_empty_not_none(self, spine_on, monkeypatch, tmp_path):
        monkeypatch.setenv("SPEC_SPINE_STORE_PATH", _write_store(tmp_path, {}))
        assert await spine.spine_specs_for("Dior", "Sauvage EDP 100ml") == {}

    async def test_unknown_fields_in_a_store_entry_are_dropped(
        self, spine_on, monkeypatch, tmp_path
    ):
        """B5 ships ``launch_year``/``perfumer`` ABSENT (7/79 and 13/79 of the
        corpus). A store row that carries them anyway must not smuggle a
        non-schema field into the response."""
        key = spine.spine_key("Christian Dior", "Sauvage Eau de Parfum 100ml")
        store = _write_store(tmp_path, {key: {"specs": {
            "scent_family": "Aromatic Fougere",
            "launch_year": "2015",
            "perfumer": "Francois Demachy",
            "price": "99",
        }}})
        monkeypatch.setenv("SPEC_SPINE_STORE_PATH", store)
        got = await spine.spine_specs_for("Dior", "Sauvage EDP 100ml")
        assert set(got) == {"scent_family", "scent_family_source"}

    async def test_a_broken_store_file_is_a_miss_not_a_crash(
        self, spine_on, monkeypatch, tmp_path
    ):
        p = tmp_path / "broken.json"
        io.open(p, "w", encoding="utf-8").write("{ not json")
        spine.reset_store_cache()
        monkeypatch.setenv("SPEC_SPINE_STORE_PATH", str(p))
        assert await spine.spine_specs_for("Dior", "Sauvage EDP 100ml") == {}


# ---------------------------------------------------------------------------
# 3. The prompt-side change: extract_specs learns to skip already-known fields.
# ---------------------------------------------------------------------------
class TestBuildSpecsPromptSkipFields:
    def test_default_prompt_is_unchanged(self):
        from app.services.extraction_service import _build_specs_prompt

        base = _build_specs_prompt("Dior", "Sauvage", "", "fragrances", "ctx")
        explicit_none = _build_specs_prompt(
            "Dior", "Sauvage", "", "fragrances", "ctx", skip_fields=None
        )
        assert base["system"] == explicit_none["system"]
        assert base["user"] == explicit_none["user"]

    def test_skipped_fields_leave_the_required_schema(self):
        from app.services.extraction_service import _build_specs_prompt

        base = _build_specs_prompt("Dior", "Sauvage", "", "fragrances", "ctx")
        assert '"scent_family": null' in base["system"]
        trimmed = _build_specs_prompt(
            "Dior", "Sauvage", "", "fragrances", "ctx",
            skip_fields={"scent_family", "notes_top"},
        )
        assert '"scent_family": null' not in trimmed["system"]
        assert '"notes_top": null' not in trimmed["system"]
        # Everything the spine did NOT cover is still asked for.
        assert '"notes_base": null' in trimmed["system"]

    def test_a_subtype_alias_of_a_skipped_field_is_skipped_too(self):
        """The fragrance prompt uses the SUBTYPE field list
        (``fragrances.niche`` -> ``longevity_hrs``, ``volume_ml``) while the
        spine speaks the CANONICAL schema (``longevity``, ``volume``). If the
        skip set were not expanded through ``subtype_spec_aliases`` the trim
        would miss precisely the fields the spine covers on the fragrance
        path — the one path this unit exists for."""
        from app.services.extraction_service import _build_specs_prompt

        base = _build_specs_prompt("Dior", "Sauvage", "", "fragrances", "ctx")
        assert base["type_key"] == "fragrances.niche"
        assert '"longevity_hrs": null' in base["system"]
        trimmed = _build_specs_prompt(
            "Dior", "Sauvage", "", "fragrances", "ctx", skip_fields={"longevity"},
        )
        assert '"longevity_hrs": null' not in trimmed["system"]

    def test_skipping_every_field_keeps_the_full_list(self):
        """Degenerate guard: an empty REQUIRED SCHEMA is not a prompt."""
        import re

        from app.services.extraction_service import _build_specs_prompt

        base = _build_specs_prompt("Dior", "Sauvage", "", "fragrances", "ctx")
        everything = set(re.findall(r'"([a-z_]+)": null', base["system"]))
        assert everything, "the base prompt must carry a schema to skip"
        trimmed = _build_specs_prompt(
            "Dior", "Sauvage", "", "fragrances", "ctx", skip_fields=everything
        )
        assert trimmed["system"] == base["system"]


# ---------------------------------------------------------------------------
# 4. The wiring in _get_specs.
# ---------------------------------------------------------------------------
def _seeded_store(tmp_path):
    key = spine.spine_key("Christian Dior", "Sauvage Eau de Parfum 100ml")
    return _write_store(tmp_path, {
        key: {"specs": {"scent_family": "Aromatic Fougere",
                        "notes_top": "Calabrian bergamot, pepper"}}
    })


class _SpecsSpy:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return dict(self.payload), {"prompt_tokens": 1, "completion_tokens": 1}


@pytest.mark.asyncio
class TestGetSpecsWiring:
    async def test_flag_off_is_byte_identical(self, spine_off, monkeypatch, tmp_path):
        """Flag OFF: the spine is not consulted, and ``extract_specs`` is called
        with EXACTLY the arguments main passes — no ``skip_fields``."""
        monkeypatch.setenv("SPEC_SPINE_STORE_PATH", _seeded_store(tmp_path))
        spy = _SpecsSpy({"scent_family": "N/A", "longevity": "8 hours"})
        svc = get_comparison_service()
        with patch("app.services.structured_comparison_service.extract_specs", spy), \
             patch("app.services.structured_comparison_service.set_cached"), \
             patch("app.services.structured_comparison_service._fire_and_forget"):
            out = await svc._get_specs(
                "Christian Dior", "Sauvage Eau de Parfum 100ml", None,
                "fragrances", "q", nocache=True, search_results={},
            )
        assert len(spy.calls) == 1
        assert "skip_fields" not in spy.calls[0][1]
        assert out["scent_family"] == "N/A"

    async def test_flag_on_spine_hit_fills_fields_and_trims_the_llm_call(
        self, spine_on, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("SPEC_SPINE_STORE_PATH", _seeded_store(tmp_path))
        spy = _SpecsSpy({"scent_family": "N/A", "notes_top": "N/A",
                         "longevity": "8 hours"})
        svc = get_comparison_service()
        with patch("app.services.structured_comparison_service.extract_specs", spy), \
             patch("app.services.structured_comparison_service.set_cached"), \
             patch("app.services.structured_comparison_service._fire_and_forget"):
            out = await svc._get_specs(
                "Christian Dior", "Sauvage Eau de Parfum 100ml", None,
                "fragrances", "q", nocache=True, search_results={},
            )
        # (a) the LLM was told not to re-derive what the spine already knows
        assert spy.calls[0][1]["skip_fields"] == {"scent_family", "notes_top"}
        # (b) the spine value WINS over the LLM's "N/A" placeholder
        assert out["scent_family"] == "Aromatic Fougere"
        assert out["notes_top"] == "Calabrian bergamot, pepper"
        assert out["scent_family_source"] == spine.SPINE_SOURCE_TAG
        # (c) the LLM still owns everything the spine lacked
        assert out["longevity"] == "8 hours"

    async def test_flag_on_spine_miss_is_byte_identical(
        self, spine_on, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("SPEC_SPINE_STORE_PATH", _write_store(tmp_path, {}))
        spy = _SpecsSpy({"scent_family": "N/A"})
        svc = get_comparison_service()
        with patch("app.services.structured_comparison_service.extract_specs", spy), \
             patch("app.services.structured_comparison_service.set_cached"), \
             patch("app.services.structured_comparison_service._fire_and_forget"):
            out = await svc._get_specs(
                "Christian Dior", "Sauvage Eau de Parfum 100ml", None,
                "fragrances", "q", nocache=True, search_results={},
            )
        assert "skip_fields" not in spy.calls[0][1]
        assert out["scent_family"] == "N/A"

    async def test_an_extraction_error_is_never_overwritten_by_the_spine(
        self, spine_on, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("SPEC_SPINE_STORE_PATH", _seeded_store(tmp_path))
        spy = _SpecsSpy({"brand": "Christian Dior", "error": "boom"})
        svc = get_comparison_service()
        with patch("app.services.structured_comparison_service.extract_specs", spy), \
             patch("app.services.structured_comparison_service.set_cached"), \
             patch("app.services.structured_comparison_service._fire_and_forget"):
            out = await svc._get_specs(
                "Christian Dior", "Sauvage Eau de Parfum 100ml", None,
                "fragrances", "q", nocache=True, search_results={},
            )
        assert out["error"] == "boom"
        assert "scent_family" not in out


# ---------------------------------------------------------------------------
# 5. The seeder — off-clock, and inert here.
# ---------------------------------------------------------------------------
class TestSeeder:
    def test_dry_run_groups_the_corpus_fixtures_without_any_llm(self, tmp_path):
        """Three cached PDPs, two of them the SAME fragrance from different
        retailers -> TWO spine candidates. No network, no OpenAI."""
        import scripts.seed_spec_spine as seeder

        dump = tmp_path / "candidates.json"
        out = tmp_path / "spec_spine.json"
        with patch.object(seeder, "extract_spine_specs",
                          AsyncMock(side_effect=AssertionError("LLM must not run"))):
            rc = seeder.main([
                "--corpus", str(FIXTURES),
                "--out", str(out),
                "--dry-run",
                "--dump-candidates", str(dump),
            ])
        assert rc == 0
        assert not out.exists(), "--dry-run must not write the store"

        candidates = json.load(io.open(dump, encoding="utf-8"))
        assert len(candidates) == 2, candidates
        by_pages = sorted(len(c["pages"]) for c in candidates.values())
        assert by_pages == [1, 2]

        # The two-page group is the Sauvage one, and its digest carries the
        # note prose the seed prompt would have to cite.
        pair = [c for c in candidates.values() if len(c["pages"]) == 2][0]
        assert pair["brand"].lower().endswith("dior")
        hosts = {p["host"] for p in pair["pages"]}
        assert hosts == {"www.fragrancex.com", "www.perfume.com"}
        assert "bergamot" in " ".join(p["text"] for p in pair["pages"]).lower()

    def test_no_api_key_is_a_clean_no_op(self, monkeypatch, tmp_path):
        import scripts.seed_spec_spine as seeder

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        out = tmp_path / "spec_spine.json"
        with patch.object(seeder, "extract_spine_specs",
                          AsyncMock(side_effect=AssertionError("LLM must not run"))):
            rc = seeder.main(["--corpus", str(FIXTURES), "--out", str(out)])
        assert rc == 0
        assert not out.exists()

    def test_html_entities_in_a_jsonld_name_are_decoded(self, tmp_path):
        """Caught by the first real dry run over the corpora: 6 of 184
        fragrances keyed on RAW entities (``grey&#x20;flannel&#x20;eau…``,
        ``Acqua dell&apos; Elba``). An entity-bearing key can never be hit by
        the runtime lookup, which sees the decoded title — the seed would be
        written and never read."""
        import scripts.seed_spec_spine as seeder

        page = tmp_path / "entities.html"
        io.open(page, "w", encoding="utf-8").write(
            '<html><head><script type="application/ld+json">'
            '{"@type":"Product",'
            '"name":"Grey&#x20;flannel&#x20;Eau&#x20;de&#x20;Toilette&#x20;120ml",'
            '"brand":{"name":"Acqua dell&apos; Elba"},'
            '"description":"Top notes are bergamot and lemon."}'
            "</script></head><body></body></html>"
        )
        cands = seeder.build_candidates([str(tmp_path)])
        assert len(cands) == 1
        key = next(iter(cands))
        assert "&#x20;" not in key and "&apos" not in key
        assert "flannel" in key and "grey" in key

    def test_every_printed_line_is_ascii(self, tmp_path, capsys):
        """House rule 5: the Windows console is cp1252 and a non-ASCII print
        raises UnicodeEncodeError mid-run. The corpora are full of accented
        brands, so the key listing must be transliterated, not raw."""
        import scripts.seed_spec_spine as seeder

        # The exact shape that crashed the first real dry run (one of four
        # non-ASCII keys across the 184 corpus fragrances): an Arabic brand and
        # title on a page whose description is English.
        page = tmp_path / "accents.html"
        io.open(page, "w", encoding="utf-8").write(
            '<html><head><script type="application/ld+json">'
            '{"@type":"Product","name":"ماء عطر '
            'يارا 100ملليلتر",'
            '"brand":{"name":"لطافة"},'
            '"description":"Eau de Parfum. Top notes are bergamot."}'
            "</script></head><body></body></html>"
        )
        rc = seeder.main(["--corpus", str(tmp_path), "--dry-run",
                          "--out", str(tmp_path / "store.json")])
        assert rc == 0
        out = capsys.readouterr().out
        out.encode("ascii")  # raises if any line carries a non-ASCII char

    def test_a_non_fragrance_page_is_not_a_candidate(self, tmp_path):
        import scripts.seed_spec_spine as seeder

        page = tmp_path / "phone.html"
        io.open(page, "w", encoding="utf-8").write(
            '<html><head><script type="application/ld+json">'
            '{"@type":"Product","name":"Apple iPhone 17 256GB",'
            '"brand":{"name":"Apple"},'
            '"description":"A19 chip, 6.1 inch display, 256 GB storage."}'
            "</script></head><body></body></html>"
        )
        assert seeder.build_candidates([str(tmp_path)]) == {}
