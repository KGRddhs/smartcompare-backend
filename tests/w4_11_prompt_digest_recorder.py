"""W4-11 prompt render-digest recorder (the committed generator, ruling R13/R14).

Renders every prompt surface W4-11 may touch through the REAL builders with
every W4-11-adjacent flag UNSET and a fake OpenAI client that records the
kwargs it is handed, and returns the sha256 of each rendered string. The
flag-OFF pins in ``tests/test_prompt_truth.py`` (T-D4, T-G1) compare a fresh
run against ``tests/fixtures/w4_11_prompt_render_digests.json``.

Fixture ownership (R13): ANY deliberate prompt edit regenerates the fixture
in the same PR, with the diff explained in the PR body. Regenerate with::

    python -m tests.w4_11_prompt_digest_recorder

(from the repo root; offline -- fake clients only; the tiktoken encoding for
``gpt-4o-mini`` must be cached). The keys ``base`` / ``extended_at`` are
metadata and are never compared.

The original 90-render fixture was recorded twice at ``61585c58`` (sha256
``10bae61d79a275ba6f21bb33772a15e1341703d1b313ef4b3a7cdc6e9bd7f5d0``, identical);
the four ``url_extract_*`` / ``image_tier3_*`` keys were added at ``58a86b3c``
(the R13 fences' pre-fence renders; the two functions are byte-unchanged
between the two SHAs).
"""
import hashlib
import json
import os
import pathlib
import types

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "w4_11_prompt_render_digests.json"
METADATA_KEYS = ("base", "extended_at")

CATS = ["electronics", "grocery", "supplements", "makeup", "skincare",
        "haircare", "fragrances", "fashion", "other", "unknowncat"]
COHORTS = {
    "none": None,
    "f2534bh": {"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"},
    "m45bh": {"age_group": "45+", "gender": "Male", "nationality": "Bahraini"},
}
QUALITIES = ["normal", "weak", "weird"]
FLAGS = ["ENABLE_SPECS_NO_FABRICATION", "ENABLE_VERDICT_PROMPT_TRUTH",
         "ENABLE_PRICE_FALLBACK_MAY_DECLINE", "ENABLE_LLM_PREFLIGHT_BREAKER",
         "ENABLE_REVIEW_SOURCE_CONSULT", "ENABLE_YOUTUBE_SOURCE", "ENABLE_GPT_WINNER",
         "ENABLE_COMPARISON_QUALITY_V2", "ENABLE_PRICE_PARSE_OFFLOAD",
         "ENABLE_COHORT_PERSONALIZATION"]

BENIGN_HTML = (
    "<html><head><title>Apple iPhone 17 256GB</title></head>"
    "<body><h1>Apple iPhone 17 256GB</h1><p>Price 312.500 BHD. In stock.</p></body></html>"
)
BENIGN_ORGANIC = [
    {"link": "https://www.apple.com/iphone-17/", "snippet": "iPhone 17 product page"},
    {"link": "https://www.example-retailer.com/iphone-17.jpg", "snippet": "iPhone 17 256GB"},
]


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class _FC:
    def __init__(self, store, content):
        self.store, self.content = store, content

    async def create(self, **kw):
        self.store.append(kw)
        m = types.SimpleNamespace(content=self.content)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=m)], usage=None)


def fake_client(store, content="{}"):
    ns = types.SimpleNamespace(chat=types.SimpleNamespace(completions=_FC(store, content)))
    ns.with_options = lambda **kw: ns
    return ns


def _no_messages(kw):
    return {k: v for k, v in kw.items() if k != "messages"}


