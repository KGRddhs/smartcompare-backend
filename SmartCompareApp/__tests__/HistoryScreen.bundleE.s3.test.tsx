/**
 * Bundle E S3 — A2 HistoryScreen JSX element-order pins (close-gap mode).
 *
 * Sources of truth:
 *  - docs/claude-design-handoff/ui_kits/mobile/HistoryScreen.jsx (1-388)
 *  - docs/plans/_s3-a2-element-order.md
 *
 * HistoryScreen.tsx is already structurally JSX-aligned (HistoryHeroStats
 * + HistoryRowV2 ProductBlock pair + center VS pill shipped in S2). This
 * suite pins the JSX-aligned shape + adds image_url slot testIDs for A4
 * to wire <Image>.
 */

import * as fs from 'fs';
import * as path from 'path';

const HISTORY_PATH = path.resolve(
  __dirname,
  '../src/screens/HistoryScreen.tsx'
);
const HISTORY_SRC = fs.readFileSync(HISTORY_PATH, 'utf8');

describe('Bundle E S3 — HistoryScreen JSX element-order (HistoryScreen.jsx 1-388)', () => {
  // # 1 Header — display title
  it('renders header with display-weight history title (JSX 369-373)', () => {
    expect(HISTORY_SRC).toMatch(/styles\.header\b/);
    expect(HISTORY_SRC).toMatch(/styles\.headerTitle\b/);
    expect(HISTORY_SRC).toMatch(/t\(['"]history\.title['"]\)/);
  });

  // # 2 HistoryHeroStats above search field
  it('renders HistoryHeroStats component above the search field (JSX 60-109)', () => {
    expect(HISTORY_SRC).toContain('history-hero-stats');
    expect(HISTORY_SRC).toMatch(/<HistoryHeroStats\b/);
  });

  it('HistoryHeroStats renders stat strip: decisions count + savings BHD', () => {
    expect(HISTORY_SRC).toMatch(/history\.hero\.eyebrow/);
    expect(HISTORY_SRC).toMatch(/history\.hero\.count/);
    expect(HISTORY_SRC).toMatch(/history\.hero\.savings/);
  });

  it('HistoryHeroStats renders horizontal marquee with mini VS cards (JSX 99-107)', () => {
    expect(HISTORY_SRC).toContain('history-hero-marquee');
    expect(HISTORY_SRC).toMatch(/horizontal/);
  });

  it('HistoryHeroStats marquee cards have image_url slot testIDs (Bundle E S3 — A4 wires Image)', () => {
    // A4 will swap the colored tile for an <Image> at this slot. Per JSX:153
    // the mini-card has one image per product.
    expect(HISTORY_SRC).toMatch(/history-hero-card-image-slot-[ab]/);
  });

  // # 3 Search field
  it('renders rounded-pill search field below hero stats (JSX 183-201)', () => {
    expect(HISTORY_SRC).toMatch(/styles\.searchContainer\b/);
    expect(HISTORY_SRC).toMatch(/styles\.searchInput\b/);
    expect(HISTORY_SRC).toMatch(/t\(['"]history\.search['"]\)/);
  });

  // # 4 DateGroupV2 sections (Today/Yesterday/This Week/Older)
  it('groups items into date sections (JSX 307-318)', () => {
    expect(HISTORY_SRC).toMatch(/history\.today/);
    expect(HISTORY_SRC).toMatch(/history\.yesterday/);
    expect(HISTORY_SRC).toMatch(/history\.thisWeek/);
    expect(HISTORY_SRC).toMatch(/history\.older/);
    expect(HISTORY_SRC).toMatch(/<SectionList\b/);
  });

  // # 5 HistoryRowV2 — VS pair card
  it('renders HistoryRowV2 with category eyebrow + ago + ProductBlock pair + center vs pill (JSX 251-305)', () => {
    expect(HISTORY_SRC).toMatch(/styles\.rowV2\b/);
    expect(HISTORY_SRC).toMatch(/styles\.rowV2Header\b/);
    expect(HISTORY_SRC).toMatch(/styles\.rowV2Pair\b/);
    expect(HISTORY_SRC).toMatch(/styles\.rowV2VsPill\b/);
    expect(HISTORY_SRC).toMatch(/styles\.rowV2Verdict\b/);
  });

  it('HistoryRowV2 marks winner with TOP MATCH eyebrow + emerald-border block', () => {
    expect(HISTORY_SRC).toMatch(/rowV2TopMatch/);
    expect(HISTORY_SRC).toMatch(/rowV2BlockWinner/);
    expect(HISTORY_SRC).toMatch(/TOP MATCH/);
  });

  it('HistoryRowV2 product tiles have image_url slot testIDs (Bundle E S3 — A4 wires Image)', () => {
    // Per JSX:226-233 ProductBlock has one image per product. A4 wires.
    expect(HISTORY_SRC).toMatch(/history-row-\$\{[^}]+\}-block-(?:a|b)-image-slot/);
  });

  it('HistoryRowV2 deduplicates brand-prefix duplicates (Path A guard preserved)', () => {
    expect(HISTORY_SRC).toMatch(/dedupeBrandPrefix/);
  });
});

describe('Bundle E S3 — HistoryScreen preserve list', () => {
  it('SectionList grouping + RefreshControl preserved', () => {
    expect(HISTORY_SRC).toMatch(/<RefreshControl\b/);
  });

  it('formatTimeAgoLocalized i18n preserved (locale-aware "منذ" / "ago")', () => {
    expect(HISTORY_SRC).toMatch(/formatTimeAgoLocalized/);
    expect(HISTORY_SRC).toMatch(/formatTimeAgo/);
  });

  it('viewAsResult navigates to Results with comparison_id (not full_response)', () => {
    expect(HISTORY_SRC).toMatch(/comparison_id:\s*item\.id/);
  });

  it('delete flow with Alert + filter preserved', () => {
    expect(HISTORY_SRC).toMatch(/deleteComparison/);
    expect(HISTORY_SRC).toMatch(/Alert\.alert/);
  });

  it('authError branch redirects via clearSession + onLogout', () => {
    expect(HISTORY_SRC).toMatch(/clearSession/);
    expect(HISTORY_SRC).toMatch(/onLogout/);
  });
});

describe('Bundle E S3 — HistoryScreen forbidden copy guard', () => {
  it('no scary EN vocab (per CLAUDE.md banned list)', () => {
    expect(HISTORY_SRC).not.toMatch(/"[^"]*couldn['\u2019]t[^"]*"/i);
    expect(HISTORY_SRC).not.toMatch(/"[^"]*try again[^"]*"/i);
    expect(HISTORY_SRC).not.toMatch(/"[^"]*Failed to[^"]*"/i);
  });

  it('no top-level info banners', () => {
    expect(HISTORY_SRC).not.toMatch(/InfoBanner/);
  });
});
