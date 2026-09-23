/**
 * W3-14 R7 — the Results demographics sheet never renders a raw backend string.
 *
 * `PUT /api/v1/auth/demographics` is `5/minute`, so a raw "Rate limit
 * exceeded. Please try again later." ("try again" = scary_vocab_en) is
 * reachable; so is the axios fall-through "Request failed with status code
 * 502". At b63a8368 `handleDemographicsSubmit`'s catch was:
 *
 *     const { message } = parseApiError(err);
 *     setDemographicsError(message || t('demographics.error.network'));
 *
 * Fix contract (spec §4): `setDemographicsError(t(settingsErrorKey(
 * parseApiError(err).code, 'demographics.error.network')))` — catalog copy
 * only, keyed by code.
 *
 * Source-contract test in the ResultsScreen.networkMatrix.m18 style (a full
 * render needs the Reanimated surface + ~9 service mocks for a 700-line
 * screen). The catch block is extracted by BALANCING braces, and comment
 * lines are dropped first so prose quoting the old code cannot fail the fence.
 */
import * as fs from 'fs';
import * as path from 'path';

const RESULTS = fs.readFileSync(
  path.resolve(__dirname, '../src/screens/ResultsScreen.tsx'),
  'utf8',
);

/** Return the balanced `{...}` block that starts at the first `{` at/after `from`. */
function balancedBlock(src: string, from: number): string {
  const open = src.indexOf('{', from);
  if (open === -1) return '';
  let depth = 0;
  for (let j = open; j < src.length; j += 1) {
    if (src[j] === '{') depth += 1;
    else if (src[j] === '}') {
      depth -= 1;
      if (depth === 0) return src.slice(open, j + 1);
    }
  }
  return '';
}

/** Return the balanced `(...)` argument list that starts at `openParen`. */
function balancedArgs(src: string, openParen: number): string {
  let depth = 0;
  for (let j = openParen; j < src.length; j += 1) {
    if (src[j] === '(') depth += 1;
    else if (src[j] === ')') {
      depth -= 1;
      if (depth === 0) return src.slice(openParen + 1, j);
    }
  }
  return '';
}

const CODE = RESULTS.split('\n')
  .filter((line) => !/^\s*(\/\/|\*|\/\*)/.test(line))
  .join('\n');

const fnStart = CODE.indexOf('const handleDemographicsSubmit');
const fnBody = fnStart === -1 ? '' : balancedBlock(CODE, fnStart);
const catchStart = fnBody.indexOf('catch');
const catchBlock = catchStart === -1 ? '' : balancedBlock(fnBody, catchStart);

describe('W3-14 R7 — handleDemographicsSubmit catch renders catalog copy only', () => {
  it('the handler and its catch block are found (the fence is not vacuous)', () => {
    expect(fnBody.length).toBeGreaterThan(0);
    expect(catchBlock).toMatch(/setDemographicsError\(/);
  });

  it("setDemographicsError's argument is a t(...) call", () => {
    const i = catchBlock.indexOf('setDemographicsError(');
    const args = balancedArgs(catchBlock, i + 'setDemographicsError'.length).trim();
    expect(args).toMatch(/^t\(/);
  });

  it("the argument is keyed by the parsed CODE through settingsErrorKey with the 'demographics.error.network' fallback", () => {
    const i = catchBlock.indexOf('setDemographicsError(');
    const args = balancedArgs(catchBlock, i + 'setDemographicsError'.length);
    expect(args).toMatch(/settingsErrorKey\(/);
    // The code must be the PARSED one: `err?.code` on a real axios error is
    // 'ERR_BAD_REQUEST', never RATE_LIMITED, so the rate-limit copy could
    // never render. Require parseApiError(...).code in the same statement.
    expect(args).toMatch(/parseApiError\(\s*err\s*\)\s*\??\.code\b/);
    expect(args).toMatch(/'demographics\.error\.network'/);
  });

  it('no `message` from parseApiError reaches the render (destructured or dotted)', () => {
    expect(catchBlock).not.toMatch(/\{\s*message\s*[,}]/);
    expect(catchBlock).not.toMatch(/\bmessage\b/);
    expect(catchBlock).not.toMatch(/(parsed|error|err)\??\.message/);
  });
});
