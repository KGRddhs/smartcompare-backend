"""Append the session-67 OTA row to docs/runbooks/qaren-canary-onboarding.md section 9 (CRLF preserved, newest first)."""
import io
import sys

p = sys.argv[1]
b = io.open(p, 'rb').read()
assert b.count(b'\r\n') > 400, 'expected a CRLF file'
text = b.decode('utf-8')
header = '| date | channel | group id | gitCommitHash | runtimeVersion | sourcemaps uploaded | published by | notes |\r\n|---|---|---|---|---|---|---|---|\r\n'
assert text.count(header) == 1, text.count(header)
row = ('| 2026-09-24 | preview | `561d2cba-f374-40e8-866b-3bfe6c7c9c3b` | `ab9442ae6625267cd114a5593661ee9b79f1a78f` | 1.0.0 '
       '| no — the publishing session had no Sentry token; upload still owed '
       '| Fable orchestrator, session 67 (the Expo account logged in on the dev box) '
       '| Session 67 set: the W3 client halves (W3-4, W3-6, W3-9, W3-11bcd, W3-14, W3-15, W3-16), R-CLIENT W1-4d logout body, '
       'B1 lucide per-icon split, M21/M23 mobile waves — PRs #163–#195. Published 12:06:46 UTC with `--clear-cache`; '
       'iOS update `01a0d34f-a2f6-7649-93bf-0a46700434c8`, Android `01a0d34f-a2f6-7578-a9af-7aa09210b108`; the served '
       'manifest was verified through u.expo.dev on both platforms (same ids, same group). The first attempt failed at '
       'bundling because the clone\'s `node_modules` did not match the lock (`intl-pluralrules` missing, axios 1.16.1 vs '
       '1.20.0 — CI\'s `npm ci` hides that class); `npm install --no-save` reconciled it. Owed: the sourcemap upload '
       '(`expo-upload-sourcemaps dist` with a Sentry token) and the on-device Arabic walkthrough. Supersedes the '
       '2026-09-02 row below as the live bundle. |\r\n')
assert 'SESSION_BUNDLES.md:' not in row and 'CONTEXT_SESSION_LOG.md:' not in row
if '561d2cba-f374-40e8-866b-3bfe6c7c9c3b' in text:
    print('row already present')
else:
    text = text.replace(header, header + row)
    io.open(p, 'wb').write(text.encode('utf-8'))
    print('row added')
