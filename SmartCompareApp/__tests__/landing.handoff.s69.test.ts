/**
 * S69 — the landing hand-off page's inline script, EXECUTED (audit RT-8 / EXPO-06).
 *
 * `landing/open.html` is served by nginx for /c/<share token>, /r/<invite code>
 * and /q/<quiz token>. Its inline script rewrites the two "Open in MYEZ"
 * buttons to the qaren:// deep link the app's linking config resolves
 * (src/navigation/linking.ts: c/:share_token, r/:code, q/:share_token,
 * prefixes 'qaren://' + 'https://qaren.app'). The static pytest pins the
 * page's structure; this suite runs the script in a stub DOM and pins the
 * behaviour, so a wrong regex, a swapped group or a missed button reddens.
 *
 * The referral link the backend builds today usually has NO share token
 * (referral_service.py:348 reads the comparison's `share_token`, NULL unless
 * POST /share/{id} created one) — /c/?ref=QR-XXXXXX must hand off to the
 * Register screen with the code (qaren://r/QR-XXXXXX), never drop the code.
 */
import * as fs from 'fs';
import * as path from 'path';
import * as vm from 'vm';

const PAGE = fs.readFileSync(path.resolve(__dirname, '..', '..', 'landing', 'open.html'), 'utf8');

function inlineScript(): string {
  const m = /<script>([\s\S]*?)<\/script>/.exec(PAGE);
  if (!m) throw new Error('open.html has no inline script');
  return m[1];
}

type Stub = {
  attrs: Record<string, string>;
  setAttribute: (k: string, v: string) => void;
  removeAttribute: (k: string) => void;
};

function run(pathname: string, search: string, language = 'en-US') {
  const els: Record<string, Stub> = {};
  const el = (id: string): Stub => {
    if (!els[id]) {
      const attrs: Record<string, string> = {};
      els[id] = {
        attrs,
        setAttribute: (k, v) => {
          attrs[k] = v;
        },
        removeAttribute: (k) => {
          delete attrs[k];
        },
      };
    }
    return els[id];
  };
  // The store buttons start hidden in the markup; mirror that so a removeAttribute shows.
  el('store-en').attrs.hidden = '';
  el('store-ar').attrs.hidden = '';
  const inserted: Array<[Stub, Stub]> = [];
  const main = { insertBefore: (a: Stub, b: Stub) => inserted.push([a, b]) };
  const documentElement = el('html');
  const doc: Record<string, unknown> = {
    getElementById: (id: string) => el(id),
    querySelector: (sel: string) => (sel === 'main' ? main : null),
    documentElement,
    title: 'Open in MYEZ — افتح في ميّز',
  };
  const window: Record<string, unknown> = { location: { pathname, search } };
  const ctx = vm.createContext({ window, document: doc, navigator: { language } });
  vm.runInContext(inlineScript(), ctx);
  return { els, inserted, doc, window };
}

describe('S69 landing hand-off script (open.html)', () => {
  it.each([
    ['/c/AbC-123_xyz', '?ref=QR-ABC234', 'qaren://c/AbC-123_xyz?ref=QR-ABC234'],
    ['/c/tok', '', 'qaren://c/tok'],
    ['/c/tok/', '?ref=QR-ABC234', 'qaren://c/tok?ref=QR-ABC234'],
    ['/r/QR-ABC234', '', 'qaren://r/QR-ABC234'],
    ['/q/quiz-token_1', '', 'qaren://q/quiz-token_1'],
    ['/c/', '?ref=QR-ABC234', 'qaren://r/QR-ABC234'],
    ['/c', '?ref=QR-ABC234', 'qaren://r/QR-ABC234'],
    ['/c/', '?utm=x&ref=qr-abc234', 'qaren://r/QR-ABC234'],
    ['/c/', '?ref=QR-ABC23', 'qaren://'],
    ['/c/', '?ref=QR-ABC23O', 'qaren://'],
    ['/c/', '', 'qaren://'],
    ['/c/a/b', '', 'qaren://'],
    ['/x/tok', '', 'qaren://'],
    ['/', '', 'qaren://'],
  ])('%s%s hands off to %s', (pathname, search, expected) => {
    const { els, window } = run(pathname, search);
    expect(els['open-en'].attrs.href).toBe(expected);
    expect(els['open-ar'].attrs.href).toBe(expected);
    const fn = window.__myezHandoff as (p: string, s: string) => string;
    expect(fn(pathname, search)).toBe(expected);
  });

  it('the store buttons stay hidden and the note visible while APP_STORE_URL is empty', () => {
    const { els } = run('/c/tok', '');
    expect(els['store-en'].attrs.hidden).toBe('');
    expect(els['store-ar'].attrs.hidden).toBe('');
    expect(els['store-en'].attrs.href).toBeUndefined();
    // The note is only touched when a store URL exists, so the stub may never be created.
    expect(els['store-note-en']?.attrs.hidden).toBeUndefined();
  });

  it('an Arabic browser reads the Arabic block first and the document switches to lang=ar', () => {
    const { inserted, els, doc } = run('/c/tok', '', 'ar-BH');
    expect(inserted).toHaveLength(1);
    expect(inserted[0][0]).toBe(els['ar']);
    expect(inserted[0][1]).toBe(els['en']);
    expect(els['html'].attrs.lang).toBe('ar');
    expect(String(doc.title)).toMatch(/^افتح في ميّز/);
  });

  it('an English browser keeps the English block first', () => {
    const { inserted, els } = run('/c/tok', '', 'en-GB');
    expect(inserted).toHaveLength(0);
    expect(els['html'].attrs.lang).toBeUndefined();
  });

  it('a percent-encoded or hostile path never becomes markup (attribute writes only)', () => {
    const { els } = run('/c/%3Cimg%20onerror%3Dx%3E', '?ref=%3Cb%3E');
    expect(els['open-en'].attrs.href).toBe('qaren://c/%3Cimg%20onerror%3Dx%3E?ref=%3Cb%3E');
    expect(inlineScript()).not.toMatch(/innerHTML|document\.write|\beval\(/);
  });
});
