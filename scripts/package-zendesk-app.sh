#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/integrations/zendesk-app"
STATE="$ROOT/.state/zendesk-app"
ZCLI_VERSION="${ZCLI_VERSION:-1.1.4}"
ZCLI_LOG="$STATE/zcli.log"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

for cmd in node npm jq unzip sha256sum find tee; do need "$cmd"; done
node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>20 || (a===20 && b>=17) ? 0 : 1)' \
  || die 'Zendesk ZCLI requires Node.js 20.17.0 or newer'

rm -rf "$APP/tmp"
install -d -m 0700 "$STATE"
: >"$ZCLI_LOG"
chmod 0600 "$ZCLI_LOG"

run_zcli() {
  if command -v zcli >/dev/null 2>&1 && zcli --version 2>/dev/null | grep -Fq "$ZCLI_VERSION"; then
    zcli "$@"
  else
    npx --yes "@zendesk/zcli@$ZCLI_VERSION" "$@"
  fi
}

run_logged() {
  local label="$1"
  shift
  say "$label"
  if ! run_zcli "$@" 2>&1 | tee -a "$ZCLI_LOG"; then
    say >&2
    say "ZCLI diagnostics retained at: $ZCLI_LOG" >&2
    exit 1
  fi
}

run_logged "Validating Zendesk app with ZCLI $ZCLI_VERSION..." apps:validate "$APP"
run_logged 'Packaging Zendesk private app...' apps:package "$APP"

mapfile -d '' packages < <(find "$APP/tmp" -maxdepth 1 -type f -name '*.zip' -print0 | sort -z)
(( ${#packages[@]} == 1 )) || die "expected exactly one ZCLI package in $APP/tmp, found ${#packages[@]}"
source_zip="${packages[0]}"
target="$STATE/talon-reply-assistant.zip"
cp "$source_zip" "$target"
chmod 0600 "$target"

listing="$STATE/package-files.txt"
unzip -Z1 "$target" | sort >"$listing"
for expected in manifest.json assets/iframe.html assets/main.js translations/en.json; do
  grep -Eq "(^|/)$expected$" "$listing" || die "ZCLI package is missing $expected"
done
for forbidden in '.env' 'zcli.apps.config.json' 'node_modules/' '/tmp/' 'TALON_.*KEY'; do
  if grep -Ei "$forbidden" "$listing" >/dev/null; then
    die "ZCLI package contains forbidden path or secret marker: $forbidden"
  fi
done

# Inspect text payloads too: the secure setting placeholder is allowed, but no
# generated credential value or repository-local secret file may be present.
extract="$STATE/extracted"
rm -rf "$extract"
mkdir -m 0700 "$extract"
unzip -qq "$target" -d "$extract"
if grep -RIE --exclude='main.js' --exclude='manifest.json' \
  'Bearer[[:space:]]+[A-Za-z0-9_-]{16,}|TALON_(CUSTOMER_SUPPORT|DOCUMENT_SUMMARY|CODING_ASSISTANT)_KEY=' \
  "$extract" >/dev/null 2>&1; then
  die 'ZCLI package appears to contain a generated credential value'
fi

sha="$(sha256sum "$target" | awk '{print $1}')"
manifest_version="$(jq -r '.version' "$APP/manifest.json")"
umask 077
cat >"$STATE/package.env" <<EOF
export ZENDESK_APP_PACKAGE=$target
export ZENDESK_APP_PACKAGE_SHA256=$sha
export ZENDESK_APP_VERSION=$manifest_version
export ZENDESK_ZCLI_VERSION=$ZCLI_VERSION
export ZENDESK_ZCLI_LOG=$ZCLI_LOG
EOF
chmod 0600 "$STATE/package.env"

say
say 'ZENDESK APP PACKAGE VERIFIED'
say "  App version:  $manifest_version"
say "  ZCLI version: $ZCLI_VERSION"
say "  Package:      $target"
say "  SHA-256:      $sha"
say "  Diagnostics:  $ZCLI_LOG"
say '  Secrets:      no generated credential values found'
