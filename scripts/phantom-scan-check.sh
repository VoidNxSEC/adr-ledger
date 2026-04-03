#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-.}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ALLOWLIST_FILE="${PHANTOM_SCAN_ALLOWLIST:-${REPO_ROOT}/.phantom-scan.allowlist}"
PHANTOM_ROOT="${PHANTOM_ROOT:-${REPO_ROOT}/../phantom}"
PHANTOM_REF="${PHANTOM_REF:-github:VoidNxSEC/phantom}"

TMP_OUTPUT="$(mktemp)"
TMP_CLEAN="$(mktemp)"
TMP_ALLOWLIST="$(mktemp)"

cleanup() {
  rm -f "$TMP_OUTPUT" "$TMP_CLEAN" "$TMP_ALLOWLIST"
}
trap cleanup EXIT

run_scan() {
  if command -v phantom-scan >/dev/null 2>&1; then
    phantom-scan "$TARGET"
    return
  fi

  if ! command -v nix >/dev/null 2>&1; then
    echo "[ERROR] nix is required when phantom-scan is not already in PATH" >&2
    exit 1
  fi

  if [ -d "$PHANTOM_ROOT" ]; then
    nix develop "$PHANTOM_ROOT" --command phantom-scan "$TARGET"
  else
    nix run "${PHANTOM_REF}#phantom-scan" -- "$TARGET"
  fi
}

run_scan | tee "$TMP_OUTPUT"

sed -E 's/\x1B\[[0-9;]*[[:alpha:]]//g' "$TMP_OUTPUT" >"$TMP_CLEAN"

extract_between() {
  local start_pattern="$1"
  local stop_pattern="${2:-}"

  awk -v start="$start_pattern" -v stop="$stop_pattern" '
    $0 ~ start {
      capture = 1
      next
    }
    capture && stop != "" && $0 ~ stop {
      capture = 0
      exit
    }
    capture {
      print
    }
  ' "$TMP_CLEAN"
}

normalize_lines() {
  sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | sed '/^$/d'
}

filter_allowlist() {
  if [ ! -f "$ALLOWLIST_FILE" ]; then
    cat
    return
  fi

  grep -vE '^[[:space:]]*(#|$)' "$ALLOWLIST_FILE" >"$TMP_ALLOWLIST"
  if [ ! -s "$TMP_ALLOWLIST" ]; then
    cat
    return
  fi

  grep -v -E -f "$TMP_ALLOWLIST" || true
}

CREDENTIAL_FINDINGS="$(
  {
    extract_between '^Potential credentials:$' '^Private keys:$' |
      normalize_lines |
      grep -v '^None found$' || true
  } | filter_allowlist
)"

PRIVATE_KEY_FINDINGS="$(
  {
    extract_between '^Private keys:$' |
      normalize_lines |
      grep -v '^None found$' |
      grep -v '^✓ Scan complete$' || true
  } | filter_allowlist
)"

if [ -n "$CREDENTIAL_FINDINGS" ] || [ -n "$PRIVATE_KEY_FINDINGS" ]; then
  echo
  echo "[ERROR] phantom-scan reported findings outside the allowlist" >&2
  if [ -n "$CREDENTIAL_FINDINGS" ]; then
    echo "[ERROR] Credential findings:" >&2
    printf '%s\n' "$CREDENTIAL_FINDINGS" >&2
  fi
  if [ -n "$PRIVATE_KEY_FINDINGS" ]; then
    echo "[ERROR] Private key findings:" >&2
    printf '%s\n' "$PRIVATE_KEY_FINDINGS" >&2
  fi
  exit 1
fi

echo
echo "[OK] phantom-scan findings are empty or allowlisted"
