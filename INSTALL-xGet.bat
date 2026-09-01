@echo off
setlocal
title xGet Installer
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"
if errorlevel 1 (
  echo.
  echo Installation failed. Please review the error above.
  pause
  exit /b 1
)
echo.
echo xGet is ready. A shortcut was created on your Desktop.
choice /C YN /N /M "Run xGet now? [Y/N]: "
if errorlevel 2 exit /b 0
call "%LOCALAPPDATA%\xGet\bin\xget.cmd"
