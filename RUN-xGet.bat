@echo off
setlocal
title xGet
if exist "%LOCALAPPDATA%\xGet\bin\xget.cmd" (
  call "%LOCALAPPDATA%\xGet\bin\xget.cmd" %*
) else (
  echo xGet is not installed yet.
  echo Double-click INSTALL-xGet.bat first.
  pause
)
