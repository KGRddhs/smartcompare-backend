/**
 * Qaren — HistoryScreen v2
 *
 * Source of truth: AI/smartcompare/SmartCompareApp/src/screens/HistoryScreen.tsx
 *
 * v2 makes History feel uniquely Qaren by leaning into the *comparison*
 * as the brand moment. Two changes from v1:
 *
 *   ▸ HERO STATS — a card at the top quantifies the value Qaren delivered
 *     this month ("27 decisions sorted · estimated 240 BHD saved"). This
 *     is Qaren's spiritual equivalent of Cal AI's daily calorie ring —
 *     a "you made progress" anchor at the top of the surface.
 *
 *   ▸ VS-ROWS — each past comparison is now a high-fidelity mini-results
 *     card: two product blocks separated by a CENTERED EMERALD "VS" pill
 *     (same component as TwoInputShell uses), with the winner block
 *     outlined in emerald and a "Top match" eyebrow above its name.
 *     A short verdict line below ("Picked Galaxy — Camera + battery
 *     beat Apple here") tells the user *why* in 1–2 beats.
 *
 * The vs metaphor IS Qaren's signature visual — leaning into it makes the
 * surface feel like the product, not a generic dated list.
 */

const T_h2 = window.qarenTokens || {};
const C_h2 = T_h2.colors || {};

const COMPARISONS_V2 = [
  {
    id: 1, when: 'Today', ago: '2 hours ago', category: 'Electronics',
    a: { name: 'iPhone 15',  sub: '128GB',  tone: '#E8E9ED', winner: false },
    b: { name: 'Galaxy S24', sub: '128GB',  tone: '#1B1C1F', winner: true  },
    verdict: 'Picked Galaxy — camera + battery edged out Apple here.',
  },
  {
    id: 2, when: 'Today', ago: '5 hours ago', category: 'Supplements',
    a: { name: 'Centrum Multi', sub: '120ct', tone: '#FBE6E6', winner: true },
    b: { name: 'One A Day',     sub: '100ct', tone: '#FFEAD4', winner: false },
    verdict: 'Picked Centrum — broader nutrient profile, same price tier.',
  },
  {
    id: 3, when: 'Yesterday', ago: '1 day ago', category: 'Skincare',
    a: { name: 'CeraVe Hydrating',  sub: '236ml', tone: '#E6EEF9', winner: false },
    b: { name: 'La Roche Effaclar', sub: '200ml', tone: '#FFF1DA', winner: true  },
    verdict: 'Picked La Roche — sensitive-skin tag matched your profile.',
  },
  {
    id: 4, when: 'This Week', ago: '3 days ago', category: 'Makeup',
    a: { name: 'Maybelline Fit Me', sub: '30ml',  tone: '#FCD9D2', winner: true },
    b: { name: 'MAC Studio Fix',    sub: '30ml',  tone: '#1B1C1F', winner: false },
    verdict: 'Picked Maybelline — better value for your budget tier.',
  },
];

// ─── Hero — recent verdicts marquee (replaces v2's black stat card) ─────
// Why this works: the brand moment lives in the marquee of YOUR own
// recent comparisons, not in a stat card. The white surface keeps the
// visual weight on the verdicts themselves; the small "27 / 240 BHD"
// stat strip below provides numeric anchor without dominating.
function HeroStats() {
  const recents = [
    { a: { name: 'iPhone 15',  tone: '#E8E9ED', winner: false },
      b: { name: 'Galaxy S24', tone: '#1B1C1F', winner: true  },
      tag: 'Electronics', ago: '2 hrs ago' },
    { a: { name: 'Centrum',    tone: '#FBE6E6', winner: true  },
      b: { name: 'One A Day',  tone: '#FFEAD4', winner: false },
      tag: 'Supplements', ago: '5 hrs ago' },
    { a: { name: 'CeraVe',     tone: '#E6EEF9', winner: false },
      b: { name: 'La Roche',   tone: '#FFF1DA', winner: true  },
      tag: 'Skincare', ago: 'Yesterday' },
    { a: { name: 'Maybelline', tone: '#FCD9D2', winner: true  },
      b: { name: 'MAC',        tone: '#1B1C1F', winner: false },
      tag: 'Makeup', ago: '3 days ago' },
  ];

  return (
    <section style={{ marginBottom: 22 }}>
      <div style={{
        display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
        paddingInline: 20, marginBottom: 12,
      }}>
        <div>
          <div style={{
            font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
            letterSpacing: '1.1px', textTransform: 'uppercase',
            color: C_h2.accentDark, marginBottom: 4,
          }}>
            ✦ Your recent verdicts
          </div>
          <div style={{ font: '700 24px/1.15 var(--qaren-font-en, system-ui)', color: C_h2.text.primary, letterSpacing: '-0.24px' }}>
            27 decisions this month
          </div>
          <div style={{ font: '400 13px/1.5 var(--qaren-font-en, system-ui)', color: C_h2.text.secondary, marginTop: 2 }}>
            ~240 BHD shopped smarter
          </div>
        </div>
      </div>

      {/* Marquee — horizontally scrollable mini vs cards */}
      <div style={{
        display: 'flex', gap: 12, overflowX: 'auto',
        paddingInline: 20, paddingBottom: 6,
        scrollbarWidth: 'none',
      }}>
        {recents.map((v, i) => <MarqueeCard key={i} v={v} />)}
      </div>
    </section>
  );
}

