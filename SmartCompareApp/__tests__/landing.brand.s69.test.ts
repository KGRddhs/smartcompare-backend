/**
 * S69 U-R — brand rename Qaren -> MYEZ (ميّز): landing fence (T4).
 *
 * Spec: docs/investigations/2026-09-29-session-69-state/UR_RENAME_MYEZ_SPEC.md §3 T4 / R4,
 * as corrected by its spec review (C12, C13, C14, open question Q5).
 *
 * Page set: EIGHT pages — landing/{index,privacy,terms,support}.html and
 * landing/ar/{index,privacy,terms,support}.html (the spec's "seven" missed
 * ar/support.html).
 *
 * Addresses stay on qaren (ruling R-B / D14). The spec's gate
 * `grep … | grep -v qaren.app` drops WHOLE lines and so hides brand text that
 * shares a line with an address (support.html:7, ar/support.html:7). Here only
 * the address itself is stripped before matching.
 *
 * Arabic: «قارن» is also the verb "compare!". ar/index.html keeps three verb
 * uses («قارن بين» x2, the tagline «قارن بذكاء»); they are pinned by count and
 * by the word that follows. The Arabic word boundary is explicit (JS \b
 * ignores Arabic letters), so «مقارنة» / «المقارنات» never trip the fence.
 *
 * Legal pages (privacy/terms, both languages): since unit U8 the fence covers
 * the WHOLE page — chrome AND body. S69 renamed only the chrome and left the
 * body paragraphs / list items to U8; U8 (rulings UL1, UL17) renders the body
 * from app/legal/*.md (scripts/render_legal_landing.py) with the MYEZ brand,
 * so the former LEGAL exemption is gone. Addresses are still stripped first.
 * ADDRESS_COUNTS changed for the four legal pages only (ruling UG20): 7 -> 5 on
 * privacy, terms, ar/privacy and ar/terms (the hand-written body contact line
 * is now rendered from the markdown with an e-mail placeholder); the support
 * pages, the index pages and open.html keep their base counts.
 */
import * as fs from 'fs';
import * as path from 'path';

const LANDING = path.resolve(__dirname, '..', '..', 'landing');

const PAGES = [
  'index.html',
  'privacy.html',
  'support.html',
  'terms.html',
  'open.html', // S69 hand-off page for /c/ /r/ /q/ (universal-link fallback)
  'ar/index.html',
  'ar/privacy.html',
  'ar/support.html',
  'ar/terms.html',
];

const MYEZ_AR = 'ميّز'; // ميّز
const OLD_AR = 'قارن'; // قارن
const AR_LETTER = '[\\u0600-\\u06FF]';
const wordRe = (w: string, flags = 'u') =>
  new RegExp(`(?<!${AR_LETTER})[\\u0628\\u0644\\u0648]?${w}(?!${AR_LETTER})`, flags);
const OLD_AR_WORD_G = wordRe(OLD_AR, 'gu');
const MYEZ_AR_WORD = wordRe(MYEZ_AR);

const ADDRESS_RE =
  /qaren:\/\/[\w/.-]*|[\w.+-]*@qaren\.app|(?:https?:\/\/)?(?:[\w-]+\.)*qaren\.app(?:\/[\w/.%-]*)?/gi;

/** Base e3f87b8b counts of `qaren.app` per page — every address must survive. */
const ADDRESS_COUNTS: Record<string, number> = {
  'index.html': 8,
  // U8 (UG20): the four legal pages keep their 4 head links (canonical + 3 hreflang) and the
  // footer support@ mailto = 5. The body's hand-written contact line (2 per page: the mailto href
  // + its text; privacy@ on privacy, legal@ on terms) is now rendered from app/legal/*.md, where
  // the address is <PLACEHOLDER:PRIVACY_EMAIL> / <PLACEHOLDER:SUPPORT_EMAIL> (legal@ dropped, C29).
  // The fill-in commit re-counts these when the placeholders become addresses.
  'privacy.html': 5,
  'support.html': 9, // unchanged by U8: the rendered contact region carries <PLACEHOLDER:SUPPORT_EMAIL>
  'terms.html': 5,
  'open.html': 3, // the two qaren.app mentions in the page's comments + the linking prefix in the script
  'ar/index.html': 8,
  'ar/privacy.html': 5,
  'ar/support.html': 9, // unchanged by U8, as support.html
  'ar/terms.html': 5,
};

