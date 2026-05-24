/**
 * Qaren — ResultsScreen (reference, web)
 *
 * Source of truth: AI/smartcompare/SmartCompareApp/src/screens/ResultsScreen.tsx
 *
 * The payoff surface — after a comparison runs, this is what the user sees.
 * Anatomy follows Bundle B/C/D § 4 "Single Scroll":
 *   1. Header bar (back + share + emerald top-match eyebrow)
 *   2. Hero — two product cards side by side, winner outlined emerald
 *   3. Factual verdict / "Why this fits you"
 *   4. Dimension bars (camera, battery, price)
 *   5. Confidence pills
 *   6. Feedback prompt ("Was this helpful?")
 *
 * Copy passes the .copy-policy.json fence:
 *   - "Top match" (not "Winner" / "Best Pick")
 *   - "Why this fits you" (not "Why we picked this")
 *   - "Tuned to your priorities" (not "We recommend")
 */

const T_res = window.qarenTokens || {};
const C_res = T_res.colors || {};

function TopMatchBadge() {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      paddingInline: 12, height: 26, borderRadius: 999,
      background: C_res.accentLight, color: C_res.accentDark,
      font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
      letterSpacing: '1.1px', textTransform: 'uppercase',
    }}>
      <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>
      Top match
    </div>
  );
}

function ProductCard({ name, sub, price, isWinner, imageColor }) {
  return (
    <div style={{
      flex: 1, minWidth: 0,
      borderRadius: 20,
      background: isWinner ? C_res.accentLight : C_res.bg.secondary,
      border: `${isWinner ? 2 : 1}px solid ${isWinner ? C_res.accent : C_res.border.light}`,
      padding: 14,
      display: 'flex', flexDirection: 'column', gap: 10,
      position: 'relative',
    }}>
      {/* product image placeholder */}
      <div style={{
        aspectRatio: '1 / 1', borderRadius: 14,
        background: imageColor || '#EEEFF4',
        display: 'grid', placeItems: 'center',
        color: C_res.text.placeholder,
      }}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="5" y="2" width="14" height="20" rx="2.5"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>
      </div>
      <div style={{ font: '600 15px/1.3 var(--qaren-font-en, system-ui)', color: C_res.text.primary }}>{name}</div>
      <div style={{ font: '400 12px/1.4 var(--qaren-font-en, system-ui)', color: C_res.text.secondary }}>{sub}</div>
      <div style={{ font: '700 18px/1 var(--qaren-font-en, system-ui)', color: C_res.text.primary, marginTop: 'auto', fontVariantNumeric: 'tabular-nums' }}>
        {price}
      </div>
    </div>
  );
}

function DimensionBar({ label, leftPct, rightPct, leftLabel, rightLabel }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', font: '500 13px/1.4 var(--qaren-font-en, system-ui)' }}>
        <span style={{ color: C_res.text.primary }}>{label}</span>
        <span style={{ color: C_res.text.secondary, fontVariantNumeric: 'tabular-nums' }}>{leftLabel} · {rightLabel}</span>
      </div>
      <div style={{ display: 'flex', height: 8, borderRadius: 999, overflow: 'hidden', background: C_res.border.light }}>
        <div style={{ width: `${leftPct}%`, background: C_res.text.secondary }} />
        <div style={{ width: 2, background: C_res.bg.primary }} />
        <div style={{ width: `${rightPct}%`, background: C_res.accent }} />
      </div>
    </div>
  );
}

function ConfidencePill({ label, level }) {
  // level: 'high' | 'medium' | 'low'
  const ring = level === 'high' ? C_res.accent : level === 'medium' ? C_res.warning : C_res.border.medium;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      paddingInline: 10, paddingBlock: 6,
      borderRadius: 999,
      background: C_res.bg.secondary,
      border: `1px solid ${C_res.border.light}`,
      font: '500 12px/1.3 var(--qaren-font-en, system-ui)',
      color: C_res.text.primary,
    }}>
      <span style={{ width: 8, height: 8, borderRadius: 4, background: ring }} />
      {label}
    </span>
  );
}

