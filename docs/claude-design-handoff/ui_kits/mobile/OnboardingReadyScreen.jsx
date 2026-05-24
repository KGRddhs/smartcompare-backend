/**
 * Qaren — OnboardingReadyScreen (s15 — "Your shopping advisor is ready")
 *
 * The pay-off moment at the end of onboarding. Big "Match" emerald badge
 * + a stat grid showing the profile that was built (top priority, budget
 * tier, peer count), then the "Compare your first product" CTA.
 *
 * Copy from en.json onboarding.s15.*.
 */

const T_or = window.qarenTokens || {};
const C_or = T_or.colors || {};

function StatBlock({ label, value, accent }) {
  return (
    <div style={{
      flex: 1, minWidth: 0,
      padding: 14, borderRadius: 16,
      background: C_or.bg.secondary, border: `1px solid ${C_or.border.light}`,
    }}>
      <div style={{ font: '500 11px/1.3 var(--qaren-font-en, system-ui)', color: C_or.text.secondary, letterSpacing: '0.4px', textTransform: 'uppercase' }}>
        {label}
      </div>
      <div style={{ font: '700 18px/1.2 var(--qaren-font-en, system-ui)', color: accent ? C_or.accent : C_or.text.primary, marginTop: 6 }}>
        {value}
      </div>
    </div>
  );
}

function QarenOnboardingReadyScreen() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: C_or.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_or.text.primary,
    }}>
      {/* Progress bar */}
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, paddingInline: 20, paddingTop: 8, paddingBottom: 16 }}>
        <div style={{ flex: 1, height: 4, borderRadius: 2, background: C_or.border.light, overflow: 'hidden' }}>
          <div style={{ width: '100%', height: '100%', background: C_or.accent }} />
        </div>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', paddingInline: 24, display: 'flex', flexDirection: 'column' }}>
        {/* Big match badge */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
          paddingBlock: 24,
        }}>
          <div style={{
            width: 88, height: 88, borderRadius: 44,
            background: C_or.accentLight, color: C_or.accentDark,
            display: 'grid', placeItems: 'center',
            position: 'relative',
          }}>
            <span style={{
              position: 'absolute', insetBlockStart: 6, insetInlineEnd: 8,
              font: '700 14px/1 var(--qaren-font-en, system-ui)',
              color: C_or.accent,
            }}>✦</span>
            <span style={{ font: '700 30px/1 var(--qaren-font-en, system-ui)' }}>92%</span>
          </div>
          <div style={{ font: '600 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '1.1px', textTransform: 'uppercase', color: C_or.accentDark }}>
            Strong match
          </div>
        </div>

        <h1 style={{
          margin: '4px 0 8px',
          font: '700 28px/1.2 var(--qaren-font-en, system-ui)',
          letterSpacing: '-0.32px', textAlign: 'center', textWrap: 'pretty',
        }}>
          Your shopping advisor is ready.
        </h1>
        <p style={{
          margin: '0 0 24px',
          font: '400 14px/1.5 var(--qaren-font-en, system-ui)', color: C_or.text.secondary,
          textAlign: 'center', maxWidth: 320, marginInline: 'auto',
        }}>
          Tuned to your priorities. Trained by your peers.
        </p>

        <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
          <StatBlock label="Top priority" value="Quality" accent />
          <StatBlock label="Budget tier" value="Mid-range" />
        </div>
        <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
          <StatBlock label="Peers in Capital" value="2,000+" />
          <StatBlock label="GCC cohort" value="15,000+" />
        </div>
      </main>

      <div style={{
        paddingInline: 20, paddingTop: 12, paddingBottom: 16,
        borderTop: `1px solid ${C_or.border.light}`, background: C_or.bg.primary,
      }}>
        <button style={{
          width: '100%', height: 56, borderRadius: 999, border: 'none',
          background: C_or.cta.primary, color: C_or.cta.onPrimary,
          font: '700 16px/1 var(--qaren-font-en, system-ui)', cursor: 'pointer',
        }}>
          Compare your first product
        </button>
      </div>
    </div>
  );
}

window.QarenOnboardingReadyScreen = QarenOnboardingReadyScreen;
