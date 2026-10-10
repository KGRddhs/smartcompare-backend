/**
 * S76 DOMAIN-MYEZ (RED) -- the landing site (Railway service qaren-landing, name unchanged)
 * is served on getmyez.com; qaren.app is retired (owner decision 2026-10-10).
 *
 * LEGAL-REGION RULE. PR #330 (unit U8) renders the legal text into ONE region per page
 * between `<!-- legal:begin -->` and `<!-- legal:end -->` (scripts/render_legal_landing.py
 * REGION_BEGIN / REGION_END) on privacy, terms and support, EN + AR. This unit never owns
 * a line inside a region: the scan below skips every region line. On a tree without the
 * markers (main before #330) it also skips the hand-written legal-body contact line
 * (mailto:privacy@... on privacy, mailto:legal@... on terms), which #330 replaces wholesale.
 *
 * The support mailbox is support@getmyez.com (owner decision 2026-10-10) -- ONE constant
 * here (SUPPORT_EMAIL). The pages are static HTML with no templating, so the address is
 * written literally; a later change of address is this constant plus one mechanical replace
 * over the chrome lines this suite scans.
 *
 * L5 and L6 PASS on the untouched tree (positive controls: the hand-off is path-based and
 * the .well-known files carry identifiers, no host); the other cases are RED.
 *
 * L7 / L8 (GREEN, rulings DG3 / DG4): www.getmyez.com 301-redirects to the apex from its own
 * nginx server block placed AFTER the catch-all, and /bot serves the crawler info page that
 * the robots User-Agent names (landing/bot/index.html: a sub-directory, so the nine-page set
 * pinned by L0 and by landing.brand.s69 stays exactly nine).
 */
import * as fs from 'fs';
import * as path from 'path';
import * as vm from 'vm';

const LANDING = path.resolve(__dirname, '..', '..', 'landing');
const HOST = 'getmyez.com';
const WEB = `https://${HOST}`;
/** Owner decision 2026-10-10 -- the one place this suite names the support mailbox. */
const SUPPORT_EMAIL = `support@${HOST}`;
const RETIRED_RE = /qaren\.app/i;
/** KEEP identifier containing the retired host as a substring (the AASA appID / package). */
const KEEP_IDENTIFIER_RE = /\bcom\.qaren\.app\b/g;
const retiredIn = (line: string) => RETIRED_RE.test(line.replace(KEEP_IDENTIFIER_RE, ' '));
const EMAIL_RE = /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g;

const REGION_BEGIN = '<!-- legal:begin -->';
const REGION_END = '<!-- legal:end -->';
const LEGAL_PAGES = new Set(['privacy.html', 'terms.html', 'ar/privacy.html', 'ar/terms.html']);
/** Pre-#330 hand-written legal-body contact line; #330 owns and replaces it. */
const PRE_U8_BODY_CONTACT = /mailto:(?:privacy|legal)@qaren\.app/;

const PAGES = [
  'index.html',
  'open.html',
  'privacy.html',
  'support.html',
  'terms.html',
  'ar/index.html',
  'ar/privacy.html',
  'ar/support.html',
  'ar/terms.html',
];

const read = (rel: string) => fs.readFileSync(path.join(LANDING, rel), 'utf8');

/** The lines this unit owns: everything outside the legal region (1-based line numbers). */
function chromeLines(rel: string): [number, string][] {
  const lines = read(rel).split('\n');
  const begins = lines.filter((l) => l.includes(REGION_BEGIN)).length;
  const ends = lines.filter((l) => l.includes(REGION_END)).length;
  if (begins !== ends || begins > 1) {
    throw new Error(`${rel}: malformed legal region (begin=${begins}, end=${ends})`);
  }
  const out: [number, string][] = [];
  let inRegion = false;
  lines.forEach((line, i) => {
    if (line.includes(REGION_BEGIN)) {
      inRegion = true;
      return;
    }
    if (line.includes(REGION_END)) {
      inRegion = false;
      return;
    }
    if (inRegion) return;
    if (begins === 0 && LEGAL_PAGES.has(rel) && PRE_U8_BODY_CONTACT.test(line)) return;
    out.push([i + 1, line]);
  });
  return out;
}

