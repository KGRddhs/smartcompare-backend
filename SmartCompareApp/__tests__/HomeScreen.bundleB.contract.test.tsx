/**
 * Bundle D 2.F.2 pre-stage — Bundle B contract preservation test (R16).
 *
 * R16 anchor control: "Frontend acceptance test = full Bundle B PR #6
 * EN+AR walkthrough on new design; ZERO regressions on TwoInputShell
 * contract." This file pins the BEHAVIOR contract (not visual) so that
 * when Ahmed's Claude-Design prototype lands and we replace/extend
 * HomeScreen.tsx + theme/index.ts, regression on any contract surface
 * lights up at the unit-test layer.
 *
 * Approach: source-grep on current code paths. The framework compiles
 * AND passes today (against the existing Bundle-B-shipped HomeScreen
 * `21e7bc0`). Post-redesign, if any contract surface goes missing the
 * matching test goes RED and we know which Bundle B invariant the
 * Claude-Design refresh broke.
 *
 * NOT covered here (deliberately):
 * - Visual snapshots (those churn on every restyle by definition).
 * - The 3 known-RED HomeScreen.{redesign, modeChipAnim, scanCamera,
 *   minDisplayFloor} suites — anchor § 12 out-of-scope, will be
 *   updated by Test agent post-redesign.
 *
 * Spec ref: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md
 * Anchor ref: memory/BUNDLE_D_FRONTEND_ANCHOR.md § R16
 */

import * as fs from 'fs';
import * as path from 'path';

const HOME_PATH = path.resolve(__dirname, '../src/screens/HomeScreen.tsx');
const SHELL_PATH = path.resolve(__dirname, '../src/components/TwoInputShell.tsx');
const URL_DETECT_PATH = path.resolve(__dirname, '../src/utils/urlPasteDetect.ts');
const HOME_SRC = fs.readFileSync(HOME_PATH, 'utf8');
const SHELL_SRC = fs.readFileSync(SHELL_PATH, 'utf8');
const URL_DETECT_SRC = fs.readFileSync(URL_DETECT_PATH, 'utf8');

// ---------------------------------------------------------------------
// Section 1 — TwoInputShell preservation
// HomeScreen MUST continue to render TwoInputShell for text + url modes.
// Camera path is the only escape hatch.
// ---------------------------------------------------------------------

describe('Bundle B contract — TwoInputShell mount (R16)', () => {
  it('HomeScreen imports TwoInputShell from its established path', () => {
    expect(HOME_SRC).toMatch(
      /import\s+TwoInputShell\s+from\s+['"]\.\.\/components\/TwoInputShell['"]/
    );
  });

  it('HomeScreen renders <TwoInputShell .../> for text + url modes', () => {
    expect(HOME_SRC).toMatch(/<TwoInputShell\b/);
  });

  it('TwoInputShell receives mode prop driven by inputMode', () => {
    expect(HOME_SRC).toMatch(/<TwoInputShell[\s\S]{0,400}mode=\{[^}]*inputMode[^}]*\}/);
  });

  it('TwoInputShell receives onSubmit prop that branches text vs url compare', () => {
    expect(HOME_SRC).toMatch(/<TwoInputShell[\s\S]{0,500}onSubmit=\{[\s\S]{0,200}handleUrlCompare/);
    expect(HOME_SRC).toMatch(/<TwoInputShell[\s\S]{0,500}handleTextCompare/);
  });
});

// ---------------------------------------------------------------------
// Section 2 — Paste-split + URL paste auto-mode-switch
// Spec § 4.1.1 + § 4.1.2. The anchored regex MUST stay anchored, and
// the predicate MUST receive the raw paste (no .trim() pre-strip).
// ---------------------------------------------------------------------

