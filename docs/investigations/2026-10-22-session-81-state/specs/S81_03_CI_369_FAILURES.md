# PR #369 backend-tests failures on 21b37039 (GitHub runner, 2026-10-23 ~05:04 UTC): 4 failed / 24,745 passed; excerpt of the FAILURES section (timestamps stripped)


=================================== FAILURES ===================================
_____________ test_red_late_start_healthy_host_is_not_blacklisted ______________
tests/test_retro_w0_1.py:572: in test_red_late_start_healthy_host_is_not_blacklisted
    assert verdict is False
E   assert True is False
---------------------------- Captured stdout setup -----------------------------
{"timestamp": "2026-10-23T05:04:23.904004+00:00", "level": "INFO", "module": "extension", "message": "Storage has been reset and all limits cleared"}
------------------------------ Captured log setup ------------------------------
INFO     slowapi:extension.py:361 Storage has been reset and all limits cleared
----------------------------- Captured stdout call -----------------------------
{"timestamp": "2026-10-23T05:04:25.607376+00:00", "level": "WARNING", "module": "url_validator", "message": "[SSRF] Could not resolve hostname: blocker-rw01c.example"}
------------------------------ Captured log call -------------------------------
WARNING  app.utils.url_validator:url_validator.py:509 [SSRF] Could not resolve hostname: blocker-rw01c.example
__ test_b5_flag_off_metadata_openai_and_total_cost_equal_base_recording[rest] __
tests/test_s81_s03_llm_ledger_v2.py:1013: in test_b5_flag_off_metadata_openai_and_total_cost_equal_base_recording
    assert meta["openai"] == B5_OPENAI
