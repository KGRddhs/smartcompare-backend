/**
 * Qaren — ProfileScreen v5 (editorial, rich)
 *
 * v4 was too uniform black-card + flat-list. v5 leans into editorial
 * typography and reuses Qaren's signature primitive — the VS PAIR —
 * as the brand moment on the profile. Your last three decisions
 * become the hero of the screen.
 *
 * Anatomy:
 *   1. Compact lens header (Q ring + initial avatar) + settings icon
 *   2. EDITORIAL HEADLINE — large display type setting context
 *   3. RECENT DECISIONS row — three mini-vs cards (horizontal). This is
 *      the unique Qaren brand moment — your own past comparisons.
 *   4. WHAT SHAPES YOUR MATCHES — 3 priority bars + cohort line
 *   5. THIS MONTH stat strip — 27 · 240 BHD · +5 credits
 *   6. Flat settings card
 */

const T_pr5 = window.qarenTokens || {};
const C_pr5 = T_pr5.colors || {};

function Lens56({ initial }) {
  const RING = 48;
  return (
    <div style={{ position: 'relative', width: RING + 6, height: RING + 6, display: 'grid', placeItems: 'center', flexShrink: 0 }}>
      <div style={{ position: 'absolute', width: RING, height: RING, borderRadius: RING/2, border: `2.5px solid ${C_pr5.text.primary}` }} />
      <div style={{ position: 'absolute', insetBlockEnd: 1, insetInlineEnd: 1, width: 14, height: 2.5, borderRadius: 2, background: C_pr5.text.primary, transform: 'rotate(45deg)', transformOrigin: 'right center' }} />
      <div style={{ position: 'absolute', insetBlockStart: 3, insetInlineEnd: 7, width: 7, height: 7, borderRadius: 4, background: C_pr5.accent, boxShadow: `0 0 0 2px ${C_pr5.bg.primary}` }} />
      <div style={{ width: 34, height: 34, borderRadius: 17, background: C_pr5.bg.secondary, display: 'grid', placeItems: 'center', font: '700 14px/1 var(--qaren-font-en, system-ui)', color: C_pr5.text.primary, zIndex: 1 }}>{initial}</div>
    </div>
  );
}

function ProfileHeaderRow({ name = 'Kareem' }) {
  return (
    <header style={{ display: 'flex', alignItems: 'center', gap: 12, paddingInline: 20, paddingTop: 8, paddingBottom: 18 }}>
      <QarenLogo size={28} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ font: '700 18px/1.2 var(--qaren-font-en, system-ui)', color: C_pr5.text.primary }}>{name}</div>
        <div style={{ font: '400 12px/1.4 var(--qaren-font-en, system-ui)', color: C_pr5.text.secondary, marginTop: 2 }}>Capital · GCC</div>
      </div>
      <button aria-label="Settings" style={{
        width: 36, height: 36, borderRadius: 18,
        background: C_pr5.bg.secondary, border: 'none',
        display: 'grid', placeItems: 'center', cursor: 'pointer',
      }}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_pr5.text.primary} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
      </button>
    </header>
  );
}

// Editorial headline removed per user feedback — Profile now leads with
// the Recent Decisions marquee, which IS the brand moment.
function EditorialHeadline() { return null; }

