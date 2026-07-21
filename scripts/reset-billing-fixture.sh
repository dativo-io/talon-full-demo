#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CASE="$ROOT/cases/billing-demo"
rm -rf "$CASE/.git" "$CASE/out"
(
  cd "$CASE"
  git init -q
  git remote remove origin >/dev/null 2>&1 || true
  git add .
  git -c user.name='Talon Demo' -c user.email='demo@dativo.io' commit -qm 'demo: initial failing billing fixture'
  if npm test >/dev/null 2>&1; then
    echo 'billing fixture unexpectedly passes' >&2
    exit 1
  fi
  [[ -z "$(git remote)" ]] || { echo 'billing fixture must not have a Git remote' >&2; exit 1; }
)
echo 'billing fixture reset, has no remote, and fails as expected'