function attr(html: string, re: RegExp): string | undefined {
  const m = re.exec(html);
  return m ? m[1] : undefined;
}

/** Expected head links per page: [canonical, hreflang en, hreflang ar, x-default, og:url]. */
const HEAD: Record<string, [string, string, string, string, string | undefined]> = {
  'index.html': [`${WEB}/`, `${WEB}/`, `${WEB}/ar/`, `${WEB}/`, `${WEB}/`],
  'ar/index.html': [`${WEB}/ar/`, `${WEB}/`, `${WEB}/ar/`, `${WEB}/`, `${WEB}/ar/`],
  'privacy.html': [`${WEB}/privacy.html`, `${WEB}/privacy.html`, `${WEB}/ar/privacy.html`, `${WEB}/privacy.html`, undefined],
  'ar/privacy.html': [`${WEB}/ar/privacy.html`, `${WEB}/privacy.html`, `${WEB}/ar/privacy.html`, `${WEB}/privacy.html`, undefined],
  'terms.html': [`${WEB}/terms.html`, `${WEB}/terms.html`, `${WEB}/ar/terms.html`, `${WEB}/terms.html`, undefined],
  'ar/terms.html': [`${WEB}/ar/terms.html`, `${WEB}/terms.html`, `${WEB}/ar/terms.html`, `${WEB}/terms.html`, undefined],
  'support.html': [`${WEB}/support`, `${WEB}/support`, `${WEB}/ar/support`, `${WEB}/support`, undefined],
  'ar/support.html': [`${WEB}/ar/support`, `${WEB}/support`, `${WEB}/ar/support`, `${WEB}/support`, undefined],
};

describe('S76 DOMAIN-MYEZ -- landing pages on getmyez.com (legal regions excluded)', () => {
  it('L0: the page set is exactly the nine pages', () => {
    const found = [
      ...fs.readdirSync(LANDING).filter((f) => f.endsWith('.html')),
      ...fs
        .readdirSync(path.join(LANDING, 'ar'))
        .filter((f) => f.endsWith('.html'))
        .map((f) => `ar/${f}`),
    ].sort();
    expect(found).toEqual([...PAGES].sort());
  });

  it('L1: no page carries "qaren.app" outside a legal region', () => {
    const offenders: string[] = [];
    for (const rel of PAGES) {
      for (const [n, line] of chromeLines(rel)) {
        if (retiredIn(line)) offenders.push(`${rel}:${n}`);
      }
    }
    expect(offenders).toEqual([]);
  });

  it('L2: canonical, hreflang and og:url name https://getmyez.com', () => {
    for (const [rel, [canonical, en, ar, xDefault, ogUrl]] of Object.entries(HEAD)) {
      const html = read(rel);
      const got = {
        rel,
        canonical: attr(html, /<link rel="canonical" href="([^"]*)"/),
        en: attr(html, /<link rel="alternate" hreflang="en" href="([^"]*)"/),
        ar: attr(html, /<link rel="alternate" hreflang="ar" href="([^"]*)"/),
        xDefault: attr(html, /<link rel="alternate" hreflang="x-default" href="([^"]*)"/),
        ogUrl: attr(html, /<meta property="og:url" content="([^"]*)"/),
      };
      expect(got).toEqual({ rel, canonical, en, ar, xDefault, ogUrl });
    }
  });

  it('L3: every e-mail address outside a legal region is SUPPORT_EMAIL (one constant)', () => {
    const offenders: string[] = [];
    const perPage: Record<string, number> = {};
    for (const rel of PAGES) {
      perPage[rel] = 0;
      for (const [n, line] of chromeLines(rel)) {
        for (const m of line.match(EMAIL_RE) ?? []) {
          if (m === SUPPORT_EMAIL) perPage[rel] += 1;
          else offenders.push(`${rel}:${n} ${m}`);
        }
      }
    }
    expect(offenders).toEqual([]);
    // Every page but the hand-off page publishes the support mailbox in its chrome.
    for (const rel of PAGES.filter((p) => p !== 'open.html')) {
      expect({ rel, atLeastOne: perPage[rel] > 0 }).toEqual({ rel, atLeastOne: true });
    }
    for (const rel of ['support.html', 'ar/support.html']) {
      expect({ rel, refresh: attr(read(rel), /<meta http-equiv="refresh" content="0; url=([^"]*)"/) }).toEqual({
        rel,
        refresh: `mailto:${SUPPORT_EMAIL}`,
      });
    }
  });

  it('L4: nginx template, open.html, Dockerfile and landing/README.md name no qaren.app (README: only a "retired" note)', () => {
    const offenders: string[] = [];
    for (const rel of ['nginx.conf.template', 'open.html', 'Dockerfile']) {
      read(rel)
        .split('\n')
        .forEach((line, i) => {
          if (retiredIn(line)) offenders.push(`${rel}:${i + 1}`);
        });
    }
    read('README.md')
      .split('\n')
      .forEach((line, i) => {
        if (retiredIn(line) && !/\bretired\b/i.test(line)) offenders.push(`README.md:${i + 1}`);
      });
    expect(offenders).toEqual([]);
    // The hand-off script documents the linking prefixes it mirrors.
    expect(read('open.html')).toContain(`'${WEB}'`);
  });
});

