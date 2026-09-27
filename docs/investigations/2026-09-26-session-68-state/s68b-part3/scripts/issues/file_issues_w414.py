"""Files the W4-14 follow-up issues (run AFTER the W4-14 PR merges). python issues/file_issues_w414.py [--dry] [PRNUM]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pr_rest import api, REPO  # noqa: E402

PR = next((a for a in sys.argv[1:] if a.isdigit()), "the W4-14 PR")
CTX = (
    f"Follow-up of PR #{PR} (W4-14 Arabic on the results surface: the `results.dimension.*` catalog family through the "
    "echo-guarded `localizedDimensionLabel`, `lang` on the two live text-compare requests, and the dark "
    "`ENABLE_ARABIC_VERDICT_OUTPUT` directive - default OFF, read per call; the client half is unflagged and OTA-gated)."
)

ISSUES = [
    ("W4-14b: localize the PersonalizationChip dimension names (additive `dim_key` on applied_shifts) and thread `lang` through /url/compare (Link mode) and /image/identify (camera)", f"""
{CTX}

**Stated limits (spec A6 / rulings Q2, Q3; the route inventory CORRECTED by the W4-14 adversary r0).**
1. `PersonalizationChip` prints `applied_shifts[].dim_display` - a 49-entry lowercase ENGLISH vocabulary (`DIMENSION_DISPLAY_NAMES`) with NO key in the payload - so an Arabic user still reads `↑ longevity` after W4-14. Localizing it needs an additive backend field.
2. `lang` is sent only on `streamComparison`'s REST and SSE requests (the Home text path). TWO other live client compare paths stay English even with `ENABLE_ARABIC_VERDICT_OUTPUT` ON: **Link mode** - `HomeScreen.handleUrlCompare` posts to `POST /api/v1/url/compare` (present since at least `61585c58`; the spec review's "no client caller" claim was wrong) and `url_extraction_service.py` calls `generate_comparison` without `output_lang`; and the **camera** - `POST /api/v1/image/identify` (`api.ts`, which runs `compare_from_text` at `image_routes.py`). (`/text/quick` has no client caller.)

**Ask.** (a) Backend: an additive `dim_key` on each `applied_shifts` entry (unflagged additive field; old phones ignore it; pinned additive - every existing key and value byte-identical). (b) Client: `PersonalizationChip` resolves `results.dimension.<dim_key>` through the same echo-guarded helper with `dim_display` as the fallback; EN renders byte-identical (pinned under the real EN catalog and under the global jest mock). (c) `lang` on `/url/compare` (HomeScreen body + `url_routes` + `url_extraction_service.generate_comparison` threading) and on `/image/identify` (threaded to `compare_from_text`), both with the same omit-when-unset idiom and the same conditional kwarg; the no-lang requests byte-identical (pinned). Full jest + tsc by path; the 24-cell prompt identity gate for (c) on each route.
"""),
    ("W4-14c: Arabic-aware guards and English replacement paths - the HARD precondition for flipping ENABLE_ARABIC_VERDICT_OUTPUT", f"""
{CTX}

**Why this blocks the flip (rulings Q7 CONFIRMED; review R4.1/R4.2).** With the directive ON the verdict prose is Arabic, but every guard and every replacement path around it is English-only:
- English-only GUARDS that pass an Arabic score leak vacuously: `text_sanitize.strip_score_internals`, `trust_validation_service.validate_verdict`, `verdict_critique_service.critique_verdict`, `response_builder.reconcile_winner_prose`, the client `SCORE_INTERNALS_RE` / `BANNED_PATTERN` at `ResultsContent.tsx` (verdictBody) and `RunnerUpWinsCard.tsx` (key_tradeoff); the pending-price guard `_PRICE_ADJECTIVE_RE` / `_leaks_price_adjective` (an Arabic "أرخص" passes it).
- English REPLACEMENT paths that silently overwrite an Arabic verdict with English (mixed-language verdicts): `_QUALITATIVE_WINNER_REASON` (used unconditionally on the winner-mismatch repair and the scrub-empties fallback), `deterministic_verdict_fields` (under `ENABLE_WINNER_PROSE_RECONCILE`), `_deterministic_partial_verdict` (the timeout partial path), the `COMPARISON_GENERATION_ERROR` fallback.
- The verdict `max_tokens` budget (`token_limit_kwargs(verdict_model, 1000)`) is unmeasured against Arabic output length - Arabic prose can truncate the JSON.

