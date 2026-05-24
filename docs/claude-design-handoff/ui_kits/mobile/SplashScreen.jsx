/**
 * Qaren — SplashScreen (reference, web)
 *
 * Source of truth: AI/smartcompare/SmartCompareApp/src/screens/SplashScreen.tsx
 *
 * App launch screen. Anatomy is minimal — this is a brand moment, not a
 * functional screen. The warm wash (peach top-left, lavender top-right)
 * is the Cal-AI-inspired splash treatment we agreed to reserve for the
 * very first surfaces (Splash + onboarding s1). Below the wash:
 *
 *   - Large Q lens glyph (magnifier + emerald accent dot, the QarenLogo
 *     mark at hero scale)
 *   - "Qaren" wordmark
 *   - tagline: "Compare smarter"
 *
 * No CTA — the app auto-advances after font load. In a real session this
 * holds for ~1.2s while fonts + auth state resolve.
 */

const T_sp = window.qarenTokens || {};
const C_sp = T_sp.colors || {};

function QarenLensGlyph({ size = 120 }) {
  const stroke = Math.max(4, size * 0.06);
  const dotSize = size * 0.12;
  return (
    <div style={{
      position: 'relative', width: size + 36, height: size + 18,
      display: 'grid', placeItems: 'center',
    }}>
      <div style={{
        position: 'absolute',
        width: size, height: size, borderRadius: size / 2,
        border: `${stroke}px solid ${C_sp.text.primary}`,
      }} />
      <div style={{
        position: 'absolute',
        insetBlockEnd: 6, insetInlineEnd: 12,
        width: size * 0.34, height: stroke,
        borderRadius: stroke / 2,
        background: C_sp.text.primary,
        transform: 'rotate(45deg)', transformOrigin: 'right center',
      }} />
      <div style={{
        position: 'absolute',
        insetBlockStart: size * 0.08, insetInlineEnd: size * 0.13,
        width: dotSize, height: dotSize, borderRadius: dotSize / 2,
        background: C_sp.accent,
        boxShadow: `0 0 0 ${stroke * 0.6}px ${C_sp.bg.primary}`,
      }} />
    </div>
  );
}

function QarenSplashScreen() {
  const C = (window.qarenTokens && window.qarenTokens.colors) || {};
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      alignItems: 'center', justifyContent: 'center', gap: 22,
      background: `radial-gradient(120% 60% at 0% 0%, rgba(255,200,160,0.22) 0%, rgba(255,200,160,0) 55%),
                   radial-gradient(120% 60% at 100% 0%, rgba(190,200,255,0.22) 0%, rgba(190,200,255,0) 55%),
                   ${C.bg?.primary || '#FFFFFF'}`,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C.text?.primary || '#0A0A0B',
    }}>
      <QarenLogo size={128} />
      <div style={{ font: '700 40px/1 var(--qaren-font-en, system-ui)', letterSpacing: '-0.8px' }}>
        Qaren
      </div>
      <div style={{ font: '400 15px/1.5 var(--qaren-font-en, system-ui)', color: C.text?.secondary || '#6B7280' }}>
        Compare smarter
      </div>
    </div>
  );
}

window.QarenSplashScreen = QarenSplashScreen;
