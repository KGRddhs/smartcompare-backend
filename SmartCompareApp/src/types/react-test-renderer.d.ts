/**
 * Ambient module shim for react-test-renderer 19.x.
 *
 * `@types/react-test-renderer` was deprecated upstream (React 19 ships
 * the package without official .d.ts files for unit-test consumers). The
 * project pulls in `react-test-renderer@^19.1.0` for the existing
 * `__tests__/CameraHelpOverlay.render.test.tsx` and
 * `__tests__/NewOnboardingHost.editMode.test.tsx` files. Without this
 * shim, `npx tsc --noEmit` emits TS7016 "Could not find a declaration
 * file" and exits 2 even though the runtime tests pass under jest.
 *
 * We expose only the surface the test files actually use:
 *   - `create(node)` — root creator
 *   - `act(callback)` — concurrent-render flush wrapper
 *   - `ReactTestRenderer` — return type of `create`
 *
 * If a future test needs `.root.findByType`, `.toJSON()`, etc., widen
 * the `ReactTestRenderer` interface below — do NOT install
 * `@types/react-test-renderer` (deprecated, will diverge from runtime).
 */

declare module 'react-test-renderer' {
  import type { ReactElement } from 'react';

  export interface ReactTestRenderer {
    root: any;
    toJSON(): any;
    update(node: ReactElement): void;
    unmount(): void;
  }

  export function create(node: ReactElement, options?: unknown): ReactTestRenderer;
  export function act(callback: () => void | Promise<void>): void;

  const TestRenderer: {
    create: typeof create;
    act: typeof act;
  };
  export default TestRenderer;
}
