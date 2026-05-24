/**
 * Qaren — SignInScreen + SaveAdvisorScreen
 *
 * Two related auth surfaces, kept in one file because they share primitives:
 *
 *   - SignInScreen — existing user path. Email/password + biometric option
 *     + social sign-in row + "Forgot password" link.
 *
 *   - SaveAdvisorScreen — Onboarding s16, the forced sign-up moment after
 *     building the advisor. NO skip link (codebase CLAUDE.md: "Step 16
 *     'Save your advisor' has NO skip link — forced sign-in"). The
 *     framing is "save your work" not "create an account", which keeps
 *     the friction calm.
 */

const T_au = window.qarenTokens || {};
const C_au = T_au.colors || {};

function AuthField({ label, type = 'text', value, onChange, placeholder, autoFocus }) {
  const [focused, setFocused] = React.useState(false);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label style={{ font: '500 12px/1.4 var(--qaren-font-en, system-ui)', color: C_au.text.secondary }}>
        {label}
      </label>
      <div style={{
        height: 48, paddingInline: 14,
        borderRadius: 12,
        background: C_au.bg.primary,
        border: `${focused ? 2 : 1}px solid ${focused ? C_au.text.primary : C_au.border.light}`,
        display: 'flex', alignItems: 'center',
      }}>
        <input
          type={type}
          value={value}
          autoFocus={autoFocus}
          onChange={onChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          style={{
            width: '100%', border: 'none', outline: 'none', background: 'transparent',
            font: '400 16px/1.5 var(--qaren-font-en, system-ui)', color: C_au.text.primary,
          }}
        />
      </div>
    </div>
  );
}

function SocialRow() {
  const opts = [
    { name: 'Apple',  glyph: <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M17.05 12.04c-.03-3.04 2.47-4.5 2.59-4.57-1.41-2.07-3.62-2.35-4.4-2.39-1.87-.19-3.66 1.1-4.6 1.1-.96 0-2.41-1.08-3.97-1.05-2.04.03-3.93 1.18-4.98 3-2.13 3.69-.54 9.13 1.51 12.12.99 1.46 2.18 3.11 3.74 3.05 1.5-.06 2.07-.97 3.88-.97s2.33.97 3.92.94c1.62-.03 2.65-1.49 3.65-2.96 1.15-1.7 1.62-3.34 1.65-3.43-.04-.02-3.16-1.21-3.19-4.81zM14.45 4.18c.83-1.01 1.39-2.41 1.24-3.81-1.2.05-2.65.8-3.51 1.8-.77.89-1.45 2.32-1.27 3.7 1.34.1 2.71-.68 3.54-1.69z"/></svg> },
    { name: 'Google', glyph: <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M21.35 11.1H12v3.05h5.35c-.23 1.3-1.45 3.8-5.35 3.8-3.22 0-5.85-2.66-5.85-5.95s2.63-5.95 5.85-5.95c1.83 0 3.05.78 3.75 1.45l2.55-2.46C16.7 3.55 14.55 2.5 12 2.5c-5.18 0-9.4 4.22-9.4 9.5s4.22 9.5 9.4 9.5c5.43 0 9-3.82 9-9.2 0-.62-.07-1.1-.15-1.2z"/></svg> },
    { name: 'Email',  glyph: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><polyline points="22 6 12 13 2 6"/></svg> },
  ];
  return (
    <div style={{ display: 'flex', gap: 8 }}>
      {opts.map(o => (
        <button key={o.name} style={{
          flex: 1, minHeight: 48, borderRadius: 12,
          background: C_au.bg.primary, border: `1px solid ${C_au.border.medium}`,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          font: '600 13px/1 var(--qaren-font-en, system-ui)', color: C_au.text.primary,
          cursor: 'pointer',
        }}>
          {o.glyph}
          {o.name}
        </button>
      ))}
    </div>
  );
}

function OrDivider() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBlock: 20 }}>
      <div style={{ flex: 1, height: 1, background: C_au.border.light }} />
      <span style={{ font: '500 11px/1.3 var(--qaren-font-en, system-ui)', color: C_au.text.placeholder, letterSpacing: '0.6px', textTransform: 'uppercase' }}>or</span>
      <div style={{ flex: 1, height: 1, background: C_au.border.light }} />
    </div>
  );
}

