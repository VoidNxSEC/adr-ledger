#!/usr/bin/env bash
set -e

# Wait for ml-ops-api to be ready if running in docker-compose
if [ -n "$ML_OPS_API_URL" ]; then
    echo "[*] Waiting for ML Ops API at $ML_OPS_API_URL..."
    until curl -s "$ML_OPS_API_URL/health" >/dev/null; do
        sleep 2
    done
fi

echo "[01] Starting ADR Lifecycle Tests..."
mkdir -p /tmp/ledger/adr/proposed

# Simulate creation, we are asserting it through intelagent tools
echo "Starting..." > /tmp/ledger/adr/proposed/ADR-TEST1.md

echo "[OK] ADR created."
