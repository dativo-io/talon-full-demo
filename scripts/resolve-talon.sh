#!/usr/bin/env bash

# Resolve the Talon CLI without assuming that the current shell inherited the
# PATH used when the real demo stack was prepared or started.
#
# Resolution order:
#   1. explicit TALON_BIN
#   2. current PATH
#   3. common user-local install locations
#   4. sibling Talon checkout build locations
#   5. the executable of a repository-owned running Talon process
resolve_talon_bin() {
  local root="${1:-}"
  local candidate pidfile pid command_line

  [[ -n "$root" ]] || return 1

  for candidate in \
    "${TALON_BIN:-}" \
    "$(command -v talon 2>/dev/null || true)" \
    "$HOME/go/bin/talon" \
    "$HOME/.local/bin/talon" \
    "$root/../talon/bin/talon" \
    "$root/../talon/talon"; do
    [[ -n "$candidate" && -x "$candidate" ]] || continue
    printf '%s\n' "$candidate"
    return 0
  done

  for pidfile in \
    "$root/.state/talon-gateway.pid" \
    "$root/.state/talon-mcp-proxy.pid"; do
    [[ -r "$pidfile" ]] || continue
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    [[ "$pid" =~ ^[0-9]+$ && -x "/proc/$pid/exe" ]] || continue
    command_line="$(tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null || true)"
    [[ "$command_line" == *"talon serve"* ]] || continue
    printf '/proc/%s/exe\n' "$pid"
    return 0
  done

  return 1
}
