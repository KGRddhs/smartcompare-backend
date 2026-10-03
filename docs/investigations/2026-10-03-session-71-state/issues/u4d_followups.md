=== TITLE: Landing pages link /favicon.png that landing/ does not ship (404)
=== LABELS: landing
## Context
Found by the U4d visual adversary (PR #307): `landing/index.html`, `open.html`, `privacy`, `support` and `terms` link `/favicon.png`, but `landing/` holds no `favicon.png` and `landing/Dockerfile` copies none, so nginx falls through `try_files` to a 404. A reviewer who opens a shared `/c/` hand-off link sees the missing icon in the tab.

## What to build
Add a MYEZ `favicon.png` to `landing/` (rendered from the committed master `docs/brand/myez-icon-master-2048.png` by `scripts/render_myez_icons.py`, with a manifest entry covered by `--check`) and a `COPY` line in the Dockerfile. It ships with the next landing redeploy (`railway up landing --path-as-root -s qaren-landing -d`, the third lever).

=== TITLE: Render-based accessibility pin for the Register email-confirmation state
=== LABELS: mobile,tests
## Context
U4d (PR #307) put the MYEZ mark on Register in both states. The engineering adversary measured two jest survivors on the email-confirmation state: a labelled `accessible` header around the mark (breaks the hidden-mark rule D3) and a dropped tagline both pass, because `authBrandMark.u4d` renders only the form state and the AST check covers only the mark's size and parent style. The shipped code is correct for both.

## What to build
One new test file (the U4d files are frozen) that drives the m18 email-confirmation path and asserts: exactly one hidden `Image` host, no `accessible` / `accessibilityLabel` host from the Image to the root, and the tagline present. Kill both mutants (notes in the session-71 scratch: `u4d/adv-engineering/mutants.py`, O4a and O4c). A `tintColor` attribute on an auth `<QarenLogo>` is already caught by `tsc` (TS2322), so no jest pin is needed for it.