// Mini VS card — used in the Recent Decisions horizontal row.
function MiniVsCard({ a, b }) {
  return (
    <div style={{
      flex: '0 0 auto', width: 168,
      padding: 12, borderRadius: 16,
      background: C_pr5.bg.secondary, border: `1px solid ${C_pr5.border.light}`,
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      <div style={{
        position: 'relative',
        display: 'flex', alignItems: 'stretch', gap: 6,
      }}>
        <MiniProduct p={a} />
        <div style={{
          position: 'absolute', insetBlockStart: '50%', insetInlineStart: '50%',
          transform: 'translate(-50%, -50%)',
        }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            height: 18, paddingInline: 6, borderRadius: 999,
            background: C_pr5.accentLight, color: C_pr5.accentDark,
            font: '700 8px/1 var(--qaren-font-en, system-ui)',
            letterSpacing: '0.8px', textTransform: 'uppercase',
            border: `2px solid ${C_pr5.bg.secondary}`,
          }}>vs</span>
        </div>
        <MiniProduct p={b} />
      </div>
      <div style={{ font: '500 11px/1.3 var(--qaren-font-en, system-ui)', color: C_pr5.text.secondary }}>
        {(a.winner ? a.name : b.name)} · {a.ago}
      </div>
    </div>
  );
}

function MiniProduct({ p }) {
  return (
    <div style={{
      flex: 1, aspectRatio: '1 / 1', borderRadius: 10,
      background: p.tone, position: 'relative',
      display: 'grid', placeItems: 'center',
      color: 'rgba(0,0,0,0.18)',
      border: p.winner ? `2px solid ${C_pr5.accent}` : 'none',
    }}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="5" y="2" width="14" height="20" rx="2.5"/>
      </svg>
      {p.winner && (
        <span style={{
          position: 'absolute', insetBlockStart: 3, insetInlineEnd: 3,
          width: 12, height: 12, borderRadius: 6,
          background: C_pr5.accent,
          display: 'grid', placeItems: 'center',
          border: `1.5px solid ${C_pr5.bg.secondary}`,
        }}>
          <svg width="7" height="7" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </span>
      )}
    </div>
  );
}

function RecentDecisions() {
  const items = [
    { a: { name: 'iPhone 15',  tone: '#E8E9ED', winner: false, ago: '2 hrs ago' },
      b: { name: 'Galaxy S24', tone: '#1B1C1F', winner: true,  ago: '2 hrs ago' } },
    { a: { name: 'Centrum',    tone: '#FBE6E6', winner: true,  ago: '5 hrs ago' },
      b: { name: 'One A Day',  tone: '#FFEAD4', winner: false, ago: '5 hrs ago' } },
    { a: { name: 'CeraVe',     tone: '#E6EEF9', winner: false, ago: 'Yesterday' },
      b: { name: 'La Roche',   tone: '#FFF1DA', winner: true,  ago: 'Yesterday' } },
  ];
  return (
    <section style={{ marginBottom: 24 }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        paddingInline: 20, marginBottom: 10,
      }}>
        <div style={{
          font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
          letterSpacing: '1.1px', textTransform: 'uppercase',
          color: C_pr5.text.secondary,
        }}>
          Recent decisions
        </div>
        <button style={{
          background: 'none', border: 'none',
          font: '500 12px/1 var(--qaren-font-en, system-ui)',
          color: C_pr5.accentDark, cursor: 'pointer',
        }}>
          See all
        </button>
      </div>
      <div style={{
        display: 'flex', gap: 10, overflowX: 'auto',
        paddingInline: 20, paddingBottom: 4,
        scrollbarWidth: 'none',
      }}>
        {items.map((it, i) => <MiniVsCard key={i} {...it} />)}
      </div>
    </section>
  );
}

function PrioritiesInline() {
  const items = [
    { label: 'Quality',    weight: 0.95 },
    { label: 'Price',      weight: 0.78 },
    { label: 'Durability', weight: 0.62 },
  ];
  return (
    <section style={{
      marginInline: 20, marginBottom: 24,
      padding: 18, borderRadius: 20,
      background: C_pr5.bg.secondary, border: `1px solid ${C_pr5.border.light}`,
    }}>
      <div style={{ font: '600 16px/1.4 var(--qaren-font-en, system-ui)', color: C_pr5.text.primary, marginBottom: 12 }}>
        What shapes your matches
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {items.map((it) => (
          <div key={it.label} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ width: 76, font: '500 13px/1.3 var(--qaren-font-en, system-ui)', color: C_pr5.text.primary }}>{it.label}</span>
            <span style={{ flex: 1, height: 6, borderRadius: 999, background: C_pr5.border.light, overflow: 'hidden' }}>
              <span style={{ display: 'block', width: `${it.weight * 100}%`, height: '100%', background: C_pr5.accent }} />
            </span>
            <span style={{ width: 32, textAlign: 'end', font: '500 12px/1.3 var(--qaren-font-en, system-ui)', color: C_pr5.text.secondary, fontVariantNumeric: 'tabular-nums' }}>
              {Math.round(it.weight * 100)}%
            </span>
          </div>
        ))}
      </div>
      <button style={{
        marginTop: 14, width: '100%', height: 44, borderRadius: 22,
        background: C_pr5.cta.primary, border: 'none', color: C_pr5.cta.onPrimary,
        font: '600 14px/1 var(--qaren-font-en, system-ui)', cursor: 'pointer',
      }}>
        Tune my priorities
      </button>
    </section>
  );
}

function MonthStrip() {
  return (
    <section style={{
      marginInline: 20, marginBottom: 24,
      display: 'flex', gap: 10,
    }}>
      <Stat n="27" l="Decisions this month" />
      <Stat n="240" l="BHD shopped smarter" subtle />
      <Stat n="+5" l="Bonus credits" />
    </section>
  );
}
function Stat({ n, l, subtle }) {
  return (
    <div style={{ flex: 1, minWidth: 0, padding: 14, borderRadius: 16, background: C_pr5.bg.secondary, border: `1px solid ${C_pr5.border.light}` }}>
      <div style={{ font: '700 22px/1 var(--qaren-font-en, system-ui)', color: subtle ? C_pr5.accentDark : C_pr5.text.primary, fontVariantNumeric: 'tabular-nums' }}>{n}</div>
      <div style={{ font: '400 11px/1.3 var(--qaren-font-en, system-ui)', color: C_pr5.text.secondary, marginTop: 6 }}>{l}</div>
    </div>
  );
}

