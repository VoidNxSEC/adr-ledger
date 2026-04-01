#!/usr/bin/env bash
# ADR-Ledger OPA policy validation wrapper
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ADR_TARGET="${1:-$REPO_ROOT/adr}"
POLICY_PATH="${OPA_POLICY_PATH:-$REPO_ROOT/policies/adr/validation.rego}"
OPA_QUERY="${OPA_QUERY:-data.adr.validation.result}"

if [[ ! -f "$POLICY_PATH" ]]; then
  echo "[ERROR] OPA policy not found: $POLICY_PATH" >&2
  exit 1
fi

python3.13 "$REPO_ROOT/scripts/validate_adr.py" \
  "$ADR_TARGET" \
  --skip-schema \
  --opa-policy "$POLICY_PATH" \
  --opa-query "$OPA_QUERY"
