/**
 * Qaren — canonical Q logo (shared)
 *
 * This is THE Qaren mark — magnifier ring + handle tail + emerald accent
 * dot at top-right. Every surface that shows the Qaren glyph imports
 * this so they're pixel-identical. Source recipe lives in
 * src/components/QarenLogo.tsx and src/icons/QaranIcon.tsx in the native
 * app; we keep this file as the web canonical.
 *
 * Sizes prop scales linearly off a 32×32 viewBox. The accent dot stays
 * proportional — 2px out of 32 = ~6% of size.
 */

function QarenLogo({ size = 28, color }) {
  const C = (window.qarenTokens && window.qarenTokens.colors) || {};
  const ink = color || C.text?.primary || '#0A0A0B';
  const accent = C.accent || '#10B981';
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      style={{ flexShrink: 0 }}
    >
      <circle cx="16" cy="16" r="13" stroke={ink} strokeWidth="2.5" fill="none" />
      <path d="M22 22 L27 27" stroke={ink} strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="22" cy="11" r="2" fill={accent} />
    </svg>
  );
}

window.QarenLogo = QarenLogo;
