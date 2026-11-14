# D4: our own database (the knowledge base, kb_*) at 731bcddf

This is a read-only report. Every code citation is `path:line` in the export of 731bcddf. E = ESTABLISHED: read in the code, or a quoted record line. L = LIKELY: an inference. None of the job scripts, kb_serve.py, kb_ingest.py, kb_service.py or migrations 045/052 changed between a74caba7 and 731bcddf (`git diff --stat` touches only scripts/meas_claude_gate.py, legal files and two spine scripts). T5's line numbers for those files still hold.

## 0. Short answer

1. **T5 is confirmed and has one big correction.** The KB is keyed on the parsed brand. The app's normal input is two typed fields (`product_a` / `product_b`, SmartCompareApp/src/screens/HomeScreen.tsx:459). That input becomes `brand ""` with the typed text as the name (structured_comparison_service.py:4438-4453, the same shape at :1959-1970). With an empty brand, `kb_product_id` returns None:
   - `spine_key` gives an empty brand axis (spec_spine_service.py:203-207, 242);
   - `kb_product_id` then refuses an empty `parts[1]` (kb_service.py:258).

   As a result, **both `fetch_cards` (kb_serve.py:166-168) and `kb_ingest.run_job` (kb_ingest.py:416-419) skip both slots of every typed two-field compare.** No later step refills the brand: `_fetch_product_data` copies `brand ""` into the result (structured_comparison_service.py:5966, 5983), and the relay's log line "Fetching reviews for:  Tyger" has the double space that shows it. (E)

   Consequence: flipping ENABLE_KB_INGEST and ENABLE_KB_FIRST_SERVE today would read and write nothing for the owner's typed compares, even with a full KB. Only the LLM-parse path and the camera path carry a brand. (E for the code; L that nearly all phone compares use two fields.)
2. **No code turns typed text into a canonical product.** kb_brands (300 rows) has **no runtime reader**: its name appears only in the column list, the builder and the Wikidata seeder (kb_service.py:58, 98, 826; kb_seed_common.py:55; seed_kb_brands_wikidata.py). The only brand list matched against typed text is the 75 `houses` of data/fragrance_lexicon.json. That list feeds the fragrance-only gate (app/services/category_gate.py), which only gates and never fills a brand; that flag is believed OFF. The card RPC looks up one exact id (`WHERE p.id = p_product_id`, migrations/045_kb_core.sql:480-481). There is no alias table, no fuzzy index and no candidate search. (E)
3. **The KB is empty for legal and corpus reasons, not code reasons.**
   - The feed walker needs `tos.verdict = "allowed"` (cron_feed_walker.py:380-382), and 0 of 410 rows have one.
   - The seeder reads only local HTML and exits on "no corpus" (seed_kb_batch.py:385-388).
   - PDP discovery writes hints only for juices that already have offers (cron_pdp_discovery.py:119-145). (E)
4. **Even a populated KB rarely gives a FULL hit from the jobs alone.** A FULL hit needs four things (kb_serve.py:339-341): identity `high`, a fresh price, complete specs and an image. The jobs fall short on three of them (E):
   - **Identity.** The walker sets `high` only when a product has a valid GTIN, and a WooCommerce product never does (cron_feed_walker.py:184, 326). The seeder follows the same GTIN rule (seed_kb_batch.py:326).
   - **Specs.** Complete specs need `concentration`, `scent_family` and `season` (extraction_service.py:368-403 minus kb_serve.py:55). No automated job writes a `concentration` spec row: the seeder's SEED_FIELDS lack it (seed_kb_batch.py:54-57) and ingest never writes kb_specs (kb_ingest.py:26). Only the operator path can (kb_operator.py:371-373).
   - **Image.** The walker writes no image (0 matches for `build_image_row` / `images` in cron_feed_walker.py).

## 1. (a) What each job does at 731bcddf (T5 confirmed)

