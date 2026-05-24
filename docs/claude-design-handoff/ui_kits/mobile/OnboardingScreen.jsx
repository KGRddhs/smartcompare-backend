/**
 * Qaren — OnboardingScreen (reference, web)
 *
 * Source of truth: AI/smartcompare/SmartCompareApp/src/screens/OnboardingScreen.tsx
 *
 * This is the "What matters most when you buy?" priorities pick (en.json
 * key `onboarding.s8.*`). Demonstrates the Cal AI-inspired icon-in-circle
 * option row pattern + the optional warm wash on the background.
 *
 * Tweakable (via TweaksPanel in index.html):
 *   - rowStyle: 'icon-circle' (default · new Cal AI pattern)
 *              | 'plain' (text only · current production)
 *   - wash:     true (default for onboarding) | false (pure white)
 *
 * Both tweaks can be flipped live so the user can compare and revert. The
 * pattern is held to the same brand rules: black-on-select, 16px row
 * radius, 44pt min height, no shake, calm copy.
 */

const T_ob = window.qarenTokens || {};
const C_ob = T_ob.colors || {};
const R_ob = T_ob.radii || {};

const PRIORITIES = [
  { value: 'price',     label: 'Best price',     icon: (c) => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>) },
  { value: 'quality',   label: 'Quality',        icon: (c) => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>) },
  { value: 'brand',     label: 'Trusted brand',  icon: (c) => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-7 8-13a8 8 0 0 0-16 0c0 6 8 13 8 13z"/></svg>) },
  { value: 'durable',   label: 'Built to last',  icon: (c) => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2 3 7v5c0 5 4 9 9 10 5-1 9-5 9-10V7l-9-5z"/></svg>) },
  { value: 'features',  label: 'Latest features',icon: (c) => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>) },
  { value: 'easy',      label: 'Easy to use',    icon: (c) => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="6.34" y2="6.34"/><line x1="17.66" y1="17.66" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/></svg>) },
  { value: 'eco',       label: 'Eco-friendly',   icon: (c) => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 20A7 7 0 0 1 4 13c0-2 1-5 4-8 0 0 1 4 6 4s8 0 8 8a7 7 0 0 1-11 3z"/></svg>) },
  { value: 'health',    label: 'Health & safety',icon: (c) => (<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>) },
];

const MAX_PICKS = 3;

function OptionRow({ option, active, onToggle, style /* 'icon-circle' | 'plain' */ }) {
  const showIcon = style === 'icon-circle';
  return (
    <button
      onClick={onToggle}
      aria-pressed={active}
      style={{
        display: 'flex', alignItems: 'center', gap: 14,
        paddingBlock: 14, paddingInline: showIcon ? 12 : 18,
        minHeight: 60,
        width: '100%',
        textAlign: 'start',
        borderRadius: 16,
        border: `1px solid ${active ? C_ob.cta.primary : C_ob.border.light}`,
        background: active ? C_ob.cta.primary : C_ob.bg.secondary,
        color: active ? C_ob.cta.onPrimary : C_ob.text.primary,
        font: '600 16px/1.4 var(--qaren-font-en, system-ui)',
        cursor: 'pointer',
        transition: 'background 180ms cubic-bezier(0.32,0.72,0,1), border-color 180ms ease',
      }}
    >
      {showIcon && (
        <span
          aria-hidden="true"
          style={{
            width: 36, height: 36, borderRadius: 18,
            background: C_ob.bg.primary,
            display: 'grid', placeItems: 'center', flexShrink: 0,
          }}
        >
          {option.icon(C_ob.text.primary)}
        </span>
      )}
      <span>{option.label}</span>
    </button>
  );
}

function QarenOnboardingScreen({ rowStyle = 'icon-circle', wash = true }) {
  const [picks, setPicks] = React.useState(new Set(['price']));
  const toggle = (v) => {
    setPicks((prev) => {
      const next = new Set(prev);
      if (next.has(v)) next.delete(v);
      else if (next.size < MAX_PICKS) next.add(v);
      return next;
    });
  };
  const canContinue = picks.size > 0;

  const washBg = wash
    ? `radial-gradient(120% 60% at 0% 0%, rgba(255,200,160,0.18) 0%, rgba(255,200,160,0) 55%),
       radial-gradient(120% 60% at 100% 0%, rgba(190,200,255,0.18) 0%, rgba(190,200,255,0) 55%),
       ${C_ob.bg.primary}`
    : C_ob.bg.primary;

  return (
    <div
      style={{
        display: 'flex', flexDirection: 'column',
        height: '100%', paddingTop: 50,
        background: washBg,
        fontFamily: 'var(--qaren-font-en, system-ui)',
        color: C_ob.text.primary,
      }}
    >
      {/* Header — back + progress bar */}
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, paddingInline: 20, paddingTop: 8, paddingBottom: 16 }}>
        <button
          aria-label="Back"
          style={{
            width: 36, height: 36, borderRadius: 18,
            background: C_ob.bg.secondary, border: 'none',
            display: 'grid', placeItems: 'center', cursor: 'pointer', flexShrink: 0,
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_ob.text.primary} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
        <div style={{ flex: 1, height: 4, borderRadius: 2, background: C_ob.border.light, overflow: 'hidden' }}>
          <div style={{ width: '55%', height: '100%', background: C_ob.cta.primary }} />
        </div>
      </header>

      {/* Title + subtitle */}
      <div style={{ paddingInline: 20, marginBottom: 20 }}>
        <h1 style={{ margin: 0, font: '700 28px/1.2 var(--qaren-font-en, system-ui)', letterSpacing: '-0.28px', textWrap: 'pretty' }}>
          What matters most when you buy?
        </h1>
        <p style={{ margin: '8px 0 0', font: '400 15px/1.5 var(--qaren-font-en, system-ui)', color: C_ob.text.secondary }}>
          Pick up to {MAX_PICKS}
        </p>
      </div>

      {/* Options */}
      <div style={{ flex: 1, overflowY: 'auto', paddingInline: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {PRIORITIES.map((opt) => (
          <OptionRow
            key={opt.value}
            option={opt}
            active={picks.has(opt.value)}
            onToggle={() => toggle(opt.value)}
            style={rowStyle}
          />
        ))}
        <div style={{ height: 24 }} />
      </div>

      {/* Sticky CTA */}
      <div style={{
        paddingInline: 20, paddingTop: 12, paddingBottom: 16,
        borderTop: `1px solid ${C_ob.border.light}`,
        background: C_ob.bg.primary,
      }}>
        <button
          disabled={!canContinue}
          style={{
            width: '100%', height: 52,
            borderRadius: 999,
            border: 'none',
            background: C_ob.cta.primary,
            color: C_ob.cta.onPrimary,
            font: '600 16px/1.5 var(--qaren-font-en, system-ui)',
            opacity: canContinue ? 1 : 0.5,
            cursor: canContinue ? 'pointer' : 'not-allowed',
          }}
        >
          Continue
        </button>
      </div>
    </div>
  );
}

window.QarenOnboardingScreen = QarenOnboardingScreen;
