@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0online\Stop-Lobby.ps1"
if errorlevel 1 pause
