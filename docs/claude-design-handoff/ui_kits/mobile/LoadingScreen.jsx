/**
 * Qaren — LoadingScreen (the "mind trick" centerpiece)
 *
 * Codebase memory:
 *   "Theatrical loading — perceived effort = perceived value. The
 *    centerpiece 'mind trick.'" — qaren-ux-redesign-design.md § 14
 *
 * v3 reshapes the loader against that vocabulary and ROTATES between
 * two variants so the same waiting moment doesn't read the same twice
 * back-to-back. Variant is picked on mount.
 *
 * VARIANT A — "Concentric"
 *   Hero: three emerald glow rings expanding outward from the Q logo,
 *   staggered ~700ms (matches motion.ts).
 *   Counter ticks 0 → 2,074 cohort peers (large enough to feel
 *   substantial; small enough to read as plausible).
 *   Below: a 5-stage StageChecklist that ticks pending→active→done.
 *   Below: rotating quiet factoid card.
 *
 * VARIANT B — "Streaming cards"
 *   Hero: two product-shape ghost cards side-by-side that fill in
 *   one field at a time — name → photo → price → rating → verdict
 *   pill — each beat marked by a thin emerald sweep on the field.
 *   Same StageChecklist + factoid card below.
 *
 * Both variants use motion tokens from colors_and_type.css for
 * easings/timings instead of hard-coded cubic-beziers (motion vocabulary
 * propagation per design system audit). Both variants finish at the
 * same beat so swapping is seamless.
 *
 * Copy avoids any "we trained on X shoppers" language — uses softer
 * framing like "2,074 cohort peers refining your match" so it reads as
 * value, not surveillance.
 */

const T_l = window.qarenTokens || {};
const C_l = T_l.colors || {};

const STAGES = [
  'Understanding your query',
  'Reading specs',
  'Cross-checking 25+ retailers',
  'Analyzing reviews',
  'Locking in your top match',
];

const ONBOARDING_STAGES = [
  'Calibrating to your region',
  'Mapping your priorities',
  'Matching your peer cohort',
  'Crafting your shopping advisor',
];

const COMPARISON_TIPS = [
  '73% of Capital shoppers your age prioritize Quality.',
  'Qaren cross-checks 25+ retailers — never just one.',
  'We work for you — never paid by sellers.',
  'Save any comparison to revisit later — even offline.',
];

const ONBOARDING_TIPS = [
  'Calibrated for the GCC — not the global average.',
  'Built around your priorities, not someone else\u2019s.',
  'Real people. Real buys. Real picks.',
];

// ─── StageChecklist — shared between both variants ──────────────────────
function StageChecklist({ stages }) {
  const [active, setActive] = React.useState(0);
  React.useEffect(() => {
    const t = setInterval(() => setActive((x) => (x + 1) % (stages.length + 2)), 900);
    return () => clearInterval(t);
  }, [stages.length]);

  return (
    <div style={{
      paddingBlock: 14, paddingInline: 16,
      borderRadius: 16,
      background: C_l.bg.secondary, border: `1px solid ${C_l.border.light}`,
      marginInline: 20,
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      {stages.map((label, i) => {
        const done = i < active;
        const isActive = i === active;
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{
              width: 18, height: 18, borderRadius: 9, flexShrink: 0,
              background: done ? C_l.accent : (isActive ? C_l.accentLight : C_l.bg.primary),
              border: done ? 'none' : `1.5px solid ${C_l.border.medium}`,
              display: 'grid', placeItems: 'center',
              color: done ? '#fff' : C_l.text.placeholder,
              transition: 'background 320ms var(--qaren-motion-screen-ease, ease)',
            }}>
              {done ? (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              ) : isActive ? (
                <span style={{
                  width: 6, height: 6, borderRadius: 3, background: C_l.accent,
                  animation: 'qarenDotPulse 0.7s ease-in-out infinite',
                }} />
              ) : null}
            </span>
            <span style={{
              flex: 1,
              font: `${isActive ? 600 : 500} 13px/1.4 var(--qaren-font-en, system-ui)`,
              color: (done || isActive) ? C_l.text.primary : C_l.text.secondary,
              transition: 'color 220ms ease',
            }}>
              {label}
            </span>
          </div>
        );
      })}
      <style>{`@keyframes qarenDotPulse { 0%,100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.6); opacity: 0.4; } }`}</style>
    </div>
  );
}

