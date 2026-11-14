# R1 - Resolving a typed name to one product, and building a product catalog

S95-FIX read-only research agent, 2026-11-14. Code cited at 731bcddf (plain export under scratchpad/src/731bcddf). Web sources are listed at the end with their URLs. ESTABLISHED = read in code or fetched from the source. LIKELY = inference.

## 0. Summary

- Both failures ("Tyger" -> truck parts and a William Blake poem; "stronger with you" -> a 15 ml decant and a no-size noon price) share one root: **the typed text goes to the web search as it is, with no brand, line, concentration or size fixed first.** At 731bcddf MYEZ has no catalog to resolve against. kb_products is empty, and nothing in app/ reads it (see section 1).
- The industry pattern is the same everywhere (Instacart, DoorDash, Shopify, idealo, Bing Shopping, and the entity-linking papers). Find **candidates** in your own catalog using cheap lexical and phonetic matching. Let a model (or rules) **choose only among those candidates**. Set a **confidence threshold** below which the system **asks the user** ("Did you mean Bvlgari Tygar?"), or abstains, instead of guessing. Only then search for offers, and search with the canonical name.
- There is no usable open perfume catalog that is free to take. Wikidata (CC0) has about 402 perfume items, with 0 GTINs and 21 images (ESTABLISHED, SPARQL count). It does not have Tygar or Stronger With You. Open Beauty Facts (ODbL, so share-alike) has 455 items in "fragrances". It has Stronger With You EDT and Intensely with EANs, but nothing for Tygar (ESTABLISHED, API). The big perfume datasets (Kaggle/TidyTuesday Parfumo set, FragDB, 10ML counts) all come from Parfumo, Fragrantica or Basenotes and are forbidden to us. **MYEZ has to build its own catalog** from brand sites and the GCC retailers it already reads (Shopify /products.json, WooCommerce, JSON-LD), with Claude doing the normalisation offline.
- Recommended stack: Postgres pg_trgm + fuzzystrmatch (levenshtein) + RapidFuzz (MIT) for candidates; an alias table fed by query logs; Claude restricted to picking a catalog id or "none"; a two-threshold auto/ask/abstain gate; later, optionally, pgvector (PostgreSQL licence) embeddings. Splink/dedupe (MIT) for offline offer dedup only.

## 1. What 731bcddf has today (ESTABLISHED unless marked)

| Item | Where | State |
|---|---|---|
| kb_products (brand, line, name, concentration, audience, identity_confidence) | migrations/045_kb_core.sql:135-148 | The schema fits a canonical product table. It has no alias column and no search index. Empty in prod (T5_kb_path.md:14). |
| kb_variants (concentration, size_ml, gtin with check digit, sku) | migrations/045_kb_core.sql:150-166 | Fits the variant level (concentration x size, the level a GTIN identifies). |
| kb_offers (variant_id, merchant, market, amount, size_ml, first_seen/last_seen) | migrations/045_kb_core.sql:168-200 | Fits offers with freshness. A belt in the table refuses fragrantica/parfumo/basenotes URLs (045:186). |
| kb_brands (Wikidata qid, label_en, label_ar, official_host) | migrations/052_kb_brands.sql:55-79 | 300 rows imported (memory). The header says it has no alias table and no product link: 052_kb_brands.sql:15-16. |
| Readers of kb_products / kb_brands on the request path | app/services/kb_service.py functions at :169-:826 are builders and validators only; a grep for `table("kb_products` finds nothing | None. No resolver exists. |
| Fuzzy or phonetic matching | grep for rapidfuzz, jellyfish, difflib, levenshtein, metaphone in app/ = 0 hits; grep for pg_trgm/fuzzystrmatch in migrations/ = 0 | None. |
| Brand alias groups | app/services/price_service.py:5177 (`_BRAND_ALIAS_GROUPS`), used at :5398, :6944, :7436 and in spec_spine_service.py:192-204 | These fold brand spellings when scoring results after the search. They do not resolve the query before it (LIKELY, from where they are used). |

## 2. (a) Resolving a typed name to ONE canonical product

### 2.1 The pipeline (consensus pattern)

