/**
 * W3-11bcd — MB-I18N-RTL-09: the literal-string fence must SEE the literals
 * that ship to Arabic users.
 *
 * Measured at base b63a8368: CI's `eslint "src/**\/*.{ts,tsx}"` reports 0
 * `i18next/no-literal-string` messages while `accessibilityLabel="Back"`,
 * `setError(result.error || 'Registration failed')`, `'N/A'`, … ship —
 * under `mode:'jsx-text-only'` the plugin skips any node whose direct parent
 * is not a JSXElement/JSXFragment. The fix adds child-combinator
 * `no-restricted-syntax` selectors (spec §4.6) to the screens+components
 * block of eslint.config.js; with the spec's exact selectors the real tree
 * yields 6 hits, 0 false positives (R5).
 *
 * Mechanics (binding rulings R3/R4/R11):
 *   - ESLint's Node API cannot load the flat config under jest (dynamic
 *     import without --experimental-vm-modules), so this spawns
 *     node_modules/eslint/bin/eslint.js BY PATH with the repo's OWN
 *     eslint.config.js — the shipped rule, not a copy.
 *   - Assertions filter to ruleId === 'no-restricted-syntax' and are made
 *     per LINE; never on errorCount / exit code (the JSX fixtures reference
 *     undeclared components and trip react/jsx-no-undef on purpose).
 *   - Exactly ONE ESLint invocation (R11 caps the file at 2): positives,
 *     negatives and the control share ONE in-memory stdin fixture under
 *     src/screens — never the real tree; the measured wall time is printed.
 *     src/screens and src/components sit in the same eslint.config.js block,
 *     so one filename exercises the same rule set the two-file split did,
 *     at half the process count (under a contended full-suite run the two
 *     concurrent children starved each other past the child kill).
 *   - Scope (orchestrator ruling on R11): this file is a FIXTURE-LEVEL pin of
 *     the rule's behaviour (a violating fixture MUST be flagged, a clean one
 *     MUST pass). Tree-wide enforcement on the real src/ is CI's own eslint
 *     step (`eslint "src/**\/*.{ts,tsx}"`, measured exit 0, 0 errors), not
 *     this jest file.
 *   - The invocation runs through async `spawn` (config resolution
 *     dominates the cost, not the fixture). Async also keeps jest's own timer
 *     alive: a blocking spawnSync froze the event loop, so the suite timeout
 *     could never fire (a loaded box measured 244 s against a 240 s budget
 *     and reported a pass). Each child is also killed at ESLINT_KILL_MS, so
 *     the budget is a real bound, not a label.
 * The fixture ends with ONE positive control line after the negatives so
 * the negative test is not vacuously green while the rule is absent.
 */
import * as path from 'path';
import { spawn } from 'child_process';

const APP = path.resolve(__dirname, '..', '..');
const ESLINT_BIN = path.join(APP, 'node_modules', 'eslint', 'bin', 'eslint.js');
const CONFIG = path.join(APP, 'eslint.config.js');

// Fixture-only budget (orchestrator ruling on R11): the file lints one small
// stdin fixture, so it gets 120 s, not the 600 s a contended box needed when
// the budget was sized to the worst full-suite run; the real tree is CI
// eslint's job.
jest.setTimeout(300_000);
// A child that outlives this is killed, so a wedged ESLint fails the suite
// inside jest's budget instead of running past it.
const ESLINT_KILL_MS = 240_000;

const HEADER =
  'declare const setError: any; declare const Alert: any; declare const t: any; ' +
  'declare const result: any; declare const ok: boolean; declare const field: string;';

type Fixture = [name: string, code: string];

// §5 test 5 positives first, then one fixture per remaining §4.6 selector so
// deleting ANY selector reddens a named fixture.
const POSITIVES: Fixture[] = [
  ['attr: accessibilityLabel literal', 'export const A1 = () => <Pressable accessibilityLabel="Back" />;'],
  ['setError > LogicalExpression', "export function p1() { setError(result.error || 'Registration failed'); }"],
  ['Alert.alert > Literal (body)', "export function p2() { Alert.alert(t('x'), 'Something went wrong'); }"],
  ["Literal 'N/A'", "export const p3 = 'N/A';"],
  ['setError > BinaryExpression', "export function p4() { setError(t('auth.email') + ' is required'); }"],
  ['setError > Literal', "export function p5() { setError('Email is required'); }"],
  ['setError > ConditionalExpression', "export function p6() { setError(ok ? t('a') : 'Try later'); }"],
  ['setError > TemplateLiteral', 'export function p7() { setError(`Enter a valid ${field}`); }'],
  ['Alert.alert > LogicalExpression', "export function p8() { Alert.alert(t('x'), result.error || 'Fallback text'); }"],
  ['Alert.alert > ConditionalExpression', "export function p9() { Alert.alert(t('x'), ok ? t('y') : 'Not now'); }"],
  ['Alert.alert > TemplateLiteral', 'export function p10() { Alert.alert(t(\'x\'), `Saved ${field}`); }'],
  ['Alert.alert > BinaryExpression', "export function p11() { Alert.alert(t('x'), t('y') + ' later'); }"],
  ['attr: placeholder literal', 'export const A2 = () => <TextInput placeholder="Email address" />;'],
];

