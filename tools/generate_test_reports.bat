@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0generate_test_reports.ps1" %*
