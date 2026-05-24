/**
 * Qaren — Onboarding extra steps
 *
 * Four screens kept compact in one file because they share primitives:
 *
 *   - OnboardingRegionScreen        (s4 — "Where do you shop?")
 *   - OnboardingPrivacyScreen       (s5 — "Your data, your call")
 *   - OnboardingBuildScreen         (s13 — animated build-out moment)
 *   - OnboardingNotificationsScreen (s17 — push opt-in)
 *
 * Copy lifted/lightly adapted from en.json onboarding.s4/s5/s13/s17.*.
 * All four share the same chrome: back-arrow + progress bar header, big
 * display headline, content, sticky Continue CTA. Same brand rules:
 * black primary CTA, emerald only as signal, no scary copy.
 */

const T_ox = window.qarenTokens || {};
const C_ox = T_ox.colors || {};

// ─── Shared chrome ──────────────────────────────────────────────────────
function OnbHeader({ progressPct = 0, onBack }) {
  return (
    <header style={{ display: 'flex', alignItems: 'center', gap: 12, paddingInline: 20, paddingTop: 8, paddingBottom: 16 }}>
      <button aria-label="Back" onClick={onBack} style={{
        width: 36, height: 36, borderRadius: 18,
        background: C_ox.bg.secondary, border: 'none',
        display: 'grid', placeItems: 'center', cursor: 'pointer', flexShrink: 0,
      }}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_ox.text.primary} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <div style={{ flex: 1, height: 4, borderRadius: 2, background: C_ox.border.light, overflow: 'hidden' }}>
        <div style={{ width: `${progressPct}%`, height: '100%', background: C_ox.cta.primary }} />
      </div>
    </header>
  );
}

function OnbCTA({ label = 'Continue', disabled, onPress }) {
  return (
    <div style={{
      paddingInline: 20, paddingTop: 12, paddingBottom: 16,
      borderTop: `1px solid ${C_ox.border.light}`,
      background: C_ox.bg.primary,
    }}>
      <button
        disabled={disabled}
        onClick={onPress}
        style={{
          width: '100%', height: 52, borderRadius: 999, border: 'none',
          background: C_ox.cta.primary, color: C_ox.cta.onPrimary,
          font: '600 16px/1.5 var(--qaren-font-en, system-ui)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
        }}
      >
        {label}
      </button>
    </div>
  );
}

function OnbHeadline({ accentWord, before, after, sub }) {
  return (
    <div style={{ paddingInline: 20, marginBottom: 22 }}>
      <h1 style={{
        margin: 0,
        font: '700 30px/1.15 var(--qaren-font-en, system-ui)',
        letterSpacing: '-0.36px', textWrap: 'pretty', maxWidth: 320,
      }}>
        {before}<span style={{ color: C_ox.accent }}>{accentWord}</span>{after}
      </h1>
      {sub && (
        <p style={{
          margin: '12px 0 0',
          font: '400 14px/1.5 var(--qaren-font-en, system-ui)', color: C_ox.text.secondary,
          maxWidth: 320,
        }}>{sub}</p>
      )}
    </div>
  );
}

// Icon-in-circle option row (matches Onboarding priorities).
function IconRow({ icon, label, sub, selected, onPress }) {
  return (
    <button
      onClick={onPress}
      aria-pressed={selected}
      style={{
        display: 'flex', alignItems: 'center', gap: 14,
        paddingBlock: 14, paddingInline: 12,
        minHeight: 60, width: '100%', textAlign: 'start',
        borderRadius: 16,
        border: `1px solid ${selected ? C_ox.cta.primary : C_ox.border.light}`,
        background: selected ? C_ox.cta.primary : C_ox.bg.secondary,
        color: selected ? C_ox.cta.onPrimary : C_ox.text.primary,
        cursor: 'pointer',
        transition: 'background 180ms cubic-bezier(0.32,0.72,0,1)',
      }}
    >
      <span style={{
        width: 36, height: 36, borderRadius: 18,
        background: selected ? 'rgba(255,255,255,0.12)' : C_ox.bg.primary,
        display: 'grid', placeItems: 'center', flexShrink: 0,
        color: selected ? C_ox.cta.onPrimary : C_ox.text.primary,
      }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ font: '600 15px/1.3 var(--qaren-font-en, system-ui)' }}>{label}</div>
        {sub && (
          <div style={{
            font: '400 12px/1.4 var(--qaren-font-en, system-ui)',
            color: selected ? 'rgba(255,255,255,0.7)' : C_ox.text.secondary,
            marginTop: 2,
          }}>{sub}</div>
        )}
      </div>
    </button>
  );
}

