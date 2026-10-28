@echo off
chcp 65001 >nul
powershell -ExecutionPolicy Bypass -File "%~dp0check_environment.ps1"
pause