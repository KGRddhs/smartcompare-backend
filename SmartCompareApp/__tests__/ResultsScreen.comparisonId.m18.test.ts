/**
 * M18 comparison-id unit — MB-contract-01 / MB-contract-03 / MB-contract-10.
 *
 * Source-string assertions (the established ResultsScreen convention — see
 * ResultsScreen.guards.test.tsx: the full render needs the whole Reanimated
 * surface + 9 service mocks, so the wiring contract is pinned structurally;
 * the behavioral halves live in api.getComparison.comparisonId.m18.test.ts
 * and InviteeQuizScreen.matchScore.m18.test.tsx).
 *
 * Contract:
 *  - MB-contract-01: ResultsScreen must NEVER send metadata.query as
 *    comparison_id. The backend (M13-29, feedback_routes.py:89-124)
 *    UUID-validates comparison_id on BOTH /feedback and /events, so a query
 *    string 422s the whole batch — and trackEvents swallows the error, so
 *    every Results event batch + every feedback row was silently dropped.
 *  - MB-contract-03: sharableComparisonId must read the real id
 *    (result.comparison_id, surfaced by getComparison, with
 *    route.params.comparison_id as fallback) — not phantom keys.
 *  - MB-contract-10: ctaVariant's margin must come from scoring_v2.win_margin
 *    or overview.winner.margin — scoring.win_margin never exists on the wire
 *    (response_builder.py:1557-1564 emits six keys, none of them win_margin).
 */

import * as fs from 'fs';
import * as path from 'path';

const SRC = (rel: string) => fs.readFileSync(path.resolve(__dirname, rel), 'utf8');

const RESULTS = SRC('../src/screens/ResultsScreen.tsx');
const TYPES = SRC('../src/types/types.ts');
const QUIZ = SRC('../src/screens/InviteeQuizScreen.tsx');

describe('ResultsScreen — comparisonId is the real UUID, never metadata.query (MB-contract-01)', () => {
  it('does NOT derive comparisonId from metadata.query', () => {
    expect(RESULTS).not.toMatch(/const\s+comparisonId\s*=\s*metadata\?\.query/);
  });

  it('derives comparisonId from result.comparison_id with the route param as fallback', () => {
    expect(RESULTS).toMatch(
      /const\s+comparisonId\s*=\s*result\?\.comparison_id\s*\?\?\s*route\?\.params\?\.comparison_id/
    );
  });
});

describe('ResultsScreen — sharableComparisonId reads the real id (MB-contract-03)', () => {
  it('no longer reads the phantom (metadata as any)?.comparison_id key', () => {
    expect(RESULTS).not.toMatch(/\(metadata as any\)\?\.comparison_id/);
  });

  it('no longer needs the (result as any) cast for comparison_id (typed on ComparisonResult)', () => {
    expect(RESULTS).not.toMatch(/\(result as any\)\?\.comparison_id/);
  });

  it('sharableComparisonId is the same real id threaded into events/feedback', () => {
    expect(RESULTS).toMatch(/const\s+sharableComparisonId\s*=\s*comparisonId/);
  });
});

describe('ResultsScreen — ctaVariant margin reads real keys (MB-contract-10)', () => {
  it('does NOT read the phantom scoring.win_margin', () => {
    expect(RESULTS).not.toMatch(/scoring\?\.win_margin/);
  });

  it('reads scoring_v2.win_margin with overview.winner.margin as fallback', () => {
    expect(RESULTS).toMatch(
      /scoring_v2\?\.win_margin\s*\?\?\s*result\?\.overview\?\.winner\?\.margin/
    );
  });
});

describe('types.ts — ScoringResult matches the wire (MB-contract-10)', () => {
  const scoringBlock = (() => {
    const m = TYPES.match(/export interface ScoringResult \{([\s\S]*?)\n\}/);
    return m ? m[1] : '';
  })();

  it('ScoringResult interface exists and keeps the real keys', () => {
    expect(scoringBlock).toContain('scores');
    expect(scoringBlock).toContain('scoring_method');
  });

  it('ScoringResult no longer declares the phantom win_margin', () => {
    expect(scoringBlock).not.toContain('win_margin');
  });

  it('ScoringResult no longer declares the phantom winner_index', () => {
    expect(scoringBlock).not.toContain('winner_index');
  });

  it('ComparisonResult declares the optional comparison_id the client now threads', () => {
    const m = TYPES.match(/export interface ComparisonResult \{([\s\S]*?)\n\}/);
    expect(m).toBeTruthy();
    expect(m![1]).toMatch(/comparison_id\?\:\s*string/);
  });
});

describe('InviteeQuizScreen — no phantom scoring.products read (MB-contract-10)', () => {
  it('does NOT read result.scoring.products', () => {
    expect(QUIZ).not.toMatch(/scoring\?\.products/);
  });

  it('reads the real scoring.scores.product_N.overall shape', () => {
    expect(QUIZ).toMatch(/scoring\?\.scores/);
    expect(QUIZ).toMatch(/overall/);
  });
});