**Ask.** One flagged unit (or a small set): Arabic twins for every guard regex (pinned on Arabic leak fixtures such as "N نقطة"), a language-aware replacement path (an `output_lang`-keyed template set, or an explicit "keep the model's Arabic and never substitute English" rule), and an Arabic `max_tokens` measurement on a sample. Until it ships the flag stays OFF; the CLAUDE.md row lists this issue as precondition (2).
"""),
    ("W4-14d: delta_text and the factual verdict lines as a key+params contract so the client can localize them", f"""
{CTX}

**Stated limit (spec section 11; rulings Q8).** After W4-14 most English prose on the Arabic results surface remains: the per-dimension `delta_text` (`_compose_delta_text`, ~31 English return templates - only the point-math form falls back to the localized label), the deterministic factual verdict `line1`/`line2` (`response_builder._format_line1/_format_line2`, English templates that embed the English dimension label), the spec VALUES, the review summary and the per-product pros/cons (cached per product under language-agnostic keys).

**Ask.** An additive key+params contract beside each English string (e.g. `delta_key` + `delta_params`, `line1_key` + `line1_params`) so the client renders them through the catalog with the EN string as the fallback; unflagged additive fields (every existing field byte-identical, pinned); the client side through the echo-guarded helper pattern; EN renders byte-identical under the real catalog and the global mock. The cached extraction prose (specs/reviews/pros-cons) is a separate unit: it needs a language-keyed cache.
"""),
    ("W4-14e: compareTextPair (0 callers) sends no `lang` - delete it or route it through the shared reader when it gains a caller", f"""
{CTX}

**Ruling R1 (red gate).** `compareTextPair` in `src/services/api.ts` has 0 call sites in `src`; the rulings gave `lang` to `streamComparison`'s REST and SSE requests only, so its body carries no `lang` and PIN 21 records that as dead-path coverage. Ask: delete the dead function (and its dead-path pins) or, if it gains a caller, send `lang` through the same `currentOutputLang()` omit-when-unset idiom with the M7/M19 pins. Mobile lane; full jest by path.
"""),
    ("DECISIONS: category_switched - disclose the switch or make the chip authoritative on explicit_pair (Ahmed)", f"""
{CTX}

**Product call (spec 1e / 14 Q4; rulings Q4).** `category_switched` exists in the type and in both catalogs (`en.json` / `ar.json`) with **0 render sites** (its banner was deliberately deleted under the no-info-banners rule). When a deterministic name hit outranks the user's chip on the explicit_pair path (`_resolve_pair_category` / `name_cat`), the user is never told. Options: (a) a one-line disclosure (the catalog key already exists in both languages) or (b) chip-authoritative precedence on explicit_pair (`ENABLE_CHIP_WINS_OVER_NAME_DETECT`, a W4-8-adjacent resolver change; W4-8d #231 is the same family). Not implemented in W4-14; needs Ahmed's decision.
"""),
]


def main():
    dry = "--dry" in sys.argv
    for title, body in ISSUES:
        body = body.strip() + "\n"
        if dry:
            print("DRY", title[:90], len(body)); continue
        st, res = api("POST", f"/repos/{REPO}/issues", {"title": title, "body": body})
        if st != 201:
            print(f"FAILED status={st} {title[:60]} {str(res)[:200]}"); continue
        print(f"created #{res['number']} {res['html_url']}")


if __name__ == "__main__":
    main()
