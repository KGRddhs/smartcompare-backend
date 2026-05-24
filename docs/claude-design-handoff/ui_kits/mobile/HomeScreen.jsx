/**
 * Qaren — HomeScreen (reference implementation, web)
 *
 * Source of truth: AI/smartcompare/SmartCompareApp/src/screens/HomeScreen.tsx
 * (this file is a faithful design-only rebuild that fixes the 3 crowding
 * issues called out in HomeScreen review:)
 *
 *   ▸ FIX 1 — Two simultaneous counter UIs collapsed into ONE:
 *     a single right-aligned counter pill in the header that doubles as
 *     a tap target into the Paywall ("2 of 3 free · 1 anytime").
 *     BonusCountdownCard and ComparisonCounter no longer both render.
 *
 *   ▸ FIX 2 — Mode chips (Scan / Link / Type) moved INTO the input card
 *     as a top segmented control. The bottom tab bar (Home/History/
 *     Profile) is the only chrome at the bottom edge — no visual fight.
 *
 *   ▸ FIX 3 — Empty state previews the comparison structure: two
 *     outlined numeral circles ① ② joined by the hairline + "vs" pill
 *     (the TwoInputShell pattern from Bundle B). Replaces the dead
 *     white card.
 *
 * Other invariants enforced (Bundle B Build Principle #4 + theme):
 *   - Primary CTA is black. Emerald used only as signal (vs pill, toggle,
 *     active tab, ready-glow shadow, winner border).
 *   - No shake/wobble/jitter on any state change. Errors render as calm
 *     hairline text below the active row.
 *   - Copy passes the .copy-policy.json fence: no "Winner", no "Failed",
 *     no "couldn't", no "try again".
 *   - RTL-ready: every margin uses {start,end}, every flex row will swap
 *     direction under [dir="rtl"]. Numeral circles + hairline anchor to
 *     the same logical edge in both directions.
 *
 * Consumes tokens via window.qarenTokens (loaded from tokens.json) so
 * frontend agent can drop these values straight into theme/index.ts.
 */

const { useState } = React;

// Local alias so the JSX reads like the native source.
const T = (window.qarenTokens && window.qarenTokens) || {};
const C = T.colors || {};
const SP = T.spacing || {};
const R = T.radii || {};
const TY = T.typography || {};

/* ─── Inline glyphs (mirror SmartCompareApp/src/icons exactly) ─── */
/* QarenLogo lives in QarenLogo.jsx and is loaded into window before this
   script — see ui_kits/mobile/index.html script order. */

function ScanIcon({ size = 16, color }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} aria-hidden="true">
      <path d="M3 7.5V5a2 2 0 0 1 2-2h2.5v2H5v2.5zM21 7.5V5a2 2 0 0 0-2-2h-2.5v2H19v2.5zM3 16.5V19a2 2 0 0 0 2 2h2.5v-2H5v-2.5zM21 16.5V19a2 2 0 0 1-2 2h-2.5v-2H19v-2.5zM12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z" />
    </svg>
  );
}
function LinkIcon({ size = 16, color }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} aria-hidden="true">
      <path d="M9.6 14.4l4.8-4.8a1.5 1.5 0 1 1 2.12 2.12l-2.12 2.12a1 1 0 1 0 1.42 1.42l2.12-2.12a3.5 3.5 0 1 0-4.95-4.95l-4.8 4.8a1 1 0 1 0 1.41 1.41z" />
    </svg>
  );
}
function TypeIcon({ size = 16, color }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} aria-hidden="true">
      <rect x="4" y="5" width="16" height="3" rx="1.5" />
      <rect x="10.5" y="6.5" width="3" height="11" rx="1" />
      <rect x="5" y="18.5" width="14" height="1.6" rx="0.8" />
    </svg>
  );
}

// Lucide-style stroke icons for categories (matching src/components/CategorySelector.tsx)
const Stroke = ({ d, size = 16, color }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {d}
  </svg>
);
const Smartphone = (p) => <Stroke {...p} d={<><rect x="5" y="2" width="14" height="20" rx="2.5"/><line x1="12" y1="18" x2="12.01" y2="18"/></>} />;
const ShoppingCart = (p) => <Stroke {...p} d={<><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></>} />;
const Pill = (p) => <Stroke {...p} d={<><path d="M10.5 20.5 20.5 10.5a4.95 4.95 0 0 0-7-7L3.5 13.5a4.95 4.95 0 0 0 7 7Z"/><line x1="8.5" y1="8.5" x2="15.5" y2="15.5"/></>} />;
const Brush = (p) => <Stroke {...p} d={<><path d="m9.06 11.9 8.07-8.06a2.85 2.85 0 1 1 4.03 4.03l-8.06 8.08"/><path d="M7.07 14.94c-1.66 0-3 1.35-3 3.02 0 1.33-2.5 1.52-2 2.02 1.08 1.1 2.49 2.02 4 2.02 2.2 0 4-1.8 4-4.04a3.01 3.01 0 0 0-3-3.02z"/></>} />;
const Sparkles = (p) => <Stroke {...p} d={<><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/></>} />;

