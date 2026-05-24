/**
 * Qaren — OnboardingWelcomeScreen (s1)
 *
 * Source: en.json onboarding.s1.* — "Look closer. Decide smarter."
 *
 * The very first screen after splash. Warm-wash background (matches the
 * splash treatment so they feel like one continuous moment). Three beats
 * of copy + big black CTA + secondary sign-in link.
 */

const T_ow = window.qarenTokens || {};
const C_ow = T_ow.colors || {};

function QarenOnboardingWelcomeScreen() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: `radial-gradient(120% 60% at 0% 0%, rgba(255,200,160,0.22) 0%, rgba(255,200,160,0) 55%),
                   radial-gradient(120% 60% at 100% 0%, rgba(190,200,255,0.22) 0%, rgba(190,200,255,0) 55%),
                   ${C_ow.bg.primary}`,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_ow.text.primary,
    }}>
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', paddingInline: 24, paddingTop: 24, paddingBottom: 16 }}>
        <div>
          <QarenLogo size={40} />
          <h1 style={{
            margin: '36px 0 0',
            font: '700 38px/1.1 var(--qaren-font-en, system-ui)',
            letterSpacing: '-0.5px', textWrap: 'pretty',
          }}>
            Look closer.<br />Decide smarter.
          </h1>
          <p style={{
            margin: '14px 0 0',
            font: '400 16px/1.5 var(--qaren-font-en, system-ui)', color: C_ow.text.secondary,
            maxWidth: 320,
          }}>
            Built for the GCC. By people like you.
          </p>
        </div>

        {/* Pull-quote pair as a visual hint */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <QuoteRow text="“Picked Galaxy — camera + battery edged out Apple here.”" />
          <QuoteRow text="“Picked La Roche — matched my sensitive-skin tag.”" />
          <QuoteRow text="“Picked Centrum — better nutrient profile.”" />
        </div>

        <div>
          <button style={{
            width: '100%', height: 56, borderRadius: 999,
            background: C_ow.cta.primary, color: C_ow.cta.onPrimary,
            border: 'none', cursor: 'pointer',
            font: '700 16px/1 var(--qaren-font-en, system-ui)',
          }}>
            Continue
          </button>
          <button style={{
            width: '100%', height: 44, marginTop: 6,
            background: 'transparent', border: 'none',
            color: C_ow.text.secondary,
            font: '500 13px/1.5 var(--qaren-font-en, system-ui)', cursor: 'pointer',
          }}>
            Already have an account? <span style={{ color: C_ow.text.primary, textDecoration: 'underline' }}>Sign in</span>
          </button>
        </div>
      </main>
    </div>
  );
}

function QuoteRow({ text }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '10px 14px',
      borderRadius: 14,
      background: 'rgba(255,255,255,0.55)',
      border: `1px solid ${C_ow.border.light}`,
      backdropFilter: 'blur(8px)',
      font: '500 13px/1.4 var(--qaren-font-en, system-ui)', color: C_ow.text.primary,
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: 3, background: C_ow.accent, flexShrink: 0,
      }} />
      {text}
    </div>
  );
}

window.QarenOnboardingWelcomeScreen = QarenOnboardingWelcomeScreen;
