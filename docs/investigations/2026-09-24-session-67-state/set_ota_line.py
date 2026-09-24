import io
import json

F = json.load(io.open('rw04_facts.json', encoding='utf-8'))
ota = ('OTA PUBLISHED 2026-09-24 12:06:46 UTC to the `preview` channel from main `ab9442ae` (gitCommitHash '
       '`ab9442ae6625267cd114a5593661ee9b79f1a78f`): EAS group `561d2cba-f374-40e8-866b-3bfe6c7c9c3b`, runtime 1.0.0, '
       'iOS update `01a0d34f-a2f6-7649-93bf-0a46700434c8` + Android update `01a0d34f-a2f6-7578-a9af-7aa09210b108`, '
       'published by the orchestrator with `--clear-cache`; sourcemaps NOT uploaded (no Sentry token in this session); '
       'the first attempt failed because the shared `node_modules` lacked `intl-pluralrules` (lock 2.0.1) and carried '
       "axios 1.16.1 against lock 1.20.0 — `npm install --no-save` reconciled it (CI's `npm ci` had hidden the drift). "
       'Phones need TWO cold launches; the on-device Arabic walkthrough is still owed. Ledger row: '
       '`docs/runbooks/qaren-canary-onboarding.md` §9.')
F['ota_line'] = ota
F['draft']['OTA_LINE'] = ota
io.open('rw04_facts.json', 'w', encoding='utf-8', newline='\n').write(json.dumps(F, ensure_ascii=False, indent=1) + '\n')
s = json.dumps(F)
print('ota_line set; remaining tokens:', {t: s.count(t) for t in ('__PR__', '__SHA__', '__TIME__', '__OTA__')})
