#!/usr/bin/env bash
# Enterprise Test Reports Aggregator Wrapper
set -e
python3 "$(dirname "$0")/generate_test_reports.py" "$@"
