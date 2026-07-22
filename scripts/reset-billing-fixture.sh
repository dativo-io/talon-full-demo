#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CASE="$ROOT/cases/billing-demo"

# Always rebuild the working fixture from the outer repository's committed
# version. The previous implementation merely committed whatever a prior
# Copilot run had left behind, so one bad run poisoned every later demo.
rm -rf "$CASE/.git" "$CASE/out" "$CASE/src" "$CASE/test"
rm -f "$CASE/package.json" "$CASE/package-lock.json"
mkdir -p "$CASE/src" "$CASE/test"

for path in package.json src/invoice.mjs test/invoice.test.mjs; do
  git -C "$ROOT" show "HEAD:cases/billing-demo/$path" > "$CASE/$path"
done

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
  [[ -z "$(git status --short)" ]] || { echo 'billing fixture reset left uncommitted changes' >&2; exit 1; }
)
echo 'billing fixture restored from committed baseline, has no remote, and fails as expected'
