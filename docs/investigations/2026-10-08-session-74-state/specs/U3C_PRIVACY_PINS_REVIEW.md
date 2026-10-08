# U3c privacy pins - adversarial spec review (session 74, 2026-10-08)

Spec: s74-state/specs/U3C_PRIVACY_PINS_SPEC.md sha256 6771fef86551f5b97e67ca3c15353202707227e86d34f7c1796c7e13fe215283
(re-hashed unchanged at 15:22). Drafts unchanged: store 29f3931972c3..., referral e19ef4376194..., GREEN patch
78d73a746bcc.... Base main dfbda511 (sc-s71-t0b clean, HEAD dfbda511, untouched; read-only).
NOTES = scratchpad/u3c/review (notes.md, t02_bypass_probe.py/.out, t01_ext_probe.py, mutate_rev.py, gl*_scan.out,
rev_*.log, mA..mD.log). Rules file read: scratchpad/harness/s74-common.txt (brief path does not exist).
Scratch: one detached worktree NOTES/wt at dfbda511, GREEN patch applied there, removed with
`git worktree remove --force` at 15:20.

## Verdict
REVISE BEFORE RED. The design (hard override at the one chokepoint, 2 script lines, display_name-or-nameless push)
is correct and every factual claim I re-checked holds. No blocking design defect. Five major fixes: one is
commit-blocking (gitleaks), two are pin-strength gaps with measured surviving mutants or bypass shapes, two are
policy-truth framing under OA2. All fixes are small and stay inside the unit.

## Measurements (my runs)
- RED at base (scratch wt, source hunks reverted, both existing-test edits kept):
  [pyt] tag=u3c-rev-red-base elapsed=9s bound=600s status=FAIL rc=1 -> 34 failed, 60 passed. Every failure is for the
  stated reason (no store key / KeyError 'store' / 'sara.q' / 'A friend' == '' / '   ' == '' / select lacks
  display_name / body opens 'Your friend' / 12 mce sites lack store / refsvc 'sara').
- GREEN (scratch, spec patch + drafts + 3 extra neighbour files):
  [pyt] tag=u3c-rev-green elapsed=14s bound=1200s status=OK rc=0 -> 199 passed, 1 skipped.
- Mutants (byte copy, restore sha OK each):
  - extra_body={"store": True} on the flag-ON dispatch: [pyt] tag=u3c-rev-mA status=FAIL rc=1 -> killed ONLY by
    T09[flag_on] (T01/T05/T06 pass it).
  - assignment moved after the `if`: [pyt] tag=u3c-rev-mB status=FAIL rc=1 -> killed by T01, T05[off], T06[off], T07,
    T09[off].
  - `if str(kwargs.get("model","")).startswith("gpt-5"): kwargs.pop("store")` after the assignment:
    [pyt] tag=u3c-rev-mC elapsed=10s status=OK rc=0 -> SURVIVES (283 passed: store pin + test_model_config_enforced +
    test_arabic_verdict_output_w414 + test_openai_breaker).
  - Arabic body `{bonus}` -> `{bonus * 2}` (push_service.py:186): [pyt] tag=u3c-rev-mD elapsed=8s status=OK rc=0 ->
    SURVIVES (99 passed, 1 skipped: referral pin + test_loop2_gift_copy + test_push_service + test_referral_service +
    test_referral_loop2 + test_referral_e2e).
- gitleaks 8.30.1 `dir` with the repo .gitleaks.toml over the two drafts at tests/ paths: rc=1, 1 finding
  (generic-api-key, store draft line 248, entropy 3.506891). Same file with api_key="test-key": rc=0. Referral draft
  and GREEN patch: clean.
- Full-config ruff on both drafts: "All checks passed!". No touched file is on .github/black-clean-paths.txt.
- Drafts and spec: 0 non-ASCII bytes, 0 CR, LF-terminated. All 8 touched files are CRLF in the working copy (CR count
  = line count). GREEN numstat in scratch matches spec section 6 exactly.

## Findings