const __skO = (d) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{d}</svg>
);

// ─── s4 · Region ────────────────────────────────────────────────────────
function QarenOnboardingRegionScreen() {
  const [pick, setPick] = React.useState('bahrain');
  const opts = [
    { v: 'bahrain', label: 'Bahrain',         sub: 'Capital, Muharraq, Northern, Southern', icon: <span style={{ font: '700 16px/1 var(--qaren-font-en, system-ui)' }}>🇧🇭</span> },
    { v: 'uae',     label: 'UAE',             sub: 'Dubai, Abu Dhabi, Sharjah',             icon: <span style={{ font: '700 16px/1 var(--qaren-font-en, system-ui)' }}>🇦🇪</span> },
    { v: 'ksa',     label: 'Saudi Arabia',    sub: 'Riyadh, Jeddah, Dammam',                icon: <span style={{ font: '700 16px/1 var(--qaren-font-en, system-ui)' }}>🇸🇦</span> },
    { v: 'kuwait',  label: 'Kuwait',          sub: 'Kuwait City, Hawalli',                  icon: <span style={{ font: '700 16px/1 var(--qaren-font-en, system-ui)' }}>🇰🇼</span> },
    { v: 'qatar',   label: 'Qatar',           sub: 'Doha',                                  icon: <span style={{ font: '700 16px/1 var(--qaren-font-en, system-ui)' }}>🇶🇦</span> },
    { v: 'oman',    label: 'Oman',            sub: 'Muscat',                                icon: <span style={{ font: '700 16px/1 var(--qaren-font-en, system-ui)' }}>🇴🇲</span> },
  ];
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%', paddingTop: 50,
      background: C_ox.bg.primary, fontFamily: 'var(--qaren-font-en, system-ui)', color: C_ox.text.primary,
    }}>
      <OnbHeader progressPct={28} />
      <OnbHeadline before="Where do you " accentWord="shop" after="?" sub="Currency, retailers, and peer cohort all calibrate to your region." />
      <div style={{ flex: 1, overflowY: 'auto', paddingInline: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {opts.map((o) => (
          <IconRow key={o.v} icon={o.icon} label={o.label} sub={o.sub} selected={pick === o.v} onPress={() => setPick(o.v)} />
        ))}
      </div>
      <OnbCTA />
    </div>
  );
}

