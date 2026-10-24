# S81-06 ANTHROPIC-ROUTER: GREEN report (agent GREEN, Opus 5.5)

Unit S81-06 (lane A). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s06, branch feature/s81-s06-anthropic-router, HEAD ceecb04a1a4c9e58c62eebe07705148a979eb31e (one commit on ea3aef15, through the pre-commit hook; not pushed, no rebase, no PR).
Notes folder: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/S81-06_green/ (notes.md, every log, comm_head/, mut/, files_changed.json, the runner copy pyt_s06.py). Byte copies before edit: .../scratchpad/S81-06_green_before/ (SHA256SUMS.txt).

## RED files
tests/test_s81_s06_anthropic_router.py sha256 8e1e03e66eac67ffc0849a0b01094c835467d0d11127834df2b7aba368bae84b at the start and at the end (unchanged, committed). The gate-added rows (GC-1/2/3/4/5) live in the NEW file tests/test_s81_s06_router_gate_rows.py so the frozen sha holds.

## Files (sha256 after; before from the byte copies)
- .github/black-clean-paths.txt +2 -0 before 45086ffd820ec3f5bd64a470df00fa42eed889d0ce829241a9556d59bb6336f9 after f7addd38f01e4a6245606be53f59608b5679f9e2d61f19a31ba3599b79b0f4a8
- CLAUDE.md +5 -2 before 783e7571ecfa163ae2c7a14f41d8213e4fcdfd2fdf75527ca3938fd354a6a2ac after ed516c88030f5963e2bb27cfe5cd33040f7433547d539ba90af966e0d5af219f
- app/api/image_routes.py +20 -2 before 5f1185057046467a36083f89a12ac565a3d2e7ecb4c71596bda58dd29ac521a4 after 9795c3598672d4f19a4c91b3f7fefb6b639c4273256abb0065e5709f86ddbb0c
- app/api/url_routes.py +12 -0 before 31f6f22a06b9222439d96494ec2f93a131c9d1b8d3666d930651dba9120190ce after 739eb37bf1e6e60a8db74255ec6a508448d55b7b01d3223fed258a3d9ee84f01
- app/legal/processors.json +13 -0 before 4052d4f73905b7c2cfbb48708b5f79254985dce8777daefd7b93e0e22ff5445e after 79b52fc61ebaad69dc4aeba871882285f4a19217aa1ca410819ad3400e55904b
- app/main.py +9 -0 before c3e37c5d70768b6988d68a557f0b473327dca97888e31dd7ee89396282456636 after 646a7c90c3d696038f8c0f86d2d8adadd0403d284cbeb7c473ede93bdaa36485
- app/services/cache_service.py +7 -1 before 54257ced533069f60d9a7c7cff9cdf346a12c40fe0734508f1d6fedd2b023024 after b86bd2e5a70af5385f03f36feede61ea40d91e7dee4da367996a285473feccf8
- app/services/content_safety_service.py +7 -0 before 7bd50a6c74523742de620cd4496426a171b60c422ccba4e96b34085a2555a81d after a7cfa77dcce88288d3653aaeb2b2d0c37a1d999fb7673adf6ea52ca438c5204a
- app/services/extraction_service.py +27 -11 before 4cbb6187bb14d2777d95f098c8d618977ad2e029f9d9888140a5a19cf3f2af0e after f10f4b7fc7dd6344f71fded105496bc89ce2f34ed276d3fb31c10e3c16553489
- app/services/image_service.py +2 -1 before 31d67f167f13517bdfdcf8dae2b649f0a66e46b6f3747ebcefe2a80fde0707f4 after 708354eb3e966e88c7e1b41ffc2e457a1217ae3a88d477b6cc4308a867bfe299
- app/services/llm_router.py +1205 -0 before (new) after 9eba85a373c9f93795e4d853a44413b0b0591202df5a26895b1b760d0e864fe9
- app/services/model_config.py +59 -1 before 550ecf8d89e728dbd4815997a44fa85d2b2409ae757eb5754469f52f7d7804d1 after c5c3a2f3301f98ed39cd2892925899b7a5a5a6f532de48c385f173e81d6eb302
- app/services/openai_service.py +22 -9 before 395a0bcf32c8705f1cd772bbf8e360f8396118116b582f4c084202208e8173f1 after 55de67ee14ec32ff22f5f6c20f10f361bfc1c9c8a76a1c9ad499d755ea953c8a
- app/services/sentry_service.py +15 -0 before a49bc68385afcd6cf76aa43af863e57e8e50e5f226631bb62c2d5a7ef69c569a after 5aed8ebf139b9f26c19a3e3cbaadf6d86f7fa5d07cb2ce3827da0a70fb004200
- app/services/structured_comparison_service.py +50 -2 before 43871533f653463bc56997f9d162d0cca09aeaa1b5a0136791bb42a3d4d8a6dd after 544ab2168fa2ad6ac9f6793a379498b63da7c371450b292e8c6111e784c18b14
- app/services/url_extraction_service.py +42 -5 before edc9a2449566b821954183715d0bdd2faabef0bf3954ef6bad5875b0f1a990ee after 0a5243074a762847a75f8468c0d3928c825d5b8188f30422665b87d820a69aa6
- app/services/verdict_critique_service.py +2 -1 before f9ceaf49e9f85942853ed5bbc9b85ad6adfda4f72621c2c37b3257d5b35d9026 after 4b19e0cc768cac1b2197f52236d4bdb057ae44bf4a66f80bf15075201df54806
- requirements.in +4 -0 before 369326873caf7400651e521e76d3f912d0f00d497c2a0d057b0f02fb66b68cf2 after b331025b585b9d624cc86788ba61c5ac2b59087af1557454c72cbd7ea7e59f5a
- scripts/fill_in_legal.py +2 -0 before 9cc0aa74b593031e53a9ae719213852dd31b8dfaa5beda6e2a28eb039a104f00 after 81696741f34df81c92044fbd24daa9308d61d25fda997ad47301eaa92afb7019
- tests/_env_safety.py +6 -0 before cba3121f4e47b9b19a124783af4ae11a891224292c6c005c5d9573a15ea069cd after 7554737c7a159e82c7ac89064cf95dede23b119f8e896e79b3c6f2fee7e64b05
- tests/fixtures/legal_fill_in_u8.json +2 -1 before df046708fa2bbc539c55fba50f7e08edcb7a1428ab166059bb209b1e48d9381c after f4b8b05601582e526e0b78cb8abba501e4c9ca3a2915fccaba57b5edb0a9a96b
- tests/fixtures/legal_s78.json +11 -0 before 0b31bab98b165e0ccc2bb7a0b0f8021ebdc6979cb1f3aadd04d583e635ddcbe4 after 61a68c6ec05f8fa8efded8259e4b3ae22b3e17892af96f356943241a177c5f92
- tests/test_legal_docs_u8.py +9 -1 before d86bf011702996387f6926538c5aac09c4fe095e0ad4474c37beb34799fc7a7c after 9d77e30d497a56480d1554f41229c2e54e7d131054d9bf4b8248d32b8ec1e7f6
- tests/test_model_config.py +6 -2 before 67f24d9cb199e71d7157c4d5d077da8bf4b482d61523a56e08c7fa10e43b0fee after cc9bdca1023b1ad377aa9e8b2d80c74d7c47fb4aa88e8f24ce75aab827acf706
- tests/test_model_config_enforced.py +14 -6 before 063c46bb115beb075151934873bd7dc0e6dd9cb0257e5b49ce9432dd8a42ac23 after 60892ad653423573c9c02751a34f3334567fc0fa99ec026cb791156878301b7d
- tests/test_prompt_fence.py +4 -0 before 622947e2a2b2ebc71436238cc0b5c62f44c83f255e4a1e2a1411090f649e56e9 after a6510be92f73417a4901b6ab8eaf156d9ef596779ed21d18bc5784d4ed61a265
- tests/test_retro_w2_1.py +5 -1 before ba125e514242fa81a1268946435a1a380e0f03ac21753a14c33b50ea254a33de after 0b9134585c14969ab8c6f78400070434d3ff60e5a0e24776c50f3d7a5e08a594
- tests/test_s71_u13_compare_auth_required.py +4 -0 before d8503cdcb51b05a9cd5e382cd2a39d2a8ace2b5584b9fcd27cb7960639943a0e after ee219f2ed7e5576e306754595effa8cfeb34005062ba16196c109ae7d9dfd992
- tests/test_s75_fanout_identity.py +5 -1 before 1b3418115b08c7a3bd85f54f5bf929cc5248398054ae97261a96e22b65593bf6 after cd11581803bb8ac7045d56a5b004003b0263a0144be69bec3607dc4bfe8e9c42
- tests/test_s81_s05_request_context.py +32 -0 before f5ce0239db2e6563ff924763ab897efa491b3824fa71e67db1489f6e59ead882 after 71cdb79401ef03723282e259dbb259282b36d167692edf984f82d50830172d6f
- tests/test_s81_s06_anthropic_router.py +2751 -0 before (new) after 8e1e03e66eac67ffc0849a0b01094c835467d0d11127834df2b7aba368bae84b
- tests/test_s81_s06_router_gate_rows.py +509 -0 before (new) after be09d4ec0ecbdfcd56aa038da11a933c77bad2819d50672c504441bf3cd6ee51
- tests/test_sentry_channels_u8d.py +10 -1 before af227b0c20d35370c04b634bfb779eb19592557b0b1be9f2b2578982d4778084 after a025dcc3b32362792075fea4d7b6f1814dbf14a3cb56c1784084369ea282f5b0
- tests/test_u3c_store_false_pin.py +56 -3 before b14bbdc75ecc36ba30b05109785dd1537b39663bfc5ad442e84d2159d5224ae3 after 63857353a6d250036a70be97b22d014d084a4436bdd24fd6188b16375e6b739e
- tests/w4_11_prompt_digest_recorder.py +5 -1 before a9d59a2a4bd6b3c278f95e77421852dd7cb35d2da95f9ca09ed18cd8764a5c3d after 5511be296870238674cd10774c6a7020e29e32a1f80859e2423ef9e635273e35