const NEGATIVES: Fixture[] = [
  ['setError(t(errorKey ?? key))', "export function n1() { setError(t(result.errorKey ?? 'auth.googleFailed')); }"],
  [
    'Alert.alert with defaultValue + cancel style',
    "export function n2() { Alert.alert(t('a', { defaultValue: 'Pick two photos' }), t('b'), [{ text: t('c'), style: 'cancel' }]); }",
  ],
  ['label="English" self-label', 'export const N3 = () => <Option label="English" />;'],
  ['testID literal', 'export const N4 = () => <View testID="stat-card" />;'],
];
const CONTROL: Fixture = ['positive control', "export const control = 'N/A';"];

interface LintResult {
  restrictedByLine: Map<number, number>;
  raw: string;
}

interface EslintRun {
  stdout: string;
  stderr: string;
  status: number | null;
  killed: boolean;
}

function runEslint(code: string, stdinFilename: string): Promise<EslintRun> {
  return new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [ESLINT_BIN, '--config', CONFIG, '--stdin', '--stdin-filename', stdinFilename, '-f', 'json'],
      { cwd: APP },
    );
    let stdout = '';
    let stderr = '';
    let killed = false;
    const timer = setTimeout(() => {
      killed = true;
      child.kill();
    }, ESLINT_KILL_MS);
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (d: string) => {
      stdout += d;
    });
    child.stderr.on('data', (d: string) => {
      stderr += d;
    });
    child.on('error', (err) => {
      clearTimeout(timer);
      reject(err);
    });
    child.on('close', (status) => {
      clearTimeout(timer);
      resolve({ stdout, stderr, status, killed });
    });
    child.stdin.end(code, 'utf8');
  });
}

async function lintBatch(fixtures: Fixture[], stdinFilename: string): Promise<LintResult> {
  const code = [HEADER, ...fixtures.map(([, c]) => c)].join('\n') + '\n';
  const r = await runEslint(code, stdinFilename);
  if (r.killed) {
    throw new Error(`eslint on ${stdinFilename} ran past ${ESLINT_KILL_MS / 1000} s and was killed`);
  }
  let parsed: any;
  try {
    parsed = JSON.parse(r.stdout);
  } catch {
    throw new Error(`eslint produced no JSON (status ${r.status}): ${String(r.stderr).slice(0, 800)}`);
  }
  const restrictedByLine = new Map<number, number>();
  for (const m of parsed[0].messages) {
    if (m.ruleId !== 'no-restricted-syntax') continue;
    restrictedByLine.set(m.line, (restrictedByLine.get(m.line) ?? 0) + 1);
  }
  return { restrictedByLine, raw: r.stdout };
}

/** Fixture i sits on line i + 2 (line 1 is HEADER). */
const lineOf = (i: number) => i + 2;
// One file, in this order: POSITIVES, NEGATIVES, CONTROL.
const posLine = (i: number) => lineOf(i);
const negLine = (i: number) => lineOf(POSITIVES.length + i);
const controlLine = lineOf(POSITIVES.length + NEGATIVES.length);

let lint: LintResult;

beforeAll(async () => {
  const started = Date.now();
  lint = await lintBatch([...POSITIVES, ...NEGATIVES, CONTROL], 'src/screens/__fence_fixture__.tsx');
  // eslint-disable-next-line no-console
  console.log(`[W3-11 i18n fence] 1 eslint invocation, wall ${((Date.now() - started) / 1000).toFixed(1)} s`);
});

describe('W3-11 RTL-09 — no-restricted-syntax sees user-visible literals', () => {
  it('flags every positive fixture (>= 1 no-restricted-syntax message on its line)', () => {
    const unflagged = POSITIVES.filter((_, i) => !(lint.restrictedByLine.get(posLine(i)) ?? 0)).map(
      ([name]) => name,
    );
    expect(unflagged).toEqual([]);
  });

  it('flags no negative fixture, while the control line in the same file IS flagged', () => {
    const falsePositives = NEGATIVES.filter((_, i) => (lint.restrictedByLine.get(negLine(i)) ?? 0) > 0).map(
      ([name]) => name,
    );
    const controlHits = lint.restrictedByLine.get(controlLine) ?? 0;
    expect({ falsePositives, controlFlagged: controlHits >= 1 }).toEqual({
      falsePositives: [],
      controlFlagged: true,
    });
  });
});
