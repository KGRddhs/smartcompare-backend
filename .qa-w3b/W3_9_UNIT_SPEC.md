# W3-9 — lucide per-icon imports (MB-STARTUP-BUNDLE-01)

**Unit:** W3-9. **Finding:** `MB-STARTUP-BUNDLE-01` (verified P1; mobile-checkup lead
"lucide barrel = ~1.27 MB / 25%"). **Base:** `origin/main` = `ed75dc708b82c0b911c9de8a3e59d4418c6e278c`,
measured 2026-09-11 in worktree `C:/Users/SynAckITPC/Documents/AI/sc-w3-lucide`.

**OTA class, per half:**

| half | class | state at ed75dc70 |
|---|---|---|
| the bundle fix itself (B1: compile-time rewrite of the 35 barrel imports) | OTA-safe | **ALREADY ON MAIN** — commits `e3d9adb5`, `8d8b9dc8`, `cea9effa`, merged in PR #138 (`2ba3d7d3`) on 2026-09-07. NOT on phones: the `preview` channel was published from `97b5f15` (2026-09-02). |
| the CI-durable fence (a test that reddens if the barrel is ever re-imported wholesale) | ci-only | **ALREADY ON MAIN** — `__tests__/babel.lucideIcons.b1.test.ts` "fences the barrel", 7/7 green, run by the required `frontend-tests` job (`npx jest --ci`). |
| residual: two measured holes in that fence (`require()` / dynamic `import()` / `.js` sources are invisible to it) | ci-only (tests only, no app source, no bundle change) | OPEN — the only work this unit can still carry. Optional; see section 4. |

**Bottom line for the orchestrator:** the plan's two red tests are both wrong at HEAD — one
would ban the only import form all three resolvers accept, the other is already true and
cannot be CI-durable without a bundle step CI does not have. The defect is fixed on main and
was measured when it landed (−1,749,282 B Hermes, 3,832 → 2,192 modules). What is left is
(a) Ahmed's OTA, which must carry `--clear-cache` the first time, and (b) an optional
test-only hardening of the fence. If the campaign wants zero-diff units closed as
already-green, close this one; if it wants the fence hardened, the spec below is exact.

---

## 2. Scope correction — what is ALREADY on main

The plan row (`docs/investigations/2026-09-06-full-review.md:136`, re-located at ed75dc70):

> | **W3-9 lucide per-icon imports** | MB-STARTUP-BUNDLE-01 | 34 barrel imports | eslint `no-restricted-imports` on the barrel (RED: 34) + a source-map assertion (<100 lucide icon modules; RED: 1,703). Measure before/after with `expo export`. | In the other session's REMAINING "B1" — one owner. OTA-safe. |

That row was written at 76ace90 with the note "In the other session's REMAINING B1 — one
owner". The other session shipped B1 the next day. Three commits, all on main at ed75dc70:

```
e3d9adb5 2026-09-07 fix(mobile): B1 — split the lucide barrel import into per-icon file imports
8d8b9dc8 2026-09-07 fix(mobile): P-B1-CACHE - key Metro transform cache on babel.config.js
cea9effa 2026-09-07 test(mobile): P-B1-FENCES - close the four holes around the B1/B4 bundle fences
2ba3d7d3            Merge pull request #138 from KGRddhs/feature/m23-mobile-w1
```

`e3d9adb5`'s body carries the measurement: "Measured with `npx expo export --platform ios -c`:
before 8,259,431 B hbc / 3,832 modules; after 6,510,149 B hbc / 2,192 modules; saved
1,749,282 B (21.18%) / 1,640 modules. Android bundles to the same 2,192 modules."
`CLAUDE.md:494` and `docs/CONTEXT_SESSION_LOG.md:12` record it as independently reproduced
at merge (`−1,749,282 B Hermes`).

### Plan red test 1 — eslint `no-restricted-imports` on the barrel (RED: 34) — DROPPED, it is wrong at HEAD

Three resolvers have to accept whatever import form the sources use: Metro (bundle), jest
(the 278-suite gate) and tsc (the `frontend-typecheck` gate). Measured on the installed
versions (section 10, probes 3/4/5) for every candidate form, as if written in
`src/screens/HomeScreen.tsx`:

| import form | Metro 0.83.3 (`unstable_enablePackageExports: true`) | jest 29.7.0 | tsc 5.9.3 (`bundler`, `customConditions: ["react-native"]`) |
|---|---|---|---|
| `'lucide-react-native'` (bare barrel) | RESOLVED → `dist/esm/lucide-react-native.mjs` (all 1,703 icons) | RESOLVED → `__mocks__/lucide-react-native.ts` (79 fn exports) | RESOLVED → `dist/lucide-react-native.d.ts` |
| `'lucide-react-native/icons'` | RESOLVED → `dist/esm/icons/index.mjs` — **itself a 1,703-export barrel** | MODULE_NOT_FOUND | RESOLVED → `dist/icons.d.ts` |
| `'lucide-react-native/icons/camera'` | FailedToResolveNameError (+ exports warning) | MODULE_NOT_FOUND | UNRESOLVED |
| `'lucide-react-native/dist/esm/icons/camera.mjs'` | RESOLVED, **with a warning: "not listed in the exports … Falling back to file-based resolution"** | MODULE_NOT_FOUND | UNRESOLVED |
| relative file `../../node_modules/lucide-react-native/dist/esm/icons/camera.mjs` | RESOLVED | throws `Cannot use import statement outside a module` (ESM, ts-jest transforms only `.tsx?`; `.mjs` is not even in `moduleFileExtensions`) | RESOLVED (`ext=.mjs`, no `.d.mts` beside it → implicit-any under `strict`) |

So the **bare barrel is the only form that passes all three**, and B1's design — keep the
barrel in source, rewrite it to the relative icon file at compile time under Metro only,
leave jest on the mock — is the only shape that works **without a package change**
(`babel-plugin-transform-imports` is NOT installed: `ls node_modules | grep -iE
'transform-imports|babel-plugin-import|modularize'` → nothing; and package.json/lockfile
are off-limits). An eslint rule that bans `from 'lucide-react-native'` would redden all 35
sites AND forbid the shipped design. It also covers LESS than the existing fence: the CI
eslint step is `npx eslint "src/**/*.{ts,tsx}"` (`.github/workflows/ci.yml:270`) — it never
lints `App.tsx`, the very file the finding cites — whereas the jest fence walks `src/` +
`App.tsx` + `index.ts`. Dropped.

Correction to B1's own text: `e3d9adb5`, `babel.config.js:51-56` and
`babel.lucideIcons.b1.test.ts:140-142` all say the dist deep path is "blocked" / "cannot
resolve" at runtime. That is true of jest and tsc and of Node (`ERR_PACKAGE_PATH_NOT_EXPORTED`),
**not of Metro**: `metro-resolver/src/resolve.js:343-349` catches `PackagePathNotExportedError`,
logs a warning and falls back to file resolution (probe 3 shows the fallback resolving
`camera.mjs`). The shipped design is still right — jest and tsc refuse the form — but the
stated reason is one resolver short. Cosmetic; see section 9 for the PR sentence if the
unit ships.

