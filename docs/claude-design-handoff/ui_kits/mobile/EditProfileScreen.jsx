/**
 * Qaren — EditProfileScreen (reference, web)
 *
 * Source of truth: AI/smartcompare/SmartCompareApp/src/screens/EditProfileScreen.tsx
 *
 * Modal-style screen pushed from Profile. Anatomy:
 *   1. Header — ←  Edit Profile  ·  (centered title)
 *   2. Avatar block — large circle with letter + "Photo upload coming soon"
 *   3. ACCOUNT card — name field (text input) + email field (read-only,
 *      lighter background)
 *   4. "Edit style profile" navigation row → opens Onboarding in edit mode
 *   5. Save CTA (sticky bottom, disabled until something changes — here
 *      always disabled to match the screenshot's initial state)
 *   6. ACCOUNT ACTIONS — Delete account (destructive)
 *
 * Visually quieter than Profile — it's a focused edit surface. Copy passes
 * the policy fence; "Photo upload coming soon" is the production placeholder.
 */

const T_ep = window.qarenTokens || {};
const C_ep = T_ep.colors || {};

function EpHeader() {
  return (
    <header style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      paddingInline: 20, paddingTop: 8, paddingBottom: 12,
      borderBottom: `1px solid ${C_ep.border.light}`,
    }}>
      <button aria-label="Back" style={{
        width: 36, height: 36, borderRadius: 18,
        background: 'transparent', border: 'none',
        display: 'grid', placeItems: 'center', cursor: 'pointer',
      }}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_ep.text.primary} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <h1 style={{ margin: 0, font: '700 17px/1.3 var(--qaren-font-en, system-ui)', color: C_ep.text.primary }}>
        Edit Profile
      </h1>
      <div style={{ width: 36, height: 36, flexShrink: 0 }} />
    </header>
  );
}

function AvatarBlock({ name = 'Kareem' }) {
  const initial = (name || 'Q').trim().charAt(0).toUpperCase();
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
      paddingBlock: 28,
    }}>
      <div style={{
        width: 96, height: 96, borderRadius: 48,
        background: C_ep.bg.secondary,
        display: 'grid', placeItems: 'center',
        font: '700 36px/1 var(--qaren-font-en, system-ui)', color: C_ep.text.primary,
      }}>{initial}</div>
      <div style={{ font: '400 13px/1.5 var(--qaren-font-en, system-ui)', color: C_ep.text.secondary }}>
        Photo upload coming soon
      </div>
    </div>
  );
}

function EyebrowHeader({ children }) {
  return (
    <div style={{
      font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
      letterSpacing: '1.1px', textTransform: 'uppercase',
      color: C_ep.text.secondary,
      paddingInline: 20, marginBottom: 8, marginTop: 12,
    }}>{children}</div>
  );
}

function FormCard({ children }) {
  return (
    <section style={{
      marginInline: 20, marginBottom: 16,
      padding: 16,
      borderRadius: 16,
      background: C_ep.bg.secondary,
      border: `1px solid ${C_ep.border.light}`,
      display: 'flex', flexDirection: 'column', gap: 14,
    }}>{children}</section>
  );
}

function Field({ label, value, placeholder, readOnly, onChange }) {
  const [focused, setFocused] = React.useState(false);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label style={{
        font: '500 12px/1.4 var(--qaren-font-en, system-ui)',
        color: C_ep.text.secondary,
      }}>{label}</label>
      <div style={{
        height: 48, paddingInline: 14,
        borderRadius: 12,
        background: readOnly ? 'transparent' : C_ep.bg.primary,
        border: `${focused && !readOnly ? 2 : 1}px solid ${focused && !readOnly ? C_ep.text.primary : C_ep.border.light}`,
        display: 'flex', alignItems: 'center',
      }}>
        <input
          value={value}
          onChange={onChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          readOnly={readOnly}
          placeholder={placeholder}
          style={{
            width: '100%', border: 'none', outline: 'none', background: 'transparent',
            font: '400 16px/1.5 var(--qaren-font-en, system-ui)',
            color: readOnly ? C_ep.text.secondary : C_ep.text.primary,
          }}
        />
      </div>
    </div>
  );
}

function NavRow({ icon, label, sub, destructive }) {
  const color = destructive ? C_ep.destructive : C_ep.text.primary;
  return (
    <button style={{
      display: 'flex', alignItems: 'center', gap: 12,
      width: '100%', minHeight: 56,
      paddingBlock: 14, paddingInline: 16,
      background: 'transparent', border: 'none',
      textAlign: 'start', cursor: 'pointer',
    }}>
      {icon && (
        <span style={{ width: 36, height: 36, borderRadius: 18, background: C_ep.bg.primary, display: 'grid', placeItems: 'center', color, flexShrink: 0 }}>
          {icon}
        </span>
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ font: '600 15px/1.3 var(--qaren-font-en, system-ui)', color }}>{label}</div>
        {sub && <div style={{ font: '400 12px/1.4 var(--qaren-font-en, system-ui)', color: C_ep.text.secondary, marginTop: 2 }}>{sub}</div>}
      </div>
      {!destructive && (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_ep.text.placeholder} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      )}
    </button>
  );
}

const __skEp = (d, w = 18) => (
  <svg width={w} height={w} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{d}</svg>
);

function QarenEditProfileScreen() {
  const [name, setName]   = React.useState('Kareem');
  const [email]           = React.useState('kinghaleem999@gmail.com');
  const dirty = name.trim() !== 'Kareem';

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      background: C_ep.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_ep.text.primary,
    }}>
      <EpHeader />

      <main style={{ flex: 1, overflowY: 'auto', paddingBottom: 8 }}>
        <AvatarBlock name={name} />

        <EyebrowHeader>Account</EyebrowHeader>
        <FormCard>
          <Field
            label="Display name"
            value={name}
            placeholder="Your name"
            onChange={(e) => setName(e.target.value)}
          />
          <Field
            label="Email"
            value={email}
            readOnly
          />
        </FormCard>

        <NavRow
          icon={__skEp(<><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></>)}
          label="Edit style profile"
          sub="Update priorities, budget, and brand stance"
        />

        <EyebrowHeader>Account actions</EyebrowHeader>
        <div style={{
          marginInline: 20, marginBottom: 16,
          borderRadius: 16,
          background: C_ep.bg.secondary,
          border: `1px solid ${C_ep.border.light}`,
          overflow: 'hidden',
        }}>
          <NavRow
            icon={__skEp(<><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></>)}
            label="Delete account"
            destructive
          />
        </div>
      </main>

      {/* Sticky Save CTA */}
      <div style={{
        paddingInline: 20, paddingTop: 12, paddingBottom: 16,
        borderTop: `1px solid ${C_ep.border.light}`,
        background: C_ep.bg.primary,
      }}>
        <button
          disabled={!dirty}
          style={{
            width: '100%', height: 52, borderRadius: 999,
            border: 'none',
            background: C_ep.cta.primary, color: C_ep.cta.onPrimary,
            font: '600 16px/1.5 var(--qaren-font-en, system-ui)',
            opacity: dirty ? 1 : 0.4,
            cursor: dirty ? 'pointer' : 'not-allowed',
          }}
        >
          Save
        </button>
      </div>
    </div>
  );
}

window.QarenEditProfileScreen = QarenEditProfileScreen;
