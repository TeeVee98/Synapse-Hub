#!/usr/bin/env bash
# Enterprise E2E Flow Prober Wrapper
set -e
python3 "$(dirname "$0")/e2e_flow_prober.py" "$@"