### Plan red test 2 — source-map assertion `< 100` lucide icon modules (RED: 1,703) — DROPPED, already true and not CI-durable

* Already true in the shipped artefact: 3,832 → 2,192 modules (`e3d9adb5`); 1,640 removed
  of which the finding's 1,703 icons minus the 68 used ≈ 1,635 are icons.
* Static equivalent, measured today (probe 1): over 151 source files the B1 plugin emits
  **exactly 68 distinct icon files** (`arrow-left.mjs` … `zap.mjs`) for 136 value specifiers
  / 68 distinct names in 35 files, 0 type-only, 0 unmapped, map size 5,844 names.
* Cannot be CI-durable: CI has no bundle step (`ci.yml` frontend-tests = `npm ci`, `jest
  --ci`, `eslint`, `tsc`), so a source-map assertion has nowhere to run. The CI-durable
  proxy already exists: `babel.lucideIcons.b1.test.ts:241-269` "fences the barrel" fails on
  any default/namespace/side-effect import, re-export, subpath, or value name the map cannot
  resolve — each of which would re-add the whole barrel. Green today (7/7).

### Plan "a test that counts barrel importers" — ALREADY EXISTS

`babel.lucideIcons.b1.test.ts:294-295`:
```ts
    // 34 barrel sites when B1 landed; guard against a silent regression to 0.
    expect(touched.length).toBeGreaterThanOrEqual(30);
```

### Anchors that moved

* Finding cites `SmartCompareApp/App.tsx:18`; at ed75dc70 the import is at **`App.tsx:19`**:
  `import { Home, Clock, User as UserIcon } from 'lucide-react-native';`
* "34 barrel imports" is **35 files**: 34 under `src/` **plus `App.tsx`** (probe 1 lists them).
  `e3d9adb5` and the b1 suite's header repeat "34"; the finding's own anchor is the 35th file.
  The importer-count pin (`>= 30`) is unaffected.

---

## 3. The defect — measured

**What the finding described (true at 76ace90, and true on the phones today):** every one of
the 35 files imports from the package barrel, e.g. `App.tsx:19` above, `HomeScreen.tsx:50`
`import { Camera } from 'lucide-react-native';`. The bare specifier resolves under Metro to
`dist/esm/lucide-react-native.mjs`, which is 1,703 lines of
`export { default as X } from './icons/x.mjs';` (measured: `grep -c "from './icons/"` =
1703; `dist/esm/icons/` holds 3,408 files = 1,704 `.mjs` + maps). `sideEffects: false` does
not help — Metro does not tree-shake re-exports — so the graph keeps all 1,703 icon factories
and runs them at boot (verifier: 1,706 requires, 5,849 `defineProperty`, 1,703 `forwardRef`
before React mounts anything; 1,212,812 B = 23.96% of the iOS JS bundle).

**What is on main at ed75dc70:** `babel.config.js:126-181` `lucideIconImportsPlugin` rewrites,
per specifier, `import { Camera } from 'lucide-react-native'` →
`import Camera from '<relative>/node_modules/lucide-react-native/dist/esm/icons/camera.mjs'`,
using a name→file map parsed from the barrel itself (`buildLucideIconMap`, `:95-124`).
Wired at `:199-201` (`if (!isTest) { plugins.push(lucideIconImportsPlugin); }`), so it is active
for `expo export`/`eas update` and inert under jest, where `jest.config.js:20` maps the bare
specifier to `__mocks__/lucide-react-native.ts`. `metro.config.js:15` folds a content hash of
`babel.config.js` + the lucide barrel into Metro's `cacheVersion` so a stale machine-global
transform cache cannot re-emit the old bundle (`8d8b9dc8` measured exactly that happening:
"pre-B1 babel.config.js → 2196 modules / 6,518,432 B (stale, wrong)").

**Probe that the shipped plugin does the job today (probe 1, full output in section 10):**
`distinctIconFilesEmitted: 68`, `unmappedNames: []`, `barrelImporterFiles: 35`.

**Probe that the fence is green today (probe 2):**
```
PASS __tests__/babel.lucideIcons.b1.test.ts (7.931 s)
  √ wires the plugin into dev + production and leaves it OFF under test
  √ keeps react-native-reanimated/plugin last in every env
  √ resolves lucide v1 renames from the barrel instead of guessing kebab-case
  √ fences the barrel: the only lucide imports are icon names the map resolves
  √ rewrites every real source file to icon paths that exist on disk
  √ leaves type-only imports on the barrel and still splits the icons beside them
  √ exports every icon the app imports from the jest lucide mock
Tests: 7 passed, 7 total
```

**The residual defect this unit CAN still address — two holes in the fence, measured by reading it:**

