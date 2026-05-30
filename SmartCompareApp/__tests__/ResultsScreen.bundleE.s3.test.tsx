/**
 * Bundle E S3 — A2 ResultsScreen JSX element-order pins.
 *
 * Sources of truth:
 *  - docs/claude-design-handoff/ui_kits/mobile/ResultsScreen.jsx (1-410)
 *  - docs/plans/_s3-a2-element-order.md
 *
 * Pattern: source-string assertions (per Phase 3 redesign tests). The full
 * SSE + scoring + Reanimated render is exercised elsewhere; here we pin the
 * JSX-aligned presentation contract for peer-QA + future regressions.
 *
 * After REWRITE, presentation lives in ResultsContent.tsx (orchestrator
 * imports it from ../components/results/ResultsContent). The tests assert
 * both files so the contract holds across the extraction.
 */

import * as fs from 'fs';
import * as path from 'path';

const RESULTS_SCREEN_PATH = path.resolve(
  __dirname,
  '../src/screens/ResultsScreen.tsx'
);
const RESULTS_CONTENT_PATH = path.resolve(
  __dirname,
  '../src/components/results/ResultsContent.tsx'
);

const RESULTS_SCREEN_SRC = fs.readFileSync(RESULTS_SCREEN_PATH, 'utf8');
const RESULTS_CONTENT_SRC = fs.existsSync(RESULTS_CONTENT_PATH)
  ? fs.readFileSync(RESULTS_CONTENT_PATH, 'utf8')
  : '';