E   AssertionError: assert {'calls': 11,...': 12122, ...} == {'basis': 'li...lls': 11, ...}
E     
E     Omitting 9 identical items, use -vv to show
E     Differing items:
E     {'by_model': {'gpt-4o-mini': {'calls': 8, 'prompt_tokens': 8646, 'cached_tokens': 0, 'completion_tokens': 1714, ...}, 'gpt-4o': {'calls': 3, 'prompt_tokens': 3476, 'cached_tokens': 0, 'completion_tokens': 684, ...}}} != {'by_model': {'gpt-4o': {'cached_tokens': 0, 'calls': 3, 'completion_tokens': 690, 'cost_usd': 0.015675, ...}, 'gpt-4o-mini': {'cached_tokens': 0, 'calls': 8, 'completion_tok
E     {'cost_usd': 0.017855} != {'cost_usd': 0.017992}
E     
E     Full diff:
E       {
E     -     'basis': 'list_price',
E     +     'calls': 11,
E     +     'priced_calls': 11,
E     +     'unpriced_calls': 0,
E     +     'prompt_tokens': 12122,
E     +     'cached_tokens': 0,
E     +     'completion_tokens': 2398,
E     +     'cost_usd': 0.017855,
E     +     'cost_complete': True,
E           'by_model': {
E     +         'gpt-4o-mini': {
E     +             'calls': 8,
E     +             'prompt_tokens': 8646,
E     +             'cached_tokens': 0,
E     +             'completion_tokens': 1714,
E     +             'cost_usd': 0.002325,
E     +         },
E               'gpt-4o': {
E     +             'calls': 3,
E     +             'prompt_tokens': 3476,
E                   'cached_tokens': 0,
E     -             'calls': 3,
E     -             'completion_tokens': 690,
E     ?                                   ^^
E     +             'completion_tokens': 684,
E     ?                                   ^^
E     -             'cost_usd': 0.015675,
E     ?                              --
E     +             'cost_usd': 0.01553,
E     ?                               +
E     -             'prompt_tokens': 3510,
E     -         },
E     -         'gpt-4o-mini': {
E     -             'cached_tokens': 0,
E     -             'calls': 8,
E     -             'completion_tokens': 1708,
E     -             'cost_usd': 0.002317,
E     -             'prompt_tokens': 8612,
E               },
E           },
E     +     'basis': 'list_price',
E     -     'cached_tokens': 0,
E     -     'calls': 11,
E     -     'completion_tokens': 2398,
E     -     'cost_complete': True,
E     -     'cost_usd': 0.017992,
E           'price_table_as_of': '2026-10-08',
E     -     'priced_calls': 11,
E     -     'prompt_tokens': 12122,
E     -     'unpriced_calls': 0,
E       }
---------------------------- Captured stdout setup -----------------------------
{"timestamp": "2026-10-23T05:08:26.386217+00:00", "level": "INFO", "module": "extension", "message": "Storage has been reset and all limits cleared"}
------------------------------ Captured log setup ------------------------------
INFO     slowapi:extension.py:361 Storage has been reset and all limits cleared
----------------------------- Captured stdout call -----------------------------
{"timestamp": "2026-10-23T05:08:26.393598+00:00", "level": "INFO", "module": "structured_comparison_service", "message": "[GL_FALLBACK_TRACE] query='Acme Widget' region=bh shopping_region=unknown items=0 category=electronics"}
{"timestamp": "2026-10-23T05:08:26.394169+00:00", "level": "INFO", "module": "review_service", "message": "Fetching reviews for:  Acme Widget (category: electronics)"}
{"timestamp": "2026-10-23T05:08:26.394407+00:00", "level": "INFO", "module": "image_service", "message": "[image] All tiers exhausted for 'Acme Widget' \u2014 returning None"}
{"timestamp": "2026-10-23T05:08:26.395145+00:00", "level": "INFO", "module": "structured_comparison_service", "message": "[GL_FALLBACK_TRACE] query='Globex Gadget' region=bh shopping_region=unknown items=0 category=electronics"}
{"timestamp": "2026-10-23T05:08:26.395646+00:00", "level": "INFO", "module": "review_service", "message": "Fetching reviews for:  Globex Gadget (category: electronics)"}
{"timestamp": "2026-10-23T05:08:26.395841+00:00", "level": "INFO", "module": "image_service", "message": "[image] All tiers exhausted for 'Globex Gadget' \u2014 returning None"}
{"timestamp": "2026-10-23T05:08:26.396453+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save specs for specs:ef7514bf87c4: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:26.396596+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save reviews for reviews:ef7514bf87c4: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:26.396998+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save specs for specs:96118f493371: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:26.397058+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save reviews for reviews:96118f493371: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:26.397412+00:00", "level": "INFO", "module": "unbxd_service", "message": "[UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:26.397498+00:00", "level": "INFO", "module": "noon_service", "message": "[NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:26.397726+00:00", "level": "INFO", "module": "unbxd_service", "message": "[UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:26.400902+00:00", "level": "INFO", "module": "noon_service", "message": "[NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:26.405545+00:00", "level": "WARNING", "module": "structured_comparison_service", "message": "PROS_POP_DIAGNOSTIC path=compare_from_text keys=['brand', 'model', 'winner_index', 'winner_declaration', 'verdict', 'reason', 'product_0_pros', 'product_0_cons', 'product_1_pros', 'product_1_cons', 'key_differences', 'tradeoffs'] p0_pros_present=True p1_pros_present=True p0_
------------------------------ Captured log call -------------------------------
INFO     app.services.structured_comparison_service:structured_comparison_service.py:7613 [GL_FALLBACK_TRACE] query='Acme Widget' region=bh shopping_region=unknown items=0 category=electronics
INFO     app.services.review_service:review_service.py:714 Fetching reviews for:  Acme Widget (category: electronics)
INFO     app.services.image_service:image_service.py:293 [image] All tiers exhausted for 'Acme Widget' — returning None
INFO     app.services.structured_comparison_service:structured_comparison_service.py:7613 [GL_FALLBACK_TRACE] query='Globex Gadget' region=bh shopping_region=unknown items=0 category=electronics
INFO     app.services.review_service:review_service.py:714 Fetching reviews for:  Globex Gadget (category: electronics)
INFO     app.services.image_service:image_service.py:293 [image] All tiers exhausted for 'Globex Gadget' — returning None
WARNING  app.services.product_data_service:product_data_service.py:246 Failed to save specs for specs:ef7514bf87c4: zero-network: supabase stubbed in test_cost_meter_s74
WARNING  app.services.product_data_service:product_data_service.py:409 Failed to save reviews for reviews:ef7514bf87c4: zero-network: supabase stubbed in test_cost_meter_s74
WARNING  app.services.product_data_service:product_data_service.py:246 Failed to save specs for specs:96118f493371: zero-network: supabase stubbed in test_cost_meter_s74
WARNING  app.services.product_data_service:product_data_service.py:409 Failed to save reviews for reviews:96118f493371: zero-network: supabase stubbed in test_cost_meter_s74
INFO     app.services.unbxd_service:unbxd_service.py:211 [UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
INFO     app.services.noon_service:noon_service.py:174 [NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
INFO     app.services.unbxd_service:unbxd_service.py:211 [UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
INFO     app.services.noon_service:noon_service.py:174 [NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
WARNING  app.services.structured_comparison_service:structured_comparison_service.py:4542 PROS_POP_DIAGNOSTIC path=compare_from_text keys=['brand', 'model', 'winner_index', 'winner_declaration', 'verdict', 'reason', 'product_0_pros', 'product_0_cons', 'product_1_pros', 'product_1_cons', 'key_differences', 'tradeoffs'] p0_pros_present=True p1_pros_present=True p0_pros_type=list p1_pros_type=list p0
_ test_b5_flag_off_metadata_openai_and_total_cost_equal_base_recording[stream] _
tests/test_s81_s03_llm_ledger_v2.py:1013: in test_b5_flag_off_metadata_openai_and_total_cost_equal_base_recording
    assert meta["openai"] == B5_OPENAI
E   AssertionError: assert {'calls': 11,...': 12122, ...} == {'basis': 'li...lls': 11, ...}
E     
E     Omitting 9 identical items, use -vv to show
E     Differing items:
E     {'by_model': {'gpt-4o-mini': {'calls': 8, 'prompt_tokens': 8646, 'cached_tokens': 0, 'completion_tokens': 1714, ...}, 'gpt-4o': {'calls': 3, 'prompt_tokens': 3476, 'cached_tokens': 0, 'completion_tokens': 684, ...}}} != {'by_model': {'gpt-4o': {'cached_tokens': 0, 'calls': 3, 'completion_tokens': 690, 'cost_usd': 0.015675, ...}, 'gpt-4o-mini': {'cached_tokens': 0, 'calls': 8, 'completion_tok
E     {'cost_usd': 0.017855} != {'cost_usd': 0.017992}
E     
E     Full diff:
E       {
E     -     'basis': 'list_price',
E     +     'calls': 11,
E     +     'priced_calls': 11,
E     +     'unpriced_calls': 0,
E     +     'prompt_tokens': 12122,
E     +     'cached_tokens': 0,
E     +     'completion_tokens': 2398,
E     +     'cost_usd': 0.017855,
E     +     'cost_complete': True,
E           'by_model': {
E     +         'gpt-4o-mini': {
E     +             'calls': 8,
E     +             'prompt_tokens': 8646,
E     +             'cached_tokens': 0,
E     +             'completion_tokens': 1714,
E     +             'cost_usd': 0.002325,
E     +         },
E               'gpt-4o': {
E     +             'calls': 3,
E     +             'prompt_tokens': 3476,
E                   'cached_tokens': 0,
E     -             'calls': 3,
E     -             'completion_tokens': 690,
E     ?                                   ^^
E     +             'completion_tokens': 684,
E     ?                                   ^^
E     -             'cost_usd': 0.015675,
E     ?                              --
E     +             'cost_usd': 0.01553,
E     ?                               +
E     -             'prompt_tokens': 3510,
E     -         },
E     -         'gpt-4o-mini': {
E     -             'cached_tokens': 0,
E     -             'calls': 8,
E     -             'completion_tokens': 1708,
E     -             'cost_usd': 0.002317,
E     -             'prompt_tokens': 8612,
E               },
E           },
E     +     'basis': 'list_price',
E     -     'cached_tokens': 0,
E     -     'calls': 11,
E     -     'completion_tokens': 2398,
E     -     'cost_complete': True,
E     -     'cost_usd': 0.017992,
E           'price_table_as_of': '2026-10-08',
E     -     'priced_calls': 11,
E     -     'prompt_tokens': 12122,
E     -     'unpriced_calls': 0,
E       }
---------------------------- Captured stdout setup -----------------------------
{"timestamp": "2026-10-23T05:08:26.469886+00:00", "level": "INFO", "module": "extension", "message": "Storage has been reset and all limits cleared"}
------------------------------ Captured log setup ------------------------------
INFO     slowapi:extension.py:361 Storage has been reset and all limits cleared
----------------------------- Captured stdout call -----------------------------
{"timestamp": "2026-10-23T05:08:26.477099+00:00", "level": "INFO", "module": "structured_comparison_service", "message": "[GL_FALLBACK_TRACE] query='Acme Widget' region=bh shopping_region=unknown items=0 category=electronics"}
{"timestamp": "2026-10-23T05:08:26.477855+00:00", "level": "INFO", "module": "review_service", "message": "Fetching reviews for:  Acme Widget (category: electronics)"}
{"timestamp": "2026-10-23T05:08:26.478115+00:00", "level": "INFO", "module": "image_service", "message": "[image] All tiers exhausted for 'Acme Widget' \u2014 returning None"}
{"timestamp": "2026-10-23T05:08:26.478810+00:00", "level": "INFO", "module": "structured_comparison_service", "message": "[GL_FALLBACK_TRACE] query='Globex Gadget' region=bh shopping_region=unknown items=0 category=electronics"}
{"timestamp": "2026-10-23T05:08:26.479294+00:00", "level": "INFO", "module": "review_service", "message": "Fetching reviews for:  Globex Gadget (category: electronics)"}
{"timestamp": "2026-10-23T05:08:26.479500+00:00", "level": "INFO", "module": "image_service", "message": "[image] All tiers exhausted for 'Globex Gadget' \u2014 returning None"}
{"timestamp": "2026-10-23T05:08:26.480361+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save specs for specs:ef7514bf87c4: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:26.480445+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save reviews for reviews:ef7514bf87c4: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:26.481015+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save specs for specs:96118f493371: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:26.481098+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save reviews for reviews:96118f493371: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:26.481491+00:00", "level": "INFO", "module": "unbxd_service", "message": "[UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:26.481768+00:00", "level": "INFO", "module": "noon_service", "message": "[NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:26.481833+00:00", "level": "INFO", "module": "unbxd_service", "message": "[UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:26.485282+00:00", "level": "INFO", "module": "noon_service", "message": "[NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:26.493478+00:00", "level": "WARNING", "module": "structured_comparison_service", "message": "PROS_POP_DIAGNOSTIC path=compare_from_text_streaming keys=['brand', 'model', 'winner_index', 'winner_declaration', 'verdict', 'reason', 'product_0_pros', 'product_0_cons', 'product_1_pros', 'product_1_cons', 'key_differences', 'tradeoffs'] p0_pros_present=True p1_pros_presen
------------------------------ Captured log call -------------------------------
INFO     app.services.structured_comparison_service:structured_comparison_service.py:7613 [GL_FALLBACK_TRACE] query='Acme Widget' region=bh shopping_region=unknown items=0 category=electronics
INFO     app.services.review_service:review_service.py:714 Fetching reviews for:  Acme Widget (category: electronics)
INFO     app.services.image_service:image_service.py:293 [image] All tiers exhausted for 'Acme Widget' — returning None
INFO     app.services.structured_comparison_service:structured_comparison_service.py:7613 [GL_FALLBACK_TRACE] query='Globex Gadget' region=bh shopping_region=unknown items=0 category=electronics
INFO     app.services.review_service:review_service.py:714 Fetching reviews for:  Globex Gadget (category: electronics)
INFO     app.services.image_service:image_service.py:293 [image] All tiers exhausted for 'Globex Gadget' — returning None
WARNING  app.services.product_data_service:product_data_service.py:246 Failed to save specs for specs:ef7514bf87c4: zero-network: supabase stubbed in test_cost_meter_s74
WARNING  app.services.product_data_service:product_data_service.py:409 Failed to save reviews for reviews:ef7514bf87c4: zero-network: supabase stubbed in test_cost_meter_s74
WARNING  app.services.product_data_service:product_data_service.py:246 Failed to save specs for specs:96118f493371: zero-network: supabase stubbed in test_cost_meter_s74
WARNING  app.services.product_data_service:product_data_service.py:409 Failed to save reviews for reviews:96118f493371: zero-network: supabase stubbed in test_cost_meter_s74
INFO     app.services.unbxd_service:unbxd_service.py:211 [UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
INFO     app.services.noon_service:noon_service.py:174 [NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
INFO     app.services.unbxd_service:unbxd_service.py:211 [UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
INFO     app.services.noon_service:noon_service.py:174 [NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
WARNING  app.services.structured_comparison_service:structured_comparison_service.py:5342 PROS_POP_DIAGNOSTIC path=compare_from_text_streaming keys=['brand', 'model', 'winner_index', 'winner_declaration', 'verdict', 'reason', 'product_0_pros', 'product_0_cons', 'product_1_pros', 'product_1_cons', 'key_differences', 'tradeoffs'] p0_pros_present=True p1_pros_present=True p0_pros_type=list p1_pros_ty
_________ test_i6_camera_real_compare_total_cost_and_llm_mirror_openai _________
tests/test_s81_s03_llm_ledger_v2.py:2652: in test_i6_camera_real_compare_total_cost_and_llm_mirror_openai
    assert meta["total_cost"] == 0.032127, meta["total_cost"]
E   AssertionError: 0.03199
E   assert 0.03199 == 0.032127
---------------------------- Captured stdout setup -----------------------------
{"timestamp": "2026-10-23T05:08:27.918741+00:00", "level": "INFO", "module": "extension", "message": "Storage has been reset and all limits cleared"}
------------------------------ Captured log setup ------------------------------
INFO     slowapi:extension.py:361 Storage has been reset and all limits cleared
----------------------------- Captured stdout call -----------------------------
{"timestamp": "2026-10-23T05:08:27.925926+00:00", "level": "INFO", "module": "image_routes", "message": "[IMAGE] Received 2 image(s) for identification"}
{"timestamp": "2026-10-23T05:08:27.926041+00:00", "level": "INFO", "module": "image_routes", "message": "[IMAGE]   Image 1: 66 bytes, image/jpeg"}
{"timestamp": "2026-10-23T05:08:27.926081+00:00", "level": "INFO", "module": "image_routes", "message": "[IMAGE]   Image 2: 66 bytes, image/jpeg"}
{"timestamp": "2026-10-23T05:08:27.926409+00:00", "level": "INFO", "module": "image_routes", "message": "[IMAGE] Identified 2 product(s): ['Acme Widget', 'Globex Gadget']"}
{"timestamp": "2026-10-23T05:08:27.926482+00:00", "level": "INFO", "module": "image_routes", "message": "[IMAGE] Auto-comparing: query_hash=15ab8b4511d6 length=28"}
{"timestamp": "2026-10-23T05:08:27.929704+00:00", "level": "INFO", "module": "structured_comparison_service", "message": "[GL_FALLBACK_TRACE] query='Acme Widget' region=bh shopping_region=unknown items=0 category=electronics"}
{"timestamp": "2026-10-23T05:08:27.930522+00:00", "level": "INFO", "module": "review_service", "message": "Fetching reviews for: Acme Widget (category: electronics)"}
{"timestamp": "2026-10-23T05:08:27.930799+00:00", "level": "INFO", "module": "image_service", "message": "[image] All tiers exhausted for 'Acme Widget' \u2014 returning None"}
{"timestamp": "2026-10-23T05:08:27.931504+00:00", "level": "INFO", "module": "structured_comparison_service", "message": "[GL_FALLBACK_TRACE] query='Globex Gadget' region=bh shopping_region=unknown items=0 category=electronics"}
{"timestamp": "2026-10-23T05:08:27.932014+00:00", "level": "INFO", "module": "review_service", "message": "Fetching reviews for: Globex Gadget (category: electronics)"}
{"timestamp": "2026-10-23T05:08:27.932226+00:00", "level": "INFO", "module": "image_service", "message": "[image] All tiers exhausted for 'Globex Gadget' \u2014 returning None"}
{"timestamp": "2026-10-23T05:08:27.933265+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save specs for specs:ed855c8a3b7f: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:27.933363+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save reviews for reviews:ed855c8a3b7f: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:27.933628+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save specs for specs:e434c5c8fde3: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:27.933686+00:00", "level": "WARNING", "module": "product_data_service", "message": "Failed to save reviews for reviews:e434c5c8fde3: zero-network: supabase stubbed in test_cost_meter_s74"}
{"timestamp": "2026-10-23T05:08:27.934034+00:00", "level": "INFO", "module": "unbxd_service", "message": "[UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:27.934124+00:00", "level": "INFO", "module": "noon_service", "message": "[NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:27.937799+00:00", "level": "INFO", "module": "unbxd_service", "message": "[UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:27.937895+00:00", "level": "INFO", "module": "noon_service", "message": "[NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)"}
{"timestamp": "2026-10-23T05:08:27.942736+00:00", "level": "WARNING", "module": "structured_comparison_service", "message": "PROS_POP_DIAGNOSTIC path=compare_from_text keys=['brand', 'model', 'winner_index', 'winner_declaration', 'verdict', 'reason', 'product_0_pros', 'product_0_cons', 'product_1_pros', 'product_1_cons', 'key_differences', 'tradeoffs'] p0_pros_present=True p1_pros_present=True p0_
{"timestamp": "2026-10-23T05:08:27.962121+00:00", "level": "INFO", "module": "_client", "message": "HTTP Request: POST http://testserver/api/v1/image/identify \"HTTP/1.1 200 OK\""}
------------------------------ Captured log call -------------------------------
INFO     app.api.image_routes:image_routes.py:209 [IMAGE] Received 2 image(s) for identification
INFO     app.api.image_routes:image_routes.py:271 [IMAGE]   Image 1: 66 bytes, image/jpeg
INFO     app.api.image_routes:image_routes.py:271 [IMAGE]   Image 2: 66 bytes, image/jpeg
INFO     app.api.image_routes:image_routes.py:447 [IMAGE] Identified 2 product(s): ['Acme Widget', 'Globex Gadget']
INFO     app.api.image_routes:image_routes.py:482 [IMAGE] Auto-comparing: query_hash=15ab8b4511d6 length=28
INFO     app.services.structured_comparison_service:structured_comparison_service.py:7613 [GL_FALLBACK_TRACE] query='Acme Widget' region=bh shopping_region=unknown items=0 category=electronics
INFO     app.services.review_service:review_service.py:714 Fetching reviews for: Acme Widget (category: electronics)
INFO     app.services.image_service:image_service.py:293 [image] All tiers exhausted for 'Acme Widget' — returning None
INFO     app.services.structured_comparison_service:structured_comparison_service.py:7613 [GL_FALLBACK_TRACE] query='Globex Gadget' region=bh shopping_region=unknown items=0 category=electronics
INFO     app.services.review_service:review_service.py:714 Fetching reviews for: Globex Gadget (category: electronics)
INFO     app.services.image_service:image_service.py:293 [image] All tiers exhausted for 'Globex Gadget' — returning None
WARNING  app.services.product_data_service:product_data_service.py:246 Failed to save specs for specs:ed855c8a3b7f: zero-network: supabase stubbed in test_cost_meter_s74
WARNING  app.services.product_data_service:product_data_service.py:409 Failed to save reviews for reviews:ed855c8a3b7f: zero-network: supabase stubbed in test_cost_meter_s74
WARNING  app.services.product_data_service:product_data_service.py:246 Failed to save specs for specs:e434c5c8fde3: zero-network: supabase stubbed in test_cost_meter_s74
WARNING  app.services.product_data_service:product_data_service.py:409 Failed to save reviews for reviews:e434c5c8fde3: zero-network: supabase stubbed in test_cost_meter_s74
INFO     app.services.unbxd_service:unbxd_service.py:211 [UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
INFO     app.services.noon_service:noon_service.py:174 [NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
INFO     app.services.unbxd_service:unbxd_service.py:211 [UNBXD] search error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
INFO     app.services.noon_service:noon_service.py:174 [NOON] transport error: test_cost_meter_s74: curl_cffi egress stubbed (G3)
WARNING  app.services.structured_comparison_service:structured_comparison_service.py:4542 PROS_POP_DIAGNOSTIC path=compare_from_text keys=['brand', 'model', 'winner_index', 'winner_declaration', 'verdict', 'reason', 'product_0_pros', 'product_0_cons', 'product_1_pros', 'product_1_cons', 'key_differences', 'tradeoffs'] p0_pros_present=True p1_pros_present=True p0_pros_type=list p1_pros_type=list p0
INFO     httpx2:_client.py:1085 HTTP Request: POST http://testserver/api/v1/image/identify "HTTP/1.1 200 OK"
=============================== warnings summary ===============================
app/main.py:179: 1 warning
tests/test_backend_cleanup.py: 1 warning
tests/test_retro_w1_9.py: 25 warnings
  /home/runner/work/smartcompare-backend/smartcompare-backend/app/main.py:179: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

../../../../../opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/site-packages/fastapi/applications.py:4681: 5 warnings
tests/test_backend_cleanup.py: 5 warnings
tests/test_retro_w1_9.py: 125 warnings
  /opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/site-packages/fastapi/applications.py:4681: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)  # ty: ignore[deprecated]

app/main.py:192: 1 warning
tests/test_backend_cleanup.py: 1 warning
tests/test_retro_w1_9.py: 25 warnings
  /home/runner/work/smartcompare-backend/smartcompare-backend/app/main.py:192: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

app/main.py:344: 1 warning
tests/test_backend_cleanup.py: 1 warning
tests/test_retro_w1_9.py: 25 warnings
  /home/runner/work/smartcompare-backend/smartcompare-backend/app/main.py:344: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

app/main.py:350: 1 warning
tests/test_backend_cleanup.py: 1 warning
tests/test_retro_w1_9.py: 25 warnings
  /home/runner/work/smartcompare-backend/smartcompare-backend/app/main.py:350: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("shutdown")

app/main.py:399: 1 warning
tests/test_backend_cleanup.py: 1 warning
tests/test_retro_w1_9.py: 25 warnings
  /home/runner/work/smartcompare-backend/smartcompare-backend/app/main.py:399: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("shutdown")

../../../../../opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/site-packages/supabase/_sync/client.py:309: 1 warning
tests/test_auth_interceptor.py: 4 warnings
tests/test_personalization.py: 2 warnings
tests/test_retro_w0_2.py: 4 warnings
tests/test_s78_all_timeout_cap_as_timeout.py: 1 warning
tests/test_supabase_client_reuse.py: 2 warnings
tests/test_text_error_envelope_no_raw_exception.py: 1 warning
  /opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/site-packages/supabase/_sync/client.py:309: DeprecationWarning: The 'timeout' parameter is deprecated. Please configure it in the http client instead.
    return SyncPostgrestClient(

../../../../../opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/site-packages/supabase/_sync/client.py:309: 1 warning
tests/test_auth_interceptor.py: 4 warnings
tests/test_personalization.py: 2 warnings
tests/test_retro_w0_2.py: 4 warnings
tests/test_s78_all_timeout_cap_as_timeout.py: 1 warning
tests/test_supabase_client_reuse.py: 2 warnings
tests/test_text_error_envelope_no_raw_exception.py: 1 warning
  /opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/site-packages/supabase/_sync/client.py:309: DeprecationWarning: The 'verify' parameter is deprecated. Please configure it in the http client instead.
    return SyncPostgrestClient(

tests/test_money_parser_v2.py:456
  /home/runner/work/smartcompare-backend/smartcompare-backend/tests/test_money_parser_v2.py:456: SyntaxWarning: invalid escape sequence '\d'
    "fallback regex's first \d+ run happens to be the whole integer part"),

tests/test_429_contract.py::test_429_carries_retry_after_header
  /home/runner/work/smartcompare-backend/smartcompare-backend/tests/conftest.py:226: DeprecationWarning: There is no current event loop
    loop = asyncio.get_event_loop_policy().get_event_loop()

tests/test_migration_023.py::TestMigration023SQLFile::test_adds_lifetime_invites_consumed_column
tests/test_precommit_hook.py::TestPreCommitHook::test_scenario[sh-red_jwt_refused]
tests/test_precommit_hook_phase_b.py::TestPreCommitHookPhaseB::test_scenario[sh-gl_shim_finding_with_report_refuses]
tests/test_precommit_hook_phase_b_round2.py::TestPreCommitHookPhaseBRound2::test_scenario[sh-a1_ext_diff_reveal_four_branch]
tests/test_precommit_hook_phase_b_round2.py::TestPreCommitHookPhaseBRound4::test_scenario[sh-f1_dead_awk_after_an_allowlisted_png_akia_refused]
tests/test_precommit_hook_phase_b_round2.py::TestPreCommitHookPhaseBRound5::test_scenario[sh-r5_dead_awk_sk_key_refused]
tests/test_precommit_hook_round2.py::TestPreCommitHookRound2::test_scenario[sh-d1_bulk_text_without_the_value_passes_with_no_message]
  /opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/site-packages/_pytest/fixtures.py:1313: PytestRemovedIn10Warning: Class-scoped fixture defined as instance method is deprecated.
  Instance attributes set in this fixture will NOT be visible to test methods,
  as each test gets a new instance while the fixture runs only once per class.
  Use @classmethod decorator and set attributes on cls instead.
  See https://docs.pytest.org/en/stable/deprecations.html#class-scoped-fixture-as-instance-method
    fixturefunc = resolve_fixture_function(fixturedef, request)

tests/test_preference_history_wiring.py::test_save_user_preferences_defaults_change_source_to_manual_edit
  /opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/unittest/mock.py:2217: RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
    def __init__(self, name, parent):
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/test_prescoring_showable_guard.py::test_08_red_streaming_compute_scores_receives_guarded_product_data[False-10.0]
  /opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/unittest/mock.py:655: RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
    def __getattr__(self, name):
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/test_spec_spine_d2.py::TestGetSpecsWiring::test_flag_on_spine_miss_is_byte_identical
  /opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/pathlib.py:1164: RuntimeWarning: coroutine 'save_specs' was never awaited
    def __new__(cls, *args, **kwargs):
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/test_spec_spine_d2.py::TestSeeder::test_dry_run_groups_the_corpus_fixtures_without_any_llm
  /home/runner/work/smartcompare-backend/smartcompare-backend/tests/test_spec_spine_d2.py:364: RuntimeWarning: coroutine 'save_specs' was never awaited
    import scripts.seed_spec_spine as seeder
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/test_specs_no_fabrication_guard.py::TestFlagOffIsByteIdentical::test_flag_off_still_stamps_na_and_keeps_training_values
  /opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/unittest/mock.py:2217: RuntimeWarning: coroutine 'save_specs' was never awaited
    def __init__(self, name, parent):
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
[hermeticity] sentinel checked 24821 test(s)
[netguard] blocked 690 attempt(s) from 205 node(s)
[netguard]   <collection>: 1 attempt(s) outside any test, e.g. socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_adapter_prefetch_hook.py::TestNonSupplementAdapterHook::test_adapter_miss_falls_through_to_discovery [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_adapter_prefetch_hook.py::TestAdapterCancellationNoOrphan::test_lazy_factory_contract_holds_on_adapter_miss_cancel_path [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_algolia_catalog_stores.py::test_oman_sharafdg_price_zero_returns_none [egress] curl_cffi.Session.request https://oman.sharafdg.com/
[netguard]   tests/test_algolia_tier2_wiring.py::TestAlgoliaTier2CallSite::test_genuine_algolia_hit_short_circuits [egress] curl_cffi.Session.request https://www.noon.com/_svc/catalog/api/v3/search?q=Nike+Air+Max+SC&limit=10
[netguard]   tests/test_algolia_tier2_wiring.py::TestAlgoliaTier2CallSite::test_algolia_miss_falls_through [egress] curl_cffi.Session.request https://www.footlocker.com.bh/configs.json
[netguard]   tests/test_auth_interceptor.py::test_login_user_success [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_auth_interceptor.py::test_refresh_session_success [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_auth_interceptor.py::test_refresh_session_includes_user_data [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_auth_routes_invite_fingerprint.py::test_register_invite_code_valid_format_accepted [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_auth_routes_invite_fingerprint.py::test_register_resolves_code_then_links_invite [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_bh_gcc_cascade_wiring.py::TestNewAdapterCascadeWiring::test_woo_genuine_hit_short_circuits [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_bh_gcc_cascade_wiring.py::TestNewAdapterCascadeWiring::test_converted_adapter_hit_does_NOT_short_circuit [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_bh_gcc_cascade_wiring.py::TestNewAdapterCascadeWiring::test_new_adapter_miss_falls_through [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_cascade_parallel.py::test_discovery_prefetch_starts_concurrently_with_shopping [egress] curl_cffi.Session.request https://search.unbxd.io/72883ca2a4420a7c7ca07cefda404539/ss-unbxd-auk-extra-bahrain-en-prod11541714990628/search?q=Apple+iPhone+15&rows=20
[netguard]   tests/test_cascade_parallel.py::test_prefetch_SKIPPED_when_algolia_sources_exist [egress] curl_cffi.Session.request https://www.noon.com/_svc/catalog/api/v3/search?q=Tom+Ford+Oud+Wood&limit=10
[netguard]   tests/test_cascade_parallel.py::test_prefetch_FIRES_for_shopify_category_with_lulu_discovery[grocery] [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_cascade_parallel.py::test_prefetch_FIRES_for_shopify_category_with_lulu_discovery[electronics] [egress] curl_cffi.Session.request https://sonyworld.bh/products.json?limit=250
[netguard]   tests/test_category_selection.py::TestAPIParameter::test_api_accepts_selected_category_param [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_category_selection.py::TestAPIParameter::test_api_accepts_null_selected_category [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_category_selection.py::TestAPIParameter::test_api_passes_selected_category_to_service [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_category_selection.py::TestAPIParameter::test_api_accepts_invalid_category_without_422 [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_category_selection.py::TestCategorySwitchingResponse::test_category_switching_response_fields [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_category_selection.py::TestCategorySwitchingResponse::test_no_switch_response_fields [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_category_selection.py::TestCategorySwitchingResponse::test_each_new_category_in_response [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_cron_reengagement.py::TestCronPagination::test_dispatch_called_when_payload_returned [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_explicit_pair_integration_mocked.py::test_explicit_pair_scoring_breakdown_is_fragrance_dims_e2e [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_explicit_pair_integration_mocked.py::test_explicit_pair_response_category_used_is_fragrances_e2e [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_explicit_pair_integration_mocked.py::test_explicit_pair_category_switched_surfaces_on_response_e2e [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_fan_out_integration.py::TestFanOutHighestRankWinner::test_fan_out_returns_highest_rank_winner [egress] curl_cffi.Session.request https://www.noon.com/_svc/catalog/api/v3/search?q=Louis+Vuitton+Neverfull+MM&limit=10
[netguard]   tests/test_fan_out_integration.py::TestPendingScrapersCancelledOnConfirmation::test_pending_scrapers_cancelled_on_confirmation [egress] curl_cffi.Session.request https://02X7U6O3SI-dsn.algolia.net/1/indexes/enterprise_magento_en_bh_products/query
[netguard]   tests/test_fan_out_integration.py::TestCounterfeitDomainFiltered::test_counterfeit_domain_filtered_even_when_first [egress] curl_cffi.Session.request https://02X7U6O3SI-dsn.algolia.net/1/indexes/enterprise_magento_en_bh_products/query
[netguard]   tests/test_fan_out_integration.py::TestScrapingModeSoftSkipsFirecrawl::test_scrapingmode_soft_skips_firecrawl_for_non_luxury [egress] curl_cffi.Session.request https://www.noon.com/_svc/catalog/api/v3/search?q=Louis+Vuitton+Neverfull+MM&limit=10
[netguard]   tests/test_fan_out_integration.py::TestFallthroughToTier2WhenAllScrapersFail::test_fan_out_falls_through_to_tier2_when_all_scrapers_fail [egress] curl_cffi.Session.request https://www.noon.com/_svc/catalog/api/v3/search?q=Louis+Vuitton+Neverfull+MM&limit=10
[netguard]   tests/test_flush_live_price_key.py::test_flag_off_body_is_the_legacy_shape_exactly [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_flush_live_price_key.py::test_flag_on_deletes_the_size_aware_key_for_an_identity_query [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_flush_live_price_key.py::test_price_key_builder_puts_the_live_key_first_and_dedupes [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_flush_live_price_key.py::test_price_key_builder_falls_back_to_the_request_identity [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_flush_live_price_key.py::test_flag_on_category_chip_targets_the_key_the_live_path_keyed_under [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_flush_live_price_key.py::test_flag_on_a_misguessed_chip_still_deletes_the_live_key [egress] socket.getaddrinfo api.openai.com:443
[netguard]   ... 165 more node(s) in the report
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.12.15-final-0 _______________

Name                                            Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------------
app/__init__.py                                     0      0   100%

# short test summary
=========================== short test summary info ============================
XFAIL tests/test_correctness_coverage_sweep_fixes.py::test_deferred_redos_cap_truncation - the 512-char ReDoS cap drops a trailing storage axis; reachability is near-zero (real titles < 200 chars)
XFAIL tests/test_kpi_truth_modernization.py::test_switch2_accepts_extra_console_title - matcher over-rejection (Wave B): 'Light' in extra.com's colourway 'Light Blue and Light Red' reads as a variant qualifier (Switch-Lite class) instead of a colour modifier — bisect-proven: 'Nintendo Switch 2 Blue'
XFAIL tests/test_prompt_truth.py::test_shipped_prompt_does_not_license_training_data - PO-PROMPTS-11: the shipped CODE default of ENABLE_SPECS_NO_FABRICATION is OFF, so the fabricating specs prefix ships. NOT permanent (ruling R6): the planned end state is to retire the flag once the Railway flip is
XFAIL tests/test_scoring_rubric_truth.py::test_spec_dim_can_separate_two_fashion_products - PO-RUBRIC-03 limit (ruling R4 / open question 2): fashion/other have no numeric spec discriminator, so two different products tie on craft/function under any W4-6a flag state; separation needs a non-numeric m
XFAIL tests/test_value_math.py::test_value_formula_coefficients_match_spec[price-coeffs0] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_formula_coefficients_match_spec[quality-coeffs1] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_formula_coefficients_match_spec[durability-coeffs2] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_formula_coefficients_match_spec[latest_features-coeffs3] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_formula_coefficients_match_spec[brand_reputation-coeffs4] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_formula_coefficients_match_spec[eco_friendly-coeffs5] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_formula_coefficients_match_spec[ease_of_use-coeffs6] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_formula_coefficients_match_spec[_default-coeffs7] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_formula_first_match_wins_quality - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_formula_first_match_wins_price_overrides_quality - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_formula_default_when_no_priorities - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_delta_text_price_percentage_format - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_delta_text_rating_stars_format - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_delta_text_value_with_priority_match_copy - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_delta_text_value_no_priority_match_copy - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_value_match[mid-mid-in_range] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_value_match[mid-premium-above_range] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_value_match[mid-budget-below_range] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_value_match[mid-luxury-above_range] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_value_match[mid-top_tier-above_range] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_value_match[luxury-budget-below_range] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_value_match[budget-top_tier-above_range] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_value_match[top_tier-top_tier-in_range] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_match_caption_in_range_is_silent - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_match_caption_one_tier_above - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_match_caption_one_tier_below - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_value_match_caption_two_plus_tier_above_appends_tradeoff - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_budget_mismatch[budget-product_tiers0-above] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_budget_mismatch[budget-product_tiers1-above] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_budget_mismatch[luxury-product_tiers2-below] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_budget_mismatch[top_tier-product_tiers3-below] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_budget_mismatch[mid-product_tiers4-None] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_budget_mismatch[mid-product_tiers5-None] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_classify_budget_mismatch[premium-product_tiers6-None] - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
XFAIL tests/test_value_math.py::test_budget_mismatch_passes_to_preferences_prompt - RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet — see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md
= 4 failed, 24745 passed, 94 skipped, 124 deselected, 39 xfailed, 314 warnings in 723.26s (0:12:03) =
##[error]Process completed with exit code 1.
