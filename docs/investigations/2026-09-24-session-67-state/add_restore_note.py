"""Record the production restore in the four docs files of the docs PR (byte-safe, line endings preserved)."""
import io
import sys

W = sys.argv[1]
ANCHOR = 'The Railway MCP plugin stays Unauthorized; the CLI works.'
NOTE = (' **RESTORED 2026-09-24 15:18–15:20 local:** Ahmed subscribed; Railway re-created `web` (SUCCESS 12:18:27Z, '
        'image `fe0298ae`) and `qaren-landing` (12:18:28Z); the orchestrator\'s `railway redeploy` re-issued both a '
        'minute later (web `6a8fbc3a`, landing `253bb93d`); `/health` answered 200 at 15:20:36 with `loop_lag_max_ms` '
        '2.0 on the fresh process; the landing\'s Railway domain is 200 while `qaren.app` stays 522 (the pre-existing '
        'Cloudflare-origin finding, not this outage). Current main (`dff65210`) still has to reach `web`: the merge of '
        'the docs PR is the first push since the plan and therefore the test of the GitHub trigger.')

changed = []
for rel in ('CLAUDE.md', 'docs/CONTEXT_SESSION_LOG.md', 'docs/investigations/2026-09-24-session-67-state.md'):
    p = W + '/' + rel
    b = io.open(p, 'rb').read()
    t = b.decode('utf-8')
    n = t.count(ANCHOR)
    assert n >= 1, (rel, n)
    if 'RESTORED 2026-09-24 15:18' in t:
        continue
    t = t.replace(ANCHOR, ANCHOR + NOTE)
    io.open(p, 'wb').write(t.encode('utf-8'))
    changed.append((rel, n))

p = W + '/docs/investigations/2026-09-24-session-67-state/APPLY_PACK_AHMED.md'
b = io.open(p, 'rb').read()
t = b.decode('utf-8')
old = 'Do, in order:'
assert t.count(old) == 1
if 'UPDATE 15:20 local' not in t:
    t = t.replace(old, ('**UPDATE 15:20 local — steps 1 and 2 are DONE:** you subscribed at ~15:18; Railway re-created `web` '
                        'and `qaren-landing` and I re-issued `railway redeploy` for both; `/health` is 200 on image `fe0298ae` '
                        '(2026-09-11). What remains here is step 4: current main has to deploy — the docs PR #197 merge is the '
                        'first push after the plan; if no `BUILDING` row appears on `web` within a minute of it, reconnect the '
                        'source as described.\n\nDo, in order:'))
    io.open(p, 'wb').write(t.encode('utf-8'))
    changed.append(('APPLY_PACK_AHMED.md', 1))
print('changed', changed)