`babel.lucideIcons.b1.test.ts:90-104`:
```ts
/** Every .ts/.tsx under src/, plus the two bundled entry files beside it. */
function sourceFiles(): string[] {
  ...
      else if (/\.tsx?$/.test(entry.name)) found.push(full);
```
and `:135-139`:
```ts
  for (const node of ast.program.body) {
    const source = node.source?.value;
    if (typeof source !== 'string' || !new RegExp(`^${LUCIDE_PACKAGE}(/|$)`).test(source)) {
      continue;
    }
```
Only top-level `import`/`export … from` declarations are seen. A `const L =
require('lucide-react-native')`, an `await import('lucide-react-native')`, an `import L =
require('lucide-react-native')`, or any of those in a `.js`/`.jsx` file under `src/` (Metro
`sourceExts` includes `js`/`jsx`/`mjs`/`cjs` — probe 3 settings) is invisible to the fence,
is NOT rewritten by the plugin (it visits `ImportDeclaration` only, `babel.config.js:130`),
and under Metro pulls the whole barrel back: 1,703 modules, ~1.75 MB, with every CI check
green. Under jest the same `require` resolves to the mock, so no other suite reddens either.
Today there are zero such sites (`grep -rnE "require\(['\"]lucide|import\(['\"]lucide" src
App.tsx index.ts` → only the b1 suite's own `require` at `:327`, which is the mock) and zero
non-TS sources under `src/` (only `src/i18n/*.json`), so this is a latent hole, not a live
regression.

---

## 4. The fix — MINIMAL design (optional; test-only; ci-only)

Nothing under `src/`, `App.tsx`, `index.ts`, `babel.config.js`, `metro.config.js`,
`jest.config.js`, `package.json` or any mock changes. If the unit ships at all it is this:

1. **`SmartCompareApp/__tests__/helpers/lucideFence.ts` (new)** — move `sourceFiles()` and
   `lucideRefs()` out of the suite unchanged in behaviour, then extend them:
   * `sourceFiles()` matches `/\.(tsx?|jsx?|mjs|cjs)$/` (Metro's script `sourceExts`, minus
     json/css) — still `src/` + `App.tsx` + `index.ts`.
   * `lucideRefs()` additionally walks the whole AST (`@babel/traverse` 7.29.0 IS resolvable
     from the app root — measured: `require.resolve('@babel/traverse')` →
     `node_modules/@babel/traverse/lib/index.js`; it is a transitive dependency of
     `@babel/core`, not a direct one in package.json, so import it via `require` the way the
     suite already requires `@babel/core` and `@babel/parser`; if a future lockfile drops it,
     a hand-rolled recursive walk over node keys is ~15 lines and needs no package) and reports:
     * `CallExpression` whose callee is identifier `require` and whose sole argument is a
       string literal matching `^lucide-react-native(/|$)` → shape `'require'`;
     * `ImportExpression` / `CallExpression` with callee type `Import` and the same literal
       → shape `'dynamic-import'`;
     * `TSImportEqualsDeclaration` with `TSExternalModuleReference` to that literal →
       shape `'require'`.
   * Parse `.js`/`.jsx` with the same `['typescript','jsx']` parser plugins (superset; fine).
2. **`SmartCompareApp/__tests__/babel.lucideIcons.b1.test.ts`** — import the helper; the
   existing assertion at `:257` (`shape` not in `['value','type']` → `[]`) then covers the
   new shapes with no other change. Update the header comment (item 5) and the `:140-142`
   comment ("blocked by the package's exports map at runtime" → "blocked under jest and tsc;
   Metro warns and falls back — either way the plugin never rewrites it").
3. **`SmartCompareApp/__tests__/helpers/lucideFence.test.ts` (new)** — the self-test in
   section 5, on synthetic code, so the fence's own reach is pinned and a mutation of the
   helper is caught.

What does NOT change: the plugin, its map, the mock, the `>= 30` importer pin, the 68 icons,
the bundle. Backward compatibility with the backend: N/A (no runtime change). No flag: nothing
runs on a device.

---

## 5. Red tests — exact files, assertions, measured reason each is RED today

All in `SmartCompareApp/__tests__/helpers/lucideFence.test.ts`, on synthetic source strings
(the real tree has zero offenders, so the real-tree fence cannot be made red without editing
`src/`, which this batch forbids and which would be a fake red anyway).

| # | assertion | RED today because (measured) | mutation that must redden it after the fix |
|---|---|---|---|
| R1 | `lucideRefs('x.ts', "const L = require('lucide-react-native');")` returns one ref with `shape: 'require'` | the helper module does not exist; and the logic it would be extracted from returns `[]` for this input (`:135-139` only reads `node.source` on top-level statements — a `VariableDeclaration` has none) | delete the `CallExpression`/`require` branch → returns `[]` |
| R2 | `lucideRefs('x.ts', "export async function f(){ return import('lucide-react-native'); }")` returns one ref with `shape: 'dynamic-import'` | same | delete the `Import` callee branch |
| R3 | `lucideRefs('x.ts', "import L = require('lucide-react-native');")` returns one ref with `shape: 'require'` | same | delete the `TSImportEqualsDeclaration` branch |
| R4 | `sourceFiles()` applied to a temp dir containing `a.tsx`, `b.js`, `c.jsx`, `d.json` returns `a.tsx`, `b.js`, `c.jsx` and not `d.json` (inject the root as a parameter; do not touch `src/`) | today's regex is `/\.tsx?$/` → `b.js`/`c.jsx` missing | revert the regex to `/\.tsx?$/` |
| R5 (regression pin, GREEN today — keep, label as pin) | `lucideRefs` on `"import { Camera, type LucideIcon } from 'lucide-react-native';"` yields `value 'Camera'` + `type 'LucideIcon'`; on `"import * as L from 'lucide-react-native'"` yields `namespace`; on `"export * from 'lucide-react-native'"` yields `re-export`; on `"import x from 'lucide-react-native/icons'"` yields `subpath` | already the behaviour at `:143-172` | remove any branch → its case fails |
| R6 (positive control on the real tree, GREEN today) | the extracted `sourceFiles()` over the real `src/` returns ≥ 150 files and the real-tree fence still reports 136 value refs across 35 files with `[]` non-value/type shapes | measured: 151 files, 136 value specifiers, 35 importers | replace the walk with `[]` → the `values.length > 50` positive control at `:252` reddens |

Decoration check: R1–R4 each name the mutation; R5/R6 are pins with a mutation and say so.

---

## 6. Preserve — behaviours that must stay identical, with the proof

| behaviour | proof |
|---|---|
| The plugin is ON for development + production and OFF under test | `babel.lucideIcons.b1.test.ts:211-220` (green) |
| `react-native-reanimated/plugin` stays last | `:222-227` (green) |
| Alias-aware map (`Home`→`house.mjs`, `AlertCircle`→`circle-alert.mjs`, `BarChart3`→`chart-column.mjs`) | `:229-239` (green) |
| Every real barrel importer is rewritten to an existing icon file; ≥ 30 importers | `:271-296` (green; 35 today) |
| Type-only imports stay on the barrel | `:298-319` (green) |
| Every imported icon name is a callable export of the jest mock (79 today) | `:321-338` (green) |
| `metro.config.js` is the stock Expo default plus the `cacheVersion` line; the key changes when `babel.config.js` or the barrel changes | `metro.cacheVersion.js` + its suite (grep `__tests__` for `cacheVersion` before touching; not touched here) |
| `CategorySelector.tsx` uses the named-import form | `__tests__/components/CategorySelector.test.tsx:76-86` (green, 12/12 with DirectionalIcon) |
| `DirectionalIcon` renders a barrel icon through the mock | `__tests__/primitives/DirectionalIcon.test.tsx:18` (green) |

---

## 7. Gates

Client only; there is no backend half (no pytest, no ruff, no comm gate).

1. Red-first: R1–R4 fail for the stated reasons before the helper exists.
2. Unit suites: `node node_modules/jest/bin/jest.js --ci __tests__/babel.lucideIcons.b1.test.ts __tests__/helpers/lucideFence.test.ts`.
3. Neighbours (every suite that names lucide or the mock; measured by
   `grep -rln "lucide" __tests__ __mocks__`): `__tests__/components/CategorySelector.test.tsx`,
   `__tests__/primitives/DirectionalIcon.test.tsx` — baseline **2 suites / 12 tests green** at
   ed75dc70. Every screen suite consumes the mock transitively, which is why the full suite
   runs once in the green phase (baseline 2,729 passed / 0 failed / 278 suites at ece0fbbe).
4. `node node_modules/typescript/bin/tsc --noEmit` — baseline **exit 0** (6.3 s; `tsc -v` =
   Version 5.9.3, package.json pin `~5.9.2`).
5. `node node_modules/eslint/bin/eslint.js <touched test files>` — the CI step lints `src/**`
   only, so lint the test files locally; baseline on `App.tsx src/screens/HomeScreen.tsx
   src/components/ImageSlotRow.tsx` = 0 errors / 4 warnings (pre-existing `no-unused-vars`,
   `import/no-duplicates`).
6. Git status empty except the intended test files; no `package.json`/lockfile/`node_modules`
   change.

---

## 8. What this unit CANNOT do / Ahmed dependencies / device-only

* **The phones still ship 1,703 icons.** The `preview` channel is from `97b5f15` (2026-09-02);
  B1 merged 2026-09-07. Only Ahmed's `eas update --branch preview --clear-cache` from main
  changes that. `--clear-cache` is REQUIRED on the first publish after `8d8b9dc8` ("run the
  first eas update / expo export after this lands with --clear-cache / -c; the key handles
  every change after that") — without it a box with a pre-B1 `%TEMP%\metro-cache` re-emits the
  old bundle (`8d8b9dc8` measured exactly this). Ahmed dependency #1.
* **Before/after `expo export` measurement — do NOT run it in this worktree.** Feasible offline
  in principle: `@expo/cli` 54.0.24 honours `EXPO_OFFLINE=1` (`build/src/utils/env.js:47-48`
  "Disable all network requests"), the only `fetch` under `build/src/export/` is in
  `exportStaticAsync.js` (web static export), and Hermes is local
  (`node_modules/react-native/sdks/hermesc/win64-bin/hermesc.exe` present). Command would be
  `EXPO_OFFLINE=1 EXPO_NO_TELEMETRY=1 node node_modules/@expo/cli/build/bin/cli export
  --platform ios -c --output-dir <scratchpad>`. But **here** `SmartCompareApp/node_modules` is
  a junction whose realpath is `C:\Users\SynAckITPC\Documents\AI\sc-scraper-proof\SmartCompareApp\node_modules`
  (measured, `fs.realpathSync`), Metro's resolver already returns those realpaths (probe 3
  output shows `../../sc-scraper-proof/...`), the default config has `watchFolders: []`, and
  `sc-scraper-proof` is off-limits — so a bundle from this worktree may fail on
  outside-project-root files or silently transform another tree's copy of the package.
  Also, a "before" needs the pre-B1 `babel.config.js`, i.e. a checkout, which this batch
  forbids. Use the numbers already recorded in `e3d9adb5`/`8d8b9dc8` (and reproduced at merge
  per CLAUDE.md:494); a fresh re-measurement is an EAS/Ahmed step, or a session with a
  non-junction install.
* **Only a device can verify** the cold-start effect the verifier attributed to eager factory
  execution (1,706 requires before React mounts). The module-count drop is measured; the
  wall-clock startup gain is not, and cannot be from here.
* **No package change is possible from this unit** (`package.json`/lockfile frozen, `npm ci`
  forbidden). If the campaign ever wants source-level per-icon imports instead of the babel
  rewrite, that needs a lucide release exposing `./icons/*` in `exports` (Ahmed dependency,
  not recommended: the babel path already yields the same 68-module graph).

---

## 9. PR-body facts (only if the optional test-only hardening ships)

1. "W3-9 / MB-STARTUP-BUNDLE-01 is already fixed on main by B1 (`e3d9adb5`, `8d8b9dc8`,
   `cea9effa`; PR #138, merged 2026-09-07): 35 barrel importers (34 under `src/` + `App.tsx`)
   are rewritten at compile time to 68 per-icon files; measured 8,259,431 → 6,510,149 B iOS
   Hermes (−1,749,282 B, −21.18%), 3,832 → 2,192 modules (−1,640). This PR changes no source
   and no bundle."
2. "The plan's eslint `no-restricted-imports` ban on the barrel is NOT taken: the bare barrel
   is the only import form Metro 0.83.3, jest 29.7.0 and tsc 5.9.3 all resolve (table in the
   spec); banning it would forbid the shipped design, and CI's eslint step lints `src/**`
   only, not `App.tsx`."
3. "The plan's `< 100 icon modules` source-map assertion is NOT taken: CI has no bundle step;
   the static equivalent is 68 distinct icon files emitted over 151 sources (probe), and the
   existing barrel fence is the CI-durable guard."
4. "This PR closes two holes in that fence: `require('lucide-react-native')`, dynamic
   `import('lucide-react-native')`, `import x = require(...)`, and `.js/.jsx/.mjs/.cjs` sources
   under `src/` were invisible to it (it read only top-level `import`/`export` statements in
   `.ts/.tsx`). Zero such sites exist today; any one of them would re-add all 1,703 icon
   modules with CI green."
5. "Correction to B1's comments: Metro does NOT block the unexported `dist/esm/icons/*.mjs`
   subpath — `metro-resolver` 0.83.3 warns and falls back to file resolution (measured); jest
   and tsc do refuse it. The design is unchanged; the comment is."
6. "Phones are still on the pre-B1 bundle (`preview` from `97b5f15`); the next
   `eas update --branch preview` must pass `--clear-cache` (P-B1-CACHE)."
7. Gates: b1 suite 7/7 + new self-test N/N; neighbours CategorySelector + DirectionalIcon
   12/12; full jest <count> / 0 failed; tsc 0; eslint 0 errors on touched files.

---

## 10. Measurements run (command → observed output)

Versions: `node node_modules/typescript/bin/tsc -v` → `Version 5.9.3` (pin `~5.9.2`).
Installed: lucide-react-native **1.14.0** (package.json `^1.7.0`, lockfile `^1.7.0` range at
`package-lock.json:41`); metro 0.83.3; metro-resolver 0.83.3; expo 54.0.34; @expo/cli 54.0.24;
@expo/metro-config 54.0.15; babel-preset-expo 54.0.10; @babel/core 7.29.0; jest 29.7.0;
ts-jest 29.4.9; eslint 9.39.4; eslint-config-expo 55.0.1; react-native-svg 15.15.5. Node 24.11.1.

**M1 — lucide package layout.** `cat node_modules/lucide-react-native/package.json` → `exports`
has exactly `"."` (import → `dist/esm/lucide-react-native.mjs`, require → `dist/cjs/...js`)
and `"./icons"` (→ `dist/esm/icons/index.mjs`); `"react-native": "dist/esm/lucide-react-native.mjs"`;
`sideEffects: false`. `ls dist/esm/icons | wc -l` → 3408; `grep -c "from './icons/"
dist/esm/lucide-react-native.mjs` → 1703; `grep -c "^export" dist/esm/icons/index.mjs` → 1703.
`cat dist/esm/icons/camera.mjs` → `import createLucideIcon from '../createLucideIcon.mjs'; const
Camera = createLucideIcon("Camera", [...]); export { Camera as default };`.

**M2 — barrel importers at ed75dc70.** `grep -rlE "from ['\"]lucide-react-native['\"]" src
App.tsx | wc -l` → **35**. Non-import mentions of the package under `src/` are comments only.

**Probe 1 — `scratchpad/b5/W3-9/count_icons.js`** (AST over `src/**/*.ts(x)` + `App.tsx` +
`index.ts`, map from `babel.config.js`'s `buildLucideIconMap()`):
```
sourceFilesScanned: 151, barrelImporterFiles: 35, specifierShapes: { value: 136 },
distinctValueNames: 68, distinctIconFilesEmitted: 68, unmappedNames: [], mapSize: 5844
iconFiles: arrow-left, at-sign, award, battery, bell, brush, camera, chart-column, check,
chef-hat, chevron-down, chevron-left, chevron-right, chevron-up, circle-alert,
circle-question-mark, clock, coins, copy, cpu, dollar-sign, ellipsis, external-link, flower,
gem, gift, hammer, hard-drive, heart-pulse, heart, house, image, info, leaf, list-checks, lock,
mail, message-circle, minus, monitor, mountain, mouse-pointer-click, music, package, palette,
pill, plane, plus, rotate-ccw, scissors, search, send, settings, share-2, shield-check, shield,
shopping-bag, shopping-cart, smartphone, sparkles, star, trash-2, trending-up, trophy, user,
users, x, zap  (.mjs)
```

**Probe 2 — existing suite.** `node node_modules/jest/bin/jest.js --ci
__tests__/babel.lucideIcons.b1.test.ts` → `PASS`, 7 passed / 7 (8.6 s). Output quoted in §3.

**Probe 3 — Metro resolver, `scratchpad/b5/W3-9/metro_resolve.js`** (metro-resolver 0.83.3
`resolve()` with the project's `expo/metro-config` resolver settings — measured:
`unstable_enablePackageExports: true`, `unstable_conditionNames: []`,
`unstable_conditionsByPlatform.ios: ["react-native"]`, `resolverMainFields:
["react-native","browser","main"]`, `sourceExts: [ts,tsx,mjs,js,jsx,json,cjs,scss,sass,css]`,
`watchFolders: []`, `projectRoot: "."`; origin `src/screens/HomeScreen.tsx`, platform ios,
ESM import):
```
bare barrel: RESOLVED -> ../../sc-scraper-proof/SmartCompareApp/node_modules/lucide-react-native/dist/esm/lucide-react-native.mjs
exports subpath ./icons: RESOLVED -> .../dist/esm/icons/index.mjs
unlisted subpath icons/camera: THROWS FailedToResolveNameError: Module does not exist in the Haste module map or in these directories:
    warning: Attempted to import the module ".../lucide-react-native/icons/camera" which is not listed in the "exports" of ...
unlisted subpath dist/esm/icons/camera.mjs: RESOLVED -> .../dist/esm/icons/camera.mjs
    warning: Attempted to import the module ".../dist/esm/icons/camera.mjs" which is not listed in the "exports" of ...
unlisted subpath dist/esm/icons/camera (no ext): RESOLVED -> .../dist/esm/icons/camera.mjs   (+ same warning)
relative file (what the B1 plugin emits): RESOLVED -> .../dist/esm/icons/camera.mjs
```
Fallback source: `node_modules/metro-resolver/src/resolve.js:343-349` —
`if (e instanceof _PackagePathNotExportedError.default) { context.unstable_logWarning(e.message
+ " Falling back to file-based resolution. ..."); }` then `return resolveModulePath(...)`.

**Probe 4 — jest resolver, `.qa-w3b/probes/lucideDeepImport.probe.test.ts`** run with
`node node_modules/jest/bin/jest.js --ci --config ../.qa-w3b/probes/jest.probe.config.js
../.qa-w3b/probes/lucideDeepImport.probe.test.ts` (the override spreads the real
`jest.config.js`, pins `rootDir` to `SmartCompareApp` so every `<rootDir>/__mocks__` mapper and
`__tests__/setup.ts` still apply, and adds `.qa-w3b/probes/**/*.probe.test.ts` to
`roots`/`testMatch` — the default `testMatch` is `**/__tests__/**` under `rootDir` and would not
see it):
```
bare barrel (mapped): RESOLVED keys=79 sample=ArrowLeft,Search,Camera,History,User default=undefined
exports subpath ./icons: THROWS MODULE_NOT_FOUND Cannot find module 'lucide-react-native/icons'
unlisted subpath icons/camera: THROWS MODULE_NOT_FOUND
unlisted subpath dist/esm/icons/camera.mjs: THROWS MODULE_NOT_FOUND
unlisted subpath dist/cjs/icons/camera.js: THROWS MODULE_NOT_FOUND
relative file dist/esm/icons/camera.mjs: THROWS Cannot use import statement outside a module
relative file dist/cjs/icons/camera.js: RESOLVED keys=2 sample=$$typeof,render default=undefined
```
(The CJS relative file loads under jest but is useless: tsc has no declaration for it and the
plugin emits ESM paths; noted for completeness.)

**Probe 5 — TypeScript resolver, `scratchpad/b5/W3-9/tsc_resolve.js`** (`ts.resolveModuleName`
from `src/screens/HomeScreen.tsx` under `moduleResolution: Bundler`, `customConditions:
["react-native"]`, `module: Preserve`, `allowJs` — the effective options from
`expo/tsconfig.base.json` which `tsconfig.json` extends):
```
lucide-react-native -> RESOLVED .../dist/lucide-react-native.d.ts ext=.d.ts external=true
lucide-react-native/icons -> RESOLVED .../dist/icons.d.ts ext=.d.ts external=true
lucide-react-native/icons/camera -> UNRESOLVED (failedLookupLocations=152)
lucide-react-native/dist/esm/icons/camera.mjs -> UNRESOLVED (failedLookupLocations=185)
lucide-react-native/dist/esm/icons/camera -> UNRESOLVED (failedLookupLocations=152)
../../node_modules/lucide-react-native/dist/esm/icons/camera.mjs -> RESOLVED node_modules/lucide-react-native/dist/esm/icons/camera.mjs ext=.mjs external=true
typescript 5.9.3
```

**M3 — no transform-imports plugin installed.** `ls node_modules | grep -iE
'transform-imports|babel-plugin-import|modularize'` → empty (exit 1).

**M4 — CI wiring.** `.github/workflows/ci.yml` frontend-tests: `npm ci` (`:260`) → `npx jest --ci`
(`:264`) → `npx eslint "src/**/*.{ts,tsx}"` (`:270`) → `npx tsc --noEmit` (`:274`; the
frontend-typecheck job repeats it at `:223`). No bundle/export step. `eslint.config.js`
has no `no-restricted-imports`; `eslint-config-expo` 55.0.1 contains none either (grep empty).

**M5 — gates baseline.** `tsc --noEmit` → exit 0 (6.3 s). eslint on `App.tsx`,
`src/screens/HomeScreen.tsx`, `src/components/ImageSlotRow.tsx` → 0 errors / 4 warnings, exit 0.
Neighbour suites `CategorySelector.test.tsx` + `DirectionalIcon.test.tsx` → 2 passed / 12 tests.

**M6 — junction + export feasibility.** `fs.realpathSync('node_modules')` →
`C:\Users\SynAckITPC\Documents\AI\sc-scraper-proof\SmartCompareApp\node_modules`;
`@expo/cli/build/bin/cli` present; `env.js:47-48` `EXPO_OFFLINE` "Disable all network
requests"; `grep -rln fetch build/src/export/*.js` → `exportStaticAsync.js` only;
`react-native/sdks/hermesc/win64-bin/hermesc.exe` present. `expo export` was NOT run.

**M7 — fence holes.** `grep -rnE "require\(['\"]lucide|import\(['\"]lucide|= require\(['\"]lucide"
src App.tsx index.ts __tests__ __mocks__` → only `__tests__/babel.lucideIcons.b1.test.ts:327`
(the mock require inside the suite). `find src -type f ! -name "*.ts" ! -name "*.tsx"` →
`src/i18n/.copy-policy.json`, `src/i18n/ar.json`, `src/i18n/en.json` (no `.js`/`.jsx`).

**M8 — git.** `git status --short` at the end of measurement → empty (`git check-ignore -v`
confirms `.gitignore:72` `.qa-*/` covers the spec and both probe files; the other probes live
in the scratchpad). `require.resolve('@babel/traverse')` → resolvable, 7.29.0.

**Anchor discipline:** every `babel.config.js` / `metro.config.js` / `jest.config.js` / `ci.yml`
line number above was re-checked with `grep -n` after a first pass cited them from un-numbered
output (four were off by 1–17 lines and are corrected here); the b1-suite, `App.tsx`,
`resolve.js` and `env.js` anchors came from numbered output directly.

Probe files: `.qa-w3b/probes/jest.probe.config.js`, `.qa-w3b/probes/lucideDeepImport.probe.test.ts`,
`scratchpad/b5/W3-9/{count_icons.js,metro_resolve.js,tsc_resolve.js}`.

---

## FABLE REVIEW RULINGS (binding, 2026-09-11)

Verdict: **APPROVED_WITH_RULINGS**. Re-measured at `ed75dc708b82c0b911c9de8a3e59d4418c6e278c`,
`git status --short` empty before and after. Every load-bearing claim in sections 2, 3, 5 and 10
reproduces on the installed versions (list at the end). Four factual defects and two test-design
defects follow; each ruling states the correction and the evidence. The red phase reads this file
once — everything binding is here.

**R-1. Scope and disposition (DECIDED — do not ask).** The defect is fixed on main:
`git merge-base --is-ancestor` confirms `e3d9adb5`, `8d8b9dc8` and `cea9effa` are all ancestors of
HEAD; `git show --stat` of the three = `babel.config.js` (+162), `__tests__/babel.lucideIcons.b1.test.ts`,
`metro.config.js`, `metro.cacheVersion.js`, `__tests__/metro.cacheVersion.pb1.test.ts`,
`__mocks__/lucide-react-native.ts`. Both plan red tests are correctly DROPPED for the measured reasons
(the bare barrel is the only form Metro 0.83.3 + jest 29.7.0 + tsc 5.9.3 all resolve — probes 3/4/5
re-run identically; `ci.yml:260/264/270/274` has no bundle step; `eslint.config.js` and
`eslint-config-expo` 55.0.1 carry no `no-restricted-imports`). The importer-count test exists at
`:294-295`. **The red phase EXECUTES the test-only hardening R1–R6 as amended below.** Reason it is
not decoration: under Metro a `require('lucide-react-native')` resolves to a full barrel under EITHER
exports condition (`dist/cjs/lucide-react-native.js` carries 1,703 `require('./icons/…')`, measured,
same as the ESM barrel's 1,703), a dynamic `import()` likewise, the plugin visits `ImportDeclaration`
only (`babel.config.js:130`), and CI's only reaction is a non-blocking eslint warning (R-4). If the
orchestrator prefers to close the unit as already-green instead, nothing in this spec needs to
change — but a red phase that runs, runs R1–R6.

**R-2. `SmartCompareApp/__tests__/helpers/` is NOT new.** It exists at HEAD with one file,
`w312BootSandbox.ts` (9,529 B), imported by `__tests__/bootSentryAlarm.w312.test.ts` and
`__tests__/bootSentryOrder.w312.test.ts`. Only the two FILES `helpers/lucideFence.ts` and
`helpers/lucideFence.test.ts` are new (no `*lucideFence*` exists anywhere under `__tests__/`).
Consequences: (a) `jest.config.js:4` `testMatch` is `**/__tests__/**/*.test.ts(x)`, so a helper
without `.test.` is never collected — keep that naming; (b) `tsconfig.json` has NO `include`, so
`node node_modules/typescript/bin/tsc --noEmit` typechecks `__tests__/**` including helpers under
`strict: true` (tsc is exit 0 today WITH `w312BootSandbox.ts` present, 9.4 s wall here) — the new
helper must pass strict; (c) do not touch `w312BootSandbox.ts`.

**R-3. `@babel/traverse` is a namespace object; the walker is `.default`.** Measured:
`typeof require('@babel/traverse') === 'object'`, `typeof require('@babel/traverse').default ===
'function'` (7.29.0, resolvable from the app root, transitive via `@babel/core`, `NOT DIRECT` in
`package.json`). Section 4's "import it via require the way the suite already requires `@babel/core`"
is incomplete: `const traverse = require('@babel/traverse').default;`. The hand-rolled walk stays the
permitted alternative (no new package either way). Every `require(...)` in a test file draws
`@typescript-eslint/no-require-imports` as a WARNING (b1 suite baseline: 6 warnings incl. 3 of these +
3 `array-type`, 0 errors; `metro.cacheVersion.pb1.test.ts`: 4 warnings, 0 errors; exit 0) — gate 5 is
0 ERRORS on touched files; warnings are baseline behaviour, an `// eslint-disable-next-line
@typescript-eslint/no-require-imports` as at `:326` is optional.

**R-4. "Silently … with every CI check green" is overstated for R1/R3 — CI eslint WARNS.** Measured via
`eslint --stdin --stdin-filename src/probeR1.ts` (no file written): `const L =
require('lucide-react-native')` → `1:11 warning A require() style import is forbidden
@typescript-eslint/no-require-imports`, exit 0; `import L = require('lucide-react-native')` → same
warning at `1:12`, exit 0; the same warning fires for a root-level file. `export async function f(){
return import('lucide-react-native'); }` → NO diagnostic, exit 0; `import x from
'lucide-react-native/icons'` → NO diagnostic, exit 0. CI runs `npx eslint "src/**/*.{ts,tsx}"` with
no `--max-warnings`, so the job stays GREEN in every case — the claim's conclusion holds (all five
required checks green), but the spec and the PR body must say "CI eslint emits a non-blocking
warning for the two `require` shapes and nothing for dynamic `import()` or a subpath", not
"silently". Section 9 item 4 is amended accordingly.

**R-5. AST shapes, measured on the installed `@babel/parser` 7.29.3 with `plugins:
['typescript','jsx']` (probe `scratchpad/b5/W3-9/review/ast_shapes.js`, which also runs a verbatim
copy of the b1 classifier `:135-172`):**
* R1 `const L = require('lucide-react-native');` → top-level `VariableDeclaration`, `init:
  CallExpression`, `callee: Identifier 'require'`, `arguments[0]: StringLiteral`. b1 classifier → `[]`.
* R2 `export async function f(){ return import('lucide-react-native'); }` → the call is
  `CallExpression` with `callee.type === 'Import'` and the specifier in `arguments[0]`; it becomes
  `ImportExpression` (specifier in `.source`) ONLY when the parser is given
  `createImportExpressions: true`. The helper MUST handle both node types and read the literal from
  the right field for each. b1 classifier → `[]`.
* R3 `import L = require('lucide-react-native');` → top-level `TSImportEqualsDeclaration`,
  `moduleReference.type === 'TSExternalModuleReference'`, `.expression: StringLiteral`,
  `importKind: 'value'`, `node.source === undefined`. b1 classifier → `[]`.
* R5 controls reproduce today's shapes (`ImportSpecifier` ×2 for value+type, `ImportNamespaceSpecifier`,
  `re-export` for `export * from`, `subpath`).
So R1–R4 are RED today for the stated reason (helper absent; the logic it is extracted from reads only
`node.source` on `ast.program.body`). **Amendment to R3:** `import type L = require('lucide-react-native')`
parses with `importKind: 'type'` and is erased by TS — classify it `'type'`, not `'require'`, and pin
that as a second R3 case; otherwise the fence at `:257` would redden on a form that costs no bytes.

**R-6. R6 must assert BOUNDS, not the exact 151 / 136 / 35.** An assertion of `=== 136` value refs or
`=== 35` importers reddens on every icon added or removed — a maintenance trap, not a fence, and the
existing suite deliberately pins `> 50` (`:252`) and `>= 30` (`:295`). R6 is: `sourceFiles(realRoot).length
>= 150`; value refs `> 50`; distinct importer files `>= 30`; non-`value`/`type` shapes `toEqual([])`.
Record 151 / 136 / 35 / 68 as a dated comment only. Mutation for R6 stays "replace the walk with `[]`".

**R-7. R4 temp-dir discipline.** Create with `fs.mkdtempSync(path.join(os.tmpdir(), 'lucide-fence-'))`
— never a path under the worktree — and remove exactly that path with `fs.rmSync(dir, { recursive:
true, force: true })` in `afterAll`/`finally`. `sourceFiles(root)` takes the root as a parameter with
today's `src` + `App.tsx` + `index.ts` behaviour preserved for the real tree. Note that the current
`/\.tsx?$/` already sweeps `src/types/react-test-renderer.d.ts` (the only `.d.ts` under `src/`) and
the suite is green, so the widened `/\.(tsx?|jsx?|mjs|cjs)$/` keeps that behaviour — no `.d.ts`
exclusion is added. Also measured: no `.js/.jsx/.mjs/.cjs` under `src/` (only `src/i18n/*.json`), and
the root-level `.js` files (`babel.config.js`, `eslint.config.js`, `jest.config.js`,
`metro.cacheVersion.js`, `metro.config.js`) are config, not walked — the walk stays rooted at `src/`
plus the two entry files, exactly as today.

**R-8. Anchor corrections (each re-located at HEAD).**
* `metro-resolver/src/resolve.js`: the `PackagePathNotExportedError` catch + warning is `:343-351`; the
  file-based fallback `return resolveModulePath(context, absoluteCandidatePath, platform)` is `:359`
  (spec said `:343-349`).
* Section 8 / M6 "the only `fetch` under `build/src/export/` is `exportStaticAsync.js`" is WRONG:
  `grep -rln fetch node_modules/@expo/cli/build/src/export/*.js` matches NOTHING; recursively the sole
  hit is a CLI help string at `export/embed/index.js:131` ("Try to fetch transformed JS code from the
  global cache"), on the `export:embed` path, not `expo export`. The offline-feasibility conclusion is
  unchanged (stronger); `EXPO_OFFLINE` at `utils/env.js:47-48` and `hermesc.exe` verified. `expo
  export` was NOT run and MUST NOT be run in this worktree (junction realpath
  `sc-scraper-proof/SmartCompareApp/node_modules` re-measured; `watchFolders: []`).
* `docs/investigations/2026-09-06-full-review-verified.json:12081-12140` carries the pre-B1
  1,212,812 B / 23.96 % figure; it does NOT carry 3,832 / 2,192 / 1,749,282 — those live only in
  `e3d9adb5`'s body, `CLAUDE.md:494` and `docs/CONTEXT_SESSION_LOG.md:12`. The 5,299,992 (iOS) /
  8,285,250 (Android) hbc figures are at `verified.json:1574`, `:12453`, `:12481` and
  `CONTEXT_SESSION_LOG.md:12`, which itself flags `e3d9adb5`'s "iOS" label as unreconciled. No unit
  action; the module-count drop is the platform-independent fact.
* Finding row `2026-09-06-full-review-tables.md:69` cites `App.tsx:18`; at HEAD the import is `App.tsx:19`
  (confirmed). `babel.config.js:47`, `b1.test.ts:4` and `:294` say "34"; the true count is 35 files
  (34 under `src/` + `App.tsx`; `grep -rlE "from ['\"]lucide-react-native['\"]" src App.tsx index.ts | wc -l`
  → 35, `src` alone → 34). The test-file comments at `:4`/`:294` MAY be corrected to "35 (34 under
  src/ + App.tsx)"; **`babel.config.js:47` is SOURCE and is NOT touched by this unit.**

**R-9. Which comments the unit edits in `babel.lucideIcons.b1.test.ts`.** Section 4 item 2 says
"header item 5"; the statements that are wrong for Metro are the header preamble `:10-14` ("neither
`lucide-react-native/icons/<kebab>` nor `…/dist/esm/icons/<kebab>.mjs` resolves" — the first throws
`FailedToResolveNameError` under Metro, the second RESOLVES with a warning and file-based fallback;
jest → `MODULE_NOT_FOUND` for both, tsc → UNRESOLVED for both) and the inline comment `:140-142`
("blocked by the package's exports map at runtime"). Edit those two; header item 5 (`:31-40`) only
gains the sentence that `require()` / dynamic `import()` / `import x = require()` and `.js/.jsx/.mjs/.cjs`
sources are now fenced too. Item 6 (`:41-45`), the mock fence, is untouched.

**R-10. Live Metro settings, read from `require('./metro.config.js')` (not from docs):** `sourceExts
["ts","tsx","mjs","js","jsx","json","cjs","scss","sass","css"]`, `watchFolders []`,
`unstable_enablePackageExports true`, `unstable_conditionNames []`, `unstable_conditionsByPlatform
{ios:["react-native"], android:["react-native"], web:["browser"]}`, `resolverMainFields
["react-native","browser","main"]`, `cacheVersion "1.0-qaren1-7a818df450cba3bf"`. Section 10 probe-3
settings are confirmed.

**R-11. Files the red phase may create/edit — unchanged from section 4, restated as the whole list:**
`SmartCompareApp/__tests__/helpers/lucideFence.ts` (new), `SmartCompareApp/__tests__/helpers/lucideFence.test.ts`
(new), `SmartCompareApp/__tests__/babel.lucideIcons.b1.test.ts` (import the helper; comment edits per
R-9). NOTHING under `src/`, `App.tsx`, `index.ts`, `babel.config.js`, `metro.config.js`,
`metro.cacheVersion.js`, `jest.config.js`, `__mocks__/`, `package.json`, the lockfile, `node_modules`
(a junction into `sc-scraper-proof` — never delete, never install), `__tests__/helpers/w312BootSandbox.ts`.
Client tools by path only (`node node_modules/typescript/bin/tsc`, `node node_modules/jest/bin/jest.js --ci`,
`node node_modules/eslint/bin/eslint.js`; `tsc -v` = 5.9.3, pin `~5.9.2`). No `expo export`, no
`eas`, no network.

**R-12. Gates with the baselines measured in THIS review (supersede section 7's timings):**
1. Red-first: R1–R4 fail before the helper exists (R-5 gives the reason per case); R5/R6 green pins,
   each with its named mutation confirmed to redden before commit (campaign rule: a test that
   survives removal of its fix is decoration).
2. `node node_modules/jest/bin/jest.js --ci __tests__/babel.lucideIcons.b1.test.ts
   __tests__/helpers/lucideFence.test.ts` — b1 baseline 7/7 PASS (3.0 s here).
3. Neighbours `__tests__/components/CategorySelector.test.tsx __tests__/primitives/DirectionalIcon.test.tsx`
   — baseline 2 suites / 12 tests PASS. Full suite once in the green phase (2,729 / 0 / 278 at ece0fbbe).
4. `node node_modules/typescript/bin/tsc --noEmit` — baseline exit 0 (9.4 s wall).
5. `node node_modules/eslint/bin/eslint.js <the three touched test files>` — baseline on
   `babel.lucideIcons.b1.test.ts` = 6 warnings / 0 errors; gate is 0 errors. (Source-file baseline
   `App.tsx src/screens/HomeScreen.tsx src/components/ImageSlotRow.tsx` = 0 errors / 4 warnings, exit 0.)
6. `git status --short` shows only the three test files; `.qa-w3b/` stays gitignored (`.gitignore:72`).

**R-13. Ahmed dependencies stand as written in section 8** (the `--clear-cache` OTA from main is the
only lever that changes phones; a fresh before/after `expo export` is not a step for this worktree;
startup wall-clock is device-only; no package change). Nothing in this unit is flagged, gated, or
device-visible; OTA class `ci-only` is confirmed.

**Measurements run for this review (command → observed):** `git rev-parse HEAD` → ed75dc70…;
`git merge-base --is-ancestor` ×3 → all ancestors; `git show -s/--stat` e3d9adb5/8d8b9dc8/cea9effa;
`cat -n babel.config.js` (plugin :126-181, map :95-124, wiring :199-201, visitor :130, comment :44-77),
`metro.config.js:15`, `jest.config.js:4/:5/:20`; `cat -n babel.lucideIcons.b1.test.ts` (:90-104, :97,
:135-172, :140-142, :241-269, :252, :257, :294-295, :326-327); `tsc -v` → 5.9.3; installed versions
(lucide-react-native 1.14.0 read by path — its `exports` blocks `require('…/package.json')` —,
metro/metro-resolver 0.83.3, expo 54.0.34, @expo/cli 54.0.24, @expo/metro-config 54.0.15,
babel-preset-expo 54.0.10, @babel/core 7.29.0, @babel/traverse 7.29.0, @babel/parser 7.29.3, jest
29.7.0, ts-jest 29.4.9, eslint 9.39.4, eslint-config-expo 55.0.1, react-native-svg 15.15.5, Node
24.11.1); lucide `exports` = `.` + `./icons` only, `react-native` field → `dist/esm/lucide-react-native.mjs`,
`sideEffects false`; `ls dist/esm/icons | wc -l` → 3408 (1,704 `.mjs`); ESM barrel 1,703 icon re-exports,
`icons/index.mjs` 1,703 exports, CJS barrel 1,703 icon requires; no `camera.d.mts`/`.d.ts` beside
`camera.mjs`; importer count 35 (`src` 34) + `App.tsx:19` quoted; zero `require(`/`import(` lucide sites
outside `b1.test.ts:327`; only `src/i18n/*.json` non-TS under `src/`; `ls node_modules | grep -iE
'transform-imports|babel-plugin-import|modularize'` → empty; `ci.yml:214/223/260/264/270/274`; no
`no-restricted-imports` anywhere; `eslint.config.js` read in full; probe 1 `count_icons.js` → 151 / 35 /
`{value:136}` / 68 / 68 / `unmappedNames []` / mapSize 5844; probe 2 b1 suite → 7/7 PASS; probe 3
`metro_resolve.js` → identical table; probe 4 `lucideDeepImport.probe.test.ts` via
`--config ../.qa-w3b/probes/jest.probe.config.js` → identical seven lines (mock keys 79); probe 5
`tsc_resolve.js` → identical six lines; live Metro config (R-10); AST probe `review/ast_shapes.js` (R-5);
eslint `--stdin` probes ×5 (R-4); eslint on b1 + metro suites → 10 warnings / 0 errors; neighbours
2/12 PASS; `tsc --noEmit` exit 0; `fs.realpathSync('node_modules')` → sc-scraper-proof; `@expo/cli`
`env.js:47-48`, `export/` listing, recursive fetch grep (R-8); `hermesc.exe` present; `tsconfig.json`
+ `expo/tsconfig.base.json` (`allowJs`, `bundler`, `customConditions ["react-native"]`, `module
preserve`, no `include`); `package.json` `main: index.ts`; `__tests__/helpers/` listing (R-2);
`@babel/traverse` export shape (R-3); doc anchors `full-review.md:136`, `tables.md:69`,
`verified.json:1574/:12081/:12453/:12481`, `2026-09-02-mobile-checkup-findings.md:145-146`,
`CLAUDE.md:494`, `CONTEXT_SESSION_LOG.md:12`; `git check-ignore -v` → `.gitignore:72 .qa-*/`;
`git status --short` → empty at start and end. Review probe: `scratchpad/b5/W3-9/review/ast_shapes.js`.
