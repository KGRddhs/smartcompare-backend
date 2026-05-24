/**
 * Qaren — ShareBottomSheet v3 (modern, visual-first)
 *
 * v2 still felt list-y. v3 leads with the SHARED VS-PAIR as a hero card
 * — show the user exactly what they're sending. Then a clean message
 * card, then the reward inline as an emerald-accent line, then share
 * targets as a single row with bigger glyphs. Privacy stays as a quiet
 * tap-to-expand line at the bottom.
 *
 * Note on share-target icons: shape-true placeholders — Claude Code
 * should swap to official brand assets. `data-placeholder="brand-icon"`.
 */

const T_sh3 = window.qarenTokens || {};
const C_sh3 = T_sh3.colors || {};

function PreviewVs() {
  return (
    <section style={{
      padding: 14,
      borderRadius: 18,
      background: C_sh3.bg.secondary, border: `1px solid ${C_sh3.border.light}`,
      marginBottom: 18,
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{
          display: 'inline-flex', paddingInline: 10, height: 22, alignItems: 'center', borderRadius: 999,
          background: C_sh3.bg.primary,
          font: '600 10px/1 var(--qaren-font-en, system-ui)',
          color: C_sh3.text.secondary,
          letterSpacing: '0.6px', textTransform: 'uppercase',
        }}>Electronics</span>
        <span style={{
          display: 'inline-flex', paddingInline: 8, height: 22, alignItems: 'center', borderRadius: 999,
          background: C_sh3.accentLight, color: C_sh3.accentDark,
          font: '700 9px/1 var(--qaren-font-en, system-ui)',
          letterSpacing: '1px', textTransform: 'uppercase',
        }}>
          Top match
        </span>
      </div>

      <div style={{ position: 'relative', display: 'flex', gap: 8 }}>
        <PreviewTile tone="#E8E9ED" name="iPhone 15" />
        <div style={{
          position: 'absolute', insetBlockStart: '50%', insetInlineStart: '50%',
          transform: 'translate(-50%, -50%)',
        }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            height: 22, paddingInline: 10, borderRadius: 999,
            background: C_sh3.accentLight, color: C_sh3.accentDark,
            font: '700 11px/1 var(--qaren-font-en, system-ui)',
            letterSpacing: '1px', textTransform: 'uppercase',
            border: `2px solid ${C_sh3.bg.secondary}`,
          }}>vs</span>
        </div>
        <PreviewTile tone="#1B1C1F" name="Galaxy S24" winner />
      </div>

      <div style={{ font: '500 12px/1.4 var(--qaren-font-en, system-ui)', color: C_sh3.text.secondary }}>
        Picked Galaxy — camera + battery edged out Apple here.
      </div>
    </section>
  );
}

