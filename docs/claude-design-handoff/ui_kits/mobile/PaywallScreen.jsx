/**
 * Qaren — PaywallScreen v3 (high-conversion, Qaren voice)
 *
 * Triggered when free comparisons run out (NEVER in onboarding — user
 * explicitly: "we won't show subscription in onboarding").
 *
 * v3 anatomy — lifted Cal AI's *conversion structure*, kept Qaren's calm:
 *
 *   1. Close X (top-left)
 *   2. HERO VISUAL — three stacked mini vs-pairs (the brand moment that
 *      shows what they're getting: more comparisons)
 *   3. Headline + sub
 *   4. SOCIAL PROOF strip: avatar dots + "Trusted by 5,000+ GCC shoppers"
 *      + 4.8★ rating pill
 *   5. PLAN CARDS — Yearly (hero, highlighted with "3 days free" badge
 *      and "Save ~70%" line) + Monthly (radio-quiet)
 *   6. 3-step trial timeline (quieter, below plans)
 *   7. Feature bullets (4 plain rows, emerald-circle checks)
 *   8. STICKY CTA — big black "Start My 3-Day Free Trial"
 *      + "No Payment Due Now" trust line below
 *      + fine print + Terms/Privacy/Restore links
 */

const T_pw3 = window.qarenTokens || {};
const C_pw3 = T_pw3.colors || {};

function HeroVisual() {
  const items = [
    { a: '#E8E9ED', b: '#1B1C1F', winnerB: true },
    { a: '#FBE6E6', b: '#FFEAD4', winnerA: true },
    { a: '#E6EEF9', b: '#FFF1DA', winnerB: true },
  ];
  return (
    <div style={{
      display: 'flex', justifyContent: 'center',
      gap: 8, paddingBlock: 16, paddingInline: 16,
    }}>
      {items.map((it, i) => (
        <div key={i} style={{
          flex: '0 0 auto',
          padding: 8, borderRadius: 12,
          background: C_pw3.bg.secondary, border: `1px solid ${C_pw3.border.light}`,
          transform: `translateY(${i === 1 ? '-6px' : '0'})`,
          boxShadow: i === 1 ? '0 4px 12px rgba(0,0,0,0.08)' : 'none',
        }}>
          <div style={{ position: 'relative', display: 'flex', gap: 4 }}>
            <div style={{
              width: 38, aspectRatio: '1 / 1', borderRadius: 8, background: it.a,
              border: it.winnerA ? `2px solid ${C_pw3.accent}` : 'none',
            }} />
            <div style={{ position: 'absolute', insetBlockStart: '50%', insetInlineStart: '50%', transform: 'translate(-50%, -50%)' }}>
              <span style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                height: 16, paddingInline: 5, borderRadius: 999,
                background: C_pw3.accentLight, color: C_pw3.accentDark,
                font: '700 8px/1 var(--qaren-font-en, system-ui)',
                letterSpacing: '0.8px', textTransform: 'uppercase',
                border: `1.5px solid ${C_pw3.bg.secondary}`,
              }}>vs</span>
            </div>
            <div style={{
              width: 38, aspectRatio: '1 / 1', borderRadius: 8, background: it.b,
              border: it.winnerB ? `2px solid ${C_pw3.accent}` : 'none',
            }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function SocialProof() {
  const avatars = ['#FCD9D2', '#E6EEF9', '#FFF1DA', '#FBE6E6', '#1B1C1F'];
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
      marginBottom: 18,
    }}>
      <div style={{ display: 'flex' }}>
        {avatars.map((c, i) => (
          <div key={i} style={{
            width: 24, height: 24, borderRadius: 12,
            background: c, marginInlineStart: i ? -8 : 0,
            border: `2px solid ${C_pw3.bg.primary}`,
            display: 'grid', placeItems: 'center',
            color: i === 4 ? '#fff' : 'rgba(0,0,0,0.4)',
            font: '700 9px/1 var(--qaren-font-en, system-ui)',
          }}>{['K','M','A','S','+'][i]}</div>
        ))}
      </div>
      <div style={{ font: '500 12px/1.4 var(--qaren-font-en, system-ui)', color: C_pw3.text.primary }}>
        Trusted by <span style={{ fontWeight: 700 }}>5,000+</span> GCC shoppers
      </div>
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        paddingInline: 8, height: 22, borderRadius: 999,
        background: C_pw3.accentLight, color: C_pw3.accentDark,
        font: '700 11px/1 var(--qaren-font-en, system-ui)',
      }}>
        <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>
        4.8
      </span>
    </div>
  );
}