1. **Normalise**: lowercase, strip accents (anyascii), drop the noise words "perfume", "cologne", "ml", "for men". Pull out the explicit parts with the regexes MYEZ already has (concentration, size_ml; spec_spine migration 035:26 mentions `extract_concentration` and `extract_size_ml_any`).
2. **Candidate generation in our own catalog**, never on the open web. Use several cheap signals together:
   - exact or alias hit (an alias table: "SWY", "stronger with u", Arabic transliterations, common misspellings);
   - trigram word similarity (pg_trgm `word_similarity`, GIN index);
   - edit distance on the name token (fuzzystrmatch `levenshtein`, or RapidFuzz in Python);
   - phonetic codes. The PostgreSQL docs warn that metaphone/dmetaphone do not handle multibyte UTF-8 well, so use them only on the transliterated ASCII form;
   - later, a dense embedding (pgvector) for "blue chanel" -> "Bleu de Chanel" style paraphrases.
3. **Choose among the candidates**, by rules or by an LLM shown the top-k candidates with their ids. Its only allowed outputs are one of those ids or NONE. This is the retrieve-then-rerank design of LELA (arXiv 2601.05192). Instacart's Intent Engine adds post-generation checks so that answers stay within its taxonomy. GenDecider (NAACL 2024) warns that when the right item is missing from the list, the LLM still picks something. So "none of these" must be a real option and must be measured.
4. **Gate on confidence** with two thresholds. Above the high one: resolve silently. Between the two: show a "Which one did you mean?" list (with pictures). Below the low one: say so, or treat the input as a new item. The entity-linking literature uses exactly this similarity-threshold abstain rule (MHEL-LLaMo, arXiv 2601.08500; CEUR Vol-4314 on asymmetric costs). The conversational-search studies (Ma et al., CIKM 2024; the ProductAgent benchmark) find clarifying questions help most at the first turn. They also find that more than one question lowers satisfaction. So ask once, with at most about 4 options.
5. **Search for offers with the canonical identity** (brand + line + concentration and, where known, size or GTIN), not with the user's string. Google Merchant Center's own rule is that offers are matched by GTIN, or else by brand + MPN. Without them "accurate matching can't be assured" (Google support page 6324461 and secondary guides).

### 2.2 The two failing inputs, scored (ESTABLISHED: computed locally with a pg_trgm-style trigram function and Levenshtein in pure Python; no library installed)

| Query | Candidate | trigram sim | word-sim | edit distance to name |
|---|---|---|---|---|
| Tyger | Bvlgari Tygar | 0.19 | 0.50 | **1** |
| Tyger | Tyger Auto Tonneau Cover (a web result) | 0.26 | **1.00** | - |
| Tyger | Emporio Armani Stronger With You | 0.05 | 0.33 | 28 |
| stronger with you | EA Stronger With You | **0.55** | 1.00 | - |
| stronger with you | EA SWY Oud | 0.49 | 1.00 | - |
| stronger with you | EA SWY Intensely / Absolutely | 0.42 | 1.00 | - |

What this shows:
- **Trigram alone is weak on a short one-word typo.** "Tyger" and "Tygar" share only half their trigrams. On the open web the exact word "Tyger" (the truck brand, the Blake poem) beats the intended item. Edit distance (1) and phonetics fix it: both words likely give the code TKR (LIKELY, not computed). They fix it **only because the candidate set is limited to fragrances**. This is why resolution must run against a fragrance catalog, not against web results.
- **Flankers tie on word-similarity (1.00 for all four).** The tie-break that works is "the fewest extra tokens wins". The base Stronger With You EDT has the highest whole-string similarity (0.55), so it is the default. The next step should be a short choice list ("Stronger With You EDT / Intensely EDP / Absolutely / Oud"), since the flankers smell different and are priced differently. The gap between the top two scores is the ambiguity signal (the score-spread heuristic in the e-commerce agent paper, arXiv 2509.06185).
- Concentration and size are **variant** attributes (kb_variants). Resolve the product first. Then resolve the variant from the explicit tokens, or ask, or default to the most-offered size. Never let a 15 ml decant (the "Aura Fragrance" 6.38 BHD case) or a no-size listing stand for the product.

### 2.3 How the big players do query understanding and matching