## Runs
- red_at_base: `[pyt] tag=s06g-red-at-base start=2026-10-24 10:00:21 end=2026-10-24 10:05:47 elapsed=326s bound=600s status=FAIL rc=1`
- unit_1: `[pyt] tag=s06g-unit-1 start=2026-10-24 11:01:27 end=2026-10-24 11:04:25 elapsed=178s bound=600s status=OK rc=0`
- gcrows_1: `[pyt] tag=s06g-gcrows-1 start=2026-10-24 11:22:51 end=2026-10-24 11:22:56 elapsed=5s bound=600s status=OK rc=0`
- pins_1: `[pyt] tag=s06g-pins-1 start=2026-10-24 11:23:33 end=2026-10-24 11:25:00 elapsed=87s bound=1200s status=OK rc=0`
- readers_1: `[pyt] tag=s06g-readers-1 start=2026-10-24 12:02:39 end=2026-10-24 12:03:24 elapsed=45s bound=600s status=OK rc=0`
- unit_final: `[pyt] tag=s06g-unit-final start=2026-10-24 12:04:06 end=2026-10-24 12:04:29 elapsed=23s bound=600s status=OK rc=0`
- ci_order: `[pyt] tag=s06g-ci-order start=2026-10-24 12:13:41 end=2026-10-24 12:16:48 elapsed=187s bound=1200s status=OK rc=0`
- `[pyt] tag=s06g-comm-head-00 start=2026-10-24 11:28:18 end=2026-10-24 11:28:55 elapsed=37s bound=1200s status=OK rc=0`: 821 passed, 1 deselected; `[netguard] blocked 24 attempt(s) from 7 node(s)`
- `[pyt] tag=s06g-comm-head-01 start=2026-10-24 11:28:56 end=2026-10-24 11:29:52 elapsed=56s bound=1200s status=OK rc=0`: 597 passed, 31 deselected; `[netguard] blocked 30 attempt(s) from 7 node(s)`
- `[pyt] tag=s06g-comm-head-02 start=2026-10-24 11:29:54 end=2026-10-24 11:31:39 elapsed=106s bound=1200s status=FAIL rc=1`: 1 failed, 1604 passed, 1 skipped, 7 deselected; `[netguard] blocked 14 attempt(s) from 9 node(s)`
- `[pyt] tag=s06g-comm-head-03 start=2026-10-24 11:31:40 end=2026-10-24 11:32:10 elapsed=30s bound=1200s status=OK rc=0`: 425 passed, 9 deselected; `[netguard] blocked 2 attempt(s) from 1 node(s)`
- `[pyt] tag=s06g-comm-head-04 start=2026-10-24 11:32:11 end=2026-10-24 11:32:48 elapsed=37s bound=1200s status=OK rc=0`: 1464 passed, 2 skipped; `[netguard] blocked 27 attempt(s) from 9 node(s)`
- `[pyt] tag=s06g-comm-head-05 start=2026-10-24 11:32:52 end=2026-10-24 11:37:37 elapsed=285s bound=1200s status=OK rc=0`: 1947 passed, 1 skipped; `[netguard] blocked 63 attempt(s) from 40 node(s)`
- `[pyt] tag=s06g-comm-head-06 start=2026-10-24 11:40:20 end=2026-10-24 11:40:52 elapsed=32s bound=1200s status=OK rc=0`: 525 passed, 14 deselected; `[netguard] blocked 13 attempt(s) from 2 node(s)`
- `[pyt] tag=s06g-comm-head-07 start=2026-10-24 11:40:53 end=2026-10-24 11:41:30 elapsed=37s bound=1200s status=OK rc=0`: 398 passed; `[netguard] blocked 1 attempt(s) from 1 node(s)`
- `[pyt] tag=s06g-comm-head-08 start=2026-10-24 11:41:31 end=2026-10-24 11:41:57 elapsed=26s bound=1200s status=OK rc=0`: 525 passed, 1 skipped, 10 deselected; `[netguard] blocked 0 attempt(s) from 0 node(s)`
- `[pyt] tag=s06g-comm-head-09 start=2026-10-24 11:41:58 end=2026-10-24 11:42:52 elapsed=53s bound=1200s status=FAIL rc=1`: 2 failed, 3639 passed, 22 skipped; `[netguard] blocked 130 attempt(s) from 9 node(s)`
- `[pyt] tag=s06g-comm-head-10 start=2026-10-24 11:42:53 end=2026-10-24 11:44:08 elapsed=75s bound=1200s status=OK rc=0`: 636 passed, 3 skipped, 15 deselected; `[netguard] blocked 39 attempt(s) from 15 node(s)`
- `[pyt] tag=s06g-comm-head-11 start=2026-10-24 11:44:13 end=2026-10-24 11:46:22 elapsed=129s bound=1200s status=FAIL rc=1`: 793 passed, 5 skipped, 1 deselected, 1 xfailed, 2 errors; `[netguard] blocked 10 attempt(s) from 2 node(s)`
- `[pyt] tag=s06g-comm-head-12 start=2026-10-24 11:46:23 end=2026-10-24 11:48:19 elapsed=116s bound=1200s status=OK rc=0`: 884 passed; `[netguard] blocked 20 attempt(s) from 1 node(s)`
- `[pyt] tag=s06g-comm-head-13 start=2026-10-24 11:48:20 end=2026-10-24 11:52:05 elapsed=225s bound=1200s status=OK rc=0`: 3273 passed, 1 xfailed; `[netguard] blocked 29 attempt(s) from 5 node(s)`
- `[pyt] tag=s06g-comm-head-14 start=2026-10-24 11:54:38 end=2026-10-24 11:56:40 elapsed=121s bound=1200s status=OK rc=0`: 1097 passed; `[netguard] blocked 18 attempt(s) from 8 node(s)`
- `[pyt] tag=s06g-comm-head-15 start=2026-10-24 11:56:41 end=2026-10-24 11:58:08 elapsed=87s bound=1200s status=OK rc=0`: 520 passed, 8 skipped, 10 deselected; `[netguard] blocked 101 attempt(s) from 38 node(s)`
- `[pyt] tag=s06g-comm-head-16 start=2026-10-24 11:58:11 end=2026-10-24 11:59:57 elapsed=106s bound=1200s status=OK rc=0`: 548 passed, 8 deselected, 35 xfailed; `[netguard] blocked 84 attempt(s) from 29 node(s)`
- `[pyt] tag=s06g-comm-head-17 start=2026-10-24 12:00:44 end=2026-10-24 12:01:23 elapsed=40s bound=1200s status=OK rc=0`: 1183 passed, 9 skipped; `[netguard] blocked 8 attempt(s) from 8 node(s)`
- `[pyt] tag=s06g-comm-head-18 start=2026-10-24 12:01:24 end=2026-10-24 12:01:39 elapsed=15s bound=1200s status=OK rc=0`: 198 passed, 1 skipped; `[netguard] blocked 12 attempt(s) from 4 node(s)`
- mutants: MG1-MG8 KILLED (s06g-mut-MG1..MG8, each status=FAIL rc=1 on an AssertionError, restores sha-verified, lock created and removed); M34 KILLED (s06g-mut-M34, the real SDK).