// ─── TipCard — shared ───────────────────────────────────────────────────
function TipCard({ tips }) {
  const [idx, setIdx] = React.useState(0);
  React.useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % tips.length), 3200);
    return () => clearInterval(t);
  }, [tips.length]);
  return (
    <div style={{
      paddingBlock: 12, paddingInline: 14, borderRadius: 14,
      background: 'transparent',
      marginInline: 20, marginTop: 10,
      display: 'flex', alignItems: 'center', gap: 10,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: 3, background: C_l.accent, flexShrink: 0 }} />
      <div key={idx} style={{
        flex: 1, font: '500 12px/1.5 var(--qaren-font-en, system-ui)',
        color: C_l.text.secondary,
        animation: 'qarenTipFade 3.2s ease infinite',
        textWrap: 'pretty',
      }}>
        {tips[idx]}
      </div>
      <style>{`@keyframes qarenTipFade { 0%,100% { opacity: 0; transform: translateY(4px); } 15%,85% { opacity: 1; transform: translateY(0); } }`}</style>
    </div>
  );
}

// ─── Variant A: Concentric rings + counter ──────────────────────────────
function ConcentricVariant({ target = 2074 }) {
  const [n, setN] = React.useState(0);
  React.useEffect(() => {
    const start = Date.now();
    const t = setInterval(() => {
      const elapsed = (Date.now() - start) / 2400;
      const eased = elapsed < 1 ? 1 - Math.pow(1 - elapsed, 3) : 1;
      setN(Math.round(target * eased));
      if (elapsed >= 1) clearInterval(t);
    }, 50);
    return () => clearInterval(t);
  }, [target]);

  return (
    <div style={{ position: 'relative', width: 220, height: 220, display: 'grid', placeItems: 'center' }}>
      {/* Three expanding rings staggered 700ms */}
      {[0, 0.7, 1.4].map((delay, i) => (
        <div key={i} aria-hidden="true" style={{
          position: 'absolute', width: 80, height: 80, borderRadius: 40,
          border: `2px solid ${C_l.accent}`,
          animation: `qarenRing 2.1s ease-out infinite`,
          animationDelay: `${delay}s`,
        }} />
      ))}
      <QarenLogo size={68} />
      {/* counter chip */}
      <div style={{
        position: 'absolute', insetBlockEnd: -36, insetInlineStart: '50%',
        transform: 'translateX(-50%)',
        paddingInline: 12, paddingBlock: 6, borderRadius: 999,
        background: C_l.bg.secondary, border: `1px solid ${C_l.border.light}`,
        display: 'flex', alignItems: 'center', gap: 6,
        whiteSpace: 'nowrap',
      }}>
        <span style={{
          font: '700 14px/1 var(--qaren-font-en, system-ui)',
          color: C_l.text.primary, fontVariantNumeric: 'tabular-nums',
        }}>
          {n.toLocaleString()}
        </span>
        <span style={{ font: '500 11px/1 var(--qaren-font-en, system-ui)', color: C_l.text.secondary }}>
          cohort peers refining your match
        </span>
      </div>

      <style>{`@keyframes qarenRing { 0% { transform: scale(0.8); opacity: 0.9; } 100% { transform: scale(2.5); opacity: 0; } }`}</style>
    </div>
  );
}