| Job (flag; Railway service) | Collects / from | Rule that blocks it today | Writes |
|---|---|---|---|
| D09 feed walker (`ENABLE_FEED_WALKER`; feedwalker) | Shopify `/products.json`, Woo Store API, on live registry hosts, Bahrain tier first (cron_feed_walker.py:68-86) | ToS verdict `allowed` (:380-382) and `PoliteFetcher(require_tos=True)` (:447). Brand = Shopify `vendor` or Woo `brands[0]`, never guessed; otherwise `no_brand` (:173-178, 252, 323-326) | kb_products (identity `high` only with a GTIN, else `medium`; the name is the raw retailer title), kb_variants, kb_offers in the registry currency with rung `expected_missing` (Shopify, :271) or `platform_api` (Woo, :316-319). No images, no specs |
| D11 PDP discovery (`ENABLE_PDP_DISCOVERY`, sub `ENABLE_CC_CDX`; pdpdiscovery) | robots-declared sitemaps of JSON-LD hosts (cron_pdp_discovery.py:1-15) | APPLY matches only "ranked juices", meaning juices with at least one kb_offers row (:119-145). With 0 offers it matches 0 by construction | kb_gaps `pdp_<hash>` hint rows only. It fetches no PDP |
| S81-16 seeder (`ENABLE_KB_SEED`; kbseed) | local `*.html` (seed_spec_spine.py:269-275) with a JSON-LD Product carrying a brand and a name plus a fragrance signal (:233-266). Text = name + description, up to 4,000 characters (:85) | the page host must be live with a robots record that allows it. **No ToS check** (`url_gate` without `require_tos`, seed_kb_batch.py:197). No corpus on Railway | kb_products / kb_variants plus cited kb_specs for 11 fields. Model `anthropic_model("text")` = claude-haiku-5-5 (model_config.py:218, 227-234); key `ANTHROPIC_API_KEY` snapshot at import (seed_kb_batch.py:31); bound `KB_SEED_MAX_USD` <= 10 (:122-123); `KB_SEED_MAX_JUICES` 500 (:126-127) |
| S81-17 ingest (`ENABLE_KB_INGEST`, on web) | each successful compare, fire-and-forget (structured_comparison_service.py:3968-3988) | needs pair identity high/medium **and a non-empty brand** (kb_ingest.py:412-419). Offers: genuine BH method, robots-allowed URL, region bahrain, never a KB price (:445-448) | kb_products/variants (high only), kb_offers (market BH), kb_images, kb_reviews (aggregates), kb_gaps. Never kb_specs |
| S81-19 enrich (`ENABLE_KB_ENRICH_WORKER`, `ENABLE_KB_GAP_FILL`; kb-enrich, already apply) | open non-`pdp_` gaps, through registry search templates and pdp hints (cron_kb_enrich.py:14-27) | `require_tos=True` too; gaps come only from ingest | offers / images / reviews; a `specs` gap goes to `licence` (:66) |
| D16 operator (`ENABLE_OPERATOR_INGEST`) | a page a person browsed, posted with the admin key | host live, or blocked with `tos.reviewed_at` | every table, including any spec field |

**ENABLE_KB_FIRST_SERVE (kb_serve.py).** It runs one task before the product gather (structured_comparison_service.py:4559-4562), bounded by `KB_FIRST_SERVE_TIMEOUT_SECONDS` (1.0 s default). It reads two `kb_product_card` RPCs through `db_offload.run_db` (kb_serve.py:151-182). For each slot (structured_comparison_service.py:6049-6076):
- **Price.** It serves a KB price only for region `bahrain`, an offer in market `BH` and currency `BHD`, not marked out of stock, from an allowed source (kb_serve.py:278-281).
  - "Fresh" means within `GENUINE_PRICE_DB_TTL` (7 days).
  - Otherwise the price is "asof", but only for a client that sends `price_asof`, up to 30 days (:283-289). The app sends none, so anything older is refused.
  - A served price carries `as_of`, `size` when a variant has a size, and `_cache_source "kb"` (:216-234).
- **Specs.** It uses the KB specs only when they are complete (:318; structured_comparison_service.py:6065).
- **Image, rating, review count:** https image only (:320-326); rating and review count as aggregates (:328-337).
- **Hit level.** Any card that exists is at least `partial` (:341). A missing card is `miss`, and the slot runs the normal live path.

## 2. (b) Can the KB be the product resolution catalog?

**What exists (E, 045 / 052):**
- **kb_products:** brand (free text, not linked to kb_brands), `line` (written by nobody: no writer passes `line=`), name, concentration (7 values), audience (men / women / unisex) and identity_confidence (045:135-148).
- **kb_variants:** size_ml, GTIN (check digit enforced), sku (045:150-166).
- **kb_images:** image URLs (045:202-226).
- **kb_brands:** qid, label_en, label_ar, official_host (052). There is no alias column, so "Armani" and "Emporio Armani", or "Bvlgari" and "Bulgari", have no link.
- **Product identity:** the id is `fragrances|<brand axis>|<sorted identity tokens>|<conc>`. It is deterministic. Flanker words stay distinct: fragrance has no variant qualifiers (price_service.py:5099-5101), so "Intensely" and "Elixir" remain identity tokens. The brand-alias fold covers 13 groups, including `{armani, giorgio, emporio}` (price_service.py:5177-5199).

