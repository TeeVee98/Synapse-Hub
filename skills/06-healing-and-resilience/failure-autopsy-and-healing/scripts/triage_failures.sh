#!/usr/bin/env bash
# Triage Failures Script for Enterprise Automation
# Cross-platform: Compatible with macOS, Linux CI, and Windows Git Bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if git -C "$SCRIPT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
    WORKSPACE_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
else
    WORKSPACE_DIR="$(pwd)"
fi
SCREENSHOT_DIR="$WORKSPACE_DIR/Screenshots"
REPORTS_DIR="$WORKSPACE_DIR/Reports"
if [ ! -d "$REPORTS_DIR" ] && [ -d "$WORKSPACE_DIR/reports" ]; then
    REPORTS_DIR="$WORKSPACE_DIR/reports"
fi

echo "=========================================================="
echo "  ENTERPRISE FAILURE AUTOPSY & TRIAGE SCANNER (CROSS-PLATFORM)"
echo "  Workspace: $WORKSPACE_DIR"
echo "=========================================================="

# 1. Scan latest JUnit XML report
LATEST_JUNIT=$(find "$REPORTS_DIR" -type f \( -name "JUnit_Report.xml" -o -name "junit*.xml" \) 2>/dev/null | sort -r | head -n 1)

if [ -n "$LATEST_JUNIT" ]; then
    echo "Latest JUnit report: $(basename "$(dirname "$LATEST_JUNIT")")/$(basename "$LATEST_JUNIT")"
    FAILED_JUNIT_TESTS=$(grep -B 1 '<failure' "$LATEST_JUNIT" 2>/dev/null | grep '<testcase' | sed -n 's/.*name="\([^"]*\)".*/\1/p')
    if [ -n "$FAILED_JUNIT_TESTS" ]; then
        echo "FAILED Test Cases in JUnit XML:"
        echo "$FAILED_JUNIT_TESTS" | while read -r tc; do
            echo "   [FAIL] $tc"
        done
        echo "----------------------------------------------------------"
    else
        echo "[PASS] Zero failed test cases detected in latest JUnit XML."
        echo "----------------------------------------------------------"
    fi
fi

# 2. Scan FAILED_*.png error screenshots
if [ ! -d "$SCREENSHOT_DIR" ]; then
    echo "Info: No Screenshots directory found. Workspace has no screenshot failures."
    exit 0
fi

FAILED_COUNT=$(find "$SCREENSHOT_DIR" -maxdepth 1 -name "FAILED_*.png" 2>/dev/null | wc -l | tr -d ' ')

if [ "$FAILED_COUNT" -eq "0" ]; then
    echo "[PASS] Zero failure screenshots found in $SCREENSHOT_DIR."
    exit 0
fi

echo "Warning: Detected $FAILED_COUNT failure screenshot(s):"
echo "----------------------------------------------------------"

# Cross-platform stat helper (Linux GNU stat, macOS BSD stat, POSIX ls fallback)
list_recent_screenshots() {
    if stat --version 2>&1 | grep -q "GNU"; then
        find "$SCREENSHOT_DIR" -maxdepth 1 -name "FAILED_*.png" -type f -exec stat -c "%Y %y %n" {} + 2>/dev/null | \
            sort -rn | head -n 10 | awk '{print $1, $2, $3, $NF}'
    elif stat -f "%m" . >/dev/null 2>&1; then
        find "$SCREENSHOT_DIR" -maxdepth 1 -name "FAILED_*.png" -type f -exec stat -f "%m %Sm %N" -t "%Y-%m-%d %H:%M:%S" {} + 2>/dev/null | \
            sort -rn | head -n 10
    else
        ls -lt "$SCREENSHOT_DIR"/FAILED_*.png 2>/dev/null | head -n 10 | awk '{print "0", $6, $7, $NF}'
    fi
}

REPO_MAP_FILE=""
for cand in "$WORKSPACE_DIR/reports/repo_map.txt" "$WORKSPACE_DIR/repo_map.txt"; do
    if [ -f "$cand" ]; then
        REPO_MAP_FILE="$cand"
        break
    fi
done

list_recent_screenshots | while read -r epoch date time filepath; do
    filename=$(basename "$filepath")
    suggested_page="BasePage"
    if [ -n "$REPO_MAP_FILE" ] && [[ "$filename" =~ TC-([0-9]+) ]]; then
        tc_pattern="TC-${BASH_REMATCH[1]}"
        found_page=$(grep -m 1 -i "$tc_pattern" "$REPO_MAP_FILE" | awk '{print $1}' 2>/dev/null)
        if [ -n "$found_page" ]; then
            suggested_page="$found_page"
        fi
    fi

    echo "[$date $time] $filename"
    echo "   -> Screenshot : $filepath"
    echo "   -> Target POM : $suggested_page (under pages/ or Keywords/pages/)"
done

echo "----------------------------------------------------------"
echo "Tip: Inspect the screenshot or run tools/report/pinpoint_failure.py before patching the Page Class."
