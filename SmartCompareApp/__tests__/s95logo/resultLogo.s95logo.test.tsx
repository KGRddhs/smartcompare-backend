/**
 * S95-LOGO RESULT-LOGO-OVERLAY - the result page draws no MYEZ logo.
 *
 * Spec: S95_LOGO_UNIT_SPEC.md (session 95) section 5, rows L1-L5.
 * Evidence: the owner, 2026-11-13: a large MYEZ logo is drawn over the
 * result page while scrolling. ResultsContent mounts the winner-reveal
 * celebration RevealBurst in an absolute-fill slot over the score bars; its
 * badge (a QarenLogo) only springs its scale to 1 and never fades, and the
 * slot is never unmounted, so the mark stays over the bars for the life of
 * the screen.
 *
 * RED at base: L1, L4, L5. PIN (green at base and after): L2, L3.
 *
 * Binding conventions:
 * - L1-L3 render the REAL ResultsContent with the REAL RevealBurst: its path
 *   is NOT mocked in this file. Every other mock and the props are those of
 *   __tests__/components/ResultsContent.render.test.tsx, with synthetic
 *   product names. react-native, react-native-reanimated and
 *   react-native-svg resolve to the project mocks named in jest.config.js.
 * - L4 / L5 read the TypeScript AST with the installed `typescript`, as
 *   __tests__/brand/inAppMark.u4c.test.ts does; every source is read INSIDE
 *   its own `it`.
 * - "The result page" = src/screens/ResultsScreen.tsx and every .tsx under
 *   src/components/results/ (spec section 2). The loading view's LoadingRings
 *   mark is not the result page and is not scanned.
 *
 * No snapshot, no timer, no network, no personal value.
 */
import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';
import { render } from '@testing-library/react-native';

// Local Reanimated mock (copied from ResultsContent.render.test.tsx): extends
// the project mock with the FadeIn / FadeInDown entering animations consumed
// by ResultsContent.
jest.mock('react-native-reanimated', () => {
  const real = jest.requireActual('react-native-reanimated');
  const entering = {
    duration: () => entering,
    delay: () => entering,
  };
  return {
    __esModule: true,
    ...real,
    default: real.default ?? real,
    FadeIn: entering,
    FadeInDown: entering,
  };
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      let str = (opts?.defaultValue as string) ?? key;
      if (opts) {
        for (const [k, v] of Object.entries(opts)) {
          if (k === 'defaultValue') continue;
          str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
        }
      }
      return str;
    },
  }),
}));

// Heavy children render placeholders (copied from
// ResultsContent.render.test.tsx). That file's RevealBurst mock is
// deliberately NOT copied: these rows render the real celebration.
jest.mock('../../src/components/results/TopMatchBadge', () => ({
  TopMatchBadge: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-top-match-badge'} />;
  },
}));
jest.mock('../../src/components/results/DimensionBars', () => ({
  DimensionBars: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-dim-bars'} />;
  },
}));
jest.mock('../../src/components/results/FactualVerdict', () => ({
  FactualVerdict: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-factual-verdict'} />;
  },
}));
jest.mock('../../src/components/results/ConfidencePills', () => ({
  ConfidencePills: ({ testID, onPillPress }: any) => {
    const { View, TouchableOpacity } = require('react-native');
    return (
      <View testID={testID ?? 'mock-confidence-pills'}>
        <TouchableOpacity
          testID="mock-pill-price"
          onPress={() => onPillPress?.('price')}
        />
      </View>
    );
  },
}));
jest.mock('../../src/components/results/ConfidenceDetailsSheet', () => ({
  ConfidenceDetailsSheet: ({ testID, onClose }: any) => {
    const { View, TouchableOpacity } = require('react-native');
    return (
      <View testID={testID ?? 'mock-confidence-sheet'}>
        <TouchableOpacity testID="mock-sheet-close" onPress={onClose} />
      </View>
    );
  },
}));
jest.mock('../../src/components/results/PersonalizationChip', () => ({
  PersonalizationChip: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-personalization-chip'} />;
  },
}));
jest.mock('../../src/components/FeedbackCard', () => ({
  __esModule: true,
  default: ({ submitted, onSubmitted }: any) => {
    const { View, TouchableOpacity } = require('react-native');
    return (
      <View testID="mock-feedback-card">
        <TouchableOpacity testID="mock-feedback-submit" onPress={onSubmitted} />
        {submitted ? <View testID="mock-feedback-thanks" /> : null}
      </View>
    );
  },
}));
jest.mock('../../src/components/results/ResultsAccordion', () => ({
  ResultsAccordion: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-accordion'} />;
  },
}));
jest.mock('../../src/services/sourceMethod', () => ({
  anyEstimated: jest.fn(() => false),
  isConvertedUsd: jest.fn((p: any) => p?.source_method === 'converted_usd'),
}));

import { ResultsContent } from '../../src/components/results/ResultsContent';
import QarenLogo from '../../src/components/QarenLogo';

