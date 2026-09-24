"""Current main went live via the flag-triggered rebuild: correct the four docs files (byte-safe)."""
import io
import sys

W = sys.argv[1]
OLD = ('Current main (`dff65210`) still has to reach `web`: the merge of the docs PR is the first push since the plan '
       'and therefore the test of the GitHub trigger.')
NEW = ('**Current main `dff65210` went LIVE at 15:24 local:** the `ENABLE_LOGOUT_UPSTREAM_REVOCATION=true` variable '
       'change rebuilt `web` from the connected GitHub source (deployment `2c4dbf6e`, commit `dff65210`), so the whole '
       'session-66/67 code line is in production with the Bright Data gate and the logout flag ON; `/health` 200, '
       '`loop_lag_max_ms` 101 at startup, and R-MAIN\'s `loop_lag_max_60s_ms` field is visible (absent at `fe0298ae`) = '
       'proof of the new code. The GitHub source is connected; the #197 merge should show a `BUILDING` row within a minute.')
changed = []
for rel in ('CLAUDE.md', 'docs/CONTEXT_SESSION_LOG.md', 'docs/investigations/2026-09-24-session-67-state.md'):
    p = W + '/' + rel
    t = io.open(p, 'rb').read().decode('utf-8')
    n = t.count(OLD)
    if n == 0 and 'went LIVE at 15:24' in t:
        continue
    assert n == 1, (rel, n)
    io.open(p, 'wb').write(t.replace(OLD, NEW).encode('utf-8'))
    changed.append(rel)

p = W + '/docs/investigations/2026-09-24-session-67-state/APPLY_PACK_AHMED.md'
t = io.open(p, 'rb').read().decode('utf-8')
OLD2 = ('What remains here is step 4: current main has to deploy — the docs PR #197 merge is the first push after the '
        'plan; if no `BUILDING` row appears on `web` within a minute of it, reconnect the source as described.')
NEW2 = ('**UPDATE 15:25: step 4 is DONE too** — the logout-flag variable change rebuilt `web` from the connected GitHub '
        'source at current main `dff65210` (deployment `2c4dbf6e`, `/health` 200), so every session-66/67 merge is now in '
        'production with `ENABLE_BRIGHTDATA_BUDGET_GATE=true` and `ENABLE_LOGOUT_UPSTREAM_REVOCATION=true`. Nothing '
        'remains in this section except watching the first `[auth]` and `[BUDGET]` log lines.')
if OLD2 in t:
    io.open(p, 'wb').write(t.replace(OLD2, NEW2).encode('utf-8'))
    changed.append('APPLY_PACK_AHMED.md')
print('changed', changed)
