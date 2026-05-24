/**
 * Qaren — ScanCameraScreen (reference, web)
 *
 * Source of truth: AI/smartcompare/SmartCompareApp/src/screens/ScanCameraScreen.tsx
 *
 * Full-bleed camera surface — the only screen in the app where chrome
 * sits on a dark/full-bleed background. Anatomy:
 *
 *   1. Faux camera viewfinder (gradient + scanline) — placeholder for the
 *      real expo-camera feed
 *   2. Top bar — Close (X) on the left, slot indicator "1 of 2" centered,
 *      help icon on the right
 *   3. Viewfinder reticle — 4 corner brackets with rounded inner radius
 *   4. Bottom — captured-slot thumbnails (one filled, one empty), then
 *      gallery / shutter / flash row, then the "Compare" CTA
 *
 * Copy from en.json: "home.camera.tap_to_scan", "home.camera.slot".
 * Build Principle #4 still holds — no scary state copy.
 */

const T_sc = window.qarenTokens || {};
const C_sc = T_sc.colors || {};

function Reticle() {
  const corner = (style) => (
    <div style={{
      position: 'absolute', width: 28, height: 28,
      borderColor: 'rgba(255,255,255,0.9)',
      borderStyle: 'solid', borderWidth: 0,
      ...style,
    }} />
  );
  return (
    <div style={{
      position: 'absolute', insetInlineStart: '50%', insetBlockStart: '50%',
      transform: 'translate(-50%, -50%)',
      width: 260, height: 260,
    }}>
      {corner({ insetBlockStart: 0, insetInlineStart: 0, borderTopWidth: 3, borderInlineStartWidth: 3, borderStartStartRadius: 12 })}
      {corner({ insetBlockStart: 0, insetInlineEnd: 0, borderTopWidth: 3, borderInlineEndWidth: 3, borderStartEndRadius: 12 })}
      {corner({ insetBlockEnd: 0, insetInlineStart: 0, borderBottomWidth: 3, borderInlineStartWidth: 3, borderEndStartRadius: 12 })}
      {corner({ insetBlockEnd: 0, insetInlineEnd: 0, borderBottomWidth: 3, borderInlineEndWidth: 3, borderEndEndRadius: 12 })}
    </div>
  );
}

function CamPill({ children, onClick }) {
  return (
    <button onClick={onClick} style={{
      paddingInline: 14, height: 36, borderRadius: 999,
      background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)',
      border: '1px solid rgba(255,255,255,0.2)',
      color: '#FFFFFF',
      font: '500 13px/1 var(--qaren-font-en, system-ui)',
      cursor: 'pointer',
      display: 'inline-flex', alignItems: 'center', gap: 6,
      whiteSpace: 'nowrap', minWidth: 60,
    }}>{children}</button>
  );
}

function CircleBtn({ children, size = 44, onClick, label }) {
  return (
    <button aria-label={label} onClick={onClick} style={{
      width: size, height: size, borderRadius: size / 2,
      background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)',
      border: '1px solid rgba(255,255,255,0.2)',
      color: '#FFFFFF',
      display: 'grid', placeItems: 'center', cursor: 'pointer',
    }}>{children}</button>
  );
}

function SlotThumb({ filled, tone }) {
  return (
    <div style={{
      width: 56, height: 56, borderRadius: 12,
      background: filled ? tone : 'rgba(255,255,255,0.1)',
      border: `1.5px solid ${filled ? C_sc.accent : 'rgba(255,255,255,0.3)'}`,
      display: 'grid', placeItems: 'center',
      color: filled ? 'rgba(0,0,0,0.4)' : 'rgba(255,255,255,0.4)',
      position: 'relative',
    }}>
      {filled ? (
        <>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="5" y="2" width="14" height="20" rx="2.5"/></svg>
          <span style={{
            position: 'absolute', insetBlockStart: -4, insetInlineEnd: -4,
            width: 16, height: 16, borderRadius: 8, background: C_sc.accent,
            display: 'grid', placeItems: 'center', border: '2px solid #0A0A0B',
          }}>
            <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </span>
        </>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>
      )}
    </div>
  );
}

function QarenScanCameraScreen() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: '#0A0A0B', color: '#FFFFFF',
      fontFamily: 'var(--qaren-font-en, system-ui)',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Faux camera feed — soft gradient simulating an out-of-focus shot */}
      <div aria-hidden="true" style={{
        position: 'absolute', inset: 0,
        background: 'radial-gradient(60% 50% at 50% 45%, #2A2D33 0%, #14161A 70%, #0A0B0D 100%)',
      }} />
      {/* faint scanline */}
      <div aria-hidden="true" style={{
        position: 'absolute', insetInlineStart: 0, insetInlineEnd: 0,
        top: '50%', height: 1, background: 'linear-gradient(90deg, transparent, rgba(16,185,129,0.45), transparent)',
      }} />

      <Reticle />

      {/* Top bar */}
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingInline: 16, paddingTop: 8 }}>
        <CircleBtn label="Close">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </CircleBtn>
        <CamPill>
          1 of 2
        </CamPill>
        <CircleBtn label="Help">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </CircleBtn>
      </div>

      {/* Hint text */}
      <div style={{
        position: 'absolute', insetBlockStart: '24%', insetInlineStart: 0, insetInlineEnd: 0,
        textAlign: 'center',
        font: '600 16px/1.4 var(--qaren-font-en, system-ui)', color: '#FFFFFF',
      }}>
        Center the product
        <div style={{ font: '400 13px/1.5 var(--qaren-font-en, system-ui)', color: 'rgba(255,255,255,0.65)', marginTop: 4 }}>
          Fit the whole product in the brackets
        </div>
      </div>

      <div style={{ flex: 1 }} />

      {/* Slot thumbs */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginBottom: 16, position: 'relative' }}>
        <SlotThumb filled tone="#E8E9ED" />
        <SlotThumb />
      </div>

      {/* Capture row — gallery / shutter / flash */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingInline: 32, position: 'relative' }}>
        <CircleBtn size={48} label="Gallery">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
        </CircleBtn>
        <button aria-label="Capture" style={{
          width: 76, height: 76, borderRadius: 38,
          background: '#FFFFFF', border: '4px solid rgba(255,255,255,0.4)',
          boxShadow: '0 0 0 2px #0A0A0B inset',
          cursor: 'pointer',
        }} />
        <CircleBtn size={48} label="Flash">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M13 2L4 14h7v8l9-12h-7V2z"/></svg>
        </CircleBtn>
      </div>

      {/* Compare CTA */}
      <div style={{ paddingInline: 20, paddingTop: 16, paddingBottom: 16, position: 'relative' }}>
        <button disabled style={{
          width: '100%', height: 52, borderRadius: 999,
          background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)',
          border: '1px solid rgba(255,255,255,0.2)',
          color: '#FFFFFF',
          font: '600 16px/1 var(--qaren-font-en, system-ui)',
          cursor: 'not-allowed',
          opacity: 0.6,
        }}>
          Snap one more to compare
        </button>
      </div>
    </div>
  );
}

window.QarenScanCameraScreen = QarenScanCameraScreen;
