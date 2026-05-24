/**
 * Qaren — DemographicsBottomSheet (reference, web)
 *
 * Source of truth: AI/smartcompare/SmartCompareApp/src/components/DemographicsBottomSheet.tsx
 *
 * Bottom sheet that pops on Results after the first comparison to capture
 * age / gender / governorate — three quick taps to tune the cohort match.
 * Copy from en.json `demographics.*`.
 */

const T_d = window.qarenTokens || {};
const C_d = T_d.colors || {};

function PickerGroup({ label, options, value, onChange }) {
  return (
    <section style={{ marginBottom: 18 }}>
      <div style={{
        font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
        letterSpacing: '1.1px', textTransform: 'uppercase',
        color: C_d.text.secondary, marginBottom: 8,
      }}>
        {label}
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {options.map((o) => {
          const active = o === value;
          return (
            <button
              key={o}
              onClick={() => onChange(o)}
              aria-pressed={active}
              style={{
                minHeight: 44, paddingInline: 14,
                borderRadius: 999,
                background: active ? C_d.cta.primary : C_d.bg.secondary,
                border: `1px solid ${active ? C_d.cta.primary : C_d.border.light}`,
                color: active ? C_d.cta.onPrimary : C_d.text.primary,
                font: `${active ? 600 : 500} 13px/1 var(--qaren-font-en, system-ui)`,
                cursor: 'pointer',
              }}
            >
              {o}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function QarenDemographicsBottomSheet() {
  const [age, setAge] = React.useState('25-34');
  const [gender, setGender] = React.useState('Female');
  const [gov, setGov] = React.useState('Capital');

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      position: 'relative',
      background: C_d.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_d.text.primary,
    }}>
      {/* dim layer */}
      <div aria-hidden="true" style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(180deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.65) 100%)',
      }} />

      {/* sheet */}
      <div style={{
        position: 'absolute', insetInlineStart: 0, insetInlineEnd: 0, insetBlockEnd: 0,
        background: C_d.bg.primary,
        borderStartStartRadius: 24, borderStartEndRadius: 24,
        boxShadow: '0 -8px 24px rgba(0,0,0,0.18)',
        paddingBottom: 16,
        display: 'flex', flexDirection: 'column',
        maxHeight: '88%',
      }}>
        <div style={{ display: 'grid', placeItems: 'center', paddingTop: 8, paddingBottom: 4 }}>
          <div style={{ width: 40, height: 4, borderRadius: 2, background: C_d.border.medium }} />
        </div>

        <div style={{ paddingInline: 20, paddingTop: 6, overflow: 'auto' }}>
          <h2 style={{ margin: 0, font: '700 22px/1.25 var(--qaren-font-en, system-ui)', color: C_d.text.primary }}>
            Tell us about you
          </h2>
          <p style={{ margin: '6px 0 18px', font: '400 13px/1.5 var(--qaren-font-en, system-ui)', color: C_d.text.secondary, maxWidth: 320 }}>
            Want recommendations tuned to people like you? 3 quick taps.
          </p>

          <PickerGroup
            label="Age group"
            options={['18-24', '25-34', '35-44', '45-54', '55+']}
            value={age}
            onChange={setAge}
          />
          <PickerGroup
            label="Gender"
            options={['Female', 'Male', 'Prefer not to say']}
            value={gender}
            onChange={setGender}
          />
          <PickerGroup
            label="Governorate"
            options={['Capital', 'Muharraq', 'Northern', 'Southern', 'Other']}
            value={gov}
            onChange={setGov}
          />
        </div>

        <div style={{ paddingInline: 20, paddingTop: 12, borderTop: `1px solid ${C_d.border.light}` }}>
          <button style={{
            width: '100%', height: 52, borderRadius: 999,
            background: C_d.cta.primary, color: C_d.cta.onPrimary, border: 'none', cursor: 'pointer',
            font: '600 16px/1 var(--qaren-font-en, system-ui)',
          }}>
            Save
          </button>
          <button style={{
            width: '100%', height: 40, marginTop: 4,
            background: 'transparent', border: 'none',
            color: C_d.text.secondary,
            font: '500 13px/1.5 var(--qaren-font-en, system-ui)', cursor: 'pointer',
          }}>
            Skip for now
          </button>
        </div>
      </div>
    </div>
  );
}

window.QarenDemographicsBottomSheet = QarenDemographicsBottomSheet;
