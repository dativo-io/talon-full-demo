#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/integrations/zendesk-app"
STATE="$ROOT/.state/zendesk-app"
MODE="${1:-offline}"
ZCLI_VERSION="${ZCLI_VERSION:-1.1.4}"
ZCLI_LOG="$STATE/zcli.log"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

for cmd in node npm jq unzip sha256sum find python3 tee; do need "$cmd"; done
case "$MODE" in offline|zcli) ;; *) die 'usage: package-zendesk-app.sh offline|zcli' ;; esac
install -d -m 0700 "$STATE"
rm -rf "$APP/tmp"

validate_source_contract() {
  for required in \
    manifest.json translations/en.json assets/iframe.html assets/main.js assets/icon_ticket_editor.svg; do
    [[ -s "$APP/$required" ]] || die "Zendesk app source is missing $required"
  done
  jq -e '
    .name and .version and .frameworkVersion == "2.0"
    and .private == true
    and .author.name and .author.email and .author.url
    and .location.support.ticket_editor.url == "assets/iframe.html"
    and any(.parameters[]; .name == "adapter_domain" and .required == true and .secure == false)
    and any(.parameters[]; .name == "adapter_token" and .required == true and .secure == true and (.scopes | index("header")))
    and (.domainWhitelist | index("{{setting.adapter_domain}}"))
  ' "$APP/manifest.json" >/dev/null || die 'Zendesk manifest is missing the private-app, location, author, or secure-setting contract'
  grep -Fq 'viewBox=' "$APP/assets/icon_ticket_editor.svg" \
    || die 'ticket editor SVG icon is missing a viewBox'
  if grep -Eq '<[^>]+fill=' "$APP/assets/icon_ticket_editor.svg"; then
    die 'ticket editor SVG icon must not hard-code fill styling'
  fi
}

inspect_zip() {
  local source_zip="$1" target="$2" proof="$3"
  cp "$source_zip" "$target"
  chmod 0600 "$target"

  local listing="$STATE/package-files.txt"
  unzip -Z1 "$target" | sort >"$listing"
  for expected in manifest.json assets/iframe.html assets/main.js assets/icon_ticket_editor.svg translations/en.json; do
    grep -Eq "(^|/)$expected$" "$listing" || die "Zendesk package is missing $expected"
  done
  for forbidden in '.env' 'zcli.apps.config.json' 'node_modules/' '/tmp/' 'TALON_.*KEY' '/test/' '^test/'; do
    if grep -Ei "$forbidden" "$listing" >/dev/null; then
      die "Zendesk package contains forbidden path or secret marker: $forbidden"
    fi
  done

  local extract="$STATE/extracted"
  rm -rf "$extract"
  mkdir -m 0700 "$extract"
  unzip -qq "$target" -d "$extract"
  if grep -RIE --exclude='main.js' --exclude='manifest.json' \
    'Bearer[[:space:]]+[A-Za-z0-9_-]{16,}|TALON_(CUSTOMER_SUPPORT|DOCUMENT_SUMMARY|CODING_ASSISTANT)_KEY=' \
    "$extract" >/dev/null 2>&1; then
    die 'Zendesk package appears to contain a generated credential value'
  fi

  local sha manifest_version
  sha="$(sha256sum "$target" | awk '{print $1}')"
  manifest_version="$(jq -r '.version' "$APP/manifest.json")"
  umask 077
  cat >"$STATE/package.env" <<EOF
export ZENDESK_APP_PACKAGE=$target
export ZENDESK_APP_PACKAGE_SHA256=$sha
export ZENDESK_APP_VERSION=$manifest_version
export ZENDESK_PACKAGE_PROOF=$proof
export ZENDESK_ZCLI_VERSION=$ZCLI_VERSION
export ZENDESK_ZCLI_LOG=$ZCLI_LOG
EOF
  chmod 0600 "$STATE/package.env"

  say
  say 'ZENDESK APP PACKAGE VERIFIED'
  say "  App version:  $manifest_version"
  say "  Proof:        $proof"
  say "  Package:      $target"
  say "  SHA-256:      $sha"
  say '  Secrets:      no generated credential values found'
}

offline_package() {
  validate_source_contract
  local staging="$STATE/offline-staging" source_zip="$STATE/offline-package.zip"
  rm -rf "$staging" "$source_zip"
  install -d -m 0700 "$staging"
  cp "$APP/manifest.json" "$staging/manifest.json"
  cp -R "$APP/assets" "$staging/assets"
  cp -R "$APP/translations" "$staging/translations"

  python3 - "$staging" "$source_zip" <<'PY'
from pathlib import Path
import sys, zipfile
root = Path(sys.argv[1])
out = Path(sys.argv[2])
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        info = zipfile.ZipInfo(path.relative_to(root).as_posix(), (1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        zf.writestr(info, path.read_bytes())
PY
  inspect_zip "$source_zip" "$STATE/talon-reply-assistant.offline.zip" 'offline-structure-and-secret-scan'
}

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
    say 'Authenticated ZCLI validation requires a Zendesk account.' >&2
    say 'Run `zcli login -i`, or set ZENDESK_SUBDOMAIN and ZENDESK_OAUTH_TOKEN, then retry.' >&2
    say "ZCLI diagnostics retained at: $ZCLI_LOG" >&2
    exit 1
  fi
}

zcli_package() {
  validate_source_contract
  node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>20 || (a===20 && b>=17) ? 0 : 1)' \
    || die 'Zendesk ZCLI requires Node.js 20.17.0 or newer'
  : >"$ZCLI_LOG"
  chmod 0600 "$ZCLI_LOG"
  run_logged "Validating Zendesk app with authenticated ZCLI $ZCLI_VERSION..." apps:validate "$APP"
  run_logged 'Packaging Zendesk private app with authenticated ZCLI...' apps:package "$APP"

  mapfile -d '' packages < <(find "$APP/tmp" -maxdepth 1 -type f -name '*.zip' -print0 | sort -z)
  (( ${#packages[@]} == 1 )) || die "expected exactly one ZCLI package in $APP/tmp, found ${#packages[@]}"
  inspect_zip "${packages[0]}" "$STATE/talon-reply-assistant.zcli.zip" 'authenticated-zcli-validation-and-package'
  say "  Diagnostics:  $ZCLI_LOG"
}

case "$MODE" in
  offline) offline_package ;;
  zcli) zcli_package ;;
esac
