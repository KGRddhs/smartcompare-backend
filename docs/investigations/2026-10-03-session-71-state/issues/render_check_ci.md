## Context
U4b (PR #279) adds `scripts/render_myez_icons.py` with a `--check` mode that re-renders the four launcher files in memory and compares pixels and the manifest. Nothing in CI runs it. The jest pins (`nativeBundle.w37`) check size, mode, chunks, colours, the safe circle and the manifest hashes, but not the splash mark position: a mutant that moved the splash mark to a corner and updated the manifest consistently passed all 58 tests (U4b App Review adversary).

## Proposal
1. Add a CI step (backend job, the pinned Pillow is already in `requirements-dev.txt`): `python scripts/render_myez_icons.py --check`. It exits 1 on any mismatch and 2 on a precondition failure.
2. Add a jest pin for the splash mark position: the alpha bounding box centre within a few pixels of the expected offset from the canvas centre.
3. Add a pin that `ICON_ART_SUPPLIED` is `true`, so a flip back to `false` cannot silently skip the art tests (the toggle mutant only skipped two tests and failed none).

## Acceptance
- Editing any of the four PNGs without re-running the renderer fails CI.
- The moved-splash mutant and the toggle mutant both fail.

Severity: low (test strength). Source: U4b adversary minors; test files were frozen after the RED gate, so these were not applied in the unit.