- **Etsy** (Code as Craft, 2017): a spelling model trained on query reformulations. Two spellings that lead users to click the same items are treated as the same intent. MYEZ's equivalent: log typed text -> the chosen candidate, and promote frequent pairs into the alias table.
- **Amazon**: phonetic spelling correction for e-commerce (ECNLP 2022), and a RAG spelling corrector for new brand names (arXiv 2410.11655). Its AutoKnow product graph (KDD 2020) covers taxonomy, attribute extraction, anomaly detection and *synonym discovery* for beauty and consumables.
- **Instacart** (2025 Intent Engine): one LLM layer replaced several separate query-understanding models. It works because of grounding (catalog context in the prompt) plus guardrails that reject outputs outside the taxonomy. **DoorDash** keeps its LLMs mostly offline, in batch, to build knowledge graphs. Both apply to MYEZ: Claude offline to build and clean the catalog; online only to pick among candidates.
- **Shopify** (Catalog clustering parts I-II, 2026): most grouping is deterministic (barcode, title, merchant schema). LLMs are used only for the hard cases, and the approach is precision-first. "A missed match is not fatal." A wrong edge in their earlier graph method merged large clusters of wrong products.
- **idealo** (tech blog; PyCon DE 2022): offers that do not match the catalog are clustered with Sentence-Transformers + FAISS. EAN alone fails because EANs are missing, wrong, or differ per size.
- **Bing Shopping** (Microsoft Research, KDD): a learned function matches unstructured offers to structured catalog products.
- **LLM entity matching** (Peeters, Steiner, Bizer; arXiv 2310.11244, 2305.03423, 2409.08185): GPT-4-class models reach about 89 F1 zero-shot on the hard WDC Products benchmark (figure from a secondary leaderboard). This makes an LLM a credible pairwise judge of "same product?" when offers are deduplicated offline.

## 3. (b) Open-source repositories (licence read from the GitHub API or the LICENSE file, 2026-11-14)

| Repo | Licence | Activity (stars, last push) | Reuse for MYEZ |
|---|---|---|---|
| rapidfuzz/RapidFuzz | MIT | 4.2k, 2026-11-09 | **Code.** Levenshtein, Jaro-Winkler, token_set ratio and `process.extract` over a few-thousand-row in-memory catalog, in the FastAPI process. |
| jamesturk/jellyfish | MIT | 2.2k, 2026-10-16 | **Code.** Metaphone, Soundex, NYSIIS. |
| mammothb/symspellpy / wolfgarbe/SymSpell | MIT / MIT | 0.9k / 3.5k, Nov 2026 | **Code.** Spelling correction against a dictionary built from the catalog's tokens. |
| anyascii/anyascii | ISC | 0.4k, 2026-06 | **Code.** Turns Unicode into ASCII before the phonetic step (Arabic script input). |
| pgvector/pgvector | PostgreSQL licence (LICENSE file; GitHub shows NOASSERTION) | 23.7k, 2026-11-14 | **Code / extension** (Supabase offers it). Embedding candidate search in phase 2. |
| huggingface/sentence-transformers | Apache-2.0 | 19.3k, 2026-11-13 | **Code.** Offline embeddings for clustering offers (the idealo pattern). |
| facebookresearch/faiss | MIT | 41.7k, 2026-11-14 | Only needed when the catalog is large; pgvector is enough at MYEZ scale. |
| dedupeio/dedupe | MIT | 4.5k, 2025-07-29 (slower) | **Offline idea/code**: active-learning dedup of offers into products. Overkill on the request path. |
| moj-analytical-services/splink | MIT | 2.6k, 2026-11-11 | **Offline code**: probabilistic record linkage (Fellegi-Sunter) over DuckDB. Good for merging retailer feeds; not for single queries. |
| J535D165/recordlinkage | BSD-3-Clause | 1.1k, 2024-02 (stale) | Idea only. |
| zinggAI/zingg | AGPL-3.0 | 1.3k, 2026-11-03 | **Avoid** (AGPL; Spark). |
| openfoodfacts/robotoff | AGPL-3.0 | 0.1k, 2026-11-14 | **Idea only.** It proposes product facts from photos and OCR, and humans confirm them ("insights"). AGPL, so do not copy the code into MYEZ's public repo without accepting AGPL. |
| openfoodfacts/openfoodfacts-server, search-a-licious | AGPL-3.0 | 1.2k / 31 | Idea only. |
| openfoodfacts/openfoodfacts-python | MIT (LICENSE points to LICENSES/MIT.txt; GitHub shows Other) | 0.5k, 2026-11-01 | Code, if MYEZ reads Open Beauty Facts (ODbL terms still apply to the data). |
| pyrfume/pyrfume-data | MIT | 0.1k | Molecules and odour science, not retail products. Not relevant to identity. |
| HigumaSoft/aromatheca | none on the repo; the site says data CC BY 4.0 | 0 stars, alpha "v0.1.0", 2026-11-08 | Too early, and the data origin is not stated. Do not depend on it. |
| FragDB/fragrance-database | CC-BY-NC-4.0 (README badge) | 72 | **Forbidden.** README: "a full crawl: every fragrance page of the source", 134K fragrances with UGC reviews. Most likely a Fragrantica/Parfumo crawl (LIKELY). It is also non-commercial. |

