# Test Coverage Design: 7 Uncovered Areas

**Date**: 2026-02-22
**Status**: Approved
**Cost per full run**: ~$0.06 (live tests) + $0 (mocked tests)

## Goal

Add ~44 tests across 7 files covering all untested core logic: camera/vision, singleton state, iHerb scraping, rating tiers, price fallback, unified search merging, and error paths. Hybrid approach: live tests where possible for shipping confidence, mocked only where edge cases can't be triggered live.

## Test Architecture

- **Convention**: Match existing test patterns (`sys.path.insert`, `@pytest.fixture def service()`, `run_async()` for async)
- **Markers**: `@pytest.mark.unit` (mocked, free), `@pytest.mark.live_unit` (live, costs money)
- **Mock strategy**: Mock at external boundaries only (Serper, OpenAI, httpx, curl_cffi, Supabase)
- **Run commands**:
  - All: `python -m pytest tests/ -v -m "unit or live_unit"`
  - Free only: `python -m pytest tests/ -v -m unit`
  - Per-file: `python -m pytest tests/test_<area>.py -v`

## File Specifications

### 1. `tests/test_camera_vision.py` (~6 tests, LIVE)

Tests the camera/vision identification pipeline end-to-end.

| Test | Marker | What it verifies |
|------|--------|-----------------|
| 2 images identify 2 products with names/brands | live_unit | Vision pipeline works |
| 1 image returns "need_second_product" | live_unit | Single-product handling |
| `size_or_count` field present for supplements | live_unit | OCR reads packaging |
| Identified products feed into compare pipeline | live_unit | Vision-to-comparison handoff |
| Invalid image (empty bytes) graceful error | unit | Error response, no crash |
| Response schema: `products` array with fields | live_unit | Contract validation |

**Mocks**: None for live tests. For error test: mock OpenAI client.
**Test images**: Use existing `test_iphone.png`, `test_two.jpg` in repo root.
**Cost**: ~$0.024

### 2. `tests/test_singleton_state.py` (~4 tests, HYBRID)

Tests singleton service doesn't leak state between requests.

| Test | Marker | What it verifies |
|------|--------|-----------------|
| `_shopping_items_cache` empty at start of each call | unit | State reset |
| `total_cost` and `api_calls` reset per request | unit | Counter reset |
| Two sequential comparisons, second not polluted | live_unit | Cross-request isolation |
| `get_comparison_service()` returns same instance | unit | Singleton pattern |

**Mocks**: Mocked tests patch `compare_from_text` internals to verify reset. Live test makes 2 real API calls.
**Cost**: ~$0.02

### 3. `tests/test_iherb_scraping.py` (~7 tests, LIVE)

Tests iHerb direct scrape via curl_cffi. All free (no API keys, just HTTP).

| Test | Marker | What it verifies |
|------|--------|-----------------|
| Known supplement (NOW D3) returns price + brand + URL | live_unit | Basic scraping |
| Regional store (bh.iherb.com) returns BHD currency | live_unit | Regional pricing |
| Brand matching: "NOW" filters correctly | live_unit | Brand logic |
| Number matching: "5000 IU" doesn't match "1000 IU" | live_unit | Variant precision |
| Unknown product returns None (not crash) | live_unit | Empty results |
| Query cleanup strips "supplement", pill counts | unit | Search optimization |
| Non-supplement brand returns None | live_unit | Brand filter |

**Mocks**: Only query cleanup test is mocked (tests internal string logic).
**Cost**: $0 (HTTP only)

### 4. `tests/test_rating_tiers.py` (~7 tests, HYBRID)

Tests rating tier selection, consensus logic, and regional fallback.

| Test | Marker | What it verifies |
|------|--------|-----------------|
| Popular phone gets Tier 1 rating (Amazon/BestBuy) | live_unit | Real tier selection |
| Rating 1.0-5.0 with source attribution | live_unit | Data quality |
| `rating_source` has url, source, extract_method | live_unit | Schema |
| Empty shopping items returns empty dict | unit | Edge case |
| Only Tier 3 <1000 reviews rejected | unit | Threshold |
| 3+ identical ratings triggers consensus | unit | Consensus path |
| BH search fails, US fallback triggers | live_unit | Regional fallback |