// ─── Variant B: Streaming product cards (the "fields populate" mind trick) ─
function StreamingCardsVariant() {
  // Tick through five fields filling on both cards. Field-by-field reveal.
  const [tick, setTick] = React.useState(0);
  React.useEffect(() => {
    const t = setInterval(() => setTick((x) => (x + 1) % 6), 700);
    return () => clearInterval(t);
  }, []);
  return (
    <div style={{ display: 'flex', gap: 10, paddingInline: 20, width: '100%', maxWidth: 340, marginInline: 'auto' }}>
      <StreamingCard tick={tick} winner={false} tone="#E8E9ED" name="iPhone 15" price="329 BHD" />
      <StreamingCard tick={tick} winner={true}  tone="#1B1C1F" name="Galaxy S24" price="299 BHD" />
    </div>
  );
}
function StreamingCard({ tick, winner, tone, name, price }) {
  const fields = [
    { type: 'photo', show: tick >= 1 },
    { type: 'name',  show: tick >= 2, value: name },
    { type: 'price', show: tick >= 3, value: price },
    { type: 'stars', show: tick >= 4 },
    { type: 'badge', show: tick >= 5 },
  ];
  return (
    <div style={{
      flex: 1, padding: 10, borderRadius: 14,
      background: C_l.bg.secondary, border: `${winner && tick >= 5 ? 2 : 1}px solid ${winner && tick >= 5 ? C_l.accent : C_l.border.light}`,
      display: 'flex', flexDirection: 'column', gap: 8,
      transition: 'border-color 320ms var(--qaren-motion-screen-ease, ease)',
      position: 'relative',
    }}>
      <div style={{
        aspectRatio: '1 / 1', borderRadius: 10,
        background: fields[0].show ? tone : '#EFEFF3',
        display: 'grid', placeItems: 'center',
        color: fields[0].show ? 'rgba(0,0,0,0.18)' : 'transparent',
        position: 'relative', overflow: 'hidden',
      }}>
        {fields[0].show && (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="5" y="2" width="14" height="20" rx="2.5"/>
          </svg>
        )}
        {!fields[0].show && <ShimmerOverlay />}
      </div>

      <SkeletonOrText show={fields[1].show} value={fields[1].value} font="600 12px" height={14} />
      <SkeletonOrText show={fields[2].show} value={fields[2].value} font="700 14px" height={16} />

      {fields[3].show ? (
        <div style={{ display: 'flex', gap: 1 }}>
          {[1,2,3,4,5].map(s => (
            <svg key={s} width="11" height="11" viewBox="0 0 24 24" fill={s <= 4 ? C_l.warning : C_l.border.medium}><path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>
          ))}
        </div>
      ) : (
        <SkeletonLine height={11} width="60%" />
      )}

      {fields[4].show && winner && (
        <span style={{
          position: 'absolute', insetBlockStart: 6, insetInlineEnd: 6,
          paddingInline: 6, height: 18,
          display: 'inline-flex', alignItems: 'center',
          borderRadius: 999,
          background: C_l.accent, color: '#fff',
          font: '700 9px/1 var(--qaren-font-en, system-ui)',
          letterSpacing: '0.6px', textTransform: 'uppercase',
        }}>Top match</span>
      )}
    </div>
  );
}
function SkeletonLine({ height, width }) {
  return (
    <div style={{
      width, height, borderRadius: 4, background: '#EFEFF3',
      position: 'relative', overflow: 'hidden',
    }}>
      <ShimmerOverlay />
    </div>
  );
}
function SkeletonOrText({ show, value, font, height }) {
  return show ? (
    <div style={{ font: `${font} var(--qaren-font-en, system-ui)`, color: C_l.text.primary, minHeight: height }}>
      {value}
    </div>
  ) : (
    <SkeletonLine height={height} width="80%" />
  );
}
function ShimmerOverlay() {
  return (
    <>
      <div aria-hidden="true" style={{
        position: 'absolute', inset: 0,
        background: `linear-gradient(110deg, transparent 30%, ${C_l.accentLight} 50%, transparent 70%)`,
        animation: 'qarenShimmer 1.4s linear infinite',
      }} />
      <style>{`@keyframes qarenShimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }`}</style>
    </>
  );
}

// ─── QarenLoadingScreen ────────────────────────────────────────────────
function QarenLoadingScreen({ mode = 'comparison', variant: forcedVariant }) {
  // Pick variant once per mount — rotates so users don't see the same one twice.
  const variant = React.useMemo(
    () => forcedVariant || (Math.random() < 0.5 ? 'concentric' : 'streaming'),
    [forcedVariant]
  );
  const isOnb = mode === 'onboarding';
  const stages = isOnb ? ONBOARDING_STAGES : STAGES;
  const tips   = isOnb ? ONBOARDING_TIPS   : COMPARISON_TIPS;
  // Onboarding always uses concentric (the dramatic moment); comparison rotates.
  const useVariant = isOnb ? 'concentric' : variant;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: C_l.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_l.text.primary,
    }}>
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        paddingInline: 20, paddingTop: 12, paddingBottom: 8,
      }}>
        <QarenLogo size={22} />
        <span style={{
          font: '500 11px/1.4 var(--qaren-font-en, system-ui)',
          letterSpacing: '0.6px', textTransform: 'uppercase',
          color: C_l.text.secondary,
        }}>
          {isOnb ? 'Building your advisor' : 'Comparing'}
        </span>
      </header>

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 40, paddingTop: 8, paddingBottom: 8 }}>
        <div style={{ display: 'grid', placeItems: 'center' }}>
          {useVariant === 'concentric' ? <ConcentricVariant /> : <StreamingCardsVariant />}
        </div>
        <StageChecklist stages={stages} />
      </main>

      <TipCard tips={tips} />
      <div style={{ height: 24 }} />
    </div>
  );
}

window.QarenLoadingScreen = QarenLoadingScreen;
