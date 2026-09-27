"""Files the W4-8 follow-up issues (run AFTER the W4-8 PR merges). python issues/file_issues_w48.py [--dry] [PRNUM]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pr_rest import api, REPO  # noqa: E402

PR = next((a for a in sys.argv[1:] if a.isdigit()), "the W4-8 PR")
CTX = f"Follow-up of PR #{PR} (W4-8 category truth: `ENABLE_CATEGORY_TOKEN_FIX` - the tablet veto rebuilt, grams never veto; `ENABLE_BLOCKLIST_PRECISION_V2` - v2 lists = v1 verbatim plus a per-token exemption map; both default OFF)."

ISSUES = [
    ("W4-8b: key the specs cache on the resolved category (a rollback of ENABLE_CATEGORY_TOKEN_FIX leaves supplements-schema specs cached 7 d / 30 d)", f"""
{CTX}

**What is wrong.** The L1/L2 specs cache is keyed on the product, not on the resolved category. Under `ENABLE_CATEGORY_TOKEN_FIX` a pharmacy "tablets" pair resolves to the supplements schema and its specs are cached; a rollback of the flag then serves supplements-schema specs to an electronics resolution for up to 7 d (L1) / 30 d (L2) - and the reverse held before the flag. The PR's canary note works around it with `nocache=true` or never-seen pairs.

**Ask.** Include the resolved category (the pair-resolved `category_used`) in the specs cache key on both layers, behind its own default-OFF flag with a flag-OFF byte-identical key; pin the key shape in both states and state the cache-miss cost of the flip (every cached pair misses once).
"""),
    ("W4-8c: Arabic category tokens (ENABLE_ARABIC_CATEGORY_TOKENS) - the classifier's token table is English-only", f"""
{CTX}

**What is wrong.** `classify_category_from_text` reads English tokens only; an Arabic query (or an Arabic listing title on the shopping surface) falls through to `other` unless a brand carries the category. The W4-8 corpus (`tests/fixtures/category_corpus_gcc_360.json`, 360 GCC strings) carries the Arabic rows the unit measured but did not change.

**Ask.** An Arabic token table for the nine categories (the same veto structure as the English one: unit / pharmacy-token / pack-count rungs for the tablet collision), behind `ENABLE_ARABIC_CATEGORY_TOKENS` (default OFF, per call, flag-OFF byte-identical over the 360-record corpus gate), with the AR rows of the corpus enumerated as the ON delta and alef/hamza normalisation shared with W4-8f.
"""),
    ("W4-8d (DECISIONS_AHMED): EN weapon-intent phrasings v3, an intent-word guard on the co-occurrence exemption, and per-field is_text_safe call sites", f"""
{CTX}

Three product calls for Ahmed, recorded by the unit as stated limits:

1. **EN intent phrases v3.** The v2 lists equal v1 verbatim by design (a safety list never gets more permissive on an unlisted phrasing), so the EN/AR parity gap stays: `buy opium` and `hunting rifle` are ALLOWED in both states while their Arabic twins are blocked. A v3 that adds EN intent phrasings is a product decision (false-positive cost on legitimate EN queries).
2. **An intent-word guard on the exemption.** Under v2 the allowed set is OPEN over co-occurrence: a weapon-intent phrasing that carries a qualifier is allowed (`glock 17 exhaust silencer`, `buy silencer hilux`, `exhaust silencer for sale`, `tactical knife gerber for combat`, the AR `buy air rifle` forms - all measured). Decide whether an intent word (buy / sell / for sale / a weapon brand) next to the token should cancel the exemption.
3. **`is_text_safe` per field (W4-8h).** `is_text_safe` receives ONE caller-composed string at its 22 call sites (title + retailer / domain / the USER's product name), so a qualifier in the user's own query exempts every listing title on those adapters that carries the same token (`car silencer` as the query lets a `Silencer 9mm` listing through). The L2 `filter_shopping_items` surface is already per-field (R16c). Decide whether the call sites should pass fields.

Canary input: the newly-allowed queries under B that carry an exempted token plus intent wording, and the L2 `dropped N/M` INFO lines.
"""),
    ("W4-8e: gram-denominated tablet doses stay electronics under ENABLE_CATEGORY_TOKEN_FIX (stated limit of 'grams never veto'); a dose followed by a pack number", f"""
{CTX}

**Stated limits to close.** By ruling (three carve-out rounds failed on device strings), a number followed by g/G never vetoes, so a gram-denominated tablet dose with no other pharmacy signal stays electronics under the flag: `tablet 1.5g`, `Metformin 1g tablets` (`metformin` is not a pharmacy token), `Aspirin 2.4g tablets`, `Dextrose 4g tablets`, `4g tablets` (`Glucose 4g tablets` is caught by the `glucose` token). Also a dose followed by a pack number under 30 with no pack word (`Nurofen 200mg 24 tablets`, `Ferrous sulfate 65mg 28 tablets`, `Thyroxine 50mcg 28 tablets`) does not veto on the dose rung (the R16a digit lookahead) and stays electronics - the flag-OFF verdict.

**Ask.** Close them WITHOUT a gram carve-out: extend the pharmacy TOKEN table (metformin, aspirin, dextrose, nurofen, ibuprofen, thyroxine, ferrous ... the pharmacy generics the Bahrain drug database already lists - `bahrain_approved_drugs` has 655 rows) so the token rung carries these, measured over the 360-record corpus with the ON delta enumerated; and decide whether a `<dose> <n> tablets` form (a dose followed by a count) may count as a pack context. Pin every row above in both directions.
"""),
    ("W4-8f: alef/hamza normalisation in the blocklist matcher; audit the Arabic drug/weapon lists for spelling variants", f"""
{CTX}

**What is wrong.** The v1 Arabic drug list carries only the hamza spelling of the opium token (أفيون), so the bare-alef form (افيون) is ALLOWED at HEAD under v1 and v2 alike - a pre-existing normalisation gap the unit measured and pinned as the current behaviour (ruling R14c). The same class applies to any AR token whose common spellings differ in alef/hamza (ا / أ / إ / آ) or in taa marbuta / haa and yaa / alef maqsura.

**Ask.** Normalise the AR side of the matcher (both the haystack and the terms) for the alef family and the other standard variants before matching, in BOTH v1 and v2 (a safety fix, so it changes the flag-OFF verdict on the bare-alef forms - state it as an unflagged security control with the measured newly-blocked set), and audit `app/data/content_blocklist.json`'s Arabic lists for variants; pin the bare-alef opium form as BLOCKED afterwards.
"""),
    ("W4-8g: car-accessory listings naming the MG or ML brands beside a model year read as a milligram/millilitre dose under ENABLE_CATEGORY_TOKEN_FIX", f"""
{CTX}

**Stated limit (ruling R16b, no carve-out).** A model year before the MG brand reads as a milligram dose: `2023 MG ZS tablet holder` and `tablet mount for 2021 MG HS` are electronics OFF and SUPPLEMENTS ON, pinned in both states. `2024 MG4 ...`, `ML350` and `ML 350` are electronics because a unit followed by a digit is a model code (R16a). No rule separates a car year + brand from a four-digit milligram dose (`2000 mg tablets` is real) without a new carve-out chain.

**Ask.** Measure the incidence on real shopping titles (the `_proof` corpus and the recorded L2 titles) before deciding; candidates are a car-accessory context word set (holder / mount / screen protector / dashboard) that cancels the unit rung, or the Bahrain drug database as a positive dose signal. The strings are on the flag's first-window canary list.
"""),
    ("PO-CATEGORIES-I18N-09b: the bare Arabic handgun token blocks massage / glue / caulk / heat / water guns", f"""
{CTX}

**What is wrong.** The Arabic audit (PO-CATEGORIES-I18N-09) measured that the bare AR handgun token blocks legitimate tool and toy queries: massage gun, glue gun, caulk gun, heat gun, water gun in Arabic. The W4-8 exemption map covered the AR rifle token's measured collisions (water / air / Nerf) but the handgun token got no qualifiers because the spec measured none for it at the time.

**Ask.** Measure the AR handgun collisions over the corpus and add the measured qualifiers to `v2.exempt.weapons.ar` (the R11 rule: qualifiers are the measured legitimate collisions plus the named context words), each pinned ALLOWED under v2 / BLOCKED under v1, with bare and intent forms still blocked under both.
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
