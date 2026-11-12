# S81-07 MEAS-CLAUDE-GATE: adversary, lens security-and-spend (written through the shell)

Unit S81-07; HEAD verified f10c6ae34fcf72232f88362e094801bad954a80c (git rev-parse in the worktree). Base 6b909e0a.
Verdict: NOT_READY (1 blocking, 1 major).
Notes, probes and logs: <scratch>/S81-07_green/adv/sec_notes/ (probe file test_zz_s07g_secprobe.py, probe_out/*.json, secmut.py / secmut2.py, secmut_results*.json, mut_S*.log).
Scratch worktree <scratch>/S81-07_green/adv_securityandspend (detached at HEAD, python only, no junction): removed at the end.

## BLOCKING

B1 THE PR BODY'S RUN COMMAND PUTS THE CREDENTIAL VALUE INTO ARGV (R-S07-3 (c), R-S07-28; lens (e)).
PR_BODY.md:95 (and pr_body_template.md) reads `... env -u ANTHROPIC_API_KEY ... -u YOUTUBE_API_KEY MEAS_ANTHROPIC_TEST_KEY="$(cat <KEYFILE>)" <PY> -m scripts.meas_claude_gate <stage> --out <OUT>`.
After the command word `env`, `NAME="$(cat f)"` is NOT a shell prefix assignment: bash expands the file and passes `NAME=<value>` as an ARGUMENT to env.exe.
Measured on this box (Git Bash env.exe, a non-credential name and a run-time canary, then Get-CimInstance Win32_Process):
- argument form: `16456 env.exe :: "C:\Program Files\Git\usr\bin\env.exe" -u S07G_NOPE S07G_ARGV_PROBE=qzxprobe187626130 C:/.../python.exe -c ...` (the value in the command line, listed while the python child was still running: env.exe stays alive as the parent for the whole run)
- prefix form `S07G_ARGV_PROBE="$(cat f)" env -u S07G_NOPE <PY> ...`: `23308 env.exe :: ... env.exe" -u S07G_NOPE C:/.../python.exe -c ...` (no value); the child saw the variable in both forms (True True).
So the official command exposes the owner's key to every process listing for the run's duration (this box's own harness rules make agents poll Win32_Process command lines every 30 s), to command-line audit logging and EDR. The CLAUDE.md block (prose only, no concrete command) is not affected.
Fix (documentation): `cd <unit worktree> && MEAS_ANTHROPIC_TEST_KEY="$(cat <KEYFILE>)" env -u ... <PY> -m scripts.meas_claude_gate <stage> --out <OUT>` (the assignment BEFORE env), and say in the body that it must precede `env`.

## MAJOR

M1 THE LIVE NETWORK GUARD REFUSES THE ONE ALLOWED HOST: every live stage stops at its first send (GC-8, R-S07-26 (a); lens (c)).
scripts/meas_claude_gate.py:306-314 `host_allowed` does `h = str(host or "").strip().lower()`; the gai wrapper (:1041-1044) passes the caller's host through it. The pinned transport stack (httpx2 2.12.0 / httpcore2 2.12.0 / anyio 4.14.2 / anthropic 1.12.1) calls socket.getaddrinfo with the IDNA-encoded BYTES host, so str(b"api.anthropic.com") = "b'api.anthropic.com'" and the host is refused.
Measured (probe_out/probe_e2e_live.json): main(["text","--out",<tmp>,"--settings","A4_refusal_names","--max-calls","3"]) in live mode, with the REAL httpx2 transport and a fake resolver that would only record and raise: exit 6, stop_reason host_refused, hosts_refused ["b'api.anthropic.com'"], resolver_calls [] (never reached), ledger [sent, done StageStop usd=worst 0.000675], stderr empty, no canary leak. probe_selector_loop.json: the same refusal on the _WindowsSelectorEventLoop AND the default ProactorEventLoop; host_allowed("api.anthropic.com",443) True, host_allowed(b"api.anthropic.com",443) False.
No row sees it: R60 / R68 call socket.getaddrinfo("example.invalid", 443) with a str; every other row uses a fake client or a MockTransport (no resolution).
Effect: fail-closed (no leak, no real spend; one phantom worst-case booking per stage start), but the harness cannot measure anything: the ops lane's first run of every stage ends host_refused on call 1.
Fix: decode bytes (ascii / idna) in host_allowed and _loopback (and record the decoded name); add a row that drives one send through the real httpx2 transport with a fake resolver (the probe's shape). Follow-on hazard for the fix: on a selector loop the connect wrapper then sees the resolved IP literal and refuses it (host_allowed("192.0.2.1",443) False, measured), so either allow the addresses the wrapper itself resolved for the allowed host or state that the run uses the Windows proactor default (L15 already says the wrappers do not see a proactor connect).

## MINOR (stated limits by default)

m1 A ledger line with a wrong-typed attempt ("x"), an unhashable call_id (a list) or a non-UTF-8 byte refuses the start as `crashed class=ValueError / TypeError / UnicodeDecodeError` (exit 3), not `ledger_corrupt file=<path> line=<n>` (exit 2). Measured (probe_ledger_*.json): nothing sent, lock removed in all three; a truncated line gives the ruled `ledger_corrupt ... line=1` exit 2.
m2 The PR body's `env -u` list names 4 of the ANTHROPIC_* names; any other present name refuses the start (prefix rule, names only) and the body says to add `-u`: fail-closed.
m3 A --dry-run started with the variable set neither reads nor removes it, so the _git_head child inherits it (no output byte carries it). The contract says the dry run runs with the variable unset.
m4 Stage W: the worst case = prompt bound + 60,000 tokens per search, which stays below the Haiku 100,000-token long-context threshold, while a real server-tool turn (two sampling passes: about 2 x prompt + results) can cross it and be priced at 5x for the whole request. W sends are sequential, so the overshoot is at most one call: about 0.05-0.10 USD over the 3.00 stage cap at the 2026-10-22 table (L8 already stated; the workspace limit is the backstop).
m5 app/config.py Settings(BaseSettings) with env_file ".env" reads a CWD dotenv into memory, outside the dotenv guard (it never touches os.environ; no harness path uses Settings). The run command's `cd <unit worktree>` (no dotenv) is the control.
m6 Equivalent survivor S06: removing Budget.reserve's in-run unit-ceiling clause is killed by no row; it is equivalent while the start check (unit on disk + this stage's max_usd <= 15) and the lock hold (the stage cap then bounds the unit), so it is defense in depth only, unpinned.
m7 Process: the shared wait script excludes every s07g- tag, so this adversary's runs overlapped with another s07g- pytest of the lane (PIDs 15932 / 25716 seen at 07:50); no foreign-tag run was overlapped.

## MEASURED CLEAN
- THE CREDENTIAL (probe_canary_*.json; canary built at run time, set through monkeypatch only; the real SDK with a MockTransport that echoes the x-api-key header into the body, a response header and an exception message): success (redactions 12), 400 (BadRequestError, booked 0), 401 (exit 5 after one request), 429 (4 sends booked 0, then the setting stops), 500 (3 transients booked worst, exit 6), ConnectError with the key in its message (APIConnectionError, exit 6), a crash raising ValueError(<canary>) after the send (`crashed class=ValueError`, exit 3, intent line only), KeyboardInterrupt in the transport (exit 130, done line booked worst): no 4-character window of the canary in any file under --out, stdout or stderr; the variable absent inside the transport on every request, at the _git_head seam and after main (GC-10); the lock gone on every path (GC-7).
- SSLKEYLOGFILE (set in-process to a tmp path): the httpx2 2.12.0 client's SSL context has keylog_filename None with trust_env False and True.
- Production name: no code path reads ANTHROPIC_API_KEY (the prefix refusal precedes the read); proxies ignored (trust_env False, pinned by R07).
- THE CEILING: the reservation is synchronous (no await between check and reserve); GC-6 sticky stop; an intent with no done line is booked at worst on the next start (resume keeps the attempt counter, so a re-send never pairs with an old intent); O_EXCL lock; corrupt / truncated ledger refuses the start. Largest overspend constructed: text / moderation / vision none beyond the price table (the byte bound over-estimates); stage W one call's excess (m4); two output folders double the 15.00 ceiling (stated; the workspace spend limit is the only cross-folder backstop).
- THE INPUTS: every fixture string path listed (compare_pairs, fragrance_names, moderation_parity, verdict_gold, web_search_domains): synthetic catalogue notes, public product names, BHD prices, scores_summary text; no personal value, no instruction aimed at the model; the 20 flag-worthy moderation texts are 3 synthetic templates (an insult, a threat to a seller, a counterfeit offer), no real person, no excluded category.

## MUTANTS (lens; byte copies in the scratch worktree; every restore sha256-verified c38854da...; the scratch base run fails only test_r35_fixtures, a CRLF-checkout artefact of the scratch worktree)
[pyt] tag=s07g-secbase elapsed=30s status=FAIL rc=1 (1 failed: test_r35_fixtures, b'\r' in a fixture of the CRLF scratch checkout)
S01 variable not popped: KILLED by r70 (s07g-sm-S01 elapsed=37s status=FAIL)
S02 hook ignores the port: KILLED by r69 (s07g-sm-S02 elapsed=50s)
S03 hook ignores the scheme: KILLED by r69 (s07g-sm-S03 elapsed=45s)
S04 scrub passthrough: KILLED by r52 (s07g-sm-S04 elapsed=36s)
S05 every error booked 0: KILLED by r44, r48b (s07g-sm-S05 elapsed=41s)
S06 no in-run unit clause: SURVIVED (equivalent, m6) (s07g-sm-S06 elapsed=33s)
S07 live gai allows any host: KILLED by r60 (s07g-sm-S07 elapsed=31s)
S08 logging not silenced: KILLED by r75 (s07g-sm-S08 elapsed=37s)
S09 no post-import re-scan: KILLED by r36, r67 (s07g-sm-S09 elapsed=33s)
S10 trust_env True: KILLED by r07 (s07g-sm-S10 elapsed=32s)
S11 lock not exclusive: KILLED by r49 (s07g-sm-S11 elapsed=43s)
S12 intent not fsynced: KILLED by r20 (s07g-sm-S12 elapsed=33s)

## RUNS
[pyt] tag=s07g-secprobe1 elapsed=5s status=OK rc=0 (14 passed; first draft, superseded)
[pyt] tag=s07g-secprobe2 elapsed=6s status=OK rc=0 (14 passed) [netguard] blocked 0
[pyt] tag=s07g-secprobe3 elapsed=23s status=OK rc=0 (1 passed, the e2e live probe) [netguard] blocked 0
No jest run (no client byte; not this lens's gate). No network, no live API, no ANTHROPIC_* or MEAS_ANTHROPIC_TEST_KEY set in any shell; .env never read.
