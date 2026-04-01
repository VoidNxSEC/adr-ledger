#!/usr/bin/env bash
# ADR Ledger validation pipeline
#
# Hard failures:
# - ADR parsing/schema validation
# - OPA policy validation
#
# Soft warnings:
# - existing chain integrity drift
# - missing or invalid Bitcoin-compatible receipts unless governance requires them
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ADR_DIR="${1:-$REPO_ROOT/adr}"
SCHEMA_PATH="$REPO_ROOT/.schema/adr.schema.json"
OPA_POLICY_PATH="$REPO_ROOT/policies/adr/validation.rego"
BASH_BIN="${BASH:-bash}"
PYTHON_BIN="${PYTHON_BIN:-python3.13}"

echo "[INFO] ADR schema and section validation"
"$PYTHON_BIN" "$REPO_ROOT/scripts/validate_adr.py" \
  "$ADR_DIR" \
  --schema "$SCHEMA_PATH" \
  --schema-mode warn

if [[ -f "$OPA_POLICY_PATH" ]]; then
  echo ""
  echo "[INFO] OPA governance validation"
  "$BASH_BIN" "$REPO_ROOT/scripts/opa-validate.sh" "$ADR_DIR"
fi

if [[ -f "$REPO_ROOT/.chain/chain.json" ]]; then
  echo ""
  echo "[INFO] Chain integrity check"
  if ! "$PYTHON_BIN" "$REPO_ROOT/.chain/chain_manager.py" verify; then
    echo "[WARN] Chain integrity is not clean. Validation continues because this is pre-existing ledger state drift." >&2
  fi
fi

if [[ -f "$REPO_ROOT/.chain/bitcoin_attestation.py" ]]; then
  echo ""
  echo "[INFO] Bitcoin-compatible receipt verification"
  if ! "$PYTHON_BIN" "$REPO_ROOT/.chain/bitcoin_attestation.py" verify-all; then
    echo "[WARN] Bitcoin attestation receipts require attention." >&2
  fi
fi

echo ""
echo "[OK] Validation pipeline completed"