No open perfume-specific product-matching project was found that is not built on Fragrantica or Parfumo data.

## 4. (c) Datasets for product identity

| Source | Licence / terms | Perfume coverage (measured 2026-11-14) | Origin | Verdict |
|---|---|---|---|---|
| **Wikidata** | CC0 (already MYEZ's brand source, 052:13-14) | About 402 items under "perfume" (Q131746) and its subclasses; **0 with GTIN (P3962)**, 21 with an image. Bleu de Chanel = Q16874465 (2010), Baccarat Rouge 540 present; **Stronger With You and Tygar absent** | Community edits | Good for brands (done) and a few hundred famous lines. It cannot be the product catalog. |
| **Open Beauty Facts** | Database ODbL; contents DbCL; **images CC BY-SA** (OBF terms page). Share-alike: a database derived from it must be shared under ODbL | 455 in "fragrances"; text search finds 6 Stronger With You rows (EDT 30/50/100 ml EANs 3605522040229/281/588, Intensely EDP 150 ml), **0 Tygar**, 1 Bleu de Chanel, Sauvage mostly noise | Crowd-sourced, scanned | A useful **EAN seed** for famous lines, but sparse and noisy. Keep any OBF-derived table separate so the share-alike duty stays limited to it. |
| **GS1 (Verified by GS1 / GEPIR)** | Terms of use must be accepted. Batch or API access is enterprise or national-office only. The GS1 UK terms forbid any use they do not explicitly allow | GTIN -> brand owner, product description and image when the brand owner filled them in | Brand owners | Use only to **check** a GTIN that is already in hand, under a signed agreement. Not a catalog to copy. An owner/legal step. |
| **Brand catalogues** (armanibeauty, bulgari.com, dior.com...) | Each site's terms and robots.txt | Complete line lists, flankers, concentrations, sizes, official images | First party | **The best source of identity.** Read the sitemaps and product JSON-LD politely; store facts, not page copies; check terms per brand (owner ToS verdicts, as for the KB jobs). |
| **GCC retailer feeds** already in the code (Shopify `/products.json`, price_service.py:15335-15354; WooCommerce; JSON-LD) | Each retailer's terms | What is actually sold in BH/GCC, often with a GTIN in JSON-LD | Retailers | **The main ingest stream** for variants and offers. These are also the pages MYEZ already prices. |
| Kaggle "Parfumo Fragrance Dataset" (TidyTuesday 2024-12-10) | Stated licence irrelevant | 59k perfumes | **Scraped from Parfumo** | **Forbidden.** |
| FragDB | CC-BY-NC-4.0 | 134k | Crawl of a perfume community site (LIKELY Fragrantica) | **Forbidden.** |
| 10ML datasets (IEEE DataPort) | CC BY 4.0 | Counts per year and price indexes, not products | Counts taken from Parfumo, Fragrantica and Basenotes | Not identity data; skip. |
| Kaggle eBay perfume listings / "perfumes price in KSA stores" | As stated on Kaggle (not verified) | Retail listings | Scraped from eBay and Saudi retailers (LIKELY, from the titles) | Do not use. Retailer terms are unknown, and the prices are stale. |
| WDC Products (Web Data Commons) | Not verified (page fetch failed) | Few beauty items | Common Crawl schema.org | Benchmark only. |

## 5. (d) How comparable projects build and refresh the knowledge base

- **Three tables**: canonical product (brand, line, concentration family) -> variant (concentration x size, GTIN) -> offer (merchant, price, currency, first and last seen). MYEZ's 045 schema already has this. The missing pieces are an **alias table** (alias text, normalised form, product_id, source = operator/log/brand/llm, hits, created_at) and search indexes.
- **Ingest** (Shopify, idealo, Bing): read merchant feeds or catalogs in batch. Match each offer to a variant: first an exact GTIN; then brand + normalised name + concentration + size; then a model for the hard rest. An offer that matches nothing goes to a **pending cluster**, not into the catalog. New products are created from clusters only when there is enough evidence (several merchants, or a brand page).
- **Deduplicate precision-first** (Shopify). A missed merge costs little; a wrong merge spreads (one wrong edge -> one big wrong cluster). Splink or dedupe, or an LLM pairwise judge, run offline over the pending clusters, with a human (the operator) confirming the merges that are not certain. This is the pattern of Robotoff's "insights" (AGPL; reuse the idea, not the code).
- **Freshness**: identity changes slowly (re-read a brand catalog monthly; flankers launch a few times a year). Offers change daily. Keep `last_seen` per offer and expire anything not seen within N days. MYEZ's kb_offers already has first_seen/last_seen (045:181-182).
- **Learn from use** (Etsy): every "which one did you mean?" answer is a labelled alias, so the catalog improves with traffic.

## 6. Recommendation for MYEZ (FastAPI + Supabase Postgres, 300 brands, empty products, Claude on the server)

1. **Seed a small canonical catalog first: about 300-500 products that cover most GCC searches.** Take the lines of the 300 kb_brands that GCC retailers actually sell (from the Shopify/WooCommerce reads MYEZ already does). Add each brand's own line list (owner ToS verdict per brand site) and the Wikidata/OBF items (OBF in its own table because of ODbL). Claude **normalises offline** (brand, line, flanker, concentration, audience, sizes) under a strict JSON schema. A product row is written only when a retailer or brand page supports it (identity_confidence high/medium). Server deploy plus an ops seeding run. Fixed set first: Bvlgari Tygar, the Stronger With You family, Sauvage EDT/EDP/Elixir, the Bleu de Chanel family.
2. **Add migration: `kb_aliases` + pg_trgm GIN index + fuzzystrmatch** (both are standard Supabase extensions). Add one RPC that returns the top 8 candidates, scored as max(alias exact, word_similarity, 1 - levenshtein/len), with a phonetic bonus on the ASCII form. RapidFuzz (MIT) in Python is an equivalent in-memory path while the catalog is small (a few thousand rows fit in RAM).
3. **Resolver gate before any search**: score >= about 0.85 and a clear margin over the second candidate -> resolve; about 0.5-0.85, or several flankers tied -> return a `disambiguation` payload (up to 4 candidates with image, brand, concentration) for the client to show as "Which one did you mean?" (this needs an App Store build or an OTA, depending on whether the client can render it); below that -> do not run the comparison. Tell the user the product was not recognised, and log a kb_gap row. Calibrate the thresholds on logged queries; the numbers here are starting values (LIKELY).
4. **Claude only as a constrained chooser** for the middle band. The prompt lists the candidate ids and the user's text. The output schema is {product_id | "none", confidence}. Reject any id not in the list (the Instacart guardrail; the GenDecider caution). Claude's own knowledge may *propose* a brand for a brand-less input ("Tygar is Bvlgari"), but the proposal has to resolve to a catalog row or it is treated as unresolved.
5. **Search with the canonical identity**: brand + line + concentration (+ size/GTIN) in the Serper/retailer queries. Keep a fragrance-only filter on results (the believed-OFF ENABLE_FRAGRANCE_ONLY_GATE is the existing hook to evaluate). This alone would have stopped "Tyger Auto" and the Blake picture (LIKELY).
6. **Later**: pgvector embeddings for paraphrases; Splink/LLM-judged offline merging of retailer offers into variants; promote aliases from logged choices; refresh offers daily and identity monthly.
7. **Do not** import any Fragrantica-, Parfumo- or Basenotes-derived dataset, whatever licence it states (FragDB, the Kaggle Parfumo set). **Do not** copy AGPL code (Robotoff, Zingg) into the public repo. Use GS1 data only under a signed agreement (an owner step).

## Sources

- Etsy spelling correction: https://codeascraft.com/2017/05/01/modeling-spelling-correction-for-search-at-etsy/
- Amazon phonetic spelling correction: https://amazon.science/publications/spelling-correction-using-phonetics-in-e-commerce-search ; RAG spelling for brand names: https://export.arxiv.org/pdf/2410.11655 ; weak-supervision spell correction: https://aclanthology.org/2023.acl-industry.66
- AutoKnow: https://arxiv.org/pdf/2006.13473 ; https://amazon.science/blog/building-product-graphs-automatically
- Instacart Intent Engine: https://company.instacart.com/tech-innovation/building-the-intent-engine-how-instacart-is-revamping-query-understanding-with-llms ; comparison: https://blog.bytebytego.com/p/why-doordash-instacart-and-uber-eats
- Shopify catalog clustering: https://shopify.engineering/catalog-clustering ; https://shopify.engineering/catalog-clustering-part-ii ; https://shopify.engineering/leveraging-multimodal-llms
- idealo: https://medium.com/idealo-tech-blog/automate-product-creation-by-clustering-millions-of-shops-offers-with-machine-learning-3db3162dbad4 ; https://pycon.de/archive/2022/talks/transformer-based-clustering-identifying-product-clusters-for-e-commerce/
- Bing Shopping offer matching: https://www.microsoft.com/en-us/research/wp-content/uploads/2010/08/matching_TR.pdf ; Google Product Search offer clustering (EDBT 2012): https://old.dbs.uni-leipzig.de/file/edbt2012_final.pdf
- LLM entity matching: https://arxiv.org/pdf/2310.11244 ; https://arxiv.org/pdf/2305.03423 ; https://arxiv.org/pdf/2409.08185
- Entity linking with LLM rerank and abstain: https://arxiv.org/pdf/2601.05192 ; https://arxiv.org/html/2601.08500v1 ; https://aclanthology.org/2024.naacl-short.22.pdf ; https://ceur-ws.org/Vol-4314/ReDH7.pdf
- Clarifying questions: https://pure.uva.nl/ws/files/292941595/3627673.3679875.pdf ; https://arxiv.org/html/2407.00942v1 ; https://www.arxiv.org/pdf/2509.06185
- Google identifiers: https://support.google.com/merchants/answer/6324461 ; https://support.google.com/merchants/answer/6098295?hl=en
- PostgreSQL fuzzystrmatch (multibyte caveat): https://www.postgresql.org/docs/18/fuzzystrmatch.html ; pg_trgm: https://neon.com/docs/extensions/pg_trgm.md
- Repos (licences via api.github.com/repos/<owner>/<repo>): https://github.com/rapidfuzz/RapidFuzz , https://github.com/jamesturk/jellyfish , https://github.com/mammothb/symspellpy , https://github.com/wolfgarbe/SymSpell , https://github.com/anyascii/anyascii , https://github.com/pgvector/pgvector (LICENSE file) , https://github.com/huggingface/sentence-transformers , https://github.com/facebookresearch/faiss , https://github.com/dedupeio/dedupe , https://github.com/moj-analytical-services/splink , https://github.com/J535D165/recordlinkage , https://github.com/zinggAI/zingg , https://github.com/openfoodfacts/robotoff , https://github.com/openfoodfacts/openfoodfacts-server , https://github.com/openfoodfacts/search-a-licious , https://github.com/openfoodfacts/openfoodfacts-python , https://github.com/pyrfume/pyrfume-data , https://github.com/HigumaSoft/aromatheca , https://higumasoft.github.io/aromatheca/ , https://github.com/FragDB/fragrance-database
- Wikidata API and SPARQL (queried 2026-11-14): https://www.wikidata.org/w/api.php , https://query.wikidata.org/sparql , item https://www.wikidata.org/wiki/Q16874465
- Open Beauty Facts terms and API (queried 2026-11-14): https://world.openbeautyfacts.org/terms-of-use , https://world.openbeautyfacts.org/cgi/search.pl
- GS1: https://gs1.org/docs/verified-by-gs1/public-verified-by-gs1-tou.pdf ; https://gs1uk.org/terms-and-conditions/verified-by-GS1 ; https://www.gs1au.org/resources/faq/verified-by-gs1
- Forbidden-origin datasets: https://rfordatascience.github.io/tidytuesday/data/2024/2024-12-10/readme.html (Parfumo) ; https://ieee-dataport.org/documents/perfume-launches-year-2010-2025-three-public-fragrance-databases (10ML, counts taken from Parfumo, Fragrantica and Basenotes)
