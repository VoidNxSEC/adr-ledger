#!/usr/bin/env bash
set -e

echo "==========================================="
echo "   ADR Ledger & IntelAgent Smoke Tests     "
echo "==========================================="

REPORT_FILE="/tmp/test-report.json"
echo '{"status": "running", "tests": []}' > "$REPORT_FILE"

run_test() {
    local script=$1
    echo "Running $script..."
    if bash "tests/smoke/$script"; then
        echo "✅ Passed: $script"
        jq ".tests += [{\"name\": \"$script\", \"status\": \"passed\"}]" "$REPORT_FILE" > "$REPORT_FILE.tmp" && mv "$REPORT_FILE.tmp" "$REPORT_FILE"
    else
        echo "❌ Failed: $script"
        jq ".tests += [{\"name\": \"$script\", \"status\": \"failed\"}]" "$REPORT_FILE" > "$REPORT_FILE.tmp" && mv "$REPORT_FILE.tmp" "$REPORT_FILE"
        exit 1
    fi
}

run_test "01_adr_lifecycle.sh"
run_test "02_cerebro_memory.sh"
run_test "03_ml_inference.sh"

jq '.status = "success"' "$REPORT_FILE" > "$REPORT_FILE.tmp" && mv "$REPORT_FILE.tmp" "$REPORT_FILE"
echo "All tests passed successfully! Report logged to $REPORT_FILE."
cat "$REPORT_FILE"
