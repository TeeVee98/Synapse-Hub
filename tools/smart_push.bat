@echo off
REM ==============================================================================
REM ENTERPRISE AUTOMATION - DUAL REMOTE PRIVACY PUSH ENGINE (Windows Wrapper)
REM ==============================================================================
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0smart_push.ps1" %*
endlocal
