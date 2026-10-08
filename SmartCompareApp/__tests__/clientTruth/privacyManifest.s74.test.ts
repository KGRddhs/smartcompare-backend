/**
 * S74 CLIENT-TRUTH - the SearchHistory privacy declaration names Analytics (C34).
 *
 * Spec CLIENT_TRUTH_SPEC.md section 6 + section 8 row CT-P1. The server logs
 * every compare query to search_logs (app/services/database_service.py
 * log_search), and the admin dashboards read the top query strings back
 * (app/services/analytics_service.py get_daily_stats / get_popular_queries),
 * so SearchHistory is also collected for Analytics. At main dfbda511 the iOS
 * privacy manifest (app.json, SearchHistory purposes) and the inventory row 5
 * (docs/privacy-data-inventory.md) declare AppFunctionality and
 * ProductPersonalization only. Native-build only (a precondition of the
 * production eas build); nativeBundle.w37 c3 keeps app.json and the
 * inventory JSON fence identical.
 */
import * as fs from 'fs';
import * as path from 'path';

const APP_DIR = path.resolve(__dirname, '../..');
const REPO = path.resolve(APP_DIR, '..');

function findSearchHistoryEntries(node: unknown, out: any[] = []): any[] {
  if (Array.isArray(node)) {
    node.forEach((n) => findSearchHistoryEntries(n, out));
  } else if (node && typeof node === 'object') {
    const obj = node as Record<string, unknown>;
    if (obj.NSPrivacyCollectedDataType === 'NSPrivacyCollectedDataTypeSearchHistory') out.push(obj);
    Object.values(obj).forEach((v) => findSearchHistoryEntries(v, out));
  }
  return out;
}

describe('S74 CLIENT-TRUTH SearchHistory declares Analytics', () => {
  it('CT-P1: app.json SearchHistory purposes include NSPrivacyCollectedDataTypePurposeAnalytics', () => {
    const appJson = JSON.parse(fs.readFileSync(path.join(APP_DIR, 'app.json'), 'utf8'));
    const entries = findSearchHistoryEntries(appJson);
    expect(entries).toHaveLength(1);
    expect(entries[0].NSPrivacyCollectedDataTypePurposes).toContain(
      'NSPrivacyCollectedDataTypePurposeAnalytics',
    );
  });

  it('CT-P1: inventory row 5 (SearchHistory) lists Analytics among its purposes and cites analytics_service.py', () => {
    const inventory = fs.readFileSync(path.join(REPO, 'docs/privacy-data-inventory.md'), 'utf8');
    const row = inventory.split(/\r?\n/).find((l) => /^\|\s*5\s*\|\s*`SearchHistory`\s*\|/.test(l));
    expect(row).toBeDefined();
    const cells = (row as string)
      .split(/(?<!\\)\|/)
      .map((c) => c.trim())
      .filter((c) => c.length > 0);
    const purposes = cells[cells.length - 1];
    expect(purposes.split(',').map((p) => p.trim())).toContain('Analytics');
    expect(row).toContain('analytics_service.py');
  });
});