function PlanCardLarge({ name, price, sub, eyebrow, selected, onSelect }) {
  return (
    <button
      onClick={onSelect}
      aria-pressed={selected}
      style={{
        width: '100%', minHeight: 92,
        padding: '14px 16px',
        borderRadius: 18,
        background: C_pw3.bg.primary,
        border: `${selected ? 2 : 1}px solid ${selected ? C_pw3.cta.primary : C_pw3.border.light}`,
        cursor: 'pointer', textAlign: 'start',
        position: 'relative',
        display: 'flex', alignItems: 'center', gap: 14,
        marginTop: eyebrow ? 14 : 8,
      }}
    >
      {eyebrow && (
        <span style={{
          position: 'absolute', insetBlockStart: -10, insetInlineStart: 16,
          paddingInline: 10, height: 22, borderRadius: 999,
          display: 'inline-flex', alignItems: 'center',
          background: C_pw3.accent, color: '#FFFFFF',
          font: '700 10px/1 var(--qaren-font-en, system-ui)',
          letterSpacing: '1px', textTransform: 'uppercase',
        }}>{eyebrow}</span>
      )}
      <div style={{
        width: 22, height: 22, borderRadius: 11, flexShrink: 0,
        border: `${selected ? 6 : 1.5}px solid ${selected ? C_pw3.cta.primary : C_pw3.border.medium}`,
        background: selected ? C_pw3.bg.primary : 'transparent',
      }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ font: '700 17px/1.3 var(--qaren-font-en, system-ui)', color: C_pw3.text.primary }}>{name}</span>
        </div>
        <div style={{ font: '400 12px/1.4 var(--qaren-font-en, system-ui)', color: C_pw3.text.secondary, marginTop: 4 }}>
          {sub}
        </div>
      </div>
      <div style={{ textAlign: 'end', flexShrink: 0 }}>
        <div style={{ font: '700 18px/1 var(--qaren-font-en, system-ui)', color: C_pw3.text.primary, fontVariantNumeric: 'tabular-nums' }}>
          {price}
        </div>
      </div>
    </button>
  );
}

function FeatureLine({ text }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingBlock: 6 }}>
      <span style={{
        width: 18, height: 18, borderRadius: 9, background: C_pw3.accentLight,
        display: 'grid', placeItems: 'center', flexShrink: 0,
      }}>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke={C_pw3.accentDark} strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      </span>
      <span style={{ font: '500 13px/1.4 var(--qaren-font-en, system-ui)', color: C_pw3.text.primary }}>
        {text}
      </span>
    </div>
  );
}