**Mocks**: Edge case tests construct shopping item dicts directly, call `_extract_rating_from_shopping()`.
**Cost**: ~$0.003

### 5. `tests/test_price_fallback.py` (~6 tests, HYBRID)

Tests the 3-tier price fallback chain and supplement routing.

| Test | Marker | What it verifies |
|------|--------|-----------------|
| Electronics gets Tier 1 (Serper Shopping) price | live_unit | Primary path |
| Supplement routes to iHerb (not Serper Shopping) | live_unit | Supplement routing |
| Price has amount, currency, retailer, url | live_unit | Schema |
| High-value item price >= BHD 50 | live_unit | Sanity filter |
| All tiers fail returns `estimated: true` | unit | Fallback chain end |
| `_convert_to_bhd()` various currencies | unit | Currency conversion |

**Mocks**: Tier-fail test patches all Serper + GPT calls to return None/empty.
**Cost**: ~$0.005

### 6. `tests/test_unified_search.py` (~4 tests, HYBRID)

Tests search call merging saves API calls and cost.

| Test | Marker | What it verifies |
|------|--------|-----------------|
| Full comparison api_calls <= 15 | live_unit | Call efficiency |
| total_cost <= $0.015 | live_unit | Cost tracking |
| Cached product triggers zero Serper calls | unit | Cache bypass |
| search_results param passed to specs + reviews | unit | Sharing logic |

**Mocks**: Cache test patches `get_cached()` to return data. Sharing test patches `_get_specs` and `_get_reviews` to verify `search_results` kwarg.
**Cost**: ~$0.01

### 7. `tests/test_error_paths.py` (~10 tests, ALL MOCKED)

Tests error handling and edge cases that can't be triggered live.

| Test | Marker | What it verifies |
|------|--------|-----------------|
| `_convert_to_bhd(None, "USD")` handles None amount | unit | Null safety |
| `_convert_to_bhd(100, None)` handles None currency | unit | Null safety |
| Malformed GPT JSON returns error dict | unit | JSON parse failure |
| Serper empty results triggers fallback | unit | Empty data handling |
| Drug DB timeout continues without context | unit | Graceful degradation |
| `_calculate_freshness` with `price: None` | unit | NoneType guard |
| `_parse_price_string` with garbage input | unit | Input validation |
| `_is_supplement_query` with anti-keywords | unit | False positive prevention |
| `_strict_title_match` with hyphens (D-3 vs D3) | unit | String normalization |
| `_numbers_match` with year vs count | unit | Number disambiguation |

**Mocks**: All tests call methods directly with crafted inputs or mock external dependencies.
**Cost**: $0

## Team Structure

3 Opus agents, each owns 2-3 files. Cross-QA: each agent reviews another's work.

| Agent | Owns (writes) | QAs (reviews) |
|-------|--------------|---------------|
| Agent A | test_camera_vision, test_singleton_state, test_iherb_scraping | Agent B's files |
| Agent B | test_rating_tiers, test_price_fallback | Agent C's files |
| Agent C | test_unified_search, test_error_paths | Agent A's files |

**Workflow**:
1. Each agent writes their test files (red-green: write failing test, verify it fails, make it pass)
2. When done, idle agents write additional red-green tests to hit 80% coverage on their areas
3. Cross-QA: each agent reviews the other's work for completeness, correctness, and edge cases
4. If QA finds issues, work is sent back for fixes
5. Team only dissolves when all QA passes

## Success Criteria

- All 44 tests pass: `python -m pytest tests/ -v -m "unit or live_unit"`
- No test depends on another test's execution order
- Mocked tests run in <5s total
- Live tests complete within existing integration test timeframe (~4 min)
- Total live test cost per run: ~$0.06