**What is missing for "typed text -> one product or a short list" (L, a design proposal):**
1. **Schema** (a new migration, for example 05x_kb_resolve.sql):
   - `kb_aliases(alias_norm text, lang, kind ∈ {brand, line, product, misspelling, arabic, retailer_title}, brand_qid → kb_brands, product_id → kb_products nullable, source, weight, created_at)`, unique on (alias_norm, kind, coalesce(product_id, brand_qid));
   - a btree index on alias_norm, plus a `pg_trgm` GIN index for misspellings ("Tyger" -> Bvlgari "Tygar"). Whether the extension is available is not checked; that is a read-only `pg_extension` read;
   - `kb_products.brand_qid` (FK, nullable) and a clean display name (today `name` is the first retailer title seen, because inserts ignore duplicates);
   - an RPC `kb_resolve(p_text, p_lang, p_limit)` that returns scored candidates.
2. **Code:**
   - a new `app/services/kb_resolve.py` behind a new flag. It normalizes with the price path's folding, finds the brand by the longest alias match, then matches the remaining tokens to line and product aliases. It returns ONE product when the top score clears a margin, otherwise up to about 3 candidates;
   - the call goes into the Step-1 explicit-pair branch (structured_comparison_service.py:4438-4453) and into `_explicit_pair_products` (:1959-1970). It fills `brand`, `name` and `variant` before `fetch_cards` and before the live search;
   - this one change also lets KB ingest and serve match;
   - the client needs a "Did you mean" picker for a candidate list (JS only, so an over-the-air update is possible).
3. **Alias seed sources:**
   - kb_brands labels (en/ar);
   - a small hand list of house families (Armani, Bvlgari/Bulgari, Dior/Christian Dior, and similar);
   - feed-walker titles (`retailer_title`);
   - the seeder's JSON-LD names;
   - later, typed queries that the user confirmed in the picker.

   Feed and seed rows give the line names that resolution needs, such as "Stronger With You" → Emporio Armani. Without such rows, "stronger with you" has no brand to find.

## 3. (c) Ordered steps

### A. Background jobs that can run now (no change on the phone until a live flip)

| # | Who | Flag / command | Waits on | What changes |
|---|---|---|---|---|
| A1 | OWNER verdict | fill FEED_HOSTS_TOS_LIST.md rows 1-13 first (the Bahrain BHD hosts), then 15 and 18-21; the RELAY writes `kb_merchants.tos {reviewed_at, verdict, terms_url}` | the owner's legal reading of each site's terms | nothing visible |
| A2 | RELAY run | feedwalker `ENABLE_FEED_WALKER=true`, read the logs on the plain word FEED_WALKER, then set `false` | A1 | per-host products / kept / `no_brand` counts; 0 rows written |
| A3 | RELAY run (owner yes) | `ENABLE_FEED_WALKER=apply` twice, a day apart, then `false`; then a read-only count of kb_offers with last_seen > first_seen | A2 clean | kb_products/variants/offers rows, mostly `medium` identity |
| A4 | OWNER yes | the feedwalker cron, daily (06:30 UTC was suggested), away from robots-registry 02:30 | A3 | keeps offers inside the 7-day fresh window |
| A5 | BUILD (small) then OWNER yes + RELAY | fix the seeder's page filter (non-perfumes were admitted: teacup, burner, mists, a decant, a dupe). Then run `ENABLE_KB_SEED=apply` on kbseed plus the box `--corpus` run (KB_JOBS note §4B) | the filter fix; the Anthropic key (web's key by reference; memory says a production key is proven on web) | about 41 juices, about 0.09 USD by the DRY bound; none of the golden pairs |
| A6 | RELAY run | pdpdiscovery `ENABLE_PDP_DISCOVERY=apply`, then `false` | A3 has written offers | `pdp_` hints for kb-enrich |
| A7 | OWNER (optional) | Common Crawl Terms sign-off, then `ENABLE_CC_CDX=true` + `KB_CC_INDEX` with a DRY first | owner item 15 | more PDP URLs |

### B. Build units (server deploy unless stated)

| # | Unit | Why |
|---|---|---|
| B1 | KB resolver: the migration + kb_resolve.py + the explicit-pair wiring, behind a new flag | without it, ingest and serve never match typed compares (§0.1) |
| B2 | client candidate picker (over-the-air update) | "Tyger" is ambiguous: the poem, the truck parts, Bvlgari Tygar |
| B3 | walker extras: image rows from Shopify `images[].src` / Woo `images`; a cited `concentration` spec row from the product's concentration axis; promote identity to `high` when two or more merchants agree on one id | makes a FULL hit reachable |
| B4 | corpus fetcher: politely save the HTML of D11-listed PDPs (vperfumes.com, faces.ae/sa and others) into a corpus folder or a storage bucket that the kbseed service can read | the seeder's corpus is git-excluded; D11 found 16,730 URLs |

### C. Live-path flips on web (one canary window each, the owner's yes)

