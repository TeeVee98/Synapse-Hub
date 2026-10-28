@echo off
chcp 65001 >nul
powershell -ExecutionPolicy Bypass -File "%~dp0e2e_flow_prober.ps1"
pause