const read = (rel: string) => fs.readFileSync(path.join(LANDING, rel), 'utf8');

/** Text in scope for the fence: the whole page (legal body included since U8), addresses stripped. */
function scoped(rel: string): string {
  return read(rel).replace(ADDRESS_RE, ' ');
}

function lineOf(html: string, index: number): number {
  return html.slice(0, index).split('\n').length;
}

describe('S69 U-R T4 — landing brand fence (MYEZ / ميّز)', () => {
  it('no page carries Latin "Qaren" outside an address (legal body included, U8)', () => {
    // The page set is exactly the nine pages (the spec's "seven" missed ar/support.html; S69 added open.html).
    const found = [
      ...fs.readdirSync(LANDING).filter((f) => f.endsWith('.html')),
      ...fs
        .readdirSync(path.join(LANDING, 'ar'))
        .filter((f) => f.endsWith('.html'))
        .map((f) => `ar/${f}`),
    ].sort();
    expect(found).toEqual([...PAGES].sort());
    const offenders: string[] = [];
    for (const rel of PAGES) {
      const s = scoped(rel);
      for (const m of s.matchAll(/Qaren/g)) offenders.push(`${rel}:${lineOf(s, m.index ?? 0)}`);
    }
    expect(offenders).toEqual([]);
  });

  it('standalone Arabic «قارن» survives only as the 3 verb uses on ar/index.html', () => {
    const offenders: string[] = [];
    let verbUses = 0;
    for (const rel of PAGES) {
      const s = scoped(rel);
      for (const m of s.matchAll(OLD_AR_WORD_G)) {
        const after = s.slice((m.index ?? 0) + m[0].length, (m.index ?? 0) + m[0].length + 7);
        const isVerb = rel === 'ar/index.html' && /^ (?:بين|بذكاء)/.test(after);
        if (isVerb) verbUses += 1;
        else offenders.push(`${rel}:${lineOf(s, m.index ?? 0)}`);
      }
    }
    expect(offenders).toEqual([]);
    expect(verbUses).toBe(3);
  });

  it('every <title> names the brand: MYEZ (en pages) / «ميّز» (ar pages), addresses kept', () => {
    // R-B / D14: every address survives (S76: re-hosted on getmyez.com, owner decision 2026-10-10).
    for (const rel of PAGES) {
      const n = (read(rel).match(/qaren\.app|getmyez\.com/g) ?? []).length;
      expect({ rel, n }).toEqual({ rel, n: ADDRESS_COUNTS[rel] });
    }
    for (const rel of PAGES) {
      const title = (read(rel).match(/<title>([\s\S]*?)<\/title>/) ?? [])[1] ?? '';
      const ok = rel.startsWith('ar/') ? MYEZ_AR_WORD.test(title) : /\bMYEZ\b/.test(title);
      expect({ rel, title, ok }).toEqual({ rel, title, ok: true });
    }
  });

  it('every wordmark shows both forms, MYEZ and «ميّز»', () => {
    for (const rel of PAGES) {
      const html = read(rel);
      const at = html.indexOf('class="brand-name"');
      const mark = at < 0 ? '' : html.slice(at, html.indexOf('</span></span>', at) + 14);
      const ok = /\bMYEZ\b/.test(mark) && mark.includes(MYEZ_AR);
      expect({ rel, mark, ok }).toEqual({ rel, mark, ok: true });
    }
  });

  it('the © line reads "© 2026 MYEZ" on both index pages', () => {
    for (const rel of ['index.html', 'ar/index.html']) {
      expect({ rel, has: read(rel).includes('&copy; 2026 MYEZ') }).toEqual({ rel, has: true });
    }
  });
});