// ─── s5 · Privacy ───────────────────────────────────────────────────────
function PrivacyRow({ icon, head, body }) {
  return (
    <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
      <span style={{
        width: 36, height: 36, borderRadius: 18, flexShrink: 0,
        background: C_ox.accentLight, color: C_ox.accentDark,
        display: 'grid', placeItems: 'center',
      }}>
        {icon}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ font: '600 15px/1.3 var(--qaren-font-en, system-ui)', color: C_ox.text.primary }}>{head}</div>
        <div style={{ font: '400 13px/1.5 var(--qaren-font-en, system-ui)', color: C_ox.text.secondary, marginTop: 4, textWrap: 'pretty' }}>{body}</div>
      </div>
    </div>
  );
}
function QarenOnboardingPrivacyScreen() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%', paddingTop: 50,
      background: C_ox.bg.primary, fontFamily: 'var(--qaren-font-en, system-ui)', color: C_ox.text.primary,
    }}>
      <OnbHeader progressPct={36} />
      <OnbHeadline before="Your data, your " accentWord="call" after="." sub="A handful of inputs sharpen the match. Three are off-limits, forever." />
      <main style={{ flex: 1, overflowY: 'auto', paddingInline: 20, display: 'flex', flexDirection: 'column', gap: 20 }}>
        <PrivacyRow
          icon={__skO(<polyline points="20 6 9 17 4 12"/>)}
          head="What we use"
          body="Age range, governorate, priorities, budget tier, brand stance — to find peers like you."
        />
        <PrivacyRow
          icon={__skO(<><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></>)}
          head="What's anonymized"
          body="Your queries help Qaren get smarter. We strip your name, email, and identity first."
        />
        <PrivacyRow
          icon={__skO(<><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></>)}
          head="What we never share"
          body="Your name. Your email. Your budget. Not now, not ever."
        />
      </main>
      <OnbCTA label="I'm in" />
    </div>
  );
}

// ─── s13 · Build (animated) ─────────────────────────────────────────────
function QarenOnboardingBuildScreen() {
  // Reuses the LoadingScreen recipe but with build-specific copy and a
  // fixed final beat. In production this auto-advances to s14 (loading)
  // → s15 (ready).
  const items = [
    { label: 'Locking your region', delay: 0 },
    { label: 'Mapping your priorities', delay: 200 },
    { label: 'Matching to 47 peers in Capital', delay: 600 },
    { label: 'Calibrating your advisor', delay: 1100 },
  ];
  const [tick, setTick] = React.useState(0);
  React.useEffect(() => {
    if (tick >= items.length + 1) return;
    const t = setTimeout(() => setTick(x => x + 1), 850);
    return () => clearTimeout(t);
  }, [tick, items.length]);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%', paddingTop: 50,
      background: C_ox.bg.primary, fontFamily: 'var(--qaren-font-en, system-ui)', color: C_ox.text.primary,
    }}>
      <OnbHeader progressPct={88} />
      <OnbHeadline before="Building your " accentWord="advisor" after="…" sub="One profile, four steps. Stay with us." />
      <main style={{ flex: 1, overflowY: 'auto', paddingInline: 20 }}>
        <div style={{
          padding: 18, borderRadius: 20,
          background: C_ox.bg.secondary, border: `1px solid ${C_ox.border.light}`,
          display: 'flex', flexDirection: 'column', gap: 14,
        }}>
          {items.map((it, i) => {
            const done = tick > i;
            const active = tick === i;
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{
                  width: 22, height: 22, borderRadius: 11, flexShrink: 0,
                  background: done ? C_ox.accent : (active ? C_ox.accentLight : C_ox.bg.primary),
                  border: done ? 'none' : `1.5px solid ${C_ox.border.medium}`,
                  display: 'grid', placeItems: 'center',
                  color: done ? '#fff' : C_ox.text.placeholder,
                  transition: 'background 240ms ease',
                }}>
                  {done ? (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  ) : active ? (
                    <span style={{
                      width: 8, height: 8, borderRadius: 4, background: C_ox.accent,
                      animation: 'qarenBuildPulse 0.8s ease-in-out infinite',
                    }} />
                  ) : null}
                </span>
                <span style={{
                  font: `${active ? 600 : 500} 14px/1.4 var(--qaren-font-en, system-ui)`,
                  color: (done || active) ? C_ox.text.primary : C_ox.text.secondary,
                }}>
                  {it.label}
                </span>
              </div>
            );
          })}
          <style>{`@keyframes qarenBuildPulse { 0%,100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.5); opacity: 0.4; } }`}</style>
        </div>

        <p style={{
          marginTop: 20, font: '400 13px/1.5 var(--qaren-font-en, system-ui)', color: C_ox.text.secondary,
          textAlign: 'center',
        }}>
          Did you know — 73% of Capital shoppers your age prioritize Quality first.
        </p>
      </main>
      <OnbCTA disabled={tick < items.length + 1} label="Almost there…" />
    </div>
  );
}

