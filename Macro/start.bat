@echo off
cd /d "%~dp0"
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~s0' -Verb RunAs"
    exit
)
python macro.py