function MarqueeCard({ v }) {
  return (
    <article style={{
      flex: '0 0 auto', width: 184,
      padding: 12, borderRadius: 18,
      background: C_h2.bg.secondary,
      border: `1px solid ${C_h2.border.light}`,
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{
          display: 'inline-flex', paddingInline: 8, height: 20, alignItems: 'center', borderRadius: 999,
          background: C_h2.bg.primary,
          font: '600 9px/1 var(--qaren-font-en, system-ui)',
          color: C_h2.text.secondary,
          letterSpacing: '0.6px', textTransform: 'uppercase',
        }}>{v.tag}</span>
        <span style={{ font: '400 11px/1 var(--qaren-font-en, system-ui)', color: C_h2.text.placeholder }}>{v.ago}</span>
      </div>
      <div style={{ position: 'relative', display: 'flex', gap: 6 }}>
        <MqProduct p={v.a} />
        <div style={{ position: 'absolute', insetBlockStart: '50%', insetInlineStart: '50%', transform: 'translate(-50%, -50%)' }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            height: 20, paddingInline: 8, borderRadius: 999,
            background: C_h2.accentLight, color: C_h2.accentDark,
            font: '700 9px/1 var(--qaren-font-en, system-ui)',
            letterSpacing: '1px', textTransform: 'uppercase',
            border: `2px solid ${C_h2.bg.secondary}`,
          }}>vs</span>
        </div>
        <MqProduct p={v.b} />
      </div>
      <div style={{
        font: '600 12px/1.3 var(--qaren-font-en, system-ui)', color: C_h2.text.primary,
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }}>
        Picked {v.a.winner ? v.a.name : v.b.name}
      </div>
    </article>
  );
}
function MqProduct({ p }) {
  return (
    <div style={{
      flex: 1, aspectRatio: '1 / 1', borderRadius: 10,
      background: p.tone, position: 'relative',
      display: 'grid', placeItems: 'center',
      color: 'rgba(0,0,0,0.18)',
      border: p.winner ? `2px solid ${C_h2.accent}` : 'none',
    }}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="5" y="2" width="14" height="20" rx="2.5"/>
      </svg>
      {p.winner && (
        <span style={{
          position: 'absolute', insetBlockStart: 3, insetInlineEnd: 3,
          width: 14, height: 14, borderRadius: 7,
          background: C_h2.accent,
          display: 'grid', placeItems: 'center',
          border: `2px solid ${C_h2.bg.secondary}`,
        }}>
          <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </span>
      )}
    </div>
  );
}

// ─── Search field (decorative) ──────────────────────────────────────────
function SearchField() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      height: 42, paddingInline: 14,
      borderRadius: 999,
      background: C_h2.bg.secondary,
      border: `1px solid ${C_h2.border.light}`,
      marginInline: 20, marginBottom: 18,
    }}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={C_h2.text.placeholder} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <span style={{ font: '400 14px/1.5 var(--qaren-font-en, system-ui)', color: C_h2.text.placeholder }}>
        Search comparisons…
      </span>
    </div>
  );
}

