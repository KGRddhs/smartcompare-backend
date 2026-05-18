// Bundle C — shared frontend assertion helpers (Section C plan, task C.0.1).
//
// Enforces the FIVE critical rules across all Bundle C frontend tests:
//   1. NO info banners — `expectNoBanner`.
//   2. NO backend internals in user-facing reveals — `expectNoMagnitudeStrings`.
//   3. NEVER "estimated" / "reference" / "indicative" in user-facing copy.
//   5. NO scary copy in i18n EN+AR.
//
// Import these helpers from any Bundle C frontend test file.

import type { ReactTestInstance } from "react-test-renderer";

export const FORBIDDEN_UI_STRINGS: RegExp[] = [
  /estimated/i,
  /estimate/i,
  /reference/i,
  /indicative/i,
  /couldn't/i,
  /try again/i,
  /Failed to/i,
  /تقدير/,
  /مُقدَّر/,
  /تعذر/,
  /فشل/,
];

const FORBIDDEN_MAGNITUDE_PATTERNS: RegExp[] = [
  /coefficient/i,
  /\b(magnitude|shift_pct|weight_delta|cap_pct|cap_percent|shift_magnitude|scaling_factor|formula_weight|raw_shift|shift_value)\b/i,
];

function serialise(tree: ReactTestInstance | unknown): string {
  if (!tree) return "";
  if (typeof tree === "string") return tree;
  // RNTL/react-test-renderer `.toJSON()` already returns a serialisable tree.
  try {
    return JSON.stringify(tree);
  } catch {
    return String(tree);
  }
}

export function expectNoForbiddenStrings(
  renderedTree: ReactTestInstance | unknown,
): void {
  const text = serialise(renderedTree);
  for (const re of FORBIDDEN_UI_STRINGS) {
    if (re.test(text)) {
      throw new Error(
        `Forbidden UI string ${re} found in rendered tree (excerpt: ${text.slice(0, 200)})`,
      );
    }
  }
}

export function expectNoMagnitudeStrings(
  renderedTree: ReactTestInstance | unknown,
): void {
  const text = serialise(renderedTree);
  for (const re of FORBIDDEN_MAGNITUDE_PATTERNS) {
    if (re.test(text)) {
      throw new Error(
        `Forbidden magnitude/coefficient term ${re} found in rendered tree (excerpt: ${text.slice(0, 200)})`,
      );
    }
  }
}

type Query = (matcher: any) => any;

/**
 * Assert ABSENCE of banner-like elements per project rule #1.
 *
 * Pass `queryByRole` and `queryByLabelText` from a RNTL `render` call.
 */
export function expectNoBanner(
  queryByRole: Query | undefined,
  queryByLabelText: Query | undefined,
): void {
  if (typeof queryByRole === "function") {
    // Native React Native components rarely expose role="alert" by default,
    // but Aria-role props or web testing surfaces may. Treat any hit as a fail.
    const alert = queryByRole("alert");
    if (alert) {
      throw new Error("Found role=alert in rendered tree (banner forbidden)");
    }
  }
  if (typeof queryByLabelText === "function") {
    for (const re of [
      /info banner/i,
      /warning banner/i,
      /insufficient.*data/i,
      /banner-/i,
    ]) {
      const hit = queryByLabelText(re);
      if (hit) {
        throw new Error(
          `Found banner-like accessibilityLabel matching ${re} (banner forbidden)`,
        );
      }
    }
  }
}