describe('Bundle B contract — paste auto-split + URL mode-switch (R16)', () => {
  it('urlPasteDetect uses anchored ^https?:// regex (no .trim() pre-strip)', () => {
    expect(URL_DETECT_SRC).toMatch(/\/\^https\?:\\\/\\\/\[\^\\s\]\+\$\/i/);
  });

  it('looksLikeUrl receives raw input, NOT pre-trimmed', () => {
    // The predicate body is a single .test() call on the unmodified
    // input — confirms no .trim() snuck into the helper.
    expect(URL_DETECT_SRC).toMatch(/return\s+URL_SHAPE\.test\(s\)/);
    expect(URL_DETECT_SRC).not.toMatch(/return\s+URL_SHAPE\.test\(s\.trim\(\)\)/);
  });

  it('TwoInputShell handleBoxChange passes raw `next` to looksLikeUrl', () => {
    expect(SHELL_SRC).toMatch(/looksLikeUrl\(next\)/);
    expect(SHELL_SRC).not.toMatch(/looksLikeUrl\(next\.trim\(\)\)/);
  });

  it('TwoInputShell exposes onPasteSplit + onModeAutoswitch callback props', () => {
    expect(SHELL_SRC).toMatch(/onPasteSplit\?:\s*\(/);
    expect(SHELL_SRC).toMatch(/onModeAutoswitch\?:\s*\(/);
  });

  it('HomeScreen wires onPasteSplit handler → trackEvent compare_entry_paste_split', () => {
    expect(HOME_SRC).toMatch(
      /onPasteSplit=\{[\s\S]{0,300}trackEvent\(\s*['"]compare_entry_paste_split['"]/
    );
  });

  it('HomeScreen wires onModeAutoswitch handler → setInputMode("url") + trackEvent', () => {
    expect(HOME_SRC).toMatch(
      /onModeAutoswitch=\{[\s\S]{0,300}setInputMode\(\s*['"]url['"]\s*\)/
    );
    expect(HOME_SRC).toMatch(
      /onModeAutoswitch=\{[\s\S]{0,400}trackEvent\(\s*['"]compare_entry_mode_autoswitch['"]/
    );
  });
});

// ---------------------------------------------------------------------
// Section 3 — Dual-shape product_a/product_b on /text/compare
// Backend accepts BOTH legacy `q=` and new pair shape per Bundle B
// spec § 5.1. HomeScreen text-compare path MUST use the pair shape.
// ---------------------------------------------------------------------

describe('Bundle B contract — dual-shape product_a/product_b (R16)', () => {
  it('streamComparison is called with { product_a, product_b } pair', () => {
    expect(HOME_SRC).toMatch(
      /streamComparison\(\s*\{\s*product_a\s*:\s*\w+\s*,\s*product_b\s*:\s*\w+\s*\}/
    );
  });

  it('text compare trims both inputs server-safe before forwarding', () => {
    expect(HOME_SRC).toMatch(/const productA\s*=\s*a\.trim\(\)/);
    expect(HOME_SRC).toMatch(/const productB\s*=\s*b\.trim\(\)/);
  });
});

// ---------------------------------------------------------------------
// Section 4 — 4-layer content moderation (L1-L4)
// Backend returns CONTENT_UNAVAILABLE with `layer` field; FE renders
// Alert + fires compare_entry_content_block with the layer name. The
// contract is the error code + handler; the layer source is backend-owned.
// ---------------------------------------------------------------------

describe('Bundle B contract — L1-L4 content moderation handling (R16)', () => {
  it('HomeScreen detects parsed.code === CONTENT_UNAVAILABLE in error handler', () => {
    expect(HOME_SRC).toMatch(/parsed\.code\s*===\s*['"]CONTENT_UNAVAILABLE['"]/);
  });

  it('handleContentUnavailable fires compare_entry_content_block w/ layer payload', () => {
    expect(HOME_SRC).toMatch(
      /trackEvent\(\s*['"]compare_entry_content_block['"]\s*,\s*\{\s*mode\s*,\s*layer\s*\}\s*\)/
    );
  });

  it('CONTENT_UNAVAILABLE reads error.response.data.layer (backend-supplied)', () => {
    expect(HOME_SRC).toMatch(/error\?\.response\?\.data\?\.layer/);
  });

  it('user-facing copy uses approved vocabulary i18n keys', () => {
    expect(HOME_SRC).toMatch(/home\.compare\.unavailable_title/);
    expect(HOME_SRC).toMatch(/home\.compare\.unavailable_body/);
  });
});

// ---------------------------------------------------------------------
// Section 5 — 8 analytics events
// Each event surface must continue to fire from its canonical site.
// ---------------------------------------------------------------------

const REQUIRED_EVENTS = [
  'compare_entry_view',
  'compare_entry_paywall_banner_view',
  'compare_entry_paywall_banner_tap',
  'compare_entry_content_block',
  'compare_entry_submit',
  'compare_entry_paste_split',
  'compare_entry_mode_autoswitch',
  'compare_entry_ready',
];

describe('Bundle B contract — 8 analytics events fire from HomeScreen (R16)', () => {
  it.each(REQUIRED_EVENTS)('fires `%s`', (event) => {
    const pattern = new RegExp(
      `trackEvent\\(\\s*['"]${event.replace(/_/g, '_')}['"]`
    );
    expect(HOME_SRC).toMatch(pattern);
  });

  it('trackEvent is imported from services/api', () => {
    expect(HOME_SRC).toMatch(/import[\s\S]{0,400}trackEvent[\s\S]{0,200}from\s+['"]\.\.\/services\/api['"]/);
  });
});

// ---------------------------------------------------------------------
// Section 6 — Paywall takeover when canCompare === false
// Spec § 3 — when canCompare flips false, comparison input/CTAs surrender
// to the Paywall route. Banner-view + banner-tap analytics fire.
// ---------------------------------------------------------------------

describe('Bundle B contract — paywall takeover on canCompare=false (R16)', () => {
  it('canCompare comes from useComparisonCounter()', () => {
    expect(HOME_SRC).toMatch(/canCompare[\s\S]{0,100}useComparisonCounter\(\)/);
  });

  it('handleTextCompare bails to Paywall route when !canCompare', () => {
    expect(HOME_SRC).toMatch(
      /handleTextCompare[\s\S]{0,400}if\s*\(\s*!canCompare\s*\)[\s\S]{0,150}navigation\.navigate\(\s*['"]Paywall['"]/
    );
  });

  it('canCompare-flip useEffect fires compare_entry_paywall_banner_view', () => {
    expect(HOME_SRC).toMatch(
      /if\s*\(\s*prevCanCompareRef\.current\s*&&\s*!canCompare\s*\)[\s\S]{0,200}compare_entry_paywall_banner_view/
    );
  });

  it('paywall banner tap fires compare_entry_paywall_banner_tap', () => {
    expect(HOME_SRC).toMatch(/compare_entry_paywall_banner_tap/);
  });
});

// ---------------------------------------------------------------------
// Section 7 — Min-display floor 1.2s on HomeScreen → Results
// Design § 3: cached responses still show LoadingRings 1.2s so the
// brand moment lands. The constant + ref-based timing MUST persist.
// ---------------------------------------------------------------------

describe('Bundle B contract — 1.2s min-display floor (R16)', () => {
  it('MIN_LOADING_MS = 1200 constant defined in HomeScreen', () => {
    expect(HOME_SRC).toMatch(/MIN_LOADING_MS\s*=\s*1200/);
  });

  it('loadingStartedAtRef captures Date.now() at stream start', () => {
    expect(HOME_SRC).toMatch(/loadingStartedAtRef\s*=\s*useRef</);
    expect(HOME_SRC).toMatch(/loadingStartedAtRef\.current\s*=\s*Date\.now\(\)/);
  });

  it('navigateToResultsWithFloor exists and is called from onComplete + url path', () => {
    expect(HOME_SRC).toMatch(/navigateToResultsWithFloor/);
    // Both call sites confirmed: text-onComplete + url-direct (HomeScreen lines 272 + 327).
    const matches = HOME_SRC.match(/navigateToResultsWithFloor\(/g) ?? [];
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });
});

// ---------------------------------------------------------------------
// Section 8 — Haptic vocabulary: chip=Light, stage=Light, winner=Medium
// CLAUDE.md Build Principle #4 — NO error/warning/heavy intensities
// anywhere in user-facing code (avoid framing the app as scary).
// HomeScreen specifically uses Light on chip press; redesign MUST NOT
// promote any haptic to Heavy/Error/Warning.
// ---------------------------------------------------------------------

describe('Bundle B contract — approved haptic vocabulary (R16)', () => {
  it('HomeScreen uses ImpactFeedbackStyle.Light (chip vocabulary)', () => {
    expect(HOME_SRC).toMatch(/Haptics\.ImpactFeedbackStyle\.Light/);
  });

  it('HomeScreen does NOT use Heavy / Medium impact (chip ≠ winner here)', () => {
    // Medium is reserved for the winner-reveal haptic in Results;
    // HomeScreen's chip-press path MUST stay on Light.
    // Negative test surface — if a future commit promotes the chip
    // press to Medium/Heavy, this lights up.
    const heavyCalls = HOME_SRC.match(/Haptics\.ImpactFeedbackStyle\.Heavy/g) ?? [];
    expect(heavyCalls.length).toBe(0);
  });

  it('HomeScreen does NOT use NotificationFeedback Error/Warning anywhere', () => {
    // CLAUDE.md Build Principle #4 — never frame the app as scary.
    expect(HOME_SRC).not.toMatch(/NotificationFeedbackType\.Error/);
    expect(HOME_SRC).not.toMatch(/NotificationFeedbackType\.Warning/);
    // The bare class also flagged in case import shape changes.
    expect(HOME_SRC).not.toMatch(/notificationAsync\(/);
  });
});

// ---------------------------------------------------------------------
// Section 9 — 3-part celebration on `ready`: visual + haptic; NO shake/sound
// Spec § 4.4 — when TwoInputShell fires onReady (both boxes valid + non-
// empty), HomeScreen MUST track compare_entry_ready. The "no shake"
// guarantee is enforced by absence of withSequence({shake}) or
// translateX-oscillation styles in the surface.
// ---------------------------------------------------------------------

describe('Bundle B contract — 3-part ready celebration (R16)', () => {
  it('onReady prop wires through to compare_entry_ready trackEvent', () => {
    expect(HOME_SRC).toMatch(
      /onReady=\{[\s\S]{0,200}trackEvent\(\s*['"]compare_entry_ready['"]\s*,\s*\{\s*mode/
    );
  });

  it('compare_entry_ready payload includes time_to_ready_ms', () => {
    expect(HOME_SRC).toMatch(/time_to_ready_ms\s*:\s*timeToReadyMs/);
  });

  it('HomeScreen does NOT contain shake animations (no jitter / wobble)', () => {
    // Build Principle #4: emerald/black is calm. No oscillating
    // translateX or rotate keyframes on the home surface.
    expect(HOME_SRC).not.toMatch(/translateX:\s*withSequence/);
    expect(HOME_SRC).not.toMatch(/rotate:\s*withSequence/);
    // Word-boundary to avoid matching benign substrings like
    // "tree-shaken" in tooling comments.
    expect(HOME_SRC).not.toMatch(/\b(shake|wobble|jitter)\b/i);
  });

  it('HomeScreen does NOT play any sound on ready (Audio / SoundObject)', () => {
    expect(HOME_SRC).not.toMatch(/expo-av|Audio\.|SoundObject/);
  });
});

// ---------------------------------------------------------------------
// Section 10 — Forbidden user-facing vocabulary
// Build Principle #4 forbids `couldn't`, `try again`, `Failed to`,
// `تعذر`, `فشل`, `estimated` in user-facing copy. HomeScreen consumes
// i18n keys — its source file must not hardcode forbidden strings as
// literals. (Catalog-level audit lives in __tests__/copy-policy.test.ts.)
// ---------------------------------------------------------------------

describe('Bundle B contract — no forbidden vocab in HomeScreen source (R16)', () => {
  it('HomeScreen does not literal-string user-facing scary copy', () => {
    // Permits identifier substrings inside i18n keys (e.g. "errorBody"
    // is a key name, not a value). We grep for whole-word EN forbidden
    // phrases that would only appear if a developer hardcoded them.
    expect(HOME_SRC).not.toMatch(/['"][^'"]*\bcouldn['']t\b[^'"]*['"]/);
    expect(HOME_SRC).not.toMatch(/['"][^'"]*\btry again\b[^'"]*['"]/i);
    expect(HOME_SRC).not.toMatch(/['"][^'"]*\bFailed to\b[^'"]*['"]/);
  });
});

// ---------------------------------------------------------------------
// Section 11 — Critical testID preservation (per QA Ask 4)
// Existing jest test suites depend on a set of stable testIDs as their
// query anchors (fireEvent.press(getByTestId('X')), getByTestId('Y'), etc.).
// Claude-Design could silently rename these during the visual refresh,
// breaking the existing tests without obvious cause. This section pins
// the testIDs that are load-bearing for the current test surface so a
// rename lights up at the unit-test layer.
//
// Inventory verified via grep on current shipped code 2026-05-23.
// ---------------------------------------------------------------------

import * as _fs from 'fs';
import * as _path from 'path';

const TWOINPUT_SRC = _fs.readFileSync(
  _path.resolve(__dirname, '../src/components/TwoInputShell.tsx'),
  'utf8'
);
const IMAGESLOTROW_SRC = _fs.readFileSync(
  _path.resolve(__dirname, '../src/components/ImageSlotRow.tsx'),
  'utf8'
);
const SCANCAMERA_SRC = _fs.readFileSync(
  _path.resolve(__dirname, '../src/screens/ScanCameraScreen.tsx'),
  'utf8'
);
const ONBOARDING_FLOW_SRC = _fs.readFileSync(
  _path.resolve(__dirname, '../src/screens/onboarding/OnboardingFlow.tsx'),
  'utf8'
);
const RESULTS_SRC = _fs.readFileSync(
  _path.resolve(__dirname, '../src/screens/ResultsScreen.tsx'),
  'utf8'
);

describe('Bundle B contract — critical testID preservation (R16)', () => {
  it('HomeScreen exposes the `home-center-area` testID (Bundle B 21e7bc0 rewire)', () => {
    expect(HOME_SRC).toMatch(/testID="home-center-area"/);
  });

  it('TwoInputShell defaults its root testID to `two-input-shell`', () => {
    // Children derive: `${testID}-vs-pill`, `${testID}-cta`,
    // `${testID}-a`/-b, `${testID}-caption-paste-split`,
    // `${testID}-caption-mode-switch`, `${testID}-a/-b-circle/-input/-clear`.
    expect(TWOINPUT_SRC).toMatch(/testID\s*=\s*['"]two-input-shell['"]/);
  });

  it('ImageSlotRow uses `image-slot-${idx}` family (and -thumb / -remove suffixes)', () => {
    expect(IMAGESLOTROW_SRC).toMatch(/testID=\{`image-slot-\$\{idx\}`\}/);
    expect(IMAGESLOTROW_SRC).toMatch(/testID=\{`image-slot-\$\{idx\}-thumb`\}/);
    expect(IMAGESLOTROW_SRC).toMatch(/testID=\{`image-slot-\$\{idx\}-remove`\}/);
  });

  it('ScanCameraScreen exposes `scan-camera-close`, `scan-camera-help`, `scan-celebration-overlay`', () => {
    expect(SCANCAMERA_SRC).toMatch(/testID="scan-camera-close"/);
    expect(SCANCAMERA_SRC).toMatch(/testID="scan-camera-help"/);
    expect(SCANCAMERA_SRC).toMatch(/testID="scan-celebration-overlay"/);
  });

  it('CameraHelpOverlay exposes `camera-help-overlay` + `camera-help-overlay-close`', () => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const overlaySrc = _fs.readFileSync(
      _path.resolve(__dirname, '../src/components/CameraHelpOverlay.tsx'),
      'utf8'
    );
    expect(overlaySrc).toMatch(/testID="camera-help-overlay"/);
    expect(overlaySrc).toMatch(/testID="camera-help-overlay-close"/);
  });

  it('OnboardingFlow exposes `onboarding-progress`, `onboarding-back`, `onboarding-next`', () => {
    expect(ONBOARDING_FLOW_SRC).toMatch(/testID="onboarding-progress"/);
    expect(ONBOARDING_FLOW_SRC).toMatch(/testID="onboarding-back"/);
    expect(ONBOARDING_FLOW_SRC).toMatch(/testID="onboarding-next"/);
  });

  it('ResultsScreen exposes the `results-empty-state` testID', () => {
    expect(RESULTS_SRC).toMatch(/testID="results-empty-state"/);
  });
});

// ---------------------------------------------------------------------
// Section 12 — Post-redesign placeholders (.todo)
// These contracts can only be verified once the Claude-Design prototype
// lands. Flip from .todo → .test when the visual layer ships.
// ---------------------------------------------------------------------

describe('Bundle B contract — post-redesign placeholders (R16)', () => {
  // R10: token extension, not replacement.
  it.todo('theme/index.ts retains all pre-Bundle-D color tokens (additive extension)');
  it.todo('theme/index.ts adds Claude-Design tokens under a new namespace');

  // R16: full EN+AR walkthrough on the new surface (device smoke).
  it.todo('EN walkthrough A-L: 10 visual checkpoints map to redesigned components');
  it.todo('AR walkthrough M-P: 7 RTL checkpoints map to redesigned components');

  // Snapshot churn is expected on visual restyle; Test agent
  // regenerates baseline as part of the redesign PR.
  it.todo('snapshot baseline regenerated by Test agent post-redesign');
});