function PreviewTile({ tone, name, winner }) {
  return (
    <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{
        aspectRatio: '1 / 1', borderRadius: 12,
        background: tone, position: 'relative',
        display: 'grid', placeItems: 'center', color: 'rgba(0,0,0,0.18)',
        border: winner ? `2px solid ${C_sh3.accent}` : 'none',
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="5" y="2" width="14" height="20" rx="2.5"/>
        </svg>
        {winner && (
          <span style={{
            position: 'absolute', insetBlockStart: 4, insetInlineEnd: 4,
            width: 18, height: 18, borderRadius: 9, background: C_sh3.accent,
            display: 'grid', placeItems: 'center', border: `2px solid ${C_sh3.bg.secondary}`,
          }}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </span>
        )}
      </div>
      <div style={{ font: `${winner ? 700 : 500} 13px/1.3 var(--qaren-font-en, system-ui)`, color: C_sh3.text.primary, paddingInline: 2 }}>
        {name}
      </div>
    </div>
  );
}

function MessageCard() {
  return (
    <section style={{
      padding: 14, borderRadius: 18,
      background: C_sh3.bg.primary, border: `1px solid ${C_sh3.border.light}`,
      marginBottom: 14,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 8,
      }}>
        <span style={{ font: '500 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '0.6px', textTransform: 'uppercase', color: C_sh3.text.secondary }}>
          Your message
        </span>
        <button style={{
          background: 'none', border: 'none', cursor: 'pointer',
          font: '600 12px/1 var(--qaren-font-en, system-ui)', color: C_sh3.accentDark,
        }}>
          Edit
        </button>
      </div>
      <div style={{
        font: '500 14px/1.55 var(--qaren-font-en, system-ui)',
        color: C_sh3.text.primary, textWrap: 'pretty',
      }}>
        I overthink every purchase. Qaren ends the debate in 30 seconds. Worth a try?
      </div>
      <div style={{
        marginTop: 10, paddingTop: 10,
        borderTop: `1px dashed ${C_sh3.border.light}`,
        font: '500 12px/1.4 var(--qaren-font-en, system-ui)', color: C_sh3.accentDark,
      }}>
        qaren.app/qr-7F4K2A
      </div>
    </section>
  );
}

function RewardLine() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '12px 14px', borderRadius: 14,
      background: C_sh3.accentLight, color: C_sh3.accentDark,
      marginBottom: 18,
    }}>
      <span style={{
        width: 28, height: 28, borderRadius: 14, flexShrink: 0,
        background: C_sh3.accent, color: '#FFFFFF',
        display: 'grid', placeItems: 'center',
      }}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><line x1="12" y1="22" x2="12" y2="7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>
        </svg>
      </span>
      <div style={{ flex: 1, font: '600 13px/1.4 var(--qaren-font-en, system-ui)' }}>
        <span style={{ fontWeight: 700 }}>+1 Deep Review credit</span> for you, <span style={{ fontWeight: 700 }}>+5 comparisons</span> if they sign up.
      </div>
    </div>
  );
}

function ShareTarget({ name, color, glyph, dark }) {
  return (
    <button
      data-placeholder="brand-icon"
      style={{
        flex: 1, minWidth: 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
        background: 'transparent', border: 'none', cursor: 'pointer',
        padding: 0,
      }}
    >
      <span style={{
        width: 52, height: 52, borderRadius: 18,
        background: color, color: dark ? '#000' : '#FFF',
        display: 'grid', placeItems: 'center',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      }}>
        {glyph}
      </span>
      <span style={{ font: '500 11px/1.3 var(--qaren-font-en, system-ui)', color: C_sh3.text.secondary }}>{name}</span>
    </button>
  );
}