// ─── SignInScreen ───────────────────────────────────────────────────────
function QarenSignInScreen() {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: C_au.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_au.text.primary,
    }}>
      <header style={{ display: 'flex', alignItems: 'center', paddingInline: 20, paddingTop: 8, paddingBottom: 12 }}>
        <button aria-label="Back" style={{
          width: 36, height: 36, borderRadius: 18,
          background: 'transparent', border: 'none',
          display: 'grid', placeItems: 'center', cursor: 'pointer',
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_au.text.primary} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', paddingInline: 24 }}>
        <h1 style={{ margin: '8px 0 8px', font: '700 32px/1.2 var(--qaren-font-en, system-ui)', letterSpacing: '-0.4px' }}>
          Welcome back.
        </h1>
        <p style={{ margin: '0 0 24px', font: '400 14px/1.5 var(--qaren-font-en, system-ui)', color: C_au.text.secondary }}>
          Your advisor and credits are waiting.
        </p>

        <SocialRow />
        <OrDivider />

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <AuthField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoFocus />
          <AuthField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          <button style={{
            alignSelf: 'flex-end', background: 'none', border: 'none', cursor: 'pointer',
            font: '500 12px/1 var(--qaren-font-en, system-ui)', color: C_au.accentDark,
          }}>
            Forgot password?
          </button>
        </div>
      </main>

      <div style={{
        paddingInline: 20, paddingTop: 12, paddingBottom: 16,
        borderTop: `1px solid ${C_au.border.light}`, background: C_au.bg.primary,
      }}>
        <button style={{
          width: '100%', height: 52, borderRadius: 999, border: 'none',
          background: C_au.cta.primary, color: C_au.cta.onPrimary,
          font: '600 16px/1.5 var(--qaren-font-en, system-ui)', cursor: 'pointer',
        }}>
          Sign in
        </button>
        <div style={{
          marginTop: 10, textAlign: 'center',
          font: '500 12px/1.4 var(--qaren-font-en, system-ui)', color: C_au.text.secondary,
        }}>
          New here? <span style={{ color: C_au.text.primary, textDecoration: 'underline' }}>Create an account</span>
        </div>
      </div>
    </div>
  );
}

// ─── SaveAdvisorScreen (Onboarding s16) ─────────────────────────────────
// CRITICAL: NO skip link. Codebase memory verifies this is forced.
function QarenSaveAdvisorScreen() {
  const [email, setEmail] = React.useState('');
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: C_au.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_au.text.primary,
    }}>
      {/* Progress bar (no back arrow — forced step) */}
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, paddingInline: 20, paddingTop: 8, paddingBottom: 16 }}>
        <div style={{ flex: 1, height: 4, borderRadius: 2, background: C_au.border.light, overflow: 'hidden' }}>
          <div style={{ width: '94%', height: '100%', background: C_au.cta.primary }} />
        </div>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', paddingInline: 24 }}>
        {/* Hero — emerald-tint check */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 18 }}>
          <div style={{
            width: 72, height: 72, borderRadius: 36,
            background: C_au.accentLight, color: C_au.accentDark,
            display: 'grid', placeItems: 'center',
          }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 21V5a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v16l7-3 7 3z"/>
            </svg>
          </div>
        </div>

        <h1 style={{ margin: '0 0 8px', font: '700 28px/1.2 var(--qaren-font-en, system-ui)', letterSpacing: '-0.32px', textAlign: 'center' }}>
          Save your advisor.
        </h1>
        <p style={{
          margin: '0 0 24px', textAlign: 'center', maxWidth: 320, marginInline: 'auto',
          font: '400 14px/1.5 var(--qaren-font-en, system-ui)', color: C_au.text.secondary,
        }}>
          So your match travels with you. Sync your profile across devices and never lose your decisions.
        </p>

        <SocialRow />
        <OrDivider />
        <AuthField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoFocus />

        <p style={{
          margin: '18px 0 0',
          font: '400 11px/1.5 var(--qaren-font-en, system-ui)', color: C_au.text.placeholder,
          textAlign: 'center',
        }}>
          By continuing, you agree to our <span style={{ color: C_au.text.secondary, textDecoration: 'underline' }}>Terms</span> &amp; <span style={{ color: C_au.text.secondary, textDecoration: 'underline' }}>Privacy Policy</span>.
        </p>
      </main>

      <div style={{
        paddingInline: 20, paddingTop: 12, paddingBottom: 16,
        borderTop: `1px solid ${C_au.border.light}`, background: C_au.bg.primary,
      }}>
        <button style={{
          width: '100%', height: 52, borderRadius: 999, border: 'none',
          background: C_au.cta.primary, color: C_au.cta.onPrimary,
          font: '600 16px/1.5 var(--qaren-font-en, system-ui)', cursor: 'pointer',
        }}>
          Save my advisor
        </button>
        {/* NO skip link — forced per design system rule. */}
      </div>
    </div>
  );
}

window.QarenSignInScreen = QarenSignInScreen;
window.QarenSaveAdvisorScreen = QarenSaveAdvisorScreen;
