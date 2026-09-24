"""Fold the production outage + Bright Data flag + OTA placeholder into docs_patch_s67.py and the draft.
Run from the scratchpad. Idempotent: refuses to double-apply."""
import io
import re
import json

F = json.load(io.open('rw04_facts.json', encoding='utf-8'))
assert 'prod_state' in F and 'ota_line' in F, 'facts not prepared'

s = io.open('docs_patch_s67.py', encoding='utf-8').read()
if 'prod_state_short' in s:
    print('docs_patch_s67.py already patched')
else:
    def rep(old, new, n=1):
        global s
        assert s.count(old) == n, (old[:60], s.count(old))
        s = s.replace(old, new)

    rep('NOTHING flipped, Railway NOT read; merged',
        'Railway READ via the CLI — " + F["prod_state_short"] + "; merged')
    m = re.search(r'rotate the eight leaked keys \(\+ the R-W0 harness incident\), then `ADMIN_API_KEY`; '
                  r'`ENABLE_BRIGHTDATA_BUDGET_GATE=true` on `web` \+ `price-warmer`; the OTA above;', s)
    assert m, 'ahmed list anchor'
    rep(m.group(0),
        '**select a Railway plan, then redeploy `web` and `qaren-landing` (the trial expired 2026-09-21; '
        'nothing merged since #162 has ever run in prod)**; rotate the eight leaked keys (+ the R-W0 harness '
        'incident), then `ADMIN_API_KEY`; `ENABLE_BRIGHTDATA_BUDGET_GATE=true` is DONE on both services (takes '
        'effect on the first deployment after the plan); " + F["ota_line"] + "; the two decision briefs '
        '(`DECISIONS_AHMED.md`) and the migration apply pack (`APPLY_PACK_AHMED.md` §A–§E) are in the state folder;')
    rep('- **Mobile OTA is still the lever:** ',
        '- **Mobile OTA (the lever for the whole W3 lane; status: " + F["ota_line"] + "):** ')

    NL = chr(92) + 'n'          # the two characters backslash + n as they appear in the source file
    lines = s.split('\n')
    idx = next(i for i, l in enumerate(lines) if l.startswith('    "**STATUS 2026-09-24 " + F["close_time"]'))
    assert lines[idx].rstrip().endswith(NL + '"'), lines[idx][-30:]
    lines.insert(idx + 1, '    "- **PRODUCTION DOWN (measured 2026-09-24 ~15:00 local via the Railway CLI):** "'
                          ' + F["prod_state"] + "' + NL + '"')
    idx = next(i for i, l in enumerate(lines) if l.startswith('    "# SESSION 67 — the retro-fix wave'))
    assert lines[idx].rstrip().endswith(NL + NL + '"'), lines[idx][-30:]
    lines.insert(idx + 1, '    "**Production, measured 2026-09-24 ~15:00 local via the Railway CLI:** "'
                          ' + F["prod_state"] + " OTA: " + F["ota_line"] + "' + NL + NL + '"')
    s = '\n'.join(lines)
    io.open('docs_patch_s67.py', 'w', encoding='utf-8', newline='\n').write(s)
    print('docs_patch_s67.py patched')

d = io.open('session67_state_draft.md', encoding='utf-8').read()
if '{{PROD_STATE}}' in d:
    print('draft already patched')
else:
    L = d.split('\n')
    i0 = next(i for i, l in enumerate(L) if l.startswith('The box recovered (process spawns instant'))
    L[i0] = L[i0].rstrip() + ' **Production, measured at ~15:00: {{PROD_STATE}}**'
    i6 = next(i for i, l in enumerate(L) if l.startswith('1. Rotate the eight leaked keys'))
    assert L[i6 + 1].startswith('2. `ENABLE_BRIGHTDATA_BUDGET_GATE=true`'), L[i6 + 1][:60]
    assert L[i6 + 2].startswith('3. OTA `eas update'), L[i6 + 2][:60]
    L[i6 + 1] = ('2. ~~`ENABLE_BRIGHTDATA_BUDGET_GATE=true` on `web` + `price-warmer`~~ — DONE 2026-09-24 ~14:50 by the '
                 "orchestrator on Ahmed's explicit delegation (exact-line count verified on both services; takes effect "
                 'on the first deployment after the plan).')
    L[i6 + 2] = ('3. OTA: {{OTA_LINE}} Then the on-device Arabic walkthrough (the ONLY verification for the '
                 'module-scope `textAlign` class).')
    L.insert(i6, '0. **FIRST — select a Railway plan and redeploy `web` + `qaren-landing`:** the trial expired '
                 '2026-09-21 08:03 UTC; production has had no live deployment since, and nothing merged after #162 '
                 '(2026-09-11) has ever run in prod. Recipe, census queries, flag order and the two product-decision '
                 'briefs: `docs/investigations/2026-09-24-session-67-state/APPLY_PACK_AHMED.md` + `DECISIONS_AHMED.md`.')
    io.open('session67_state_draft.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(L))
    print('draft patched')
