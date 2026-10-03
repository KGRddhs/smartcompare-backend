#!/bin/sh
# Point this clone at the repo's committed hooks in .githooks/, so the
# pre-commit gate runs on every commit. Run it once per clone:
#
#   sh scripts/setup_hooks.sh
#
# PowerShell equivalent, one line, run from inside the clone:
#   git config core.hooksPath .githooks; git config --get core.hooksPath
#
# The setting is written to the clone's own config (local scope), which its
# linked worktrees share. The script sets that one value and prints it;
# nothing else.
set -eu

cd "$(dirname "$0")/.."
git config core.hooksPath .githooks
printf 'core.hooksPath = %s\n' "$(git config --get core.hooksPath)"
