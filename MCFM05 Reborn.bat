@echo off
REM Abre a interface do MCFM05 Reborn pedindo permissao de administrador (sem janela preta).
net session >nul 2>&1
if %errorlevel% neq 0 (
  powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs -WindowStyle Hidden"
  exit /b
)
cd /d "%~dp0"
start "" pythonw gui.py
