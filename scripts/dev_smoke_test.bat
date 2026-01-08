@echo off
rem This batch file calls the PowerShell script for better reliability on Windows
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev_smoke_test.ps1"
exit /b %ERRORLEVEL%
