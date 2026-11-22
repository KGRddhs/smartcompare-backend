/**
 * INC-C1 C1-4: a one-shot hand-off from the camera's photo state to Home.
 *
 * The photo state's "Type the names" button records the mode Home should open
 * in, then pops the stack back to Main; Home's focus effect reads it once.
 * Module state only, no storage: reading clears it, so a later focus keeps the
 * mode the user picked, and nothing outlives the running app.
 */

let pendingMode: 'type' | null = null;

/** Asks the next Home focus to open in `mode`. */
export function requestHomeMode(mode: 'type'): void {
  pendingMode = mode;
}

/** The pending mode, once: the read clears it. */
export function consumeHomeMode(): 'type' | null {
  const mode = pendingMode;
  pendingMode = null;
  return mode;
}
