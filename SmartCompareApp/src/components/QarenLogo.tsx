/**
 * QarenLogo — the in-app MYEZ mark (session 71, unit U4c).
 * Spec: docs/investigations/2026-10-03-session-71-state/U4C_INAPP_MARK_SPEC.md
 *
 * Draws Ahmed's MYEZ logo (the black MY/EZ wordmark and the emerald dot)
 * as ONE bundled PNG, so the app shows the same mark as the launcher icon.
 * The three scales assets/brand/myez-mark.png, @2x and @3x are rendered from
 * the committed master by scripts/render_myez_icons.py — never hand-edit
 * them. The component keeps its name and path (identifiers stay `qaren`).
 *
 * The PNG carries its own colours: there is no colour prop and no tint. Its
 * transparency is exact over white, which is what every current site has.
 *
 * `fadeDuration={0}`: Android fades a non-resource image in over 300 ms, and
 * an asset delivered by an OTA update is a file, not a resource. iOS
 * ignores the prop.
 */
import React from 'react';
import { Image } from 'react-native';

// Module scope: the require is resolved once and Metro bundles every scale.
const MARK = require('../../assets/brand/myez-mark.png');

type Props = {
  size?: number;
};

export default function QarenLogo({ size = 32 }: Props) {
  return (
    // Decorative, hidden from VoiceOver/TalkBack exactly as the old glyph
    // was: the mark has no label, and any title beside it speaks for the
    // screen. Matches the decorative-overlay pattern used in ScannerReticle.
    <Image
      source={MARK}
      style={{ width: size, height: size }}
      resizeMode="contain"
      fadeDuration={0}
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
    />
  );
}