const APP = path.resolve(__dirname, '..', '..');
const SRC = path.join(APP, 'src');
const RESULTS_SCREEN = path.join(SRC, 'screens', 'ResultsScreen.tsx');
const RESULTS_DIR = path.join(SRC, 'components', 'results');
const RESULTS_CONTENT = path.join(RESULTS_DIR, 'ResultsContent.tsx');

// Synthetic products (no real product, brand or store name).
const mockProducts: any = [
  {
    name: 'Sample Scent Alpha',
    brand: 'Brand Alpha',
    price: { amount: 29, currency: 'BHD', retailer: 'Store One' },
    pros: ['Longer lasting'],
    cons: ['Higher price'],
  },
  {
    name: 'Sample Scent Beta',
    brand: 'Brand Beta',
    price: { amount: 25, currency: 'BHD', retailer: 'Store One' },
    pros: ['Fresher opening', 'Better value'],
    cons: ['Lighter projection'],
  },
];

const mockResult: any = {
  overview: {
    winner: {
      product_index: 1,
      name: 'Sample Scent Beta',
      reason: 'Tuned to your priorities - value and freshness win',
      key_tradeoff: 'Value and freshness edge out Alpha',
    },
    products: mockProducts,
  },
  comparison: {},
  recommendation: 'Sample Scent Beta wins on value and freshness',
  metadata: { query: 'sample-scent-alpha-vs-sample-scent-beta', elapsed_seconds: 14 },
};

// Normal mode with three dimensions: the branch that mounts the slot at base.
const mockScoringV2: any = {
  overall_score: { product_a: 72, product_b: 81 },
  dimensions: [
    { dim: 'longevity', winner_index: 0, leftPct: 58, rightPct: 42 },
    { dim: 'freshness', winner_index: 1, leftPct: 30, rightPct: 70 },
    { dim: 'price', winner_index: 1, leftPct: 44, rightPct: 56 },
  ],
  confidence_legs: { price: 'high', reviews: 'medium', specs: 'high' },
  factual_verdict: {
    line1: 'Sample Scent Beta takes 2 of 3 dimensions',
    line2: 'Freshness and price hold the most weight in your priorities',
  },
  personalization: { applied_shifts: [] },
  comparison_quality: 'normal',
  confidence_details: {},
};

// The props of ResultsContent.render.test.tsx (winnerRevealed: true).
const baseProps: any = {
  result: mockResult,
  products: mockProducts,
  winnerIndex: 1 as 0 | 1,
  scoring_v2: mockScoringV2,
  comparisonId: 'cmp-s95-logo',
  cohortPeerCount: 2400,
  cohortGovernorate: 'Capital',
  isRTL: false,
  feedbackSubmitted: false,
  onFeedbackSubmitted: jest.fn(),
  feedbackComparisonId: 'cmp-s95-logo',
  sheetLeg: null,
  onPillPress: jest.fn(),
  onCloseSheet: jest.fn(),
  winnerRevealed: true,
  winnerScaleAnimStyle: { transform: [{ scale: 1 }] },
  onBack: jest.fn(),
  onShare: jest.fn(),
};

const relApp = (file: string): string => path.relative(APP, file).split(path.sep).join('/');

/** Every .tsx file under `dir`, at any depth, sorted. */
function listTsx(dir: string, out: string[] = []): string[] {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) listTsx(p, out);
    else if (/\.tsx$/.test(e.name)) out.push(p);
  }
  return out.sort();
}

function parse(file: string): ts.SourceFile {
  return ts.createSourceFile(
    file,
    fs.readFileSync(file, 'utf8'),
    ts.ScriptTarget.Latest,
    true,
    file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  );
}

function walk(node: ts.Node, fn: (n: ts.Node) => void): void {
  fn(node);
  ts.forEachChild(node, (c) => walk(c, fn));
}

const lineOf = (sf: ts.SourceFile, n: ts.Node): number =>
  sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;

/** A module specifier that ends with hero/RevealBurst or /QarenLogo (an extension allowed). */
const BANNED_SPECIFIER = /(hero\/RevealBurst|\/QarenLogo)(\.tsx?)?$/;
/** A JSX tag named RevealBurst or QarenLogo (also as the last member of a dotted tag). */
const BANNED_TAG = /(^|\.)(RevealBurst|QarenLogo)$/;

/**
 * The result-page offences of one file: every import / export-from /
 * import = require / require() / import() whose module specifier is banned,
 * and every JSX element whose tag is banned. Each entry names the file, the
 * line and the import or the element.
 */
