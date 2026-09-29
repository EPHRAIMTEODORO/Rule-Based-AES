@echo off
setlocal

set "APP_DIR=%LOCALAPPDATA%\Programs\hitl-academic-writing-scorer-desktop"
set "APP_EXE=%APP_DIR%\HITL Academic Writing Scorer.exe"
set "START_MENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "START_MENU_LINK=%START_MENU_DIR%\HITL Academic Writing Scorer.lnk"
set "DESKTOP_LINK=%USERPROFILE%\Desktop\HITL Academic Writing Scorer.lnk"

if not exist "%APP_DIR%" mkdir "%APP_DIR%"
"%~dp07za.exe" x "%~dp0hitl-app.7z" -o"%APP_DIR%" -y
if errorlevel 1 exit /b 1

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $target=$env:LOCALAPPDATA + '\Programs\hitl-academic-writing-scorer-desktop\HITL Academic Writing Scorer.exe'; $work=Split-Path $target; $desktop=$env:USERPROFILE + '\Desktop\HITL Academic Writing Scorer.lnk'; $start=$env:APPDATA + '\Microsoft\Windows\Start Menu\Programs\HITL Academic Writing Scorer.lnk'; foreach($link in @($desktop,$start)){ $s=$ws.CreateShortcut($link); $s.TargetPath=$target; $s.WorkingDirectory=$work; $s.IconLocation=$target + ',0'; $s.Save() }"

start "" "%APP_EXE%"
exit /b 0
