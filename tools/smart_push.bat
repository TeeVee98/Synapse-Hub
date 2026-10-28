@echo off
REM ==============================================================================
REM DMIT AUTOMATION - DUAL REMOTE PRIVACY PUSH ENGINE (Windows Wrapper)
REM ==============================================================================
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0smart_push.ps1" %*
endlocal