// ─── s17 · Notifications opt-in ─────────────────────────────────────────
function QarenOnboardingNotificationsScreen() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%', paddingTop: 50,
      background: C_ox.bg.primary, fontFamily: 'var(--qaren-font-en, system-ui)', color: C_ox.text.primary,
    }}>
      <OnbHeader progressPct={96} />

      {/* Mock iOS push prompt — the user's visual anchor */}
      <div style={{ paddingInline: 20, marginBottom: 22 }}>
        <div style={{
          padding: 14, borderRadius: 20,
          background: C_ox.bg.secondary, border: `1px solid ${C_ox.border.light}`,
          boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
          display: 'flex', alignItems: 'flex-start', gap: 12,
          marginInline: 10,
        }}>
          <QarenLogo size={32} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ font: '600 12px/1.3 var(--qaren-font-en, system-ui)', color: C_ox.text.primary }}>Qaren</span>
              <span style={{ font: '400 11px/1 var(--qaren-font-en, system-ui)', color: C_ox.text.secondary }}>now</span>
            </div>
            <div style={{
              font: '500 13px/1.45 var(--qaren-font-en, system-ui)', color: C_ox.text.primary, marginTop: 4,
              textWrap: 'pretty',
            }}>
              ✦ Strong match this week — 4 peers in Capital just compared a phone you scanned.
            </div>
          </div>
        </div>
      </div>

      <OnbHeadline
        before="One helpful nudge "
        accentWord="per week"
        after="."
        sub="No price-drop spam. No streaks. Just the moments worth knowing about."
      />

      <main style={{ flex: 1, overflowY: 'auto', paddingInline: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <Tag head="Decision insights" body="When a peer match strengthens your last verdict." />
        <Tag head="Cohort echoes" body="When 5+ peers your age just compared the same pair." />
        <Tag head="Smart shortcuts" body="A heads-up when an item you scanned drops sharply." />
      </main>

      <div style={{
        paddingInline: 20, paddingTop: 12, paddingBottom: 16,
        borderTop: `1px solid ${C_ox.border.light}`, background: C_ox.bg.primary,
      }}>
        <button style={{
          width: '100%', height: 52, borderRadius: 999, border: 'none',
          background: C_ox.cta.primary, color: C_ox.cta.onPrimary,
          font: '600 16px/1.5 var(--qaren-font-en, system-ui)', cursor: 'pointer',
        }}>
          Allow notifications
        </button>
        <button style={{
          width: '100%', height: 40, marginTop: 4,
          background: 'transparent', border: 'none',
          color: C_ox.text.secondary,
          font: '500 13px/1.5 var(--qaren-font-en, system-ui)', cursor: 'pointer',
        }}>
          Maybe later
        </button>
      </div>
    </div>
  );
}

function Tag({ head, body }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 12,
      paddingBlock: 12, paddingInline: 14,
      borderRadius: 14, background: C_ox.bg.secondary, border: `1px solid ${C_ox.border.light}`,
    }}>
      <span style={{
        width: 8, height: 8, borderRadius: 4, background: C_ox.accent, marginTop: 6, flexShrink: 0,
      }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ font: '600 13px/1.3 var(--qaren-font-en, system-ui)', color: C_ox.text.primary }}>{head}</div>
        <div style={{ font: '400 12px/1.4 var(--qaren-font-en, system-ui)', color: C_ox.text.secondary, marginTop: 2 }}>{body}</div>
      </div>
    </div>
  );
}

window.QarenOnboardingRegionScreen        = QarenOnboardingRegionScreen;
window.QarenOnboardingPrivacyScreen       = QarenOnboardingPrivacyScreen;
window.QarenOnboardingBuildScreen         = QarenOnboardingBuildScreen;
window.QarenOnboardingNotificationsScreen = QarenOnboardingNotificationsScreen;
