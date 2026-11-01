#!/usr/bin/env bash
# Enterprise Allure Report Generator Wrapper
set -e
python3 "$(dirname "$0")/generate_allure_report.py" "$@"
