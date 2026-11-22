#!/usr/bin/env bash

# Resolve a Talon CLI that supports the evidence interface used by presenters.
# When no installed binary is suitable, build the checked-out core source
# (typically current main) without changing the running Talon service.

talon_supports_demo_audit() {
  local candidate="$1" export_help verify_help
  [[ -n "$candidate" && -x "$candidate" ]] || return 1
  export_help="$("$candidate" audit export --help 2>&1 || true)"
  verify_help="$("$candidate" audit verify --help 2>&1 || true)"
  if [[ "${TALON_REQUIRE_OPENSHELL_AUDIT:-0}" == 1 ]]; then
    local runtime_help
    runtime_help="$("$candidate" audit list --help 2>&1 || true)"
    grep -Fq -- '--runtime-ref' <<<"$runtime_help" || return 1
    grep -Fq -- '--operation' <<<"$verify_help" || return 1
  fi
  grep -Fq -- '--session' <<<"$export_help" \
    && grep -Fq -- 'signed-json' <<<"$export_help" \
    && grep -Fq -- '--file' <<<"$verify_help"
}

build_checked_out_talon_audit_cli() {
  [[ "${TALON_REQUIRE_OPENSHELL_AUDIT:-0}" != 1 ]] || return 1
  local root="$1" source pin cache_dir target tmp worktree
  source="${TALON_REPO:-$root/../talon}"
  command -v git >/dev/null 2>&1 || return 1
  command -v go >/dev/null 2>&1 || return 1
  git -C "$source" rev-parse --git-dir >/dev/null 2>&1 || return 1

  # The caller supplies a Talon checkout (current main in CI). Build HEAD
  # from that checkout, never a historical Full Demo pin.
  pin="$(git -C "$source" rev-parse HEAD)"

  cache_dir="$root/.state/talon-audit-cli/$pin"
  target="$cache_dir/talon"
  if talon_supports_demo_audit "$target"; then
    printf '%s\n' "$target"
    return 0
  fi

  install -d -m 0700 "$cache_dir"
  tmp="$cache_dir/talon.tmp.$$"
  worktree="$root/.state/talon-audit-source-$pin-$$"
  rm -rf "$worktree" "$tmp"

  printf 'Building the checked-out Talon audit CLI for evidence presentation...\n' >&2
  if ! git -C "$source" worktree add --detach "$worktree" "$pin" >/dev/null 2>&1; then
    return 1
  fi

  if ! (
    cd "$worktree"
    CGO_ENABLED=1 go build -o "$tmp" ./cmd/talon/
  ); then
    git -C "$source" worktree remove --force "$worktree" >/dev/null 2>&1 || true
    rm -f "$tmp"
    return 1
  fi
  git -C "$source" worktree remove --force "$worktree" >/dev/null 2>&1 || true

  chmod 0700 "$tmp"
  mv "$tmp" "$target"
  talon_supports_demo_audit "$target" || return 1
  printf '%s\n' "$target"
}

resolve_talon_audit_bin() {
  local root="${1:-}" candidate resolved pidfile pid
  [[ -n "$root" ]] || return 1

  for candidate in \
    "${TALON_AUDIT_BIN:-}" \
    "${TALON_BIN:-}" \
    "$(command -v talon 2>/dev/null || true)" \
    "$HOME/go/bin/talon" \
    "$HOME/.local/bin/talon" \
    "$root/../talon/bin/talon" \
    "$root/../talon/talon"; do
    if talon_supports_demo_audit "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  for pidfile in \
    "$root/.state/talon-gateway.pid" \
    "$root/.state/talon-mcp-proxy.pid"; do
    [[ -r "$pidfile" ]] || continue
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    [[ "$pid" =~ ^[0-9]+$ ]] || continue
    candidate="/proc/$pid/exe"
    if talon_supports_demo_audit "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  resolved="$(build_checked_out_talon_audit_cli "$root" || true)"
  [[ -n "$resolved" ]] || return 1
  printf '%s\n' "$resolved"
}