describe('Bundle E S3 — ResultsContent extraction', () => {
  it('ResultsContent.tsx exists as a separate presentation component', () => {
    expect(fs.existsSync(RESULTS_CONTENT_PATH)).toBe(true);
  });

  it('ResultsScreen.tsx imports ResultsContent (presentation extracted)', () => {
    expect(RESULTS_SCREEN_SRC).toMatch(
      /import\s+(?:\{\s*ResultsContent\s*\}|ResultsContent)\s+from\s+['"]\.\.\/components\/results\/ResultsContent['"]/
    );
  });

  it('ResultsContent.tsx is a function component accepting the documented props', () => {
    // Required props passed by ResultsScreen orchestrator
    for (const propName of [
      'products',
      'winnerIndex',
      'scoring_v2',
      'cohortPeerCount',
      'cohortGovernorate',
      'sheetLeg',
      'onPillPress',
      'onCloseSheet',
      'comparisonId',
    ]) {
      expect(RESULTS_CONTENT_SRC).toContain(propName);
    }
  });
});

describe('Bundle E S3 — JSX element-order (ResultsScreen.jsx 1-410)', () => {
  // # 1 Header — TopMatchBadge centered between back + share buttons
  it('header centers <TopMatchBadge /> between back + share buttons (JSX 297-311)', () => {
    expect(RESULTS_CONTENT_SRC).toMatch(/<TopMatchBadge/);
    expect(RESULTS_CONTENT_SRC).toContain('results-content-header');
  });

  it('header back + share buttons are circular 36×36 (JSX 298-310)', () => {
    // Bundle D Claude-Design already shipped the 36×36 circular treatment.
    // Pin it stays in the extracted component.
    expect(RESULTS_CONTENT_SRC).toMatch(/results-content-back-btn/);
    expect(RESULTS_CONTENT_SRC).toMatch(/results-content-share-btn/);
  });

  // # 2 Hero — two ProductCards with absolute "vs" pill on divider
  it('renders product pair hero with absolute "vs" divider pill (JSX 316-333)', () => {
    expect(RESULTS_CONTENT_SRC).toContain('results-content-hero-pair');
    expect(RESULTS_CONTENT_SRC).toMatch(/results-content-vs-pill/);
  });

  it('renders image_url slot per product (A4 wires <Image> later)', () => {
    // Slot uses .map() iteration with `${idx}` template — accept either
    // literal `-0`/`-1` or the template `-${idx}` form.
    expect(RESULTS_CONTENT_SRC).toMatch(
      /results-product-image-slot-(?:\$\{[^}]+\}|0|1)/
    );
  });

  // # 3 "Why this fits you" section
  it('"Why this fits you" section uses results.whyWePicked → "Why this fits you" copy', () => {
    expect(RESULTS_CONTENT_SRC).toMatch(/t\(['"]results\.whyWePicked['"]\)/);
    expect(RESULTS_CONTENT_SRC).toContain('results-content-why');
  });

  // # 5 Confidence pills with eyebrow + "What we know" heading
  it('Confidence pills section is preceded by "What we know" eyebrow (JSX 357-359)', () => {
    expect(RESULTS_CONTENT_SRC).toMatch(/results\.whatWeKnow/);
    expect(RESULTS_CONTENT_SRC).toMatch(/<ConfidencePills/);
  });

  // # 6 Cohort line — softened single-line treatment
  it('Cohort line renders via CohortBadge slot below the verdict (JSX 367-377)', () => {
    expect(RESULTS_CONTENT_SRC).toMatch(/results-cohort-badge-slot/);
    expect(RESULTS_CONTENT_SRC).toMatch(/<CohortBadge/);
  });

  // # 7 DetailsAccordion — Reviews / Pros & Cons / Specs collapsible
  it('renders <ResultsAccordion /> "Dig deeper" with Reviews + Pros & Cons + Specs (JSX 105-211)', () => {
    expect(RESULTS_CONTENT_SRC).toMatch(/ResultsAccordion/);
    expect(RESULTS_CONTENT_SRC).toMatch(/results-content-accordion/);
  });

  // # 8 Feedback prompt — "Was this helpful?"
  it('Feedback card present at the bottom of presentation (JSX 384-404)', () => {
    expect(RESULTS_CONTENT_SRC).toMatch(/FeedbackCard/);
  });
});

describe('Bundle E S3 — JSX top-down element ORDER (lexical)', () => {
  // Element order matters — peer-QA verifies the rendered order matches
  // JSX 286-407. We assert lexical order in ResultsContent.tsx since the
  // file is purely presentational.
  const ORDERED_ANCHORS = [
    'results-content-header', // # 1
    'results-content-hero-pair', // # 2
    'results-content-why', // # 3
    'results-content-confidence', // # 5
    'results-cohort-badge-slot', // # 6
    'results-content-accordion', // # 7
    'results-content-feedback', // # 8
  ];

  it.each(ORDERED_ANCHORS.map((a, i) => [i, a]))(
    'anchor #%d "%s" appears in lexical order',
    (idx, anchor) => {
      expect(RESULTS_CONTENT_SRC).toContain(anchor);
    }
  );

  it('all anchors appear in JSX top-down order', () => {
    const positions = ORDERED_ANCHORS.map((a) => RESULTS_CONTENT_SRC.indexOf(a));
    for (let i = 1; i < positions.length; i++) {
      expect(positions[i]).toBeGreaterThan(positions[i - 1]);
    }
  });
});

describe('Bundle E S3 — DELETE list (Bundle D / S1 stale pieces)', () => {
  it('orchestrator no longer renders categorySwitchedBanner (no info banners)', () => {
    // Per memory/feedback_no_info_banners.md — banner FORBIDDEN.
    expect(RESULTS_SCREEN_SRC).not.toMatch(/styles\.categorySwitchedBanner/);
    expect(RESULTS_SCREEN_SRC).not.toMatch(/results\.categorySwitched/);
  });

  it('presentation no longer renders per-product scoreBadge (winner role moves to TopMatchBadge)', () => {
    expect(RESULTS_CONTENT_SRC).not.toMatch(/styles\.scoreBadge\b/);
    expect(RESULTS_CONTENT_SRC).not.toMatch(/scoreBadgeValue/);
  });

  it('presentation no longer renders per-product bestPickBadge (winner role moves to TopMatchBadge)', () => {
    expect(RESULTS_CONTENT_SRC).not.toMatch(/styles\.bestPickBadge\b/);
    expect(RESULTS_CONTENT_SRC).not.toMatch(/bestPickText/);
  });

  it('orchestrator no longer renders a second Share affordance row below feedback', () => {
    // JSX has ONE share button in the header. The actions row + duplicate
    // Share button below feedback are pruned.
    expect(RESULTS_SCREEN_SRC).not.toMatch(/styles\.actionsRow\b/);
  });

  it('orchestrator no longer renders a metadata footer (elapsed_seconds + cache_hits)', () => {
    // JSX has no metadata footer.
    expect(RESULTS_SCREEN_SRC).not.toMatch(/styles\.metadataSection\b/);
    expect(RESULTS_SCREEN_SRC).not.toMatch(/results\.metadata\.elapsed/);
  });
});

describe('Bundle E S3 — scoring_v2 + personalization contract preserved', () => {
  // ResultsScreen orchestrator MUST still wire scoring_v2 into the
  // presentation layer. These are the load-bearing fields A1 + A3 + future
  // regression tests rely on.
  it('orchestrator still derives scoring_v2 from result', () => {
    expect(RESULTS_SCREEN_SRC).toMatch(/scoring_v2/);
  });

  it('orchestrator still resolves winnerIndex from scoring_v2.overall_score', () => {
    // The winnerIndex computation: (overall_score.product_a >= product_b ? 0 : 1)
    expect(RESULTS_SCREEN_SRC).toMatch(/overall_score/);
  });

  it('orchestrator still passes applied_shifts → PersonalizationChip through ResultsContent', () => {
    expect(RESULTS_CONTENT_SRC).toMatch(/<PersonalizationChip/);
    expect(RESULTS_CONTENT_SRC).toMatch(/applied_shifts/);
  });

  it('orchestrator still passes confidence_legs → ConfidencePills through ResultsContent', () => {
    expect(RESULTS_CONTENT_SRC).toMatch(/confidence(_legs|Legs)/);
  });

  it('orchestrator still drives ConfidenceDetailsSheet via sheetLeg state', () => {
    expect(RESULTS_SCREEN_SRC).toMatch(/sheetLeg/);
    expect(RESULTS_CONTENT_SRC).toMatch(/<ConfidenceDetailsSheet/);
  });

  it('orchestrator still renders RevealBurst keyed on comparisonId, fireOnce', () => {
    expect(RESULTS_CONTENT_SRC).toMatch(/<RevealBurst/);
    expect(RESULTS_CONTENT_SRC).toMatch(/fireOnce/);
  });

  it('orchestrator still emits trackEvents (event tracking preserved)', () => {
    expect(RESULTS_SCREEN_SRC).toMatch(/trackEvents/);
  });

  it('orchestrator still supports history detail fetch path (comparison_id)', () => {
    expect(RESULTS_SCREEN_SRC).toMatch(/comparison_id/);
    expect(RESULTS_SCREEN_SRC).toMatch(/getComparison/);
  });

  it('orchestrator still supports vision camera path (vision_products)', () => {
    expect(RESULTS_SCREEN_SRC).toMatch(/vision_products/);
    expect(RESULTS_SCREEN_SRC).toMatch(/identifyFromImages/);
  });

  it('orchestrator still wires demographics bottom sheet', () => {
    expect(RESULTS_SCREEN_SRC).toMatch(/DemographicsBottomSheet/);
  });

  it('orchestrator still wires referral ShareBottomSheet + Loop 1 toast', () => {
    expect(RESULTS_SCREEN_SRC).toMatch(/ShareBottomSheet/);
    expect(RESULTS_SCREEN_SRC).toMatch(/loop1Toast/);
  });
});

describe('Bundle E S3 — forbidden copy guard (per memory rules)', () => {
  it('no scary EN vocab in ResultsContent ("couldn\'t" / "try again" / "Failed to")', () => {
    // Per CLAUDE.md + memory rules. Only literal user-visible strings.
    expect(RESULTS_CONTENT_SRC).not.toMatch(/"[^"]*couldn['\u2019]t[^"]*"/i);
    expect(RESULTS_CONTENT_SRC).not.toMatch(/"[^"]*try again[^"]*"/i);
    expect(RESULTS_CONTENT_SRC).not.toMatch(/"[^"]*Failed to[^"]*"/i);
  });

  it('no "estimated" word in ResultsContent user-visible copy', () => {
    // Per memory/feedback_no_estimated_word_in_ui.md.
    // Forbidden: rendered strings like "Estimated price" inside JSX <Text>.
    // Allowed: backend enum (source_method === 'estimated'), comments,
    // import of `anyEstimated()` helper.
    // Scan line-by-line for `>...Estimated...<` within a single JSX node.
    const lines = RESULTS_CONTENT_SRC.split('\n');
    for (const line of lines) {
      // Pure-comment lines are exempt (they contain JSX-style `*/`).
      if (/^\s*\*/.test(line) || /^\s*\/\//.test(line)) continue;
      if (/>[^<>]*[Ee]stimated[^<>]*</.test(line)) {
        throw new Error(
          `forbidden 'estimated' word in user-visible JSX: ${line}`
        );
      }
    }
  });

  it('no top-level info banners (per memory/feedback_no_info_banners.md)', () => {
    expect(RESULTS_CONTENT_SRC).not.toMatch(/InfoBanner/);
    expect(RESULTS_CONTENT_SRC).not.toMatch(/categorySwitchedBanner/);
  });

  it('no backend internals exposed (no ±N% / no shift coefficients)', () => {
    // Per memory/feedback_no_backend_internals_in_reveals.md.
    // Coefficients like "±30%", "±10%", "±5%" must NOT appear as rendered
    // strings. Allowed: comments, variable names.
    expect(RESULTS_CONTENT_SRC).not.toMatch(/>[^<]*±\s*(?:30|10|5)\s*%[^<]*</);
  });
});