/* ─── Numeral circle (rest / valid states) ─── */
function NumeralCircle({ value, valid }) {
  return (
    <div
      style={{
        width: 24, height: 24, borderRadius: 12,
        borderWidth: 1, borderStyle: 'solid',
        borderColor: valid ? C.accent : C.border.medium,
        background: valid ? C.accent : C.bg.primary,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}
      aria-hidden="true"
    >
      {valid ? (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={C.bg.primary} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      ) : (
        <span style={{ font: '600 11px/1 var(--qaren-font-en, system-ui)', color: C.text.secondary }}>{value}</span>
      )}
    </div>
  );
}

/* ─── Segmented mode control (lives at top of input card now) ─── */
function ModeSegment({ value, onChange }) {
  const items = [
    { key: 'scan', label: 'Scan', Icon: ScanIcon },
    { key: 'link', label: 'Link', Icon: LinkIcon },
    { key: 'type', label: 'Type', Icon: TypeIcon },
  ];
  return (
    <div
      role="tablist"
      aria-label="Input mode"
      style={{
        display: 'flex',
        padding: 4,
        gap: 4,
        background: C.bg.primary,
        border: `1px solid ${C.border.light}`,
        borderRadius: 999,
      }}
    >
      {items.map(({ key, label, Icon }) => {
        const active = value === key;
        return (
          <button
            key={key}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(key)}
            style={{
              flex: 1,
              minHeight: 36,
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              padding: '0 12px',
              borderRadius: 999,
              border: 'none',
              background: active ? C.cta.primary : 'transparent',
              color: active ? C.cta.onPrimary : C.text.secondary,
              font: `${active ? 600 : 500} 13px/1.5 var(--qaren-font-en, system-ui)`,
              cursor: 'pointer',
              transition: 'background 180ms cubic-bezier(0.32,0.72,0,1), color 180ms cubic-bezier(0.32,0.72,0,1)',
            }}
          >
            <Icon size={14} color={active ? C.cta.onPrimary : C.text.secondary} />
            {label}
          </button>
        );
      })}
    </div>
  );
}

/* ─── Compare card: segmented mode rail + body for the active mode ─── */
function CompareCard({ mode, setMode, productA, productB, setA, setB }) {
  const validA = mode === 'type' ? productA.trim().length >= 2 : false;
  const validB = mode === 'type' ? productB.trim().length >= 2 : false;
  const bothValid = validA && validB;

  return (
    <section
      style={{
        background: C.bg.secondary,
        borderRadius: R.card,
        padding: 16,
        border: `1px solid ${C.border.light}`,
      }}
    >
      <ModeSegment value={mode} onChange={setMode} />

      <div style={{ marginTop: 20, position: 'relative' }}>
        {mode === 'scan' && <ScanBody />}
        {mode === 'link' && (
          <TwoInputBody
            placeholderA="First link · paste from Amazon, Noon…"
            placeholderB="Second link"
            a={productA} b={productB} setA={setA} setB={setB}
            validA={validA} validB={validB}
          />
        )}
        {mode === 'type' && (
          <TwoInputBody
            placeholderA="Product A · e.g. iPhone 15"
            placeholderB="Product B · e.g. Galaxy S24"
            a={productA} b={productB} setA={setA} setB={setB}
            validA={validA} validB={validB}
          />
        )}
      </div>

      <button
        disabled={!bothValid && mode !== 'scan'}
        style={{
          marginTop: 20,
          width: '100%',
          height: 48,
          borderRadius: R.button,
          border: 'none',
          background: C.cta.primary,
          color: C.cta.onPrimary,
          font: '600 16px/1.5 var(--qaren-font-en, system-ui)',
          opacity: (bothValid || mode === 'scan') ? 1 : 0.5,
          boxShadow: bothValid ? '0 0 12px rgba(16,185,129,0.45)' : 'none',
          transition: 'opacity 200ms ease, box-shadow 240ms ease',
          cursor: (bothValid || mode === 'scan') ? 'pointer' : 'not-allowed',
        }}
      >
        {mode === 'scan' ? 'Open camera' : 'Compare'}
      </button>
    </section>
  );
}

