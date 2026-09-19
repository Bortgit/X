@echo off
REM Doble clic en este archivo para instalar Ollama y el modelo que usa
REM el bot, sin tener que escribir ningun comando.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_ollama_windows.ps1"
echo.
pause