// ─── Product block ──────────────────────────────────────────────────────
function ProductBlock({ p }) {
  return (
    <div style={{
      flex: 1, minWidth: 0,
      display: 'flex', flexDirection: 'column', gap: 8,
      padding: 10,
      borderRadius: 14,
      background: p.winner ? C_h2.accentLight : C_h2.bg.secondary,
      border: `${p.winner ? 2 : 1}px solid ${p.winner ? C_h2.accent : C_h2.border.light}`,
    }}>
      {p.winner && (
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          font: '600 9px/1.2 var(--qaren-font-en, system-ui)',
          color: C_h2.accentDark,
          letterSpacing: '1px', textTransform: 'uppercase',
        }}>
          <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>
          Top match
        </div>
      )}
      <div style={{
        aspectRatio: '1 / 1', borderRadius: 10,
        background: p.tone, display: 'grid', placeItems: 'center',
        color: 'rgba(0,0,0,0.18)',
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="5" y="2" width="14" height="20" rx="2.5"/>
        </svg>
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{
          font: `${p.winner ? 700 : 600} 13px/1.3 var(--qaren-font-en, system-ui)`,
          color: C_h2.text.primary,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{p.name}</div>
        {p.sub && (
          <div style={{ font: '400 11px/1.4 var(--qaren-font-en, system-ui)', color: C_h2.text.secondary, marginTop: 1 }}>
            {p.sub}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── VS row — Qaren's brand moment, used as the history card ────────────
function HistoryRowV2({ c }) {
  return (
    <article style={{
      marginBottom: 14,
      paddingBlock: 14, paddingInline: 14,
      background: C_h2.bg.primary,
      borderRadius: 18,
      border: `1px solid ${C_h2.border.light}`,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 12,
      }}>
        <span style={{
          display: 'inline-flex', alignItems: 'center',
          paddingInline: 10, height: 22, borderRadius: 999,
          background: C_h2.bg.secondary,
          font: '600 10px/1 var(--qaren-font-en, system-ui)',
          color: C_h2.text.secondary,
          letterSpacing: '0.6px', textTransform: 'uppercase',
        }}>{c.category}</span>
        <span style={{ font: '400 12px/1 var(--qaren-font-en, system-ui)', color: C_h2.text.secondary, fontVariantNumeric: 'tabular-nums' }}>
          {c.ago}
        </span>
      </div>

      <div style={{ position: 'relative', display: 'flex', alignItems: 'stretch', gap: 10 }}>
        <ProductBlock p={c.a} />
        {/* centered vs pill — the brand moment */}
        <div style={{
          position: 'absolute', insetBlockStart: '50%', insetInlineStart: '50%',
          transform: 'translate(-50%, -50%)', zIndex: 1,
        }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            height: 26, paddingInline: 12, borderRadius: 999,
            background: C_h2.accentLight, color: C_h2.accentDark,
            font: '700 11px/1 var(--qaren-font-en, system-ui)',
            letterSpacing: '1.2px', textTransform: 'uppercase',
            border: `2px solid ${C_h2.bg.primary}`,
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}>vs</span>
        </div>
        <ProductBlock p={c.b} />
      </div>

      <p style={{
        margin: '12px 0 0',
        font: '500 12px/1.5 var(--qaren-font-en, system-ui)',
        color: C_h2.text.primary,
        textWrap: 'pretty',
      }}>{c.verdict}</p>
    </article>
  );
}

function DateGroupV2({ label, items }) {
  return (
    <section style={{ marginBottom: 16 }}>
      <h2 style={{
        margin: '0 0 10px', paddingInline: 4,
        font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
        letterSpacing: '1.1px', textTransform: 'uppercase',
        color: C_h2.text.secondary,
      }}>{label}</h2>
      {items.map((c) => <HistoryRowV2 key={c.id} c={c} />)}
    </section>
  );
}

// Tab bar (matches Profile + Home).
const __strokeH2 = (d) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{d}</svg>
);
function TabBarH2({ active = 'history' }) {
  const items = [
    { key: 'home',    label: 'Qaren',   icon: __strokeH2(<path d="M3 9 12 2l9 7v11a2 2 0 0 1-2 2h-4v-7H10v7H5a2 2 0 0 1-2-2z"/>) },
    { key: 'history', label: 'History', icon: __strokeH2(<><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></>) },
    { key: 'profile', label: 'Profile', icon: __strokeH2(<><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></>) },
  ];
  return (
    <nav style={{
      display: 'flex', borderTop: `1px solid ${C_h2.border.light}`,
      background: C_h2.bg.primary, paddingTop: 6, paddingBottom: 6,
    }}>
      {items.map((it) => {
        const isActive = active === it.key;
        const color = isActive ? C_h2.accent : C_h2.text.secondary;
        return (
          <button key={it.key} style={{
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
            padding: '6px 0', border: 'none', background: 'transparent', cursor: 'pointer', minHeight: 44, color,
          }}>
            <span style={{ width: 22, height: 22 }}>{it.icon}</span>
            <span style={{ font: `${isActive ? 600 : 500} 11px/1.2 var(--qaren-font-en, system-ui)`, color }}>{it.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

function QarenHistoryScreen() {
  const groups = COMPARISONS_V2.reduce((acc, c) => {
    if (!acc[c.when]) acc[c.when] = [];
    acc[c.when].push(c);
    return acc;
  }, {});
  const order = ['Today', 'Yesterday', 'This Week', 'Older'];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: C_h2.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_h2.text.primary,
    }}>
      <header style={{ paddingInline: 20, paddingTop: 8, paddingBottom: 16 }}>
        <h1 style={{ margin: 0, font: '700 28px/1.2 var(--qaren-font-en, system-ui)', letterSpacing: '-0.28px' }}>
          History
        </h1>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', paddingBottom: 8 }}>
        <HeroStats />
        <SearchField />
        <div style={{ paddingInline: 20 }}>
          {order.map((label) => groups[label] ? <DateGroupV2 key={label} label={label} items={groups[label]} /> : null)}
        </div>
      </main>

      <TabBarH2 active="history" />
    </div>
  );
}

window.QarenHistoryScreen = QarenHistoryScreen;