function QarenPaywallScreen() {
  const [plan, setPlan] = React.useState('yearly');
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: C_pw3.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_pw3.text.primary,
    }}>
      {/* Top close */}
      <header style={{ display: 'flex', alignItems: 'center', paddingInline: 16, paddingBlock: 4 }}>
        <button aria-label="Close" style={{
          width: 36, height: 36, borderRadius: 18,
          background: C_pw3.bg.secondary, border: 'none',
          display: 'grid', placeItems: 'center', cursor: 'pointer',
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_pw3.text.primary} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', paddingInline: 20, paddingBottom: 12 }}>
        <HeroVisual />

        <h1 style={{
          margin: '4px 0 6px',
          font: '700 26px/1.2 var(--qaren-font-en, system-ui)',
          letterSpacing: '-0.3px', textWrap: 'pretty', textAlign: 'center',
        }}>
          Keep deciding with <span style={{ color: C_pw3.accent }}>confidence</span>.
        </h1>
        <p style={{
          margin: '0 0 18px', font: '400 14px/1.5 var(--qaren-font-en, system-ui)',
          color: C_pw3.text.secondary, textAlign: 'center', maxWidth: 320, marginInline: 'auto',
        }}>
          Unlimited comparisons, deeper reviews, full price history.
        </p>

        <SocialProof />

        {/* Plans */}
        <PlanCardLarge
          name="Yearly"
          price="0.9 BHD/mo"
          sub="10.8 BHD billed yearly · Save ~70%"
          eyebrow="3 days free · Best value"
          selected={plan === 'yearly'}
          onSelect={() => setPlan('yearly')}
        />
        <PlanCardLarge
          name="Monthly"
          price="2.9 BHD"
          sub="Billed monthly · Cancel anytime"
          selected={plan === 'monthly'}
          onSelect={() => setPlan('monthly')}
        />

        {/* Features */}
        <section style={{
          marginTop: 18, padding: '12px 16px', borderRadius: 16,
          background: C_pw3.bg.secondary, border: `1px solid ${C_pw3.border.light}`,
        }}>
          <FeatureLine text="70 comparisons per month" />
          <FeatureLine text="Full price history across 25+ GCC retailers" />
          <FeatureLine text="Priority processing — results in under 8 seconds" />
          <FeatureLine text="Ad-free, always" />
        </section>

        {/* Mini timeline below — quieter than v2 */}
        <div style={{ marginTop: 16, padding: '12px 14px', borderRadius: 14, border: `1px dashed ${C_pw3.border.light}` }}>
          <div style={{ font: '600 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '0.8px', textTransform: 'uppercase', color: C_pw3.text.secondary, marginBottom: 8 }}>
            How the trial works
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, font: '500 12px/1.4 var(--qaren-font-en, system-ui)', color: C_pw3.text.primary }}>
            <div><span style={{ color: C_pw3.accentDark, fontWeight: 700 }}>Today</span> · Unlock everything immediately.</div>
            <div><span style={{ color: C_pw3.text.secondary, fontWeight: 700 }}>In 2 days</span> · Gentle reminder before billing.</div>
            <div><span style={{ color: C_pw3.text.secondary, fontWeight: 700 }}>In 3 days</span> · Billing starts — cancel anytime.</div>
          </div>
        </div>
      </main>

      <div style={{
        paddingInline: 20, paddingTop: 12, paddingBottom: 16,
        borderTop: `1px solid ${C_pw3.border.light}`,
        background: C_pw3.bg.primary,
      }}>
        <button style={{
          width: '100%', height: 56, borderRadius: 999, border: 'none',
          background: C_pw3.cta.primary, color: C_pw3.cta.onPrimary,
          font: '700 17px/1 var(--qaren-font-en, system-ui)', cursor: 'pointer',
          boxShadow: '0 4px 12px rgba(0,0,0,0.12)',
        }}>
          Start My 3-Day Free Trial
        </button>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          marginTop: 10,
          font: '500 12px/1.4 var(--qaren-font-en, system-ui)', color: C_pw3.text.secondary,
        }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={C_pw3.accentDark} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          No payment due now · Cancel anytime
        </div>
        <div style={{
          display: 'flex', justifyContent: 'center', gap: 14, marginTop: 6,
          font: '500 11px/1 var(--qaren-font-en, system-ui)', color: C_pw3.text.placeholder,
        }}>
          <span>Terms</span><span>·</span><span>Privacy</span><span>·</span><span>Restore</span>
        </div>
      </div>
    </div>
  );
}

window.QarenPaywallScreen = QarenPaywallScreen;