/* Empty-state preview of the comparison structure (FIX 3). */
function ScanBody() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <PreviewRow numeral="1" placeholder="Tap to snap product A" />
      <div style={{ height: 6, position: 'relative' }}>
        <div style={{ position: 'absolute', insetInlineStart: 11, top: -6, bottom: -6, width: 1, background: C.border.light }} />
        <div style={{ position: 'absolute', insetInlineStart: -8, top: 0, bottom: 0, display: 'flex', alignItems: 'center' }}>
          <span style={{ marginInlineStart: 28, height: 22, padding: '0 10px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: C.accentLight, borderRadius: 999, color: C.accentDark, font: '600 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '1.1px', textTransform: 'uppercase' }}>vs</span>
        </div>
      </div>
      <PreviewRow numeral="2" placeholder="Tap to snap product B" />
      <p style={{ margin: '4px 0 0 36px', font: '400 12px/1.5 var(--qaren-font-en, system-ui)', color: C.text.secondary }}>
        Center each product in the brackets — sharper match every time.
      </p>
    </div>
  );
}

function PreviewRow({ numeral, placeholder }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <NumeralCircle value={numeral} valid={false} />
      <button
        style={{
          flex: 1,
          height: 48,
          borderRadius: R.card,
          background: C.bg.primary,
          border: `1px dashed ${C.border.medium}`,
          color: C.text.placeholder,
          font: '400 15px/1.5 var(--qaren-font-en, system-ui)',
          textAlign: 'start',
          paddingInline: 16,
          cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 8,
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C.text.placeholder} strokeWidth="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
        {placeholder}
      </button>
    </div>
  );
}

function TwoInputBody({ a, b, setA, setB, placeholderA, placeholderB, validA, validB }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0, position: 'relative' }}>
      {/* hairline + vs pill, between the two rows */}
      <div aria-hidden="true" style={{
        position: 'absolute', insetInlineStart: 11, top: 48, bottom: 48,
        width: 1, background: C.border.light,
      }} />
      <div aria-hidden="true" style={{
        position: 'absolute', insetInlineStart: -7, top: '50%',
        transform: 'translateY(-50%)',
        display: 'flex', alignItems: 'center',
      }}>
        <span style={{
          marginInlineStart: 28,
          height: 24, padding: '0 12px',
          background: C.accentLight, color: C.accentDark,
          borderRadius: 999,
          font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
          letterSpacing: '1.1px', textTransform: 'uppercase',
        }}>vs</span>
      </div>

      <InputRow numeral="1" value={a} onChange={setA} valid={validA} placeholder={placeholderA} />
      <div style={{ height: 32 }} />
      <InputRow numeral="2" value={b} onChange={setB} valid={validB} placeholder={placeholderB} />
    </div>
  );
}

function InputRow({ numeral, value, onChange, valid, placeholder }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <NumeralCircle value={numeral} valid={valid} />
      <div style={{
        flex: 1, height: 48, display: 'flex', alignItems: 'center', paddingInline: 16,
        background: C.bg.primary, borderRadius: R.card,
        border: focused ? `2px solid ${C.text.primary}` : `1px solid ${C.border.light}`,
      }}>
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          style={{
            width: '100%', border: 'none', outline: 'none', background: 'transparent',
            font: '400 16px/1.5 var(--qaren-font-en, system-ui)', color: C.text.primary,
          }}
        />
      </div>
    </div>
  );
}

/* ─── Header counter (FIX 1: collapsed from two pills into one) ─── */
function HeaderCounter({ free, total, bonus }) {
  const isLast = free === 1;
  return (
    <button
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        paddingInline: 12, height: 28,
        borderRadius: 999,
        background: isLast ? C.accentLight : C.bg.secondary,
        border: `1px solid ${isLast ? C.accent : C.border.light}`,
        color: isLast ? C.accentDark : C.text.secondary,
        font: '600 12px/1.5 var(--qaren-font-en, system-ui)',
        cursor: 'pointer',
      }}
      aria-label={`${free} of ${total} free comparisons${bonus ? `, plus ${bonus} bonus` : ''}`}
    >
      <span style={{ fontVariantNumeric: 'tabular-nums' }}>{free}/{total} free</span>
      {bonus > 0 && (
        <>
          <span aria-hidden="true" style={{ opacity: 0.5 }}>·</span>
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>+{bonus}</span>
        </>
      )}
    </button>
  );
}

