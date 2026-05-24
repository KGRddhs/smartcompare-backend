/**
 * Qaren — OnboardingCohortScreen (s12 — "388 GCC shoppers helped train this")
 *
 * Source of truth: AI/smartcompare/SmartCompareApp/src/screens/OnboardingScreen.tsx
 *                  (s12 step, copy keys onboarding.s12.*)
 *
 * The peer-validation moment in onboarding — telling the user that their
 * recommendations are grounded in real GCC shoppers, not a global model.
 * This is the screen that earns the cohort claim.
 *
 * Layout:
 *   - Back button + progress bar (75%)
 *   - Display headline with the 388 highlighted in emerald
 *   - 3 bullet points (real people, GCC-calibrated, peers refine it)
 *   - A horizontal row of peer dots (visualizing 388)
 *   - Continue CTA
 */

const T_ob12 = window.qarenTokens || {};
const C_ob12 = T_ob12.colors || {};

function CohortBullet({ children }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
      <span style={{
        width: 24, height: 24, borderRadius: 12, flexShrink: 0,
        background: C_ob12.accentLight, color: C_ob12.accentDark,
        display: 'grid', placeItems: 'center', marginTop: 1,
      }}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      </span>
      <div style={{ font: '500 15px/1.5 var(--qaren-font-en, system-ui)', color: C_ob12.text.primary, textWrap: 'pretty' }}>
        {children}
      </div>
    </div>
  );
}

function PeerLattice() {
  // 8 rows × 12 cols dot lattice with falloff opacity. Centre cell has
  // a larger emerald YOU dot.
  const cols = 12, rows = 7;
  const cells = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      cells.push({ r, c, distance: Math.hypot(c - (cols - 1) / 2, r - (rows - 1) / 2) });
    }
  }
  return (
    <div style={{ position: 'relative', display: 'grid', placeItems: 'center', marginBlock: 18 }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: 7,
        width: '100%', maxWidth: 320,
      }}>
        {cells.map(({ r, c, distance }, i) => {
          const isCentre = r === (rows - 1) / 2 && c === (cols - 1) / 2;
          const opacity = Math.max(0.15, 0.85 - distance * 0.10);
          return (
            <div key={i} style={{
              aspectRatio: '1 / 1',
              borderRadius: '50%',
              background: isCentre ? 'transparent' : C_ob12.text.primary,
              opacity: isCentre ? 0 : opacity,
            }} />
          );
        })}
      </div>
      <div style={{
        position: 'absolute', insetBlockStart: '50%', insetInlineStart: '50%',
        transform: 'translate(-50%, -50%)',
        width: 20, height: 20, borderRadius: 10,
        background: C_ob12.accent,
        boxShadow: `0 0 0 4px ${C_ob12.bg.primary}, 0 0 0 6px ${C_ob12.accent}`,
      }} />
    </div>
  );
}

function QarenOnboardingCohortScreen() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: C_ob12.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_ob12.text.primary,
    }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, paddingInline: 20, paddingTop: 8, paddingBottom: 16 }}>
        <button aria-label="Back" style={{
          width: 36, height: 36, borderRadius: 18,
          background: C_ob12.bg.secondary, border: 'none',
          display: 'grid', placeItems: 'center', cursor: 'pointer', flexShrink: 0,
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_ob12.text.primary} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
        <div style={{ flex: 1, height: 4, borderRadius: 2, background: C_ob12.border.light, overflow: 'hidden' }}>
          <div style={{ width: '75%', height: '100%', background: C_ob12.cta.primary }} />
        </div>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', paddingInline: 20 }}>
        <h1 style={{ margin: '8px 0 12px', font: '700 30px/1.15 var(--qaren-font-en, system-ui)', letterSpacing: '-0.36px', textWrap: 'pretty' }}>
          You're joining <span style={{ color: C_ob12.accent }}>15,000+ GCC shoppers</span>.
        </h1>
        <p style={{ margin: '0 0 24px', font: '400 14px/1.5 var(--qaren-font-en, system-ui)', color: C_ob12.text.secondary }}>
          Real picks from real people across the Gulf — sharper than a global average could ever be.
        </p>

        <PeerLattice />

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 8 }}>
          <CohortBullet>Picks rooted in your region — Bahrain, KSA, UAE, and beyond.</CohortBullet>
          <CohortBullet>Calibrated for the GCC — not a global average.</CohortBullet>
          <CohortBullet>Every comparison sharpens the match for everyone.</CohortBullet>
        </div>
      </main>

      <div style={{
        paddingInline: 20, paddingTop: 12, paddingBottom: 16,
        borderTop: `1px solid ${C_ob12.border.light}`, background: C_ob12.bg.primary,
      }}>
        <button style={{
          width: '100%', height: 52, borderRadius: 999, border: 'none',
          background: C_ob12.cta.primary, color: C_ob12.cta.onPrimary,
          font: '600 16px/1.5 var(--qaren-font-en, system-ui)', cursor: 'pointer',
        }}>
          Continue
        </button>
      </div>
    </div>
  );
}

window.QarenOnboardingCohortScreen = QarenOnboardingCohortScreen;