### F1 major (commit-blocking) - the RED commit is refused by gitleaks
Evidence: draft tests/test_u3c_store_false_pin.py:248 `api_key = "u3c-" + "placeholder" (the draft wrote it as ONE literal)` matches gitleaks generic-api-key
(entropy 3.5069 > 3.5). Measured rc=1 (NOTES/gl2_scan.out); "test-key" rc=0 (NOTES/gl3_scan.out). The hook runs gitleaks
over staged changes (.githooks/pre-commit:443-480) and CI secret-scan uses the same config.
Fix: `api_key="test-key"` (any value under 10 characters, or built by concatenation). RED re-runs gitleaks `dir` with
the repo config on both new files before staging.

### F2 major - T02 misses most non-canonical dispatch shapes, including the Responses API path the repo already names
Evidence (NOTES/t02_bypass_probe.out, draft helpers copied verbatim): draft T02 flags 3/10 shapes; it MISSES a bound-method
alias (`create = client.chat.completions.create`), `getattr(..., "create")`, `functools.partial(...create)`,
`client.responses.parse`, `client.responses.with_raw_response.create`, `client.post("/chat/completions", ...)`,
`client.batches.create`. model_config.py:34 says gpt-5-pro is Responses-API only; the Responses API stores by default,
so adopting it via `.responses.parse` (SDK has it: resources/responses/responses.py:1302) silently breaks the promise.
A stricter rule (any ast.Attribute named chat/responses/batches/completions/beta/realtime/conversations outside the
guarded_llm_create body; any non-docstring str constant starting with "/chat/completions", "/responses", "/batches",
"/completions"; getattr(x, "create"|"completions"|"chat"|"responses")) has 0 hits in app/ at dfbda511 and flags 10/10.
Fix: replace FORBIDDEN_TAILS logic in T02 with the attribute rule (GUARD, green at main).

### F3 major - a conditional pop inside the chokepoint survives every test
Evidence: mutant mC above (283 passed). T01 counts only Subscript stores/dels; runtime tests use models "m" and
"gpt-4o-mini"; test_model_config_enforced M2 (gpt-5 ids) does not look at store. A model-specific strip is a realistic
hotfix shape here (model_config already strips rejected kwargs per model, :107-139).
Fix: extend T01: inside guarded_llm_create no call `kwargs.<attr>(...)` except `get`, no Store/Del of the Name
`kwargs`, and each dispatch call has no positional args and exactly one keyword (`**kwargs`). Measured with
NOTES/t01_ext_probe.py: 0 offenders at GREEN; flags mC (kwargs.pop) and mA (extra keyword on the dispatch). Optional:
add `assert kw["store"] is False` to the gpt-5 M2 test in test_model_config_enforced (third existing-test edit; R6).

### F4 major - the unit's own text states a retention promise OA2 makes false
Evidence: GREEN patch docstring (api_budget_service hunk) "The privacy policy says OpenAI keeps API data only in its
abuse-monitoring logs; a stored completion would make that false"; draft store test docstring lines 3-4 "OpenAI keeps
API data only in its abuse-monitoring logs (policy section 4)". Under OA2 (FABLE_RULINGS_S74_OPENAI.md:6-7) sharing is
ON for all projects and the replacement section-4 text says shared data is governed by OpenAI's terms rather than the
30-day abuse-monitoring limit. So store=False does not make privacy.html:246 "keep ... up to 30 days" a complete
retention statement. What store=False guarantees is narrower: no request becomes a stored completion (SDK docstring
completions.py:511-514: stored for distillation/evals, "Supports text and image inputs"), i.e. dashboard Logs stay empty
(OA3). Spec section 0 lists :246 as made true.
Fix: docstrings and spec section 0 say "every chat completion is sent with store=False, so none is a stored completion
(dashboard Logs); the organisation data-sharing setting (OA2) is separate and unaffected (OA3)". The U8 fill-in must not
cite U3c as the basis of any 30-day bound. Sentence U3c does make true: privacy.html:264 (push shows the display name);
it also removes one OpenAI copy behind :280 ("Photos: we do not store them; section 4 explains what OpenAI keeps").