/* ─── Bottom tab bar ─── */
function TabBar({ active }) {
  const items = [
    { key: 'home', label: 'Qaren', icon: (color) => (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M3 9 12 2l9 7v11a2 2 0 0 1-2 2h-4v-7H10v7H5a2 2 0 0 1-2-2z"/></svg>) },
    { key: 'history', label: 'History', icon: (color) => (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>) },
    { key: 'profile', label: 'Profile', icon: (color) => (<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>) },
  ];
  return (
    <nav
      style={{
        display: 'flex',
        borderTop: `1px solid ${C.border.light}`,
        background: C.bg.primary,
        paddingTop: 6, paddingBottom: 6,
      }}
    >
      {items.map((it) => {
        const isActive = active === it.key;
        const color = isActive ? C.accent : C.text.secondary;
        return (
          <button
            key={it.key}
            style={{
              flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
              padding: '6px 0',
              border: 'none', background: 'transparent', cursor: 'pointer',
              minHeight: 44,
            }}
            aria-current={isActive ? 'page' : undefined}
          >
            {it.icon(color)}
            <span style={{ font: `${isActive ? 600 : 500} 11px/1.2 var(--qaren-font-en, system-ui)`, color }}>{it.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

/* ─── Category strip ─── */
function CategoryStrip({ value, onChange }) {
  const cats = [
    { v: 'electronics', label: 'Electronics', Icon: Smartphone },
    { v: 'grocery', label: 'Grocery', Icon: ShoppingCart },
    { v: 'supplements', label: 'Supplements', Icon: Pill },
    { v: 'makeup', label: 'Makeup', Icon: Brush },
    { v: 'skincare', label: 'Skincare', Icon: Sparkles },
  ];
  return (
    <div
      style={{
        display: 'flex', gap: 8, overflowX: 'auto',
        paddingInline: 20, paddingBlock: 8,
        scrollbarWidth: 'none',
      }}
    >
      {cats.map(({ v, label, Icon }) => {
        const active = value === v;
        return (
          <button
            key={v}
            onClick={() => onChange(v)}
            aria-pressed={active}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              paddingInline: 14, paddingBlock: 8, minHeight: 36,
              borderRadius: 999,
              background: active ? C.accent : C.bg.secondary,
              border: `1px solid ${active ? C.accent : C.border.light}`,
              color: active ? '#FFFFFF' : C.text.primary,
              font: `${active ? 600 : 500} 13px/1.5 var(--qaren-font-en, system-ui)`,
              cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
            }}
          >
            <Icon size={16} color={active ? '#FFFFFF' : C.text.primary} />
            {label}
          </button>
        );
      })}
    </div>
  );
}

/* Smart pick of the day — replaces the GCC Pulse activity feed.
   Editorial card spotlighting one curated comparison from Qaren's data
   set. Reads as a "today's pick" not a feed — feels intentional, not
   data-sloppy. */
function SmartPickCard() {
  return (
    <section style={{ marginTop: 22 }}>
      <div style={{
        font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
        letterSpacing: '1.1px', textTransform: 'uppercase',
        color: C.text.secondary, marginBottom: 10,
      }}>
        Smart pick of the day
      </div>
      <article style={{
        padding: 16, borderRadius: 20,
        background: C.bg.secondary, border: `1px solid ${C.border.light}`,
        display: 'flex', flexDirection: 'column', gap: 14,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            paddingInline: 8, height: 22, borderRadius: 999,
            background: C.bg.primary, border: `1px solid ${C.border.light}`,
            font: '500 10px/1 var(--qaren-font-en, system-ui)',
            color: C.text.secondary, letterSpacing: '0.6px', textTransform: 'uppercase',
          }}>
            Electronics
          </span>
          <span style={{ font: '500 11px/1 var(--qaren-font-en, system-ui)', color: C.accentDark }}>
            Updated today
          </span>
        </div>

        <div style={{ position: 'relative', display: 'flex', gap: 10 }}>
          <PickTile tone="#E8E9ED" name="iPhone 15" sub="128GB" price="329 BHD" />
          <div style={{ position: 'absolute', insetBlockStart: '50%', insetInlineStart: '50%', transform: 'translate(-50%, -50%)' }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              height: 24, paddingInline: 10, borderRadius: 999,
              background: C.accentLight, color: C.accentDark,
              font: '700 11px/1 var(--qaren-font-en, system-ui)',
              letterSpacing: '1.1px', textTransform: 'uppercase',
              border: `2px solid ${C.bg.secondary}`,
            }}>vs</span>
          </div>
          <PickTile tone="#1B1C1F" name="Galaxy S24" sub="128GB" price="299 BHD" winner />
        </div>

        <p style={{
          margin: 0, font: '500 13px/1.5 var(--qaren-font-en, system-ui)',
          color: C.text.primary, textWrap: 'pretty',
        }}>
          Tap to see why Galaxy edged out Apple this week — camera + battery in a tighter package, ~30 BHD less.
        </p>

        <button style={{
          width: '100%', height: 40, borderRadius: 999,
          background: C.bg.primary, border: `1px solid ${C.text.primary}`,
          font: '600 13px/1 var(--qaren-font-en, system-ui)',
          color: C.text.primary, cursor: 'pointer',
        }}>
          See full verdict
        </button>
      </article>
    </section>
  );
}

function PickTile({ tone, name, sub, price, winner }) {
  return (
    <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{
        aspectRatio: '1 / 1', borderRadius: 12,
        background: tone, position: 'relative',
        display: 'grid', placeItems: 'center', color: 'rgba(0,0,0,0.18)',
        border: winner ? `2px solid ${C.accent}` : 'none',
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="5" y="2" width="14" height="20" rx="2.5"/>
        </svg>
        {winner && (
          <span style={{
            position: 'absolute', insetBlockStart: 4, insetInlineEnd: 4,
            width: 18, height: 18, borderRadius: 9, background: C.accent,
            display: 'grid', placeItems: 'center', border: `2px solid ${C.bg.secondary}`,
          }}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          </span>
        )}
      </div>
      <div>
        <div style={{ font: `${winner ? 700 : 600} 13px/1.3 var(--qaren-font-en, system-ui)`, color: C.text.primary }}>{name}</div>
        <div style={{ font: '400 11px/1.4 var(--qaren-font-en, system-ui)', color: C.text.secondary, marginTop: 1 }}>{sub} · {price}</div>
      </div>
    </div>
  );
}

/* Quick categories — single tap to jump straight to a primed Compare card. */
function QuickCategories() {
  const cats = [
    { v: 'electronics', label: 'Electronics', icon: '⌬' },
    { v: 'skincare',    label: 'Skincare',    icon: '✦' },
    { v: 'supplements', label: 'Supplements', icon: '◉' },
    { v: 'makeup',      label: 'Makeup',      icon: '◑' },
  ];
  return (
    <section style={{ marginTop: 22 }}>
      <div style={{
        font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
        letterSpacing: '1.1px', textTransform: 'uppercase',
        color: C.text.secondary, marginBottom: 10,
      }}>
        Jump back in
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
        {cats.map((c) => (
          <button key={c.v} style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '14px 14px', minHeight: 56,
            borderRadius: 14, background: C.bg.secondary, border: `1px solid ${C.border.light}`,
            font: '600 14px/1.3 var(--qaren-font-en, system-ui)', color: C.text.primary,
            cursor: 'pointer', textAlign: 'start',
          }}>
            <span style={{
              width: 28, height: 28, borderRadius: 14,
              background: C.bg.primary, display: 'grid', placeItems: 'center',
              color: C.accentDark, font: '700 14px/1 var(--qaren-font-en, system-ui)', flexShrink: 0,
            }}>{c.icon}</span>
            {c.label}
          </button>
        ))}
      </div>
    </section>
  );
}

/* Savings banner — surfaces the *value* Qaren delivers. */
function SavingsBanner() {
  return (
    <section style={{
      marginTop: 22,
      padding: '16px 18px',
      borderRadius: 18,
      background: C.bg.inverse, color: C.text.onInverse,
      display: 'flex', alignItems: 'center', gap: 14,
      position: 'relative', overflow: 'hidden',
    }}>
      <div aria-hidden="true" style={{
        position: 'absolute', insetBlockStart: -40, insetInlineEnd: -40,
        width: 110, height: 110, borderRadius: 55,
        border: `1.5px solid rgba(16,185,129,0.4)`,
      }} />
      <div aria-hidden="true" style={{
        position: 'absolute', insetBlockStart: -10, insetInlineEnd: 24,
        width: 7, height: 7, borderRadius: 4, background: C.accent,
      }} />
      <div style={{ flex: 1, position: 'relative' }}>
        <div style={{ font: '500 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '0.9px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.55)' }}>
          This month
        </div>
        <div style={{ font: '700 22px/1.15 var(--qaren-font-en, system-ui)', marginTop: 2 }}>
          ~240 BHD shopped smarter
        </div>
        <div style={{ font: '400 12px/1.4 var(--qaren-font-en, system-ui)', color: 'rgba(255,255,255,0.7)', marginTop: 2 }}>
          Across 8 decisions sorted with Qaren.
        </div>
      </div>
    </section>
  );
}

/* Trending near you — light tile, a casual "what your peers compared" hook. */
function TrendingNearYou() {
  const items = [
    { tag: 'Electronics', a: 'iPhone 15',  b: 'Galaxy S24',     count: 142 },
    { tag: 'Skincare',    a: 'CeraVe',     b: 'La Roche',       count: 88  },
    { tag: 'Supplements', a: 'Centrum',    b: 'One A Day',      count: 64  },
  ];
  return (
    <section style={{ marginTop: 22 }}>
      <div style={{
        font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
        letterSpacing: '1.1px', textTransform: 'uppercase',
        color: C.text.secondary, marginBottom: 10,
      }}>
        Trending in Capital
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {items.map((it, i) => (
          <button key={i} style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '12px 14px', minHeight: 56,
            borderRadius: 14, background: C.bg.secondary, border: `1px solid ${C.border.light}`,
            cursor: 'pointer', textAlign: 'start',
          }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center',
              paddingInline: 8, height: 20, borderRadius: 999,
              background: C.bg.primary, border: `1px solid ${C.border.light}`,
              font: '500 10px/1 var(--qaren-font-en, system-ui)',
              color: C.text.secondary, letterSpacing: '0.6px', textTransform: 'uppercase',
              flexShrink: 0,
            }}>{it.tag}</span>
            <div style={{ flex: 1, minWidth: 0, font: '500 13px/1.3 var(--qaren-font-en, system-ui)', color: C.text.primary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {it.a} <span style={{ color: C.accentDark, fontWeight: 700 }}>vs</span> {it.b}
            </div>
            <div style={{ font: '500 11px/1.3 var(--qaren-font-en, system-ui)', color: C.text.secondary, fontVariantNumeric: 'tabular-nums', flexShrink: 0 }}>
              {it.count} ↗
            </div>
          </button>
        ))}
      </div>
      <div style={{ height: 8 }} />
    </section>
  );
}

/* ─── HomeScreen composition ─── */
function HomeScreen() {
  const [mode, setMode] = useState('type');
  const [category, setCategory] = useState('electronics');
  const [a, setA] = useState('iPhone 15');
  const [b, setB] = useState('Galaxy S24');

  return (
    <div
      style={{
        display: 'flex', flexDirection: 'column',
        height: '100%',
        // iOS safe-area inset — clears status bar + dynamic island.
        // Lives on the screen (not IOSDevice) so each screen owns its inset.
        paddingTop: 50,
        background: C.bg.primary,
        fontFamily: 'var(--qaren-font-en, system-ui)',
        color: C.text.primary,
      }}
    >
      {/* Header */}
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        paddingInline: 20, paddingTop: 8, paddingBottom: 4,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <QarenLogo size={24} />
          <span style={{ font: '700 20px/1.2 var(--qaren-font-en, system-ui)' }}>Qaren</span>
        </div>
        <HeaderCounter free={2} total={3} bonus={1} />
      </header>

      <p style={{
        margin: 0,
        paddingInline: 20, paddingTop: 4, paddingBottom: 8,
        font: '600 16px/1.5 var(--qaren-font-en, system-ui)',
      }}>
        Compare anything.
      </p>

      <CategoryStrip value={category} onChange={setCategory} />

      <main style={{ flex: 1, paddingInline: 20, paddingTop: 8, paddingBottom: 16, overflow: 'auto' }}>
        <CompareCard
          mode={mode} setMode={setMode}
          productA={a} setA={setA}
          productB={b} setB={setB}
        />

        {/* Home-only content — distinct from History. A curated "Smart pick
            of the day", quick-jump categories, a savings stat, and
            trending pairs. No personal-history echo of the History tab. */}
        <SmartPickCard />
        <QuickCategories />
        <SavingsBanner />
        <TrendingNearYou />
      </main>

      <TabBar active="home" />
    </div>
  );
}

// Expose to other scripts.
window.QarenHomeScreen = HomeScreen;