describe('S76 DOMAIN-MYEZ -- open.html hands https://getmyez.com/{c,r,q}/... to qaren://', () => {
  function inlineScript(): string {
    const m = /<script>([\s\S]*?)<\/script>/.exec(read('open.html'));
    if (!m) throw new Error('open.html has no inline script');
    return m[1];
  }

  /** Run the page script as a browser on `url` would, and return the Open button's href. */
  function openHref(url: string): string | undefined {
    const u = new URL(url);
    const attrs: Record<string, Record<string, string>> = {};
    const el = (id: string) => {
      attrs[id] = attrs[id] ?? {};
      return {
        setAttribute: (k: string, v: string) => {
          attrs[id][k] = v;
        },
        removeAttribute: (k: string) => {
          delete attrs[id][k];
        },
      };
    };
    const document = {
      getElementById: (id: string) => el(id),
      querySelector: () => null,
      documentElement: el('html'),
      title: '',
    };
    const window: Record<string, unknown> = { location: { pathname: u.pathname, search: u.search } };
    vm.runInNewContext(inlineScript(), { window, document, navigator: { language: 'en-US' } });
    return (attrs['open-en'] ?? {}).href;
  }

  it('L5 (control): c/<token>?ref, r/<code>, q/<token> and the token-less /c/?ref map to qaren://', () => {
    const table: [string, string][] = [
      [`${WEB}/c/TOK1?ref=QR-ABCDEF`, 'qaren://c/TOK1?ref=QR-ABCDEF'],
      [`${WEB}/r/QR-ABCDEF`, 'qaren://r/QR-ABCDEF'],
      [`${WEB}/q/TOK2`, 'qaren://q/TOK2'],
      [`${WEB}/c/?ref=QR-ABCDEF`, 'qaren://r/QR-ABCDEF'],
      [`${WEB}/`, 'qaren://'],
    ];
    for (const [url, expected] of table) {
      expect({ url, href: openHref(url) }).toEqual({ url, href: expected });
    }
  });

  it('L6 (control): the .well-known files carry identifiers only, unchanged (no host to move)', () => {
    const aasa = JSON.parse(read('.well-known/apple-app-site-association'));
    expect(aasa.applinks.details).toEqual([
      { appID: '8K562M549D.com.qaren.app', paths: ['/r/*', '/c/*', '/q/*'] },
    ]);
    const assetlinks = JSON.parse(read('.well-known/assetlinks.json'));
    expect(assetlinks[0].target.package_name).toBe('com.qaren.app');
    for (const rel of ['.well-known/apple-app-site-association', '.well-known/assetlinks.json']) {
      expect({ rel, host: /https?:\/\//.test(read(rel)) }).toEqual({ rel, host: false });
    }
  });
});

describe('S76 DOMAIN-MYEZ -- nginx: www.getmyez.com redirect (DG3) and the /bot crawler page (DG4)', () => {
  const REPO = path.resolve(LANDING, '..');
  const HOST_RE = HOST.replace(/\./g, '\\.');

  /** The template's top-level server blocks, comments stripped (a commented-out line configures nothing). */
  function serverBlocks(): string[] {
    const text = read('nginx.conf.template')
      .split('\n')
      .map((line) => line.split('#')[0])
      .join('\n');
    const blocks: string[] = [];
    const re = /(?:^|\n)\s*server\s*\{/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      const start = m.index + m[0].length - 1;
      let depth = 0;
      let i = start;
      for (; i < text.length; i += 1) {
        if (text[i] === '{') depth += 1;
        else if (text[i] === '}') {
          depth -= 1;
          if (depth === 0) break;
        }
      }
      blocks.push(text.slice(start, i + 1));
      re.lastIndex = i + 1;
    }
    return blocks;
  }

  it('L7 (DG3): www.getmyez.com answers 301 to https://getmyez.com$request_uri from its own block, AFTER the catch-all', () => {
    const blocks = serverBlocks();
    expect(blocks.length).toBe(2);
    const [catchAll, www] = blocks;
    // nginx's default server for a listen socket is the FIRST block declaring it: the catch-all
    // stays first so the Railway host and the apex keep reaching the site.
    expect(catchAll).toMatch(/\bserver_name\s+_;/);
    expect(catchAll).not.toMatch(/\bwww\./);
    expect(www).toMatch(/\blisten\s+\$\{PORT\};/);
    expect(www).toMatch(new RegExp(`\\bserver_name\\s+www\\.${HOST_RE};`));
    expect(www).toMatch(new RegExp(`\\breturn\\s+301\\s+https://${HOST_RE}\\$request_uri;`));
    // A pure redirect: it serves nothing itself.
    expect(www).not.toMatch(/\b(?:location|root|try_files|index)\b/);
  });

  it('L8 (DG4): /bot serves landing/bot/index.html, an ASCII bilingual page naming the crawler token, robots.txt and SUPPORT_EMAIL', () => {
    const [catchAll] = serverBlocks();
    expect(catchAll).toMatch(/location\s*=\s*\/bot\s*\{\s*try_files\s+\/bot\/index\.html\s+=404;\s*\}/);
    expect(read('Dockerfile')).toMatch(/^COPY\s+bot\s+\/usr\/share\/nginx\/html\/bot\/?\s*$/m);

    const bytes = fs.readFileSync(path.join(LANDING, 'bot', 'index.html'));
    expect(bytes.filter((b) => b > 127).length).toBe(0);
    const page = bytes.toString('utf8');

    // The live robots User-Agent names this page, and the page names the UA's product token.
    const ua = fs.readFileSync(path.join(REPO, 'app', 'services', 'sitemap_discovery_service.py'), 'utf8');
    expect(ua).toContain(`(+${WEB}/bot;`);
    const robotsEval = fs.readFileSync(path.join(REPO, 'app', 'services', 'robots_eval.py'), 'utf8');
    const agent = (/^NAMED_AGENT = "([^"]+)"/m.exec(robotsEval) ?? [])[1] ?? '';
    expect(agent).not.toBe('');

    expect(page).toMatch(/<title>[^<]*\bMYEZ\b[^<]*<\/title>/);
    expect(page).toContain(`<link rel="canonical" href="${WEB}/bot">`);
    const en = attr(page, /<p lang="en" dir="ltr">([\s\S]*?)<\/p>/) ?? '';
    const ar = (attr(page, /<p lang="ar" dir="rtl">([\s\S]*?)<\/p>/) ?? '').replace(/&#x([0-9a-f]+);/gi, (_, h) =>
      String.fromCharCode(parseInt(h, 16))
    );
    const myezAr = String.fromCharCode(0x645, 0x64a, 0x651, 0x632);
    for (const [lang, text] of [
      ['en', en],
      ['ar', ar],
    ]) {
      expect({
        lang,
        agent: text.includes(agent),
        robots: text.includes('robots.txt'),
        mail: text.includes(`mailto:${SUPPORT_EMAIL}`),
      }).toEqual({ lang, agent: true, robots: true, mail: true });
    }
    expect(en).toMatch(/\bMYEZ\b/);
    expect(ar).toContain(myezAr);

    // One mailbox, no retired host, and the old brand only inside the UA token (an identifier).
    expect([...new Set(page.match(EMAIL_RE) ?? [])]).toEqual([SUPPORT_EMAIL]);
    expect(page.split('\n').filter(retiredIn)).toEqual([]);
    expect(page.split(agent).join(' ')).not.toMatch(/Qaren/i);
  });
});