// ─── Collapsible details (Reviews · Pros & Cons · Specs) ───────────────
// Keeps the verdict-first surface scan-able while making depth one tap away.
function DetailsAccordion() {
  const [open, setOpen] = React.useState(null); // 'reviews' | 'proscons' | 'specs' | null
  const toggle = (k) => setOpen((curr) => (curr === k ? null : k));
  const sections = [
    {
      key: 'reviews',
      label: 'Reviews',
      sub: '4.8★ avg · 1,240 reviews across both',
      icon: (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>),
      body: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <ReviewLine source="Amazon" stars={5} text="Battery actually lasts a full day, even with heavy use." />
          <ReviewLine source="Noon"   stars={4} text="Camera in low light is the best I've used at this price." />
          <ReviewLine source="X"      stars={5} text="Switched from iPhone after 4 years. No regrets." />
        </div>
      ),
    },
    {
      key: 'proscons',
      label: 'Pros & Cons',
      sub: 'Each product, both sides',
      icon: (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>),
      body: (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <ProsConsCol name="Galaxy S24" pros={['Stronger camera', 'Longer battery', '30 BHD less']} cons={['Slower app updates']} winner />
          <ProsConsCol name="iPhone 15" pros={['Faster CPU', 'Better ecosystem']} cons={['Lower camera score', 'Shorter battery']} />
        </div>
      ),
    },
    {
      key: 'specs',
      label: 'Specs',
      sub: '8 dimensions',
      icon: (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>),
      body: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <SpecRow label="Display"     left="6.1″ OLED"  right="6.2″ AMOLED" />
          <SpecRow label="Camera"      left="48 MP main" right="50 MP main" winnerRight />
          <SpecRow label="Battery"     left="3,349 mAh"  right="4,000 mAh"  winnerRight />
          <SpecRow label="Storage"     left="128 GB"     right="128 GB" />
          <SpecRow label="RAM"         left="6 GB"       right="8 GB"       winnerRight />
          <SpecRow label="Weight"      left="171 g"      right="167 g"      winnerRight />
          <SpecRow label="Charging"    left="20 W"       right="45 W"       winnerRight />
          <SpecRow label="Water rating" left="IP68"     right="IP68" />
        </div>
      ),
    },
  ];

  return (
    <section style={{ marginBottom: 8 }}>
      <h3 style={{ margin: '0 0 10px', font: '600 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '1.1px', textTransform: 'uppercase', color: C_res.text.secondary }}>
        Dig deeper
      </h3>
      <div style={{
        borderRadius: 16,
        background: C_res.bg.secondary, border: `1px solid ${C_res.border.light}`,
        overflow: 'hidden',
      }}>
        {sections.map((s, i) => {
          const isOpen = open === s.key;
          return (
            <div key={s.key} style={{ borderBlockEnd: i < sections.length - 1 ? `1px solid ${C_res.border.light}` : 'none' }}>
              <button
                onClick={() => toggle(s.key)}
                aria-expanded={isOpen}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  width: '100%', minHeight: 60,
                  paddingBlock: 14, paddingInline: 16,
                  background: 'transparent', border: 'none', cursor: 'pointer',
                  textAlign: 'start',
                  color: C_res.text.primary,
                }}
              >
                <span style={{
                  width: 32, height: 32, borderRadius: 16,
                  background: C_res.bg.primary, color: isOpen ? C_res.accentDark : C_res.text.secondary,
                  display: 'grid', placeItems: 'center', flexShrink: 0,
                  transition: 'color 220ms ease',
                }}>
                  {s.icon}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ font: '600 14px/1.3 var(--qaren-font-en, system-ui)' }}>{s.label}</div>
                  <div style={{ font: '400 12px/1.4 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, marginTop: 2 }}>{s.sub}</div>
                </div>
                <svg
                  width="16" height="16" viewBox="0 0 24 24"
                  fill="none" stroke={C_res.text.placeholder} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                  style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 220ms ease' }}
                >
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </button>
              {isOpen && (
                <div style={{ paddingInline: 16, paddingBottom: 16, background: C_res.bg.primary, borderBlockStart: `1px solid ${C_res.border.light}` }}>
                  <div style={{ paddingTop: 14 }}>{s.body}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ReviewLine({ source, stars, text }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{
          paddingInline: 6, height: 18,
          display: 'inline-flex', alignItems: 'center', borderRadius: 999,
          background: C_res.bg.secondary, font: '600 9px/1 var(--qaren-font-en, system-ui)',
          color: C_res.text.secondary, letterSpacing: '0.5px', textTransform: 'uppercase',
        }}>{source}</span>
        <span style={{ display: 'inline-flex', gap: 1 }}>
          {[1,2,3,4,5].map(s => (
            <svg key={s} width="10" height="10" viewBox="0 0 24 24" fill={s <= stars ? C_res.warning : C_res.border.medium}>
              <path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
            </svg>
          ))}
        </span>
      </div>
      <div style={{ font: '500 12px/1.5 var(--qaren-font-en, system-ui)', color: C_res.text.primary, textWrap: 'pretty' }}>
        "{text}"
      </div>
    </div>
  );
}

function ProsConsCol({ name, pros, cons, winner }) {
  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8,
        font: `${winner ? 700 : 600} 12px/1.3 var(--qaren-font-en, system-ui)`,
        color: winner ? C_res.accentDark : C_res.text.primary,
      }}>
        {winner && <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>}
        {name}
      </div>
      {pros.map((p, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, font: '500 11px/1.5 var(--qaren-font-en, system-ui)', color: C_res.text.primary, marginBottom: 3 }}>
          <span style={{ color: C_res.accentDark, marginTop: 1 }}>+</span>
          <span>{p}</span>
        </div>
      ))}
      {cons.map((c, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, font: '500 11px/1.5 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, marginBottom: 3 }}>
          <span style={{ color: C_res.text.placeholder, marginTop: 1 }}>−</span>
          <span>{c}</span>
        </div>
      ))}
    </div>
  );
}