// Flat settings card — same as v4.
function SettingsRow({ label, value, destructive, last }) {
  const color = destructive ? C_pr5.destructive : C_pr5.text.primary;
  return (
    <button style={{
      display: 'flex', alignItems: 'center', gap: 12,
      width: '100%', minHeight: 52, paddingBlock: 13, paddingInline: 16,
      background: 'transparent', border: 'none', textAlign: 'start', cursor: 'pointer',
      borderBlockEnd: last ? 'none' : `1px solid ${C_pr5.border.light}`,
    }}>
      <div style={{ flex: 1, font: '500 14px/1.3 var(--qaren-font-en, system-ui)', color }}>{label}</div>
      {value && <div style={{ font: '400 13px/1.3 var(--qaren-font-en, system-ui)', color: C_pr5.text.secondary }}>{value}</div>}
      {!destructive && <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={C_pr5.text.placeholder} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>}
    </button>
  );
}
function SettingsEyebrow({ children }) {
  return (
    <div style={{
      font: '600 10px/1.4 var(--qaren-font-en, system-ui)',
      letterSpacing: '1.1px', textTransform: 'uppercase',
      color: C_pr5.text.placeholder,
      paddingBlock: 10, paddingInline: 16,
      background: C_pr5.bg.primary,
      borderBlockEnd: `1px solid ${C_pr5.border.light}`, borderBlockStart: `1px solid ${C_pr5.border.light}`,
    }}>{children}</div>
  );
}
function FlatSettings() {
  return (
    <section style={{
      marginInline: 20, marginBottom: 20,
      borderRadius: 18, background: C_pr5.bg.secondary,
      border: `1px solid ${C_pr5.border.light}`, overflow: 'hidden',
    }}>
      <SettingsEyebrow>Account</SettingsEyebrow>
      <SettingsRow label="Edit profile" />
      <SettingsRow label="Change password" />
      <SettingsRow label="Language" value="English" />
      <SettingsEyebrow>Privacy & notifications</SettingsEyebrow>
      <SettingsRow label="Help improve AI quality" value="On" />
      <SettingsRow label="Smart Decision Notifications" value="On" />
      <SettingsRow label="Invite a friend" value="+5 each" />
      <SettingsEyebrow>Help</SettingsEyebrow>
      <SettingsRow label="Privacy Policy" />
      <SettingsRow label="Terms of Service" />
      <SettingsRow label="Contact us" />
      <SettingsRow label="Log out" />
      <SettingsEyebrow>Danger zone</SettingsEyebrow>
      <SettingsRow label="Delete account" destructive last />
    </section>
  );
}

const __strokeP5 = (d) => (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{d}</svg>);
function TabBarP5({ active = 'profile' }) {
  const items = [
    { key: 'home',    label: 'Qaren',   icon: __strokeP5(<path d="M3 9 12 2l9 7v11a2 2 0 0 1-2 2h-4v-7H10v7H5a2 2 0 0 1-2-2z"/>) },
    { key: 'history', label: 'History', icon: __strokeP5(<><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></>) },
    { key: 'profile', label: 'Profile', icon: __strokeP5(<><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></>) },
  ];
  return (
    <nav style={{ display: 'flex', borderTop: `1px solid ${C_pr5.border.light}`, background: C_pr5.bg.primary, paddingTop: 6, paddingBottom: 6 }}>
      {items.map((it) => {
        const isActive = active === it.key;
        const color = isActive ? C_pr5.accent : C_pr5.text.secondary;
        return (
          <button key={it.key} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, padding: '6px 0', border: 'none', background: 'transparent', cursor: 'pointer', minHeight: 44, color }}>
            <span style={{ width: 22, height: 22 }}>{it.icon}</span>
            <span style={{ font: `${isActive ? 600 : 500} 11px/1.2 var(--qaren-font-en, system-ui)`, color }}>{it.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

function QarenProfileScreen() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: C_pr5.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_pr5.text.primary,
    }}>
      <main style={{ flex: 1, overflowY: 'auto', paddingBottom: 12 }}>
        <ProfileHeaderRow />
        <EditorialHeadline />
        <RecentDecisions />
        <PrioritiesInline />
        <MonthStrip />
        <FlatSettings />
        <div style={{ height: 8 }} />
      </main>
      <TabBarP5 active="profile" />
    </div>
  );
}

window.QarenProfileScreen = QarenProfileScreen;