| # | Flag | Waits on | What the user would see |
|---|---|---|---|
| C1 | `ENABLE_SYNC_DB_OFFLOAD` (its state on web is not in my lists). If ON, skip; if OFF, every KB read blocks the event loop (T5 gate) | none | nothing |
| C2 | `ENABLE_KB_INGEST` | C1, B1 (otherwise it writes about 0 rows from typed compares) | nothing visible; the KB grows from real compares |
| C3 | the new resolver flag | B1, kb_aliases seeded | the full product name ("Emporio Armani Stronger With You EDT"), the right brand on the review and spec searches, and a picker instead of the Blake poem |
| C4 | `ENABLE_KB_FIRST_SERVE` | C1, A3 + C2 data, the counsel ruling on dated prices (T5), optionally `ENABLE_VERDICT_CACHE_LOG` first | Bahrain-shop BHD prices with a size and an as-of date; faster slots on a FULL hit |
| C5 | `ENABLE_KB_GAP_FILL` on kb-enrich (an ops flip, not web) | C2 gaps exist, A1 verdicts | missing prices and images fill in overnight |
| C6 | `ENABLE_OPERATOR_INGEST` | `tos.reviewed_at` on the blocked hosts | hand-captured items for blocked sellers |

## 4. (d) What a lawful, durable catalog also needs

**Which feed hosts matter for BHD.** Only rows 1-13 of the list can put a price on the page (kb_serve.py:278-281). Judged by host name (L):
- **Multi-brand designer sellers, most valuable for pairs like Armani vs Bvlgari:** bh.jashanmal.com (#1), beautyandblends.com (#6), bh-en.smellsoreal.com (#10), fragrancebh.com (#11), theperfumesclub.com (#13), alibaksh.com (#12).
- **Single-house Arabian stores, useful for their own lines only:** bahrain.naseem.com, bh.mubkhar.com, bh.taifalemarat.com, bh.azhaperfumes.com, bh.afnan.com.
- **Unclassified:** perfumistaaloud.com, goldencollections.net.
- **Woo stores need a `brands` taxonomy.** Without one, every product counts `no_brand` (cron_feed_walker.py:323-326). The A2 DRY will show how many. (L that it is many.)
- **The big Bahrain sellers seen live** (noon.com, 29.320 BHD) are not feed hosts. They reach the KB only through ingest or the operator path.

**Seeder.**
- **Claude:** yes. It uses claude-haiku-5-5 Message Batches with `ANTHROPIC_API_KEY` and the `KB_SEED_MAX_USD` bound, at about 0.0021 USD per juice by the DRY bound (0.087 / 41). The 10 USD cap covers about 4,700 juices at that rate, but `KB_SEED_MAX_JUICES` 500 caps one run. (E for the code; L for the arithmetic.)
- **Corpus:** the seeder can read only local HTML.
  - PDP discovery stores URLs, never pages.
  - The feed walker keeps no description text, although Shopify's `body_html` often lists the notes.

  So the corpus can come from those jobs only through B4 (fetch and save the pages) or a seeder change that reads saved feed descriptions. Either way it is a new fetch of merchant pages, which is the owner's terms call per host. (E that nothing does this today; L for the design.)

**Images and specs.**
- Images: today only ingest (identity high), enrich (ToS-gated gaps) and the operator path write them.
- Specs: only the seeder and the operator path write them. Notes, longevity and sillage are licence fields: they are served when cited but never count toward "complete" (kb_serve.py:55, 143-147).
- No source gives review text; the KB holds aggregates only (045:252-270).

**Risks.**
- **Terms:** the verdict is the owner's per host, and enrich and the walker both enforce it.
- **Robots:** the record is re-read daily; a stale record closes the host.
- **Staleness:**
  - prices older than 7 days are refused for today's app;
  - the walker must run on a schedule;
  - a changed amount makes a new row (045:28-40).
- **Wrong-product joins:**
  - an id collision when two retailer titles reduce to the same tokens;
  - a decant or dupe minted as a product (the seeder note);
  - a size-less variant `|-` whose price would show with no size (kb_serve.py:296-300);
  - a resolver that picks a brand on a weak match. The resolver needs a score margin, and a picker below it.
- **Load:** the 1 s KB read bound and the offload gate.

## 5. Not settled here

- The state of ENABLE_SYNC_DB_OFFLOAD and of ENABLE_PARSE_PRESPLIT on web. The pre-split gives the same `brand ""` shape (structured_comparison_service.py:4080-4083).
- Whether pg_trgm is enabled.
- The real `no_brand` share on the BHD hosts.
- Whether the owner's 21:19 compare took the explicit-pair branch. A missing "Parsing query" log line would show it.