function logoOffences(file: string): string[] {
  const sf = parse(file);
  const where = relApp(file);
  const out: string[] = [];
  walk(sf, (n) => {
    let spec: string | undefined;
    if (
      (ts.isImportDeclaration(n) || ts.isExportDeclaration(n)) &&
      n.moduleSpecifier &&
      ts.isStringLiteral(n.moduleSpecifier)
    ) {
      spec = n.moduleSpecifier.text;
    } else if (
      ts.isImportEqualsDeclaration(n) &&
      ts.isExternalModuleReference(n.moduleReference) &&
      ts.isStringLiteral(n.moduleReference.expression)
    ) {
      spec = n.moduleReference.expression.text;
    } else if (ts.isCallExpression(n) && n.arguments[0] && ts.isStringLiteralLike(n.arguments[0])) {
      const callee = n.expression;
      if ((ts.isIdentifier(callee) && callee.text === 'require') || callee.kind === ts.SyntaxKind.ImportKeyword) {
        spec = n.arguments[0].text;
      }
    }
    if (spec !== undefined && BANNED_SPECIFIER.test(spec)) {
      out.push(`${where}:${lineOf(sf, n)} imports '${spec}'`);
    }
    let tag: string | undefined;
    if (ts.isJsxSelfClosingElement(n)) tag = n.tagName.getText(sf);
    else if (ts.isJsxOpeningElement(n)) tag = n.tagName.getText(sf);
    if (tag !== undefined && BANNED_TAG.test(tag)) {
      out.push(`${where}:${lineOf(sf, n)} renders <${tag}>`);
    }
  });
  return out;
}

const propertyNameText = (name: ts.PropertyName, sf: ts.SourceFile): string =>
  ts.isIdentifier(name) || ts.isStringLiteral(name) || ts.isNumericLiteral(name)
    ? name.text
    : name.getText(sf);

describe('S95-LOGO the result page draws no MYEZ logo', () => {
  it('L1 a revealed winner in normal mode with 3 dimensions and the real RevealBurst renders no reveal-burst slot, no reveal-burst badge and no QarenLogo', () => {
    const r = render(<ResultsContent {...baseProps} />);
    expect({
      'results-v2-reveal-burst-slot rendered': r.queryByTestId('results-v2-reveal-burst-slot') !== null,
      'reveal-burst-badge rendered': r.queryByTestId('reveal-burst-badge') !== null,
      'QarenLogo instances': r.UNSAFE_queryAllByType(QarenLogo).length,
    }).toEqual({
      'results-v2-reveal-burst-slot rendered': false,
      'reveal-burst-badge rendered': false,
      'QarenLogo instances': 0,
    });
  });

  it('L2 the same render still shows the dimension-bars section and the bars (PIN)', () => {
    const { getByTestId } = render(<ResultsContent {...baseProps} />);
    expect(getByTestId('results-v2-bars')).toBeTruthy();
    expect(getByTestId('results-scoring-v2')).toBeTruthy();
  });

  it('L3 winnerRevealed=false, and weird mode with winnerRevealed=true, render no reveal-burst badge and no QarenLogo while the bars render (PIN)', () => {
    const cases: [string, Record<string, unknown>][] = [
      ['winnerRevealed=false', { winnerRevealed: false }],
      [
        "comparison_quality='weird' and winnerRevealed=true",
        { winnerRevealed: true, scoring_v2: { ...mockScoringV2, comparison_quality: 'weird' } },
      ],
    ];
    const seen = cases.map(([where, extra]) => {
      const r = render(<ResultsContent {...baseProps} {...extra} />);
      const row = {
        where,
        'reveal-burst-badge rendered': r.queryByTestId('reveal-burst-badge') !== null,
        'QarenLogo instances': r.UNSAFE_queryAllByType(QarenLogo).length,
        'results-v2-bars rendered': r.queryByTestId('results-v2-bars') !== null,
      };
      r.unmount();
      return row;
    });
    expect(seen).toEqual(
      cases.map(([where]) => ({
        where,
        'reveal-burst-badge rendered': false,
        'QarenLogo instances': 0,
        'results-v2-bars rendered': true,
      }))
    );
  });

  it('L4 no result-page source imports hero/RevealBurst or QarenLogo, or renders <RevealBurst> or <QarenLogo> (TypeScript AST)', () => {
    const files = [RESULTS_SCREEN, ...listTsx(RESULTS_DIR)];
    // Non-vacuity: the scan covers the orchestrator and the presentation layer.
    expect(files.map(relApp)).toEqual(
      expect.arrayContaining(['src/screens/ResultsScreen.tsx', 'src/components/results/ResultsContent.tsx'])
    );
    const offences = files.flatMap((file) => logoOffences(file));
    expect(offences).toEqual([]);
  });

  it('L5 ResultsContent.tsx declares no revealBurstSlot style (AST: no property assignment named revealBurstSlot)', () => {
    const sf = parse(RESULTS_CONTENT);
    const where = relApp(RESULTS_CONTENT);
    let styleSheetCreateCalls = 0;
    const hits: string[] = [];
    walk(sf, (n) => {
      if (
        ts.isCallExpression(n) &&
        ts.isPropertyAccessExpression(n.expression) &&
        n.expression.getText(sf) === 'StyleSheet.create'
      ) {
        styleSheetCreateCalls += 1;
      }
      if (ts.isPropertyAssignment(n) && propertyNameText(n.name, sf) === 'revealBurstSlot') {
        hits.push(`${where}:${lineOf(sf, n)} revealBurstSlot`);
      }
    });
    // Non-vacuity: the file's StyleSheet was parsed.
    expect({ styleSheetCreateCalls }).toEqual({ styleSheetCreateCalls: 1 });
    expect(hits).toEqual([]);
  });
});
