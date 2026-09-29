@echo off
setlocal

set "APP_DIR=%LOCALAPPDATA%\Programs\hitl-academic-writing-scorer-desktop"
set "APP_EXE=%APP_DIR%\HITL Academic Writing Scorer.exe"

if not exist "%APP_DIR%" mkdir "%APP_DIR%"
"%~dp07za.exe" x "%~dp0hitl-app.7z" -o"%APP_DIR%" -y
if errorlevel 1 exit /b 1

set "HITL_APP_EXE=%APP_EXE%"
call "%~dp0create-shortcuts.cmd"
if errorlevel 1 exit /b 1

start "" "%APP_EXE%"
exit /b 0