### F5 major - completions stored before deploy are not addressed
Evidence: U3c changes future calls only. At dfbda511 no call sends store (census), and the spec's own quote is that chat
completions are stored by default for new accounts; "Enabled per call" has no verified definition. If any completions
(text or photos) were stored, they persist after U3c, so :280 and the section-9 deletion promise stay untrue for them.
Fix (owner/orchestrator, read-only first): read dashboard Logs > Completions BEFORE deploy and record the count; if
non-zero, the owner deletes them (dashboard, or chat.completions.delete) and the ledger records it; then the spec's
post-deploy check. UNVERIFIED: no dashboard access.

### F6 minor - T15/T16 do not pin the Arabic body; the spec claims they do
Evidence: mutant mD (AR bonus count doubled) survives; T16 checks only the AR prefix "Sara" + U+060C + " " + AR "your
friend", T15 only "starts with AR your-friend and no Latin". Spec section 3 says "Named copy byte-identical (T16)" and
section 6 calls the AR line the byte-sensitive edit. Existing tests (test_loop2_gift_copy.py:80-108,
test_push_service.py:72-84) check only expiry tokens / any Arabic character.
Fix: build AR_REST by chr() from the code points of push_service.py:185-186 at main (after the name prefix, with
{bonus}=5) and assert full equality: named == "Sara" + AR_COMMA + " " + AR_REST, nameless == AR_REST. Green at GREEN by
construction; kills mD.

### F7 minor - comm gate list incomplete
Evidence: tests/test_prompt_fence.py (:396-470 capturing fake through openai_service/extraction_service ->
chokepoint), tests/test_smart_fallback.py (:381), tests/test_specs_refill_no_fabrication.py (:270-279) drive the
chokepoint and are not in NOTES/comm_files.txt. Measured green at GREEN (u3c-rev-green). No defect, list only.
Fix: add the three files.

### F8 minor - T04 accepts the scripts assignment anywhere in the function
Evidence: draft :146 `fn_sets = any(_is_store_false_assign(s) for s in ast.walk(fn))` passes an assignment placed after
the dispatch, in an except arm, or in a dead branch of shadow_experiments._create_with_retry (:989-1010).
Fix: reuse the T01 dominance rule (top-level statement before the first dispatching statement) for `kwargs` targets;
keep the keyword form for seed_spec_spine.py:382.

### F9 note - A5 is better supported than cited; one residual coupling
Evidence: docs/investigations/2026-10-03-session-71-state/FABLE_RULINGS_U8B.md:10 lists the 27 measured prod columns of
public.users including display_name; auth_service.py:372 already selects "display_name, auth_provider" on the login
path; auth_service.py:907 writes it. Coupling: `_load_invitee` feeds AbuseDetectionService.evaluate_invite
(referral_service.py:655-664); if the select ever errors, the fallback {"id", "email": ""} makes the disposable-email
control (abuse_detection_service.py:254-256) pass silently. Pre-existing pattern; R4 adds a column to that select.
Fix: cite the U8B evidence in A5; no code change.

### F10 note (out of scope) - SAME_DEVICE referral control is dead in prod
Evidence: `_load_invitee` (referral_service.py:762) never selects device_fingerprint_hash; evaluate_invite reads it
(abuse_detection_service.py:249); is_same_device returns False on None (:124-125). Same select line U3c edits.
Fix: separate unit (a fraud-gate behaviour change); do NOT fold into U3c.

### F11 note - OPENAI_BASE_URL indirection
Evidence: llm_provider.py:1-60 documents switching all clients to Azure OpenAI or a gateway by env. store is now sent
unconditionally: a target that rejects unknown params would 400 every compare, and a logging gateway would keep prompts
regardless of store=False. UNVERIFIED (no provider docs research granted; prod value of OPENAI_BASE_URL unknown).
Fix: one runbook/CLAUDE.md sentence: before setting OPENAI_BASE_URL confirm the target accepts `store` and does not log
request bodies; the policy names OpenAI only. Owner confirms the NAME OPENAI_BASE_URL is unset on `web` and the warmer.