async def record(monkeypatch, enc):
    """Return the digest dict. ``enc`` is a tiktoken encoding (tests pass the
    one from ``tests._tokenizer.encoding_for_model_or_skip``)."""
    # Import first (extraction_service's first import runs load_dotenv), THEN
    # clear the flags, so a local .env can never leak into the render.
    import app.services.extraction_service as es
    import app.services.image_service as imgsvc
    import app.services.openai_service as osvc
    import app.services.url_extraction_service as urlsvc
    from app.services import prompt_personalities as pp
    from app.services.model_router_service import model_router

    for f in FLAGS:
        monkeypatch.delenv(f, raising=False)
    for k in list(os.environ):
        if k.startswith("OPENAI_MODEL_"):
            monkeypatch.delenv(k, raising=False)

    d = {"base": "61585c58", "extended_at": "58a86b3c", "verdict_system": {},
         "specs_system_off": {}, "specs_system_on": {}, "personality": {}}
    for cat in CATS:
        d["personality"][cat] = sha(pp.build_personality_prompt(cat))
        for cname, coh in COHORTS.items():
            for q in QUALITIES:
                d["verdict_system"][f"{cat}|{cname}|{q}"] = sha(
                    es.build_verdict_prompt([{}, {}], q, coh, cat))
    d["cohort_divergence"] = {}
    for cat in CATS:
        a = es.build_verdict_prompt([{}, {}], "normal", None, cat)
        b = es.build_verdict_prompt([{}, {}], "normal", COHORTS["m45bh"], cat)
        n = 0
        for x, y in zip(a, b):
            if x != y:
                break
            n += 1
        static_pc = es.COMPARISON_SYSTEM + pp.build_personality_prompt(cat)
        try:
            from app.services.verdict_exemplar_loader import build_exemplar_block
            static_pc += build_exemplar_block(cat)
        except Exception:  # noqa: BLE001
            pass
        d["cohort_divergence"][cat] = {
            "differs": a != b,
            "common_prefix_chars": n,
            "common_prefix_tokens": len(enc.encode(a[:n])),
            "static_per_category_chars": len(static_pc),
            "divergence_after_static": n >= len(static_pc),
        }
    for cat in CATS[:-1]:
        d["specs_system_off"][cat] = sha(es._build_specs_prompt(
            "Apple", "iPhone 17", "256GB", cat, "[snippet_1] x")["system"])
    monkeypatch.setenv("ENABLE_SPECS_NO_FABRICATION", "true")
    for cat in CATS[:-1]:
        d["specs_system_on"][cat] = sha(es._build_specs_prompt(
            "Apple", "iPhone 17", "256GB", cat, "[snippet_1] x")["system"])
    monkeypatch.delenv("ENABLE_SPECS_NO_FABRICATION", raising=False)
    d["COMPARISON_SYSTEM"] = sha(es.COMPARISON_SYSTEM)
    d["UNIVERSAL_TRUST_RULES"] = sha(pp.UNIVERSAL_TRUST_RULES)
    d["PRICE_FALLBACK_SYSTEM"] = sha(es.PRICE_FALLBACK_SYSTEM)
    d["SEARCH_RESULTS_GUARD"] = sha(es.SEARCH_RESULTS_GUARD)

    # extract_specs_targeted / synthesized: benign render
    calls = []
    monkeypatch.setattr(osvc, "get_client", lambda *a, **k: fake_client(calls, '{"battery": "5000 mAh"}'))
    await osvc.extract_specs_targeted(brand="Apple", name="iPhone 16", variant=None,
                                      category="electronics", fields=["battery"], context="snip")
    d["targeted_system"] = sha(calls[0]["messages"][0]["content"])
    d["targeted_user"] = sha(calls[0]["messages"][1]["content"])
    d["targeted_kwargs"] = _no_messages(calls[0])
    calls.clear()
    await osvc.extract_specs_synthesized(brand="Apple", name="iPhone 16", variant=None,
                                         category="electronics", fields=["battery"], model="gpt-4o")
    d["synth_system"] = sha(calls[0]["messages"][0]["content"])
    d["synth_kwargs"] = _no_messages(calls[0])

    # generate_comparison: benign payload user message
    async def _gm(priority="standard"):
        return "gpt-4o"

    async def _ru(model, tokens):
        return None

    monkeypatch.setattr(model_router, "get_model", _gm)
    monkeypatch.setattr(model_router, "record_usage", _ru)
    vcalls = []
    monkeypatch.setattr(es, "get_client", lambda *a, **k: fake_client(vcalls, '{"winner_index": 0}'))
    p1 = {"name": "iPhone 17", "brand": "Apple", "category": "electronics",
          "specs": {"battery": "3500 mAh"},
          "reviews": {"average_rating": 4.5, "review_summary": {"consensus": "Solid phone."}}}
    p2 = {"name": "Galaxy S25", "brand": "Samsung", "category": "electronics",
          "specs": {"battery": "4000 mAh"}, "reviews": {"average_rating": 4.4}}
    await es.generate_comparison(p1, p2, "bahrain", category="electronics",
                                 scores_summary="P1 72 / P2 70")
    d["verdict_benign_user"] = sha(vcalls[0]["messages"][1]["content"])
    d["verdict_benign_system"] = sha(vcalls[0]["messages"][0]["content"])
    d["verdict_kwargs"] = _no_messages(vcalls[0])

    # price fallback
    pcalls = []
    monkeypatch.setattr(es, "get_client", lambda *a, **k: fake_client(pcalls, '{"amount": 300, "original_currency": "USD"}'))
    res, _ = await es.extract_price_from_training_data("Apple", "iPhone 17", None, "bahrain")
    d["price_fallback_user"] = sha(pcalls[0]["messages"][1]["content"])
    d["price_fallback_kwargs"] = _no_messages(pcalls[0])
    d["price_fallback_result"] = res

    # R13 fences (pre-fence renders; these two digests MUST move when the
    # fences land, their kwargs must not)
    ucalls = []
    monkeypatch.setattr(urlsvc, "get_client", lambda *a, **k: fake_client(ucalls, '{"name": "iPhone 17"}'))
    await urlsvc.extract_with_ai("https://www.example-retailer.com/p/iphone-17", BENIGN_HTML,
                                 {"key": "generic", "name": "Example"})
    d["url_extract_user"] = sha(ucalls[0]["messages"][-1]["content"])
    d["url_extract_kwargs"] = _no_messages(ucalls[0])
    icalls = []
    monkeypatch.setattr(imgsvc, "get_client", lambda *a, **k: fake_client(icalls, '{"image_url": null}'))
    await imgsvc.extract_image_via_gpt("Apple iPhone 17", BENIGN_ORGANIC)
    d["image_tier3_user"] = sha(icalls[0]["messages"][-1]["content"])
    d["image_tier3_kwargs"] = _no_messages(icalls[0])
    return d


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def dump(d):
    return json.dumps(d, indent=1, sort_keys=True, ensure_ascii=True)


def main():  # pragma: no cover - the regeneration entry point
    import asyncio

    import pytest

    os.environ.setdefault("OPENAI_API_KEY", "sk-test-w4-11-recorder")
    from tests._tokenizer import encoding_for_model_or_skip

    enc = encoding_for_model_or_skip("gpt-4o-mini")
    with pytest.MonkeyPatch.context() as mp:
        d = asyncio.run(record(mp, enc))
    with open(FIXTURE, "w", encoding="utf-8", newline="\n") as fh:  # LF bytes on every OS
        fh.write(dump(d))
    print("wrote", FIXTURE, sha(FIXTURE.read_text(encoding="utf-8")))


if __name__ == "__main__":  # pragma: no cover
    main()