## Deviations
- D1 pyt.py hard-codes VENV_PY=.venv-qaren and documents no interpreter option: a copy pyt_s06.py in the notes folder with VENV_PY=.venv-s81-06 (HERE = the shared harness dir, so the ledger and netguard plugin dir are the shared ones) ran every pytest; the shared pyt.py was not edited.
- D2 FIRST gate: 229 failed / 112 passed, not 230 / 111: the only node that moved vs the RED junit is test_r25b_real_spend_breaker_present (F->P), a presence-only row satisfied by the S81-04 merge the gate itself names as the precondition; all 229 failures AssertionError-only. Read as the gate's 'R25b must be satisfiable' and proceeded; flagged for the orchestrator.
- D3 GC-1 moderation: the OpenAI moderations endpoint is not behind the W1-3 breaker and fails open, so moderation adds a breaker to the AND only when it routes to Claude; read this way the frozen R33 cell 4 (text+verdict on Claude, openai OPEN -> no short-circuit) stays green; the critic adds its provider when ENABLE_SELF_CRITIQUE is ON.
- D4 GC-3 cache axis: no verdict cache exists in app/ and get_comparison_cache_key has no production caller; the axis is added there (lazy router import in cache_service) and pinned both ways (G02a/G02b).
- D5 GC-6: all eleven format-None JSON sites took option (b) (reasons in the PR body table).
- D6 GREEN-added rows in a new file tests/test_s81_s06_router_gate_rows.py (33 nodes) instead of appending to the frozen RED file.
- D7 extra URL mappings beyond the gate text: compare_from_urls maps an extraction LLMUnavailableError and a re-raised verdict LLMUnavailableError to the coded LLM_UNAVAILABLE result under any role ON (else R-S06-2's re-raise would 500 the URL path); the REST impl's generic except maps it too (else the impl swallowed it into INTERNAL_ERROR); flags OFF both branches are unreachable.
- D8 the eighth fill-in flag needed tests/fixtures/legal_fill_in_u8.json flags.ENABLE_ANTHROPIC_TEXT = "off" (recorded by an agent: the name is new, so unset in production by construction; the fixture comment says the orchestrator records flags: confirm).
- D9 E9 import shape: the router reads only consent_version / header_state (header_state with the str name 'x-ai-consent-version', S81-05 GC-1) so the attribute set is exactly {consent_version, header_state}; the P1 string-constant check is skipped for llm_router (its import shape is pinned instead).
- D10 black-clean-paths lists llm_router.py and the gate-rows file, not the frozen RED file (not black-formatted; editing it is forbidden).
- D11 the commit trailer names Opus 5.5 (the model that committed; the computed template said Fable 5.1, the common brief says the committing agent's own model).
- D12 GC-9 base record: the full 461-file set was run at HEAD only; the base record at ea3aef15 was NOT re-run (the 2 h budget); the HEAD failure set equals the gate's accepted baselines plus one black allowlist failure caused and fixed in this unit.
- D13 SDK surface re-measured on 1.12.1 (R0-8 rule): new params cache_control, container, diagnostics, inference_geo, service_tier, user_profile_id, workspace_id; new ServiceUnavailableError (503) / DeadlineExceededError (504) classify transient by status; explicit api_key disables env credential discovery; ANTHROPIC_CUSTOM_HEADERS is still env-read (stated limit 7).

## Open questions
- Q1 Accept D2 (229/112 with R25b green at base) as the GC-8 first gate?
- Q2 Accept D3 (OpenAI moderation not in the preflight AND) or rule that moderation always adds openai (would turn frozen R33 cell 4 red)?
- Q3 Should the orchestrator re-record the fill-in flag value (D8) or keep the agent's 'off'?
- Q4 Run the GC-9 base record at ea3aef15 (D12) before the adversaries, or accept HEAD-vs-accepted-baselines?

## NOT MEASURED
- The full comm base record at ea3aef15 (D12). The adversaries (not this agent's step). Live provider behaviour (no network).

## git status --short at the end
(empty: the commit holds every changed file; nothing untracked in the worktree)