### F12 note - display name provenance and Q4
Evidence: display_name is written only by PUT /auth/profile (auth_routes.py:157 min 2/max 100, :1057;
auth_service.py:902-907); signup inserts (auth_service.py:405-410, 827-833) carry no name; no writer in backend/,
scripts/, migrations/; client trims (EditProfileScreen.tsx:91-103). An out-of-band DB trigger cannot be excluded
(display_name is an out-of-band column per U8B spec :93). Q4: no user / safety_identifier / metadata / prompt_cache_key /
extra_headers / extra_body kwarg in app/ or scripts/ (grep).
Fix: owner read-only query counting users whose display_name contains "@" or equals split_part(email,'@',1); extend the
T03 denylist to ("store", "extra_body", "user", "safety_identifier", "metadata", "prompt_cache_key", "extra_headers")
to pin privacy.html:244 (green at main).

### F13 note - T08 is tautological
Evidence: `**params` always builds a fresh dict in Python; T08 cannot fail while the signature is `(client, **kwargs)`.
Fix: keep as documentation or drop; do not count it as a guard.

### F14 note - a test reaches the real client today
Evidence: tests/test_smart_fallback.py::test_smart_fallback_overwrites_NA_string makes 7 getaddrinfo attempts to
api.openai.com:443 (netguard blocks), identical at base ([pyt] tag=u3c-rev-smartfb-base elapsed=7s status=OK rc=0).
Pre-existing, unaffected by U3c. Fix: none in U3c.

### F15 note - R3 (nameless vs "A friend")
Evidence: push_service.py:181-192: a literal "A friend" gives EN "A friend, your friend just used MYEZ." and Latin text
at the head of the AR body. The nameless EN/AR bodies in the GREEN patch are grammatical and need no new translation.
The plan row says "A friend", so the deviation needs the R3 ruling. UNVERIFIED: whether the AR branch is reachable
(push_service.py:182 compares language == "Arabic"; OnboardingData.language is 'en'|'ar' at
SmartCompareApp/src/types/types.ts:659); the EN defect alone justifies R3.
Recommendation: rule R3 = nameless.

### F16 note - pin path resolution
Evidence: REPO comes from abs_mod.__file__; in the scratch worktree every mutant changed results, so the import
resolved to the tree under test. Optional: assert Path(__file__).resolve().parents[1] == REPO.

## Verified spec claims (file:line at dfbda511)
guarded_llm_create def :951, flag check :966, dispatches :967/:974; llm_preflight_breaker_enabled :709;
_openai_dispatch_admission :792; model_config sampling_kwargs :107, token_limit_kwargs :126; 15 call sites (census);
no other chat dispatch in app/ (grep + AST probe); scripts/seed_spec_spine.py:382/:389, shadow_experiments.py:994/:998;
content_safety_service.py:252 moderations only; deployed entry points Procfile, railway.json (app.main),
railway.warmer.json (scripts.cron_warm_price_cache -> compare_from_text at :221-225 -> chokepoint); app/ and scripts/
never import backend/. SDK 3.3.1 (requirements.txt:97, _version.py): store :2888, body :2937, transform :2909,
extra_body :2956, _transform.py:436, _base_client.py:538-543, :2278. Referral :758-771, :762, :926-930; push
:173-194, :181, :185, :191. tests/test_referral_service.py:1012, tests/test_model_config_enforced.py:266. CLAUDE.md:41,
:268, :650. migrations/014:100. Not reconciled: spec says backend/ has 23 direct dispatches; grep counts 18 lines
(out of scope either way).

## Unverified
"Enabled per call" semantics; whether completions are stored today (F5); whether OpenAI's sharing programme covers image
inputs; prod OPENAI_BASE_URL (F11); out-of-band triggers on users.display_name (F12); AR push reachability (F15); the
spec's "this org is not ZDR". I ran no test files beyond the ones named above (CI runs the rest).

## Process notes
I wrote NOTES/t01_ext_probe.py and one stdin probe through a bash heredoc (content had no backslashes or backticks);
every other file was written with Write/Edit. No git write outside the scratch worktree; no network; no .env read.