function SpecRow({ label, left, right, winnerRight, winnerLeft }) {
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '1fr 90px 1fr',
      alignItems: 'center', gap: 12,
      paddingBlock: 8,
      borderBlockEnd: `1px solid ${C_res.border.light}`,
    }}>
      <div style={{ textAlign: 'end', font: `${winnerLeft ? 700 : 500} 12px/1.3 var(--qaren-font-en, system-ui)`, color: winnerLeft ? C_res.accentDark : C_res.text.primary }}>
        {left}
      </div>
      <div style={{ textAlign: 'center', font: '500 11px/1.3 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, letterSpacing: '0.4px', textTransform: 'uppercase' }}>
        {label}
      </div>
      <div style={{ font: `${winnerRight ? 700 : 500} 12px/1.3 var(--qaren-font-en, system-ui)`, color: winnerRight ? C_res.accentDark : C_res.text.primary }}>
        {right}
      </div>
    </div>
  );
}

function QarenResultsScreen() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: C_res.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_res.text.primary,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingInline: 20, paddingBlock: 8 }}>
        <button aria-label="Back" style={{
          width: 36, height: 36, borderRadius: 18, background: C_res.bg.secondary, border: 'none',
          display: 'grid', placeItems: 'center', cursor: 'pointer',
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_res.text.primary} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
        <TopMatchBadge />
        <button aria-label="Share" style={{
          width: 36, height: 36, borderRadius: 18, background: C_res.bg.secondary, border: 'none',
          display: 'grid', placeItems: 'center', cursor: 'pointer',
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_res.text.primary} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
        </button>
      </header>

      {/* Scrolling body */}
      <main style={{ flex: 1, overflowY: 'auto', paddingInline: 20, paddingTop: 12, paddingBottom: 24 }}>
        {/* Hero — product pair */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 20, position: 'relative' }}>
          <ProductCard name="iPhone 15" sub="128GB · Black" price="329 BHD" isWinner={false} imageColor="#E8E9ED" />
          {/* vs pill on the divider */}
          <div style={{
            position: 'absolute', insetBlockStart: '50%', insetInlineStart: '50%',
            transform: 'translate(-50%, -50%)', zIndex: 1,
          }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              height: 24, paddingInline: 10, borderRadius: 999,
              background: C_res.accentLight, color: C_res.accentDark,
              font: '600 11px/1 var(--qaren-font-en, system-ui)',
              letterSpacing: '1.1px', textTransform: 'uppercase',
              border: `2px solid ${C_res.bg.primary}`,
            }}>vs</span>
          </div>
          <ProductCard name="Galaxy S24" sub="128GB · Onyx" price="299 BHD" isWinner={true} imageColor="#1B1C1F" />
        </div>

        {/* Why this fits you */}
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ margin: 0, font: '600 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '1.1px', textTransform: 'uppercase', color: C_res.text.secondary }}>
            Why this fits you
          </h3>
          <p style={{ margin: '8px 0 0', font: '600 18px/1.45 var(--qaren-font-en, system-ui)', color: C_res.text.primary, textWrap: 'pretty' }}>
            Tuned to your priorities — camera quality and battery beat Apple here, and it lands 30 BHD under your usual range.
          </p>
          <p style={{ margin: '8px 0 0', font: '400 13px/1.5 var(--qaren-font-en, system-ui)', color: C_res.text.secondary }}>
            Weighted ↑ Camera ↑ Battery — based on your priorities.
          </p>
        </section>

        {/* Dimension bars */}
        <section style={{ marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <DimensionBar label="Camera"  leftPct={38} rightPct={62} leftLabel="iPhone" rightLabel="Galaxy" />
          <DimensionBar label="Battery" leftPct={30} rightPct={70} leftLabel="iPhone" rightLabel="Galaxy" />
          <DimensionBar label="Price"   leftPct={56} rightPct={44} leftLabel="iPhone" rightLabel="Galaxy" />
        </section>

        {/* Confidence pills */}
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ margin: '0 0 10px', font: '600 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '1.1px', textTransform: 'uppercase', color: C_res.text.secondary }}>
            What we know
          </h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <ConfidencePill label="Price · High" level="high" />
            <ConfidencePill label="Reviews · Medium" level="medium" />
            <ConfidencePill label="Specs · High" level="high" />
          </div>
        </section>

        {/* Cohort line — softened framing per user feedback. */}
        <p style={{
          margin: '12px 0 20px',
          font: '500 12px/1.5 var(--qaren-font-en, system-ui)',
          color: C_res.text.secondary,
          padding: '10px 12px',
          borderRadius: 12,
          background: C_res.bg.secondary,
        }}>
          2,000+ shoppers in Capital leaned the same way.
        </p>

        {/* Collapsible details — keeps the verdict scan-able while
            making reviews / pros & cons / specs one tap away. */}
        <DetailsAccordion />

        {/* Feedback prompt */}
        <section style={{
          padding: 16, borderRadius: 16,
          border: `1px solid ${C_res.border.light}`,
          background: C_res.bg.secondary,
        }}>
          <div style={{ font: '600 15px/1.4 var(--qaren-font-en, system-ui)', marginBottom: 10 }}>
            Was this helpful?
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {['Accurate', 'Detailed', 'Fast'].map((l) => (
              <button key={l} style={{
                paddingInline: 14, height: 36, borderRadius: 999,
                background: C_res.bg.primary, border: `1px solid ${C_res.border.light}`,
                color: C_res.text.primary, font: '500 13px/1 var(--qaren-font-en, system-ui)',
                cursor: 'pointer',
              }}>
                {l}
              </button>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

window.QarenResultsScreen = QarenResultsScreen;