function QarenShareBottomSheet() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', paddingTop: 50,
      position: 'relative',
      background: C_sh3.bg.primary,
      fontFamily: 'var(--qaren-font-en, system-ui)',
      color: C_sh3.text.primary,
    }}>
      {/* dimmed Results backdrop */}
      <div aria-hidden="true" style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(180deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.65) 100%)',
      }} />
      <div aria-hidden="true" style={{
        position: 'absolute', insetInlineStart: 20, insetInlineEnd: 20, insetBlockStart: 110,
        display: 'flex', gap: 10, opacity: 0.22,
      }}>
        <div style={{ flex: 1, aspectRatio: '0.7 / 1', borderRadius: 16, background: '#E8E9ED' }} />
        <div style={{ flex: 1, aspectRatio: '0.7 / 1', borderRadius: 16, background: '#1B1C1F' }} />
      </div>

      {/* Sheet */}
      <div style={{
        position: 'absolute', insetInlineStart: 0, insetInlineEnd: 0, insetBlockEnd: 0,
        background: C_sh3.bg.primary,
        borderStartStartRadius: 28, borderStartEndRadius: 28,
        boxShadow: '0 -8px 24px rgba(0,0,0,0.18)',
        paddingBottom: 20,
        maxHeight: '90%', overflow: 'hidden',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* Grab bar + close */}
        <div style={{ position: 'relative', display: 'grid', placeItems: 'center', paddingTop: 10, paddingBottom: 4 }}>
          <div style={{ width: 40, height: 4, borderRadius: 2, background: C_sh3.border.medium }} />
          <button aria-label="Close" style={{
            position: 'absolute', insetInlineEnd: 16, insetBlockStart: 6,
            width: 32, height: 32, borderRadius: 16,
            background: C_sh3.bg.secondary, border: 'none',
            display: 'grid', placeItems: 'center', cursor: 'pointer',
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={C_sh3.text.primary} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <div style={{ paddingInline: 20, paddingTop: 12, overflow: 'auto' }}>
          <h2 style={{ margin: '0 0 4px', font: '700 22px/1.25 var(--qaren-font-en, system-ui)' }}>
            Share this verdict
          </h2>
          <p style={{ margin: '0 0 18px', font: '400 13px/1.5 var(--qaren-font-en, system-ui)', color: C_sh3.text.secondary }}>
            Send a friend the comparison you ran — they'll get 5 free.
          </p>

          <PreviewVs />
          <MessageCard />
          <RewardLine />

          <div style={{
            font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
            letterSpacing: '1.1px', textTransform: 'uppercase',
            color: C_sh3.text.secondary, marginBottom: 12,
          }}>
            Send to
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6, marginBottom: 8 }}>
            <ShareTarget name="WhatsApp" color="#25D366" glyph={
              <svg width="26" height="26" viewBox="0 0 32 32" fill="#FFFFFF">
                <path d="M16 5.3c-5.9 0-10.7 4.8-10.7 10.7 0 1.9.5 3.7 1.4 5.3l-1.5 5.5 5.6-1.5a10.6 10.6 0 0 0 5.1 1.3h.01c5.9 0 10.7-4.8 10.7-10.7a10.6 10.6 0 0 0-3.1-7.5A10.6 10.6 0 0 0 16 5.3zm6.2 15.1c-.3.7-1.5 1.4-2.1 1.5-.5.1-1.2.1-2-.1-.5-.1-1.1-.3-1.8-.7-3.2-1.4-5.3-4.6-5.4-4.8-.2-.2-1.3-1.7-1.3-3.3 0-1.6.8-2.3 1.1-2.7.3-.3.6-.4.9-.4h.6c.2 0 .5-.1.7.5.3.6.9 2.2 1 2.4.1.2.1.3 0 .6-.1.2-.2.3-.3.5-.2.2-.3.4-.5.6-.2.2-.3.3-.1.7.2.3.8 1.4 1.8 2.2 1.2 1.1 2.3 1.4 2.6 1.6.3.2.5.1.7-.1.2-.2.8-.9 1-1.3.2-.3.4-.3.6-.2.3.1 1.6.8 1.9.9.3.1.5.2.5.3.1.1.1.7-.2 1.3z"/>
              </svg>
            } />
            <ShareTarget name="Telegram" color="#229ED9" glyph={
              <svg width="24" height="24" viewBox="0 0 24 24" fill="#FFFFFF"><path d="M22 4 2.5 11.5l5.5 2 2 6.5 3-3 5.5 4z"/></svg>
            } />
            <ShareTarget name="X" color="#000000" glyph={
              <svg width="22" height="22" viewBox="0 0 24 24" fill="#FFFFFF"><path d="M17.5 2h3l-6.5 7.4L22 22h-6l-4.7-5.7L5.9 22H3l7-8L2 2h6l4.2 5.2L17.5 2z"/></svg>
            } />
            <ShareTarget name="Instagram" color="#E1306C" glyph={
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="#FFFFFF"/></svg>
            } />
            <ShareTarget name="Copy" color="#1F2937" glyph={
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            } />
          </div>

          {/* Privacy footnote */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            paddingBlock: 8,
            font: '400 11px/1.4 var(--qaren-font-en, system-ui)', color: C_sh3.text.secondary,
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-7 8-13a8 8 0 0 0-16 0c0 6 8 13 8 13z"/></svg>
            Your budget and personal answers stay private.
          </div>
        </div>
      </div>
    </div>
  );
}

window.QarenShareBottomSheet = QarenShareBottomSheet;
